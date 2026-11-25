#!/usr/bin/env python
#   This file is part of nexdatas - Tango Server for NeXus data writer
#
#    Copyright (C) 2026 DESY, Jan Kotanski <jkotan@mail.desy.de>
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

""" Provides h5map file writer

The writer builds the NeXus tree in an in-memory HDF5 file, so that
the nexdatas XML elements, strategies and datasources work as with
the file writers, but nothing is written to disk.  The tree is exported
as a blissdata h5map, i.e. a JSON-serializable dictionary which can be
put into the ``h5maps`` of a blissdata scan and written by blisswriter.

The tree is built by the ``h5cpp`` writer if available, otherwise by the
``h5py`` writer.  The backend can be selected by the ``backend`` parameter
of :func:`create_file`, e.g. with the ``h5map?backend=h5py`` writer of
NXSDataWriter, or by the module ``backend`` variable.  The tree is
exported with h5py in both cases.

Fields with the ``STEP`` strategy are exported as blissdata streams
when their stream names are provided, see :meth:`H5MapFile.h5map`.
All other fields are exported with their values.
"""

import io
import base64
import contextlib

import h5py
import numpy as np

from . import filewriter
from . import h5pywriter
from .nxsfileparser import getdsname, getdssource

try:
    from pninexus import h5cpp
    from . import h5cppwriter
    #: (:obj:`bool`) h5cpp backend with in-memory files and file images
    H5CPP = hasattr(h5cpp.file, "MemoryDriver") \
        and hasattr(h5cpp.file, "from_buffer") \
        and hasattr(h5cpp.file.File, "to_buffer")
except Exception:
    h5cppwriter = None
    H5CPP = False


#: (:obj:`list` <:obj:`str`>) strategies of fields exported as streams
STREAM_STRATEGIES = ["STEP"]

#: (:obj:`dict` <:obj:`str`, :obj:`module`>) available backend writers
BACKENDS = {"h5py": h5pywriter}
if H5CPP:
    BACKENDS["h5cpp"] = h5cppwriter

#: (:obj:`list` <:obj:`str`>) backends in order of preference
DEFAULTBACKENDS = ["h5cpp", "h5py"]

#: (:obj:`str`) default backend, the first available one if None
backend = None


def default_backend():
    """ provides the default backend name

    :returns: the default backend, i.e. h5cpp if available
    :rtype: :obj:`str`
    """
    if backend:
        return _backend_name(backend)
    for name in DEFAULTBACKENDS:
        if name in BACKENDS:
            return name


def _backend_name(name=None):
    """ checks the backend name

    :param name: backend name, the default backend if None
    :type name: :obj:`str`
    :returns: backend name
    :rtype: :obj:`str`
    """
    if not name:
        return default_backend()
    name = str(name).lower()
    if name not in BACKENDS:
        raise ValueError(
            "h5mapwriter: backend '%s' is not available (available: %s)"
            % (name, ", ".join(sorted(BACKENDS))))
    return name


def _module(parent=None):
    """ provides the backend writer module of a node

    :param parent: tree node or None for the default backend
    :type parent: :class:`nxstools.filewriter.FTObject`
    :returns: backend writer module
    :rtype: :obj:`module`
    """
    node = parent
    while node is not None:
        if isinstance(node, H5MapFile):
            return node.writer
        node = getattr(node, "parent", None)
    return BACKENDS[default_backend()]


def is_image_file_supported():
    """ provides if loading of image files are supported

    :retruns: if loading of image files are supported
    :rtype: :obj:`bool`
    """
    return _module().is_image_file_supported()


def is_vds_supported():
    """ provides if VDS are supported

    :retruns: if VDS are supported
    :rtype: :obj:`bool`
    """
    return _module().is_vds_supported()


def is_unlimited_vds_supported():
    """ provides if unlimited VDS are supported

    :retruns: if unlimited VDS are supported
    :rtype: :obj:`bool`
    """
    return _module().is_unlimited_vds_supported()


def unlimited(parent=None):
    """ provides the unlimited dimension size

    :param parent: parent object
    :type parent: :class:`nxstools.filewriter.FTObject`
    :returns: unlimited dimension size
    :rtype: :obj:`int`
    """
    return _module(parent).unlimited()


