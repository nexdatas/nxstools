#!/usr/bin/env python
#   This file is part of nexdatas - Tango Server for NeXus data writer
#
#    Copyright (C) 2012-2018 DESY, Jan Kotanski <jkotan@mail.desy.de>
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

"""  pyeval helper functions for limaccd """

import os


def postrun(commonblock,
            saving_next_number,
            saving_directory,
            saving_suffix,
            acq_nb_frames,
            saving_index_format,
            saving_prefix,
            saving_next_number_str,
            name=None,
            saving_format=None,
            saving_frame_per_file=None,
            image_height=None,
            image_width=None,
            image_type=None,
            acq_trigger_mode=None,
            acq_mode='SINGLE',
            filename=None,
            entryname=None,
            insname=None,
            acq_modes="",
            field_path="/entry_0000/measurement/data"
            ):
    """ code for postrun datasource

    :param commonblock: commonblock of nxswriter
    :type commonblock: :obj:`dict`<:obj:`str`, `any`>
    :param saving_next_number: saving next number
    :type saving_next_number: :obj:`int`
    :param saving_directory: saving directory
    :type saving_directory: :obj:`str`
    :param saving_suffix: saving suffix
    :type saving_suffix: :obj:`str`
    :param acq_nb_frames: number of frames acquired
    :type acq_nb_frames: :obj:`str`
    :param saving_index_format: saving index format
    :type saving_index_format: :obj:`str`
    :param saving_prefix: saving prefix
    :type saving_prefix: :obj:`str`
    :param saving_next_number_str: datasource string name
    :type saving_next_number_str: :obj:`str`
    :param name: component name
    :type name: :obj:`str`
    :param saving_format: saving format
    :type saving_format: :obj:`str`
    :param saving_frame_per_file: saving frame per file
    :type saving_frame_per_file: :obj:`str`
    :param image_height: image height
    :type image_height: :obj:`int`
    :param image_width: image width
    :type image_width: :obj:`int`
    :param image_type: image type
    :type image_type: :obj:`int`
    :param acq_mode: acquisition mode
    :type acq_mode: :obj:`str`
    :param acq_trigger_mode: acquisition trigger mode
    :type acq_trigger_mode: :obj:`str`
    :param filename: file name
    :type filename: :obj:`str`
    :param entryname: entry name
    :type entryname: :obj:`str`
    :param insname: instrument name
    :type insname: :obj:`str`
    :param acq_modes: acquisition modes
    :type acq_modes: :obj:`str`
    :param field_path: nexus field path
    :type field_path: :obj:`str`
    :returns: name of saved file
    :rtype: :obj:`str`
    """
    filedir = (saving_directory).replace("\\", "/")
    amodes = acq_modes.split(",")
    if len(filedir) > 1 and filedir[1] == ":":
        filedir = "/data" + filedir[2:]
    if filedir and filedir[-1] == "/":
        filedir = filedir[:-1]
    if acq_mode == "SINGLE" and \
            acq_trigger_mode in ["INTERNAL_TRIGGER_MULTI",
                                 "EXTERNAL_TRIGGER_MULTI"] and \
            saving_format == "HDF5":
        filelastnumber = saving_next_number - 1
        nbfiles = (acq_nb_frames + saving_frame_per_file - 1) \
            // saving_frame_per_file
        filestartnum = filelastnumber - nbfiles + 1

        if "__root__" in commonblock.keys():
            root = commonblock["__root__"]
            if root.h5object.__class__.__name__ == "File":
                import nxstools.h5pywriter as nxw
            else:
                import nxstools.h5cppwriter as nxw
        else:
            raise Exception("Writer cannot be found")

        path = ""
        sfname = []
        if not filename:
            if root._tparent is not None:
                filename = root._tparent.filename
        basepath = ""
        if filename:
            sfname = (filename).split("/")
            path = sfname[-1].split(".")[0] + "/"
            basepath = "/".join(os.path.abspath(filename).split("/")[:-1])
        if filedir and filedir.startswith(basepath):
            path = filedir[len(basepath) + 1:]
        else:
            path += '%s' % (name)
        path += '/%s' % (saving_prefix)

        en = root.open(entryname)
        dt = en.open("data")
        ins = en.open(insname)
        det = ins.open(name)
        try:
            col = det.open("collection")
        except Exception:
            col = det.create_group("collection", "NXcollection")

        shape = [image_height, image_width]
        if "VDS" in amodes and "data" not in det.names():
            l2nt = {
                "bpp8": "uint8", "bpp8s": "int8",
                "bpp16": "uint16", "bpp16s": "int16",
                "bpp32": "uint32", "bpp32s": "int32",
                "bpp32f": "float",
            }
            dtype = l2nt.get(image_type.lower(), "int32")
            vfl = nxw.virtual_field_layout(
                [acq_nb_frames, shape[0], shape[1]], dtype)

        fnamepattern = "%s%s%s" % (path, saving_index_format, saving_suffix)

        for nbf in range(filestartnum, filelastnumber + 1):
            rnbf = nbf - filestartnum
            try:
                detfn = fnamepattern % nbf
            except Exception:
                detfn = fnamepattern

            nxw.link("%s:/%s" % (detfn, field_path),
                     col, "data_%05i" % (nbf))
            nxw.link("/%s/%s/%s/collection/%s" %
                     (entryname, insname, name, "data_%05i" % (nbf)), dt,
                     "%s_%05i" % (name, nbf))

            if "VDS" in amodes and "data" not in det.names():
                off = saving_frame_per_file * rnbf
                if rnbf + 1 == nbfiles:
                    nb = acq_nb_frames - off
                else:
                    nb = saving_frame_per_file
                ef = nxw.target_field_view(
                    detfn, field_path,
                    [nb, shape[0], shape[1]], dtype)
                vfl.add(
                    (slice(off, off + nb),
                     slice(0, shape[0]),
                     slice(0, shape[1])),
                    ef, (slice(None), slice(None), slice(None)))
        if "VDS" in amodes and "data" not in det.names():
            det.create_virtual_field("data", vfl)
        elif nbfiles == 1:
            nxw.link("/%s/%s/%s/collection/%s" %
                     (entryname, insname, name, "data_%05i"
                      % (filestartnum)), det, "data")
        if name not in dt.names() and "data" in det.names():
            nxw.link("/%s/%s/%s/data" % (entryname, insname, name),
                     dt, name)
        result = ""
    else:
        filestartnum = commonblock[saving_next_number_str] - 1
        result = "" + filedir + "/" + saving_prefix + saving_index_format
        result += saving_suffix + ":"
        filelastnumber = saving_next_number - 1
        if acq_mode == "SINGLE" and \
                acq_trigger_mode in ["INTERNAL_TRIGGER_MULTI",
                                     "EXTERNAL_TRIGGER_MULTI"]:
            nbfiles = (acq_nb_frames + saving_frame_per_file - 1) \
                // saving_frame_per_file
            filestartnum = filelastnumber - nbfiles + 1
        if "__root__" in commonblock.keys():
            root = commonblock["__root__"]
            if hasattr(root, "currentfileid") and \
                    hasattr(root, "stepsperfile"):
                spf = root.stepsperfile
                cfid = root.currentfileid
                if spf > 0 and cfid > 0:
                    filelastnumber = min(
                        filestartnum + cfid * acq_nb_frames * spf - 1,
                        filelastnumber)
                    filestartnum = filestartnum + (cfid - 1) \
                        * acq_nb_frames * spf
        result += str(filestartnum) + ":" + str(filelastnumber)
    return result
