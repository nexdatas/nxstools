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

""" Provides h5cpp file writer """

import math
import os
import sys
import time
import datetime
import getpass
import threading
import numpy as np

from . import filewriter
# from .Types import nptype
from .redisutils import (
    REDIS, getDataStore, build_acq_chain, build_plots,
    progattrdesc, progattr, get_title)
from .nxsfileparser import (getdsname, getdssource,
                            tolist,
                            # getdstype
                            )

UNLIMITED = 18446744073709551615

MAXSIZE = 100

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

LimaStream = None
try:
    from blissdata.streams.lima.stream import LimaStream
    from blissdata.lima.client import acquisition_on_server
    PLUGINS["lima"] = LimaStream
except Exception:
    LimaStream = None
    acquisition_on_server = None

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
    "trans_vector": ["vector", tolist],
    "trans_offset": ["offset", tolist],
    # "source_name": ["nexdatas_source", getdsname],
    # "source_type": ["nexdatas_source", getdstype],
    "source": ["nexdatas_source", getdssource],
    "nexdatas_source": ["nexdatas_source", str],
    # "strategy": ["nexdatas_strategy", str],
}


try:
    _npver = np.version.version.split(".")
    NPMAJOR = int(_npver[0])
    if NPMAJOR > 1:
        npunicode = np.str_
    else:
        npunicode = np.unicode_
except Exception:
    NPMAJOR = 1
    npunicode = np.unicode_


def nptype(dtype):
    """ converts to numpy types

    :param dtype: h5 writer type type
    :type dtype: :obj:`str`
    :returns: nupy type
    :rtype: :obj:`str`
    """
    if str(dtype) in ['string', b'string']:
        return 'str'
    return dtype


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
        return str(text, "utf-8")
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
    res = []
    if isinstance(sel, tuple):
        res = []
        for sl in sel:
            if hasattr(sl, "stop"):
                res.append(True if sl.stop in [unlimited()] else False)
            elif hasattr(sl, "count"):
                res.append(True if sl.count in [unlimited()] else False)
            else:
                res.append(True if sl in [unlimited()] else False)

    elif hasattr(sel, "count"):
        res = []
        for ct in sel.count:
            res.append(True if ct in [unlimited()] else False)
    elif isinstance(sel, slice):
        res = [True if sel.stop in [unlimited()] else False]

    elif sel in [unlimited()]:
        res = [True]
    lsh = len(shape)
    lct = len(res)
    ln = max(lsh, lct)
    if res and any(t is True for t in res):
        offset = [0 for _ in range(ln)]
        block = [1 for _ in range(ln)]
        stride = [1 for _ in range(ln)]
        count = list(shape)
        while lct > len(count):
            count.append(1)
        for si in range(lct):
            if res[si]:
                count[si] = UNLIMITED
        # print("Hyperslab1 %s %s %s %s" % (offset, block, count, stride))
        return filewriter.FTHyperslab(
            offset=offset, block=block, count=count, stride=stride)
    else:
        return None


def _selection2slice(t, shape):
    """ converts selection to slice(s)

    :param t: slice tuple
    :type t: :obj:`tuple`
    :return shape: field shape
    :type shape: :obj:`list` < :obj:`int` >
    :returns: tuple of slices
    :rtype: :obj:`tuple`<>
    """
    if isinstance(t, filewriter.FTHyperslab):
        offset = list(t.offset or [])
        block = list(t.block or [])
        count = list(t.count or [])
        stride = list(t.stride or [])
        slices = []
        for dm, sz in enumerate(shape):
            if len(offset) > dm:
                if offset[dm] is None:
                    offset[dm] = 0
            else:
                offset.append(0)
            if len(block) > dm:
                if block[dm] is None:
                    block[dm] = 1
            else:
                block.append(1)
            if len(count) > dm:
                if count[dm] is None:
                    count[dm] = sz
            else:
                count.append(sz)
            if len(stride) > dm:
                if stride[dm] is None:
                    stride[dm] = 1
            else:
                block.append(1)
            if len(stride) > dm:
                if stride[dm] is None:
                    stride[dm] = 1
            else:
                stride.append(1)
            if block[dm] == 1 and count[dm] == 1 and stride[dm] == 1:
                slices.append(offset[dm])
            elif stride[dm] == 1:
                slices.append(slice(
                    offset[dm], offset[dm] + block[dm] * count[dm], None))
            elif stride[dm] != 1 and block[dm] == 1:
                slices.append(slice(offset[dm],
                                    offset[dm] + count[dm] * stride[dm],
                                    stride[dm]))
            elif stride[dm] != 1 and count[dm] == 1:
                slices.append(slice(offset[dm],
                                    offset[dm] + block[dm] * stride[dm],
                                    stride[dm]))
            else:
                slices.append(Ellipsis)
        return tuple(slices)
    return t


def _slice2selection(t, shape):
    """ converts slice(s) to selection

    :param t: slice tuple
    :type t: :obj:`tuple`
    :param shape: field shape
    :type shape: :obj:`list` < :obj:`int` >
    :returns: hyperslab selection
    :rtype: :class:`h5cpp.dataspace.Hyperslab`
    """
    if t is Ellipsis:
        return None
    elif isinstance(t, filewriter.FTHyperslab):
        offset = list(t.offset or [])
        block = list(t.block or [])
        count = list(t.count or [])
        stride = list(t.stride or [])
        for dm, sz in enumerate(shape):
            if len(offset) > dm:
                if offset[dm] is None:
                    offset[dm] = 0
            else:
                offset.append(0)
            if len(block) > dm:
                if block[dm] is None:
                    block[dm] = 1
            else:
                block.append(1)
            if len(count) > dm:
                if count[dm] is None:
                    count[dm] = sz
            else:
                count.append(sz)
            if len(stride) > dm:
                if stride[dm] is None:
                    stride[dm] = 1
            else:
                stride.append(1)
        # print("Hyperslab2 %s %s %s %s" % (offset, block, count, stride))
        return filewriter.FTHyperslab(offset, block, count, stride)

    elif isinstance(t, slice):
        start = t.start or 0
        stop = t.stop or shape[0]
        if start < 0:
            start == shape[0] + start
        if stop < 0:
            stop == shape[0] + stop
        if t.step in [None, 1]:
            return filewriter.FTHyperslab(
                offset=[start], block=[stop - start],
                count=[1], stride=[stop - start])
        else:
            return filewriter.FTHyperslab(
                offset=[start],
                count=[int(math.ceil((stop - start) / float(t.step)))],
                stride=[t.step], block=[1])
    elif isinstance(t, (int, long)) and shape and len(shape) > 1:
        offset = [0] * len(shape)
        offset[0] = t
        return filewriter.FTHyperslab(
            offset=offset, block=shape,
            stride=shape, count=[1] * len(shape))
    elif isinstance(t, (int, long)):
        return filewriter.FTHyperslab(offset=[t], block=[1],
                                      count=[1], stride=[1])
    elif isinstance(t, (list, tuple)):
        offset = []
        block = []
        count = []
        stride = []
        it = -1
        for tit, tel in enumerate(t):
            it += 1
            if isinstance(tel, (int, long)):
                if tel < 0:
                    offset.append(shape[it] + tel)
                else:
                    offset.append(tel)
                block.append(1)
                count.append(1)
                stride.append(1)
            elif isinstance(tel, slice):
                start = tel.start if tel.start is not None else 0
                stop = tel.stop if tel.stop is not None else shape[it]
                if start < 0:
                    start == shape[it] + start
                if stop < 0:
                    stop == shape[it] + stop
                if tel.step in [None, 1]:
                    offset.append(start)
                    block.append(stop - start)
                    count.append(1)
                    stride.append(stop - start)
                else:
                    offset.append(start)
                    block.append(1)
                    count.append(
                        int(math.ceil(
                            (stop - start) / float(tel.step))))
                    stride.append(tel.step)
            elif tel is Ellipsis:
                esize = len(shape) - len(t) + 1
                for jt in range(esize):
                    offset.append(0)
                    block.append(shape[it])
                    count.append(1)
                    stride.append(shape[it])
                    if jt < esize - 1:
                        it += 1
        # print("Hyperslab3 %s %s %s %s" % (offset, block, count, stride))
        if len(offset):
            return filewriter.FTHyperslab(offset, block, count, stride)


def unlimited(parent=None):
    """ return dataspace UNLIMITED variable for the current writer module

    :param parent: parent object
    :type parent: :class:`FTObject`
    :returns:  dataspace UNLIMITED variable
    :rtype: :class:`UNLIMITED`
    """
    return UNLIMITED


def open_file(filename, readonly=False, libver=None, swmr=False):
    """ open the new file

    :param filename: file name
    :type filename: :obj:`str`
    :param readonly: readonly flag
    :type readonly: :obj:`bool`
    :param libver: library version: 'lastest' or 'earliest'
    :type libver: :obj:`str`
    :returns: file object
    :rtype: :class:`RedisFile`
    """

    # fapl = h5cpp.property.FileAccessList()
    # if hasattr(fapl, "set_close_degree"):
    #     fapl.set_close_degree(h5cpp._property.CloseDegree.STRONG)
    # if readonly:
    #     flag = h5cpp.file.AccessFlags.READONLY
    # else:
    #     flag = h5cpp.file.AccessFlags.READWRITE
    # if swmr:
    #     if readonly:
    #         if hasattr(h5cpp.file.AccessFlags, "SWMRREAD"):
    #             flag = flag | h5cpp.file.AccessFlags.SWMRREAD
    #     else:
    #         if hasattr(h5cpp.file.AccessFlags, "SWMRWRITE"):
    #             flag = flag | h5cpp.file.AccessFlags.SWMRWRITE

    # if libver is None or libver == 'lastest':
    #     fapl.library_version_bounds(
    #         h5cpp.property.LibVersion.LATEST,
    #         h5cpp.property.LibVersion.LATEST)
    # return RedisFile(h5cpp.file.open(filename, flag, fapl), filename)
    return RedisFile({"filename": filename, "readonly": readonly,
                      "libver": libver,
                      "swmr": swmr}, filename)


