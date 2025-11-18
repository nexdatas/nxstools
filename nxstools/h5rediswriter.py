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

""" Provides redis h5cpp file writer """

# import math
import os
import sys
import time
# import numpy as np
# from pninexus import h5cpp
import threading
import getpass
import datetime

from . import filewriter
from .redisutils import REDIS, getDataStore
from .nxsfileparser import (getdsname, getdssource,
                            # getdstype
                            )

H5CPP = False
try:
    from . import h5cppwriter as h5writer
    H5File = h5writer.H5CppFile
    H5Group = h5writer.H5CppGroup
    H5Field = h5writer.H5CppField
    H5Link = h5writer.H5CppLink
    H5VirtualFieldLayout = h5writer.H5CppVirtualFieldLayout
    H5TargetFieldView = h5writer.H5CppTargetFieldView
    H5DataFilter = h5writer.H5CppDataFilter
    H5Deflate = h5writer.H5CppDeflate
    H5AttributeManager = h5writer.H5CppAttributeManager
    H5Attribute = h5writer.H5CppAttribute
    H5CPP = True
except Exception:
    from . import h5pywriter as h5writer
    H5File = h5writer.H5PYFile
    H5Group = h5writer.H5PYGroup
    H5Field = h5writer.H5PYField
    H5Link = h5writer.H5PYLink
    H5VirtualFieldLayout = h5writer.H5PYVirtualFieldLayout
    H5TargetFieldView = h5writer.H5PYTargetFieldView
    H5DataFilter = h5writer.H5PYDataFilter
    H5Deflate = h5writer.H5PYDeflate
    H5AttributeManager = h5writer.H5PYAttributeManager
    H5Attribute = h5writer.H5PYAttribute

PLUGINS = {}

try:
    from blissdata.redis_engine.encoding.numeric import NumericStreamEncoder
except Exception:
    NumericStreamEncoder = None
try:
    from blissdata.redis_engine.encoding.json import JsonStreamEncoder
except Exception:
    JsonStreamEncoder = None
try:
    from blissdata.streams.base import Stream
    PLUGINS["stream"] = Stream
except Exception:
    Stream = None

FileStream = None
try:
    from h5file_detector.stream import FileStream
    PLUGINS["h5file_detector"] = FileStream
except Exception:
    FileStream = None

try:
    from blissdata.schemas.scan_info import (
        ScanInfoDict,
        DeviceDict, ChainDict, ChannelDict)
except Exception:
    ScanInfoDict = None
    DeviceDict = None
    ChainDict = None
    ChannelDict = None


attrdesc = {
    "nexus_type": ["type", str],
    "unit": ["units", str],
    "depends_on": ["depends_on", str],
    "trans_type": ["transformation_type", str],
    "trans_vector": ["vector", str],
    "trans_offset": ["offset", str],
    # "source_name": ["nexdatas_source", getdsname],
    # "source_type": ["nexdatas_source", getdstype],
    "source": ["nexdatas_source", getdssource],
    # "strategy": ["nexdatas_strategy", str],
}


def splitstr(text):
    """ split string separated by space

    :param text: text to split
    :type text: :obj:`str`
    :param text: split text
    :type text: :obj:`list` <:obj:`str`>
    """
    return text.split(" ")


progattrdesc = {
    "npoints": ["npoints", int, True],
    "count_time": ["count_time", float, True],
    "measurement_group_channels": [
        "measurement_group_channels", splitstr, True],
    "title": ["scan_command", str, False],
    "beamtime_id": ["beamtime_id", str, False],
}

titleplots = {
    "mesh": {"kind": "scatter-plot", "items": [{"kind": "scatter"}]},
}


def nptype(dtype):
    """ converts to numpy types

    :param dtype: h5 writer type type
    :type dtype: :obj:`str`
    :returns: nupy type
    :rtype: :obj:`str`
    """
    return h5writer.nptype(dtype)


if sys.version_info > (3,):
    unicode = str
    long = int
else:
    bytes = str


def _tostr(text):
    """ converts text  to str type

    :param text: text
    :type text: :obj:`bytes` or :obj:`unicode`
    :returns: text in str type
    :rtype: :obj:`str`
    """
    if isinstance(text, str):
        return text
    elif sys.version_info > (3,):
        return str(text, "utf8")
    else:
        return str(text)


def unlimited_selection(sel, shape):
    """ checks if hyperslab is unlimited

    :param sel: hyperslab selection
    :type sel: :class:`filewriter.FTHyperslab`
    :param shape: give shape
    :type shape: :obj:`list`
    :returns: if hyperslab is unlimited list
    :rtype: :obj:`list` <:obj:`bool`>
    """
    return h5writer.unlimited_selection(sel, shape)


def _slice2selection(t, shape):
    """ converts slice(s) to selection

    :param t: slice tuple
    :type t: :obj:`tuple`
    :return shape: field shape
    :type shape: :obj:`list` < :obj:`int` >
    :returns: hyperslab selection
    :rtype: :class:`h5cpp.dataspace.Hyperslab`
    """
    return h5writer._slice2selection(t, shape)


def unlimited(parent=None):
    """ return dataspace UNLIMITED variable for the current writer module

    :param parent: parent object
    :type parent: :class:`FTObject`
    :returns:  dataspace UNLIMITED variable
    :rtype: :class:`h5cpp.dataspace.UNLIMITED`
    """
    return h5writer.unlimited(parent)


def open_file(filename, readonly=False, redisurl=None, session=None,
              h5fileplugin=None,
              **pars):
    """ open the new file

    :param filename: file name
    :type filename: :obj:`str`
    :param readonly: readonly flag
    :type readonly: :obj:`bool`
    :param redisurl: redis URL
    :type redisurl: :obj:`str`
    :param session: redis session
    :type session: :obj:`str`
    :param h5fileplugin: use h5file_detector plugin
    :type h5fileplugin: :obj:`str`
    :param libver: library version: 'lastest' or 'earliest'
    :type libver: :obj:`str`
    :returns: file object
    :rtype: :class:`H5RedisFile`
    """
    return H5RedisFile(h5imp=h5writer.open_file(filename, readonly, **pars),
                       redisurl=redisurl, session=session,
                       h5fileplugin=h5fileplugin)


def is_image_file_supported():
    """ provides if loading of image files are supported

    :retruns: if loading of image files are supported
    :rtype: :obj:`bool`
    """
    return h5writer.is_image_file_supported()


def is_vds_supported():
    """ provides if vds are supported

    :retruns: if vds are supported
    :rtype: :obj:`bool`
    """
    return h5writer.is_vds_supported()


def is_unlimited_vds_supported():
    """ provides if unlimited vds are supported

    :retruns: if unlimited vds are supported
    :rtype: :obj:`bool`
    """
    return h5writer.is_unlimited_vds_supported()


def load_file(membuffer, filename=None, readonly=False, **pars):
    """ load a file from memory byte buffer

    :param membuffer: memory buffer
    :type membuffer: :obj:`bytes` or :obj:`io.BytesIO`
    :param filename: file name
    :type filename: :obj:`str`
    :param readonly: readonly flag
    :type readonly: :obj:`bool`
    :param pars: parameters
    :type pars: :obj:`dict` < :obj:`str`, :obj:`str`>
    :returns: file object
    :rtype: :class:`H5RedisFile`
    """
    return H5RedisFile(
        h5imp=h5writer.load_file(membuffer, filename, readonly, **pars))


