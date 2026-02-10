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
import time
from nxstools import nxscreate


try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO


if sys.version_info > (3,):
    unicode = str
    long = int


# if 64-bit machione
IS64BIT = (struct.calcsize("P") == 8)


# test fixture
class NXSCreateClientDSFSTest(unittest.TestCase):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

        self.helperror = "Error: too few arguments\n"

        self.helpinfo = """usage: nxscreate [-h]
                 {clientds,tangods,deviceds,onlinecp,onlineds,poolds,stdcomp,comp,compare}
                 ...

 Command-line tool for creating NXSConfigServer configuration of Nexus Files

positional arguments:
  {clientds,tangods,deviceds,onlinecp,onlineds,poolds,stdcomp,comp,compare}
                        sub-command help
    clientds            create client datasources
    tangods             create tango datasources
    deviceds            create datasources for all device attributes
    onlinecp            create component from online.xml file
    onlineds            create datasources from online.xml file
    poolds              create datasources from sardana pool device
    stdcomp             create component from the standard templates
    comp                create simple components
    compare             compare two online.xml files

optional arguments:
  -h, --help            show this help message and exit

For more help:
  nxscreate <sub-command> -h

"""

        try:
            # random seed
            self.seed = long(binascii.hexlify(os.urandom(16)), 16)
        except NotImplementedError:
            # random seed
            self.seed = long(time.time() * 256)  # use fractional seconds

        self._rnd = random.Random(self.seed)

        self._bint = "int64" if IS64BIT else "int32"
        self._buint = "uint64" if IS64BIT else "uint32"
        self._bfloat = "float64" if IS64BIT else "float32"

        # home = expanduser("~")

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

    def test_clientds_simple(self):
        """ test nxsccreate clientds file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate clientds starttimetest %s' % self.flags).split(),
                'starttimetest',
                """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="starttimetest">
    <record name="starttimetest"/>
  </datasource>
</definition>
"""
            ],
            [
                ('nxscreate clientds endtimetest %s' % self.flags).split(),
                'endtimetest',
                """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="endtimetest">
    <record name="endtimetest"/>
  </datasource>
</definition>
"""
            ],
            [
                ('nxscreate clientds wwwtest %s' % self.flags).split(),
                'wwwtest',
                """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="wwwtest">
    <record name="wwwtest"/>
  </datasource>
</definition>
"""
            ],
            [
                ('nxscreate clientds abstest %s' % self.flags).split(),
                'abstest',
                """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="abstest">
    <record name="abstest"/>
  </datasource>
</definition>
"""
            ],
        ]

        totest = []
        try:
            for arg in args:
                if not self.dsexists(arg[1]):
                    totest.append(arg[1])

                    vl, er = self.runtest(arg[0])

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    xml = self.getds(arg[1])
                    self.assertEqual(arg[2], xml)

                    self.deleteds(arg[1])
        finally:
            for ds in totest:
                if self.dsexists(ds):
                    self.deleteds(ds)

    def test_clientds_first_last(self):
        """ test nxsccreate clientds file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate clientds -v test_exp_c  -l3 %s'
                 % self.flags).split(),
                ['test_exp_c01',
                 'test_exp_c02',
                 'test_exp_c03'],
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_c01">
    <record name="test_exp_c01"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_c02">
    <record name="test_exp_c02"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_c03">
    <record name="test_exp_c03"/>
  </datasource>
