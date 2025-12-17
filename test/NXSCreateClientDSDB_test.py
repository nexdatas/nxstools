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
# \package test nexdatas
# \file XMLConfigurator_test.py
# unittests for field Tags running Tango Server
#
import unittest
# import os
import sys
# import random
# import struct
# import binascii
import time
# import threading
try:
    import tango
except Exception:
    import PyTango as tango
from os.path import expanduser
# import json
# from nxstools import nxscreate

try:
    import NXSCreateClientDSFS_test
except Exception:
    from . import NXSCreateClientDSFS_test

try:
    import ServerSetUp
except ImportError:
    from . import ServerSetUp


if sys.version_info > (3,):
    unicode = str
    long = int


# test fixture
class NXSCreateClientDSDBTest(
        NXSCreateClientDSFS_test.NXSCreateClientDSFSTest):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        NXSCreateClientDSFS_test.NXSCreateClientDSFSTest.__init__(
            self, methodName)

        self.__args = '{"db":"nxsconfig", ' \
                      '"read_default_file":"/etc/my.cnf", "use_unicode":true}'

        home = expanduser("~")
        self.__args2 = '{"db":"nxsconfig", ' \
                       '"read_default_file":"%s/.my.cnf", ' \
                       '"use_unicode":true}' % home
        self._sv = ServerSetUp.ServerSetUp()
        self._proxy = None
        self.flags = " --database --server testp09/testmcs/testr228"

    # opens config server
    # \param args connection arguments
    # \returns NXSConfigServer instance
    def openConfig(self, args):

        found = False
        cnt = 0
        while not found and cnt < 100:
            try:
                sys.stdout.write(".")
                xmlc = tango.DeviceProxy(
                    self._sv.new_device_info_writer.name)
                time.sleep(0.1)
                if xmlc.state() == tango.DevState.ON:
                    found = True
                found = True
            except Exception as e:
                print("%s %s" % (self._sv.new_device_info_writer.name, e))
                found = False
            except Exception:
                found = False

            cnt += 1

        if not found:
            raise Exception(
                "Cannot connect to %s"
                % self._sv.new_device_info_writer.name)

        if xmlc.state() == tango.DevState.ON:
            xmlc.JSONSettings = args
            xmlc.Open()
        version = xmlc.version
        vv = version.split('.')
        self.revision = long(vv[-1])
        self.version = ".".join(vv[0:3])
        self.label = ".".join(vv[3:-1])

        self.assertEqual(xmlc.state(), tango.DevState.OPEN)
        return xmlc

    # closes opens config server
    # \param xmlc XMLConfigurator instance
    def closeConfig(self):
        self.assertEqual(self._proxy.state(), tango.DevState.OPEN)

        self._proxy.Close()
        self.assertEqual(self._proxy.state(), tango.DevState.ON)

    # test starter
    # \brief Common set up
    def setUp(self):
        NXSCreateClientDSFS_test.NXSCreateClientDSFSTest.setUp(self)
        self._sv.setUp()
        self.openConf()

    # test closer
    # \brief Common tear down
    def tearDown(self):
        NXSCreateClientDSFS_test.NXSCreateClientDSFSTest.tearDown(self)
        self.closeConfig()
        self._sv.tearDown()

    def openConf(self):
        try:
            el = self.openConfig(self.__args)
        except Exception:
            el = self.openConfig(self.__args2)
        self._proxy = el

    def dsexists(self, name):
        avds = self._proxy.availableDataSources()
        return name in avds

    def cpexists(self, name):
        avds = self._proxy.availableComponents()
        return name in avds

    def getds(self, name):
        avds = self._proxy.availableDataSources()
        self.assertTrue(name in avds)
        xmls = self._proxy.datasources([name])
        self.assertEqual(len(xmls), 1)
        return xmls[0]

    def getcp(self, name):
        avcp = self._proxy.availableComponents()
        self.assertTrue(name in avcp)
        xmls = self._proxy.components([name])
        self.assertEqual(len(xmls), 1)
        return xmls[0]

    def deleteds(self, name):
        self._proxy.deleteDataSource(name)

    def deletecp(self, name):
        self._proxy.deleteComponent(name)


if __name__ == '__main__':
    unittest.main()