def create_file(filename, overwrite=False, redisurl=None, session=None,
                h5fileplugin=None,
                **pars):
    """ create a new file

    :param filename: file name
    :type filename: :obj:`str`
    :param overwrite: overwrite flag
    :type overwrite: :obj:`bool`
    :param libver: library version: 'lastest' or 'earliest'
    :type libver: :obj:`str`
    :param redisurl: redis URL
    :type redisurl: :obj:`str`
    :param session: redis session
    :type session: :obj:`str`
    :param h5fileplugin: use h5file_detector plugin
    :type h5fileplugin: :obj:`str`
    :returns: file object
    :rtype: :class:`H5RedisFile`
    """
    return H5RedisFile(
        h5imp=h5writer.create_file(filename, overwrite, **pars),
        redisurl=redisurl, session=session, h5fileplugin=h5fileplugin)


def link(target, parent, name):
    """ create link

    :param target: nexus path name
    :type target: :obj:`str`
    :param parent: parent object
    :type parent: :class:`FTObject`
    :param name: link name
    :type name: :obj:`str`
    :returns: link object
    :rtype: :class:`H5RedisLink`
    """
    return H5RedisLink(h5imp=h5writer.link(target, parent, name))


def get_links(parent):
    """ get links

    :param parent: parent object
    :type parent: :class:`FTObject`
    :returns: list of link objects
    :returns: link object
    :rtype: :obj: `list` <:class:`H5RedisLink`>
    """
    links = h5writer.get_links(parent)
    return [H5RedisLink(h5imp=lk) for lk in links]


def data_filter(filterid=None, name=None, options=None, availability=None,
                shuffle=None, rate=None):
    """ create data filter

    :param filterid: hdf5 filter id
    :type filterid: :obj:`int`
    :param name: filter name
    :type name: :obj:`str`
    :param options: filter cd values
    :type options: :obj:`tuple` <:obj:`int`>
    :param availability: filter availability i.e. 'optional' or 'mandatory'
    :type availability: :obj:`str`
    :param shuffle: filter shuffle
    :type shuffle: :obj:`bool`
    :param rate: filter shuffle
    :type rate: :obj:`bool`
    :returns: data filter object
    :rtype: :class:`H5RedisDataFilter`
    """
    return H5RedisDataFilter(h5imp=h5writer.data_filter(
        filterid, name, options, availability, shuffle, rate))


def deflate_filter(rate=None, shuffle=None, availability=None):
    """ create data filter

    :param rate: filter shuffle
    :type rate: :obj:`bool`
    :param shuffle: filter shuffle
    :type shuffle: :obj:`bool`
    :returns: deflate filter object
    :rtype: :class:`H5RedisDataFilter`
    """
    return H5RedisDataFilter(
        h5imp=h5writer.deflate_filter(rate, shuffle, availability))


def target_field_view(filename, fieldpath, shape,
                      dtype=None, maxshape=None):
    """ create target field view for VDS

    :param filename: file name
    :type filename: :obj:`str`
    :param fieldpath: nexus field path
    :type fieldpath: :obj:`str`
    :param shape: shape
    :type shape: :obj:`list` < :obj:`int` >
    :param dtype: attribute type
    :type dtype: :obj:`str`
    :param maxshape: shape
    :type maxshape: :obj:`list` < :obj:`int` >
    :returns: target field view object
    :rtype: :class:`H5RedisTargetFieldView`
    """
    return H5RedisTargetFieldView(
        h5imp=h5writer.target_field_view(
            filename, fieldpath, shape, dtype, maxshape))


def virtual_field_layout(shape, dtype, maxshape=None, parent=None):
    """ creates a virtual field layout for a VDS file

    :param shape: shape
    :type shape: :obj:`list` < :obj:`int` >
    :param dtype: attribute type
    :type dtype: :obj:`str`
    :param maxshape: shape
    :type maxshape: :obj:`list` < :obj:`int` >
    :returns: virtual layout
    :rtype: :class:`H5RedisVirtualFieldLayout`
    """
    return H5RedisVirtualFieldLayout(
        h5imp=h5writer.virtual_field_layout(
            shape, dtype, maxshape, parent), tparent=parent)