</definition>
""",
                ],
            ],
            [
                ('nxscreate clientds -v test_exp_mot  -f2 -l3 %s'
                 % self.flags).split(),
                ['test_exp_mot02',
                 'test_exp_mot03'],
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_mot02">
    <record name="test_exp_mot02"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_mot03">
    <record name="test_exp_mot03"/>
  </datasource>
</definition>
""",
                ],
            ],
            [
                ('nxscreate clientds --device test_exp_vfc'
                 ' --first 2 --last 3 %s' % self.flags).split(),
                ['test_exp_vfc02',
                 'test_exp_vfc03'],
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_vfc02">
    <record name="test_exp_vfc02"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_vfc03">
    <record name="test_exp_vfc03"/>
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
            for ds in totest:
                if self.dsexists(ds):
                    self.deleteds(ds)

    def test_clientds_minimal(self):
        """ test nxsccreate clientds file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate clientds -v test_exp_cc  -m -f3 -l5 %s'
                 % self.flags).split(),
                ['test_exp_cc3',
                 'test_exp_cc4',
                 'test_exp_cc5'],
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_cc3">
    <record name="test_exp_cc3"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_cc4">
    <record name="test_exp_cc4"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_cc5">
    <record name="test_exp_cc5"/>
  </datasource>
</definition>
""",
                ],
            ],
            [
                ('nxscreate clientds -v test_exp_dd '
                 '--minimal-device --first 3 --last 4 %s'
                 % self.flags).split(),
                ['test_exp_dd3',
                 'test_exp_dd4'],
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_dd3">
    <record name="test_exp_dd3"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_dd4">
    <record name="test_exp_dd4"/>
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
            for ds in totest:
                if self.dsexists(ds):
                    self.deleteds(ds)

    def test_clientds_source_prefix(self):
        """ test nxsccreate clientds file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate clientds -v testcounter -s test_exp_vc  -f3 -l5 %s'
                 % self.flags).split(),
                ['test_exp_vc03',
                 'test_exp_vc04',
                 'test_exp_vc05'],
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_vc03">
    <record name="testcounter03"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_vc04">
    <record name="testcounter04"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_vc05">
    <record name="testcounter05"/>
  </datasource>
</definition>
""",
                ],
            ],
            [
                ('nxscreate clientds --device testdec '
                 '--datasource-prefix test_exp_d '
                 '--first 3 --last 4 %s'
                 % self.flags).split(),
                ['test_exp_d03',
                 'test_exp_d04'],
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_d03">
    <record name="testdec03"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_d04">
    <record name="testdec04"/>
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
            for ds in totest:
                if self.dsexists(ds):
                    self.deleteds(ds)

    def test_clientds_overwrite_false(self):
        """ test nxsccreate clientds file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate clientds -v testcounter -s test_exp_vc  -f3 -l5 %s'
                 % self.flags).split(),
                ['test_exp_vc03',
                 'test_exp_vc04',
                 'test_exp_vc05'],
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_vc03">
    <record name="testcounter03"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_vc04">
    <record name="testcounter04"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_vc05">
    <record name="testcounter05"/>
  </datasource>
</definition>
""",
                ],
                ('nxscreate clientds -v test2counter -s test_exp_vc -f3 -l5 %s'
                 % self.flags).split(),
            ],
            [
                ('nxscreate clientds --device testdec '
                 '--datasource-prefix test_exp_d '
                 '--first 3 --last 4 %s'
                 % self.flags).split(),
                ['test_exp_d03',
                 'test_exp_d04'],
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_d03">
    <record name="testdec03"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_d04">
    <record name="testdec04"/>
  </datasource>
</definition>
""",
                ],
                ('nxscreate clientds --device test2dec '
                 '--datasource-prefix test_exp_d '
                 '--first 3 --last 4 %s'
                 % self.flags).split(),
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
                    vl, er = self.runtestexcept(arg[3], Exception)

                    self.assertEqual('', er)
                    self.assertTrue(vl)

                    for i, ds in enumerate(arg[1]):
                        xml = self.getds(ds)
                        self.assertEqual(arg[2][i], xml)

                    for ds in arg[1]:
                        self.deleteds(ds)
        finally:
            for ds in totest:
                if self.dsexists(ds):
                    self.deleteds(ds)

    def test_clientds_overwrite_true(self):
        """ test nxsccreate clientds file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate clientds -v testcounter -s test_exp_vc  -f3 -l5 %s'
                 % self.flags).split(),
                ['test_exp_vc03',
                 'test_exp_vc04',
                 'test_exp_vc05'],
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_vc03">
    <record name="testcounter03"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_vc04">
    <record name="testcounter04"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_vc05">
    <record name="testcounter05"/>
  </datasource>
</definition>
""",
                ],
                ('nxscreate clientds -v test2counter -o -s test_exp_vc '
                 ' -f3 -l5 %s' % self.flags).split(),
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_vc03">
    <record name="test2counter03"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_vc04">
    <record name="test2counter04"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_vc05">
    <record name="test2counter05"/>
  </datasource>
</definition>
""",
                ],
            ],
            [
                ('nxscreate clientds --device testdec '
                 '--datasource-prefix test_exp_d '
                 '--first 3 --last 4 %s'
                 % self.flags).split(),
                ['test_exp_d03',
                 'test_exp_d04'],
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_d03">
    <record name="testdec03"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_d04">
    <record name="testdec04"/>
  </datasource>
</definition>
""",
                ],
                ('nxscreate clientds --device test2dec --overwrite '
                 '--datasource-prefix test_exp_d '
                 '--first 3 --last 4 %s'
                 % self.flags).split(),
                [
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_d03">
    <record name="test2dec03"/>
  </datasource>
</definition>
""",
                    """<?xml version='1.0' encoding='utf-8'?>
<definition>
  <datasource type="CLIENT" name="test_exp_d04">
    <record name="test2dec04"/>
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
                    vl, er = self.runtest(arg[3])

                    self.assertEqual('', er)
                    self.assertTrue(vl)

                    for i, ds in enumerate(arg[1]):
                        xml = self.getds(ds)
                        self.assertEqual(arg[4][i], xml)

                    for ds in arg[1]:
                        self.deleteds(ds)
        finally:
            for ds in totest:
                if self.dsexists(ds):
                    self.deleteds(ds)


if __name__ == '__main__':
    unittest.main()
