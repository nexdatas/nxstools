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

"""  pyeval helper functions for pilc """

# import json
try:
    import tango
except Exception:
    import PyTango as tango


def triggermode_cb(commonblock, name, triggermode,
                   nbtriggers, triggersperfile,
                   hostname, device,
                   filename, entryname,
                   insname, pilcfileprefix, pilcfiledir,
                   timeid=False,
                   shortdetpath=None):
    """ code for triggermode_cb  datasource

    :param commonblock: commonblock of nxswriter
    :type commonblock: :obj:`dict`<:obj:`str`, `any`>
    :param name: component name
    :type name: :obj:`str`
    :param triggermode:  trigger mode
    :type triggermode: :obj:`int` or :obj:`str`
    :param nbtriggers: a number of triggers
    :type nbtriggers: :obj:`int`
    :param triggersperfile: a number of triggers per file
    :type triggersperfile: :obj:`int`
    :param hostname: tango host name
    :type hostname: :obj:`str`
    :param device: tango device name
    :type device: :obj:`str`
    :param filename: master file name
    :type filename: :obj:`str`
    :param entryname: entry name
    :type entryname: :obj:`str`
    :param insname: instrument name
    :type insname: :obj:`str`
    :param pilcfileprefix: pilc file name prefix
    :type pilcfileprefix :obj:`str`
    :param pilcfiledir: pilc file name directory
    :type pilcfiledir :obj:`str`
    :param timeid: file id with timestamp
    :type timeid: :obj:`bool`
    :param shortdetpath: shortdetpath
    :type shortdetpath: :obj:`bool`
    :returns: triggermode
    :rtype: :obj:`str` or :obj:`int`
    """

    dp = tango.DeviceProxy('%s/%s' % (hostname, device))
    fpattern = pilcfileprefix.split("/")[-1]
    if triggersperfile >= 1:
        nbfiles = (nbtriggers + triggersperfile - 1) // triggersperfile
    else:
        nbfiles = 1
    fields = ["counter", "time", "trigger",
              "encoder_1", "encoder_2",
              "encoder_3", "encoder_4", "encoder_5"]
    nbstart = 0
    filepostfix = ".nxs"
    try:
        pilcfilename = str(dp.FileName)
        if pilcfilename.startswith(fpattern + "_") and \
                pilcfilename.endswith(filepostfix):
            nblast = int(pilcfilename[
                    len(fpattern) + 1: - len(filepostfix)])
            nbstart = max(0, nblast - nbfiles + 1)
    except Exception:
        pilcfilename = None
    nblist = [nb for nb in range(nbstart, nbstart + nbfiles)]
    path = ""
    if filename:
        sfname = (filename).split("/")
        path = sfname[-1].split(".")[0] + "/"
        if shortdetpath is None and \
                len(sfname) > 1 and sfname[-2] == path[:-1]:
            path = ""
        elif shortdetpath:
            path = ""
    path += '%s/%s_' % (name, fpattern)
    result = triggermode

    spf = 0
    cfid = 0
    if "__root__" in commonblock.keys():
        root = commonblock["__root__"]
        if hasattr(root, "currentfileid") and hasattr(root, "stepsperfile"):
            spf = root.stepsperfile
            cfid = root.currentfileid
        if type(root).__name__ == "RedisGroup":
            import nxstools.rediswriter as nxw
        elif root.h5object.__class__.__name__ == "File":
            import nxstools.h5pywriter as nxw
        else:
            import nxstools.h5cppwriter as nxw
    else:
        raise Exception("Writer cannot be found")

    en = root.open(entryname)
    dt = en.open("data")
    ins = en.open(insname)
    pilc = ins.open(name)
    pilcdata = pilc.open("data")
    col = pilc.open("collection")

    if timeid and pilcfilename and "filenames" in col.names():
        try:
            filenames = list(col.open("filenames").read())
            if filenames:
                filenames.append(str(pilcfilename))
                nlist = []
                for fname in filenames:
                    fname = str(fname)
                    if fname.startswith(fpattern + "_") and \
                            fname.endswith(filepostfix):
                        nlist.append(int(fname[
                            len(fpattern) + 1: - len(filepostfix)]))
                nblist = nlist
        except Exception:
            pass
    for nbf in nblist:
        # nnbf = "%05i" % (nbf)
        for field in fields:
            fnbf = "%s_%05i" % (field, nbf)
            if spf > 0 and cfid > 0:
                if cfid == nbf:
                    nxw.link(
                        "%s%05i%s://entry/data/%s"
                        % (path, nbf, filepostfix, field),
                        pilcdata, field)
                    nxw.link("/%s/%s/%s/data/%s"
                             % (entryname, insname, name, field),
                             dt, "%s_%s" % (name, field))
                nxw.link("%s%05i%s://entry/data/%s"
                         % (path, nbf, filepostfix, field),
                         pilcdata, "%s" % (fnbf))
            else:
                nxw.link("%s%05i%s://entry/data/%s"
                         % (path, nbf, filepostfix, field),
                         pilcdata, "%s" % (fnbf))
                nxw.link("/%s/%s/%s/data/%s" %
                         (entryname, insname, name, fnbf), dt,
                         "%s_%s" % (name, fnbf))
    return result
