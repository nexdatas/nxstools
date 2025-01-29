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

import json
try:
    import tango
except Exception:
    import PyTango as tango


def triggermode_cb(commonblock, name, triggermode,
                   nbframes, hostname, device,
                   filename, entryname, insname,
                   filedir, fileprefix, framesperfile,
                   maskdatatowrite, mcalength, savedata, , acq_modes=""):
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
    try:
        nbchannels = int(xp.get_property("NbChannels")["NbChannels"][0])
    except Exception:
        nbchannels = 0

    if not nbchannels:
        return triggermode

    path = ""
    sfname = []
    if filename:
        sfname = (filename).split("/")
        path = sfname[-1].split(".")[0] + "/"
    path += '%s/%s_' % (name, fileprefix)
    filepostfix = ".nxs"
    
    spf = 0
    cfid = 0
    if "__root__" in commonblock.keys():
        root = commonblock["__root__"]
        if hasattr(root, "currentfileid") and hasattr(root, "stepsperfile"):
            spf = root.stepsperfile
            cfid = root.currentfileid
        if root.h5object.__class__.__name__ == "File":
            import nxstools.h5pywriter as nxw
        else:
            import nxstools.h5cppwriter as nxw
    else:
        raise Exception("Writer cannot be found")

    en = root.open(entryname)
    dt = en.open("data")
    ins = en.open(insname)
    det = ins.open(name)
    col = det.open("collection")

    nbfiles = (nbframes + framesperfile - 1) // framesperfile
    
    for nch in len(nbchannels):
        masked = maskdatatowrite & (1 << nch)
        if masked:
            continue
        for nbf in range(nbfiles):
            # counter_00002_00000.nxs://entry/instrument/xspress3/channel00/histogram
            # -> col/channel00_f00000
            nxw.link(
                "%s%05i.nxs://entry/instrument/xspress3/channel%02i/histogram"
                % (path, nbf, nch),
                     col, "channel%02i_f%05i" % (nch, nbf))
            nxw.link("/%s/%s/%s/collection/%s" %
                     (entryname, insname, name, "channel%02i_f%05i" % (nch, nbf)), dt,
                     "%s_%02i_f%05i" % (name, nch, nbf))

def old:
            

    # create VDS field
    if shape and not isinstance(shape, list):
        try:
            shape = json.loads(shape)
        except Exception:
            shape = []
    if not shape or len(shape) < 2:
        return result

    if "nb_images_in_file" not in col.names():
        tni = col.create_field("nb_images_in_file", "uint64")
    else:
        tni = col.open("nb_images_in_file")
        tni.grow()
    tni[int(tni.shape[0] - 1)] = totnbimages
    ttni = tni.read()
    totalframenumbers = int(sum(ttni))
    ttfn = tfn.read()

    if "VDS" in amodes and "data" not in det.names():
        edp = tango.DeviceProxy('%s/%s' % (hostname, device))
        if hasattr(edp, "RoiMode") and edp.RoiMode:
            if hasattr(edp, "RoiModeString") and \
                    hasattr(edp, "RoiYSize") and \
                    edp.RoiModeString == "lines":
                if edp.RoiYSize:
                    try:
                        shape = [int(edp.RoiYSize), shape[1]]
                    except Exception:
                        pass
            else:
                shape = [2167, 2070]

        npath = "/entry/data/data"

        nbimg = []
        nfi = []
        fnms = []
        for ii, tt in enumerate(ttni):
            nbf = int((tt + imagesperfile - 1) // imagesperfile)
            nfi.append(nbf)
            nn = [int(imagesperfile)] * nbf

            fn = [str(ttfn[j + ii * (int(imagesperfile) - 1)])
                  for j in range(nbf)]
            if nn:
                nn[-1] = int(tt - (nbf - 1) * imagesperfile)
            nbimg.extend(nn)
            fnms.extend(fn)

        nboff = [int(sum(nbimg[:(ii)])) for ii in range(len(nbimg))]
        # eiger9m 3110 pixel x 3269 pixel
        # /entry/data/data uint32 [1, 3269 , 3110]
        # eiger4M 2070 pixel x 2167 pixel
        # /entry/data/data uint32 [1, 2167 , 2070]
        # eiger1M  1030 pixel x 1065 pixel
        # /entry/data/data uint32 [1, 1065 , 1030]

        vfl = nxw.virtual_field_layout(
            [totalframenumbers, shape[0], shape[1]], dtype)
        for ii, nb in enumerate(nbimg):
            fnm = fnms[ii]
            ef = nxw.target_field_view(
                fnm, npath, [nb, shape[0], shape[1]], dtype)
            off = nboff[ii]
            vfl.add(
                (slice(off, off + nb), slice(0, shape[0]), slice(0, shape[1])),
                ef, (slice(None), slice(None), slice(None)))

        if "data" not in det.names():
            det.create_virtual_field("data", vfl)
        if name not in dt.names():
            nxw.link("/%s/%s/%s/data" % (entryname, insname, name),
                     dt, name)

    return triggermode
