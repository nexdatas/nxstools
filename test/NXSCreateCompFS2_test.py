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
    import NXSCreateCompFS_test
except Exception:
    from . import NXSCreateCompFS_test


if sys.version_info > (3,):
    unicode = str
    long = int


# test fixture
class NXSCreateCompFS2Test(
        NXSCreateCompFS_test.NXSCreateCompFSTest):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        NXSCreateCompFS_test.NXSCreateCompFSTest.__init__(
            self, methodName)

        self.directory = "my_test_nxs"
        self._dircreated = False
        self.flags = " -d %s" % self.directory

    # test starter
    # \brief Common set up
    def setUp(self):
        NXSCreateCompFS_test.NXSCreateCompFSTest.setUp(self)
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)
            self._dircreated = True

    # test closer
    # \brief Common tear down
    def tearDown(self):
        NXSCreateCompFS_test.NXSCreateCompFSTest.tearDown(self)
        if self._dircreated:
            shutil.rmtree(self.directory)
            self._dircreated = False

    def test_comp_first_last_file_prefix(self):
        """ test nxsccreate comp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate comp -v testmotor '
                 '-s  my_exp_mot  -l 3 %s -x my_ '
                 % self.flags).split(),
                ['my_testmotor01',
                 'my_testmotor02',
                 'my_testmotor03'],
                [
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    '<definition>\n'
                    '  <group name="$var.entryname#\'scan\'$var.serialno"'
                    ' type="NXentry">\n'
                    '    <group name="instrument" type="NXinstrument">\n'
                    '      <group name="collection" type="NXcollection">\n'
                    '        <field name="my_exp_mot01" type="NX_FLOAT">'
                    '$datasources.my_exp_mot01<strategy mode="STEP"/>'
                    '</field>\n'
                    '      </group>\n'
                    '    </group>\n'
                    '  </group>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    '<definition>\n'
                    '  <group name="$var.entryname#\'scan\'$var.serialno"'
                    ' type="NXentry">\n'
                    '    <group name="instrument" type="NXinstrument">\n'
                    '      <group name="collection" type="NXcollection">\n'
                    '        <field name="my_exp_mot02" type="NX_FLOAT">'
                    '$datasources.my_exp_mot02<strategy mode="STEP"/>'
                    '</field>\n'
                    '      </group>\n'
                    '    </group>\n'
                    '  </group>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    '<definition>\n'
                    '  <group name="$var.entryname#\'scan\'$var.serialno"'
                    ' type="NXentry">\n'
                    '    <group name="instrument" type="NXinstrument">\n'
                    '      <group name="collection" type="NXcollection">\n'
                    '        <field name="my_exp_mot03" type="NX_FLOAT">'
                    '$datasources.my_exp_mot03<strategy mode="STEP"/>'
                    '</field>\n'
                    '      </group>\n'
                    '    </group>\n'
                    '  </group>\n'
                    '</definition>\n',
                ],
            ],
            [
                ('nxscreate comp -v testvm  --file-prefix test_exp_ '
                 ' -s  test_exp_mot -f 2 -l 3 %s' % self.flags).split(),
                ['test_exp_testvm02',
                 'test_exp_testvm03'],
                [
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    '<definition>\n'
                    '  <group name="$var.entryname#\'scan\'$var.serialno"'
                    ' type="NXentry">\n'
                    '    <group name="instrument" type="NXinstrument">\n'
                    '      <group name="collection" type="NXcollection">\n'
                    '        <field name="test_exp_mot02" type="NX_FLOAT">'
                    '$datasources.test_exp_mot02<strategy mode="STEP"/>'
                    '</field>\n'
                    '      </group>\n'
                    '    </group>\n'
                    '  </group>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    '<definition>\n'
                    '  <group name="$var.entryname#\'scan\'$var.serialno"'
                    ' type="NXentry">\n'
                    '    <group name="instrument" type="NXinstrument">\n'
                    '      <group name="collection" type="NXcollection">\n'
                    '        <field name="test_exp_mot03" type="NX_FLOAT">'
                    '$datasources.test_exp_mot03<strategy mode="STEP"/>'
                    '</field>\n'
                    '      </group>\n'
                    '    </group>\n'
                    '  </group>\n'
                    '</definition>\n',
                ],
            ],
        ]

        totest = []
        try:
            for arg in args:
                skip = False
                for cp in arg[1]:
                    if self.cpexists(cp):
                        skip = True
                if not skip:
                    for cp in arg[1]:
                        totest.append(cp)

                    vl, er = self.runtest(arg[0])

                    if er:
                        self.assertTrue(er.startswith("Info: "))
                    else:
                        self.assertEqual('', er)
                    self.assertTrue(vl)

                    for i, cp in enumerate(arg[1]):
                        xml = self.getcp(cp)
                        self.assertEqual(
                            arg[2][i], xml)

                    for cp in arg[1]:
                        self.deletecp(cp)
        finally:
            for cp in totest:
                if self.cpexists(cp):
                    self.deletecp(cp)

    def ttest_comp_file_prefix(self):
        """ test nxsccreate comp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate comp --device test/motor/ -x my_ '
                 '--datasource-prefix exp_mot -a Data  --last 3 %s'
                 % self.flags).split(),
                ['my_exp_mot01',
                 'my_exp_mot02',
                 'my_exp_mot03'],
                [
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    ''
                    '<definition>\n'
                    '  <datasource name="exp_mot01" type="TANGO">\n'
                    '    <device hostname="%s" member="attribute"'
                    ' name="test/motor/01" port="%s"/>\n'
                    '    <record name="Data"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    ''
                    '<definition>\n'
                    '  <datasource name="exp_mot02" type="TANGO">\n'
                    '    <device hostname="%s" member="attribute"'
                    ' name="test/motor/02" port="%s"/>\n'
                    '    <record name="Data"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    ''
                    '<definition>\n'
                    '  <datasource name="exp_mot03" type="TANGO">\n'
                    '    <device hostname="%s" member="attribute"'
                    ' name="test/motor/03" port="%s"/>\n'
                    '    <record name="Data"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                ],
            ],
            [
                ('nxscreate comp --device test/vm/ --file-prefix test_exp_ '
                 ' --datasource-prefix mot -a Voltage '
                 '--first 2 --last 3 %s'
                 % self.flags).split(),
                ['test_exp_mot02',
                 'test_exp_mot03'],
                [
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    ''
                    '<definition>\n'
                    '  <datasource name="mot02" type="TANGO">\n'
                    '    <device hostname="%s" member="attribute"'
                    ' name="test/vm/02" port="%s"/>\n'
                    '    <record name="Voltage"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    ''
                    '<definition>\n'
                    '  <datasource name="mot03" type="TANGO">\n'
                    '    <device hostname="%s" member="attribute"'
                    ' name="test/vm/03" port="%s"/>\n'
                    '    <record name="Voltage"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
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

                    if er:
                        self.assertTrue(er.startswith("Info: "))
                    else:
                        self.assertEqual('', er)
                    self.assertTrue(vl)

                    for i, ds in enumerate(arg[1]):
                        xml = self.getds(ds)
                        self.assertEqual(
                            arg[2][i] % (self.host, self.port), xml)

                    for ds in arg[1]:
                        self.deleteds(ds)
        finally:
            for ds in totest:
                if self.dsexists(ds):
                    self.deleteds(ds)


if __name__ == '__main__':
    unittest.main()
