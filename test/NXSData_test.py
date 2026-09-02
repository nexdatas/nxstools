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
import threading

try:
    import tango
except Exception:
    import PyTango as tango

from nxstools import nxsdata
from nxstools import h5cppwriter as H5CppWriter

try:
    import WriterSetUp
except ImportError:
    from . import WriterSetUp


try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO


if sys.version_info > (3,):
    unicode = str
    long = int


class mytty(object):

    def __init__(self, underlying):
        #        underlying.encoding = 'cp437'
        self.__underlying = underlying

    def __getattr__(self, name):
        return getattr(self.__underlying, name)

    def isatty(self):
        return True

    def __del__(self):
        self.__underlying.close()


# if 64-bit machione
IS64BIT = (struct.calcsize("P") == 8)

# from nxsconfigserver.XMLConfigurator  import XMLConfigurator
# from nxsconfigserver.Merger import Merger
# from nxsconfigserver.Errors import (
# NonregisteredDBRecordError, UndefinedTagError,
#                                    IncompatibleNodeError)
# import nxsconfigserver


def myinput(w, text):
    myio = os.fdopen(w, 'w')
    myio.write(text)
    myio.close()


# test fixture
class NXSDataTest(unittest.TestCase):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

        self.helperror = "Error: too few arguments\n"

        self.helpinfo = """usage: nxsdata [-h]
               {openfile,setdata,openentry,record,closefile,closeentry} ...

Command-line tool for writing NeXus files with NXSDataWriter

positional arguments:
  {openfile,setdata,openentry,record,closefile,closeentry}
                        sub-command help
    openfile            open a new H5 file
    setdata             assign global JSON data
    openentry           create new entry
    record              record one step with step JSON data
    closefile           close the current file
    closeentry          close the current entry

optional arguments:
  -h, --help            show this help message and exit

For more help:
  nxsdata <sub-command> -h

"""

        try:
            # random seed
            self.seed = long(binascii.hexlify(os.urandom(16)), 16)
        except NotImplementedError:
            import time
            # random seed
            self.seed = long(time.time() * 256)  # use fractional seconds

        self.__rnd = random.Random(self.seed)

        self._scanXmlpart = """
    <group type="NXinstrument" name="instrument">
      <attribute name ="short_name"> scan instrument </attribute>
      <group type="NXdetector" name="detector">
        <field units="m" type="NX_FLOAT" name="counter1">
          <strategy mode="STEP"/>
          <datasource type="CLIENT">
            <record name="exp_c01"/>
          </datasource>
        </field>
        <field units="" type="NX_FLOAT" name="mca">
          <dimensions rank="1">
            <dim value="2048" index="1"/>
          </dimensions>
          <strategy mode="STEP"/>
          <datasource type="CLIENT">
            <record name="p09/mca/exp.02"/>
          </datasource>
        </field>
      </group>
    </group>
"""

        self._scanXml = """
<definition>
  <group type="NXentry" name="entry1">
    <group type="NXinstrument" name="instrument">
      <attribute name ="short_name"> scan instrument </attribute>
      <group type="NXdetector" name="detector">
        <field units="m" type="NX_FLOAT" name="counter1">
          <strategy mode="INIT"/>
          <datasource type="CLIENT">
            <record name="exp_c01"/>
          </datasource>
        </field>
        <field units="" type="NX_FLOAT" name="mca">
          <dimensions rank="1">
            <dim value="2048" index="1"/>
          </dimensions>
          <strategy mode="STEP"/>
          <datasource type="CLIENT">
            <record name="p09/mca/exp.02"/>
          </datasource>
        </field>
      </group>
    </group>
    <group type="NXdata" name="data">
      <link target="/NXentry/NXinstrument/NXdetector/mca" name="data">
        <doc>
          Link to mca in /NXentry/NXinstrument/NXdetector
        </doc>
      </link>
      <link target="%s://entry1/instrument/detector/counter1" name="cnt1">
        <doc>
          Link to counter1 in /NXentry/NXinstrument/NXdetector
        </doc>
      </link>
    </group>
  </group>
</definition>
"""
        self._counter = [0.1, 0.2]
        self._mca1 = [e * 0.1 for e in range(2048)]
        self._mca2 = [e * 0.2 for e in range(2048)]

        self._bint = "int64" if IS64BIT else "int32"
        self._buint = "uint64" if IS64BIT else "uint32"
        self._bfloat = "float64" if IS64BIT else "float32"

        self.maxDiff = None

        self._sv = WriterSetUp.WriterSetUp()

    def runtest(self, argv, pipeinput=None):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = mystdout = StringIO()
        sys.stderr = mystderr = StringIO()
        old_argv = sys.argv
        sys.argv = argv

        if pipeinput is not None:
            r, w = os.pipe()
            new_stdin = mytty(os.fdopen(r, 'r'))
            old_stdin, sys.stdin = sys.stdin, new_stdin
            tm = threading.Timer(1., myinput, [w, pipeinput])
            tm.start()
        else:
            old_stdin = sys.stdin
            sys.stdin = StringIO()

        etxt = None
        try:
            nxsdata.main()
        except Exception as e:
            etxt = str(e)
        except SystemExit as e:
            etxt = str(e)
        sys.argv = old_argv

        sys.stdout = old_stdout
        sys.stderr = old_stderr
        sys.stdin = old_stdin
        sys.argv = old_argv
        vl = mystdout.getvalue()
        er = mystderr.getvalue()
        # print(vl)
        # print(er)
        if etxt:
            print(etxt)
        self.assertTrue(etxt is None)
        return vl, er

    def runtestexcept(self, argv, exception):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        old_stdin = sys.stdin
        sys.stdin = StringIO()
        sys.stdout = mystdout = StringIO()
        sys.stderr = mystderr = StringIO()

        old_argv = sys.argv
        sys.argv = argv
        try:
            error = False
            nxsdata.main()
        except exception as e:
            etxt = str(e)
            error = True
        self.assertEqual(error, True)

        sys.argv = old_argv

        sys.stdout = old_stdout
        sys.stderr = old_stderr
        sys.stdin = old_stdin
        sys.argv = old_argv
        vl = mystdout.getvalue()
        er = mystderr.getvalue()
        return vl, er, etxt

    # opens config server
    # \param args connection arguments
    # \returns NXSDataWriter instance
    def openWriter(self):

        found = False
        cnt = 0
        while not found and cnt < 1000:
            try:
                sys.stdout.write(".")
                wr = tango.DeviceProxy(
                    self._sv.new_device_info_writer.name)
                time.sleep(0.01)
                if wr.state() == tango.DevState.ON:
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

        self.assertEqual(wr.state(), tango.DevState.ON)
        return wr

    # test starter
    # \brief Common set up
    def setUp(self):
        print("\nsetting up...")
        self._sv.setUp()
        print("SEED = %s" % self.seed)

    # test closer
    # \brief Common tear down
    def tearDown(self):
        print("tearing down ...")
        self._sv.tearDown()

    # Exception tester
    # \param exception expected exception
    # \param method called method
    # \param args list with method arguments
    # \param kwargs dictionary with method arguments
    def myAssertRaise(self, exception, method, *args, **kwargs):
        try:
            error = False
            method(*args, **kwargs)
        except Exception:
            error = True
        self.assertEqual(error, True)

    def test_default(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        vl, er, et = self.runtestexcept(['nxsdata'], SystemExit)
        self.assertEqual(
            "".join(self.helpinfo.split()).replace(
                "optionalarguments:", "options:"),
            "".join(vl.split()).replace(
                "optionalarguments:", "options:").replace(
                    "usage:python3", "usage:").replace(
                        "usage:python", "usage:"))
        self.assertEqual(self.helperror, er)

    def test_help(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        helps = ['-h', '--help']
        for hl in helps:
            vl, er, et = self.runtestexcept(['nxsdata', hl], SystemExit)
            self.assertEqual(
                "".join(self.helpinfo.split()).replace(
                    "optionalarguments:", "options:"),
                "".join(vl.split()).replace(
                    "optionalarguments:", "options:").replace(
                        "usage:python3", "usage:").replace(
                            "usage:python", "usage:"))
            self.assertEqual('', er)

    def test_openfile(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        fname = '%s/%s%s.h5' % (os.getcwd(), self.__class__.__name__, fun)

        el = self.openWriter()

        commands = [
            ['nxsdata', 'openfile',
             '-s', self._sv.new_device_info_writer.name,
             fname],
            ['nxsdata', 'openfile',
             '--server', self._sv.new_device_info_writer.name,
             fname],
        ]
        for cmd in commands:
            try:
                vl, er = self.runtest(cmd)

                print(vl)
                self.assertEqual('', er)
                el.closeFile()

                from nxstools import filewriter as FileWriter
                FileWriter.writer = H5CppWriter
                f = FileWriter.open_file(fname, readonly=True)
                f = f.root()
                self.assertEqual(5, len(f.attributes))
                self.assertEqual(f.attributes["file_name"][...], fname)
                self.assertTrue(f.attributes["NX_class"][...], "NXroot")
                self.assertEqual(f.size, 1)

                en = f.open("nexus_logs")
                self.assertTrue(en.is_valid)
                self.assertEqual(en.name, "nexus_logs")
                self.assertEqual(len(en.attributes), 0)
                self.assertEqual(en.size, 1)

                ins = en.open("configuration")
                self.assertTrue(ins.is_valid)
                self.assertEqual(ins.name, "configuration")
                self.assertEqual(len(ins.attributes), 0)
                self.assertEqual(ins.size, 1)

                f.close()

            finally:
                pass
                if os.path.isfile(fname):
                    os.remove(fname)

    def test_closefile(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        fname = '%s/%s%s.h5' % (os.getcwd(), self.__class__.__name__, fun)

        el = self.openWriter()

        commands = [
            ['nxsdata', 'closefile',
             '-s', self._sv.new_device_info_writer.name],
            ['nxsdata', 'closefile',
             '--server', self._sv.new_device_info_writer.name],
        ]
        for cmd in commands:
            try:
                el.fileName = fname
                el.openFile()
                vl, er = self.runtest(cmd)

                print(vl)
                self.assertEqual('', er)

                from nxstools import filewriter as FileWriter
                FileWriter.writer = H5CppWriter
                f = FileWriter.open_file(fname, readonly=True)
                f = f.root()
                self.assertEqual(5, len(f.attributes))
                self.assertEqual(f.attributes["file_name"][...], fname)
                self.assertTrue(f.attributes["NX_class"][...], "NXroot")
                self.assertEqual(f.size, 1)

                en = f.open("nexus_logs")
                self.assertTrue(en.is_valid)
                self.assertEqual(en.name, "nexus_logs")
                self.assertEqual(len(en.attributes), 0)
                self.assertEqual(en.size, 1)

                ins = en.open("configuration")
                self.assertTrue(ins.is_valid)
                self.assertEqual(ins.name, "configuration")
                self.assertEqual(len(ins.attributes), 0)
                self.assertEqual(ins.size, 1)

                f.close()

            finally:
                pass
                if os.path.isfile(fname):
                    os.remove(fname)

    def test_openentry(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        fname = '%s/%s%s.h5' % (os.getcwd(), self.__class__.__name__, fun)
        jdata = '{"data": {"exp_c01":' + str(self._counter[0]) + \
            ', "p09/mca/exp.02":' + str(self._mca1) + '  } }'

        el = self.openWriter()

        commands = [
            ['nxsdata', 'openentry',
             '-s', self._sv.new_device_info_writer.name,
             self._scanXml % fname],
            ['nxsdata', 'openentry',
             '--server', self._sv.new_device_info_writer.name,
             self._scanXml % fname],
        ]
#        commands = [['nxsdata', 'list']]
        for cmd in commands:
            try:
                el.fileName = fname
                el.openFile()
                el.JSONRecord = jdata
                vl, er = self.runtest(cmd)

                print(vl)
                self.assertEqual('', er)
                el.closeEntry()
                el.closeFile()

                from nxstools import filewriter as FileWriter
                FileWriter.writer = H5CppWriter
                f = FileWriter.open_file(fname, readonly=True)
                f = f.root()
                self.assertEqual(5, len(f.attributes))
                self.assertEqual(f.attributes["file_name"][...], fname)
                self.assertTrue(f.attributes["NX_class"][...], "NXroot")
                self.assertEqual(f.size, 2)

                en = f.open("entry1")
                self.assertTrue(en.is_valid)
                self.assertEqual(en.name, "entry1")
                self.assertEqual(len(en.attributes), 1)
                self.assertEqual(en.size, 2)

                at = en.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXentry")

                ins = en.open("instrument")
                self.assertTrue(ins.is_valid)
                self.assertEqual(ins.name, "instrument")
                self.assertEqual(len(ins.attributes), 2)
                self.assertEqual(ins.size, 1)

                at = ins.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXinstrument")

                at = ins.attributes["short_name"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "short_name")
                self.assertEqual(at[...], "scan instrument")

                det = ins.open("detector")
                self.assertTrue(det.is_valid)
                self.assertEqual(det.name, "detector")
                self.assertEqual(len(det.attributes), 1)
                self.assertEqual(det.size, 2)

                at = det.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXdetector")

    # cnt = det.open("counter")              # bad exception
                cnt = det.open("counter1")
                self.assertTrue(cnt.is_valid)
                self.assertEqual(cnt.name, "counter1")
                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(cnt.shape), 1)
                self.assertEqual(cnt.shape, (1,))
                self.assertEqual(cnt.dtype, "float64")
                self.assertEqual(cnt.size, 1)
                value = cnt.read()
    #            value = cnt[:]
                for i in range(len(value)):
                    self.assertEqual(self._counter[0], value[i])

                self.assertEqual(len(cnt.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = cnt.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = cnt.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "m")

                at = cnt.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                mca = det.open("mca")
                self.assertTrue(mca.is_valid)
                self.assertEqual(mca.name, "mca")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(mca.shape), 2)
                self.assertEqual(mca.shape, (0, 2048))
                self.assertEqual(mca.dtype, "float64")
                self.assertEqual(mca.size, 0)
                value = mca.read()
                self.assertEqual(0, len(value))
                self.assertEqual(len(mca.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = mca.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = mca.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "")

                at = mca.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                dt = en.open("data")
                self.assertTrue(dt.is_valid)
                self.assertEqual(dt.name, "data")
                self.assertEqual(len(dt.attributes), 1)
                self.assertEqual(dt.size, 2)

                at = dt.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXdata")

                cnt = dt.open("cnt1")
                self.assertTrue(cnt.is_valid)
                self.assertEqual(cnt.name, "cnt1")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(cnt.shape), 1)
                self.assertEqual(cnt.shape, (1,))
                self.assertEqual(cnt.dtype, "float64")
                self.assertEqual(cnt.size, 1)
    #             print(cnt.read())
                value = cnt[:]
                self.assertEqual(self._counter[0], value)

                self.assertEqual(len(cnt.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = cnt.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = cnt.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "m")

                at = cnt.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                mca = dt.open("data")
                self.assertTrue(mca.is_valid)
                self.assertEqual(mca.name, "data")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(mca.shape), 2)
                self.assertEqual(mca.shape, (0, 2048))
                self.assertEqual(mca.dtype, "float64")
                self.assertEqual(mca.size, 0)
                value = mca.read()

                self.assertEqual(len(value), 0)

                self.assertEqual(len(mca.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = mca.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = mca.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "")

                at = mca.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                f.close()

            finally:

                if os.path.isfile(fname):
                    os.remove(fname)

    def test_closeentry(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        fname = '%s/%s%s.h5' % (os.getcwd(), self.__class__.__name__, fun)
        jdata = '{"data": {"exp_c01":' + str(self._counter[0]) + \
            ', "p09/mca/exp.02":' + str(self._mca1) + '  } }'

        el = self.openWriter()

        commands = [
            ['nxsdata', 'closeentry',
             '-s', self._sv.new_device_info_writer.name],
            ['nxsdata', 'closeentry',
             '--server', self._sv.new_device_info_writer.name],
        ]
        #        commands = [['nxsdata', 'list']]
        for cmd in commands:
            try:
                el.fileName = fname
                el.openFile()
                el.JSONRecord = jdata
                el.XMLSettings = self._scanXml % fname
                el.openEntry()
                vl, er = self.runtest(cmd)

                print(vl)
                self.assertEqual('', er)
                el.closeFile()

                from nxstools import filewriter as FileWriter
                FileWriter.writer = H5CppWriter
                f = FileWriter.open_file(fname, readonly=True)
                f = f.root()
                self.assertEqual(5, len(f.attributes))
                self.assertEqual(f.attributes["file_name"][...], fname)
                self.assertTrue(f.attributes["NX_class"][...], "NXroot")
                self.assertEqual(f.size, 2)

                en = f.open("entry1")
                self.assertTrue(en.is_valid)
                self.assertEqual(en.name, "entry1")
                self.assertEqual(len(en.attributes), 1)
                self.assertEqual(en.size, 2)

                at = en.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXentry")

                ins = en.open("instrument")
                self.assertTrue(ins.is_valid)
                self.assertEqual(ins.name, "instrument")
                self.assertEqual(len(ins.attributes), 2)
                self.assertEqual(ins.size, 1)

                at = ins.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXinstrument")

                at = ins.attributes["short_name"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "short_name")
                self.assertEqual(at[...], "scan instrument")

                det = ins.open("detector")
                self.assertTrue(det.is_valid)
                self.assertEqual(det.name, "detector")
                self.assertEqual(len(det.attributes), 1)
                self.assertEqual(det.size, 2)

                at = det.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXdetector")

    # cnt = det.open("counter")              # bad exception
                cnt = det.open("counter1")
                self.assertTrue(cnt.is_valid)
                self.assertEqual(cnt.name, "counter1")
                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(cnt.shape), 1)
                self.assertEqual(cnt.shape, (1,))
                self.assertEqual(cnt.dtype, "float64")
                self.assertEqual(cnt.size, 1)
                value = cnt.read()
    #            value = cnt[:]
                for i in range(len(value)):
                    self.assertEqual(self._counter[0], value[i])

                self.assertEqual(len(cnt.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = cnt.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = cnt.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "m")

                at = cnt.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                mca = det.open("mca")
                self.assertTrue(mca.is_valid)
                self.assertEqual(mca.name, "mca")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(mca.shape), 2)
                self.assertEqual(mca.shape, (0, 2048))
                self.assertEqual(mca.dtype, "float64")
                self.assertEqual(mca.size, 0)
                value = mca.read()
                self.assertEqual(0, len(value))
                self.assertEqual(len(mca.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = mca.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = mca.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "")

                at = mca.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                dt = en.open("data")
                self.assertTrue(dt.is_valid)
                self.assertEqual(dt.name, "data")
                self.assertEqual(len(dt.attributes), 1)
                self.assertEqual(dt.size, 2)

                at = dt.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXdata")

                cnt = dt.open("cnt1")
                self.assertTrue(cnt.is_valid)
                self.assertEqual(cnt.name, "cnt1")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(cnt.shape), 1)
                self.assertEqual(cnt.shape, (1,))
                self.assertEqual(cnt.dtype, "float64")
                self.assertEqual(cnt.size, 1)
                #             print(cnt.read())
                value = cnt[:]
                self.assertEqual(self._counter[0], value)

                self.assertEqual(len(cnt.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = cnt.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = cnt.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "m")

                at = cnt.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                mca = dt.open("data")
                self.assertTrue(mca.is_valid)
                self.assertEqual(mca.name, "data")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(mca.shape), 2)
                self.assertEqual(mca.shape, (0, 2048))
                self.assertEqual(mca.dtype, "float64")
                self.assertEqual(mca.size, 0)
                value = mca.read()

                self.assertEqual(len(value), 0)

                self.assertEqual(len(mca.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = mca.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = mca.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "")

                at = mca.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                f.close()

            finally:

                if os.path.isfile(fname):
                    os.remove(fname)

    def test_setdata(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        fname = '%s/%s%s.h5' % (os.getcwd(), self.__class__.__name__, fun)
        jdata = '{"data": {"exp_c01":' + str(self._counter[0]) + \
            ', "p09/mca/exp.02":' + str(self._mca1) + '  } }'

        el = self.openWriter()

        commands = [
            ['nxsdata', 'setdata',
             '-s', self._sv.new_device_info_writer.name,
             jdata],
            ['nxsdata', 'setdata',
             '--server', self._sv.new_device_info_writer.name,
             jdata],
        ]
#        commands = [['nxsdata', 'list']]
        for cmd in commands:
            try:
                el.fileName = fname
                el.openFile()
                el.JSONRecord = jdata
                vl, er = self.runtest(cmd)

                print(vl)
                self.assertEqual('', er)
                el.XMLSettings = self._scanXml % fname
                el.openEntry()
                el.closeEntry()
                el.closeFile()

                from nxstools import filewriter as FileWriter
                FileWriter.writer = H5CppWriter
                f = FileWriter.open_file(fname, readonly=True)
                f = f.root()
                self.assertEqual(5, len(f.attributes))
                self.assertEqual(f.attributes["file_name"][...], fname)
                self.assertTrue(f.attributes["NX_class"][...], "NXroot")
                self.assertEqual(f.size, 2)

                en = f.open("entry1")
                self.assertTrue(en.is_valid)
                self.assertEqual(en.name, "entry1")
                self.assertEqual(len(en.attributes), 1)
                self.assertEqual(en.size, 2)

                at = en.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXentry")

                ins = en.open("instrument")
                self.assertTrue(ins.is_valid)
                self.assertEqual(ins.name, "instrument")
                self.assertEqual(len(ins.attributes), 2)
                self.assertEqual(ins.size, 1)

                at = ins.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXinstrument")

                at = ins.attributes["short_name"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "short_name")
                self.assertEqual(at[...], "scan instrument")

                det = ins.open("detector")
                self.assertTrue(det.is_valid)
                self.assertEqual(det.name, "detector")
                self.assertEqual(len(det.attributes), 1)
                self.assertEqual(det.size, 2)

                at = det.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXdetector")

    # cnt = det.open("counter")              # bad exception
                cnt = det.open("counter1")
                self.assertTrue(cnt.is_valid)
                self.assertEqual(cnt.name, "counter1")
                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(cnt.shape), 1)
                self.assertEqual(cnt.shape, (1,))
                self.assertEqual(cnt.dtype, "float64")
                self.assertEqual(cnt.size, 1)
                value = cnt.read()
    #            value = cnt[:]
                for i in range(len(value)):
                    self.assertEqual(self._counter[0], value[i])

                self.assertEqual(len(cnt.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = cnt.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = cnt.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "m")

                at = cnt.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                mca = det.open("mca")
                self.assertTrue(mca.is_valid)
                self.assertEqual(mca.name, "mca")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(mca.shape), 2)
                self.assertEqual(mca.shape, (0, 2048))
                self.assertEqual(mca.dtype, "float64")
                self.assertEqual(mca.size, 0)
                value = mca.read()
                self.assertEqual(0, len(value))
                self.assertEqual(len(mca.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = mca.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = mca.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "")

                at = mca.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                dt = en.open("data")
                self.assertTrue(dt.is_valid)
                self.assertEqual(dt.name, "data")
                self.assertEqual(len(dt.attributes), 1)
                self.assertEqual(dt.size, 2)

                at = dt.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXdata")

                cnt = dt.open("cnt1")
                self.assertTrue(cnt.is_valid)
                self.assertEqual(cnt.name, "cnt1")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(cnt.shape), 1)
                self.assertEqual(cnt.shape, (1,))
                self.assertEqual(cnt.dtype, "float64")
                self.assertEqual(cnt.size, 1)
    #             print(cnt.read())
                value = cnt[:]
                self.assertEqual(self._counter[0], value)

                self.assertEqual(len(cnt.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = cnt.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = cnt.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "m")

                at = cnt.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                mca = dt.open("data")
                self.assertTrue(mca.is_valid)
                self.assertEqual(mca.name, "data")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(mca.shape), 2)
                self.assertEqual(mca.shape, (0, 2048))
                self.assertEqual(mca.dtype, "float64")
                self.assertEqual(mca.size, 0)
                value = mca.read()

                self.assertEqual(len(value), 0)

                self.assertEqual(len(mca.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = mca.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = mca.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "")

                at = mca.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                f.close()

            finally:

                if os.path.isfile(fname):
                    os.remove(fname)

    def test_record(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        fname = '%s/%s%s.h5' % (os.getcwd(), self.__class__.__name__, fun)
        jdata = ['{"data": {"exp_c01":' + str(self._counter[0]) +
                 ', "p09/mca/exp.02":' + str(self._mca1) + '  } }',
                 '{"data": {"exp_c01":' + str(self._counter[0]) +
                 ', "p09/mca/exp.02":' + str(self._mca2) + '  } }']

        el = self.openWriter()

        commands = [
            ['nxsdata', 'record',
             '-s', self._sv.new_device_info_writer.name],
            ['nxsdata', 'record',
             '--server', self._sv.new_device_info_writer.name],
        ]
#        commands = [['nxsdata', 'list']]
        for cmd in commands:
            try:
                el.fileName = fname
                el.openFile()
                el.JSONRecord = jdata[0]
                el.XMLSettings = self._scanXml % fname
                el.openEntry()
                for jd in jdata:
                    cd = list(cmd)
                    cd.append(jd)
                    vl, er = self.runtest(cd)

                    print(vl)
                    self.assertEqual('', er)
                el.closeEntry()
                el.closeFile()

                from nxstools import filewriter as FileWriter
                FileWriter.writer = H5CppWriter
                f = FileWriter.open_file(fname, readonly=True)
                f = f.root()
                self.assertEqual(5, len(f.attributes))
                self.assertEqual(f.attributes["file_name"][...], fname)
                self.assertTrue(f.attributes["NX_class"][...], "NXroot")
                self.assertEqual(f.size, 2)

                en = f.open("entry1")
                self.assertTrue(en.is_valid)
                self.assertEqual(en.name, "entry1")
                self.assertEqual(len(en.attributes), 1)
                self.assertEqual(en.size, 2)

                at = en.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXentry")

                ins = en.open("instrument")
                self.assertTrue(ins.is_valid)
                self.assertEqual(ins.name, "instrument")
                self.assertEqual(len(ins.attributes), 2)
                self.assertEqual(ins.size, 1)

                at = ins.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXinstrument")

                at = ins.attributes["short_name"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "short_name")
                self.assertEqual(at[...], "scan instrument")

                det = ins.open("detector")
                self.assertTrue(det.is_valid)
                self.assertEqual(det.name, "detector")
                self.assertEqual(len(det.attributes), 1)
                self.assertEqual(det.size, 2)

                at = det.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXdetector")

    # cnt = det.open("counter")              # bad exception
                cnt = det.open("counter1")
                self.assertTrue(cnt.is_valid)
                self.assertEqual(cnt.name, "counter1")
                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(cnt.shape), 1)
                self.assertEqual(cnt.shape, (1,))
                self.assertEqual(cnt.dtype, "float64")
                self.assertEqual(cnt.size, 1)
                value = cnt.read()
    #            value = cnt[:]
                for i in range(len(value)):
                    self.assertEqual(self._counter[0], value[i])

                self.assertEqual(len(cnt.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = cnt.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = cnt.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "m")

                at = cnt.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                mca = det.open("mca")
                self.assertTrue(mca.is_valid)
                self.assertEqual(mca.name, "mca")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(mca.shape), 2)
                self.assertEqual(mca.shape, (2, 2048))
                self.assertEqual(mca.dtype, "float64")
                self.assertEqual(mca.size, 4096)
                value = mca.read()
                for i in range(len(value[0])):
                    self.assertEqual(self._mca1[i], value[0][i])
                for i in range(len(value[0])):
                    self.assertEqual(self._mca2[i], value[1][i])

                self.assertEqual(len(mca.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = mca.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = mca.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "")

                at = mca.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                dt = en.open("data")
                self.assertTrue(dt.is_valid)
                self.assertEqual(dt.name, "data")
                self.assertEqual(len(dt.attributes), 1)
                self.assertEqual(dt.size, 2)

                at = dt.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXdata")

                cnt = dt.open("cnt1")
                self.assertTrue(cnt.is_valid)
                self.assertEqual(cnt.name, "cnt1")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(cnt.shape), 1)
                self.assertEqual(cnt.shape, (1,))
                self.assertEqual(cnt.dtype, "float64")
                self.assertEqual(cnt.size, 1)
    #             print(cnt.read())
                value = cnt[:]
                self.assertEqual(self._counter[0], value)

                self.assertEqual(len(cnt.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = cnt.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = cnt.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "m")

                at = cnt.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                mca = dt.open("data")
                self.assertTrue(mca.is_valid)
                self.assertEqual(mca.name, "data")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(mca.shape), 2)
                self.assertEqual(mca.shape, (2, 2048))
                self.assertEqual(mca.dtype, "float64")
                self.assertEqual(mca.size, 4096)
                value = mca.read()
                for i in range(len(value[0])):
                    self.assertEqual(self._mca1[i], value[0][i])
                for i in range(len(value[0])):
                    self.assertEqual(self._mca2[i], value[1][i])

                self.assertEqual(len(mca.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = mca.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = mca.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "")

                at = mca.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                f.close()

            finally:

                if os.path.isfile(fname):
                    os.remove(fname)

    def test_setrecorddata(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        fname = '%s/%s%s.h5' % (os.getcwd(), self.__class__.__name__, fun)
        jdata = ['{"data": {"exp_c01":' + str(self._counter[0]) +
                 ', "p09/mca/exp.02":' + str(self._mca1) + '  } }',
                 '{"data": {"exp_c01":' + str(self._counter[0]) +
                 ', "p09/mca/exp.02":' + str(self._mca2) + '  } }']

        el = self.openWriter()

        commands = [
            ['nxsdata', 'setdata',
             '-s', self._sv.new_device_info_writer.name],
            ['nxsdata', 'setdata',
             '--server', self._sv.new_device_info_writer.name],
        ]
#        commands = [['nxsdata', 'list']]
        for cmd in commands:
            try:
                el.fileName = fname
                el.openFile()
                el.JSONRecord = jdata[0]
                el.XMLSettings = self._scanXml % fname
                el.openEntry()
                for jd in jdata:
                    cd = list(cmd)
                    cd.append(jd)
                    vl, er = self.runtest(cd)

                    print(vl)
                    self.assertEqual('', er)
                    el.record('')
                el.closeEntry()
                el.closeFile()

                from nxstools import filewriter as FileWriter
                FileWriter.writer = H5CppWriter
                f = FileWriter.open_file(fname, readonly=True)
                f = f.root()
                self.assertEqual(5, len(f.attributes))
                self.assertEqual(f.attributes["file_name"][...], fname)
                self.assertTrue(f.attributes["NX_class"][...], "NXroot")
                self.assertEqual(f.size, 2)

                en = f.open("entry1")
                self.assertTrue(en.is_valid)
                self.assertEqual(en.name, "entry1")
                self.assertEqual(len(en.attributes), 1)
                self.assertEqual(en.size, 2)

                at = en.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXentry")

                ins = en.open("instrument")
                self.assertTrue(ins.is_valid)
                self.assertEqual(ins.name, "instrument")
                self.assertEqual(len(ins.attributes), 2)
                self.assertEqual(ins.size, 1)

                at = ins.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXinstrument")

                at = ins.attributes["short_name"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "short_name")
                self.assertEqual(at[...], "scan instrument")

                det = ins.open("detector")
                self.assertTrue(det.is_valid)
                self.assertEqual(det.name, "detector")
                self.assertEqual(len(det.attributes), 1)
                self.assertEqual(det.size, 2)

                at = det.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXdetector")

    # cnt = det.open("counter")              # bad exception
                cnt = det.open("counter1")
                self.assertTrue(cnt.is_valid)
                self.assertEqual(cnt.name, "counter1")
                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(cnt.shape), 1)
                self.assertEqual(cnt.shape, (1,))
                self.assertEqual(cnt.dtype, "float64")
                self.assertEqual(cnt.size, 1)
                value = cnt.read()
    #            value = cnt[:]
                for i in range(len(value)):
                    self.assertEqual(self._counter[0], value[i])

                self.assertEqual(len(cnt.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = cnt.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = cnt.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "m")

                at = cnt.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                mca = det.open("mca")
                self.assertTrue(mca.is_valid)
                self.assertEqual(mca.name, "mca")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(mca.shape), 2)
                self.assertEqual(mca.shape, (2, 2048))
                self.assertEqual(mca.dtype, "float64")
                self.assertEqual(mca.size, 4096)
                value = mca.read()
                for i in range(len(value[0])):
                    self.assertEqual(self._mca1[i], value[0][i])
                for i in range(len(value[0])):
                    self.assertEqual(self._mca2[i], value[1][i])

                self.assertEqual(len(mca.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = mca.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = mca.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "")

                at = mca.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                dt = en.open("data")
                self.assertTrue(dt.is_valid)
                self.assertEqual(dt.name, "data")
                self.assertEqual(len(dt.attributes), 1)
                self.assertEqual(dt.size, 2)

                at = dt.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXdata")

                cnt = dt.open("cnt1")
                self.assertTrue(cnt.is_valid)
                self.assertEqual(cnt.name, "cnt1")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(cnt.shape), 1)
                self.assertEqual(cnt.shape, (1,))
                self.assertEqual(cnt.dtype, "float64")
                self.assertEqual(cnt.size, 1)
    #             print(cnt.read())
                value = cnt[:]
                self.assertEqual(self._counter[0], value)

                self.assertEqual(len(cnt.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = cnt.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = cnt.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "m")

                at = cnt.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                mca = dt.open("data")
                self.assertTrue(mca.is_valid)
                self.assertEqual(mca.name, "data")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(mca.shape), 2)
                self.assertEqual(mca.shape, (2, 2048))
                self.assertEqual(mca.dtype, "float64")
                self.assertEqual(mca.size, 4096)
                value = mca.read()
                for i in range(len(value[0])):
                    self.assertEqual(self._mca1[i], value[0][i])
                for i in range(len(value[0])):
                    self.assertEqual(self._mca2[i], value[1][i])

                self.assertEqual(len(mca.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "INIT")

                at = mca.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = mca.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "")

                at = mca.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                f.close()

            finally:

                if os.path.isfile(fname):
                    os.remove(fname)

    def test_nxpath(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        fname = '%s/%s%s.h5' % (os.getcwd(), self.__class__.__name__, fun)
        jdata = ['{"data": {"exp_c01":' + str(self._counter[0]) +
                 ', "p09/mca/exp.02":' + str(self._mca1) + '  } }',
                 '{"data": {"exp_c01":' + str(self._counter[0]) +
                 ', "p09/mca/exp.02":' + str(self._mca2) + '  } }']
        nxpath = "/entry1:NXentry"

        el = self.openWriter()

        commands = [
            ['nxsdata', 'openfile',
             '-s', self._sv.new_device_info_writer.name,
             "%s:/%s" % (fname, nxpath)],
            ['nxsdata', 'openfile',
             '--server', self._sv.new_device_info_writer.name,
             "%s:/%s" % (fname, nxpath)],
        ]
#        commands = [['nxsdata', 'list']]
        for cmd in commands:
            try:
                el.fileName = fname
                el.openFile()
                vl, er = self.runtest(cmd)
                print(vl)
                self.assertEqual('', er)
                el.JSONRecord = jdata[0]
                el.XMLSettings = self._scanXmlpart
                el.openEntry()
                for jd in jdata:
                    el.record(jd)
                el.closeEntry()
                el.closeFile()

                from nxstools import filewriter as FileWriter
                FileWriter.writer = H5CppWriter
                f = FileWriter.open_file(fname, readonly=True)
                f = f.root()
                self.assertEqual(5, len(f.attributes))
                self.assertEqual(f.attributes["file_name"][...], fname)
                self.assertTrue(f.attributes["NX_class"][...], "NXroot")
                self.assertEqual(f.size, 2)

                en = f.open("entry1")
                self.assertTrue(en.is_valid)
                self.assertEqual(en.name, "entry1")
                self.assertEqual(len(en.attributes), 1)
                self.assertEqual(en.size, 1)

                at = en.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXentry")

                ins = en.open("instrument")
                self.assertTrue(ins.is_valid)
                self.assertEqual(ins.name, "instrument")
                self.assertEqual(len(ins.attributes), 2)
                self.assertEqual(ins.size, 1)

                at = ins.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXinstrument")

                at = ins.attributes["short_name"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "short_name")
                self.assertEqual(at[...], "scan instrument")

                det = ins.open("detector")
                self.assertTrue(det.is_valid)
                self.assertEqual(det.name, "detector")
                self.assertEqual(len(det.attributes), 1)
                self.assertEqual(det.size, 2)

                at = det.attributes["NX_class"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "NX_class")
                self.assertEqual(at[...], "NXdetector")

    # cnt = det.open("counter")              # bad exception
                cnt = det.open("counter1")
                self.assertTrue(cnt.is_valid)
                self.assertEqual(cnt.name, "counter1")
                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(cnt.shape), 1)
                self.assertEqual(cnt.shape, (2,))
                self.assertEqual(cnt.dtype, "float64")
                self.assertEqual(cnt.size, 2)
                value = cnt.read()
    #            value = cnt[:]
                for i in range(len(value)):
                    self.assertEqual(self._counter[0], value[i])

                self.assertEqual(len(cnt.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "STEP")

                at = cnt.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = cnt.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "m")

                at = cnt.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                mca = det.open("mca")
                self.assertTrue(mca.is_valid)
                self.assertEqual(mca.name, "mca")

                self.assertTrue(hasattr(cnt.shape, "__iter__"))
                self.assertEqual(len(mca.shape), 2)
                self.assertEqual(mca.shape, (2, 2048))
                self.assertEqual(mca.dtype, "float64")
                self.assertEqual(mca.size, 4096)
                value = mca.read()
                for i in range(len(value[0])):
                    self.assertEqual(self._mca1[i], value[0][i])
                for i in range(len(value[0])):
                    self.assertEqual(self._mca2[i], value[1][i])

                self.assertEqual(len(mca.attributes), 4)

                at = cnt.attributes["nexdatas_strategy"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "nexdatas_strategy")
                self.assertEqual(at[...], "STEP")

                at = mca.attributes["type"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "type")
                self.assertEqual(at[...], "NX_FLOAT")

                at = mca.attributes["units"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")
                self.assertEqual(at.name, "units")
                self.assertEqual(at[...], "")

                at = mca.attributes["nexdatas_source"]
                self.assertTrue(at.is_valid)
                self.assertTrue(hasattr(at.shape, "__iter__"))
                self.assertEqual(len(at.shape), 0)
                self.assertEqual(at.shape, ())
                self.assertEqual(at.dtype, "string")

                f.close()

            finally:

                if os.path.isfile(fname):
                    os.remove(fname)


if __name__ == '__main__':
    unittest.main()