class H5RedisFile(H5File):

    """ file tree file
    """

    #: (:obj:`dict`) global data stores
    global_data_stores = {}

    #: (:class:`threading.Lock`) global data store lock
    global_data_store_lock = threading.Lock()

    def __init__(self, h5object=None, filename=None, h5imp=None,
                 redisurl=None, session=None, h5fileplugin=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param filename:  file name
        :type filename: :obj:`str`
        :param h5imp: h5 implementation file
        :type h5imp: :class:`filewriter.FTFile`
        :param redisurl: redis url string
        :type redisurl: :obj:`str`
        :param session: redis session
        :type session: :obj:`str`
        :param h5fileplugin: use h5file_detector plugin
        :type h5fileplugin: :obj:`str`
        """
        if h5imp is not None:
            H5File.__init__(self, h5imp.h5object, h5imp.name)
        else:
            if h5object is None or filename is None:
                raise Exception("Undefined constructor parameters")
            H5File.__init__(self, h5object, filename)
        #: (:obj:`str`) redis url
        self.__redisurl = redisurl or "redis://localhost:6380"
        self.__session = session or "test_session"
        self.__datastore = None
        self.__scan = None
        self.__scan_lock = threading.Lock()
        self.__scaninfo = {}
        self.__devices = {}
        self.__channels = {}
        self.__streams = {}
        self.__mgchannels = []
        self.__datastore = None
        self.__entryname = ''
        self.__insname = ''
        if REDIS and self.__redisurl:
            with self.global_data_store_lock:
                # print("FILENAME", self.name)
                if self.__redisurl in self.global_data_stores:
                    self.__datastore = self.global_data_stores[self.__redisurl]
                else:
                    self.__datastore = getDataStore(self.__redisurl)
                    self.global_data_stores[self.__redisurl] = self.__datastore
            # global FileStream
            # if h5fileplugin:
            #     try:
            #         from h5file_detector.stream import FileStream
            #         PLUGINS["h5file_detector"] = FileStream
            #     except Exception:
            #         FileStream = None
            # else:
            #     FileStream = None

    def root(self):
        """ root object

        :returns: parent object
        :rtype: :class:`H5RedisGroup`
        """
        return H5RedisGroup(h5imp=H5File.root(self),
                            nxclass="NXroot")

    def append_stream(self, name, stream):
        """ scan object

        :param name: stream name
        :type name: :obj:`str`
        :param scan: stream object
        :type scan: :class:`Stream`
        """
        with self.__scan_lock:
            self.__streams[name] = stream

    def set_scan(self, scan):
        """ scan object

        :param scan: scan object
        :type scan: :class:`Scan`
        """
        with self.__scan_lock:
            self.__scan = scan

    def set_entryname(self, entryname):
        """ set entry name

        :param entryname: entry name
        :type entryname: :obj:`str`
        """
        with self.__scan_lock:
            self.__entryname = entryname

    def set_insname(self, insname):
        """ set instrument name

        :param insname: instrument name
        :type insname: :obj:`str`
        """
        with self.__scan_lock:
            self.__insname = insname

    def append_devices(self, value, keys=None):
        """ append device info parameters

        :param value: device parameter value
        :type value: :obj:`any`
        :param keys: device parameter value
        :type key: :obj:`list` <:obj:`str`>
        """
        with self.__scan_lock:
            if keys is None:
                return
            dinfo = self.__devices
            rkeys = list(reversed(keys or []))
            while rkeys:
                ky = rkeys.pop()
                if len(rkeys) > 0:
                    dinfo = dinfo[ky]
                else:
                    dinfo[ky].append(value)

    def set_devices(self, value, keys=None):
        """ set device info parameters

        :param value: device parameter value
        :type value: :obj:`any`
        :param keys: device parameter keys
        :type key: :obj:`list` <:obj:`str`>
        """
        with self.__scan_lock:
            if keys is None:
                self.__devices = dict(value)
                return
            dinfo = self.__devices

            rkeys = list(reversed(keys or []))
            while rkeys:
                ky = rkeys.pop()
                if len(rkeys) > 0:
                    dinfo = dinfo[ky]
                else:
                    dinfo[ky] = value

    def get_devices(self, keys=None):
        """ get devices info parameters

        :param keys: device parameter keys
        :type key: :obj:`list` <:obj:`str`>
        :returns value: device parameter value
        :rtype value: :obj:`any`
        """
        with self.__scan_lock:
            dinfo = self.__devices
            if keys is None:
                return dict(dinfo)

            rkeys = list(reversed(keys or []))
            while rkeys:
                ky = rkeys.pop()
                dinfo = dinfo[ky]
            return dinfo

    def set_channels(self, value, keys=None):
        """ set channel info parameters

        :param value: channel parameter value
        :type value: :obj:`any`
        :param keys: channel parameter keys
        :type key: :obj:`list` <:obj:`str`>
        """
        with self.__scan_lock:
            if keys is None:
                self.__channels = dict(value)
                return
            dinfo = self.__channels

            rkeys = list(reversed(keys or []))
            while rkeys:
                ky = rkeys.pop()
                if len(rkeys) > 0:
                    dinfo = dinfo[ky]
                else:
                    dinfo[ky] = value

    def get_channels(self, keys=None):
        """ get channel info parameters

        :param keys: channel parameter keys
        :type key: :obj:`list` <:obj:`str`>
        :returns value: channel parameter value
        :rtype value: :obj:`any`
        """
        with self.__scan_lock:
            dinfo = self.__channels
            if keys is None:
                return dict(dinfo)

            rkeys = list(reversed(keys or []))
            while rkeys:
                ky = rkeys.pop()
                dinfo = dinfo[ky]
            return dinfo

    def reset_scaninfo(self, entryname):
        """ reset scan info

        :param entryname: NXentry group name
        :type entryname: :obj:`str`
        """
        self.set_entryname(entryname)

        localfname = H5RedisLink.getfilename(self.root())
        if localfname:
            dr, fn = os.path.split(localfname)
            fbase, ext = os.path.splitext(fn)
            sfbase = fbase.rsplit("_", 1)
            sn = entryname.rsplit("_", 1)
            number = 0
            try:
                number = int(sn[1])
            except Exception:
                try:
                    number = int(sfbase[1])
                except Exception:
                    number = int(time.time() * 10)
        scinfo = {
            "name": fbase,
            "scan_nb": number,
            "session_name": self.__session,
            "data_policy": 'no_policy',
            "user_name": getpass.getuser(),
            "start_time":
            datetime.datetime.now().astimezone().isoformat(),
            "title": fbase,
            "type": "scan",
            "npoints": 1,
            "count_time": 0.0,
            ##################################
            "acquisition_chain": {},
            "devices": {},
            "channels": {},
            ##################################
            "display_extra": {"plotselect": []},
            "plots": [{"kind": "curve-plot", "items": []}],
            ##################################
            "filename": localfname,
            "images_path": os.path.splitext(localfname)[0],
            "publisher": "test",
            "publisher_version": "1.0",
            "datadesc": {},
            "snapshot": {},
            "measurement_group_channels": [],
            "beamtime_id": "",
            "scan_meta_categories": [
                "snapshot",
                "datadesc",
                #     "positioners",
                #     "nexuswriter",
                #     "instrument",
                #     "technique",
            ],
            # "save": self.nexus_save,
            # "data_writer": "nexus",
            # "writer_options": {
            #      "chunk_options": {},
            #      "separate_scan_files": False},
            # "nexuswriter": {
            #     "devices": {},
            #     "instrument_info": {
            #         "name": "desy-"+self.scan.beamline,
            #         "name@short_name": self.scan.beamline},
            #     "masterfiles": masterfiles,
            #     "technique": {},
            # },
            # "positioners": {},
            # "instrument": {},
        }
        self.set_scaninfo(scinfo)
        self.set_devices({})
        # self.set_devices(
        #     DeviceDict(name="counters", channels=[],
        #   metadata={}),
        #     ["counters"])
        # self.set_devices(
        #     DeviceDict(name="axis", channels=[], metadata={}),
        #     ["axis"])
        self.set_devices(
            DeviceDict(
                name="time", channels=[], metadata={},
                triggered_devices=["mg_channels", "other_channels",
                                   "mca", "image"]),
            ["time"])
        self.set_devices(
            DeviceDict(
                name="mg_channels", channels=[], metadata={}),
            ["mg_channels"])
        self.set_devices(
            DeviceDict(
                name="other_channels", channels=[], metadata={}),
            ["other_channels"])
        self.set_devices(
            DeviceDict(
                name="mca", channels=[], metadata={}, type="mca"),
            ["mca"])
        self.set_devices(
            DeviceDict(
                name="image", channels=[], metadata={}, type="image"),
            ["image"])
        self.set_channels({})

    def set_scaninfo(self, value, keys=None, direct=False):
        """ set scan info parameters

        :param value: scan parameter value
        :type value: :obj:`any`
        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        :param direct: scan info direct flag
        :type direct: :obj:`any`
        """
        with self.__scan_lock:
            if keys is None:
                if direct is False:
                    self.__scaninfo = dict(value)
                else:
                    self.__scan.info = ScanInfoDict(value)
                return
            if direct is False:
                sinfo = self.__scaninfo
            else:
                sinfo = self.__scan.info

            rkeys = list(reversed(keys or []))
            while rkeys:
                ky = rkeys.pop()
                if len(rkeys) > 0:
                    sinfo = sinfo[ky]
                else:
                    sinfo[ky] = value

    def get_scaninfo(self, keys=None, direct=False):
        """ get scan info parameters

        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        :returns value: scan parameter value
        :rtype value: :obj:`any`
        :param direct: scan info direct flag
        :type direct: :obj:`any`
        """
        with self.__scan_lock:
            if direct is False:
                sinfo = self.__scaninfo
            else:
                sinfo = self.__scan.info
            if keys is None:
                return dict(sinfo)
            # print("KEYS", keys)
            rkeys = list(reversed(keys or []))
            while rkeys:
                ky = rkeys.pop()
                sinfo = sinfo[ky]
            return sinfo

    def append_scaninfo(self, value, keys=None, direct=False):
        """ append scan info parameters

        :param value: scan parameter value
        :type value: :obj:`any`
        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        :param direct: scan info direct flag
        :type direct: :obj:`any`
        """
        with self.__scan_lock:
            if keys is None:
                return
            if direct is False:
                sinfo = self.__scaninfo
            else:
                sinfo = self.__scan.info
            rkeys = list(reversed(keys or []))
            while rkeys:
                ky = rkeys.pop()
                if len(rkeys) > 0:
                    if ky not in sinfo:
                        sinfo[ky] = {}
                    sinfo = sinfo[ky]
                else:
                    if ky not in sinfo:
                        sinfo[ky] = []
                    sinfo[ky].append(value)

    def scan_command(self, command, *args, **kwargs):
        """ set scan attribute

        :param command: scan command
        :type command: :obj:`str`
        :param args: function list arguments
        :type args: :obj:`list` <`any`>
        :param kwargs: function dict arguments
        :type kwargs: :obj:`dict` <:obj:`str` , `any`>
        :returns: scan command value
        :rtype:  :obj:`any`
        """
        vl = None
        with self.__scan_lock:
            if hasattr(self.__scan, command):
                cmd = getattr(self.__scan, command)
                if callable(cmd):
                    vl = cmd(*args, **kwargs)
        return vl

    def scan_getattr(self, attr):
        """ get scan attribute

        :param attr: scan attr
        :type attr: :obj:`str`
        :returns: scan attr value
        :rtype:  :obj:`any`
        """
        with self.__scan_lock:
            if hasattr(self.__scan, attr):
                attr = getattr(self.__scan, attr)
        return attr

    def scan_setattr(self, attr, value):
        """ set attribute

        :param attr: scan attr
        :type attr: :obj:`str`
        :param value: scan attr value
        :type value: :obj:`any`
        """
        with self.__scan_lock:
            if hasattr(self.__scan, attr):
                attr = setattr(self.__scan, attr, value)

    def prepare(self):
        """ start scan

        """
        if REDIS:
            localfname = H5RedisLink.getfilename(self.root())
            # print("FILE", localfname, n, nxclass)
            n = self.__entryname
            insn = self.__insname
            if localfname:
                dr, fn = os.path.split(localfname)
                fbase, ext = os.path.splitext(fn)
                sfbase = fbase.rsplit("_", 1)
                sn = n.rsplit("_", 1)
                measurement = "scan"
                try:
                    if sn[0]:
                        measurement = sn[0]
                except Exception:
                    try:
                        if sfbase[0]:
                            measurement = sfbase[0]
                    except Exception:
                        measurement = fbase
                sinfo = self.get_scaninfo()
                scandct = {"name": sinfo["name"],
                           "number": sinfo["scan_nb"],
                           "dataset": fbase,
                           "path": dr,
                           # "beamline": '',
                           "session": self.__session,
                           "collection": measurement,
                           "data_policy": "no_policy"}
                if "beamtime_id" in sinfo:
                    scandct["proposal"] = sinfo["beamtime_id"]
                    sinfo.pop("beamtime_id")

                beamline = ''
                proposal = ''
                root = self.root()
                if n in root.names():
                    entry = root.open(n)
                    if insn in entry.names():
                        ins = entry.open(insn)
                        if "name" in ins.names():
                            insname = ins.open("name")
                            if insname.attributes.exists("short_name"):
                                beamline = filewriter.first(
                                    insname.attributes["short_name"].read())
                                scandct["beamline"] = beamline
                    if 'proposal' not in scandct or not scandct["proposal"]:
                        if "experiment_identifier" in entry.names():
                            proposal = filewriter.first(
                                entry.open("experiment_identifier").read())
                            if proposal:
                                scandct["proposal"] = proposal

                scan = self.__datastore.create_scan(
                    scandct, info={"name": fbase})
                self.set_scan(scan)
                # scan.prepare()
                # scan.start()

            # print("SCAN", measurement, number)
            # print("NAMES", self.names())

    def start(self):
        """ start scan

        """
        if REDIS:
            acq_chain = {}
            devices = self.get_devices()
            for n, dd in devices.items():
                if "channels" in dd:
                    dd["channels"] = list(sorted(dd["channels"]))
            self.set_scaninfo(devices, ["devices"])
            acq_chain["axis"] = ChainDict(
                top_master="time",
                devices=list(devices.keys()),
                scalars=[],
                spectra=[],
                images=[],
                master={})
            self.set_scaninfo(acq_chain, ["acquisition_chain"])
            self.set_scaninfo(self.get_channels(), ["channels"])

            info = self.scan_getattr("info")
            sinfo = self.get_scaninfo()
            # print("SCAN INFO", sinfo)
            info.update(sinfo)

            self.scan_command("prepare")
            self.scan_command("start")

    def finish(self):
        """ start scan

        """
        # print("FINISH")
        # print("CLOSE GROUP", self.__nxclass, self.name)
        if REDIS:
            for stream in self.__streams.values():
                try:
                    if hasattr(stream, "seal"):
                        stream.seal()
                        # print("SEAL", stream.name)
                except Exception as e:
                    print("Error sealing stream %s" % stream.name)
                    print(e)
                continue
            self.scan_command("stop")
            lpars = (self.get_scaninfo(["snapshot"]) or {})
            pars = (self.get_scaninfo(
                ["snapshot"], direct=True) or {})
            pars.update(lpars)
            self.set_scaninfo(pars, ["snapshot"])

            self.set_scaninfo(
                datetime.datetime.now().astimezone().isoformat(),
                ['end_time'], direct=True)
            self.set_scaninfo('SUCCESS', ['end_reason'], direct=True)
            # print("stop SCAN")
            self.scan_command("close")
            # print("close SCAN")
            # self.set_scan(None)
            #    print("SCAN None")


class H5RedisGroup(H5Group):

    """ file tree group
    """

    def __init__(self, h5object=None, tparent=None, h5imp=None,
                 nxclass=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param tparent: tree parent
        :type tparent: :obj:`FTObject`
        :param h5imp: h5 implementation group
        :type h5imp: :class:`filewriter.FTGroup`
        :param redis: redis object
        :type redis: :obj:`any`
        :param nxclass: nxclass
        :type nxclass: :obj:`str`
        """
        if h5imp is not None:
            H5Group.__init__(self, h5imp.h5object, h5imp._tparent)
        else:
            if h5object is None:
                raise Exception("Undefined constructor parameters")
            H5Group.__init__(self, h5object, tparent)
        self.__nxclass = nxclass

    def open(self, name):
        """ open a file tree element

        :param name: element name
        :type name: :obj:`str`
        :returns: file tree object
        :rtype: :class:`H5RedisLink`
        """
        h5obj = H5Group.open(self, name)
        if isinstance(h5obj, H5Group):
            nxclass = None
            if u"NX_class" in [at.name for at in h5obj.attributes]:
                nxclass = filewriter.first(
                    h5obj.attributes["NX_class"]).read()

            return H5RedisGroup(h5imp=h5obj, nxclass=nxclass)
        elif isinstance(h5obj, H5Field):
            return H5RedisField(h5imp=h5obj)
        elif isinstance(h5obj, H5Attribute):
            return H5RedisAttribute(h5imp=h5obj)
        return H5RedisLink(h5imp=h5obj)

    def open_link(self, name):
        """ open a file tree element as link

        :param name: element name
        :type name: :obj:`str`
        :returns: file tree object
        :rtype: :class:`H5RedisLink`
        """
        return H5RedisLink(h5imp=H5Group.open_link(self, name))

    def set_scan(self, scan):
        """ scan object

        :param scan: scan object
        :param type: :class:`Scan`
        """
        if hasattr(self._tparent, "set_scan"):
            return self._tparent.set_scan(scan)

    def append_stream(self, name, stream):
        """ scan object

        :param name: stream name
        :type name: :obj:`str`
        :param scan: stream object
        :type scan: :class:`Stream`
        """
        if hasattr(self._tparent, "append_stream"):
            return self._tparent.append_stream(name, stream)

    def set_entryname(self, entryname):
        """ set entry name

        :param entryname: entry name
        :type entryname: :obj:`str`
        """
        if hasattr(self._tparent, "set_entryname"):
            return self._tparent.set_scan(entryname)

    def set_insname(self, insname):
        """ set instrument name

        :param insname: instrument name
        :type insname: :obj:`str`
        """
        if hasattr(self._tparent, "set_insname"):
            return self._tparent.set_scan(insname)

    def append_devices(self, value, keys=None):
        """ append device parameters

        :param value: device value
        :type value: :obj:`any`
        :param keys: device parameter keys
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "append_devices"):
            return self._tparent.append_devices(value, keys)

    def set_devices(self, value, keys=None):
        """ set device parameters

        :param value: device parameter value
        :type value: :obj:`any`
        :param keys: device parameter keys
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "set_devices"):
            return self._tparent.set_devices(value, keys)

    def get_devices(self, value, keys=None):
        """ get scan info parameters

        :param keys: device parameter keys
        :type key: :obj:`list` <:obj:`str`>
        :returns value: device parameter value
        :rtype value: :obj:`any`
        """
        if hasattr(self._tparent, "get_devices"):
            return self._tparent.get_devices(keys)

    def set_channels(self, value, keys=None):
        """ set device parameters

        :param value: device parameter value
        :type value: :obj:`any`
        :param keys: device parameter keys
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "set_channels"):
            return self._tparent.set_channels(value, keys)

    def get_channels(self, value, keys=None):
        """ get scan info parameters

        :param keys: device parameter keys
        :type key: :obj:`list` <:obj:`str`>
        :returns value: device parameter value
        :rtype value: :obj:`any`
        """
        if hasattr(self._tparent, "get_channels"):
            return self._tparent.get_channels(keys)

    def reset_scaninfo(self, entryname):
        """ reset scan info

        :param entryname: NXentry group name
        :type entryname: :obj:`str`
        """
        if hasattr(self._tparent, "reset_scaninfo"):
            return self._tparent.reset_scaninfo(entryname)

    def set_scaninfo(self, value, keys=None, direct=False):
        """ set scan info parameters

        :param value: scan parameter value
        :type value: :obj:`any`
        :param keys: scan parameter keys
        :type key: :obj:`list` <:obj:`str`>
        :param direct: scan info direct flag
        :type direct: :obj:`any`
        """
        if hasattr(self._tparent, "set_scaninfo"):
            return self._tparent.set_scaninfo(value, keys, direct)

    def get_scaninfo(self, keys=None, direct=False):
        """ get scan info parameters

        :param keys: scan parameter keys
        :type key: :obj:`list` <:obj:`str`>
        :returns value: scan parameter value
        :rtype value: :obj:`any`
        :param direct: scan info direct flag
        :type direct: :obj:`any`
        """
        if hasattr(self._tparent, "get_scaninfo"):
            return self._tparent.get_scaninfo(keys, direct)

    def append_scaninfo(self, value, keys=None, direct=False):
        """ append scan info parameters

        :param value: scan parameter value
        :type value: :obj:`any`
        :param keys: scan parameter keys
        :type key: :obj:`list` <:obj:`str`>
        :param direct: scan info direct flag
        :type direct: :obj:`any`
        """
        if hasattr(self._tparent, "append_scaninfo"):
            return self._tparent.append_scaninfo(value, keys, direct)

    def scan_command(self, command, *args, **kwargs):
        """ set scan attribute

        :param command: scan command
        :type command: :obj:`str`
        :param args: function list arguments
        :type args: :obj:`list` <`any`>
        :param kwargs: function dict arguments
        :type kwargs: :obj:`dict` <:obj:`str` , `any`>
        :returns: scan command value
        :rtype:  :obj:`any`
        """
        if hasattr(self._tparent, "scan_command"):
            return self._tparent.scan_command(command, *args, **kwargs)

    def scan_getattr(self, attr):
        """ get scan attribute

        :param attr: scan attr
        :type attr: :obj:`str`
        :returns: scan attr value
        :rtype:  :obj:`any`
        """
        if hasattr(self._tparent, "scan_getattr"):
            return self._tparent.scan_getattr(attr)

    def scan_setattr(self, attr, value):
        """ set attribute

        :param attr: scan attr
        :type attr: :obj:`str`
        :param value: scan attr value
        :type value: :obj:`any`
        """
        if hasattr(self._tparent, "scan_setattr"):
            return self._tparent.scan_getattr(attr, value)

    def create_group(self, n, nxclass=None):
        """ open a file tree element

        :param n: group name
        :type n: :obj:`str`
        :param nxclass: group type
        :type nxclass: :obj:`str`
        :returns: file tree group
        :rtype: :class:`H5RedisGroup`
        """
        if REDIS and nxclass in ["NXinstrument", u'NXinstrument']:
            self.set_insname(n)
        if REDIS and nxclass in ["NXentry", u'NXentry']:
            self.reset_scaninfo(n)
        return H5RedisGroup(
            h5imp=H5Group.create_group(self, n, nxclass),
            nxclass=nxclass)

    def create_virtual_field(self, name, layout, fillvalue=0):
        """ creates a virtual filed tres element

        :param name: field name
        :type name: :obj:`str`
        :param layout: virual field layout
        :type layout: :class:`H5CppFieldLayout`
        :param fillvalue:  fill value
        :type fillvalue: :obj:`int` or :class:`np.ndarray`
        :returns: file tree field
        :rtype: :class:`H5RedisField`
        """
        return H5RedisField(
            h5imp=H5Group.create_virtual_field(
                self, name, layout, fillvalue))

    def create_field(self, name, type_code,
                     shape=None, chunk=None, dfilter=None):
        """ open a file tree element

        :param n: group name
        :type n: :obj:`str`
        :param type_code: nexus field type
        :type type_code: :obj:`str`
        :param shape: shape
        :type shape: :obj:`list` < :obj:`int` >
        :param chunk: chunk
        :type chunk: :obj:`list` < :obj:`int` >
        :param dfilter: filter deflater
        :type dfilter: :class:`H5CppDataFilter`
        :returns: file tree field
        :rtype: :class:`H5RedisField`
        """
        return H5RedisField(
            h5imp=H5Group.create_field(
                self, name, type_code, shape, chunk,
                (dfilter if dfilter is None else dfilter)))

    @property
    def attributes(self):
        """ return the attribute manager

        :returns: attribute manager
        :rtype: :class:`H5CppAttributeManager`
        """
        return H5RedisAttributeManager(
            h5imp=super(H5RedisGroup, self).attributes)

    class H5RedisGroupIter(object):

        def __init__(self, group=None):
            """ constructor

            :param group: group object
            :type group: :obj:`H5RedisGroup`
            """
            self.__group = group
            self.__names = group.names()

        def __next__(self):
            """ the next attribute

            :returns: attribute object
            :rtype: :class:`FTAtribute`
            """
            if self.__names:
                return self.__group.open(self.__names.pop(0))
            else:
                raise StopIteration()

        next = __next__

        def __iter__(self):
            """ attribute iterator

            :returns: attribute iterator
            :rtype: :class:`H5RedisAttrIter`
            """
            return self

    def __iter__(self):
        """ attribute iterator

        :returns: attribute iterator
        :rtype: :class:`H5RedisAttrIter`
        """
        return self.H5RedisGroupIter(self)


class H5RedisField(H5Field):

    """ file tree file
    """

    def __init__(self, h5object=None, tparent=None, h5imp=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        :param h5imp: h5 implementation field
        :type h5imp: :class:`filewriter.FTField`
        """
        if h5imp is not None:
            H5Field.__init__(self, h5imp.h5object, h5imp._tparent)
        else:
            if h5object is None:
                raise Exception("Undefined constructor parameters")
            H5Field.__init__(self, h5object, tparent)
        self.__dsname = None
        self.__stream = None
        self.__jstream = None
        self.__rstream = None
        self.__rcounter = 0

    def append_stream(self, name, stream):
        """ scan object

        :param name: stream name
        :type name: :obj:`str`
        :param scan: stream object
        :type scan: :class:`Stream`
        """
        if hasattr(self._tparent, "append_stream"):
            return self._tparent.append_stream(name, stream)

    def set_scan(self, scan):
        """ scan object

        :param scan: scan object
        :param type: :class:`Scan`
        """
        if hasattr(self._tparent, "set_scan"):
            return self._tparent.set_scan(scan)

    def append_devices(self, value, keys=None):
        """ append device parameters

        :param value: device value
        :type value: :obj:`any`
        :param keys: device parameter keys
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "append_devices"):
            return self._tparent.append_devices(value, keys)

    def set_devices(self, value, keys=None):
        """ set device parameters

        :param value: device parameter value
        :type value: :obj:`any`
        :param keys: device parameter keys
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "set_devices"):
            return self._tparent.set_devices(value, keys)

    def get_devices(self, value, keys=None):
        """ get scan info parameters

        :param keys: device parameter keys
        :type key: :obj:`list` <:obj:`str`>
        :returns value: device parameter value
        :rtype value: :obj:`any`
        """
        if hasattr(self._tparent, "get_devices"):
            return self._tparent.get_devices(keys)

    def set_channels(self, value, keys=None):
        """ set device parameters

        :param value: device parameter value
        :type value: :obj:`any`
        :param keys: device parameter keys
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "set_channels"):
            return self._tparent.set_channels(value, keys)

    def get_channels(self, value, keys=None):
        """ get scan info parameters

        :param keys: device parameter keys
        :type key: :obj:`list` <:obj:`str`>
        :returns value: device parameter value
        :rtype value: :obj:`any`
        """
        if hasattr(self._tparent, "get_channels"):
            return self._tparent.get_channels(keys)

    def append_scaninfo(self, value, keys=None, direct=False):
        """ append scan info parameters

        :param value: scan parameter value
        :type value: :obj:`any`
        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "append_scaninfo"):
            return self._tparent.append_scaninfo(value, keys, direct)

    def get_scaninfo(self, keys=None, direct=False):
        """ get scan info parameters

        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        :returns value: scan parameter value
        :rtype value: :obj:`any`
        """
        if hasattr(self._tparent, "get_scaninfo"):
            return self._tparent.get_scaninfo(keys, direct)

    def set_scaninfo(self, value, keys=None, direct=False):
        """ set scan info parameters

        :param value: scan parameter value
        :type value: :obj:`any`
        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "set_scaninfo"):
            return self._tparent.set_scaninfo(value, keys, direct)

    def scan_command(self, command, *args, **kwargs):
        """ set scan attribute

        :param command: scan command
        :type command: :obj:`str`
        :param args: function list arguments
        :type args: :obj:`list` <`any`>
        :param kwargs: function dict arguments
        :type kwargs: :obj:`dict` <:obj:`str` , `any`>
        :returns: scan command value
        :rtype:  :obj:`any`
        """
        if hasattr(self._tparent, "scan_command"):
            return self._tparent.scan_command(command, *args, **kwargs)

    def scan_getattr(self, attr):
        """ get scan attribute

        :param attr: scan attr
        :type attr: :obj:`str`
        :returns: scan attr value
        :rtype:  :obj:`any`
        """
        if hasattr(self._tparent, "scan_getattr"):
            return self._tparent.scan_getattr(attr)

    def scan_setattr(self, attr, value):
        """ set attribute

        :param attr: scan attr
        :type attr: :obj:`str`
        :param value: scan attr value
        :type value: :obj:`any`
        """
        if hasattr(self._tparent, "scan_setattr"):
            return self._tparent.scan_getattr(attr, value)

    @property
    def attributes(self):
        """ return the attribute manager

        :returns: attribute manager
        :rtype: :class:`H5CppAttributeManager`
        """
        return H5RedisAttributeManager(
            h5imp=super(H5RedisField, self).attributes)

    def __set_step_channel_info(self, dsname, units, shape, strategy="STEP",
                                o=None):
        """ set step channel info

        :param dsname: datasource name
        :type dsname: :obj:`str`
        :param units: datasource units
        :type units: :obj:`str`
        :param shape: datasource shape
        :type shape: :obj:`list` <:obj:`int`>
        :param strategy: datasource strategy
        :type strategy: :obj:`str`
        :param o: object value to write
        :type o: :obj:`any`
        """
        attrs = self.attributes
        sds = {
            "name": dsname,
            "label": dsname,
            "strategy": strategy,
            "dtype": self.dtype
        }
        if o is not None:
            if str(type(o).__name__) == "int":
                sds["dtype"] = "int64"
            elif str(type(o).__name__) == "float":
                sds["dtype"] = "float64"

        anames = [at.name for at in attrs]
        for key, vl in attrdesc.items():
            if vl[0] in anames:
                sds[key] = vl[1](
                    filewriter.first(attrs[vl[0]].read()))
        sds["nexus_path"] = self.path
        self.append_scaninfo(sds, ["datadesc", dsname])
        try:
            if self.dtype not in ['string', b'string']:
                mgchannels = self.get_scaninfo(
                    ["measurement_group_channels"])
                device_type = "other_channels"
                if shape and len(shape) == 1:
                    device_type = "mca"
                elif shape and len(shape) == 2:
                    device_type = "image"
                # if "timestamp" in dsname or \
                #    dsname.endswith("_time"):
                if "timestamp" in dsname:
                    device_type = "time"
                elif dsname in mgchannels:
                    if shape and len(shape) == 1:
                        device_type = "mca"
                    elif shape and len(shape) == 2:
                        device_type = "image"
                    else:
                        device_type = "mg_channels"

                self.append_devices(
                    dsname, [device_type, 'channels'])
                if units:
                    ch = ChannelDict(
                        device=device_type, dim=len(shape),
                        display_name=dsname, unit=units)
                else:
                    ch = ChannelDict(
                        device=device_type, dim=len(shape),
                        display_name=dsname)
                self.set_channels(ch, [dsname])
                if len(shape) < 2:
                    encoder = NumericStreamEncoder(
                        dtype=sds["dtype"],
                        shape=shape)
                    if Stream is not None:
                        sdef = Stream.make_definition(dsname,
                                                      encoder,
                                                      shape=shape,
                                                      info={"unit": units})
                        self.__stream = self.scan_command(
                            "create_stream", sdef)
                    else:
                        self.__stream = self.scan_command(
                            "create_stream",
                            dsname,
                            encoder,
                            info={"unit": units})
                    self.append_stream(dsname, self.__stream)
                    if not shape:
                        # plot_type = 1
                        # plot_axes = []
                        # axes = []
                        # self.append_scaninfo(
                        #     {"kind": "curve-plot",
                        #      "name": dsname,
                        #      "items": axes}, ["plots"])
                        pass
                    else:
                        # self.append_scaninfo(
                        #     {"kind": "1d-plot",
                        #      # "name": "mg_channels",
                        #      "name": dsname,
                        #      "x": "index",
                        #      "items": [
                        #          {
                        #              # "kind": "curve",
                        #              "y": [dsname]
                        #          }
                        #      ]},
                        #     ["plots"])
                        pass
                elif Stream is not None and FileStream is not None:
                    filename = None
                    obj = self
                    while filename is None:
                        par = obj.parent
                        if par is None:
                            break
                        # print("PAR", par.name)
                        if hasattr(par, "root") and hasattr(par, "name"):
                            filename = par.name
                            break
                        else:
                            obj = par

                        # print("FILENAME", filename)
                    sdef = FileStream.make_definition(
                        name=dsname,
                        dtype=sds["dtype"],
                        shape=shape,
                        file_pattern=str(filename),
                        frames_per_file=0,
                        data_path=self.path,
                        # data_path="/scan/data/%s" % dsname ,
                        info={"unit": units},
                        file_index_offset=1,
                        file_mode="single")
                    self.__rstream = self.scan_command(
                        "create_stream", sdef)
                    self.__rcounter = 0
                self.append_stream(dsname, self.__rstream)
            else:
                if Stream is not None:
                    sdef = Stream.make_definition(
                        dsname, JsonStreamEncoder())
                    self.__jstream = self.scan_command(
                        "create_stream", sdef)
                else:
                    self.__jstream = self.scan_command(
                        "create_stream",
                        dsname, JsonStreamEncoder())
                self.append_stream(dsname, self.__jstream)
        except RuntimeError as e:
            if "already exists" in str(e):
                print(str(e))
            else:
                raise

    def __set_init_channel_info(self, dsname, units, shape, strategy, o):
        """ set init channel info

        :param dsname: datasource name
        :type dsname: :obj:`str`
        :param units: datasource units
        :type units: :obj:`str`
        :param shape: datasource shape
        :type shape: :obj:`list` <:obj:`int`>
        :param strategy: datasource strategy i.e. INIT or FINAL
        :type strategy: :obj:`str`
        :param o: object value to write
        :type o: :obj:`any`
        """
        attrs = self.attributes
        ids = {
            "name": dsname,
            "label": dsname,
            "value": o,
            "strategy": strategy,
            "dtype": self.dtype
        }

        anames = [at.name for at in attrs]
        for key, vl in attrdesc.items():
            if vl[0] in anames:
                ids[key] = vl[1](
                    filewriter.first(attrs[vl[0]].read()))
        ids["nexus_path"] = self.path
        pars = (self.get_scaninfo(["snapshot"]) or {}).keys()
        dsn = dsname
        while dsn in pars:
            dsn = dsn + "_"
        self.append_scaninfo(ids, ["snapshot", dsn])
        if self.name in ["program_name"]:
            for key, vl in progattrdesc.items():
                if vl[0] in anames:
                    try:
                        try:
                            np = vl[1](
                                filewriter.first(attrs[vl[0]].read()))
                        except Exception:
                            np = str(filewriter.first(attrs[vl[0]].read()))
                        if vl[2] or np:
                            self.set_scaninfo(np, [key])
                            if isinstance(np, str):
                                macro_name = np.split(" ")[0]
                            for mn, plot in titleplots.items():
                                if mn in macro_name:
                                    self.append_scaninfo(plot, ["plots"])

                    except Exception as e:
                        print(str(e))
                        pass

    def __set_channel_info(self, o):
        """ set channel value

        :param o: object value to write
        :type o: :obj:`any`
        """

        attrs = self.attributes
        strategy = filewriter.first(attrs["nexdatas_strategy"].read())
        dsname = "%s_%s" % (self._tparent.name, self.name)
        dsnm = ""
        if "nexdatas_source" in attrs.names():
            dsnm = getdsname(
                filewriter.first(attrs["nexdatas_source"].read()))
            dsname = dsnm
        units = ""
        if "units" in attrs.names():
            units = filewriter.first(attrs["units"].read())
        self.__dsname = dsname
        shape = []
        if hasattr(o, "shape"):
            shape = o.shape
        # print("SETITEM", self, self.name, self.shape,
        #       self.attributes.names(),
        #        self.__dsname, strategy, self.dtype,
        #       type(o), str(t), units)
        if strategy in ["STEP"] and dsnm:
            # skip 2D images
            if not shape or len(shape) < 2 or FileStream is not None:
                self.__set_step_channel_info(dsname, units, shape, strategy, o)
        else:
            self.__set_init_channel_info(dsname, units, shape, strategy, o)

    def __setitem__(self, t, o):
        """ set value

        :param t: slice tuple
        :type t: :obj:`tuple`
        :param o: h5 object
        :type o: :obj:`any`
        """
        if REDIS:
            if self.__dsname is None and \
               "nexdatas_strategy" in self.attributes.names():
                self.__set_channel_info(o)
        if REDIS and self.__dsname is not None:
            if hasattr(self.__stream, "send"):
                self.__stream.send(o)
            jo = o
            if hasattr(self.__jstream, "send"):
                if not isinstance(o, dict):
                    jo = {"value": o}
                self.__jstream.send(jo)
            if hasattr(self.__rstream, "send"):
                jo = {"stored": True, "frame": self.__rcounter}
                self.__rstream.send(jo)
                self.__rcounter += 1
        H5Field.__setitem__(self, t, o)


class H5RedisLink(H5Link):

    """ file tree link
    """

    def __init__(self, h5object=None, tparent=None, h5imp=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        """
        if h5imp is not None:
            H5Link.__init__(self, h5imp.h5object, h5imp._tparent)
        else:
            if h5object is None:
                raise Exception("Undefined constructor parameters")
            H5Link.__init__(self, h5object, tparent)


