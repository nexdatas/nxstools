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
    import NXSCreateOnlineDSFS_test
except Exception:
    from . import NXSCreateOnlineDSFS_test


if sys.version_info > (3,):
    unicode = str
    long = int


# test fixture
class NXSCreateOnlineDSFS2Test(
        NXSCreateOnlineDSFS_test.NXSCreateOnlineDSFSTest):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        NXSCreateOnlineDSFS_test.NXSCreateOnlineDSFSTest.__init__(
            self, methodName)

        self.directory = "my_test_nxs"
        self._dircreated = False
        self.flags = " -d %s" % self.directory

    # test starter
    # \brief Common set up
    def setUp(self):
        NXSCreateOnlineDSFS_test.NXSCreateOnlineDSFSTest.setUp(self)
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)
            self._dircreated = True

    # test closer
    # \brief Common tear down
    def tearDown(self):
        NXSCreateOnlineDSFS_test.NXSCreateOnlineDSFSTest.tearDown(self)
        if self._dircreated:
            shutil.rmtree(self.directory)
            self._dircreated = False

    def test_onlineds_stepping_motor_file_prefix(self):
        """ test nxsccreate onlineds file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname = '%s/%s%s.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml = """<?xml version="1.0"?>
<hw>
<device>
 <name>my_exp_mot01</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>p09/motor/exp.01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
<device>
 <name>my_exp_mot02</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>p09/motor/exp.02</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>2</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
<device>
 <name>my_exp_mot03</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>p09/motor/exp.03</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>3</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
</hw>
"""

        args = [
            [
                ('nxscreate onlineds -x test_ %s %s '
                 % (fname, self.flags)).split(),
                ['test_my_exp_mot01',
                 'test_my_exp_mot02',
                 'test_my_exp_mot03'],
                [
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO" name="my_exp_mot01">\n'
                    '    <device name="p09/motor/exp.01"'
                    ' member="attribute" hostname="haso000" '
                    'port="10000" group="__CLIENT__"/>\n'
                    '    <record name="Position"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO" name="my_exp_mot02">\n'
                    '    <device name="p09/motor/exp.02"'
                    ' member="attribute" hostname="haso000" '
                    'port="10000" group="__CLIENT__"/>\n'
                    '    <record name="Position"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO" name="my_exp_mot03">\n'
                    '    <device name="p09/motor/exp.03"'
                    ' member="attribute" hostname="haso000" '
                    'port="10000" group="__CLIENT__"/>\n'
                    '    <record name="Position"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                ],
            ],
            [
                ('nxscreate onlineds --file-prefix tst_ %s %s '
                 % (fname, self.flags)).split(),
                ['tst_my_exp_mot01',
                 'tst_my_exp_mot02',
                 'tst_my_exp_mot03'],
                [
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO" name="my_exp_mot01">\n'
                    '    <device name="p09/motor/exp.01"'
                    ' member="attribute" hostname="haso000" '
                    'port="10000" group="__CLIENT__"/>\n'
                    '    <record name="Position"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO" name="my_exp_mot02">\n'
                    '    <device name="p09/motor/exp.02"'
                    ' member="attribute" hostname="haso000" '
                    'port="10000" group="__CLIENT__"/>\n'
                    '    <record name="Position"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO" name="my_exp_mot03">\n'
                    '    <device name="p09/motor/exp.03"'
                    ' member="attribute" hostname="haso000" '
                    'port="10000" group="__CLIENT__"/>\n'
                    '    <record name="Position"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                ],
            ],
        ]

        totest = []
        if os.path.isfile(fname):
            raise Exception("Test file %s exists" % fname)
        with open(fname, "w") as fl:
            fl.write(xml)
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
                        self.assertTrue(er.startswith(
                            "Info"))
                    else:
                        self.assertEqual('', er)
                    self.assertTrue(vl)

                    for i, ds in enumerate(arg[1]):
                        xml = self.getds(ds)
                        self.assertEqual(
                            arg[2][i], xml)

                    for ds in arg[1]:
                        self.deleteds(ds)
        finally:
            os.remove(fname)
            for ds in totest:
                if self.dsexists(ds):
                    self.deleteds(ds)


if __name__ == '__main__':
    unittest.main()