def link(target, parent, name):
    """ creates a link

    :param target: link target, e.g. ``/entry/data`` or ``file.h5:/entry``
    :type target: :obj:`str`
    :param parent: parent group
    :type parent: :class:`nxstools.filewriter.FTGroup`
    :param name: link name
    :type name: :obj:`str`
    :returns: link object
    :rtype: :class:`nxstools.filewriter.FTLink`
    """
    return _module(parent).link(target, parent, name)


def get_links(parent):
    """ provides the links of a group

    :param parent: parent group
    :type parent: :class:`nxstools.filewriter.FTGroup`
    :returns: list of link objects
    :rtype: :obj:`list` <:class:`nxstools.filewriter.FTLink`>
    """
    return _module(parent).get_links(parent)


def data_filter(filterid=None, name=None, options=None, availability=None,
                shuffle=None, rate=None):
    """ creates a data filter of the default backend

    :returns: data filter object
    :rtype: :class:`nxstools.filewriter.FTDataFilter`
    """
    return _module().data_filter(
        filterid, name, options, availability, shuffle, rate)


def deflate_filter(rate=None, shuffle=None, availability=None):
    """ creates a deflate filter of the default backend

    :returns: deflate filter object
    :rtype: :class:`nxstools.filewriter.FTDataFilter`
    """
    return _module().deflate_filter(rate, shuffle, availability)


def target_field_view(filename, fieldpath, shape, dtype=None,
                      maxshape=None):
    """ creates a target field view of the default backend

    :returns: target field view object
    :rtype: :class:`nxstools.filewriter.FTTargetFieldView`
    """
    return _module().target_field_view(
        filename, fieldpath, shape, dtype, maxshape)


def virtual_field_layout(shape, dtype, maxshape=None, parent=None):
    """ creates a virtual field layout

    :returns: virtual field layout object
    :rtype: :class:`nxstools.filewriter.FTVirtualFieldLayout`
    """
    return _module(parent).virtual_field_layout(
        shape, dtype, maxshape, parent)


def open_file(filename, readonly=False, streams=None, backend=None,
              **pars):
    """ open the new file

    The target file belongs to the h5map consumer, e.g. blisswriter,
    which appends the h5map to an existing file.  Therefore, the file
    on disk is not read and a new in-memory tree is created.

    :param filename: file name
    :type filename: :obj:`str`
    :param readonly: readonly flag (not used)
    :type readonly: :obj:`bool`
    :param streams: stream names of STEP fields or a stream resolver,
                    see :meth:`H5MapFile.h5map`
    :type streams: :obj:`dict` <:obj:`str`, :obj:`str`> or callable
    :param backend: backend writer: ``h5cpp`` or ``h5py``,
                    the default backend if None
    :type backend: :obj:`str`
    :param pars: parameters (not used)
    :type pars: :obj:`dict` < :obj:`str`, :obj:`str`>
    :returns: file object
    :rtype: :class:`H5MapFile`
    """
    return create_file(filename, streams=streams, backend=backend)


def create_file(filename, overwrite=False, streams=None, backend=None,
                **pars):
    """ create a new in-memory file

    :param filename: file name of the h5map target
    :type filename: :obj:`str`
    :param overwrite: overwrite flag (not used)
    :type overwrite: :obj:`bool`
    :param streams: stream names of STEP fields or a stream resolver,
                    see :meth:`H5MapFile.h5map`
    :type streams: :obj:`dict` <:obj:`str`, :obj:`str`> or callable
    :param backend: backend writer: ``h5cpp`` or ``h5py``,
                    the default backend if None
    :type backend: :obj:`str`
    :param pars: parameters (not used)
    :type pars: :obj:`dict` < :obj:`str`, :obj:`str`>
    :returns: file object
    :rtype: :class:`H5MapFile`
    """
    attrs = [
        ("file_time", str(filewriter.FTFile.currenttime())),
        ("NX_class", u"NXroot"),
        ("file_name", str(filename)),
        ("file_update_time", str(filewriter.FTFile.currenttime())),
    ]
    if _backend_name(backend) == "h5cpp":
        fapl = h5cpp.property.FileAccessList()
        # no fallback to a file on disk, i.e. the target file
        h5cpp.file.MemoryDriver()(fapl)
        # the default library version bounds: the image of an open file
        # with the latest file format cannot be read back
        fl = h5cpp.file.create(
            filename, h5cpp.file.AccessFlags.TRUNCATE,
            h5cpp.property.FileCreationList(), fapl)
        mfile = H5MapCppFile(fl, filename, None, streams)
        rattrs = mfile.root().attributes
        for name, value in attrs:
            rattrs.create(name, "string", overwrite=True)[...] = value
        return mfile
    buffer = io.BytesIO()
    fl = h5py.File(buffer, "w", track_order=True)
    for name, value in attrs:
        fl.attrs[name] = value
    return H5MapPYFile(fl, filename, buffer, streams)


