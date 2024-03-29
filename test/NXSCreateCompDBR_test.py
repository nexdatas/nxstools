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
import sys
from os.path import expanduser

try:
    import NXSCreateCompDB_test
except Exception:
    from . import NXSCreateCompDB_test

try:
    import ServerSetUp
except ImportError:
    from . import ServerSetUp


if sys.version_info > (3,):
    unicode = str
    long = int


# test fixture
class NXSCreateCompDBRTest(
        NXSCreateCompDB_test.NXSCreateCompDBTest):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        NXSCreateCompDB_test.NXSCreateCompDBTest.__init__(
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
        self.flags = " --database --server testp09/testmcs/testr228 "

    # test starter
    # \brief Common set up
    def setUp(self):
        self._sv2.setUp()
        NXSCreateCompDB_test.NXSCreateCompDBTest.setUp(self)

    # test closer
    # \brief Common tear down
    def tearDown(self):
        NXSCreateCompDB_test.NXSCreateCompDBTest.tearDown(self)
        self._sv2.tearDown()


if __name__ == '__main__':
    unittest.main()
