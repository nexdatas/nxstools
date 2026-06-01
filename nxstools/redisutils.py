#   This file is part of nexdatas - Tango Server for NeXus data writer
#
#    Copyright (C) 2012-2017 DESY, Jan Kotanski <jkotan@mail.desy.de>
#
#    nexdatas is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    nexdatas is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with nexdatas.  If not, see <http://www.gnu.org/licenses/>.
#

""" Provides redis utils """


REDIS = True
try:
    from redis_om import HashModel, Field
    from typing import Optional
    from blissdata.redis_engine.identities import _UninitializedRedis
    from blissdata.redis_engine.store import DataStore
    from blissdata.schemas.scan_info import ChainDict
except Exception as e:
    print("Redis or blissdata cannot be imported: %s" % str(e))
    REDIS = False
    ChainDict = None


# Position of the moved-motor argument(s) inside a Sardana macro_command,
# counting from 0 for the macro name itself. Covers the standard Sardana
# step scans, their continuous (``*ct``) variants -- which take the same
# leading motor/start/stop arguments and only append extra timing args at
# the end, so the motor positions are unchanged -- plus the common mesh
# variants seen at DESY beamlines. This is only the best-effort fallback;
# when the deployment forwards Sardana's ``ref_moveables`` to the writer
# that is used instead and this table is irrelevant (see build_acq_chain).
SARDANA_MOTOR_POSITIONS = {
    "ascan":       [1],
    "dscan":       [1],
    "ascanct":     [1],
    "dscanct":     [1],
    "a2scan":      [1, 4],
    "d2scan":      [1, 4],
    "a2scanct":    [1, 4],
    "d2scanct":    [1, 4],
    "a3scan":      [1, 4, 7],
    "d3scan":      [1, 4, 7],
    "a3scanct":    [1, 4, 7],
    "d3scanct":    [1, 4, 7],
    "a3scan_repeat": [1, 4, 7],
    "d3scan_repeat": [1, 4, 7],
    "a4scan":      [1, 4, 7, 10],
    "d4scan":      [1, 4, 7, 10],
    "ascan_repeat": [1],
    "dscan_repeat": [1],
    "a2scan_repeat": [1, 4],
    "mesh":        [1, 5],
    "dmesh":       [1, 5],
    "dmesh_repeat": [1, 5],
    "meshct":      [1, 5],
    "mesh_repeat": [1, 5],
}


# Bookkeeping channels that are never meaningful plot Y-series; kept out of
# the acquisition_chain "scalars" list so they don't render as spurious
# curves. (The sardana-redis recorder skips point_nb entirely; the
# NXSDataWriter path records it, so we filter it here.)
NON_COUNTER_CHANNELS = {"point_nb"}


def motors_from_title(title, channels=None):
    """Return moved-motor channel names parsed from a Sardana macro_command.

    Recognises the macros listed in :data:`SARDANA_MOTOR_POSITIONS`. When
    *channels* is provided, only motors that are also recorded channels
    are kept (so a typo in the macro can't push a non-existent channel
    into the acquisition chain). Returns ``[]`` for an unrecognised or
    motorless macro (e.g. ``ct``).
    """
    if not title:
        return []
    parts = title.split()
    if not parts:
        return []
    positions = SARDANA_MOTOR_POSITIONS.get(parts[0])
    if not positions:
        return []
    motors = []
    for idx in positions:
        if idx >= len(parts):
            continue
        name = parts[idx]
        if channels is not None and name not in channels:
            continue
        motors.append(name)
    return motors


def build_acq_chain(devices, title=None, channels=None, ref_moveables=None):
    """Build a blissdata ``acquisition_chain`` dict for a Sardana scan.

    *devices* is the nxstools device-bucket dict (``"time"``,
    ``"mg_channels"``, ``"other_channels"``, ``"mca"``, ``"image"``).
    Each value has a ``channels`` list.

    The scanned motor(s) land in ``master.scalars`` (so they become the
    X-axis for downstream plot consumers like daiquiri) and are excluded
    from ``scalars`` (so they don't double up as a Y-series). The motor
    list is resolved in this order:

      1. *ref_moveables* -- Sardana's ``ref_moveables`` scan-environment
         entry, the reference moveables of *any* macro (set from the
         moveable ``is_reference`` flag, not from the macro name). This is
         robust to new/custom macros with different parameter layouts, so
         it is preferred whenever the deployment forwards it to the writer.
      2. Otherwise the motor(s) parsed from *title* (the Sardana
         ``macro_command``) via :func:`motors_from_title` -- a best-effort
         fallback for the known step/mesh macros.

    *channels* is the recorded channel-name dict; when given, motors not
    among the recorded channels are dropped. If no motor can be identified
    -- ``ct``, an unrecognised macro with no ``ref_moveables`` --
    ``master.scalars`` falls back to the time channels.
    """
    if ChainDict is None:
        return {}

    if ref_moveables:
        motors = [
            m for m in ref_moveables
            if channels is None or m in channels
        ]
    else:
        motors = motors_from_title(title, channels)
    motor_set = set(motors)

    def _channels(bucket_names):
        out = []
        for dname, dd in devices.items():
            if dname in bucket_names:
                out.extend(dd.get("channels", []) or [])
        return out

    counters = [
        ch for ch in _channels(("mg_channels", "other_channels"))
        if ch not in motor_set and ch not in NON_COUNTER_CHANNELS
    ]
    spectra = _channels(("mca",))
    images = _channels(("image",))
    time_channels = _channels(("time",))
    master_scalars = motors if motors else time_channels

    return {
        "axis": ChainDict(
            top_master="time",
            devices=list(devices.keys()),
            scalars=counters,
            spectra=spectra,
            images=images,
            master={
                "scalars": master_scalars,
                "spectra": [],
                "images": [],
            },
        )
    }


if REDIS:

    class DESYIdentityModel(HashModel):
        """Institute specific information used to link scans
           in Redis to external services.
        """

        class Meta:
            global_key_prefix = "esrf"
            model_key_prefix = "id"
            database = _UninitializedRedis()

        name: str = Field(index=True)
        number: int = Field(index=True)
        data_policy: str = Field(index=True)

        # DESY data policy
        beamline: Optional[str] = Field(index=True, default=None)
        session: Optional[str] = Field(index=True, default=None)
        proposal: Optional[str] = Field(index=True, default=None)
        collection: Optional[str] = Field(index=True, default=None)
        dataset: Optional[str] = Field(index=True, default=None)

        # Without data policy
        path: Optional[str] = Field(index=True, default=None)

else:
    DESYIdentityModel = None


def getDataStore(redisURL):

    datastore = None
    try:
        datastore = DataStore(redisURL, init_db=True,
                              identity_model_cls=DESYIdentityModel)
    except Exception:
        print("Redis DataStore already initialized")
        try:
            datastore = DataStore(redisURL,
                                  identity_model_cls=DESYIdentityModel)
        except Exception as e:
            print("Redis DataStore cannot be instantiated: %s" % str(e))

    return datastore