def memory_file(filename, **pars):
    """ create a new in-memory file

    :param filename: file name of the h5map target
    :type filename: :obj:`str`
    :param pars: parameters, i.e. ``streams`` and ``backend``
    :type pars: :obj:`dict` < :obj:`str`, :obj:`str`>
    :returns: file object
    :rtype: :class:`H5MapFile`
    """
    return create_file(filename, **pars)


def load_file(membuffer, filename=None, readonly=False, streams=None,
              backend=None, **pars):
    """ load a file from memory byte buffer

    :param membuffer: memory buffer
    :type membuffer: :obj:`bytes`, :obj:`io.BytesIO` or
                     :class:`numpy.ndarray`
    :param filename: file name of the h5map target
    :type filename: :obj:`str`
    :param readonly: readonly flag
    :type readonly: :obj:`bool`
    :param streams: stream names of STEP fields or a stream resolver
    :type streams: :obj:`dict` <:obj:`str`, :obj:`str`> or callable
    :param backend: backend writer: ``h5cpp`` or ``h5py``,
                    the default backend if None
    :type backend: :obj:`str`
    :param pars: parameters (not used)
    :type pars: :obj:`dict` < :obj:`str`, :obj:`str`>
    :returns: file object
    :rtype: :class:`H5MapFile`
    """
    if _backend_name(backend) == "h5cpp":
        image = _image_array(membuffer)
        flag = h5cpp.file.ImageFlags.READONLY if readonly \
            else h5cpp.file.ImageFlags.READWRITE
        fl = h5cpp.file.from_buffer(image, flag)
        return H5MapCppFile(fl, filename, image, streams)
    if not hasattr(membuffer, "read") or not hasattr(membuffer, "seek"):
        if hasattr(membuffer, "tobytes"):
            membuffer = membuffer.tobytes()
        membuffer = io.BytesIO(membuffer)
    fl = h5py.File(membuffer, "r" if readonly else "r+")
    return H5MapPYFile(fl, filename, membuffer, streams)


def _image_array(membuffer):
    """ converts a memory buffer to an uint8 numpy array

    :param membuffer: memory buffer
    :type membuffer: :obj:`bytes`, :obj:`io.BytesIO` or
                     :class:`numpy.ndarray`
    :returns: file image
    :rtype: :class:`numpy.ndarray`
    """
    if hasattr(membuffer, "getvalue"):
        membuffer = membuffer.getvalue()
    if isinstance(membuffer, np.ndarray):
        return np.array(membuffer, dtype="uint8").reshape(-1)
    return np.frombuffer(bytes(membuffer), dtype="uint8").copy()


def _tostr(value):
    """ converts bytes to str

    :param value: value
    :type value: :obj:`any`
    :returns: str value
    :rtype: :obj:`str`
    """
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _b64(array):
    """ converts numeric array to an h5map inline_b64 item

    :param array: numpy array
    :type array: :class:`numpy.ndarray`
    :returns: h5map data item
    :rtype: :obj:`dict` <:obj:`str`, `any`>
    """
    array = np.ascontiguousarray(array)
    dtype = array.dtype.str
    if array.dtype.itemsize == 1:
        dtype = "|" + dtype[1:]
    return {
        "type": "inline_b64",
        "dtype": dtype,
        "shape": list(array.shape),
        "value": base64.b64encode(array.tobytes()).decode("ascii"),
    }


def _nonfinite(value):
    """ converts non-finite floats to strings, recursively

    :param value: value from :meth:`numpy.ndarray.tolist`
    :type value: :obj:`any`
    :returns: JSON value
    :rtype: :obj:`any`
    """
    if isinstance(value, list):
        return [_nonfinite(vl) for vl in value]
    if isinstance(value, float) and not np.isfinite(value):
        return str(value)
    return value


