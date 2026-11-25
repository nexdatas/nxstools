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

"""  pyeval helper functions for mssar and msnsar """

import pickle
import json


def mssarenv(msenv, varname):
    """ code for mssar_env  datasource

    :param msenv: sardana env
    :type msenv: :obj:`str`
    :param varname:  env variable name
    :type varname: :obj:`str`
    :returns: sardana variable value
    :rtype: :obj:`any`
    """
    msenv = pickle.loads(msenv, encoding='latin1')['new']

    return msenv[varname]


def msnsarenv(msenv, varname):
    """ code for msnsar_env  datasource

    :param msenv: sardana env
    :type msenv: :obj:`str`
    :param varname:  env variable name
    :type varname: :obj:`str`
    :returns: sardana variable value
    :rtype: :obj:`any`
    """
    varname = json.loads(varname)

    msenv = pickle.loads(msenv, encoding='latin1')['new']

    result = msenv
    for var in varname:
        result = result[var]
    return result