class H5RedisDataFilter(H5DataFilter):

    """ file tree deflate
    """
    def __init__(self, h5object=None, tparent=None, h5imp=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        :param h5imp: h5 implementation data filter
        :type h5imp: :class:`filewriter.FTDataFilter`
        """
        if h5imp is not None:
            H5DataFilter.__init__(
                self, h5imp.h5object, h5imp._tparent)
            self.shuffle = h5imp.shuffle
            self.rate = h5imp.rate
            self.filterid = h5imp.filterid
            self.options = h5imp.options
            self.name = h5imp.name
            self.availability = h5imp.availability
        else:
            if h5object is None:
                raise Exception("Undefined constructor parameters")
            H5DataFilter.__init__(self, h5object, tparent)


class H5RedisVirtualFieldLayout(H5VirtualFieldLayout):

    """ virtual field layout """

    def __init__(self, h5object=None, shape=None, dtype=None, maxshape=None,
                 h5imp=None, tparent=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param shape: shape
        :type shape: :obj:`list` < :obj:`int` >
        :param dtype: attribute type
        :type dtype: :obj:`str`
        :param maxshape: shape
        :type maxshape: :obj:`list` < :obj:`int` >
        :param h5imp: h5 implementation  virtual field layout
        :type h5imp: :class:`filewriter.FTVirtualFieldLayout`
        """
        if h5imp is not None:
            H5VirtualFieldLayout.__init__(
                self, h5imp.h5object, h5imp.shape, h5imp.dtype,
                h5imp.maxshape, tparent)
        else:
            if h5object is None or shape is None:
                raise Exception("Undefined constructor parameters")
            H5VirtualFieldLayout.__init__(
                self, h5object, shape, dtype, maxshape, tparent)
        self.__rstream = None
        self.__rcounter = 0

    def append_vmap(self, vmap, strategy=None):
        """ appends virtual map description into vmap list

        :param vmap: virtual map description
        :type vmap: :obj:`dict`
        :param strategy: datasource strategy i.e. INIT or FINAL
        :type strategy: :obj:`str`
        """
        H5VirtualFieldLayout.append_vmap(self, vmap)
        # print("APEEND", vmap, strategy)
        plugin_stream = None
        if strategy in ["STEP"]:
            frame = 0
            if "plugin_stream" in vmap:

                plugin_stream = vmap["plugin_stream"]
                if "frame" in plugin_stream:
                    frame = plugin_stream["frame"]
            # print("FRAME", frame)
            if frame == 0 and "plugin" in vmap and \
                    vmap["plugin"] in PLUGINS.keys() \
                    and "plugin_def" in vmap:
                # print("CREATE", vmap["plugin"])
                plugin = PLUGINS[vmap["plugin"]]
                plugin_def = vmap["plugin_def"]
                try:
                    sdef = plugin.make_definition(**plugin_def)
                    # print("create", plugin_def)
                    self.__rstream = self.scan_command(
                        "create_stream", sdef)
                    self.__rcounter = 0
                    self.append_stream(plugin_def["name"], self.__rstream)
                except Exception as e:
                    print("VMAP ERROR", vmap, str(e))

                dsname = plugin_def["name"]
                sds = {
                    "name": dsname,
                    "label": dsname,
                    "strategy": strategy,
                    "dtype": plugin_def["dtype"]
                }
                shape = plugin_def["shape"]

                sds["nexus_path"] = self._tparent.path
                self.append_scaninfo(sds, ["datadesc", dsname])
                mgchannels = self.get_scaninfo(
                    ["measurement_group_channels"])
                device_type = "other_channels"
                if shape and len(shape) == 1:
                    device_type = "mca"
                elif shape and len(shape) == 2:
                    device_type = "image"
                if "timestamp" in dsname:
                    device_type = "time"
                elif dsname in mgchannels:
                    if shape and len(shape) == 1:
                        device_type = "mca"
                    elif shape and len(shape) == 2:
                        device_type = "image"
                    else:
                        device_type = "mg_channels"

                self.append_devices(
                    dsname, [device_type, 'channels'])
                units = None
                if "info" in plugin_def and "unit" in plugin_def["info"]:
                    units = plugin_def["info"]["unit"]
                if units:
                    ch = ChannelDict(
                        device=device_type, dim=len(shape),
                        display_name=dsname, unit=units)
                else:
                    ch = ChannelDict(
                        device=device_type, dim=len(shape),
                        display_name=dsname)
                self.set_channels(ch, [dsname])

            if hasattr(self.__rstream, "send") and plugin_stream is not None:
                try:
                    self.__rstream.send(plugin_stream)
                    self.__rcounter += 1
                except Exception as e:
                    print("VMAP SEND  ERROR", vmap, str(e))

    def append_devices(self, value, keys=None):
        """ append device parameters

        :param value: device value
        :type value: :obj:`any`
        :param keys: device parameter keys
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "append_devices"):
            return self._tparent.append_devices(value, keys)

    def append_stream(self, name, stream):
        """ scan object

        :param name: stream name
        :type name: :obj:`str`
        :param scan: stream object
        :type scan: :class:`Stream`
        """
        if hasattr(self._tparent, "append_stream"):
            return self._tparent.append_stream(name, stream)

    def scan_command(self, command, *args, **kwargs):
        """ set scan attribute

        :param command: scan command
        :type command: :obj:`str`
        :param args: function list arguments
        :type args: :obj:`list` <`any`>
        :param kwargs: function dict arguments
        :type kwargs: :obj:`dict` <:obj:`str` , `any`>
        :returns: scan command value
        :rtype:  :obj:`any`
        """
        if hasattr(self._tparent, "scan_command"):
            return self._tparent.scan_command(command, *args, **kwargs)

    def append_scaninfo(self, value, keys=None, direct=False):
        """ append scan info parameters

        :param value: scan parameter value
        :type value: :obj:`any`
        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "append_scaninfo"):
            return self._tparent.append_scaninfo(value, keys, direct)

    def get_scaninfo(self, keys=None, direct=False):
        """ get scan info parameters

        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        :returns value: scan parameter value
        :rtype value: :obj:`any`
        """
        if hasattr(self._tparent, "get_scaninfo"):
            return self._tparent.get_scaninfo(keys, direct)

    def set_channels(self, value, keys=None):
        """ set device parameters

        :param value: device parameter value
        :type value: :obj:`any`
        :param keys: device parameter keys
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "set_channels"):
            return self._tparent.set_channels(value, keys)


class H5RedisTargetFieldView(H5TargetFieldView):

    """ target field for VDS """

    def __init__(self, filename=None, fieldpath=None, shape=None, dtype=None,
                 maxshape=None, h5imp=None):
        """ constructor

        :param filename: file name
        :type filename: :obj:`str`
        :param fieldpath: nexus field path
        :type fieldpath: :obj:`str`
        :param shape: shape
        :type shape: :obj:`list` < :obj:`int` >
        :param dtype: attribute type
        :type dtype: :obj:`str`
        :param maxshape: shape
        :type maxshape: :obj:`list` < :obj:`int` >
        :param h5imp: h5 implementation targetfieldview
        :type h5imp: :class:`filewriter.FTTargetFieldView`
        """
        if h5imp is not None:
            if H5CPP:
                H5TargetFieldView.__init__(
                    self, h5imp.filename, h5imp.fieldpath, h5imp.shape,
                    h5imp.dtype, h5imp.maxshape)
            else:
                H5TargetFieldView.__init__(
                    self, h5imp.filename, h5imp.fieldpath, h5imp.shape,
                    h5imp.dtype, h5imp.maxshape)
        else:
            if fieldpath is None or shape is None or filename is None:
                raise Exception("Undefined constructor parameters")
            if H5CPP:
                H5TargetFieldView.__init__(
                    self, filename, fieldpath, shape, dtype, maxshape)


class H5RedisDeflate(H5RedisDataFilter):

    """ deflate filter """


class H5RedisAttributeManager(H5AttributeManager):

    """ file tree attribute
    """

    def __init__(self, h5object=None, tparent=None, h5imp=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        :param h5imp: h5 implementation attributemanager
        :type h5imp: :class:`filewriter.FTAttributeManager`
        """
        if h5imp is not None:
            H5AttributeManager.__init__(self, h5imp.h5object, h5imp._tparent)
        else:
            if h5object is None:
                raise Exception("Undefined constructor parameters")
            H5AttributeManager.__init__(self, h5object, tparent)

    def create(self, name, dtype, shape=None, overwrite=False):
        """ create a new attribute

        :param name: attribute name
        :type name: :obj:`str`
        :param dtype: attribute type
        :type dtype: :obj:`str`
        :param shape: attribute shape
        :type shape: :obj:`list` < :obj:`int` >
        :param overwrite: overwrite flag
        :type overwrite: :obj:`bool`
        :returns: attribute object
        :rtype: :class:`H5RedisAttribute`
        """
        return H5RedisAttribute(
            h5imp=H5AttributeManager.create(
                self, name, dtype, shape, overwrite))

    def __getitem__(self, name):
        """ get value

        :param name: attribute name
        :type name: :obj:`str`
        :returns: attribute object
        :rtype: :class:`FTAtribute`
        """
        return H5RedisAttribute(
            h5imp=H5AttributeManager.__getitem__(self, name))


class H5RedisAttribute(H5Attribute):

    """ file tree attribute
    """

    def __init__(self, h5object=None, tparent=None, h5imp=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        :param h5imp: h5 implementation attribute
        :type h5imp: :class:`filewriter.FTAttribute`
        """
        if h5imp is not None:
            H5Attribute.__init__(self, h5imp.h5object, h5imp._tparent)
        else:
            if h5object is None:
                raise Exception("Undefined constructor parameters")
            H5Attribute.__init__(self, h5object, tparent)
