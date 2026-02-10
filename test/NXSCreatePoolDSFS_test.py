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
import os
import sys
import random
import struct
import binascii

try:
    import tango
except Exception:
    import PyTango as tango

from nxstools import nxscreate

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

try:
    import TestServerSetUp
except ImportError:
    from . import TestServerSetUp


if sys.version_info > (3,):
    unicode = str
    long = int


# if 64-bit machione
IS64BIT = (struct.calcsize("P") == 8)


# test fixture
class NXSCreatePoolDSFSTest(unittest.TestCase):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

        try:
            # random seed
            self.seed = long(binascii.hexlify(os.urandom(16)), 16)
        except NotImplementedError:
            import time
            # random seed
            self.seed = long(time.time() * 256)  # use fractional seconds

        self._rnd = random.Random(self.seed)

        self._bint = "int64" if IS64BIT else "int32"
        self._buint = "uint64" if IS64BIT else "uint32"
        self._bfloat = "float64" if IS64BIT else "float32"

        self.__args = '{"db":"nxsconfig", ' \
                      '"read_default_file":"/etc/my.cnf", "use_unicode":true}'

        # home = expanduser("~")
        db = tango.Database()
        self.host = db.get_db_host().split(".")[0]
        self.port = db.get_db_port()
        self.directory = "."
        self.flags = "-d . "
        self._tsv = TestServerSetUp.TestServerSetUp()

    # sets xmlconfiguration
    # \param xmlc configuration instance
    # \param xml xml configuration string
    def setXML(self, xmlc, xml):
        xmlc.XMLString = xml

    # gets xmlconfiguration
    # \param xmlc configuration instance
    # \returns xml configuration string
    def getXML(self, xmlc):
        return xmlc.XMLString

    # test starter
    # \brief Common set up
    def setUp(self):
        print("\nsetting up...")
        self._tsv.setUp()
        print("SEED = %s" % self.seed)

    # test closer
    # \brief Common tear down
    def tearDown(self):
        self._tsv.tearDown()
        print("tearing down ...")

    def dsexists(self, name):
        return os.path.isfile("%s/%s.ds.xml" % (self.directory, name))

    def cpexists(self, name):
        return os.path.isfile("%s/%s.xml" % (self.directory, name))

    def getds(self, name):
        with open("%s/%s.ds.xml" % (self.directory, name), 'r') as fl:
            xml = fl.read()
        return xml

    def getcp(self, name):
        with open("%s/%s.xml" % (self.directory, name), 'r') as fl:
            xml = fl.read()
        return xml

    def deleteds(self, name):
        os.remove("%s/%s.ds.xml" % (self.directory, name))

    def deletecp(self, name):
        os.remove("%s/%s.xml" % (self.directory, name))

    def runtest(self, argv):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = mystdout = StringIO()
        sys.stderr = mystderr = StringIO()

        old_argv = sys.argv
        sys.argv = argv
        nxscreate.main()
        sys.argv = old_argv

        sys.stdout = old_stdout
        sys.stderr = old_stderr
        vl = mystdout.getvalue()
        er = mystderr.getvalue()
        return vl, er

    def runtestexcept(self, argv, exception):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = mystdout = StringIO()
        sys.stderr = mystderr = StringIO()

        old_argv = sys.argv
        sys.argv = argv
        try:
            error = False
            nxscreate.main()
        except exception:
            error = True
        self.assertEqual(error, True)

        sys.argv = old_argv

        sys.stdout = old_stdout
        sys.stderr = old_stderr
        vl = mystdout.getvalue()
        er = mystderr.getvalue()
        return vl, er

    # Exception tester
    # \param exception expected exception
    # \param method called method
    # \param args list with method arguments
    # \param kwargs dictionary with method arguments
    def myAssertRaise(self, exception, method, *args, **kwargs):
        try:
            error = False
            method(*args, **kwargs)
        except exception:
            error = True
        self.assertEqual(error, True)

    # sets selection configuration
    # \param selectionc configuration instance
    # \param selection selection configuration string
    def setSelection(self, selectionc, selection):
        selectionc.selection = selection

    # gets selectionconfiguration
    # \param selectionc configuration instance
    # \returns selection configuration string
    def getSelection(self, selectionc):
        return selectionc.selection

    def test_poolds_empty(self):
        """ test nxsccreate poolds file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        self._tsv.dp.MotorList = [
        ]
        self._tsv.dp.ExpChannelList = [
        ]
        args = [
            [
                ('nxscreate poolds -p %s %s '
                 % (self._tsv.dp.name(), self.flags)).split(),
                [],
                [],
            ],
            [
                ('nxscreate poolds --pool %s %s '
                 % (self._tsv.dp.name(), self.flags)).split(),
                [],
                [],
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
                            arg[2][i], xml)

                    for ds in arg[1]:
                        self.deleteds(ds)
        finally:
            for ds in totest:
                if self.dsexists(ds):
                    self.deleteds(ds)

    def test_poolds_pdevice_motors(self):
        """ test nxsccreate poolds file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        self._tsv.dp.MotorList = [
            '{'
            '"name": "test_exp_mot_01", '
            '"source" : "tango://haso.desy.de:10000/'
            'motor/omsvme58_exp/10/Position",'
            '"type": "Motor" '
            '}',
            '{'
            '"name": "test_exp_mot_02", '
            '"source" : "tango://haso.desy.de:10000/'
            'motor/omsvme58_exp/20/Position",'
            '"type": "Motor" '
            '}'

        ]
        self._tsv.dp.ExpChannelList = [
        ]
        args = [
            [
                ('nxscreate poolds -p %s %s '
                 % (self._tsv.dp.name(), self.flags)).split(),
                ('nxscreate poolds --pool %s %s '
                 % (self._tsv.dp.name(), self.flags)).split()
            ],
            [
                'test_exp_mot_01',
                'test_exp_mot_02',
            ],
            [
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="test_exp_mot_01">\n'
                '    <device name="motor/omsvme58_exp/10" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000" group="__CLIENT__"/>\n'
                '    <record name="Position"/>\n'
                '  </datasource>\n'
                '</definition>\n',
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="test_exp_mot_02">\n'
                '    <device name="motor/omsvme58_exp/20" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000" group="__CLIENT__"/>\n'
                '    <record name="Position"/>\n'
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

    def test_poolds_pdevice_motors_channels(self):
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
                ('nxscreate poolds -p %s %s '
                 % (self._tsv.dp.name(), self.flags)).split(),
                ('nxscreate poolds --pool %s %s '
                 % (self._tsv.dp.name(), self.flags)).split()
            ],
            [
                'tst_exp_mot01',
                'tst_exp_mot02',
                'tst_exp_c01',
                'tst_exp_adc01',
                'tst_exp_mca01',
                'tst_exp_det01',
                'tst_exp_pc01',
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

    def test_poolds_pdevice_noclientlike(self):
        """ test nxsccreate poolds file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        self._tsv.dp.MotorList = [
            '{'
            '"name": "tst_exp_Mot01", '
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
            '"name": "tst_exp_C01", '
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
                ('nxscreate poolds -t -p %s %s '
                 % (self._tsv.dp.name(), self.flags)).split(),
                ('nxscreate poolds --noclientlike --pool %s %s '
                 % (self._tsv.dp.name(), self.flags)).split()
            ],
            [
                'tst_exp_mot01',
                'tst_exp_mot02',
                'tst_exp_c01',
                'tst_exp_adc01',
                'tst_exp_mca01',
                'tst_exp_det01',
                'tst_exp_pc01',
            ],
            [
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_exp_mot01">\n'
                '    <device name="motor/oms/10" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000"/>\n'
                '    <record name="Position"/>\n'
                '  </datasource>\n'
                '</definition>\n',
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_exp_mot02">\n'
                '    <device name="pmotor/oms/20" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000"/>\n'
                '    <record name="Position"/>\n'
                '  </datasource>\n'
                '</definition>\n',
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_exp_c01">\n'
                '    <device name="p00/counter/10" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000"/>\n'
                '    <record name="Counts"/>\n'
                '  </datasource>\n'
                '</definition>\n',
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_exp_adc01">\n'
                '    <device name="p00/adc/10" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000"/>\n'
                '    <record name="Value"/>\n'
                '  </datasource>\n'
                '</definition>\n',
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_exp_mca01">\n'
                '    <device name="p00/mca/10" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000"/>\n'
                '    <record name="Value"/>\n'
                '  </datasource>\n'
                '</definition>\n',
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_exp_det01">\n'
                '    <device name="p00/det/10" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000"/>\n'
                '    <record name="Data"/>\n'
                '  </datasource>\n'
                '</definition>\n',
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_exp_pc01">\n'
                '    <device name="p00/pcounter/10" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000"/>\n'
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

    def test_poolds_pdevice_motors_nolower(self):
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
            '"name": "tst_exp_Mot02", '
            '"source" : "tango://haso.desy.de:10000/'
            'pmotor/oms/20/Position",'
            '"type": "PseudoMotor" '
            '}'

        ]
        self._tsv.dp.ExpChannelList = [
            '{'
            '"name": "tst_Exp_c01", '
            '"source" : "tango://haso.desy.de:10000/'
            'p00/counter/10/Counts",'
            '"type": "CTExpChannel" '
            '}',
            '{'
            '"name": "tst_Exp_adc01", '
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
                ('nxscreate poolds -n -p %s %s '
                 % (self._tsv.dp.name(), self.flags)).split(),
                ('nxscreate poolds --nolower --pool %s %s '
                 % (self._tsv.dp.name(), self.flags)).split()
            ],
            [
                'tst_exp_mot01',
                'tst_exp_Mot02',
                'tst_Exp_c01',
                'tst_Exp_adc01',
                'tst_exp_mca01',
                'tst_exp_det01',
                'tst_exp_pc01',
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
                '  <datasource type="TANGO" name="tst_exp_Mot02">\n'
                '    <device name="pmotor/oms/20" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000" group="__CLIENT__"/>\n'
                '    <record name="Position"/>\n'
                '  </datasource>\n'
                '</definition>\n',

                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_Exp_c01">\n'
                '    <device name="p00/counter/10" '
                'member="attribute" hostname="haso.desy.de" '
                'port="10000" group="__CLIENT__"/>\n'
                '    <record name="Counts"/>\n'
                '  </datasource>\n'
                '</definition>\n',
                '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                '<definition>\n'
                '  <datasource type="TANGO" name="tst_Exp_adc01">\n'
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

    def test_poolds_pdevice_motors_channels_types(self):
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

        types = [
            "Motor",
            "PseudoMotor",
            "CTExpChannel",
            "ZeroDExpChannel",
            "OneDExpChannel",
            "TwoDExpChannel",
            "PseudoCounter"
        ]
        args = [
            [
                ('nxscreate poolds -p %s %s '
                 % (self._tsv.dp.name(), self.flags)).split(),
                ('nxscreate poolds --pool %s %s '
                 % (self._tsv.dp.name(), self.flags)).split()
            ],
            [
                'tst_exp_mot01',
                'tst_exp_mot02',
                'tst_exp_c01',
                'tst_exp_adc01',
                'tst_exp_mca01',
                'tst_exp_det01',
                'tst_exp_pc01',
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

        for tp in types:
            totest = []
            try:
                for cmd in args[0]:
                    skip = False
                    for ds in args[1]:
                        if self.dsexists(ds):
                            skip = True
                    if not skip:
                        for i, ds in enumerate(args[1]):
                            if tp == types[i]:
                                totest.append(ds)

                        ncmd = list(cmd)
                        ncmd.append(tp)
                        vl, er = self.runtest(ncmd)
                        if er:
                            self.assertTrue(er.startswith("Info: "))
                        else:
                            self.assertEqual('', er)
                        self.assertTrue(vl)

                        for i, ds in enumerate(args[1]):
                            if tp == types[i]:
                                xml = self.getds(ds)
                                self.assertEqual(
                                    args[2][i], xml)
                            else:
                                self.myAssertRaise(Exception, self.getds, ds)

                        for i, ds in enumerate(args[1]):
                            if tp == types[i]:
                                self.deleteds(ds)
            finally:
                for ds in totest:
                    if self.dsexists(ds):
                        self.deleteds(ds)

    def test_poolds_pdevice_motors_channels_names(self):
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
                ('nxscreate poolds -p %s %s '
                 % (self._tsv.dp.name(), self.flags)).split(),
                ('nxscreate poolds --pool %s %s '
                 % (self._tsv.dp.name(), self.flags)).split()
            ],
            [
                'tst_exp_mot01',
                'tst_exp_mot02',
                'tst_exp_c01',
                'tst_exp_adc01',
                'tst_exp_mca01',
                'tst_exp_det01',
                'tst_exp_pc01',
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

        for nm in args[1]:
            totest = []
            try:
                for cmd in args[0]:
                    skip = False
                    for ds in args[1]:
                        if self.dsexists(ds):
                            skip = True
                    if not skip:
                        for i, ds in enumerate(args[1]):
                            if nm == args[1][i]:
                                totest.append(ds)

                        ncmd = list(cmd)
                        ncmd.append(nm)
                        vl, er = self.runtest(ncmd)
                        if er:
                            self.assertTrue(er.startswith("Info: "))
                        else:
                            self.assertEqual('', er)
                        self.assertTrue(vl)

                        for i, ds in enumerate(args[1]):
                            if nm == args[1][i]:
                                xml = self.getds(ds)
                                self.assertEqual(
                                    args[2][i], xml)
                            else:
                                self.myAssertRaise(Exception, self.getds, ds)

                        for i, ds in enumerate(args[1]):
                            if nm == args[1][i]:
                                self.deleteds(ds)
            finally:
                for ds in totest:
                    if self.dsexists(ds):
                        self.deleteds(ds)


if __name__ == '__main__':
    unittest.main()
