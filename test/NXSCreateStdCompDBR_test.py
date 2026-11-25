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
try:
    import tango
except Exception:
    import PyTango as tango
from os.path import expanduser

try:
    import NXSCreateStdCompDB_test
except Exception:
    from . import NXSCreateStdCompDB_test

try:
    import ServerSetUp
except ImportError:
    from . import ServerSetUp


# test fixture
class NXSCreateStdCompDBRTest(
        NXSCreateStdCompDB_test.NXSCreateStdCompDBTest):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        NXSCreateStdCompDB_test.NXSCreateStdCompDBTest.__init__(
            self, methodName)

        self.__args = '{"db":"nxsconfig", ' \
                      '"read_default_file":"/etc/my.cnf", "use_unicode":true}'

        home = expanduser("~")
        self.__args2 = '{"db":"nxsconfig", ' \
                       '"read_default_file":"%s/.my.cnf", ' \
                       '"use_unicode":true}' % home
        self._sv = ServerSetUp.ServerSetUp()
        self._sv2 = ServerSetUp.ServerSetUp(
            instance="AMCSTEST2",
            dvname="aatestp09/testmcs2/testr228")
        self._proxy = None
        self._proxy2 = None
        self.flags = " --database --server aatestp09/testmcs2/testr228 "
        self.device = 'aatestp09/testmcs2/testr228'

    def openConf2(self):
        try:
            el = self.openConfig(self.__args, self._sv2)
        except Exception:
            el = self.openConfig(self.__args2, self._sv2)
        self._proxy2 = el

    # closes opens config server
    # \param xmlc XMLConfigurator instance
    def closeConfig2(self):
        self.assertEqual(self._proxy2.state(), tango.DevState.OPEN)

        self._proxy2.Close()
        self.assertEqual(self._proxy2.state(), tango.DevState.ON)

    # test starter
    # \brief Common set up
    def setUp(self):
        self._sv2.setUp()
        self.openConf2()
        NXSCreateStdCompDB_test.NXSCreateStdCompDBTest.setUp(self)

    # test closer
    # \brief Common tear down
    def tearDown(self):
        NXSCreateStdCompDB_test.NXSCreateStdCompDBTest.tearDown(self)
        self.closeConfig2()
        self._sv2.tearDown()


if __name__ == '__main__':
    unittest.main()