def is_image_file_supported():
    """ provides if loading of image files are supported

    :retruns: if loading of image files are supported
    :rtype: :obj:`bool`
    """
    return False


def is_vds_supported():
    """ provides if vds are supported

    :retruns: if vds are supported
    :rtype: :obj:`bool`
    """
    return True


def is_unlimited_vds_supported():
    """ provides if unlimited vds are supported

    :retruns: if unlimited vds are supported
    :rtype: :obj:`bool`
    """
    return True


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
    :rtype: :class:`H5PYFile`
    """
    if not is_image_file_supported():
        raise Exception(
            "Loading a file from a memory buffer not supported")


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
    :rtype: :class:`RedisFile`
    """
    fpars = {"filename": filename, "overwrite": overwrite}
    fpars.update(pars)
    return RedisFile(fpars, filename=filename, redisurl=redisurl,
                     session=session,
                     h5fileplugin=h5fileplugin)


def link(target, parent, name):
    """ create link

    :param target: nexus path name
    :type target: :obj:`str`
    :param parent: parent object
    :type parent: :class:`FTObject`
    :param name: link name
    :type name: :obj:`str`
    :returns: link object
    :rtype: :class:`RedisLink`
    """
    if ":/" in target:
        filename, path = target.split(":/")
    else:
        filename, path = None, target

    localfname = RedisLink.getfilename(parent)
    el = RedisLink({"target": target, "name": name, "file_path": filename,
                    "object_path": path, "localfname": localfname}, parent)
    return el


def get_links(parent):
    """ get links

    :param parent: parent object
    :type parent: :class:`FTObject`
    :returns: list of link objects
    :returns: link object
    :rtype: :obj: `list` <:class:`RedisLink`>
    """
    links = [ch() for ch in parent._tchildren
             if (hasattr(ch(), "name") and ch().name
                 and type(ch()).__name__
                 not in ["RedisAttribute"])]
    return links


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
    :rtype: :class:`RedisDataFilter`
    """
    dtf = RedisDataFilter()
    if filterid:
        dtf.filterid = filterid
    if name:
        dtf.name = name
    if shuffle:
        dtf.shuffle = shuffle
    if rate:
        dtf.rate = rate
    if options:
        dtf.options = options
    if availability:
        dtf.availability = availability
    return dtf


def deflate_filter(rate=None, shuffle=None, availability=None):
    """ create data filter

    :param rate: filter shuffle
    :type rate: :obj:`bool`
    :param shuffle: filter shuffle
    :type shuffle: :obj:`bool`
    :returns: deflate filter object
    :rtype: :class:`RedisDataFilter`
    """
    dtf = RedisDataFilter()
    dtf.filterid = 1
    dtf.name = "deflate"
    if shuffle:
        dtf.shuffle = shuffle
    dtf.rate = rate or 2
    if availability:
        dtf.availability = availability
    return dtf


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
    :rtype: :class:`RedisTargetFieldView`
    """
    return RedisTargetFieldView(
        filename, fieldpath, shape, dtype, maxshape)


def virtual_field_layout(shape, dtype, maxshape=None, parent=None):
    """ creates a virtual field layout for a VDS file

    :param shape: shape
    :type shape: :obj:`list` < :obj:`int` >
    :param dtype: attribute type
    :type dtype: :obj:`str`
    :param maxshape: shape
    :type maxshape: :obj:`list` < :obj:`int` >
    :returns: virtual layout
    :rtype: :class:`RedisVirtualFieldLayout`
    """
    if not is_vds_supported():
        raise Exception("VDS not supported")

    return RedisVirtualFieldLayout(
        None,
        # h5cpp.property.VirtualDataMaps(),
        shape, dtype, maxshape, parent)


