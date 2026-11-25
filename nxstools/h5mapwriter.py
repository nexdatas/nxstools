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
the h5py writer, but nothing is written to disk.  The tree is exported
as a blissdata h5map, i.e. a JSON-serializable dictionary which can be
put into the ``h5maps`` of a blissdata scan and written by blisswriter.

Fields with the ``STEP`` strategy are exported as blissdata streams
when their stream names are provided, see :meth:`H5MapFile.h5map`.
All other fields are exported with their values.
"""

import io
import base64

import h5py
import numpy as np

from . import filewriter
from . import h5pywriter
from .nxsfileparser import getdsname, getdssource


#: (:obj:`list` <:obj:`str`>) strategies of fields exported as streams
STREAM_STRATEGIES = ["STEP"]

# the h5py writer functions which do not depend on the file backend
_slice2selection = h5pywriter._slice2selection
unlimited_selection = h5pywriter.unlimited_selection
nptype = h5pywriter.nptype
is_image_file_supported = h5pywriter.is_image_file_supported
is_vds_supported = h5pywriter.is_vds_supported
is_mbs_supported = h5pywriter.is_mbs_supported
is_unlimited_vds_supported = h5pywriter.is_unlimited_vds_supported
is_strings_as_bytes = h5pywriter.is_strings_as_bytes
unlimited = h5pywriter.unlimited
link = h5pywriter.link
get_links = h5pywriter.get_links
data_filter = h5pywriter.data_filter
deflate_filter = h5pywriter.deflate_filter
target_field_view = h5pywriter.target_field_view
virtual_field_layout = h5pywriter.virtual_field_layout


def open_file(filename, readonly=False, streams=None, **pars):
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
    :param pars: parameters (not used)
    :type pars: :obj:`dict` < :obj:`str`, :obj:`str`>
    :returns: file object
    :rtype: :class:`H5MapFile`
    """
    return create_file(filename, streams=streams)


def create_file(filename, overwrite=False, streams=None, **pars):
    """ create a new in-memory file

    :param filename: file name of the h5map target
    :type filename: :obj:`str`
    :param overwrite: overwrite flag (not used)
    :type overwrite: :obj:`bool`
    :param streams: stream names of STEP fields or a stream resolver,
                    see :meth:`H5MapFile.h5map`
    :type streams: :obj:`dict` <:obj:`str`, :obj:`str`> or callable
    :param pars: parameters (not used)
    :type pars: :obj:`dict` < :obj:`str`, :obj:`str`>
    :returns: file object
    :rtype: :class:`H5MapFile`
    """
    buffer = io.BytesIO()
    fl = h5py.File(buffer, "w", track_order=True)
    fl.attrs["file_time"] = str(H5MapFile.currenttime())
    fl.attrs["NX_class"] = u"NXroot"
    fl.attrs["file_name"] = str(filename)
    fl.attrs["file_update_time"] = str(H5MapFile.currenttime())
    return H5MapFile(fl, filename, buffer, streams)


def memory_file(filename, **pars):
    """ create a new in-memory file

    :param filename: file name of the h5map target
    :type filename: :obj:`str`
    :param pars: parameters, i.e. ``streams``
    :type pars: :obj:`dict` < :obj:`str`, :obj:`str`>
    :returns: file object
    :rtype: :class:`H5MapFile`
    """
    return create_file(filename, **pars)


def load_file(membuffer, filename=None, readonly=False, streams=None,
              **pars):
    """ load a file from memory byte buffer

    :param membuffer: memory buffer
    :type membuffer: :obj:`bytes` or :obj:`io.BytesIO`
    :param filename: file name of the h5map target
    :type filename: :obj:`str`
    :param readonly: readonly flag
    :type readonly: :obj:`bool`
    :param streams: stream names of STEP fields or a stream resolver
    :type streams: :obj:`dict` <:obj:`str`, :obj:`str`> or callable
    :param pars: parameters (not used)
    :type pars: :obj:`dict` < :obj:`str`, :obj:`str`>
    :returns: file object
    :rtype: :class:`H5MapFile`
    """
    if not hasattr(membuffer, "read") or not hasattr(membuffer, "seek"):
        if hasattr(membuffer, "tobytes"):
            membuffer = membuffer.tobytes()
        membuffer = io.BytesIO(membuffer)
    fl = h5py.File(membuffer, "r" if readonly else "r+")
    return H5MapFile(fl, filename, membuffer, streams)


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


class H5MapFile(h5pywriter.H5PYFile):

    """ file tree exported to h5map
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
        #: (:class:`io.BytesIO`) memory buffer of the h5py file
        self._buffer = buffer
        #: (:obj:`dict` <:obj:`str`, :obj:`str`> or callable) stream names
        self.streams = streams

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

    def hasswmr(self):
        """ checks if SWMR is supported

        :returns: SWMR flag
        :rtype: :obj:`bool`
        """
        return False

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
        if self.is_valid:
            return exporter.group("/", self._h5object)
        with h5py.File(self._buffer, "r") as fl:
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

    def tobytes(self):
        """ provides the in-memory HDF5 image of the file

        :returns: HDF5 file image
        :rtype: :obj:`bytes`
        """
        if self.is_valid:
            self._h5object.flush()
        return self._buffer.getvalue()


H5MapGroup = h5pywriter.H5PYGroup
H5MapField = h5pywriter.H5PYField
H5MapLink = h5pywriter.H5PYLink
H5MapDataFilter = h5pywriter.H5PYDataFilter
H5MapDeflate = h5pywriter.H5PYDeflate
H5MapVirtualFieldLayout = h5pywriter.H5PYVirtualFieldLayout
H5MapTargetFieldView = h5pywriter.H5PYTargetFieldView
H5MapAttributeManager = h5pywriter.H5PYAttributeManager
H5MapAttribute = h5pywriter.H5PYAttribute