def data_item(value):
    """ converts a value to an h5map data item

    Strings are exported as raw JSON strings, other values keep
    their numpy dtype and shape.

    :param value: value
    :type value: :obj:`any`
    :returns: h5map data item
    :rtype: :obj:`any`
    """
    if isinstance(value, (str, bytes)):
        return _tostr(value)
    array = np.asarray(value)
    if array.dtype.kind in "OSU":
        if array.shape == ():
            return _tostr(array.item())
        return np.vectorize(_tostr, otypes=[object])(array).tolist() \
            if array.size else []
    if array.dtype.kind == "b":
        if not array.size:
            return _b64(array)
        return {"type": "inline", "dtype": "bool",
                "value": array.tolist()}
    if array.dtype.kind in "iuf" and array.size \
            and array.dtype.byteorder in "=|<>":
        return {"type": "inline", "dtype": array.dtype.name,
                "value": _nonfinite(array.tolist())}
    # complex, empty or exotic types
    return _b64(array)


def _attributes(h5obj):
    """ exports attributes of an h5py object

    :param h5obj: h5py object
    :type h5obj: :class:`h5py.Group` or :class:`h5py.Dataset`
    :returns: h5map attributes
    :rtype: :obj:`dict` <:obj:`str`, `any`>
    """
    return {name: data_item(h5obj.attrs[name]) for name in h5obj.attrs}


def _attr_str(h5obj, name):
    """ reads a string attribute

    :param h5obj: h5py object
    :type h5obj: :class:`h5py.Group` or :class:`h5py.Dataset`
    :param name: attribute name
    :type name: :obj:`str`
    :returns: attribute value or empty string
    :rtype: :obj:`str`
    """
    if name not in h5obj.attrs:
        return ""
    value = filewriter.first(h5obj.attrs[name])
    return _tostr(value) if value is not None else ""


