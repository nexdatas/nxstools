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

"""  pyeval helper functions for beamtimeid """

import os
import socket


def beamtimeid(commonblock, starttime, shortname, compath, curpath, locpath,
               curprefix, curext, comprefix, comext, strip=True):
    """ code for beamtimeid  datasource

    :param commonblock: commonblock of nxswriter
    :type commonblock: :obj:`dict`<:obj:`str`, `any`>
    :param starttime:  start time
    :type starttime: :obj:`str`
    :param shortname:  short name of beamline
    :type shortname: :obj:`str`
    :param compath:  commission directory
    :type compath: :obj:`str`
    :param curpath:  current directory
    :type curpath: :obj:`str`
    :param locpath:  local directory
    :type locpath: :obj:`str`
    :param curprefix:  current prefix
    :type curprefix: :obj:`str`
    :param curext:  current postfix
    :type curext: :obj:`str`
    :param comprefix:  commission prefix
    :type comprefix: :obj:`str`
    :param comext:  commission postfix
    :type comext: :obj:`str`
    :returns:   beamtime id
    :rtype: :obj:`str`
    """

    result = None
    root = commonblock["__nxroot__"] if "__nxroot__" in commonblock else None
    if hasattr(root, "filename"):
        fpath = root.filename
    else:
        root = commonblock["__root__"]
        fpath = root.parent.name
    if fpath.startswith(curpath):
        try:
            if os.path.isdir(curpath):
                btml = [fl for fl in os.listdir(curpath)
                        if (fl.startswith(curprefix)
                            and fl.endswith(curext))]
            if btml:
                if strip:
                    result = btml[0][len(curprefix):-len(curext)]
                else:
                    result = os.path.join(os.path.abspath(curpath), btml[0])
        except Exception:
            pass
    if not result and fpath.startswith(compath):
        try:
            if os.path.isdir(compath):
                btml = [fl for fl in os.listdir(compath)
                        if (fl.startswith(comprefix)
                            and fl.endswith(comext))]
            if btml:
                if strip:
                    result = btml[0][len(comprefix):-len(comext)]
                else:
                    result = os.path.join(os.path.abspath(compath), btml[0])
        except Exception:
            pass
    if not result:
        try:
            dirpath = os.path.dirname(fpath)
            while dirpath.startswith(locpath):
                if os.path.isdir(dirpath):
                    btml = [fl for fl in os.listdir(dirpath)
                            if (fl.startswith(curprefix)
                                and fl.endswith(curext))]
                    if btml:
                        result = btml[0][len(curprefix):-len(curext)]
                        break
                    else:
                        btml = [fl for fl in os.listdir(dirpath)
                                if (fl.startswith(comprefix)
                                    and fl.endswith(comext))]
                        if btml:
                            if strip:
                                result = btml[0][len(comprefix):-len(comext)]
                            else:
                                result = os.path.join(
                                    os.path.abspath(locpath), btml[0])
                            break
                dirpath, tail = os.path.split(dirpath)
        except Exception:
            pass
    if os.path.isdir(curpath):
        try:
            if os.path.isdir(curpath):
                btml = [fl for fl in os.listdir(curpath)
                        if (fl.startswith(curprefix)
                            and fl.endswith(curext))]
            if btml:
                if strip:
                    result = btml[0][len(curprefix):-len(curext)]
                else:
                    result = os.path.join(os.path.abspath(curpath), btml[0])
        except Exception:
            pass
    if not result:
        if strip:
            result = "%s_%s@%s" % (shortname, starttime, socket.gethostname())
        else:
            result = ""
    return result


def beamtime_filename(commonblock, starttime, shortname,
                      compath, curpath, locpath,
                      curprefix, curext, comprefix, comext):
    """ code for beamtimeid  datasource

    :param commonblock: commonblock of nxswriter
    :type commonblock: :obj:`dict`<:obj:`str`, `any`>
    :param starttime:  start time
    :type starttime: :obj:`str`
    :param shortname:  short name of beamline
    :type shortname: :obj:`str`
    :param compath:  commission directory
    :type compath: :obj:`str`
    :param curpath:  current directory
    :type curpath: :obj:`str`
    :param locpath:  local directory
    :type locpath: :obj:`str`
    :param curprefix:  current prefix
    :type curprefix: :obj:`str`
    :param curext:  current postfix
    :type curext: :obj:`str`
    :param comprefix:  commission prefix
    :type comprefix: :obj:`str`
    :param comext:  commission postfix
    :type comext: :obj:`str`
    :returns:   beamtime id
    :rtype: :obj:`str`
    """
    return beamtimeid(commonblock,
                      starttime, shortname, compath, curpath, locpath,
                      curprefix, curext, comprefix, comext, strip=False)
