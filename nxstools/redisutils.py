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
except Exception as e:
    print("Redis or blissdata cannot be imported: %s" % str(e))
    REDIS = False


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
