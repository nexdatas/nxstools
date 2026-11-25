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
# \file XMLConfiguratorTest.py
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


# if 64-bit machione
IS64BIT = (struct.calcsize("P") == 8)


# test fixture
class NXSCreateCompareTest(unittest.TestCase):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

        try:
            # random seed
            self.seed = int(binascii.hexlify(os.urandom(16)), 16)
        except NotImplementedError:
            import time
            # random seed
            self.seed = int(time.time() * 256)  # use fractional seconds

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
        self.flags = ""

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
        print("SEED = %s" % self.seed)

    # test closer
    # \brief Common tear down
    def tearDown(self):
        print("tearing down ...")

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

    def myAssertDict(self, dct, dct2):
        self.assertTrue(isinstance(dct, dict))
        self.assertTrue(isinstance(dct2, dict))
        self.assertEqual(
            len(list(dct.keys())), len(list(dct2.keys())))
        for k, v in dct.items():
            self.assertTrue(k in dct2.keys())
            if isinstance(v, dict):
                self.myAssertDict(v, dct2[k])
            else:
                self.assertEqual(v, dct2[k])

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

    def test_compare_self(self):
        """ test nxsccreate compare file system
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
        commands = [('nxscreate compare %s %s %s'
                     % (fname, fname, self.flags)).split()]

        if os.path.isfile(fname):
            raise Exception("Test file %s exists" % fname)
        with open(fname, "w") as fl:
            fl.write(xml)
        try:

            for cmd in commands:
                vl, er = self.runtest(cmd)
                lines = vl.split("\n")
                self.assertEqual(len(lines), 14)
                self.assertTrue(lines[0].startswith("Comparing:"))
                self.assertEqual(lines[1], "")
                self.assertEqual(lines[3], "")
                self.assertEqual(lines[5], "")
                self.assertEqual(lines[7], "")
                self.assertEqual(lines[9], "")
                self.assertEqual(lines[11], "")
                self.assertEqual(lines[13], "")
                self.assertTrue(
                    lines[2].startswith(
                        "Additional devices in '%s' {alias: [name]} :"
                        % fname))
                self.assertTrue(
                    lines[6].startswith(
                        "Additional devices in '%s' {alias: [name]} :"
                        % fname))
                self.assertTrue(
                    lines[10].startswith(
                        "Diffrences in the common part:"))

                self.assertEqual(lines[4], "{}")
                self.assertEqual(lines[8], "{}")
                self.assertEqual(lines[12], "{}")

                # print(vl)
                # print(er)
        finally:
            os.remove(fname)

    def test_compare_diff(self):
        """ test nxsccreate compare file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname1 = '%s/%s%s_1.xml' % (
            os.getcwd(), self.__class__.__name__, fun)
        fname2 = '%s/%s%s_2.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml1 = """<?xml version="1.0"?>
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
 <sardananame>mot01</sardananame>
</device>
<device>
 <name>my_exp_mot02</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>p09/motor/exp.04</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>2</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
<device>
 <name>my_exp_mot03</name>
 <type>motor</type>
 <module>oms58</module>
 <device>p09/motor/exp.03</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>3</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
<device>
    <name>my_test_vfcadc</name>
    <type>type_tango</type>
    <module>vfcadc</module>
    <device>mytest/vfcadc/ct</device>
    <control>tango</control>
    <hostname>haso000:10000</hostname>
</device>
</hw>
"""
        xml2 = """<?xml version="1.0"?>
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
 <sardananame>mot_01</sardananame>
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
<device>
    <name>my_test_tip850dac</name>
    <type>type_tango</type>
    <module>tip850dac</module>
    <device>mytest/tip850dac/ct</device>
    <control>tango</control>
    <hostname>haso000:10000</hostname>
</device>
<device>
    <name>my_test_tip830</name>
    <type>type_tango</type>
    <module>tip830</module>
    <device>mytest/tip830/ct</device>
    <control>tango</control>
    <hostname>haso000:10000</hostname>
</device>
<device>
    <name>my_test_tip850adc</name>
    <type>type_tango</type>
    <module>tip850adc</module>
    <device>mytest/tip850adc/ct</device>
    <control>tango</control>
    <hostname>haso000:10000</hostname>
