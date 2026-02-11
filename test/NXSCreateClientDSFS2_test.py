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
import shutil
import os


try:
    import NXSCreateClientDSFS_test
except Exception:
    from . import NXSCreateClientDSFS_test


if sys.version_info > (3,):
    unicode = str
    long = int


# test fixture
class NXSCreateClientDSFS2Test(
        NXSCreateClientDSFS_test.NXSCreateClientDSFSTest):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        NXSCreateClientDSFS_test.NXSCreateClientDSFSTest.__init__(
            self, methodName)

        self.directory = "my_test_nxs"
        self._dircreated = False
        self.flags = " -d %s" % self.directory

    # test starter
    # \brief Common set up
    def setUp(self):
        NXSCreateClientDSFS_test.NXSCreateClientDSFSTest.setUp(self)
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)
            self._dircreated = True

    # test closer
    # \brief Common tear down
    def tearDown(self):
        NXSCreateClientDSFS_test.NXSCreateClientDSFSTest.tearDown(self)
        if self._dircreated:
            shutil.rmtree(self.directory)
            self._dircreated = False

    def test_clientds_file_prefix(self):
        """ test nxsccreate clientds file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate clientds -x test_ -v exp_vc  -f3 -l5 %s'
                 % self.flags).split(),
                ['test_exp_vc03',
                 'test_exp_vc04',
                 'test_exp_vc05'],
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="exp_vc03">
    <record name="exp_vc03"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="exp_vc04">
    <record name="exp_vc04"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="exp_vc05">
    <record name="exp_vc05"/>
  </datasource>
</definition>
""",
                ],
            ],
            [
                ('nxscreate clientds --device dd '
                 '--file-prefix test_exp_ '
                 '--first 3 --last 4 %s'
                 % self.flags).split(),
                ['test_exp_dd03',
                 'test_exp_dd04'],
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="dd03">
    <record name="dd03"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="dd04">
    <record name="dd04"/>
  </datasource>
</definition>
""",
                ],
            ],
        ]

        totest = []
        try:
            for arg in args:
                skip = False
                for ds in arg[1]:
                    if self.dsexists(ds):
                        skip = True
                if not skip:
                    for ds in arg[1]:
                        totest.append(ds)

                    vl, er = self.runtest(arg[0])

                    self.assertEqual('', er)
                    self.assertTrue(vl)

                    for i, ds in enumerate(arg[1]):
                        xml = self.getds(ds)
                        self.assertEqual(arg[2][i], xml)

                    for ds in arg[1]:
                        self.deleteds(ds)
        finally:
            pass
            for ds in totest:
                if self.dsexists(ds):
                    self.deleteds(ds)


if __name__ == '__main__':
    unittest.main()
