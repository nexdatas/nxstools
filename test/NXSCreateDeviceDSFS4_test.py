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
try:
    import tango
except Exception:
    import PyTango as tango

from os.path import expanduser
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

try:
    import ServerSetUp
except ImportError:
    from . import ServerSetUp


# test fixture
class NXSCreateDeviceDSFS4Test(unittest.TestCase):

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

        home = expanduser("~")
        self._bint = "int64" if IS64BIT else "int32"
        self._buint = "uint64" if IS64BIT else "uint32"
        self._bfloat = "float64" if IS64BIT else "float32"

        self.__args = '{"db":"nxsconfig", ' \
                      '"read_default_file":"/etc/my.cnf", "use_unicode":true}'

        self.__args2 = '{"db":"nxsconfig", ' \
                       '"read_default_file":"%s/.my.cnf", ' \
                       '"use_unicode":true}' % home
        self._sv = ServerSetUp.ServerSetUp()
        self._proxy = None

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

    # opens config server
    # \param args connection arguments
    # \returns NXSConfigServer instance
    def openConfig(self, args):

        found = False
        cnt = 0
        while not found and cnt < 1000:
            try:
                sys.stdout.write(".")
                xmlc = tango.DeviceProxy(
                    self._sv.new_device_info_writer.name)
                time.sleep(0.01)
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
        print("\nsetting up...")
        print("SEED = %s" % self.seed)
        self._sv.setUp()
        self.openConf()

    # test closer
    # \brief Common tear down
    def tearDown(self):
        print("tearing down ...")
        self.closeConfig()
        self._sv.tearDown()

    def openConf(self):
        try:
            el = self.openConfig(self.__args)
        except Exception:
            el = self.openConfig(self.__args2)
        self._proxy = el

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

    def test_deviceds_allattributes(self):
        """ test nxsccreate deviceds file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        device = self._proxy.name()
        args = [
            [
                ('nxscreate deviceds -v %s -s testcs_ '
                 '%s' % (device, self.flags)).split(),
                ['testcs_jsonsettings',
                 'testcs_selection',
                 'testcs_xmlstring',
                 'testcs_variables',
                 'testcs_linkdatasources',
                 'testcs_extralinkdatasources',
                 'testcs_version',
                 'testcs_stepdatasources',
                 'testcs_canfaildatasources'],
                [
                    '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO" name="testcs_jsonsettings"'
                    '>\n'
                    '    <device name="%s" '
                    'member="attribute" hostname="%s" port="%s"'
                    ' group="testcs_"/>\n'
                    '    <record name="JSONSettings"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO" name="testcs_selection">\n'
                    '    <device name="%s" '
                    'member="attribute" hostname="%s" port="%s"'
                    ' group="testcs_"/>\n'
                    '    <record name="Selection"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO" name="testcs_xmlstring">\n'
                    '    <device name="%s" '
                    'member="attribute" hostname="%s" port="%s"'
                    ' group="testcs_"/>\n'
                    '    <record name="XMLString"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO" name="testcs_variables">\n'
                    '    <device name="%s" '
                    'member="attribute" hostname="%s" port="%s"'
                    ' group="testcs_"/>\n'
                    '    <record name="Variables"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO" name="testcs_linkdatasources"'
                    '>\n'
                    '    <device name="%s" '
                    'member="attribute" hostname="%s" port="%s"'
                    ' group="testcs_"/>\n'
                    '    <record name="LinkDataSources"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO" '
                    'name="testcs_extralinkdatasources"'
                    '>\n'
                    '    <device name="%s" '
                    'member="attribute" hostname="%s" port="%s"'
                    ' group="testcs_"/>\n'
                    '    <record name="ExtraLinkDataSources"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO" name="testcs_version">\n'
                    '    <device name="%s" '
                    'member="attribute" hostname="%s" port="%s"'
                    ' group="testcs_"/>\n'
                    '    <record name="Version"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO" name="testcs_stepdatasources"'
                    '>\n'
                    '    <device name="%s" '
                    'member="attribute" hostname="%s" port="%s"'
                    ' group="testcs_"/>\n'
                    '    <record name="STEPDataSources"/>\n'
                    '  </datasource>\n'
                    '</definition>\n',
                    '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                    '<definition>\n'
                    '  <datasource type="TANGO"'
                    ' name="testcs_canfaildatasources"'
                    '>\n'
                    '    <device name="%s" '
                    'member="attribute" hostname="%s" port="%s"'
                    ' group="testcs_"/>\n'
                    '    <record name="CanFailDataSources"/>\n'
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
                            arg[2][i] % (device, self.host, self.port), xml)

                    for ds in arg[1]:
                        self.deleteds(ds)
        finally:
            for ds in totest:
                if self.dsexists(ds):
                    self.deleteds(ds)


if __name__ == '__main__':
    unittest.main()