</device>
</hw>
"""
        commands = [('nxscreate compare %s %s %s'
                     % (fname1, fname2, self.flags)).split()]

        if os.path.isfile(fname1):
            raise Exception("Test file %s exists" % fname1)
        elif os.path.isfile(fname2):
            raise Exception("Test file %s exists" % fname2)
        with open(fname1, "w") as fl:
            fl.write(xml1)
        with open(fname2, "w") as fl:
            fl.write(xml2)
        try:

            for cmd in commands:
                vl, er = self.runtest(cmd)
                lines = vl.split("\n\n")
                # print(vl)
                # print(er)
                self.assertEqual(len(lines), 7)
                self.assertTrue(lines[0].startswith("Comparing:"))
                self.assertTrue(
                    lines[1].startswith(
                        "Additional devices in '%s' {alias: [name]} :"
                        % fname1))
                self.assertTrue(
                    lines[3].startswith(
                        "Additional devices in '%s' {alias: [name]} :"
                        % fname2))
                self.assertTrue(
                    lines[5].startswith(
                        "Diffrences in the common part:"))

                first = eval(lines[2])
                second = eval(lines[4])
                common = eval(lines[6])
                self.myAssertDict(
                    first,
                    {'mot01': ['my_exp_mot01'],
                     'my_test_vfcadc': ['my_test_vfcadc']}
                )
                self.myAssertDict(
                    second,
                    {'mot_01': ['my_exp_mot01'],
                     'my_test_tip830': ['my_test_tip830'],
                     'my_test_tip850adc': ['my_test_tip850adc'],
                     'my_test_tip850dac': ['my_test_tip850dac']}
                )
                self.myAssertDict(
                    common,
                    {
                        'my_exp_mot03': [
                            {'dtype': ('motor', 'stepping_motor')}
                        ],
                        'my_exp_mot02': [
                            {
                                'tdevice':
                                ('p09/motor/exp.04', 'p09/motor/exp.02')
                            }
                        ],
                    }
                )

        finally:
            os.remove(fname1)
            os.remove(fname2)

    def test_compare_lower(self):
        """ test nxsccreate compare file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname1 = '%s/%s%s_1.xml' % (
            os.getcwd(), self.__class__.__name__, fun)
        fname2 = '%s/%s%s_2.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml1 = """<?xml version="1.0"?>
<hw>
<device>
 <name>My_exp_mot01</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>P09/motor/exp.01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
 <sardananame>mot01</sardananame>
</device>
<device>
 <name>my_exp_mot02</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>P09/motor/exp.04</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>2</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
<device>
 <name>my_exp_mot03</name>
 <type>motor</type>
 <module>oms58</module>
 <device>p09/motor/exp.03</device>
 <control>tango</control>
 <hostname>Haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>3</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
<device>
    <name>my_test_vfcadc</name>
    <type>type_tango</type>
    <module>vfcadc</module>
    <device>mytest/vfcadc/ct</device>
    <control>tango</control>
    <hostname>haso000:10000</hostname>
</device>
</hw>
"""
        xml2 = """<?xml version="1.0"?>
<hw>
<device>
 <name>my_exp_mot_01</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>p09/Motor/exp.01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
 <sardananame>mot01</sardananame>
</device>
<device>
 <name>my_exp_mot02</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>p09/motor/Exp.02</device>
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
<device>
    <name>my_test_tip850dac</name>
    <type>type_tango</type>
    <module>tip850dac</module>
    <device>mytest/tip850dac/ct</device>
    <control>tango</control>
    <hostname>haso000:10000</hostname>
</device>
<device>
    <name>my_test_tip830</name>
    <type>type_tango</type>
    <module>tip830</module>
    <device>Mytest/tip830/ct</device>
    <control>tango</control>
    <hostname>haso000:10000</hostname>
</device>
<device>
    <name>My_test_tip850adc</name>
    <type>type_tango</type>
    <module>tip850adc</module>
    <device>mytest/tip850adc/ct</device>
    <control>tango</control>
    <hostname>haso000:10000</hostname>
</device>
</hw>
"""
        commands = [('nxscreate compare %s %s %s'
                     % (fname1, fname2, self.flags)).split()]

        if os.path.isfile(fname1):
            raise Exception("Test file %s exists" % fname1)
        elif os.path.isfile(fname2):
            raise Exception("Test file %s exists" % fname2)
        with open(fname1, "w") as fl:
            fl.write(xml1)
        with open(fname2, "w") as fl:
            fl.write(xml2)
        try:

            for cmd in commands:
                vl, er = self.runtest(cmd)
                lines = vl.split("\n\n")
                # print(vl)
                # print(er)
                self.assertEqual(len(lines), 7)
                self.assertTrue(lines[0].startswith("Comparing:"))
                self.assertTrue(
                    lines[1].startswith(
                        "Additional devices in '%s' {alias: [name]} :"
                        % fname1))
                self.assertTrue(
                    lines[3].startswith(
                        "Additional devices in '%s' {alias: [name]} :"
                        % fname2))
                self.assertTrue(
                    lines[5].startswith(
                        "Diffrences in the common part:"))

                first = eval(lines[2])
                second = eval(lines[4])
                common = eval(lines[6])
                self.myAssertDict(
                    first,
                    {'my_test_vfcadc': ['my_test_vfcadc']})
                self.myAssertDict(
                    second,
                    {'my_test_tip830': ['my_test_tip830'],
                     'my_test_tip850adc': ['my_test_tip850adc'],
                     'my_test_tip850dac': ['my_test_tip850dac']})
                self.myAssertDict(
                    common,
                    {'mot01': [{'name': ('my_exp_mot01', 'my_exp_mot_01'),
                                'tdevice':
                                ('P09/motor/exp.01', 'p09/Motor/exp.01')}],
                     'my_exp_mot02':
                     [{'tdevice': ('P09/motor/exp.04', 'p09/motor/Exp.02')}],
                     'my_exp_mot03':
                     [{'dtype': ('motor', 'stepping_motor'),
                       'hostname': ('Haso000:10000', 'haso000:10000')}]}
                )

        finally:
            os.remove(fname1)
            os.remove(fname2)

    def test_compare_nolower(self):
        """ test nxsccreate compare file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname1 = '%s/%s%s_1.xml' % (
            os.getcwd(), self.__class__.__name__, fun)
        fname2 = '%s/%s%s_2.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml1 = """<?xml version="1.0"?>
