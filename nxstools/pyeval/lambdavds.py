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

"""  pyeval helper functions for lambdavds """

import json

try:
    from . import common
except Exception:
    import common


def vmap(commonblock, name, triggermode,
         translations, saveallimages,
         fileprefix, filepreext, filepostfix,
         filestartnum, framesperfile, framenumbers,
         height, width, opmode, savefilepath, savefilename,
         filename, entryname, insname, hostname, device,
         shortdetpath=None):
    """ code for triggermode_cb  datasource

    :param commonblock: commonblock of nxswriter
    :type commonblock: :obj:`dict`<:obj:`str`, `any`>
    :param name: component name
    :type name: :obj:`str`
    :param triggermode:  trigger mode
    :type triggermode: :obj:`int` or :obj:`str`
    :param translations: json dictionary with translations
    :type translations: :obj:`str`
    :param saveallimages: save all images flag
    :type saveallimages: :obj:`int` or :obj:`bool`
    :param fileprefix: filename prefix
    :type fileprefix:  :obj:`str`
    :param filepreext: filename pre ext
    :type filepreext:  :obj:`str`
    :param filepostfix: filename postfix
    :type filepostfix:  :obj:`str`
    :param filestartnum: file start number
    :type filestartnum:  :obj:`str`
    :param framesperfile: a number of frames per file
    :type framesperfile: :obj:`int`
    :param framenumbers: The frame numbers need to be acquired
    :type framenumbers: :obj:`int`
    :param height: height of the image
    :type height: :obj:`int`
    :param width: width of the image
    :type width: :obj:`int`
    :param opmode: operation mode,
                   i.e. 1="int8", 6="int8", 12="int16", 24="int32"
    :type opmode:  :obj:`int`
    :param savefilepath: savefilepath
    :type savefilepath: :obj:`str`
    :param savefilename: savefilename
    :type savefilename: :obj:`str`
    :param filename: master file name
    :type filename: :obj:`str`
    :param entryname: entry name
    :type entryname: :obj:`str`
    :param insname: instrument name
    :type insname: :obj:`str`
    :param hostname: tango host name
    :type hostname: :obj:`str`
    :param device: tango device name
    :type device: :obj:`str`
    :param shortdetpath: shortdetpath
    :type shortdetpath: :obj:`bool`
    :returns: json vmap
    :rtype: :obj:`str`
    """
    step = commonblock["__counter__"] - 1
    vmaps = []
    if saveallimages and step == 0:
        dtm = {1: "int8", 6: "int8", 12: "int16", 24: "int32"}
        try:
            dtype = dtm[opmode]
        except Exception:
            dtype = "int32"

        modoffsets = json.loads(translations)
        totalheight = 0
        totalwidth = 0
        totalframenumbers = 0
        modsize = len(list(modoffsets.keys()))
        for offset in modoffsets.values():
            totalframenumbers = max(
                totalframenumbers, framenumbers)
            totalheight = max(totalheight, height + round(offset[1]))
            totalwidth = max(totalwidth, width + round(offset[0]))
        shape = [totalheight, totalwidth]
        unlimited = False
        if totalframenumbers == framenumbers:
            unlimited = True

        path = ""
        if filename:
            sfname = (filename).split("/")
            path = sfname[-1].split(".")[0] + "/"
            if shortdetpath is None and \
                    len(sfname) > 1 and sfname[-2] == path[:-1]:
                path = ""
            elif shortdetpath:
                path = ""
        # vfl = nxw.virtual_field_layout(
        #     [totalframenumbers, totalheight, totalwidth], dtype)

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

        npath = "/entry/instrument/detector/data"
        for modulename, offset in modoffsets.items():
            mfilename = path + name + "/" + str(savefilename)
            if modsize != 1:
                mfilename += "_" + modulename
            mfilename += "." + str(filepostfix)
            # target = "%s:/%s" % (mfilename, npath)
            if unlimited:
                key = [[None, nxw.unlimited()],
                       [round(offset[1]), height + round(offset[1])],
                       [round(offset[0]), width + round(offset[0])]]
                sourcekey = [[None, nxw.unlimited()], [None], [None]]
            else:

                key = [[0, framenumbers],
                       [round(offset[1]), height + round(offset[1])],
                       [round(offset[0]), width + round(offset[0])]]
                sourcekey = [[None], [None], [None]]
            vmap = {"fieldpath": npath,
                    "filename": mfilename,
                    "dtype": dtype,
                    "key": key,
                    "sourcekey": sourcekey,
                    "shape": [totalframenumbers, height, width],
                    "dsname": "%s" % (name),
                    # "plugin_stream": {"frame": step, "stored": True}
                    }
            vmaps.append(vmap)

        # patternprefix = "%s/%s" % (pilcfiledir, pilcfileprefix)
        # if triggersperfile and nbtriggers > triggersperfile:
        #     pattern = "{prefix}_%05d.nxs".format(prefix=patternprefix)
        # else:
        #     pattern = "{prefix}%05d_00000.nxs".format(
        #         prefix=(patternprefix[:-5]))
        # meta = {
        #     "plugin": "h5file_detector",
        #     "plugin_def": {
        #         "name": "%s" % (name),
        #         "dtype": dtype,
        #         "shape": shape,
        #         "file_pattern": pattern,
        #         "frames_per_file": totalframenumbers,
        #         "data_path": npath,
        #         "info": {"unit": ""},
        #         "file_index_offset": 0,
        #         "file_mode": "noframe"
        #     }
        # }

        # if meta:
        #     vmap.update(meta)
    print(vmaps)
    return json.dumps(vmaps)


