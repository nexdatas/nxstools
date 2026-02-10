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
    import NXSCreatePoolDSFS_test
except Exception:
    from . import NXSCreatePoolDSFS_test


if sys.version_info > (3,):
    unicode = str
    long = int


# test fixture
class NXSCreatePoolDSFS2Test(
        NXSCreatePoolDSFS_test.NXSCreatePoolDSFSTest):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        NXSCreatePoolDSFS_test.NXSCreatePoolDSFSTest.__init__(
            self, methodName)

        self.directory = "my_test_nxs"
        self._dircreated = False
        self.flags = " -d %s" % self.directory

    # test starter
    # \brief Common set up
    def setUp(self):
        NXSCreatePoolDSFS_test.NXSCreatePoolDSFSTest.setUp(self)
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)
            self._dircreated = True

    # test closer
    # \brief Common tear down
    def tearDown(self):
        NXSCreatePoolDSFS_test.NXSCreatePoolDSFSTest.tearDown(self)
        if self._dircreated:
            shutil.rmtree(self.directory)
            self._dircreated = False

    def test_poolds_pdevice_motors_channels_file_prefix(self):
        """ test nxsccreate poolds file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        self._tsv.dp.MotorList = [
            '{'
            '"name": "tst_exp_mot01", '
            '"source" : "tango://haso.desy.de:10000/'
            'motor/oms/10/Position",'
            '"type": "Motor" '
            '}',
            '{'
            '"name": "tst_exp_mot02", '
            '"source" : "tango://haso.desy.de:10000/'
            'pmotor/oms/20/Position",'
            '"type": "PseudoMotor" '
            '}'

        ]
        self._tsv.dp.ExpChannelList = [
            '{'
            '"name": "tst_exp_c01", '
            '"source" : "tango://haso.desy.de:10000/'
            'p00/counter/10/Counts",'
            '"type": "CTExpChannel" '
            '}',
            '{'
            '"name": "tst_exp_adc01", '
            '"source" : "tango://haso.desy.de:10000/'
            'p00/adc/10/Value",'
            '"type": "ZeroDExpChannel" '
            '}',
            '{'
            '"name": "tst_exp_mca01", '
            '"source" : "tango://haso.desy.de:10000/'
            'p00/mca/10/Value",'
            '"type": "OneDExpChannel" '
            '}',
            '{'
            '"name": "tst_exp_det01", '
            '"source" : "tango://haso.desy.de:10000/'
            'p00/det/10/Data",'
            '"type": "TwoDExpChannel" '
            '}',
            '{'
            '"name": "tst_exp_pc01", '
            '"source" : "tango://haso.desy.de:10000/'
            'p00/pcounter/10/Counts",'
            '"type": "PseudoCounter" '
            '}',
        ]
        args = [
            [
                ('nxscreate poolds -x test_ -p %s %s '
                 % (self._tsv.dp.name(), self.flags)).split(),
                ('nxscreate poolds --file-prefix test_ --pool %s %s '
                 % (self._tsv.dp.name(), self.flags)).split()
            ],
            [
                'test_tst_exp_mot01',
                'test_tst_exp_mot02',
                'test_tst_exp_c01',
                'test_tst_exp_adc01',
                'test_tst_exp_mca01',
                'test_tst_exp_det01',
                'test_tst_exp_pc01',
            ],
            [
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_exp_mot01">\n'
                '    <device name="motor/oms/10" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000" group="__CLIENT__"/>\n'
                '    <record name="Position"/>\n'
                '  </datasource>\n'
                '</definition>\n',
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_exp_mot02">\n'
                '    <device name="pmotor/oms/20" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000" group="__CLIENT__"/>\n'
                '    <record name="Position"/>\n'
                '  </datasource>\n'
                '</definition>\n',

                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_exp_c01">\n'
                '    <device name="p00/counter/10" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000" group="__CLIENT__"/>\n'
                '    <record name="Counts"/>\n'
                '  </datasource>\n'
                '</definition>\n',
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_exp_adc01">\n'
                '    <device name="p00/adc/10" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000" group="__CLIENT__"/>\n'
                '    <record name="Value"/>\n'
                '  </datasource>\n'
                '</definition>\n',
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_exp_mca01">\n'
                '    <device name="p00/mca/10" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000" group="__CLIENT__"/>\n'
                '    <record name="Value"/>\n'
                '  </datasource>\n'
                '</definition>\n',
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_exp_det01">\n'
                '    <device name="p00/det/10" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000" group="__CLIENT__"/>\n'
                '    <record name="Data"/>\n'
                '  </datasource>\n'
                '</definition>\n',
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_exp_pc01">\n'
                '    <device name="p00/pcounter/10" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000" group="__CLIENT__"/>\n'
                '    <record name="Counts"/>\n'
                '  </datasource>\n'
                '</definition>\n',
            ],
        ]

        totest = []
        try:
            for cmd in args[0]:
                skip = False
                for ds in args[1]:
                    if self.dsexists(ds):
                        skip = True
                if not skip:
                    for ds in args[1]:
                        totest.append(ds)

                    vl, er = self.runtest(cmd)
                    if er:
                        self.assertTrue(er.startswith("Info: "))
                    else:
                        self.assertEqual('', er)
                    self.assertTrue(vl)

                    for i, ds in enumerate(args[1]):
                        xml = self.getds(ds)
                        self.assertEqual(
                            args[2][i], xml)

                    for ds in args[1]:
                        self.deleteds(ds)
        finally:
            for ds in totest:
                if self.dsexists(ds):
                    self.deleteds(ds)


if __name__ == '__main__':
    unittest.main()