<hw>
<device>
 <name>My_exp_mot01</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>P09/motor/exp.01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
 <sardananame>mot01</sardananame>
</device>
<device>
 <name>my_exp_mot02</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>P09/motor/exp.04</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>2</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
<device>
 <name>my_exp_mot03</name>
 <type>motor</type>
 <module>oms58</module>
 <device>p09/motor/exp.03</device>
 <control>tango</control>
 <hostname>Haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>3</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
<device>
    <name>my_test_vfcadc</name>
    <type>type_tango</type>
    <module>vfcadc</module>
    <device>mytest/vfcadc/ct</device>
    <control>tango</control>
    <hostname>haso000:10000</hostname>
</device>
</hw>
"""
        xml2 = """<?xml version="1.0"?>
<hw>
<device>
 <name>my_exp_mot01</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>p09/Motor/exp.01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
 <sardananame>mot_01</sardananame>
</device>
<device>
 <name>my_exp_mot02</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>p09/motor/Exp.02</device>
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
<device>
    <name>my_test_tip850dac</name>
    <type>type_tango</type>
    <module>tip850dac</module>
    <device>mytest/tip850dac/ct</device>
    <control>tango</control>
    <hostname>haso000:10000</hostname>
</device>
<device>
    <name>my_test_tip830</name>
    <type>type_tango</type>
    <module>tip830</module>
    <device>Mytest/tip830/ct</device>
    <control>tango</control>
    <hostname>haso000:10000</hostname>
</device>
<device>
    <name>My_test_tip850adc</name>
    <type>type_tango</type>
    <module>tip850adc</module>
    <device>mytest/tip850adc/ct</device>
    <control>tango</control>
    <hostname>haso000:10000</hostname>
</device>
</hw>
"""
        commands = [
            ('nxscreate compare -n %s %s %s'
             % (fname1, fname2, self.flags)).split(),
            ('nxscreate compare --nolower %s %s %s'
             % (fname1, fname2, self.flags)).split()
        ]

        if os.path.isfile(fname1):
            raise Exception("Test file %s exists" % fname1)
        elif os.path.isfile(fname2):
            raise Exception("Test file %s exists" % fname2)
        with open(fname1, "w") as fl:
            fl.write(xml1)
        with open(fname2, "w") as fl:
            fl.write(xml2)
        try:

            for cmd in commands:
                vl, er = self.runtest(cmd)
                lines = vl.split("\n\n")
                # print(vl)
                # print(er)
                self.assertEqual(len(lines), 7)
                self.assertTrue(lines[0].startswith("Comparing:"))
                self.assertTrue(
                    lines[1].startswith(
                        "Additional devices in '%s' {alias: [name]} :"
                        % fname1))
                self.assertTrue(
                    lines[3].startswith(
                        "Additional devices in '%s' {alias: [name]} :"
                        % fname2))
                self.assertTrue(
                    lines[5].startswith(
                        "Diffrences in the common part:"))

                first = eval(lines[2])
                second = eval(lines[4])
                common = eval(lines[6])
                self.myAssertDict(
                    first,
                    {'mot01': ['My_exp_mot01'],
                     'my_test_vfcadc': ['my_test_vfcadc']}
                )
                self.myAssertDict(
                    second,
                    {'My_test_tip850adc': ['My_test_tip850adc'],
                     'mot_01': ['my_exp_mot01'],
                     'my_test_tip830': ['my_test_tip830'],
                     'my_test_tip850dac': ['my_test_tip850dac']}
                    )
                self.myAssertDict(
                    common,
                    {'my_exp_mot02':
                     [{'tdevice': ('P09/motor/exp.04', 'p09/motor/Exp.02')}],
                     'my_exp_mot03':
                     [{'dtype': ('motor', 'stepping_motor'),
                       'hostname': ('Haso000:10000', 'haso000:10000')}]}
                )

        finally:
            os.remove(fname1)
            os.remove(fname2)


if __name__ == '__main__':
    unittest.main()
