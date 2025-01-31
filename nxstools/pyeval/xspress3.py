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

"""  pyeval helper functions for xspress """

import os
try:
    import tango
except Exception:
    import PyTango as tango


def triggermode_cb(commonblock, name, triggermode,
                   nbframes, hostname, device,
                   filename, entryname, insname,
                   filedir, fileprefix, framesperfile,
                   maskdatatowrite, mcalength, savedata,
                   acq_modes=""):
    """ code for triggermode_cb  datasource

    :param commonblock: commonblock of nxswriter
    :type commonblock: :obj:`dict`<:obj:`str`, `any`>
    :param name: component name
    :type name: :obj:`str`
    :param triggermode:  trigger mode
    :type triggermode: :obj:`int`
    :param nbframes: a number of images
    :type nbframes: :obj:`int`
    :param hostname: tango host name
    :type hostname: :obj:`str`
    :param device: tango device name
    :type device: :obj:`str`
    :param filename: file name
    :type filename: :obj:`str`
    :param entryname: entry name
    :type entryname: :obj:`str`
    :param insname: instrument name
    :type insname: :obj:`str`
    :param filedir: file directory
    :type filedir: :obj:`str`
    :param fileprefix: file prefix
    :type fileprefix: :obj:`str`
    :param framesperfile: frame number per file
    :type framesperfile: :obj:`int`
    :param maskdatatowrite: mask data to write
    :type maskdatatowrite: :obj:`int`
    :param mcalength: mcalength
    :type mcalength: :obj:`int`
    :param savedata: savedata flag
    :type savedata: :obj:`bool`
    :param acq_modes: acquisition modes
    :type acq_modes: :obj:`str`
    :returns: triggermode
    :rtype: :obj:`int`
    """

    if not savedata:
        return triggermode
    amodes = acq_modes.split(",")
    xp = tango.DeviceProxy('%s/%s' % (hostname, device))
    #  print("device", device, hostname)
    try:
        nbchannels = int(xp.get_property("NbChannels")["NbChannels"][0])
        # print("GET", int(xp.get_property("NbChannels")["NbChannels"][0]))
    except Exception as e:
        print("EXCE", str(e))
        nbchannels = 0

    if not nbchannels:
        return triggermode

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
    path += '/%s_' % (fileprefix)

    en = root.open(entryname)
    dt = en.open("data")
    ins = en.open(insname)

    nbfiles = (nbframes + framesperfile - 1) // framesperfile
    shape = [nbframes, mcalength]
    dtype = "int32"

    for nch in range(nbchannels):
        masked = maskdatatowrite & (1 << nch)
        # print("NCHAN", nch, masked)
        if masked:
            continue
        chname = "%s_channel%02i" % (name, nch)
        detc = ins.create_group(chname, "NXdetector")
        colc = detc.create_group("collection", "NXcollection")

        if "VDS" in amodes and "data" not in detc.names():
            vfl = nxw.virtual_field_layout(shape, dtype)

        for nbf in range(nbfiles):
            nxw.link(
                "%s%05i.nxs://entry/instrument/xspress3/channel%02i/histogram"
                % (path, nbf, nch),
                colc, "data_%05i" % (nbf))
            nxw.link("/%s/%s/%s/collection/%s" %
                     (entryname, insname, chname, "data_%05i"
                      % (nbf)), dt,
                     "%s_channel%02i_%05i" % (name, nch, nbf))

            if "VDS" in amodes and "data" not in detc.names():
                off = framesperfile * nbf
                if nbf + 1 == nbfiles:
                    nb = nbframes - off
                else:
                    nb = framesperfile
                ef = nxw.target_field_view(
                    "%s%05i.nxs" % (path, nbf),
                    "/entry/instrument/xspress3/channel%02i/histogram" % (nch),
                    [nb, shape[1]], dtype)
                vfl.add(
                    (slice(off, off + nb), slice(0, shape[1])),
                    ef, (slice(None), slice(None)))
        if "VDS" in amodes and "data" not in detc.names():
            detc.create_virtual_field("data", vfl)
        elif nbfiles == 1:
            nxw.link("/%s/%s/%s/collection/%s" %
                     (entryname, insname, chname, "data_%05i"
                      % (0)), detc, "data")
        if chname not in dt.names() and "data" in detc.names():
            nxw.link("/%s/%s/%s/data" % (entryname, insname, chname),
                     dt, chname)

    return triggermode