def nm_triggermode_cb(commonblock, name, triggermode,
                      translations, saveallimages,
                      filepostfix, framenumbers,
                      height, width, opmode,
                      savefilename, filename, entryname,
                      insname="instrument",
                      shortdetpath=None):
    """ code for triggermode_cb  datasource

    :param commonblock: commonblock of nxswriter
    :type commonblock: :obj:`dict`<:obj:`str`, `any`>
    :param name: component name
    :type name: :obj:`str`
    :param triggermode:  trigger mode
    :type triggermode: :obj:`int` or :obj:`str`
    :param translations: json dictionary with translations
    :type translations: :obj:`str`
    :param saveallimages: save all images flag
    :type saveallimages: :obj:`int` or :obj:`bool`
    :param filepostfix: filename postfix
    :type filepostfix:  :obj:`str`
    :param framenumbers: a number of frames
    :type framenumbers: :obj:`int`
    :param height: height of the image
    :type height: :obj:`int`
    :param width: width of the image
    :type width: :obj:`int`
    :param opmode: operation mode,
                   i.e. 1="int8", 6="int8", 12="int16", 24="int32"
    :type opmode:  :obj:`int`
    :param savefilename: savefilename
    :type savefilename: :obj:`str`
    :param filename: master file name
    :type filename: :obj:`str`
    :param entryname: entry name
    :type entryname: :obj:`str`
    :param shortdetpath: shortdetpath
    :type shortdetpath: :obj:`bool`
    :returns:  triggermode
    :rtype: :obj:`str` or :obj:`int`
    """
    if saveallimages:
        if "__root__" in commonblock.keys():
            root = commonblock["__root__"]
        dtm = {1: "int8", 6: "int8", 12: "int16", 24: "int32"}
        try:
            dtype = dtm[opmode]
        except Exception:
            dtype = "int32"

        modoffsets = json.loads(translations)
        totalheight = 0
        totalwidth = 0
        totalframenumbers = 0
        modsize = len(list(modoffsets.keys()))
        for offset in modoffsets.values():
            totalframenumbers = max(
                totalframenumbers, framenumbers)
            totalheight = max(totalheight, height + round(offset[1]))
            totalwidth = max(totalwidth, width + round(offset[0]))
        unlimited = False
        if totalframenumbers == framenumbers:
            unlimited = True

        path = ""
        if filename:
            sfname = (filename).split("/")
            path = sfname[-1].split(".")[0] + "/"
            if shortdetpath is None and \
                    len(sfname) > 1 and sfname[-2] == path[:-1]:
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
            [totalframenumbers, totalheight, totalwidth], dtype)
        for modulename, offset in modoffsets.items():
            mfilename = path + name + "/" + str(savefilename)
            if modsize != 1:
                mfilename += "_" + modulename
            mfilename += "." + str(filepostfix)
            ef = nxw.target_field_view(
                mfilename, npath, [framenumbers, height, width], dtype)
            if unlimited:
                vfl.add(
                    (slice(None, nxw.unlimited()),
                     slice(round(offset[1]), height + round(offset[1])),
                     slice(round(offset[0]), width + round(offset[0]))),
                    ef,
                    (slice(None, nxw.unlimited()),
                     slice(None), slice(None)))
            else:
                vfl.add(
                    (slice(0, framenumbers),
                     slice(round(offset[1]), height + round(offset[1])),
                     slice(round(offset[0]), width + round(offset[0]))),
                    ef,
                    (slice(None), slice(None), slice(None)))
        det.create_virtual_field("data", vfl)
    return triggermode


def savefilename_cb(commonblock, savefilename, savefilename_str):
    """ code for savefilename_cb  datasource

    :param commonblock: commonblock of nxswriter
    :type commonblock: :obj:`dict`<:obj:`str`, `any`>
    :param savefilename:  name of saved file
    :type savefilename: :obj:`str`
    :param savefilename_str: name of savefilename datasource
    :type savefilename_str: :obj:`str`
    :returns:   name of saved file
    :rtype: :obj:`str`
    """
    return common.blockitem_add(
        commonblock, savefilename_str, savefilename)


