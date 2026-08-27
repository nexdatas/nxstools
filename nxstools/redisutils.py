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

from . import filewriter

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


# Sardana macros that perform a 2D raster scan -- they are rendered as a
# blissdata "scatter-plot" instead of the default "curve-plot". Covers the
# absolute/relative mesh, their continuous (``*ct``) and ``*_repeat``
# variants seen at DESY beamlines. Any motor scan that is not in this set
# falls back to a curve-plot (see build_plots).
MESH_MACROS = {
    "mesh", "amesh", "dmesh",
    "meshct", "ameshct", "dmeshct",
    "mesh_repeat", "amesh_repeat", "dmesh_repeat",
}


def splitstr(text):
    """ split string separated by space

    :param text: text to split
    :type text: :obj:`str`
    :returns: split text
    :rtype: :obj:`list` <:obj:`str`>
    """
    return text.split(" ")


def joinstr(textlst):
    """ join strings

    :param textlst: text strings to join
    :type textlst: :obj:`list` <:obj:`str`>
    :returns: joined text
    :rtype: :obj:`str`
    """
    return ", ".join(textlst)


def get_title(fulltitle):
    """ join strings

    :param fulltitle: title with MG in front of
    :type fulltitle: :obj:`str`
    :returns: joined text
    :rtype: :obj:`str`
    """
    if ", " not in fulltitle:
        return fulltitle
    return fulltitle.split(", ", -1)[-1]


progattrdesc = {
    "npoints": ["npoints", int, True],
    "count_time": ["count_time", float, True],
    "measurement_group_channels": [
        "measurement_group_channels", splitstr, True],
    "title": [["measurement_group", "scan_command"], joinstr, False],
    "beamtime_id": ["beamtime_id", str, False],
    # Sardana's reference moveables (the scanned motor names). Captured
    # only when the program datasource exposes a "ref_moveables" attribute;
    # used to put the moved motor on the X-axis (acquisition_chain master)
    # independently of the macro name. See build_acq_chain in redisutils.
    "reference_moveables": ["ref_moveables", splitstr, False],
}


def progattr(vl, anames, attrs):
    np = ""
    if isinstance(vl[0], list):
        values = []
        nms = vl[0]
        for nm in nms:
            if nm in anames:
                try:
                    val = filewriter.first(attrs[nm].read())
                    values.append(val)
                except Exception:
                    pass
            else:
                values = []
                break
        if not values:
            return
        try:
            np = vl[1](values)
        except Exception:
            np = str(values)
    elif vl[0] in anames:
        try:
            np = vl[1](
                filewriter.first(attrs[vl[0]].read()))
        except Exception:
            np = str(filewriter.first(attrs[vl[0]].read()))
    return np


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


def _classify_channels(channels, motor_set):
    """Split the scan_info channel dict into plot-relevant buckets.

    Returns ``(counters, time_channels, spectra)`` lists of channel names:

      * *counters* -- scalar channels (``dim`` 0) that are neither a scanned
        motor nor a bookkeeping channel; they become the curve/scatter
        Y-series.
      * *time_channels* -- ``"time"`` device channels, used as the X-axis
        fallback for a motorless scan.
      * *spectra* -- 1D (MCA) channels. :func:`build_plots` does not act on
        these (flint infers their ``1d-plot`` from the acquisition_chain),
        but they are returned for completeness.

    2D (image) channels are skipped here -- the plot consumer builds image
    plots from the device descriptions itself.
    """
    counters = []
    time_channels = []
    spectra = []
    for name, cd in (channels or {}).items():
        cd = cd or {}
        device = cd.get("device")
        dim = cd.get("dim", 0)
        if device == "time":
            time_channels.append(name)
        elif dim == 1 or device == "mca":
            spectra.append(name)
        elif dim >= 2 or device == "image":
            continue
        elif name in motor_set or name in NON_COUNTER_CHANNELS:
            continue
        else:
            counters.append(name)
    return counters, time_channels, spectra


def _mesh_axis_meta(parts):
    """Per-motor scatter axis metadata parsed from a Sardana mesh command.

    Layout: ``mesh mot_x start_x stop_x nx mot_y start_y stop_y ny ...``.
    ``axis_points`` is intervals+1 (the number of points) and ``axis_id``
    is 0 for the fast (x) motor, 1 for the slow (y) motor. Missing or
    non-numeric arguments are skipped rather than raising.
    """
    meta = {}
    # (motor, start, stop, intervals) argument positions, and the axis id
    for mpos, spos, tpos, npos, axis_id in [(1, 2, 3, 4, 0), (5, 6, 7, 8, 1)]:
        try:
            meta[parts[mpos]] = {
                "axis_kind": "forth",
                "axis_id": axis_id,
                "axis_points": int(parts[npos]) + 1,
                "start": float(parts[spos]),
                "stop": float(parts[tpos]),
            }
        except (IndexError, ValueError):
            continue
    return meta


def _first_value_counter(counters, channels):
    """Pick a scatter ``value`` counter, preferring a non-time channel.

    A channel whose unit is seconds is a poor default value (it is usually
    the integration time), so prefer the first counter with a different
    unit, mirroring flint's default-counter selection. Falls back to the
    first counter, or ``None`` so the consumer can choose.
    """
    for name in counters:
        if (channels.get(name) or {}).get("unit") != "s":
            return name
    return counters[0] if counters else None


def build_plots(title=None, channels=None, ref_moveables=None):
    """Build blissdata ``scan_info['plots']`` descriptors for a Sardana scan.

    Returns ``{"plots": [...], "channel_meta": {name: {...}}}`` where
    ``channel_meta`` holds scatter axis metadata to merge into the channels.
    This function is independent of the optional blissdata import so it can
    be exercised without a Redis backend.
    """
    channels = channels or {}
    if ref_moveables:
        motors = [m for m in ref_moveables if m in channels]
    else:
        motors = motors_from_title(title, channels)
    motor_set = set(motors)

    # spectra are intentionally unused: flint infers their 1d-plot from the
    # acquisition_chain (see the docstring), so we never emit one here.
    counters, time_channels, _spectra = _classify_channels(channels, motor_set)

    parts = (title or "").split()
    macro = parts[0] if parts else ""

    plots = []
    channel_meta = {}

    is_mesh = macro in MESH_MACROS

    if is_mesh:
        xaxis = time_channels[0] if time_channels else None
    elif motors:
        xaxis = motors[0]
    elif time_channels:
        xaxis = time_channels[0]
    else:
        xaxis = None

    if is_mesh and len(motors) >= 2:
        item = {"kind": "scatter", "x": motors[0], "y": motors[1]}
        value = _first_value_counter(counters, channels)
        if value is not None:
            item["value"] = value
        plots.append({"kind": "scatter-plot", "items": [item]})
        channel_meta = _mesh_axis_meta(parts)

    items = []
    for counter in counters:
        item = {"kind": "curve", "y": counter}
        if xaxis is not None:
            item["x"] = xaxis
        items.append(item)
    plots.append({"kind": "curve-plot", "items": items})

    return {"plots": plots, "channel_meta": channel_meta}


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