class RedisFile(filewriter.FTFile):

    """ file tree file
    """

    #: (:obj:`dict`) global data stores
    global_data_stores = {}

    #: (:class:`threading.Lock`) global data store lock
    global_data_store_lock = threading.Lock()

    def __init__(self, h5object=None, filename=None,
                 redisurl=None, session=None, h5fileplugin=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param filename:  file name
        :type filename: :obj:`str`
        :param redisurl: redis url string
        :type redisurl: :obj:`str`
        :param session: redis session
        :type session: :obj:`str`
        :param h5fileplugin: use h5file_detector plugin
        :type h5fileplugin: :obj:`str`
        """
        filewriter.FTFile.__init__(self, h5object, filename)
        #: (:obj:`str`) object nexus path
        self.path = None
        #: (:obj:`str`) nexus file name
        h5object = h5object or {"filename": filename}
        self.filename = filename
        if "filename" in h5object:
            self.path = h5object["filename"]
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
        self._file_time = unicode(RedisFile.currenttime())
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

    def append_stream(self, name, stream):
        """ scan object

        :param name: stream name
        :type name: :obj:`str`
        :param scan: stream object
        :type scan: :class:`Stream`
        """
        with self.__scan_lock:
            self.__streams[name] = stream

    def acquisition_on_server(self, server_url):
        """ scan object

        :param server_url: server url
        :typeserver_url: :obj:`str`
        :returns: acquisition offset
        :rtype: :obj:`int`
        """
        if acquisition_on_server is not None:
            return acquisition_on_server(self.__datastore, server_url)

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
        :returns: device parameter value
        :rtype: :obj:`any`
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
        :returns: channel parameter value
        :rtype: :obj:`any`
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

        # localfname = RedisLink.getfilename(self.root())
        if "filename" in self._h5object:
            localfname = self._h5object["filename"]
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
            "reference_moveables": [],
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
        :returns: scan parameter value
        :rtype: :obj:`any`
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
            localfname = RedisLink.getfilename(self.root())
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

    def add_plot(self):
        """ build the scan_info ``plots`` descriptors for the scan kind

        A curve-plot (motor or time on x, one curve per counter) is created
        for every scan kind; mesh scans additionally get a scatter-plot.
        MCA/spectra channels get no explicit plot -- flint infers their
        1d-plot from the acquisition_chain. See :func:`redisutils.build_plots`.
        """
        result = build_plots(
            title=get_title(self.get_scaninfo(["title"])),
            channels=self.get_scaninfo(["channels"]),
            ref_moveables=self.get_scaninfo(["reference_moveables"]),
        )
        for chname, meta in result["channel_meta"].items():
            for key, value in meta.items():
                self.set_scaninfo(value, ["channels", chname, key])
        self.set_scaninfo(result["plots"], ["plots"])

    def start(self):
        """ start scan

        """
        if REDIS:
            devices = self.get_devices()
            for n, dd in devices.items():
                if "channels" in dd:
                    dd["channels"] = list(sorted(dd["channels"]))
            self.set_scaninfo(devices, ["devices"])
            channels = self.get_channels()
            acq_chain = build_acq_chain(
                devices,
                title=get_title(self.get_scaninfo(["title"])),
                channels=channels,
                ref_moveables=self.get_scaninfo(["reference_moveables"]),
            )
            self.set_scaninfo(acq_chain, ["acquisition_chain"])
            self.set_scaninfo(channels, ["channels"])

            self.add_plot()

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

            lpars = (self.get_scaninfo(["datadesc"]) or {})
            pars = (self.get_scaninfo(
                ["datadesc"], direct=True) or {})
            pars.update(lpars)
            self.set_scaninfo(pars, ["datadesc"])

            self.set_scaninfo(
                datetime.datetime.now().astimezone().isoformat(),
                ['end_time'], direct=True)
            end_reason = "SUCCESS"
            ereason = (self.get_scaninfo(["snapshot"]) or {}).get("end_reason")
            if isinstance(ereason, dict):
                ereason = ereason.get("value")
            if ereason:
                end_reason = str(ereason)
            self.set_scaninfo(end_reason, ['end_reason'], direct=True)
            # print("stop SCAN")
            self.scan_command("close")
            # print("close SCAN")
            # self.set_scan(None)
            #    print("SCAN None")

    def root(self):
        """ root object

        :returns: parent object
        :rtype: :class:`RedisGroup`
        """
        pars = {"name": ".", "NX_class": "NXroot",
                "file_name": self.filename,
                "file_time": self._file_time}
        # skip: file_update_time
        pars.update(self._h5object)
        return RedisGroup(pars, self, nxclass=pars["NX_class"])

    def flush(self):
        """ flash the data
        """
        pass

    def close(self):
        """ close file
        """
        filewriter.FTFile.close(self)

    @property
    def is_valid(self):
        """ check if file is valid

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        return True

    @property
    def readonly(self):
        """ check if file is readonly

        :returns: readonly flag
        :rtype: :obj:`bool`
        """
        if "readonly" in self._h5object:
            return self._h5object["readonly"]
        return False

    def reopen(self, readonly=False, swmr=False, libver=None):
        """ reopen file

        :param readonly: readonly flag
        :type readonly: :obj:`bool`
        :param swmr: swmr flag
        :type swmr: :obj:`bool`
        :param libver:  library version, default: 'latest'
        :type libver: :obj:`str`
        """
        self._h5object.update(
            {"readonly": readonly, "swmr": swmr, "libver": libver})
        filewriter.FTFile.reopen(self)


class RedisGroup(filewriter.FTGroup):

    """ file tree group
    """

    def __init__(self, h5object, tparent=None, nxclass=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param tparent: tree parent
        :type tparent: :obj:`FTObject`
        """
        self._ancache = set("NX_class")
        self._avcache_lock = threading.Lock()
        self._avcache = {}
        self._apcache = {}

        # print("CREATE GR", h5object)
        pars = {"NX_class": nxclass}
        attrs = {"name": "NX_class", "dtype": "string", "shape": tuple()}
        fattrs = None
        tattrs = None
        if "file_name" in h5object:
            fattrs = {"name": "file_name", "dtype": "string", "shape": tuple()}
            pars.update({"file_name":  h5object["file_name"]})
        if "file_time" in h5object:
            tattrs = {"name": "file_time", "dtype": "string", "shape": tuple()}
            pars.update({"file_time":  h5object["file_time"]})
        with self._avcache_lock:
            self._avcache.update(pars)
            self._apcache["NX_class"] = attrs
            if fattrs:
                self._apcache["file_name"] = fattrs
            if tattrs:
                self._apcache["file_time"] = tattrs
        pars.update(h5object)
        # print("CREATED GR", h5object, pars,)
        # if "attrs" in h5object:
        #     h5object["attrs"].update(attrs)
        # else:
        #     h5object["attrs"] = attrs

        filewriter.FTGroup.__init__(self, pars, tparent)

        self.__nxclass = nxclass
        #: (:obj:`str`) object nexus path
        self.path = u""
        #: (:obj:`str`) object name
        self.name = None

        if "name" in h5object:
            self.name = h5object["name"]
            if tparent and tparent.path:
                if hasattr(tparent, "root"):
                    if self.name == ".":
                        self.path = u"/"
                    else:
                        self.path = u"/" + self.name
                else:
                    if tparent.path.endswith("/"):
                        self.path = tparent.path
                    else:
                        self.path = tparent.path + u"/"
                    self.path += self.name
            if ":" not in self.name:
                # print("GROUP", type(self), self.name)
                if "NX_class" in h5object:
                    clss = filewriter.first(h5object["NX_class"])
                else:
                    clss = ""
                if clss:
                    if isinstance(clss, (list, np.ndarray)):
                        clss = clss[0]
                if clss and clss != 'NXroot':
                    self.path += u":" + str(clss)

    @property
    def size(self):
        """ a number of children

        :return: a number of children
        :rtype: :obj:`int`
        """
        return len([ch() for ch in self._tchildren
                    if (isinstance(ch(), RedisGroup)
                        or isinstance(ch(), RedisField)
                        or isinstance(ch(), RedisLink))])

    def set_attr_value(self, name, value):
        """ set device parameters

        :param name: attribute name
        :type name: :obj:`str`
        :param value: attribute value
        :type value: :obj:`any`
        """
        if name:
            with self._avcache_lock:
                self._avcache[name] = value
                self._ancache.add(name)
        # print("SET ATTR VALUE", self._avcache, self._h5object)

    def set_attr_prop(self, name, prop):
        """ set device parameters

        :param name: attribute name
        :type name: :obj:`str`
        :param prop: attribute prop
        :type prop: :obj:`any`
        """
        if name:
            with self._avcache_lock:
                self._apcache[name] = prop
                self._ancache.add(name)

    def get_attr_value(self, name):
        """ get scan info parameters

        :param name: attribute name
        :type name: :obj:`str`
        :returns: attribute value
        :rtype: :obj:`any`
        """
        # print("GET ATTR VALUE", self._avcache, self._h5object)
        if name:
            with self._avcache_lock:
                # print(self._avcache)
                vl = self._avcache.get(name, None)
            return vl

    def get_attr_prop(self, name):
        """ get scan info parameters

        :param name: attribute name
        :type name: :obj:`str`
        :returns: attribute prop
        :rtype: :obj:`any`
        """
        if name:
            with self._avcache_lock:
                # print(self._avcache)
                vl = self._apcache.get(name, None)
            return vl

    def get_attr_props(self):
        """ get attr props

        :returns: attribute properies
        :rtype: :obj:`dict`
        """
        with self._avcache_lock:
            vl = dict(self._apcache or {})
        return vl

    def get_attr_names(self):
        """ get scan info parameters

        :returns: attribute value
        :rtype: :obj:`any`
        """
        with self._avcache_lock:
            names = self._ancache
        return names

    def remove_attr_name(self, name):
        """ remove the attribute name

        :param name: attribute name
        :type name: :obj:`str`
        """
        if name:
            with self._avcache_lock:
                if self._ancache is not None and name in self._ancache:
                    self._ancache.pop(name)

    def add_attr_name(self, name):
        """ add the attribute name

        :param name: attribute name
        :type name: :obj:`str`
        """
        if name:
            with self._avcache_lock:
                if self._ancache is not None and name not in self._ancache:
                    self._ancache.add(name)

    def open(self, name):
        """ open a file tree element

        :param name: element name
        :type name: :obj:`str`
        :returns: file tree object
        :rtype: :class:`FTObject`
        """
        fch = None
        for ch in self._tchildren:
            nch = ch()
            if hasattr(nch, "name") and nch.name == name:
                fch = nch
                break
        return fch

    def open_link(self, name):
        """ open a file tree element as link

        :param name: element name
        :type name: :obj:`str`
        :returns: file tree object
        :rtype: :class:`FTObject`
        """
        obj = self.open(name)
        pars = dict(obj.h5object)
        pars["name"] = name
        return RedisLink(pars, self)
        # raise Exception("RedisGourp.open_link not supported")

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

    def acquisition_on_server(self, server_url):
        """ scan object

        :param server_url: server url
        :typeserver_url: :obj:`str`
        :returns: acquisition offset
        :rtype: :obj:`int`
        """
        if hasattr(self._tparent, "acquisition_on_server"):
            return self._tparent.acquisition_on_server(server_url)

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
        :returns: device parameter value
        :rtype: :obj:`any`
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
        :returns: device parameter value
        :rtype: :obj:`any`
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
        :returns: scan parameter value
        :rtype: :obj:`any`
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
        :rtype: :class:`RedisGroup`
        """
        # gr = h5cpp.node.Group(None, n)
        # if nxclass is not None:
        #     gr.attributes.create(
        #         "NX_class", pTh["unicode"]).write(unicode(nxclass))
        if REDIS and nxclass in ["NXinstrument", u'NXinstrument']:
            self.set_insname(n)
        if REDIS and nxclass in ["NXentry", u'NXentry']:
            self.reset_scaninfo(n)
        gr = RedisGroup({"name": n, "NX_class": nxclass},
                        self, nxclass=nxclass)

        # print("CREATE__GROUP", "NX_class", nxclass, n)
        # self.set_attr_value("NX_class", nxclass)
        # print("CREATE2__GROUP", "NX_class", nxclass, n)
        return gr

    def create_virtual_field(self, name, layout, fillvalue=0):
        """ creates a virtual filed tres element

        :param name: field name
        :type name: :obj:`str`
        :param layout: virual field layout
        :type layout: :class:`RedisFieldLayout`
        :param fillvalue:  fill value
        :type fillvalue: :obj:`int` or :class:`np.ndarray`
        """
        if not is_vds_supported():
            raise Exception("VDS not supported")
        # shape = layout["shape"] if "shape" in layout else [1]
        shape = layout.shape or [1]
        dataspace = {"class": "Simple",
                     "shape": tuple(shape),
                     "maxshape": tuple([UNLIMITED] * len(shape))}
        vf = {"class": "VirtualDataset",
              "h5object": self._h5object,
              "name": name,
              "dtype": _tostr(layout.dtype),
              "dataspace": dataspace,
              "layout": dict(layout.h5object or {}),
              "fillvalue": fillvalue,
              # skip: dcpl
              }
        return RedisField(vf, self)

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
        :type dfilter: :class:`RedisDataFilter`
        :returns: file tree field
        :rtype: :class:`RedisField`
        """

        shape = tuple(shape) if shape else tuple()
        # dataspace = {"class": "Simple",
        #              "shape": shape,
        #              "maxshape": tuple([UNLIMITED] * len(shape or []))}
        # vf = {"class": "VirtualDataset",
        #       "h5object": self._h5object,
        #       "name": name,
        #       "dtype": (type_code or "float"),
        #       "dataspace": dataspace,
        #       "layout": {},
        #       # skip: dcpl
        #       }
        # return RedisField(vf, self)

        # print("CREATE", name, type_code, shape, chunk)
        if type_code in ["str", "unicode", "string"] and \
           not shape and not chunk:
            dataspace = {"class": "Scalar"}
            fl = {"class": "Dataset",
                  "h5object": self._h5object,
                  "name": name,
                  "dtype": str(type_code or "float"),
                  "dataspace": dataspace,
                  # skip: dcpl
                  }
            return RedisField(fl, self)
        else:
            shape = shape or [1]
            dataspace = {"class": "Simple",
                         "shape": tuple(shape),
                         "maxshape": tuple([UNLIMITED] * len(shape))}
            if chunk is None and shape is not None:
                chunk = [(dm if dm != 0 else 1) for dm in shape]
            layout = {"type": "CHUNKED"}
            fl = {"class": "Dataset",
                  "h5object": self._h5object,
                  "name": name,
                  "layout": layout,
                  "dtype": str(type_code or "float"),
                  "dataspace": dataspace,
                  # skip: dcpl
                  }
            # TODO
            # if dfilter:
            #     fl["dfilter"] = dict(dfilter)
            return RedisField(fl, self)

    @property
    def attributes(self):
        """ return the attribute manager

        :returns: attribute manager
        :rtype: :class:`RedisAttributeManager`
        """
        return RedisAttributeManager({}, self)

    def close(self):
        """ close group
        """
        filewriter.FTGroup.close(self)

    def reopen(self):
        """ reopen group
        """
        filewriter.FTGroup.reopen(self)

    def exists(self, name):
        """ if child exists

        :param name: child name
        :type name: :obj:`str`
        :returns: existing flag
        :rtype: :obj:`bool`
        """
        return name in self.names()

    def names(self):
        """ read the child names

        :returns: h5 object
        :rtype: :obj:`list` <`str`>
        """
        return [ch().name for ch in self._tchildren
                if (hasattr(ch(), "name") and ch().name
                    and type(ch()).__name__
                    not in ["RedisAttribute"])]

    class RedisGroupIter(object):

        def __init__(self, group):
            """ constructor

            :param group: group object
            :type manager: :obj:`RedisGroup`
            """

            # raise Exception("RedisGroupUIter.__init__ not supported")
            self.__group = group
            self.__names = group.names()

        def __next__(self):
            """ the next attribute

            :returns: attribute object
            :rtype: :class:`FTAtribute`
            """
            # raise Exception("RedisGroupIter.__next__ not supported")
            if self.__names:
                return self.__group.open(self.__names.pop(0))
            else:
                raise StopIteration()

        next = __next__

        def __iter__(self):
            """ attribute iterator

            :returns: attribute iterator
            :rtype: :class:`RedisAttrIter`
            """
            # raise Exception("RedisGroupIter.__iter__ not supported")
            return self

    def __iter__(self):
        """ attribute iterator

        :returns: attribute iterator
        :rtype: :class:`RedisAttrIter`
        """
        # raise Exception("RedisGroup.__iter__ not supported")
        return self.RedisGroupIter(self)

    @property
    def is_valid(self):
        """ check if field is valid

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        return True


class RedisField(filewriter.FTField):

    """ file tree file
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param tparent: tree parent
        :type tparent: :obj:`FTObject`
        """
        self._ancache = None
        self._avcache_lock = threading.Lock()
        self._avcache = {}
        self._apcache = {}
        filewriter.FTField.__init__(self, h5object, tparent)
        #: (:obj:`str`) object nexus path
        self.path = ''
        #: (:obj:`str`) object name
        self.name = None
        self.__dsname = None
        self.__stream = None
        self.__jstream = None
        self.__rstream = None
        self.__rcounter = 0
        if "name" in h5object:
            self.name = h5object["name"]
            if tparent and tparent.path:
                if tparent.path == "/":
                    self.path = "/" + self.name
                else:
                    self.path = tparent.path + "/" + self.name
        #: (:obj:`bool`) bool flag
        # self.boolflag = False

    def get_attrs(self):
        """ get scan info parameters

        :param name: attribute name
        :type name: :obj:`str`
        :returns: attribute value
        :rtype: :obj:`any`
        """
        with self._avcache_lock:
            vl = dict(self._avcache)
        return vl

    def append_stream(self, name, stream):
        """ scan object

        :param name: stream name
        :type name: :obj:`str`
        :param scan: stream object
        :type scan: :class:`Stream`
        """
        if hasattr(self._tparent, "append_stream"):
            return self._tparent.append_stream(name, stream)

    def acquisition_on_server(self, server_url):
        """ scan object

        :param server_url: server url
        :typeserver_url: :obj:`str`
        :returns: acquisition offset
        :rtype: :obj:`int`
        """
        if hasattr(self._tparent, "acquisition_on_server"):
            return self._tparent.acquisition_on_server(server_url)

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
        :returns: device parameter value
        :rtype: :obj:`any`
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
        :returns: device parameter value
        :rtype: :obj:`any`
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
        :returns: scan parameter value
        :rtype: :obj:`any`
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

    def set_attr_value(self, name, value):
        """ set device parameters

        :param name: attribute name
        :type name: :obj:`str`
        :param value: attribute value
        :type value: :obj:`any`
        """
        if name:
            with self._avcache_lock:
                self._avcache[name] = value
                if self._ancache is None:
                    self._ancache = set(self._avcache.keys())
                self._ancache.add(name)

    def set_attr_prop(self, name, prop):
        """ set attribute properies

        :param name: attribute name
        :type name: :obj:`str`
        :param prop: attribute prop
        :type prop: :obj:`any`
        """
        if name:
            with self._avcache_lock:
                self._apcache[name] = prop
                if self._ancache is None:
                    self._ancache = set(self._apcache.keys())
                self._ancache.add(name)

    def get_attr_names(self):
        """ get scan info parameters

        :returns: attribute value
        :rtype: :obj:`any`
        """
        with self._avcache_lock:
            ancache = self._ancache
        if ancache is not None:
            names = self._ancache
        else:
            names = list(nm for nm in self._avcache.keys() if nm)
            names2 = list(nm for nm in self._apcache.keys() if nm)
            with self._avcache_lock:
                self._ancache = set(names)
                self._ancache.update(names2)
        return names

    def remove_attr_name(self, name):
        """ remove the attribute

        :param name: attribute name
        :type name: :obj:`str`
        """
        with self._avcache_lock:
            if self._ancache is not None and name in self._ancache:
                self._ancache.pop()

    def add_attr_name(self, name):
        """ add the attribute name

        :param name: attribute name
        :type name: :obj:`str`
        """
        if name:
            with self._avcache_lock:
                if self._ancache is not None and name not in self._ancache:
                    self._ancache.add(name)

    def get_attr_value(self, name):
        """ get scan info parameters

        :param name: attribute name
        :type name: :obj:`str`
        :returns: attribute value
        :rtype: :obj:`any`
        """
        with self._avcache_lock:
            vl = self._avcache.get(name, None)
        return vl

    def get_attr_prop(self, name):
        """ get scan info parameters

        :param name: attribute name
        :type name: :obj:`str`
        :returns prop: attribute prop
        :rtype prop: :obj:`any`
        """
        with self._avcache_lock:
            vl = self._apcache.get(name, None)
        return vl

    def get_attr_props(self):
        """ get attr props

        :returns: attribute properies
        :rtype: :obj:`dict`
        """
        with self._avcache_lock:
            vl = dict(self._apcache or {})
        return vl

    @property
    def attributes(self):
        """ return the attribute manager

        :returns: attribute manager
        :rtype: :class:`RedisAttributeManager`
        """
        return RedisAttributeManager({}, self)

    def __set_step_channel_info(self, dsname, units, shape, strategy="STEP",
                                o=None, av=None):
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
        av = av or {}
        attrs = self.attributes
        sds = {
            "name": dsname,
            "label": dsname,
            "shape": shape,
            "strategy": strategy,
            "dtype": self.dtype
        }
        if o is not None:
            if str(type(o).__name__) == "int":
                sds["dtype"] = "int64"
            elif str(type(o).__name__) == "float":
                sds["dtype"] = "float64"

        anames = attrs._names()
        for key, vl in attrdesc.items():
            if vl[0] in anames:
                avl = av[vl[0]] if vl[0] in av.keys() else attrs[vl[0]].read()
                sds[key] = vl[1](filewriter.first(avl))
        sds["nexus_path"] = self.path
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
                    sds["stream"] = "stream"
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
                    sds["stream"] = "h5file_detector"
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
                sds["stream"] = "stream"
        except RuntimeError as e:
            if "already exists" in str(e):
                print(str(e))
            else:
                raise
        pars = (self.get_scaninfo(["datadesc"]) or {}).keys()
        dsn = dsname
        while dsn in pars:
            dsn = dsn + "_"
        sds["name"] = dsn
        self.set_scaninfo(sds, ["datadesc", dsn])

    def __set_init_channel_info(self, dsname, units, shape, strategy, o, av):
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
            "shape": shape,
            "strategy": strategy,
            "dtype": self.dtype
        }

        anames = attrs._names()
        for key, vl in attrdesc.items():
            if vl[0] in anames:
                avl = av[vl[0]] if vl[0] in av.keys() else attrs[vl[0]].read()
                ids[key] = vl[1](filewriter.first(avl))
        ids["nexus_path"] = self.path
        pars = (self.get_scaninfo(["snapshot"]) or {}).keys()
        dsn = dsname
        while dsn in pars:
            dsn = dsn + "_"
        self.set_scaninfo(ids, ["snapshot", dsn])
        if self.name in ["program_name"]:
            for key, vl in progattrdesc.items():
                np = ""
                try:
                    np = progattr(vl, anames, attrs)
                    if vl[2] or np:
                        self.set_scaninfo(np, [key])
                except Exception as e:
                    print(str(e))
                    pass

    def __set_channel_info(self, o):
        """ set channel value

        :param o: object value to write
        :type o: :obj:`any`
        """
        attrs = self.attributes
        av = self.get_attrs()
        strategy = av.get("nexdatas_strategy", None)
        if strategy is None:
            strategy = attrs["nexdatas_strategy"].read()
        strategy = filewriter.first(strategy)
        dsname = "%s_%s" % (self._tparent.name, self.name)
        dsnm = ""
        dsnm = av.get("nexdatas_source", None)
        if dsnm is None and "nexdatas_source" in attrs._names():
            #     dsnm = self.get_attr_value("nexdatas_source")
            #     if dsnm is None:
            dsnm = attrs["nexdatas_source"].read()
        if dsnm is not None:
            dsnm = getdsname(filewriter.first(dsnm))
            dsname = dsnm
        units = av.get("units", None)
        if units is None:
            if "units" in attrs._names():
                units = attrs["units"].read()
                # print("READ UNIT", units)
        if units is not None:
            units = filewriter.first(units)
        else:
            units = ""
        self.__dsname = dsname
        shape = []
        if hasattr(o, "shape"):
            shape = o.shape
        elif isinstance(o, list) and len(o) > 1:
            shape = [len(o)]
            if isinstance(o[0], list):
                shape.append(len(o[0]))
        # print("SETITEM", self, self.name, self.shape,
        #       self.attributes.names(),
        #        self.__dsname, strategy, self.dtype,
        #       type(o), str(t), units)
        if strategy in ["STEP"] and dsnm:
            # skip 2D images
            if not shape or len(shape) < 2 or FileStream is not None:
                self.__set_step_channel_info(
                    dsname, units, shape, strategy, o, av)
        else:
            self.__set_init_channel_info(dsname, units, shape, strategy, o, av)

    def __setitem__(self, t, o):
        """ set value

        :param t: slice tuple
        :type t: :obj:`tuple`
        :param o: h5 object
        :type o: :obj:`any`
        """
        if REDIS:
            if self.__dsname is None and \
               "nexdatas_strategy" in self.attributes._names():
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
        if isinstance(o, list):
            o = np.array(o)
        if self.shape == (1,) and t == 0:
            self._h5object["value"] = o
        elif self.size > MAXSIZE:
            self._h5object["value"] = None
        elif t is Ellipsis or t is tuple():
            self._h5object["value"] = o
        else:
            sslice = _selection2slice(t, self.shape)
            if sslice is None:
                self._h5object["value"] = o
            else:
                if self.dtype in ['string', b'string']:
                    var = self._h5object["value"]
                    var = np.array(var, dtype="object")
                    var[sslice] = np.array(o, dtype="object")
                    # var = var.astype(dtype)
                    self._h5object["value"] = var
                else:
                    if "value" in self._h5object:
                        try:
                            self._h5object["value"][sslice] = o
                        except Exception:
                            self._h5object["value"] = o
                    else:
                        self._h5object["value"] = o

    def close(self):
        """ close field
        """
        filewriter.FTField.close(self)

    def reopen(self):
        """ reopen field
        """
        filewriter.FTField.reopen(self)

    def refresh(self):
        """ refresh the field

        :returns: refreshed
        :rtype: :obj:`bool`
        """
        return True

    def grow(self, dim=0, ext=1):
        """ grow the field

        :param dim: growing dimension
        :type dim: :obj:`int`
        :param dim: size of the grow
        :type dim: :obj:`int`
        """
        shape = None
        if "shape" in self._h5object:
            shape = list(self._h5object["shape"])
            if dim < len(shape):
                shape[dim] += ext
                self._h5object["shape"] = tuple(shape)
        if "dataspace" in self._h5object:
            dtspace = self._h5object["dataspace"]
            if "shape" in dtspace:
                shape = list(dtspace["shape"])
                if dim < len(shape):
                    shape[dim] += ext
                    dtspace["shape"] = tuple(shape)
        if "value" in self._h5object:
            if self.size > MAXSIZE:
                self._h5object["value"] = None
            if shape:
                if isinstance(self._h5object["value"], list):
                    self._h5object["value"] = np.array(self._h5object["value"])
                elif not isinstance(self._h5object["value"], np.ndarray):
                    self._h5object["value"] = np.array(
                        [self._h5object["value"]])
                if isinstance(self._h5object["value"], np.ndarray):
                    val = self._h5object["value"]
                    self._h5object["value"] = \
                        np.zeros(shape=shape, dtype=val.dtype)
                    slices = tuple([slice(None, dim, None)
                                    for dim in val.shape])
                    try:
                        self._h5object["value"][slices] = val
                    except Exception:
                        self._h5object["value"] = val

    def read(self):
        """ read the field value

        :returns: h5 object
        :rtype: :obj:`any`
        """
        if "value" in self._h5object:
            if isinstance(self._h5object["value"], list):
                return list(self._h5object["value"])
            return self._h5object["value"]
        return None

    def write(self, o):
        """ write the field value

        :param o: h5 object
        :type o: :obj:`any`
        """
        self[...] = o

    def __getitem__(self, t):
        """ get value

        :param t: slice tuple
        :type t: :obj:`tuple`
        :returns: h5 object
        :rtype: :obj:`any`
        """
        # print("GET", self.name, self.shape, t)
        if self.shape == (1,) and t == 0:
            if self.dtype in ['string', b'string']:
                # workaround for bug: h5cpp #355
                if self.size == 0:
                    if self.shape:
                        v = np.empty(shape=self.shape, dtype=self.dtype)
                    else:
                        v = []
                else:
                    if "value" in self._h5object:
                        return self._h5object["value"]

            else:
                if "value" in self._h5object:
                    return self._h5object["value"]

        if self.size > MAXSIZE:
            return None
        sslice = _selection2slice(t, self.shape)
        # print("SEL", sslice, t, self.shape)
        if sslice in [None, tuple(), Ellipsis]:
            if self.dtype in ['string', b'string']:
                # workaround for bug: h5cpp #355
                if self.size == 0:
                    if self.shape:
                        v = np.empty(shape=self.shape, dtype=self.dtype)
                    else:
                        v = []
                else:
                    if "value" in self._h5object:
                        return self._h5object["value"]
                try:
                    v = v.decode('UTF-8')
                except Exception:
                    pass
            else:
                if "value" in self._h5object:
                    return self._h5object["value"]
            return v
        v = self._h5object["value"] \
            if "value" in self._h5object else None
        if isinstance(v, list):
            v = np.array(v)
        v = v[sslice]
        # if hasattr(v, "shape") and hasattr(v, "reshape"):
        #     shape = [sh for sh in v.shape if sh != 1]
        #     if shape != list(v.shape):
        #         v.reshape(shape)

        # print("VAL", v)
        if hasattr(v, "shape"):
            shape = v.shape
            if len(shape) == 3 and shape[2] == 1:
                #: problem with old numpy
                # v.reshape(shape[:2])
                v = v[:, :, 0]
                shape = v.shape
            if len(shape) == 3 and shape[1] == 1:
                # v.reshape([shape[0], shape[2]])
                v = v[:, 0, :]
                shape = v.shape
            if len(shape) == 3 and shape[0] == 1:
                # v.reshape([shape[1], shape[2]])
                v = v[0, :, :]
                shape = v.shape
            if len(shape) == 2 and shape[1] == 1:
                # v.reshape([shape[0]]]
                v = v[0, :]
                shape = v.shape
            if len(shape) == 2 and shape[0] == 1:
                # v.reshape([shape[1]])
                v = v[:, 0]
                shape = v.shape
            if len(shape) == 1 and shape[0] == 1:
                v = v[0]
        # print("VAL2", v)
        if self.dtype in ['string', b'string']:
            try:
                v = v.decode('UTF-8')
            except Exception:
                pass
        return v

    @property
    def is_valid(self):
        """ check if field is valid

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        return True

    @property
    def dtype(self):
        """ field data type

        :returns: field data type
        :rtype: :obj:`str`
        """
        if "dtype" in self.h5object:
            return self._h5object["dtype"]
        return "float"

    @property
    def shape(self):
        """ field shape

        :returns: field shape
        :rtype: :obj:`list` < :obj:`int` >
        """
        # print(self._h5object)
        if "dataspace" in self._h5object \
                and "shape" in self._h5object["dataspace"]:
            return tuple(self._h5object["dataspace"]["shape"])
        if "shape" in self._h5object:
            return tuple(self._h5object["shape"])
        return tuple()

    @property
    def size(self):
        """ field size

        :returns: field size
        :rtype: :obj:`int`
        """
        if "dataspace" in self._h5object:
            dataspace = self._h5object["dataspace"]
            if "shape" in dataspace:
                try:
                    return math.prod(dataspace["shape"])
                except Exception:
                    pass
        return 1


class RedisLink(filewriter.FTLink):

    """ file tree link
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param tparent: tree parent
        :type tparent: :obj:`FTObject`
        """
        self._avcache_lock = threading.Lock()
        self._avcache = {}
        self._apcache = {}
        self._ancache = None
        filewriter.FTLink.__init__(self, h5object, tparent)
        #: (:obj:`str`) object nexus path
        self.path = ''
        #: (:obj:`str`) object name
        self.name = h5object["name"] if "name" in h5object else None
        if tparent and tparent.path:
            self.path = tparent.path
        if not self.path.endswith("/"):
            self.path += "/"
        #    self.name = h5object.path.name
        self.path += self.name

    def set_attr_value(self, name, value):
        """ set device parameters

        :param name: attribute name
        :type name: :obj:`str`
        :param value: attribute value
        :type value: :obj:`any`
        """
        if name:
            with self._avcache_lock:
                self._avcache[name] = value
                if self._ancache is None:
                    self._ancache = set(self._avcache.keys())
                self._ancache.add(name)

    def set_attr_prop(self, name, prop):
        """ set device parameters

        :param name: attribute name
        :type name: :obj:`str`
        :param prop: attribute prop
        :type prop: :obj:`any`
        """
        if name:
            with self._avcache_lock:
                self._apcache[name] = prop
                if self._ancache is None:
                    self._ancache = set(self._apcache.keys())
                self._ancache.add(name)

    def get_attr_names(self):
        """ get scan info parameters

        :returns: attribute value
        :rtype: :obj:`any`
        """
        with self._avcache_lock:
            ancache = self._ancache
        if ancache is not None:
            names = self._ancache
        else:
            names = list(nm for nm in self._avcache.keys() if nm)
            names2 = list(nm for nm in self._apcache.keys() if nm)
            with self._avcache_lock:
                self._ancache = set(names)
                self._ancache.update(names2)
        return names

    def get_attr_value(self, name):
        """ get scan info parameters

        :param name: attribute name
        :type name: :obj:`str`
        :returns: attribute value
        :rtype: :obj:`any`
        """
        if name:
            with self._avcache_lock:
                vl = self._avcache.get(name, None)
            return vl

    def get_attr_prop(self, name):
        """ get scan info parameters

        :param name: attribute name
        :type name: :obj:`str`
        :returns prop: attribute prop
        :rtype prop: :obj:`any`
        """
        if name:
            with self._avcache_lock:
                vl = self._apcache.get(name, None)
            return vl

    def get_attr_props(self):
        """ get attr props

        :returns: attribute properies
        :rtype: :obj:`dict`
        """
        with self._avcache_lock:
            vl = dict(self._apcache or {})
        return vl

    def add_attr_name(self, name):
        """ add the attribute name

        :param name: attribute name
        :type name: :obj:`str`
        """
        if name:
            with self._avcache_lock:
                if self._ancache is not None and name not in self._ancache:
                    self._ancache.add(name)

    def remove_attr_name(self, name):
        """ remove the attribute

        :param name: attribute name
        :type name: :obj:`str`
        """
        with self._avcache_lock:
            if self._ancache is not None and name in self._ancache:
                self._ancache.pop()
        if hasattr(self._tparent, "remove_attr_name"):
            self._tparent.remove_attr_name(name)

    @property
    def is_valid(self):
        """ check if link is valid

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        return True

    def refresh(self):
        """ refresh the field

        :returns: refreshed
        :rtype: :obj:`bool`
        """
        return True

    @classmethod
    def getfilename(cls, obj):
        """ provides a filename from h5 node

        :param obj: h5 node
        :type obj: :class:`FTObject`
        :returns: file name
        :rtype: :obj:`str`
        """
        filename = ""
        while not filename:
            par = obj.parent
            if par is None:
                break
            if hasattr(par, "filename"):
                filename = par.filename
                break
            else:
                obj = par
        return filename

    @property
    def target_path(self):
        """ target path

        :returns: target path
        :rtype: :obj:`str`
        """
        fpath = ""
        opath = ""
        if "target" in self._h5object:
            if ":/" in self._h5object["target"]:
                return self._h5object["target"]
            else:
                opath = self._h5object["target"]
        if "file_path" in self._h5object:
            fpath = self._h5object["file_path"]
        if "object_path" in self._h5object:
            opath = self._h5object["object_path"]
        if not fpath:
            fpath = self.getfilename(self)
        if not opath:
            return "%s:/" % fpath
        return "%s:/%s" % (fpath, opath)

    def reopen(self):
        """ reopen field
        """
        filewriter.FTLink.reopen(self)

    def close(self):
        """ close group
        """
        filewriter.FTLink.close(self)
        # self._h5object = None


class RedisDataFilter(filewriter.FTDataFilter):

    """ file tree deflate
    """
    def __init__(self, h5object=None, tparent=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        """
        h5object = h5object or {}
        filewriter.FTDataFilter.__init__(self, h5object, tparent)
        for ap in ["shuffle", "rate", "filterid",
                   "options", "name", "availability"]:
            if ap in h5object.keys():
                setattr(self, ap, h5object[ap])


class RedisVirtualFieldLayout(filewriter.FTVirtualFieldLayout):

    """ virtual field layout """

    def __init__(self, h5object, shape, dtype=None, maxshape=None,
                 tparent=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param shape: shape
        :type shape: :obj:`list` < :obj:`int` >
        :param dtype: attribute type
        :type dtype: :obj:`str`
        :param maxshape: shape
        :type maxshape: :obj:`list` < :obj:`int` >
        """
        h5object = h5object or {"shape": (shape or tuple()), "dtype": dtype,
                                "maxshape": maxshape}
        filewriter.FTVirtualFieldLayout.__init__(self, h5object, tparent)
        #: (:obj:`list` < :obj:`int` >) shape
        self.shape = shape
        # : (:obj:`str`): data type
        self.dtype = dtype
        # : (:obj:`str`): datasource name
        self.dsname = None
        #: (:obj:`list` < :obj:`int` >) maximal shape
        self.maxshape = maxshape
        #: (:obj:`list` <:obj:`dict` >) vmap list
        self.__vmaps = []
        self.__rstream = None
        self.__rcounter = 0

    def append_vmap(self, vmap, strategy=None):
        """ appends virtual map description into vmap list

        :param vmap: virtual map description
        :type vmap: :obj:`dict`
        :param strategy: datasource strategy i.e. INIT or FINAL
        :type strategy: :obj:`str`
        """
        vkeys = [ky for ky in vmap.keys()
                 if not ky.startswith("plugin")] if vmap else []
        if vkeys:
            self.__vmaps.append(vmap)
        if "dsname" in vmap:
            self.dsname = vmap["dsname"]
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
                    if "acquisition_offset" in plugin_def and \
                            not plugin_def["acquisition_offset"]:
                        if "server_url" in plugin_def and \
                                plugin_def["server_url"]:
                            acq_off = self.acquisition_on_server(
                                plugin_def["server_url"])
                            if acq_off is not None:
                                plugin_def["acquisition_offset"] = acq_off
                except Exception as e:
                    print("Cannot read acquisition_on_server for",
                          vmap, str(e))
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
                shape = plugin_def["shape"]
                sds = {
                    "name": dsname,
                    "label": dsname,
                    "strategy": strategy,
                    "shape": shape,
                    "stream": vmap["plugin"],
                    "dtype": plugin_def["dtype"]
                }

                self.fieldname = self.fieldname or "data"
                sds["nexus_path"] = "%s/%s" % (
                    self._tparent.path, self.fieldname)
                self.set_scaninfo(sds, ["datadesc", dsname])
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

    def acquisition_on_server(self, server_url):
        """ scan object

        :param server_url: server url
        :typeserver_url: :obj:`str`
        :returns: acquisition offset
        :rtype: :obj:`int`
        """
        if hasattr(self._tparent, "acquisition_on_server"):
            return self._tparent.acquisition_on_server(server_url)

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

    def set_scaninfo(self, value, keys=None, direct=False):
        """ set scan info parameters

        :param value: scan parameter value
        :type value: :obj:`any`
        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "set_scaninfo"):
            return self._tparent.set_scaninfo(value, keys, direct)

    def get_scaninfo(self, keys=None, direct=False):
        """ get scan info parameters

        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        :returns: scan parameter value
        :rtype: :obj:`any`
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

    @classmethod
    def cure_keys(cls, key):
        """ cure keys

        :param key: field key
        :type key: :class:`FTHyperslab` or :obj:`tuple` or :obj:`list`
        :  or :obj:`int`
        :returns: field key
        :rtype: :class:`FTHyperslab` or :obj:`tuple`
        """
        tkey = []
        if isinstance(key, list):
            try:
                sk = list(set([len(ky) for ky in key]))
            except Exception:
                sk = []
            if len(sk) == 1 and sk[0] == 4:
                offset, block, count, stride = map(list, zip(*key))
                return filewriter.FTHyperslab(offset, block, count, stride)
            for ky in key:
                if isinstance(ky, list) and len(ky) > 0 and len(ky) < 4:
                    tkey.append(slice(*ky))
                else:
                    if ky is None:
                        ky = slice(None)
                    tkey.append(ky)

            return tuple(tkey)
        return key

    @classmethod
    def cure_shape(cls, vmaps, shape):
        """ cure shape from virtual map elements

        :param vmaps: list of virtual map description
        :type vmaps: :obj:`list`<:obj:`dict`>
        :param shape: field shape
        :type shape: :obj:`list` < :obj:`int` >
        :returns: field shape
        :rtype: :obj:`list` < :obj:`int` >
        """
        # print("vmaps", vmaps, shape)
        if shape is None:
            return shape
        sizes = [(sh if sh > 1 else 0) for sh in shape]
        for vmap in vmaps:
            if "key" in vmap:
                key = vmap["key"]
                try:
                    sk = list(set([len(ky) for ky in key]))
                except Exception:
                    sk = []
                if len(sk) == 1 and sk[0] == 4:
                    offset, block, count, stride = map(list, zip(*key))
                    for si, sh in enumerate(shape):
                        if sh < 2:
                            if block[si] != unlimited() \
                                    and count[si] != unlimited() \
                                    and count[si] and block[si] and stride[si]:
                                sizes[si] = max(
                                    sizes[si],
                                    offset[si] + stride[si] * [count[si] - 1]
                                    + block[si])
                            else:
                                sizes[si] = max(
                                    sizes[si], 1)
                else:
                    eshape = vmap["shape"] if "shape" in vmap else []

                    for si, sh in enumerate(shape):
                        if sh < 2:
                            if isinstance(key, list) and len(key) > si \
                                    and isinstance(key[si], list) \
                                    and len(key[si]) > 0 and len(key[si]) < 4:
                                sky = slice(*key[si])
                                if sky.stop != unlimited():
                                    start = sky.start or 0
                                    stop = sky.stop or 0
                                    step = sky.step or 1
                                    size = (step * ((stop - start - 1) // step)
                                            + start) + 1
                                    sizes[si] = max(sizes[si], size)
                                else:
                                    sizes[si] = max(
                                        sizes[si],
                                        eshape[si]
                                        if len(eshape) > si else 1, 1)
                            else:
                                if si:
                                    sizes[si] = max(
                                        sizes[si],
                                        eshape[si]
                                        if len(eshape) > si else 1, 1)
                                else:
                                    sizes[si] += max(
                                        eshape[si]
                                        if len(eshape) > si else 1, 1)
            else:
                eshape = vmap["shape"] if "shape" in vmap else []
                for si, sh in enumerate(shape):
                    if sh < 2:
                        if si:
                            sizes[si] = max(
                                sizes[si],
                                eshape[si] if len(eshape) > si else 1, 1)
                        else:
                            sizes[si] += max(
                                eshape[si] if len(eshape) > si else 1, 1)
        return sizes

    def process_target_field_views(self, parent=None):
        """ process target fields views to virtual field layout

        :param parent: tree parent
        :type parent: :obj:`FTObject`
        """
        if self.__vmaps is not None:
            # print("SHAPE1", shape)
            self.shape = self.cure_shape(self.__vmaps, self.shape)
        # print("SHAPE12", shape)
        counter = 0
        plugin = False
        for vmap in self.__vmaps:
            if "plugin" in vmap and vmap["plugin"] in PLUGINS.keys():
                plugin = True
            edtype = vmap["dtype"] \
                if "dtype" in vmap else self.dtype
            key = vmap["key"] if "key" in vmap else counter
            key = self.cure_keys(key)
            if "shape" in vmap:
                eshape = vmap["shape"]
            elif isinstance(key, int):
                eshape = list(self.shape)
                eshape[0] = 1
            else:
                eshape = [0] * len(self.shape)

            fieldpath = vmap["fieldpath"] \
                if "fieldpath" in vmap else "/data"
            filename = vmap["filename"] if "filename" in vmap else None
            if "target" in vmap:
                target = vmap["target"]
                if target.startswith("h5file:/"):
                    target = target[8:]
                if "::" in target:
                    filename, fieldpath = target.split("::")
                elif ":/" in target:
                    filename, fieldpath = target.split(":/")
                else:
                    fieldpath = target
            if self._tparent is None and parent is not None:
                self._tparent = parent
            obj = self._tparent
            while filename is None:
                par = obj.parent
                if par is None:
                    break
                if hasattr(par, "root") and hasattr(par, "name"):
                    filename = par.name
                    break
                else:
                    obj = par
            sourceshape = vmap["sourceshape"] \
                if "sourceshape" in vmap else None
            sourcekey = vmap["sourcekey"] \
                if "sourcekey" in vmap else None
            sourcekey = self.cure_keys(sourcekey)
            if not any(eshape):
                eshape = self.find_shape(key, eshape, change_unlimited=False)
            ef = target_field_view(
                filename, fieldpath, eshape, edtype)
            if eshape:
                counter += eshape[0]
            else:
                counter += 1
            # print("KEY", key, sourcekey, sourceshape, eshape)
            self.add(key, ef, sourcekey, sourceshape)
        if self.dsname:
            self.set_scaninfo(
                self.shape, ["datadesc", self.dsname, "__vmaps_shape__"])
            if not plugin:
                self.set_scaninfo(
                    self.dtype, ["datadesc", self.dsname, "dtype"])
                self.set_scaninfo(
                    self.shape, ["datadesc", self.dsname, "shape"])
                self.set_scaninfo(
                    self.dsname, ["datadesc", self.dsname, "name"])
                self.set_scaninfo(
                    self.dsname, ["datadesc", self.dsname, "label"])
                nexus_path = "%s/%s" % (self._tparent.path, self.fieldname)
                self.set_scaninfo(
                    nexus_path, ["datadesc", self.dsname, "nexus_path"])

    @classmethod
    def find_shape(cls, key, eshape=None, change_unlimited=True):
        """ find a layout shape from elemnt keys and shape

        :param key: field key
        :type key: :class:`FTHyperslab` o :obj:`tuple`
        :param eshape: element shape
        :type eshape: ::obj:`list`
        :param change_unlimited: unlimited flag
        :type change_unlimited: ::obj:`bool`
        :returns: layout shape
        :rtype: :obj:`list` < :obj:`int` >
        """

        if isinstance(key, filewriter.FTHyperslab):
            if not change_unlimited:
                count = [(ct if ct != unlimited() else 1) for ct in key.count]
                block = [(ct if ct != unlimited() else 1) for ct in key.block]
            else:
                count = key.count
                block = key.block
            eshape = [bl * count[hi] for hi, bl in enumerate(block)]
        if isinstance(key, tuple):
            eshape = []
            for ky in key:
                if not change_unlimited and ky.stop == unlimited():
                    eshape.append(1)
                elif isinstance(ky, slice) and ky.stop > 0:
                    start = ky.start if ky.start is not None else 0
                    step = ky.step if ky.step is not None else 1
                    eshape.append((ky.stop - start) // step)
                else:
                    eshape.append(1)
        return eshape

    def __len__(self):
        """ provides virtual map list length
        :rtype: :obj:`int`
        :returns:  virtual map list length
        """
        # print("LEN", len(self.__vmaps))
        return (len(self.__vmaps))

    def __setitem__(self, key, source):
        """ add target field to layout

        :param key: slide
        :type key: :obj:`tuple`
        :param source: target field view
        :type source: :class:`H5PYTargetFieldView`
        """
        self.add(key, source)

    def add(self, key, source, sourcekey=None, shape=None):
        """ add target field to layout

        :param key: slide
        :type key: :obj:`tuple`
        :param source: target field view
        :type source: :class:`H5PYTargetFieldView`
        :param sourcekey: slide or selection
        :type sourcekey: :obj:`tuple`
        :param shape: target shape in the layout
        :type shape: :obj:`tuple`
        """
        if shape is None:
            shape = list(source.shape or [])
            if hasattr(key, "__len__"):
                size = len(key)
                while len(shape) < size:
                    shape.insert(0, 1)

        lds = {"class": "Simple",
               "shape": tuple(shape)}
        # lds = h5cpp.dataspace.Simple(tuple(shape))
        selection = None
        if key is not None and key != filewriter.FTHyperslab():
            selection = _slice2selection(key, shape)
            lview = {"class": "View",
                     "dataspace": lds,
                     "selection": vars(selection)}
        else:
            lview = {"class": "View",
                     "dataspace": lds}
        sds = {"class": "Simple",
               "shape": tuple(shape)}
        if sourcekey is not None and sourcekey != filewriter.FTHyperslab():
            srcsel = _slice2selection(sourcekey, source.shape)
            eview = {"class": "View",
                     "dataspace": sds,
                     "selection": vars(srcsel)}
        elif selection is not None:
            usel = unlimited_selection(selection, shape)
            if usel is not None:
                eview = {"class": "View",
                         "dataspace": sds,
                         "selection": vars(usel)}
            else:
                eview = {"class": "View",
                         "dataspace": sds}
        else:
            eview = {"class": "View",
                     "dataspace": sds}
        fname = source.filename
        path = (source.fieldpath)
        vdm = {"class": "VirtualDataMap",
               "view": lview,
               "filename": str(fname),
               "path": path,
               "sourceview": eview
               }
        if "vmaps" in self._h5object:
            self._h5object["vmaps"].append(vdm)
        else:
            self._h5object["vmaps"] = [vdm]
        if self.dsname:
            self.append_scaninfo(
                vdm, ["datadesc", self.dsname, "__vmaps__"])


class RedisTargetFieldView(filewriter.FTTargetFieldView):

    """ target field for VDS """

    def __init__(self, filename, fieldpath, shape, dtype=None, maxshape=None):
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
        """
        filewriter.FTTargetFieldView.__init__(self, None)
        #: (:obj:`str`) directory and file name
        self.filename = filename
        #: (:obj:`str`) nexus field path
        self.fieldpath = fieldpath
        #: (:obj:`list` < :obj:`int` >) shape
        self.shape = shape
        # : (:obj:`str`): data type
        self.dtype = dtype
        #: (:obj:`list` < :obj:`int` >) maximal shape
        self.maxshape = maxshape


class RedisDeflate(RedisDataFilter):

    """ deflate filter """


class RedisAttributeManager(filewriter.FTAttributeManager):

    """ file tree attribute
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param tparent: tree parent
        :type tparent: :obj:`FTObject`
        """
        h5object = h5object or {}
        if hasattr(tparent, "get_attr_props"):
            h5object = dict(tparent.get_attr_props())
        filewriter.FTAttributeManager.__init__(self, h5object, tparent)
        #: (:obj:`str`) object nexus path
        self.path = ''
        #: (:obj:`str`) object name
        self.name = None

    def remove(self, name):
        """ remove the attribute

        :param name: attribute name
        :type name: :obj:`str`
        """
        # print("remove", name)
        if hasattr(self._tparent, "remove_attr_name"):
            self._tparent.remove_attr_name(name)

    def append_scaninfo(self, value, keys=None, direct=False):
        """ append scan info parameters

        :param value: scan parameter value
        :type value: :obj:`any`
        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "append_scaninfo"):
            return self._tparent.append_scaninfo(value, keys, direct)

    def set_scaninfo(self, value, keys=None, direct=False):
        """ set scan info parameters

        :param value: scan parameter value
        :type value: :obj:`any`
        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "set_scaninfo"):
            return self._tparent.set_scaninfo(value, keys, direct)

    def get_scaninfo(self, keys=None, direct=False):
        """ get scan info parameters

        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        :returns: scan parameter value
        :rtype: :obj:`any`
        """
        if hasattr(self._tparent, "get_scaninfo"):
            return self._tparent.get_scaninfo(keys, direct)

    def set_attr_value(self, name, value):
        """ set device parameters

        :param name: attribute name
        :type name: :obj:`str`
        :param value: attribute value
        :type value: :obj:`any`
        """
        if hasattr(self._tparent, "set_attr_value"):
            return self._tparent.set_attr_value(name, value)

    def set_attr_prop(self, name, prop):
        """ set attribute properties

        :param name: attribute name
        :type name: :obj:`str`
        :param prop: attribute properties
        :type prop: :obj:`dict`
        """
        if hasattr(self._tparent, "set_attr_prop"):
            return self._tparent.set_attr_prop(name, prop)

    def get_attr_value(self, name):
        """ get scan info parameters

        :param name: attribute name
        :type name: :obj:`str`
        :returns: attribute value
        :rtype: :obj:`any`
        """
        if hasattr(self._tparent, "get_attr_value"):
            return self._tparent.get_attr_value(name)

    def get_attr_prop(self, name):
        """ get scan info parameters

        :param name: attribute name
        :type name: :obj:`str`
        :returns prop: attribute prop
        :rtype prop: :obj:`any`
        """
        if hasattr(self._tparent, "get_attr_prop"):
            return self._tparent.get_attr_prop(name)

    def get_attr_props(self):
        """ get attribute properties

        :returns: attribute properites
        :rtype: :obj:`dict`
        """
        if hasattr(self._tparent, "get_attr_props"):
            return self._tparent.get_attr_props()

    def names(self):
        """ key values

        :returns: attribute names
        :rtype: :obj:`list` <:obj:`str`>
        """
        return self._names()

    def _names(self):
        """ key values

        :returns: attribute names
        :rtype: :obj:`list` <:obj:`str`>
        """
        # print("NAMESS")
        if hasattr(self._tparent, "get_attr_names"):
            return self._tparent.get_attr_names()

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
        :rtype: :class:`RedisAtribute`
        """
        at = None
        names = self._names()
        value = None
        shape = tuple(shape) if shape else shape
        if name in names:
            if overwrite:
                try:
                    prop = dict(self.get_attr_prop(name))
                    if "shape" not in prop:
                        prop["shape"] = tuple()
                    if "dtype" not in prop:
                        prop["dtype"] = "float"
                    if str(prop["dtype"]) == _tostr(dtype) \
                       and prop["shape"] == shape:
                        at = prop
                except Exception as e:
                    print(str(e))
                if at is None:
                    self.remove(name)
            else:
                raise Exception("Attribute %s exists" % name)
        shape = shape or []
        if shape:
            if at is None:
                at = {"name": name, "dtype": dtype, "shape": shape}
                if hasattr(self._tparent, "add_attr_name"):
                    self._tparent.add_attr_name(name)
            if dtype in ['string', b'string']:
                emp = np.empty(shape, dtype="unicode")
                emp[:] = ''
                value = emp
            else:
                value = np.zeros(shape, dtype=dtype)
        else:
            if at is None:
                at = {"name": name, "dtype": dtype}
                if hasattr(self._tparent, "add_attr_name"):
                    self._tparent.add_attr_name(name)
            if dtype in ['string', b'string']:
                value = np.array(u"", dtype="unicode")
            else:
                value = np.array(0, dtype=dtype)

        # print("set prop", name, at)
        if "name" not in at:
            at["name"] = name
        self.set_attr_prop(name, at)
        atr = RedisAttribute(at, self.parent)
        # if overwrite:
        self.set_attr_value(name, value)
        # if dtype == "bool":
        #     at.boolflag = True
        return atr

    def __len__(self):
        """ number of attributes

        :returns: number of attributes
        :rtype: :obj:`int`
        """
        return len(self.get_attr_props().keys())

    def __getitem__(self, name):
        """ get value

        :param name: attribute name
        :type name: :obj:`str`
        :returns: attribute object
        :rtype: :class:`FTAtribute`
        """
        if isinstance(name, int):
            pro = self.get_attr_props()
            prop = pro[list(pro.keys())[name]]
            return RedisAttribute(prop, self.parent)
        else:
            return RedisAttribute(
                self.get_attr_prop(name), self.parent)

    def close(self):
        """ close attribure manager
        """
        filewriter.FTAttributeManager.close(self)

    def reopen(self):
        """ reopen field
        """
        # self._h5object = self._tparent.h5object.attributes
        filewriter.FTAttributeManager.reopen(self)

    @property
    def is_valid(self):
        """ check if link is valid

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        return True


class RedisAttribute(filewriter.FTAttribute):

    """ file tree attribute
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param tparent: tree parent
        :type tparent: :obj:`FTObject`
        """
        filewriter.FTAttribute.__init__(self, h5object, tparent)
        #: (:obj:`str`) object name
        self.name = h5object["name"]
        #: (:obj:`str`) object nexus path
        self.path = tparent.path
        self.path += "@%s" % self.name

        #: (:obj:`str`) datasource name
        self._dsname = None
        #: (:obj:`str`) strategy mode
        self._strategy = None

        #: (:obj:`bool`) bool flag
        # self.boolflag = False

    def close(self):
        """ close attribute
        """
        filewriter.FTAttribute.close(self)

    def read(self):
        """ read attribute value

        :returns: python object
        :rtype: :obj:`any`
        """
        vl = None
        if hasattr(self, "get_attr_value"):
            vl = self.get_attr_value(self.name)
            # print("READ", self.name, vl)
        # if self.dtype in ['string', b'string']:
        #     try:
        #         vl = vl.decode('UTF-8')
        #     except Exception:
        #         pass
        return vl

    def write(self, o):
        """ write attribute value

        :param o: python object
        :type o: :obj:`any`
        """
        vl = o
        if vl is not None:
            # if self.dtype in ['string', b'string']:
            #     try:
            #         vl = vl.decode('UTF-8')
            #     except Exception:
            #         pass
            # print("WRITE", self.name, vl)
            if hasattr(self, "set_attr_value"):
                self.set_attr_value(self.name, vl)
            if self._dsname and self._strategy:
                self.__set_attr_channel_info(
                    self._dsname, self.shape, self._strategy, vl)

    def __set_attr_channel_info(self, dsname, shape, strategy, o):
        """ set init channel info

        :param dsname: datasource name
        :type dsname: :obj:`str`
        :param shape: datasource shape
        :type shape: :obj:`list` <:obj:`int`>
        :param strategy: datasource strategy i.e. INIT or FINAL
        :type strategy: :obj:`str`
        :param o: object value to write
        :type o: :obj:`any`
        """
        ids = {
            "name": dsname,
            "label": dsname,
            "value": o,
            "shape": shape,
            "strategy": strategy,
            "dtype": self.dtype
        }

        ids["nexus_path"] = self.path
        pars = (self.get_scaninfo(["snapshot"]) or {}).keys()
        dsn = dsname
        while dsn in pars:
            dsn = dsn + "_"
        self.set_scaninfo(ids, ["snapshot", dsn])

    def append_scaninfo(self, value, keys=None, direct=False):
        """ append scan info parameters

        :param value: scan parameter value
        :type value: :obj:`any`
        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "append_scaninfo"):
            return self._tparent.append_scaninfo(value, keys, direct)

    def set_scaninfo(self, value, keys=None, direct=False):
        """ set scan info parameters

        :param value: scan parameter value
        :type value: :obj:`any`
        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        """
        if hasattr(self._tparent, "set_scaninfo"):
            return self._tparent.set_scaninfo(value, keys, direct)

    def get_scaninfo(self, keys=None, direct=False):
        """ get scan info parameters

        :param keys: scan parameter value
        :type key: :obj:`list` <:obj:`str`>
        :returns: scan parameter value
        :rtype: :obj:`any`
        """
        if hasattr(self._tparent, "get_scaninfo"):
            return self._tparent.get_scaninfo(keys, direct)

    def __setitem__(self, t, o):
        """ write attribute value

        :param t: slice tuple
        :type t: :obj:`tuple`
        :param o: python object
        :type o: :obj:`any`
        """
        if t is Ellipsis or t == slice(None, None, None) or \
           t == (slice(None, None, None), slice(None, None, None)) or \
           (hasattr(o, "__len__") and t == slice(0, len(o), None)):
            if self.dtype in ['string', b'string']:
                if isinstance(o, str):
                    self.write(unicode(o))
                else:
                    dtype = npunicode
                    self.write(np.array(o, dtype=dtype))
            else:
                self.write(np.array(o, dtype=self.dtype))
        elif isinstance(t, slice):
            var = self.read()
            if self.dtype not in ['string', b'string']:
                var[t] = np.array(o, dtype=nptype(self.dtype))
            else:
                dtype = npunicode
                var = np.array(var, dtype="object")
                var[t] = np.array(o, dtype="object")
                var = var.astype(dtype)
            try:
                self.write(var)
            except Exception:
                dtype = npunicode
                tvar = np.array(var, dtype=dtype)
                self.write(tvar)

        elif isinstance(t, tuple):
            var = self.read()
            if self.dtype not in ['string', b'string']:
                var[t] = np.array(o, dtype=nptype(self.dtype))
            else:
                dtype = npunicode
                if hasattr(var, "flatten"):
                    vv = var.flatten().tolist() + \
                        np.array(o, dtype=dtype).flatten().tolist()
                    nt = np.array(vv, dtype=dtype)
                    var = np.array(var, dtype=nt.dtype)
                    var[t] = np.array(o, dtype=dtype)
                elif hasattr(var, "tolist"):
                    var = var.tolist()
                    var[t] = np.array(o, dtype=self.dtype).tolist()
                else:
                    var[t] = np.array(o, dtype=self.dtype).tolist()
                var = var.astype(dtype)
            self.write(var)
        else:
            if isinstance(o, str) or isinstance(o, unicode):
                self.write(unicode(o))
            else:
                self.write(np.array(o, dtype=self.dtype))

    def __getitem__(self, t):
        """ read attribute value

        :param t: slice tuple
        :type t: :obj:`tuple`
        :returns: python object
        :rtype: :obj:`any`
        """
        rv = self.read()
        if t is Ellipsis:
            return rv
        v = rv[t]
        # if hasattr(v, "shape") and hasattr(v, "reshape"):
        #     shape = [sh for sh in v.shape if sh != 1]
        #     if shape != list(v.shape):
        #         v.reshape(shape)
        # if hasattr(v, "shape"):
        #     shape = v.shape
        #     if len(shape) == 3 and shape[2] == 1:
        #         #: problem with old numpy
        #         # v.reshape(shape[:2])
        #         v = v[:, :, 0]
        #         shape = v.shape
        #     if len(shape) == 3 and shape[1] == 1:
        #         # v.reshape([shape[0], shape[2]])
        #         v = v[:, 0, :]
        #         shape = v.shape
        #     if len(shape) == 3 and shape[0] == 1:
        #         # v.reshape([shape[1], shape[2]])
        #         v = v[0, :, :]
        #         shape = v.shape
        #     if len(shape) == 2 and shape[1] == 1:
        #         # v.reshape([shape[0]])
        #         v = v[0, :]
        #         shape = v.shape
        #     if len(shape) == 2 and shape[0] == 1:
        #         # v.reshape([shape[1]])
        #         v = v[:, 0]
        #         shape = v.shape
        #     if len(shape) == 1 and shape[0] == 1:
        #         v = v[0]
        # if self.dtype in ['string', b'string']:
        #     try:
        #         v = v.decode('UTF-8')
        #     except Exception:
        #         pass
        return v

    @property
    def is_valid(self):
        """ check if attribute is valid

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        return True

    @property
    def dtype(self):
        """ field data type

        :returns: field data type
        :rtype: :obj:`str`
        """
        # if self.boolflag:
        #     return "bool"
        return self._h5object["dtype"] \
            if "dtype" in self._h5object else "string"

    @property
    def shape(self):
        """ attribute shape

        :returns: attribute shape
        :rtype: :obj:`list` < :obj:`int` >
        """
        return tuple(self._h5object["shape"]) \
            if "shape" in self._h5object else ()

    def reopen(self):
        """ reopen attribute
        """
        filewriter.FTAttribute.reopen(self)

    def set_attr_value(self, name, value):
        """ set device parameters

        :param name: attribute name
        :type name: :obj:`str`
        :param value: attribute value
        :type value: :obj:`any`
        """
        if hasattr(self._tparent, "set_attr_value"):
            return self._tparent.set_attr_value(name, value)

    def get_attr_value(self, name):
        """ get scan info parameters

        :param name: attribute name
        :type name: :obj:`str`
        :returns: attribute value
        :rtype: :obj:`any`
        """
        if hasattr(self._tparent, "get_attr_value"):
            return self._tparent.get_attr_value(name)

    def get_attr_prop(self, name):
        """ get scan info parameters

        :param name: attribute name
        :type name: :obj:`str`
        :returns prop: attribute prop
        :rtype prop: :obj:`any`
        """
        if hasattr(self._tparent, "get_attr_prop"):
            return self._tparent.get_attr_prop(name)