def framenumbers_cb(commonblock, framenumbers, framenumbers_str):
    """ code for triggermode_cb  datasource

    :param commonblock: commonblock of nxswriter
    :type commonblock: :obj:`dict`<:obj:`str`, `any`>
    :param framenumbers:  number of frames
    :type framenumbers: :obj:`str` or :obj:`int`
    :param framenumbers_str: name of framenumbers datasource
    :type framenumbers_str: :obj:`str`
    :returns:  number of frames
    :rtype: :obj:`str` or :obj:`int`
    """
    return common.blockitem_addint(
        commonblock, framenumbers_str, framenumbers)


def triggermode_cb(commonblock, name, triggermode, saveallimages,
                   framesperfile, height, width, opmode,
                   filepostfix, savefilename_str, framenumbers_str,
                   filename_str, entry_str,
                   shortdetpath=None):
    """ code for triggermode_cb  datasource

    :param commonblock: commonblock of nxswriter
    :type commonblock: :obj:`dict`<:obj:`str`, `any`>
    :param name: component name
    :type name: :obj:`str`
    :param triggermode:  trigger mode
    :type triggermode: :obj:`int` or :obj:`str`
    :param saveallimages: save all images flag
    :type saveallimages: :obj:`int` or :obj:`bool`
    :param height: height of the image
    :type height: :obj:`int`
    :param framesperfile: a number of frames per fiel
    :type framesperfile: :obj:`int`
    :param height: height of the image
    :type height: :obj:`int`
    :param width: width of the image
    :type width: :obj:`int`
    :param opmode: operation mode,
                   i.e. 1="int8", 6="int8", 12="int16", 24="int32"
    :type opmode:  :obj:`int`
    :param filepostfix: filename postfix
    :type filepostfix:  :obj:`str`
    :param savefilename_str: name of savefilename datasource
    :type savefilename_str: :obj:`str`
    :param framenumbers_str: name of framenumbers datasource
    :type framenumbers_str: :obj:`str`
    :param filename_str: file name
    :type filename_str: :obj:`str`
    :param entry_str: entry name
    :type entry_str: :obj:`str`
    :param shortdetpath: shortdetpath
    :type shortdetpath: :obj:`bool`
    :returns:  triggermode
    :rtype: :obj:`str` or :obj:`int`
    """

    if saveallimages:

        if "__root__" in commonblock.keys():
            root = commonblock["__root__"]
        filenames = []
        framesnumbers = []
        if savefilename_str in commonblock:
            filenames = commonblock[savefilename_str]
        if framenumbers_str in commonblock:
            framesnumbers = commonblock[framenumbers_str]
        fln = min(len(framesnumbers), len(filenames))

        filesframes = []
        lastfile = None
        totalframenumbers = 0
        for fi in range(fln):
            if lastfile != filenames[fi]:
                filesframes.append((filenames[fi], framesnumbers[fi]))
                lastfile = filenames[fi]
                totalframenumbers += framesnumbers[fi]
        dtm = {1: "int8", 6: "int8", 12: "int16", 24: "int32"}
        try:
            dtype = dtm[opmode]
        except Exception:
            dtype = "int32"

        path = ""
        if filename_str:
            sfname = (filename_str).split("/")
            path = sfname[-1].split(".")[0] + "/"
            if shortdetpath is None and \
                    len(sfname) > 1 and sfname[-2] == path[:-1]:
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

        en = root.open(entry_str)
        ins = en.open("instrument")
        det = ins.open(name)
        npath = "/entry/instrument/detector/data"

        vfl = nxw.virtual_field_layout(
            [totalframenumbers, height, width], dtype)

        foffset = 0
        for savefilename, framenumbers in filesframes:
            if framenumbers > 0 and framesperfile > 10:
                nbfiles = (framenumbers - 1) // framesperfile + 1
                lastfilenbframes = framenumbers - (nbfiles - 1) * framesperfile
            elif framenumbers > 0:
                nbfiles = 1
                lastfilenbframes = framenumbers
            else:
                nbfiles = 0
                lastfilenbframes = 0

            if nbfiles > 0:
                for nbf in range(0, nbfiles):
                    if framenumbers > framesperfile and framesperfile > 10:
                        connector = "_part%05d." % nbf
                    else:
                        connector = "."
                    filename = path + name + "/" + str(savefilename) \
                        + connector + str(filepostfix)
                    ln = framesperfile if nbf + 1 != nbfiles \
                        else lastfilenbframes
                    ef = nxw.target_field_view(
                        filename, npath, [ln, height, width], dtype)
                    vfl[
                        (foffset + nbf * framesperfile):
                        (foffset + nbf * framesperfile + ln), :, :] = ef
                foffset += framenumbers
        det.create_virtual_field("data", vfl)
    return triggermode
