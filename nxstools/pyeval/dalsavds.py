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

"""  pyeval helper functions for dalsa """


def triggermode(commonblock, name,
                filedir, fileprefix, filepostfix, filestartnum, filesaving,
                triggermode, framespernxfile, pixelformat, height, width,
                acquisitionmode, acquisitionframecount,
                filestartnum_str, nrexposedframes_str,
                filename, entryname, insname="instrument",
                shortdetpath=None):
    """ code for external_data datasource

    :param commonblock: commonblock of nxswriter
    :type commonblock: :obj:`dict`<:obj:`str`, `any`>
    :param name: detector name
    :type name: :obj:`str`
    :param filedir: file directory
    :type filedir: :obj:`str`
    :param fileprefix: file prefix
    :type fileprefix: :obj:`str`
    :param filepostfix: file postfix
    :type filepostfix: :obj:`str`
    :param filestartnum: file start number
    :type filestartnum: :obj:`int`
    :param filesaving: file saving flag
    :type filesaving: :obj:`int` or :obj:`bool`
    :param triggermode: trigger mode
    :type triggermode: :obj:`str`
    :param framespernxfile: frames per nexus file
    :type framespernxfile: :obj:`int`
    :param pixelformat: pixel format
    :type pixelformat: :obj:`str`
    :param height: image height
    :type height: :obj:`int`
    :param width: image width
    :type width: :obj:`int`
    :param acquisitionmode: acquisition mode
    :type acquisitionmode: :obj:`str`
    :param acquisitionframecount: acquisition frame count
    :type acquisitionframecount: :obj:`str`
    :param filestartnum_str: filestartnum name string
    :type filestartnum_str: :obj:`str`
    :param nrexposedframes_str: nrexposedframes name string
    :type nrexposedframes_str: :obj:`str`
    :param filename: file name
    :type filename: :obj:`str`
    :param entryname: entry name
    :type entryname: :obj:`str`
    :param insname: instrument name
    :type insname: :obj:`str`
    :param shortdetpath: shortdetpath
    :type shortdetpath: :obj:`bool`
    :returns: trigger mode
    :rtype: :obj:`str`
    """
    result = triggermode

    if filesaving:
        if "__root__" in commonblock.keys():
            root = commonblock["__root__"]
        # filenames = []
        filestartnumbers = []
        if filestartnum_str in commonblock:
            filestartnumbers = commonblock[filestartnum_str]
        if nrexposedframes_str in commonblock:
            nrexposedframes = commonblock[nrexposedframes_str]
        flen = len(filestartnumbers)
        frlen = nrexposedframes[-1] if nrexposedframes else 0

        lastfilenumber = filestartnumbers[-1] if filestartnumbers else 0

        totalframenumbers = 0

        mode = acquisitionmode
        framecount = acquisitionframecount
        filesizes = []
        totalframenumbers = []
        nbfiles = 0
        if mode in ["MultiFrame"]:
            totalframenumbers = flen * framecount
            if 1 > framespernxfile or framespernxfile > framecount:
                filesizes = [framecount] * (flen)
                nbfiles = len(filesizes)
                lastfilenbframes = framecount
            else:
                fsizes = []
                filesizes = []
                nbfiles = 0
                nfiles = (framecount + 1) // framespernxfile + 1
                lastfilenbframes = framecount % framespernxfile
                print(nfiles)
                if nfiles:
                    fsizes = [framespernxfile] * (nfiles - 1)
                if lastfilenbframes:
                    fsizes.append(lastfilenbframes)
                for i in range(nfiles):
                    filesizes = filesizes + fsizes
                nbfiles = nfiles * len(fsizes)

        elif mode in ["SingleFrame"]:
            totalframenumbers = flen
            filesizes = [1 for _ in range(flen)]
            nbfiles = len(filesizes)
            lastfilenbframes = nbfiles
        elif mode in ["Continuous"]:
            totalframenumbers = frlen
            if 1 > framespernxfile or framespernxfile > frlen:
                filesizes = [frlen]
                nbfiles = len(filesizes)
                lastfilenbframes = frlen
            else:
                nbfiles = (frlen + 1) // framespernxfile + 1
                lastfilenbframes = frlen % framespernxfile
                filesizes = []
                if nbfiles:
                    filesizes = [framespernxfile] * (nbfiles - 1)
                if lastfilenbframes:
                    filesizes.append(lastfilenbframes)

        dtm = {
            "Mono8": "uint8",
            "Mono8Signed": "int8",
            "Mono10": "uint16",
            "Mono12": "uint16",
            "Mono10Packed": "uint16",
            "Mono12Packed": "uint16",
            "Mono14": "uint16",
            "Mono16": "uint16",
            "Mono16Signed": "int16",
            "BayerGR10": "uint16",
            "BayerRG10": "uint16",
            "BayerGB10": "uint16",
            "BayerBG10": "uint16",
            "BayerGR12": "uint16",
            "BayerRG12": "uint16",
            "BayerGB12": "uint16",
            "BayerBG12": "uint16",
        }

        try:
            dtype = dtm[pixelformat]
        except Exception:
            dtype = "uint8"

        path = ""
        if filename:
            sfname = (filename).split("/")
            path = sfname[-1].split(".")[0] + "/"
            if shortdetpath is None and \
                    len(sfname) > 1 and sfname[-2] == result[:-1]:
                path = ""
            elif shortdetpath:
                path = ""

        if "__root__" in commonblock.keys():
            root = commonblock["__root__"]
            if type(root).__name__ == "RedisGroup":
                import nxstools.rediswriter as nxw
            elif root.h5object.__class__.__name__ == "File":
                import nxstools.h5pywriter as nxw
            else:
                import nxstools.h5cppwriter as nxw
        else:
            raise Exception("Writer cannot be found")

        en = root.open(entryname)
        ins = en.open(insname)
        det = ins.open(name)
        npath = "/entry/instrument/detector/data"

        vfl = nxw.virtual_field_layout(
            [totalframenumbers, height, width], dtype)
        firstfilenumber = lastfilenumber - nbfiles
        if nbfiles > 0:
            i1 = 0
            i2 = 0
            for nbf in range(firstfilenumber, lastfilenumber):
                ln = filesizes[nbf - firstfilenumber]
                i1 = i2
                i2 = i2 + ln
                connector = "_%05d." % nbf
                filename = path + name + "/" + str(fileprefix) + connector + \
                    str(filepostfix)
                ef = nxw.target_field_view(
                    filename, npath, [ln, height, width], dtype)
                vfl[i1: i2, :, :] = ef
        det.create_virtual_field("data", vfl)

    return result
