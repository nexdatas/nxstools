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

import json


def vmap(commonblock, name, fieldname,
         triggermode,
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
    :param attrname: attribute name
    :type attrname: :obj:`str`
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
    step = commonblock["__counter__"] - 1
    path = ""
    if filename:
        sfname = (filename).split("/")
        path = sfname[-1].split(".")[0] + "/"
        if shortdetpath is None and \
                len(sfname) > 1 and sfname[-2] == path[:-1]:
            path = ""
        elif shortdetpath:
            path = ""
    fpattern = pilcfileprefix.split("/")[-1]
    path += '%s/%s' % (name, fpattern)
    return json.dumps(
        # {"target": "%s_%05d_00000.nxs:/entry/data/%s"
        {"target": "%s_%05d.nxs:/entry/data/%s"
         % (path, step, fieldname), "key": step, "shape": [1, nbtriggers]})