def _selection(space):
    """ converts an h5py dataspace selection to an h5map space selection

    :param space: h5py dataspace
    :type space: :class:`h5py.h5s.SpaceID`
    :returns: h5map space selection, with empty lists for a whole
              dataspace of unknown extent
    :rtype: :obj:`dict` <:obj:`str`, `any`>
    """
    dims = list(space.get_simple_extent_dims())
    stype = space.get_select_type()
    if stype == h5py.h5s.SEL_ALL:
        return {"start": [0] * len(dims), "count": dims}
    if stype != h5py.h5s.SEL_HYPERSLABS or \
            not space.is_regular_hyperslab():
        raise ValueError("Only regular hyperslab selections are supported")
    start, stride, count, block = space.get_regular_hyperslab()
    ulim = unlimited()
    count = list(count)
    block = list(block)
    for i, ct in enumerate(count):
        if ct == ulim:
            # the current extent of the dimension
            size = dims[i] if i < len(dims) else 0
            count[i] = max(
                0, (size - start[i] - block[i]) // stride[i] + 1) \
                if block[i] != ulim else 1
        if block[i] == ulim:
            size = dims[i] if i < len(dims) else 0
            block[i] = max(0, size - start[i])
    stride = list(stride)
    for i in range(len(count)):
        # contiguous selections as simple counts
        if count[i] == 1 or stride[i] == block[i]:
            count[i] *= block[i]
            block[i] = 1
            stride[i] = 1
    selection = {"start": list(start), "count": count}
    if any(st != 1 for st in stride):
        selection["stride"] = list(stride)
    if any(bl != 1 for bl in block):
        selection["block"] = block
    return selection


def _virtual_dataset(dset, filename, attributes):
    """ exports a virtual dataset

    :param dset: h5py virtual dataset
    :type dset: :class:`h5py.Dataset`
    :param filename: file name of the h5map target
    :type filename: :obj:`str`
    :param attributes: h5map attributes
    :type attributes: :obj:`dict` <:obj:`str`, `any`>
    :returns: h5map virtual dataset
    :rtype: :obj:`dict` <:obj:`str`, `any`>
    """
    sources = []
    for vmap in dset.virtual_sources():
        srcfile = vmap.file_name
        if srcfile == ".":
            srcfile = filename
        vspace = _selection(vmap.vspace)
        src_space = _selection(vmap.src_space)
        if not src_space["count"]:
            # the whole source of unknown extent, e.g. in a reopened file,
            # has as many elements per dimension as the virtual selection
            src_space = {
                "start": [0] * len(vspace["count"]),
                "count": [ct * bl for ct, bl in zip(
                    vspace["count"],
                    vspace.get("block", [1] * len(vspace["count"])))]}
        sources.append({
            "vspace": vspace,
            "src_file": srcfile,
            "src_dataset": vmap.dset_name,
            "src_space": src_space,
        })
    dtype = dset.dtype.str
    if dset.dtype.itemsize == 1:
        dtype = "|" + dtype[1:]
    item = {
        "type": "virtual_dataset",
        "dtype": dtype,
        "shape": list(dset.shape),
        "virtual_sources": sources,
    }
    if attributes:
        item["attributes"] = attributes
    return item


class H5MapExporter(object):
    """ exports an h5py tree to h5map
    """

    def __init__(self, filename, streams=None, skip=None):
        """ constructor

        :param filename: file name of the h5map target
        :type filename: :obj:`str`
        :param streams: stream names of STEP fields or a stream resolver,
                        see :meth:`H5MapFile.h5map`
        :type streams: :obj:`dict` <:obj:`str`, :obj:`str`> or callable
        :param skip: strategies of fields to be skipped, e.g. ``["FINAL"]``
        :type skip: :obj:`list` <:obj:`str`>
        """
        #: (:obj:`str`) file name of the h5map target
        self.filename = filename
        #: (:obj:`dict` <:obj:`str`, :obj:`str`> or callable) stream names
        self.streams = streams
        #: (:obj:`list` <:obj:`str`>) strategies of fields to be skipped
        self.skip = list(skip or [])

    def stream_name(self, path, dset):
        """ provides a stream name of a field

        :param path: field path
        :type path: :obj:`str`
        :param dset: h5py dataset
        :type dset: :class:`h5py.Dataset`
        :returns: stream name or None
        :rtype: :obj:`str`
        """
        if not self.streams:
            return None
        strategy = _attr_str(dset, "nexdatas_strategy")
        if strategy not in STREAM_STRATEGIES:
            return None
        source = _attr_str(dset, "nexdatas_source")
        dsname = getdsname(source) if source else ""
        record = getdssource(source) if source else ""
        if callable(self.streams):
            return self.streams(path, dsname, record, strategy)
        for key in (path, dsname, record):
            if key and key in self.streams:
                return self.streams[key]
        return None

    def dataset(self, path, dset):
        """ exports a dataset

        :param path: dataset path
        :type path: :obj:`str`
        :param dset: h5py dataset
        :type dset: :class:`h5py.Dataset`
        :returns: h5map dataset
        :rtype: :obj:`dict` <:obj:`str`, `any`>
        """
        attributes = _attributes(dset)
        if dset.is_virtual:
            return _virtual_dataset(dset, self.filename, attributes)
        stream = self.stream_name(path, dset)
        if stream:
            value = {"type": "stream", "stream": stream}
        else:
            value = data_item(dset[()])
        item = {"type": "dataset", "value": value}
        if attributes:
            item["attributes"] = attributes
        return item

    def group(self, path, grp):
        """ exports a group with its children

        :param path: group path
        :type path: :obj:`str`
        :param grp: h5py group
        :type grp: :class:`h5py.Group`
        :returns: h5map group
        :rtype: :obj:`dict` <:obj:`str`, `any`>
        """
        item = {"type": "group"}
        attributes = _attributes(grp)
        if attributes:
            item["attributes"] = attributes
        children = {}
        for name in grp.keys():
            cpath = "%s/%s" % (path.rstrip("/"), name)
            lnk = grp.get(name, getlink=True)
            if isinstance(lnk, h5py.SoftLink):
                children[name] = {
                    "type": "soft_link", "target_path": lnk.path}
            elif isinstance(lnk, h5py.ExternalLink):
                children[name] = {
                    "type": "external_link",
                    "target_file": lnk.filename,
                    "target_path": lnk.path}
            else:
                child = grp[name]
                if isinstance(child, h5py.Group):
                    children[name] = self.group(cpath, child)
                elif not self.skip or _attr_str(
                        child, "nexdatas_strategy") not in self.skip:
                    children[name] = self.dataset(cpath, child)
        if children:
            item["children"] = children
        return item


class H5MapFile(object):

    """ file tree exported to h5map, the base of the backend files
    """

    def _h5map_init(self, module, streams=None):
        """ initializes the h5map part of the file

        :param module: backend writer module
        :type module: :obj:`module`
        :param streams: stream names of STEP fields or a stream resolver,
                        see :meth:`h5map`
        :type streams: :obj:`dict` <:obj:`str`, :obj:`str`> or callable
        """
        #: (:obj:`module`) backend writer module
        self._backend_module = module
        #: (:obj:`dict` <:obj:`str`, :obj:`str`> or callable) stream names
        self.streams = streams

    @property
    def writer(self):
        """ backend writer module of the tree nodes

        :mod:`nxstools.filewriter` finds the writer module of a node
        via its file, so that links and filters are created by the backend.

        :returns: backend writer module
        :rtype: :obj:`module`
        """
        return getattr(self, "_backend_module", None)

    @writer.setter
    def writer(self, value):
        """ ignores the module set by :mod:`nxstools.filewriter`

        :param value: writer module
        :type value: :obj:`module`
        """

    @property
    def backend(self):
        """ backend name

        :returns: ``h5cpp`` or ``h5py``
        :rtype: :obj:`str`
        """
        for name, module in BACKENDS.items():
            if module is self.writer:
                return name

    def hasswmr(self):
        """ checks if SWMR is supported

        :returns: SWMR flag
        :rtype: :obj:`bool`
        """
        return False

    @contextlib.contextmanager
    def _h5py_file(self):
        """ provides the tree as an h5py file

        :returns: h5py file
        :rtype: :class:`h5py.File`
        """
        raise NotImplementedError
        yield

    def h5map(self, streams=None, skip=None):
        """ exports the file tree to an h5map

        Fields with the ``STEP`` strategy are exported as streams when
        *streams* provides their stream names.  *streams* is either a
        dictionary with field paths, datasource names or datasource
        records as keys and stream names as values, or a callable
        ``streams(path, dsname, record, strategy)`` returning a stream
        name or None.  The other fields are exported with their values.

        Fields which are not written yet can be skipped by their strategy,
        e.g. ``skip=["FINAL"]`` before closing the entry.

        :param streams: stream names of STEP fields or a stream resolver,
                        the file ``streams`` by default
        :type streams: :obj:`dict` <:obj:`str`, :obj:`str`> or callable
        :param skip: strategies of fields to be skipped
        :type skip: :obj:`list` <:obj:`str`>
        :returns: h5map of the root group, serializable to JSON
        :rtype: :obj:`dict` <:obj:`str`, `any`>
        """
        streams = streams if streams is not None else self.streams
        exporter = H5MapExporter(self.name, streams, skip)
        with self._h5py_file() as fl:
            return exporter.group("/", fl)

    def h5maps(self, streams=None, skip=None):
        """ exports the file tree to the h5maps of a blissdata scan

        :param streams: stream names of STEP fields or a stream resolver
        :type streams: :obj:`dict` <:obj:`str`, :obj:`str`> or callable
        :param skip: strategies of fields to be skipped
        :type skip: :obj:`list` <:obj:`str`>
        :returns: ``{file name: h5map}``
        :rtype: :obj:`dict` <:obj:`str`, `any`>
        """
        return {self.name: self.h5map(streams, skip)}


class H5MapPYFile(H5MapFile, h5pywriter.H5PYFile):

    """ file tree built with the h5py backend
    """

    def __init__(self, h5object, filename, buffer=None, streams=None):
        """ constructor

        :param h5object: in-memory h5py file
        :type h5object: :class:`h5py.File`
        :param filename: file name of the h5map target
        :type filename: :obj:`str`
        :param buffer: memory buffer of the h5py file
        :type buffer: :class:`io.BytesIO`
        :param streams: stream names of STEP fields or a stream resolver,
                        see :meth:`h5map`
        :type streams: :obj:`dict` <:obj:`str`, :obj:`str`> or callable
        """
        h5pywriter.H5PYFile.__init__(self, h5object, filename)
        self._h5map_init(h5pywriter, streams)
        #: (:class:`io.BytesIO`) memory buffer of the h5py file
        self._buffer = buffer

    @property
    def is_valid(self):
        """ check if file is open

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        try:
            return bool(self._h5object.id.valid)
        except Exception:
            return False

    def close(self):
        """ closes the file but keeps its memory buffer
        """
        if not self.is_valid:
            return
        filewriter.FTFile.close(self)
        if self._h5object.mode in ["r+"]:
            self._h5object.attrs["file_update_time"] = \
                str(self.currenttime())
        self._h5object.close()

    def reopen(self, readonly=False, swmr=False, libver=None):
        """ reopens the file from its memory buffer

        :param readonly: readonly flag
        :type readonly: :obj:`bool`
        :param swmr: swmr flag (not used)
        :type swmr: :obj:`bool`
        :param libver: library version (not used)
        :type libver: :obj:`str`
        """
        if self.is_valid:
            if (self._h5object.mode in ["r"]) == bool(readonly):
                return
            self._h5object.close()
        if self._buffer is None:
            raise Exception("H5MapFile: memory buffer is not available")
        self._h5object = h5py.File(
            self._buffer, "r" if readonly else "r+")
        filewriter.FTFile.reopen(self)

    @contextlib.contextmanager
    def _h5py_file(self):
        """ provides the tree as an h5py file

        :returns: h5py file
        :rtype: :class:`h5py.File`
        """
        if self.is_valid:
            yield self._h5object
        else:
            with h5py.File(self._buffer, "r") as fl:
                yield fl

    def tobytes(self):
        """ provides the in-memory HDF5 image of the file

        :returns: HDF5 file image
        :rtype: :obj:`bytes`
        """
        if self.is_valid:
            self._h5object.flush()
        return self._buffer.getvalue()


if H5CPP:

    class H5MapCppFile(H5MapFile, h5cppwriter.H5CppFile):

        """ file tree built with the h5cpp backend

        The tree is an h5cpp file of the memory driver.  Its image is
        exported with h5py and kept when the file is closed.
        """

        def __init__(self, h5object, filename, image=None, streams=None):
            """ constructor

            :param h5object: in-memory h5cpp file
            :type h5object: :class:`pninexus.h5cpp.file.File`
            :param filename: file name of the h5map target
            :type filename: :obj:`str`
            :param image: file image of the closed file
            :type image: :class:`numpy.ndarray`
            :param streams: stream names of STEP fields or a stream
                            resolver, see :meth:`h5map`
            :type streams: :obj:`dict` <:obj:`str`, :obj:`str`> or callable
            """
            h5cppwriter.H5CppFile.__init__(self, h5object, filename)
            self._h5map_init(h5cppwriter, streams)
            #: (:class:`numpy.ndarray`) file image of the closed file
            self._image = image

        def image(self):
            """ provides the HDF5 image of the file

            :returns: HDF5 file image
            :rtype: :class:`numpy.ndarray`
            """
            if self.is_valid:
                self._h5object.flush(h5cpp.file.Scope.GLOBAL)
                image = np.zeros(self._h5object.buffer_size, dtype="uint8")
                self._h5object.to_buffer(image)
                return image
            if self._image is None:
                raise Exception("H5MapFile: file image is not available")
            return self._image

        def close(self):
            """ closes the file but keeps its image
            """
            if not self.is_valid:
                return
            if not self.readonly:
                self.root().attributes.create(
                    "file_update_time", "string", overwrite=True)[...] = \
                    str(self.currenttime())
            self._image = self.image()
            filewriter.FTFile.close(self)
            self._h5object.close()

        def reopen(self, readonly=False, swmr=False, libver=None):
            """ reopens the file from its image

            :param readonly: readonly flag
            :type readonly: :obj:`bool`
            :param swmr: swmr flag (not used)
            :type swmr: :obj:`bool`
            :param libver: library version (not used)
            :type libver: :obj:`str`
            """
            if self.is_valid:
                if bool(self.readonly) == bool(readonly):
                    return
                self.close()
            flag = h5cpp.file.ImageFlags.READONLY if readonly \
                else h5cpp.file.ImageFlags.READWRITE
            self._h5object = h5cpp.file.from_buffer(self.image(), flag)
            filewriter.FTFile.reopen(self)

        @contextlib.contextmanager
        def _h5py_file(self):
            """ provides the tree as an h5py file

            :returns: h5py file
            :rtype: :class:`h5py.File`
            """
            with h5py.File(io.BytesIO(self.image().tobytes()), "r") as fl:
                yield fl

        def tobytes(self):
            """ provides the in-memory HDF5 image of the file

            :returns: HDF5 file image
            :rtype: :obj:`bytes`
            """
            return self.image().tobytes()
