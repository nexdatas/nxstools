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
import shutil
import fabio
import numpy as np
import json
from nxstools import nxscollect
from nxstools import filewriter
try:
    from pninexus import h5cpp
    H5CPP = True
except ImportError:
    H5CPP = False


try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO


if sys.version_info > (3,):
    unicode = str
    long = int

WRITERS = {}

try:
    from nxstools import h5pywriter
    WRITERS["h5py"] = h5pywriter
except Exception:
    pass

try:
    from nxstools import h5cppwriter
    WRITERS["h5cpp"] = h5cppwriter
except Exception:
    pass


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

    # myio.close()


# test fixture
class NXSCollectTest(unittest.TestCase):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        # self.maxDiff = None

        self.helperror = "Error: too few arguments\n"

        self.helpinfo = """usage: nxscollect [-h] {append,link,vds} ...

  Command-line tool to merge images of external file-formats """ + \
            """into the master NeXus file

positional arguments:
  {append,link,vds}  sub-command help
    append           append images to the master file
    link             create an external or internal link in the master file
    vds              create a virual dataset in the master file

optional arguments:
  -h, --help         show this help message and exit

For more help:
  nxscollect <sub-command> -h

"""

        try:
            # random seed
            self.seed = long(binascii.hexlify(os.urandom(16)), 16)
        except NotImplementedError:
            import time
            # random seed
            self.seed = long(time.time() * 256)  # use fractional seconds

        self.__rnd = random.Random(self.seed)

        self._bint = "int64" if IS64BIT else "int32"
        self._buint = "uint64" if IS64BIT else "uint32"
        self._bfloat = "float64" if IS64BIT else "float32"
        self.maxDiff = None

        if "h5cpp" in WRITERS.keys():
            self.writer = "h5cpp"
        else:
            self.writer = "h5py"

        self.flags = ""
        self.externalfilters = True

    # test starter
    # \brief Common set up
    def setUp(self):
        print("\nsetting up...")
        print("SEED = %s" % self.seed)

    # test closer
    # \brief Common tear down
    def tearDown(self):
        print("tearing down ...")

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

    def test_default(self):
        """ test nxsconfig default
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = mystdout = StringIO()
        sys.stderr = mystderr = StringIO()
        old_argv = sys.argv
        sys.argv = ['nxscollect']
        with self.assertRaises(SystemExit):
            nxscollect.main()

        sys.argv = old_argv
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        vl = mystdout.getvalue()
        er = mystderr.getvalue()
        self.assertEqual(
            "".join(self.helpinfo.split()).replace(
                "optionalarguments:", "options:"),
            "".join(vl.split()).replace(
                "optionalarguments:", "options:").replace(
                    "usage:python3", "usage:").replace(
                        "usage:python", "usage:"))
        self.assertEqual(self.helperror, er)

    def test_help(self):
        """ test nxsconfig help
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        helps = ['-h', '--help']
        for hl in helps:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = mystdout = StringIO()
            sys.stderr = mystderr = StringIO()
            old_argv = sys.argv
            sys.argv = ['nxscollect', hl]
            with self.assertRaises(SystemExit):
                nxscollect.main()

            sys.argv = old_argv
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            vl = mystdout.getvalue()
            er = mystderr.getvalue()
            self.assertEqual(
                "".join(self.helpinfo[0:-1].split()).replace(
                    "optionalarguments:", "options:"),
                "".join(vl.split()).replace(
                    "optionalarguments:", "options:").replace(
                    "usage:python3", "usage:").replace(
                        "usage:python", "usage:"))
            self.assertEqual('', er)

    def test_append_test_emptyfile(self):
        """ test nxsconfig append empty file
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = '%s/%s%s.nxs' % (os.getcwd(),
                                    self.__class__.__name__, fun)

        commands = [
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s -r %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            nxsfile = filewriter.create_file(filename, overwrite=True)
            nxsfile.close()

            for cmd in commands:
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertEqual('', vl)

        finally:
            os.remove(filename)

    def test_append_test_nofile(self):
        """ test nxsconfig append empty file
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = '%s/%s%s.nxs' % (os.getcwd(),
                                    self.__class__.__name__, fun)
        commands = [
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append -s %s %s' % (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append -s %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s -r %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        nxsfile = filewriter.create_file(
            filename, overwrite=True)
        nxsfile.close()
        os.remove(filename)

        for cmd in commands:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = mystdout = StringIO()
            sys.stderr = mystderr = StringIO()
            old_argv = sys.argv
            sys.argv = cmd
            self.myAssertRaise(IOError, nxscollect.main)

            sys.argv = old_argv
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            vl = mystdout.getvalue()
            er = mystderr.getvalue()

            self.assertEqual('', er)
            self.assertEqual('', vl)

    def test_append_test_file_withdata(self):
        """ test nxsconfig append file with data field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = '%s/%s%s.nxs' % (os.getcwd(),
                                    self.__class__.__name__, fun)
        commands = [
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -s  %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s  %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s -r %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            nxsfile = filewriter.create_file(
                filename, overwrite=True)
            rt = nxsfile.root()
            entry = rt.create_group("entry12345", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("detector", "NXdetector")
            entry.create_group("data", "NXdata")
            det.create_field("intimage", "uint32", [0, 30], [1, 30])
            nxsfile.close()

            for cmd in commands:
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertEqual('', vl)
                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)

        finally:
            os.remove(filename)

    def test_append_test_file_withpostrun_nofile(self):
        """ test nxsconfig append file with data field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = '%s/%s%s.nxs' % (os.getcwd(),
                                    self.__class__.__name__, fun)
        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append -r %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test -r %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test -r %s %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            nxsfile = filewriter.create_file(
                filename, overwrite=True)
            rt = nxsfile.root()
            entry = rt.create_group("entry12345", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("detector", "NXdetector")
            entry.create_group("data", "NXdata")
            col = det.create_group("collection", "NXcollection")
            postrun = col.create_field("postrun", "string")
            postrun.write("test1_%05d.cbf:0:5")
            nxsfile.close()

            for cmd in commands:
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                # if '-r' not in cmd:
                #     os.remove("%s.__nxscollect_old__" % filename)

        finally:
            os.remove(filename)

    def test_append_file_withpostrun_tif(self):
        """ test nxsconfig append file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = '%s/%s%s.nxs' % (os.getcwd(),
                                    self.__class__.__name__, fun)
        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file0.tif', './test1_00000.tif')
            shutil.copy2('test/files/test_file1.tif', './test1_00001.tif')
            shutil.copy2('test/files/test_file2.tif', './test1_00002.tif')
            shutil.copy2('test/files/test_file3.tif', './test1_00003.tif')
            shutil.copy2('test/files/test_file4.tif', './test1_00004.tif')
            shutil.copy2('test/files/test_file5.tif', './test1_00005.tif')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                # er =
                mystderr.getvalue()

                # self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 8)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.tif:0:5']")
                for i in range(1, 6):

                    self.assertTrue(svl[i].startswith(' * append '))
                    self.assertTrue(
                        svl[i].endswith('test1_%05d.tif ' % (i - 1)))

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (6, 195, 487))
                for i in range(6):
                    fbuffer = fabio.open('./test1_%05d.tif' % i)
                    fimage = fbuffer.data[...]
                    image = buffer[i, :, :]
                    self.assertTrue((image == fimage).all())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.tif')
            os.remove('./test1_00001.tif')
            os.remove('./test1_00002.tif')
            os.remove('./test1_00003.tif')
            os.remove('./test1_00004.tif')
            os.remove('./test1_00005.tif')

    def test_append_file_withpostrun_tif_pilatus300k_comp(self):
        """ test nxsconfig append file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = '%s/%s%s.nxs' % (os.getcwd(),
                                    self.__class__.__name__, fun)
        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r -s -c1  %s' %
             (filename, self.flags)).split(),
            ('nxscollect append  %s -c2 %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -c3 %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -c4 %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -c5 %s' %
             (filename, self.flags)).split(),
            ('nxscollect append  %s -s -c6 %s' %
             (filename, self.flags)).split(),

            ('nxscollect append %s -s -c7 %s' %
             (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s -c8 %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s -c9' %
             (filename, self.flags)).split(),
        ]
        extra_commands = [
            ('nxscollect append  %s -r -s -c32008:0,2 %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s -c32008:0,2' %
             (filename, self.flags)).split(),
        ]
        if self.externalfilters and H5CPP:
            if hasattr(h5cpp.filter, "is_filter_available") \
               and h5cpp.filter.is_filter_available(32008):
                commands.extend(extra_commands)

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            shutil.copy2('test/files/test_file0.tif',
                         './testcollect/pilatus300k/test1_00000.tif')
            shutil.copy2('test/files/test_file1.tif',
                         './testcollect/pilatus300k/test1_00001.tif')
            shutil.copy2('test/files/test_file2.tif',
                         './testcollect/pilatus300k/test1_00002.tif')
            shutil.copy2('test/files/test_file3.tif',
                         './testcollect/pilatus300k/test1_00003.tif')
            shutil.copy2('test/files/test_file4.tif',
                         './testcollect/pilatus300k/test1_00004.tif')
            shutil.copy2('test/files/test_file5.tif',
                         './testcollect/pilatus300k/test1_00005.tif')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 8)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.tif:0:5']")
                for i in range(1, 6):
                    self.assertTrue(
                        svl[i],
                        ' * append /home/jkotan/ndts/nexdatas.tools/'
                        'test1_%05d.tif ' % (i - 1)
                    )

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (6, 195, 487))
                for i in range(6):
                    fbuffer = fabio.open(
                        './testcollect/pilatus300k/test1_%05d.tif' % i)
                    fimage = fbuffer.data[...]
                    image = buffer[i, :, :]
                    self.assertTrue((image == fimage).all())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./testcollect/pilatus300k/test1_00000.tif')
            os.remove('./testcollect/pilatus300k/test1_00001.tif')
            os.remove('./testcollect/pilatus300k/test1_00002.tif')
            os.remove('./testcollect/pilatus300k/test1_00003.tif')
            os.remove('./testcollect/pilatus300k/test1_00004.tif')
            os.remove('./testcollect/pilatus300k/test1_00005.tif')
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_append_file_withpostrun_tif_pilatus300k_skip(self):
        """ test nxsconfig append file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            shutil.copy2('test/files/test_file0.tif',
                         './testcollect/pilatus300k/test1_00000.tif')
            shutil.copy2('test/files/test_file1.tif',
                         './testcollect/pilatus300k/test1_00001.tif')
            # shutil.copy2('test/files/test_file2.tif',
            #              './testcollect/pilatus300k/test1_00002.tif')
            shutil.copy2('test/files/test_file3.tif',
                         './testcollect/pilatus300k/test1_00003.tif')
            # shutil.copy2('test/files/test_file4.tif',
            #              './testcollect/pilatus300k/test1_00004.tif')
            shutil.copy2('test/files/test_file5.tif',
                         './testcollect/pilatus300k/test1_00005.tif')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 8)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.tif:0:5']")
                for i in range(1, 6):
                    if i not in [3, 5]:
                        self.assertEqual(
                            svl[i],
                            ' * append testcollect/pilatus300k/'
                            'test1_%05d.tif ' % (i - 1)
                        )
                    else:
                        self.assertTrue(
                            svl[i].startswith("Cannot open any of "))

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (4, 195, 487))
                ii = 0
                for i in range(6):
                    if i not in [2, 4]:
                        fbuffer = fabio.open(
                            './testcollect/pilatus300k/test1_%05d.tif' % i)
                        fimage = fbuffer.data[...]
                        image = buffer[ii, :, :]
                        self.assertTrue((image == fimage).all())
                        ii += 1
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./testcollect/pilatus300k/test1_00000.tif')
            os.remove('./testcollect/pilatus300k/test1_00001.tif')
            # os.remove('./testcollect/pilatus300k/test1_00002.tif')
            os.remove('./testcollect/pilatus300k/test1_00003.tif')
            # os.remove('./testcollect/pilatus300k/test1_00004.tif')
            os.remove('./testcollect/pilatus300k/test1_00005.tif')
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_append_file_withpostrun_tif_pilatus300k_wait(self):
        """ test nxsconfig append file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                shutil.copy2('test/files/test_file0.tif',
                             './testcollect/pilatus300k/test1_00000.tif')
                shutil.copy2('test/files/test_file1.tif',
                             './testcollect/pilatus300k/test1_00001.tif')
                shutil.copy2('test/files/test_file2.tif',
                             './testcollect/pilatus300k/test1_00002.tif')

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 8)

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (3, 195, 487))
                ii = 0
                for i in range(3):
                    fbuffer = fabio.open(
                        './testcollect/pilatus300k/test1_%05d.tif' % i)
                    fimage = fbuffer.data[...]
                    image = buffer[ii, :, :]
                    self.assertTrue((image == fimage).all())
                    ii += 1
                nxsfile.close()

                shutil.copy2('test/files/test_file3.tif',
                             './testcollect/pilatus300k/test1_00003.tif')
                shutil.copy2('test/files/test_file4.tif',
                             './testcollect/pilatus300k/test1_00004.tif')

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (5, 195, 487))
                ii = 0
                for i in range(5):
                    fbuffer = fabio.open(
                        './testcollect/pilatus300k/test1_%05d.tif' % i)
                    fimage = fbuffer.data[...]
                    image = buffer[ii, :, :]
                    self.assertTrue((image == fimage).all())
                    ii += 1
                nxsfile.close()

                os.remove('./testcollect/pilatus300k/test1_00000.tif')
                os.remove('./testcollect/pilatus300k/test1_00001.tif')
                os.remove('./testcollect/pilatus300k/test1_00002.tif')
                os.remove('./testcollect/pilatus300k/test1_00003.tif')
                os.remove('./testcollect/pilatus300k/test1_00004.tif')
                os.remove(filename)

        finally:
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_append_file_withpostrun_tif_pilatus300k_missing(self):
        """ test nxsconfig append file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            shutil.copy2('test/files/test_file0.tif',
                         './testcollect/pilatus300k/test1_00000.tif')
            shutil.copy2('test/files/test_file1.tif',
                         './testcollect/pilatus300k/test1_00001.tif')
            shutil.copy2('test/files/test_file2.tif',
                         './testcollect/pilatus300k/test1_00002.tif')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 6)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.tif:0:5']")
                for i in range(1, 5):
                    if i not in [4]:
                        self.assertEqual(
                            svl[i],
                            ' * append testcollect/pilatus300k/'
                            'test1_%05d.tif ' % (i - 1)
                        )
                    else:
                        self.assertTrue(
                            svl[i].startswith("Cannot open any of "))

                # if '-r' not in cmd:
                #      os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./testcollect/pilatus300k/test1_00000.tif')
            os.remove('./testcollect/pilatus300k/test1_00001.tif')
            os.remove('./testcollect/pilatus300k/test1_00002.tif')
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_append_file_withpostrun_cbf(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file.cbf', './test1_00000.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00001.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00002.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00003.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00004.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00005.cbf')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 8)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.cbf:0:5']")
                for i in range(1, 6):

                    self.assertTrue(svl[i].startswith(' * append '))
                    self.assertTrue(
                        svl[i].endswith('test1_%05d.cbf ' % (i - 1)))

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (6, 195, 487))
                for i in range(6):
                    fbuffer = fabio.open('./test1_%05d.cbf' % i)
                    fimage = fbuffer.data[...]
                    image = buffer[i, :, :]
                    self.assertTrue((image == fimage).all())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.cbf')
            os.remove('./test1_00001.cbf')
            os.remove('./test1_00002.cbf')
            os.remove('./test1_00003.cbf')
            os.remove('./test1_00004.cbf')
            os.remove('./test1_00005.cbf')

    def test_append_file_withpostrun_cbf_pilatus300k_comp(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r -s -c1 %s' %
             (filename, self.flags)).split(),
            ('nxscollect append  %s -c2 %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -c3 %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -c4 %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -c5 %s' %
             (filename, self.flags)).split(),
            ('nxscollect append  %s -s -c6 %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -s -c7 %s' %
             (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s -c8 %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s -c9' %
             (filename, self.flags)).split(),
        ]
        extra_commands = [
            ('nxscollect append  %s -r -s -c32008:0,2 %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s -c32008:0,2' %
             (filename, self.flags)).split(),
        ]
        if self.externalfilters and H5CPP:
            if hasattr(h5cpp.filter, "is_filter_available") \
               and h5cpp.filter.is_filter_available(32008):
                commands.extend(extra_commands)

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00000.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00001.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00002.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00003.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00004.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00005.cbf')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()
                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()
                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 8:
                    print(svl)
                self.assertEqual(len(svl), 8)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.cbf:0:5']")
                for i in range(1, 6):
                    self.assertTrue(
                        svl[i],
                        ' * append /home/jkotan/ndts/nexdatas.tools/'
                        'test1_%05d.cbf ' % (i - 1)
                    )

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (6, 195, 487))
                for i in range(6):
                    fbuffer = fabio.open(
                        './testcollect/pilatus300k/test1_%05d.cbf' % i)
                    fimage = fbuffer.data[...]
                    image = buffer[i, :, :]
                    self.assertTrue((image == fimage).all())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./testcollect/pilatus300k/test1_00000.cbf')
            os.remove('./testcollect/pilatus300k/test1_00001.cbf')
            os.remove('./testcollect/pilatus300k/test1_00002.cbf')
            os.remove('./testcollect/pilatus300k/test1_00003.cbf')
            os.remove('./testcollect/pilatus300k/test1_00004.cbf')
            os.remove('./testcollect/pilatus300k/test1_00005.cbf')
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_append_file_withpostrun_cbf_pilatus300k_skip(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00000.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00001.cbf')
            # shutil.copy2('test/files/test_file.cbf',
            #              './testcollect/pilatus300k/test1_00002.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00003.cbf')
            # shutil.copy2('test/files/test_file.cbf',
            #              './testcollect/pilatus300k/test1_00004.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00005.cbf')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 8)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.cbf:0:5']")
                for i in range(1, 6):
                    if i not in [3, 5]:
                        self.assertEqual(
                            svl[i],
                            ' * append testcollect/pilatus300k/'
                            'test1_%05d.cbf ' % (i - 1)
                        )
                    else:
                        self.assertTrue(
                            svl[i].startswith("Cannot open any of "))

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (4, 195, 487))
                ii = 0
                for i in range(6):
                    if i not in [2, 4]:
                        fbuffer = fabio.open(
                            './testcollect/pilatus300k/test1_%05d.cbf' % i)
                        fimage = fbuffer.data[...]
                        image = buffer[ii, :, :]
                        self.assertTrue((image == fimage).all())
                        ii += 1
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./testcollect/pilatus300k/test1_00000.cbf')
            os.remove('./testcollect/pilatus300k/test1_00001.cbf')
            # os.remove('./testcollect/pilatus300k/test1_00002.cbf')
            os.remove('./testcollect/pilatus300k/test1_00003.cbf')
            # os.remove('./testcollect/pilatus300k/test1_00004.cbf')
            os.remove('./testcollect/pilatus300k/test1_00005.cbf')
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_append_file_withpostrun_cbf_pilatus300k_wait(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                shutil.copy2('test/files/test_file.cbf',
                             './testcollect/pilatus300k/test1_00000.cbf')
                shutil.copy2('test/files/test_file.cbf',
                             './testcollect/pilatus300k/test1_00001.cbf')
                shutil.copy2('test/files/test_file.cbf',
                             './testcollect/pilatus300k/test1_00002.cbf')

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 8)

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (3, 195, 487))
                ii = 0
                for i in range(3):
                    fbuffer = fabio.open(
                        './testcollect/pilatus300k/test1_%05d.cbf' % i)
                    fimage = fbuffer.data[...]
                    image = buffer[ii, :, :]
                    self.assertTrue((image == fimage).all())
                    ii += 1
                nxsfile.close()

                shutil.copy2('test/files/test_file.cbf',
                             './testcollect/pilatus300k/test1_00003.cbf')
                shutil.copy2('test/files/test_file.cbf',
                             './testcollect/pilatus300k/test1_00004.cbf')

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (5, 195, 487))
                ii = 0
                for i in range(5):
                    fbuffer = fabio.open(
                        './testcollect/pilatus300k/test1_%05d.cbf' % i)
                    fimage = fbuffer.data[...]
                    image = buffer[ii, :, :]
                    self.assertTrue((image == fimage).all())
                    ii += 1
                nxsfile.close()

                os.remove('./testcollect/pilatus300k/test1_00000.cbf')
                os.remove('./testcollect/pilatus300k/test1_00001.cbf')
                os.remove('./testcollect/pilatus300k/test1_00002.cbf')
                os.remove('./testcollect/pilatus300k/test1_00003.cbf')
                os.remove('./testcollect/pilatus300k/test1_00004.cbf')
                os.remove(filename)

        finally:
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_append_file_withpostrun_cbf_pilatus300k_missing(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00000.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00001.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00002.cbf')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 6)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.cbf:0:5']")
                for i in range(1, 5):
                    if i not in [4]:
                        self.assertEqual(
                            svl[i],
                            ' * append testcollect/pilatus300k/'
                            'test1_%05d.cbf ' % (i - 1)
                        )
                    else:
                        self.assertTrue(
                            svl[i].startswith("Cannot open any of "))

                # if '-r' not in cmd:
                #      os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./testcollect/pilatus300k/test1_00000.cbf')
            os.remove('./testcollect/pilatus300k/test1_00001.cbf')
            os.remove('./testcollect/pilatus300k/test1_00002.cbf')
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_append_file_withpostrun_raw(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
            "int8": [12, "NX_INT8", "int8", (1,)],
            "int16": [-123, "NX_INT16", "int16", (1,)],
            "int32": [12345, "NX_INT32", "int32", (1,)],
            "int64": [-12345, "NX_INT64", "int64", (1,)],
            "uint": [123, "NX_UINT", "uint64", (1,)],
            "uint8": [12, "NX_UINT8", "uint8", (1,)],
            "uint16": [123, "NX_UINT16", "uint16", (1,)],
            "uint32": [12345, "NX_UINT32", "uint32", (1,)],
            "uint64": [12345, "NX_UINT64", "uint64", (1,)],
            "float": [-12.345, "NX_FLOAT", "float64", (1,), 1.e-14],
            "number": [-12.345e+2, "NX_NUMBER", "float64", (1,), 1.e-14],
            "float32": [-12.345e-1, "NX_FLOAT32", "float32", (1,), 1.e-5],
            "float64": [-12.345, "NX_FLOAT64", "float64", (1,), 1.e-14],
        }

        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]

            attrs[k][0] = np.array(
                [[[attrs[k][0] * self.__rnd.randint(0, 3)
                   for c in range(mlen[1])]
                  for i in range(mlen[0])]
                 for _ in range(6)],
                dtype=attrs[k][2]
                )
            try:
                for i in range(6):
                    with open("rawtest1_%05d.dat" % i, "w") as fl:
                        attrs[k][0][i].tofile(fl)
                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    ins = entry.create_group("instrument", "NXinstrument")
                    det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    col = det.create_group("collection", "NXcollection")
                    postrun = col.create_field("postrun", "string")
                    postrun.write("rawtest1_%05d.dat:0:5")
                    atts = postrun.attributes
                    atts.create("fielddtype", "string").write(attrs[k][2])
                    atts.create("fieldshape", "string").write(
                        json.dumps(attrs[k][0].shape[1:]))
                    nxsfile.close()

                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = cmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    # print(svl)
                    self.assertEqual(len(svl), 8)
                    self.assertTrue(
                        svl[0],
                        "populate: /entry12345:NXentry/"
                        "instrument:NXinstrument/pilatus300k:NXdetector"
                        "/data with ['test1_%05d.cbf:0:5']")
                    for i in range(1, 6):
                        self.assertTrue(svl[i].startswith(' * append '))
                        self.assertTrue(
                            svl[i].endswith('test1_%05d.dat ' % (i - 1)))

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    det = ins.open("pilatus300k")
                    dt = det.open("data")
                    buffer = dt.read()
                    self.assertEqual(buffer.shape, attrs[k][0].shape)
                    for i in range(6):
                        fimage = attrs[k][0][i]
                        image = buffer[i, :, :]
                        self.assertTrue((image == fimage).all())
                    nxsfile.close()
                    os.remove(filename)

            finally:
                for i in range(6):
                    os.remove("rawtest1_%05d.dat" % i)

    def test_append_file_withpostrun_h5(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
            "int8": [12, "NX_INT8", "int8", (1,)],
            "int16": [-123, "NX_INT16", "int16", (1,)],
            "int32": [12345, "NX_INT32", "int32", (1,)],
            "int64": [-12345, "NX_INT64", "int64", (1,)],
            "uint": [123, "NX_UINT", "uint64", (1,)],
            "uint8": [12, "NX_UINT8", "uint8", (1,)],
            "uint16": [123, "NX_UINT16", "uint16", (1,)],
            "uint32": [12345, "NX_UINT32", "uint32", (1,)],
            "uint64": [12345, "NX_UINT64", "uint64", (1,)],
            "float": [-12.345, "NX_FLOAT", "float64", (1,), 1.e-14],
            "number": [-12.345e+2, "NX_NUMBER", "float64", (1,), 1.e-14],
            "float32": [-12.345e-1, "NX_FLOAT32", "float32", (1,), 1.e-5],
            "float64": [-12.345, "NX_FLOAT64", "float64", (1,), 1.e-14],
        }

        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]

            attrs[k][0] = np.array(
                [[[attrs[k][0] * self.__rnd.randint(0, 3)
                   for c in range(mlen[1])]
                  for i in range(mlen[0])]
                 for _ in range(6)],
                dtype=attrs[k][2]
                )
            try:
                for i in range(6):
                    fl = filewriter.create_file("h5test1_%05d.h5" % i,
                                                overwrite=True)
                    rt = fl.root()
                    shp = attrs[k][0][i].shape
                    data = rt.create_field("data", attrs[k][2], shp, shp)
                    data.write(attrs[k][0][i])
                    data.close()
                    fl.close()
                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    ins = entry.create_group("instrument", "NXinstrument")
                    det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    col = det.create_group("collection", "NXcollection")
                    postrun = col.create_field("postrun", "string")
                    postrun.write("h5test1_%05d.h5:0:5")
                    nxsfile.close()

                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = cmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    self.assertEqual(len(svl), 8)
                    self.assertTrue(
                        svl[0],
                        "populate: /entry12345:NXentry/"
                        "instrument:NXinstrument/pilatus300k:NXdetector"
                        "/data with ['test1_%05d.cbf:0:5']")
                    for i in range(1, 6):
                        self.assertTrue(svl[i].startswith(' * append '))
                        self.assertTrue(
                            svl[i].endswith('test1_%05d.h5 ' % (i - 1)))

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    det = ins.open("pilatus300k")
                    dt = det.open("data")
                    buffer = dt.read()
                    self.assertEqual(buffer.shape, attrs[k][0].shape)
                    for i in range(6):
                        fimage = attrs[k][0][i]
                        image = buffer[i, :, :]
                        self.assertTrue((image == fimage).all())
                    nxsfile.close()
                    os.remove(filename)

            finally:
                pass
                for i in range(6):
                    os.remove("h5test1_%05d.h5" % i)

    def test_append_file_parameters_tif(self):
        """ test nxsconfig append file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        ifiles = 'test1_%05d.tif:0:5'
        path = '/entry12345/instrument/pilatus300k/data'
        commands = [
            ('nxscollect append  %s %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -r %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -r %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -s %s --input-files %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -r -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -r -s %s --input-files %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file0.tif', './test1_00000.tif')
            shutil.copy2('test/files/test_file1.tif', './test1_00001.tif')
            shutil.copy2('test/files/test_file2.tif', './test1_00002.tif')
            shutil.copy2('test/files/test_file3.tif', './test1_00003.tif')
            shutil.copy2('test/files/test_file4.tif', './test1_00004.tif')
            shutil.copy2('test/files/test_file5.tif', './test1_00005.tif')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                # er =
                mystderr.getvalue()

                # self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 8:
                    print(svl)
                self.assertEqual(len(svl), 8)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.tif:0:5']")
                for i in range(1, 6):

                    self.assertTrue(svl[i].startswith(' * append '))
                    self.assertTrue(
                        svl[i].endswith('test1_%05d.tif ' % (i - 1)))

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (6, 195, 487))
                for i in range(6):
                    fbuffer = fabio.open('./test1_%05d.tif' % i)
                    fimage = fbuffer.data[...]
                    image = buffer[i, :, :]
                    self.assertTrue((image == fimage).all())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.tif')
            os.remove('./test1_00001.tif')
            os.remove('./test1_00002.tif')
            os.remove('./test1_00003.tif')
            os.remove('./test1_00004.tif')
            os.remove('./test1_00005.tif')

    def test_append_file_parameters_tif_list(self):
        """ test nxsconfig append file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        ifiles = 'test1_00000.tif,test1_00001.tif,test1_00002.tif,' \
            'test1_00003.tif,test1_00004.tif,test1_00005.tif'
        path = '/entry12345/instrument/pilatus300k/data'
        commands = [
            ('nxscollect append  %s %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -r %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -r %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -s %s --input-files %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -r -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -r -s %s --input-files %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file0.tif', './test1_00000.tif')
            shutil.copy2('test/files/test_file1.tif', './test1_00001.tif')
            shutil.copy2('test/files/test_file2.tif', './test1_00002.tif')
            shutil.copy2('test/files/test_file3.tif', './test1_00003.tif')
            shutil.copy2('test/files/test_file4.tif', './test1_00004.tif')
            shutil.copy2('test/files/test_file5.tif', './test1_00005.tif')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                # er =
                mystderr.getvalue()

                # self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 8:
                    print(svl)
                self.assertEqual(len(svl), 8)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.tif:0:5']")
                for i in range(1, 6):

                    self.assertTrue(svl[i].startswith(' * append '))
                    self.assertTrue(
                        svl[i].endswith('test1_%05d.tif ' % (i - 1)))

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (6, 195, 487))
                for i in range(6):
                    fbuffer = fabio.open('./test1_%05d.tif' % i)
                    fimage = fbuffer.data[...]
                    image = buffer[i, :, :]
                    self.assertTrue((image == fimage).all())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.tif')
            os.remove('./test1_00001.tif')
            os.remove('./test1_00002.tif')
            os.remove('./test1_00003.tif')
            os.remove('./test1_00004.tif')
            os.remove('./test1_00005.tif')

    def test_append_file_parameters_tif_list_sep(self):
        """ test nxsconfig append file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        ifiles = 'test1_00000.tif:test1_00001.tif:test1_00002.tif:' \
            'test1_00003.tif:test1_00004.tif:test1_00005.tif'
        path = '/entry12345/instrument/pilatus300k/data'
        commands = [
            ('nxscollect append  %s %s -i %s -p %s --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s %s -i %s --path %s --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -r %s -i %s -p %s --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -r %s -i %s --path %s --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -s %s --input-files %s -p %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -s %s --input-files %s --path %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -r -s %s --input-files %s -p %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -r -s %s --input-files %s --path %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file0.tif', './test1_00000.tif')
            shutil.copy2('test/files/test_file1.tif', './test1_00001.tif')
            shutil.copy2('test/files/test_file2.tif', './test1_00002.tif')
            shutil.copy2('test/files/test_file3.tif', './test1_00003.tif')
            shutil.copy2('test/files/test_file4.tif', './test1_00004.tif')
            shutil.copy2('test/files/test_file5.tif', './test1_00005.tif')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                # er =
                mystderr.getvalue()

                # self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 8:
                    print(svl)
                self.assertEqual(len(svl), 8)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.tif:0:5']")
                for i in range(1, 6):

                    self.assertTrue(svl[i].startswith(' * append '))
                    self.assertTrue(
                        svl[i].endswith('test1_%05d.tif ' % (i - 1)))

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (6, 195, 487))
                for i in range(6):
                    fbuffer = fabio.open('./test1_%05d.tif' % i)
                    fimage = fbuffer.data[...]
                    image = buffer[i, :, :]
                    self.assertTrue((image == fimage).all())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.tif')
            os.remove('./test1_00001.tif')
            os.remove('./test1_00002.tif')
            os.remove('./test1_00003.tif')
            os.remove('./test1_00004.tif')
            os.remove('./test1_00005.tif')

    def test_append_file_parameters_cbf(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        ifiles = 'test1_%05d.cbf:0:5'
        path = '/entry12345/instrument/pilatus300k/data'
        commands = [
            ('nxscollect append  %s %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -r %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -r %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -s %s --input-files %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -r -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -r -s %s --input-files %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file.cbf', './test1_00000.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00001.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00002.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00003.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00004.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00005.cbf')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                # er =
                mystderr.getvalue()

                # self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 8:
                    print(svl)
                self.assertEqual(len(svl), 8)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.cbf:0:5']")
                for i in range(1, 6):

                    self.assertTrue(svl[i].startswith(' * append '))
                    self.assertTrue(
                        svl[i].endswith('test1_%05d.cbf ' % (i - 1)))

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (6, 195, 487))
                for i in range(6):
                    fbuffer = fabio.open('./test1_%05d.cbf' % i)
                    fimage = fbuffer.data[...]
                    image = buffer[i, :, :]
                    self.assertTrue((image == fimage).all())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.cbf')
            os.remove('./test1_00001.cbf')
            os.remove('./test1_00002.cbf')
            os.remove('./test1_00003.cbf')
            os.remove('./test1_00004.cbf')
            os.remove('./test1_00005.cbf')

    def test_append_file_parameters_cbf_list(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        ifiles = 'test1_00000.cbf,test1_00001.cbf,test1_00002.cbf,' \
            'test1_00003.cbf,test1_00004.cbf,test1_00005.cbf'
        path = '/entry12345/instrument/pilatus300k/data'
        commands = [
            ('nxscollect append  %s %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -r %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -r %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -s %s --input-files %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -r -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -r -s %s --input-files %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file.cbf', './test1_00000.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00001.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00002.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00003.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00004.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00005.cbf')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                # er =
                mystderr.getvalue()

                # self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 8:
                    print(svl)
                self.assertEqual(len(svl), 8)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.cbf:0:5']")
                for i in range(1, 6):

                    self.assertTrue(svl[i].startswith(' * append '))
                    self.assertTrue(
                        svl[i].endswith('test1_%05d.cbf ' % (i - 1)))

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (6, 195, 487))
                for i in range(6):
                    fbuffer = fabio.open('./test1_%05d.cbf' % i)
                    fimage = fbuffer.data[...]
                    image = buffer[i, :, :]
                    self.assertTrue((image == fimage).all())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.cbf')
            os.remove('./test1_00001.cbf')
            os.remove('./test1_00002.cbf')
            os.remove('./test1_00003.cbf')
            os.remove('./test1_00004.cbf')
            os.remove('./test1_00005.cbf')

    def test_append_file_parameters_cbf_list_sep(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        ifiles = 'test1_00000.cbf:test1_00001.cbf:test1_00002.cbf:' \
            'test1_00003.cbf:test1_00004.cbf:test1_00005.cbf'
        path = '/entry12345/instrument/pilatus300k/data'
        commands = [
            ('nxscollect append  %s %s -i %s -p %s --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s %s -i %s --path %s --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -r %s -i %s -p %s --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -r %s -i %s --path %s --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -s %s --input-files %s -p %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -s %s --input-files %s --path %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append  %s -r -s %s --input-files %s -p %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append %s -r -s %s --input-files %s --path %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file.cbf', './test1_00000.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00001.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00002.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00003.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00004.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00005.cbf')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                # er =
                mystderr.getvalue()

                # self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 8:
                    print(svl)
                self.assertEqual(len(svl), 8)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.cbf:0:5']")
                for i in range(1, 6):

                    self.assertTrue(svl[i].startswith(' * append '))
                    self.assertTrue(
                        svl[i].endswith('test1_%05d.cbf ' % (i - 1)))

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                buffer = dt.read()
                self.assertEqual(buffer.shape, (6, 195, 487))
                for i in range(6):
                    fbuffer = fabio.open('./test1_%05d.cbf' % i)
                    fimage = fbuffer.data[...]
                    image = buffer[i, :, :]
                    self.assertTrue((image == fimage).all())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.cbf')
            os.remove('./test1_00001.cbf')
            os.remove('./test1_00002.cbf')
            os.remove('./test1_00003.cbf')
            os.remove('./test1_00004.cbf')
            os.remove('./test1_00005.cbf')

    def test_append_file_parameters_raw(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
            "int8": [12, "NX_INT8", "int8", (1,)],
            "int16": [-123, "NX_INT16", "int16", (1,)],
            "int32": [12345, "NX_INT32", "int32", (1,)],
            "int64": [-12345, "NX_INT64", "int64", (1,)],
            "uint": [123, "NX_UINT", "uint64", (1,)],
            "uint8": [12, "NX_UINT8", "uint8", (1,)],
            "uint16": [123, "NX_UINT16", "uint16", (1,)],
            "uint32": [12345, "NX_UINT32", "uint32", (1,)],
            "uint64": [12345, "NX_UINT64", "uint64", (1,)],
            "float": [-12.345, "NX_FLOAT", "float64", (1,), 1.e-14],
            "number": [-12.345e+2, "NX_NUMBER", "float64", (1,), 1.e-14],
            "float32": [-12.345e-1, "NX_FLOAT32", "float32", (1,), 1.e-5],
            "float64": [-12.345, "NX_FLOAT64", "float64", (1,), 1.e-14],
        }

        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]

            attrs[k][0] = np.array(
                [[[attrs[k][0] * self.__rnd.randint(0, 3)
                   for c in range(mlen[1])]
                  for i in range(mlen[0])]
                 for _ in range(6)],
                dtype=attrs[k][2]
                )
            try:
                for i in range(6):
                    with open("rawtest1_%05d.dat" % i, "w") as fl:
                        attrs[k][0][i].tofile(fl)
                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    # to be created
                    # ins = entry.create_group("instrument", "NXinstrument")
                    # det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    nxsfile.close()
                    pcmd = cmd
                    pcmd.extend(["-i", "rawtest1_%05d.dat:0:5"])
                    pcmd.extend(
                        ["-p", '/entry12345/instrument/pilatus300k/data'])
                    pcmd.extend(
                        ["--shape", json.dumps(attrs[k][0].shape[1:])])
                    pcmd.extend(
                        ["--dtype", attrs[k][2]])

                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = pcmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    self.assertEqual(len(svl), 8)
                    self.assertTrue(
                        svl[0],
                        "populate: /entry12345:NXentry/"
                        "instrument:NXinstrument/pilatus300k:NXdetector"
                        "/data with ['test1_%05d.cbf:0:5']")
                    for i in range(1, 6):
                        self.assertTrue(svl[i].startswith(' * append '))
                        self.assertTrue(
                            svl[i].endswith('test1_%05d.dat ' % (i - 1)))

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    det = ins.open("pilatus300k")
                    dt = det.open("data")
                    buffer = dt.read()
                    self.assertEqual(buffer.shape, attrs[k][0].shape)
                    for i in range(6):
                        fimage = attrs[k][0][i]
                        image = buffer[i, :, :]
                        self.assertTrue((image == fimage).all())
                    nxsfile.close()
                    os.remove(filename)

            finally:
                for i in range(6):
                    os.remove("rawtest1_%05d.dat" % i)

    def test_append_file_parameters_nxs(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
            "int8": [12, "NX_INT8", "int8", (1,)],
            "int16": [-123, "NX_INT16", "int16", (1,)],
            "int32": [12345, "NX_INT32", "int32", (1,)],
            "int64": [-12345, "NX_INT64", "int64", (1,)],
            "uint": [123, "NX_UINT", "uint64", (1,)],
            "uint8": [12, "NX_UINT8", "uint8", (1,)],
            "uint16": [123, "NX_UINT16", "uint16", (1,)],
            "uint32": [12345, "NX_UINT32", "uint32", (1,)],
            "uint64": [12345, "NX_UINT64", "uint64", (1,)],
            "float": [-12.345, "NX_FLOAT", "float64", (1,), 1.e-14],
            "number": [-12.345e+2, "NX_NUMBER", "float64", (1,), 1.e-14],
            "float32": [-12.345e-1, "NX_FLOAT32", "float32", (1,), 1.e-5],
            "float64": [-12.345, "NX_FLOAT64", "float64", (1,), 1.e-14],
        }

        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]

            attrs[k][0] = np.array(
                [[[attrs[k][0] * self.__rnd.randint(0, 3)
                   for c in range(mlen[1])]
                  for i in range(mlen[0])]
                 for _ in range(6)],
                dtype=attrs[k][2]
                )
            try:
                for i in range(6):
                    fl = filewriter.create_file("h5test1_%05d.nxs" % i,
                                                overwrite=True)
                    rt = fl.root()

                    at = rt.attributes.create("default", "string")
                    at.write("entry12345")
                    at.close()

                    entry = rt.create_group("entry12345", "NXentry")
                    at = entry.attributes.create("default", "string")
                    at.write("data")
                    at.close()

                    dt = entry.create_group("data", "NXdata")
                    at = dt.attributes.create("signal", "string")
                    at.write("data")
                    at.close()

                    shp = attrs[k][0][i].shape
                    data = dt.create_field("data", attrs[k][2], shp, shp)
                    data.write(attrs[k][0][i])
                    data.close()

                    dt.close()
                    entry.close()
                    fl.close()

                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    ins = entry.create_group("instrument", "NXinstrument")
                    # det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    # col = det.create_group("collection", "NXcollection")
                    # postrun = col.create_field("postrun", "string")
                    # postrun.write("h5test1_%05d.h5:0:5")
                    nxsfile.close()

                    pcmd = cmd
                    pcmd.extend(["-i", "h5test1_%05d.nxs:0:5"])
                    pcmd.extend(
                        ["-p", '/entry12345/instrument/pilatus300k/data'])

                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = pcmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    if len(svl) != 8:
                        print(svl)
                    self.assertEqual(len(svl), 8)
                    self.assertTrue(
                        svl[0],
                        "populate: /entry12345:NXentry/"
                        "instrument:NXinstrument/pilatus300k:NXdetector"
                        "/data with ['test1_%05d.cbf:0:5']")
                    for i in range(1, 6):
                        self.assertTrue(svl[i].startswith(' * append '))
                        self.assertTrue(
                            svl[i].endswith('test1_%05d.nxs ' % (i - 1)))

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    det = ins.open("pilatus300k")
                    dt = det.open("data")
                    buffer = dt.read()
                    self.assertEqual(buffer.shape, attrs[k][0].shape)
                    for i in range(6):
                        fimage = attrs[k][0][i]
                        image = buffer[i, :, :]
                        self.assertTrue((image == fimage).all())
                    nxsfile.close()
                    os.remove(filename)

            finally:
                pass
                for i in range(6):
                    os.remove("h5test1_%05d.nxs" % i)

    def test_append_file_parameters_nxs_3d_many(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
            "int8": [12, "NX_INT8", "int8", (1,)],
            "int16": [-123, "NX_INT16", "int16", (1,)],
            "int32": [12345, "NX_INT32", "int32", (1,)],
            "int64": [-12345, "NX_INT64", "int64", (1,)],
            "uint": [123, "NX_UINT", "uint64", (1,)],
            "uint8": [12, "NX_UINT8", "uint8", (1,)],
            "uint16": [123, "NX_UINT16", "uint16", (1,)],
            "uint32": [12345, "NX_UINT32", "uint32", (1,)],
            "uint64": [12345, "NX_UINT64", "uint64", (1,)],
            "float": [-12.345, "NX_FLOAT", "float64", (1,), 1.e-14],
            "number": [-12.345e+2, "NX_NUMBER", "float64", (1,), 1.e-14],
            "float32": [-12.345e-1, "NX_FLOAT32", "float32", (1,), 1.e-5],
            "float64": [-12.345, "NX_FLOAT64", "float64", (1,), 1.e-14],
        }

        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 20),
                    self.__rnd.randint(10, 20),
                    self.__rnd.randint(10, 20)]

            attrs[k][0] = np.array(
                [[[[attrs[k][0] * self.__rnd.randint(0, 3)
                    for d in range(mlen[2])]
                   for c in range(mlen[1])]
                  for i in range(mlen[0])]
                 for _ in range(6)],
                dtype=attrs[k][2]
                )
            try:
                for i in range(6):
                    fl = filewriter.create_file("h5test1_%05d.nxs" % i,
                                                overwrite=True)
                    rt = fl.root()

                    at = rt.attributes.create("default", "string")
                    at.write("entry12345")
                    at.close()

                    entry = rt.create_group("entry12345", "NXentry")
                    at = entry.attributes.create("default", "string")
                    at.write("data")
                    at.close()

                    dt = entry.create_group("data", "NXdata")
                    at = dt.attributes.create("signal", "string")
                    at.write("data")
                    at.close()

                    shp = attrs[k][0][i].shape
                    data = dt.create_field("data", attrs[k][2], shp, shp)
                    data.write(attrs[k][0][i])
                    data.close()

                    dt.close()
                    entry.close()
                    fl.close()

                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    ins = entry.create_group("instrument", "NXinstrument")
                    # det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    # col = det.create_group("collection", "NXcollection")
                    # postrun = col.create_field("postrun", "string")
                    # postrun.write("h5test1_%05d.h5:0:5")
                    nxsfile.close()

                    pcmd = cmd
                    pcmd.extend(["-i", "h5test1_%05d.nxs:0:5"])
                    pcmd.extend(
                        ["-p", '/entry12345/instrument/pilatus300k/data'])

                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = pcmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    if len(svl) != 8:
                        print(svl)
                    self.assertEqual(len(svl), 8)
                    self.assertTrue(
                        svl[0],
                        "populate: /entry12345:NXentry/"
                        "instrument:NXinstrument/pilatus300k:NXdetector"
                        "/data with ['test1_%05d.cbf:0:5']")
                    for i in range(1, 6):
                        self.assertTrue(svl[i].startswith(' * append '))
                        self.assertTrue(
                            svl[i].endswith('test1_%05d.nxs ' % (i - 1)))
                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)

                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    det = ins.open("pilatus300k")
                    dt = det.open("data")
                    buffer = dt.read()
                    self.assertEqual(
                        buffer.shape[0],
                        attrs[k][0].shape[0] * attrs[k][0].shape[1])
                    self.assertEqual(buffer.shape[1:],
                                     attrs[k][0].shape[2:])
                    for i in range(6):
                        fimage = attrs[k][0][i]
                        image = buffer[
                            i * attrs[k][0].shape[1]:
                            (i + 1) * attrs[k][0].shape[1], :, :]
                        self.assertTrue((image == fimage).all())
                    nxsfile.close()
                    os.remove(filename)

            finally:
                pass
                for i in range(6):
                    os.remove("h5test1_%05d.nxs" % i)

    def test_append_file_parameters_nxs_1d(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
            "int8": [12, "NX_INT8", "int8", (1,)],
            "int16": [-123, "NX_INT16", "int16", (1,)],
            "int32": [12345, "NX_INT32", "int32", (1,)],
            "int64": [-12345, "NX_INT64", "int64", (1,)],
            "uint": [123, "NX_UINT", "uint64", (1,)],
            "uint8": [12, "NX_UINT8", "uint8", (1,)],
            "uint16": [123, "NX_UINT16", "uint16", (1,)],
            "uint32": [12345, "NX_UINT32", "uint32", (1,)],
            "uint64": [12345, "NX_UINT64", "uint64", (1,)],
            "float": [-12.345, "NX_FLOAT", "float64", (1,), 1.e-14],
            "number": [-12.345e+2, "NX_NUMBER", "float64", (1,), 1.e-14],
            "float32": [-12.345e-1, "NX_FLOAT32", "float32", (1,), 1.e-5],
            "float64": [-12.345, "NX_FLOAT64", "float64", (1,), 1.e-14],
        }

        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200)]

            attrs[k][0] = np.array(
                [[attrs[k][0] * self.__rnd.randint(0, 3)
                  for i in range(mlen[0])]
                 for _ in range(6)],
                dtype=attrs[k][2]
            )
            try:
                for i in range(6):
                    fl = filewriter.create_file("h5test1_%05d.nxs" % i,
                                                overwrite=True)
                    rt = fl.root()

                    at = rt.attributes.create("default", "string")
                    at.write("entry12345")
                    at.close()

                    entry = rt.create_group("entry12345", "NXentry")
                    at = entry.attributes.create("default", "string")
                    at.write("data")
                    at.close()

                    dt = entry.create_group("data", "NXdata")
                    at = dt.attributes.create("signal", "string")
                    at.write("data")
                    at.close()

                    shp = attrs[k][0][i].shape
                    data = dt.create_field("data", attrs[k][2], shp, shp)
                    data.write(attrs[k][0][i])
                    data.close()

                    dt.close()
                    entry.close()
                    fl.close()

                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    ins = entry.create_group("instrument", "NXinstrument")
                    # det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    # col = det.create_group("collection", "NXcollection")
                    # postrun = col.create_field("postrun", "string")
                    # postrun.write("h5test1_%05d.h5:0:5")
                    nxsfile.close()

                    pcmd = cmd
                    pcmd.extend(["-i", "h5test1_%05d.nxs:0:5"])
                    pcmd.extend(
                        ["-p", '/entry12345/instrument/pilatus300k/data'])

                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = pcmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    if len(svl) != 8:
                        print(svl)
                    self.assertEqual(len(svl), 8)
                    self.assertTrue(
                        svl[0],
                        "populate: /entry12345:NXentry/"
                        "instrument:NXinstrument/pilatus300k:NXdetector"
                        "/data with ['test1_%05d.cbf:0:5']")
                    for i in range(1, 6):
                        self.assertTrue(svl[i].startswith(' * append '))
                        self.assertTrue(
                            svl[i].endswith('test1_%05d.nxs ' % (i - 1)))

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    det = ins.open("pilatus300k")
                    dt = det.open("data")
                    buffer = dt.read()
                    self.assertEqual(buffer.shape, attrs[k][0].shape)
                    for i in range(6):
                        fimage = attrs[k][0][i]
                        image = buffer[i, :]
                        self.assertTrue((image == fimage).all())
                    nxsfile.close()
                    os.remove(filename)

            finally:
                pass
                for i in range(6):
                    os.remove("h5test1_%05d.nxs" % i)

    def test_append_file_parameters_nxs_3d(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
            "int8": [12, "NX_INT8", "int8", (1,)],
            "int16": [-123, "NX_INT16", "int16", (1,)],
            "int32": [12345, "NX_INT32", "int32", (1,)],
            "int64": [-12345, "NX_INT64", "int64", (1,)],
            "uint": [123, "NX_UINT", "uint64", (1,)],
            "uint8": [12, "NX_UINT8", "uint8", (1,)],
            "uint16": [123, "NX_UINT16", "uint16", (1,)],
            "uint32": [12345, "NX_UINT32", "uint32", (1,)],
            "uint64": [12345, "NX_UINT64", "uint64", (1,)],
            "float": [-12.345, "NX_FLOAT", "float64", (1,), 1.e-14],
            "number": [-12.345e+2, "NX_NUMBER", "float64", (1,), 1.e-14],
            "float32": [-12.345e-1, "NX_FLOAT32", "float32", (1,), 1.e-5],
            "float64": [-12.345, "NX_FLOAT64", "float64", (1,), 1.e-14],
        }

        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]

            attrs[k][0] = np.array(
                [[[attrs[k][0] * self.__rnd.randint(0, 3)
                   for c in range(mlen[1])]
                  for i in range(mlen[0])]
                 for _ in range(6)],
                dtype=attrs[k][2]
                )
            try:
                fl = filewriter.create_file("h5test1_00001.nxs",
                                            overwrite=True)
                rt = fl.root()

                at = rt.attributes.create("default", "string")
                at.write("entry12345")
                at.close()

                entry = rt.create_group("entry12345", "NXentry")
                at = entry.attributes.create("default", "string")
                at.write("data")
                at.close()

                dt = entry.create_group("data", "NXdata")
                at = dt.attributes.create("signal", "string")
                at.write("data")
                at.close()

                shp = attrs[k][0].shape
                data = dt.create_field("data", attrs[k][2], shp, shp)
                data.write(attrs[k][0])
                data.close()

                dt.close()
                entry.close()
                fl.close()

                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    ins = entry.create_group("instrument", "NXinstrument")
                    # det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    # col = det.create_group("collection", "NXcollection")
                    # postrun = col.create_field("postrun", "string")
                    # postrun.write("h5test1_%05d.h5:0:5")
                    nxsfile.close()

                    pcmd = cmd
                    pcmd.extend(["-i", "h5test1_00001.nxs"])
                    pcmd.extend(
                        ["-p", '/entry12345/instrument/pilatus300k/data'])

                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = pcmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    if len(svl) != 3:
                        print(svl)
                    self.assertEqual(len(svl), 3)
                    self.assertTrue(
                        svl[0],
                        "populate: /entry12345:NXentry/"
                        "instrument:NXinstrument/pilatus300k:NXdetector"
                        "/data with ['h5test1_00001.nxs']")
                    self.assertTrue(svl[1].startswith(' * append '))
                    self.assertTrue(
                            svl[1].endswith('h5test1_00001.nxs '))

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    det = ins.open("pilatus300k")
                    dt = det.open("data")
                    buffer = dt.read()
                    self.assertEqual(buffer.shape, attrs[k][0].shape)
                    for i in range(6):
                        fimage = attrs[k][0][i]
                        image = buffer[i, :, :]
                        self.assertTrue((image == fimage).all())
                    nxsfile.close()
                    os.remove(filename)

            finally:
                os.remove("h5test1_00001.nxs")

    def test_append_file_parameters_nxs_path(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
            "int8": [12, "NX_INT8", "int8", (1,)],
            "int16": [-123, "NX_INT16", "int16", (1,)],
            "int32": [12345, "NX_INT32", "int32", (1,)],
            "int64": [-12345, "NX_INT64", "int64", (1,)],
            "uint": [123, "NX_UINT", "uint64", (1,)],
            "uint8": [12, "NX_UINT8", "uint8", (1,)],
            "uint16": [123, "NX_UINT16", "uint16", (1,)],
            "uint32": [12345, "NX_UINT32", "uint32", (1,)],
            "uint64": [12345, "NX_UINT64", "uint64", (1,)],
            "float": [-12.345, "NX_FLOAT", "float64", (1,), 1.e-14],
            "number": [-12.345e+2, "NX_NUMBER", "float64", (1,), 1.e-14],
            "float32": [-12.345e-1, "NX_FLOAT32", "float32", (1,), 1.e-5],
            "float64": [-12.345, "NX_FLOAT64", "float64", (1,), 1.e-14],
        }

        commands = [
            ('nxscollect append  %s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect append  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append %s -r -s %s' % (filename, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]

            attrs[k][0] = np.array(
                [[[attrs[k][0] * self.__rnd.randint(0, 3)
                   for c in range(mlen[1])]
                  for i in range(mlen[0])]
                 for _ in range(6)],
                dtype=attrs[k][2]
                )
            try:
                for i in range(6):
                    fl = filewriter.create_file("h5test1_%05d.nxs" % i,
                                                overwrite=True)
                    rt = fl.root()
                    entry = rt.create_group("entry345", "NXentry")

                    dt = entry.create_group("data", "NXdata")

                    shp = attrs[k][0][i].shape
                    data = dt.create_field("data", attrs[k][2], shp, shp)
                    data.write(attrs[k][0][i])
                    data.close()

                    dt.close()
                    entry.close()
                    fl.close()

                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    ins = entry.create_group("instrument", "NXinstrument")
                    # det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    # col = det.create_group("collection", "NXcollection")
                    # postrun = col.create_field("postrun", "string")
                    # postrun.write("h5test1_%05d.h5:0:5")
                    nxsfile.close()

                    pcmd = cmd
                    pcmd.extend(
                        ["-i", "h5test1_%05d.nxs://entry345/data/data:0:5"])
                    pcmd.extend(
                        ["-p", '/entry12345/instrument/pilatus300k/data'])

                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = pcmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    if len(svl) != 8:
                        print(svl)
                    self.assertEqual(len(svl), 8)
                    self.assertTrue(
                        svl[0],
                        "populate: /entry12345:NXentry/"
                        "instrument:NXinstrument/pilatus300k:NXdetector"
                        "/data with ['test1_%05d.nxs:0:5']")
                    for i in range(1, 6):
                        self.assertTrue(svl[i].startswith(' * append '))
                        self.assertTrue(
                            svl[i].endswith('test1_%05d.nxs ' % (i - 1)))

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    det = ins.open("pilatus300k")
                    dt = det.open("data")
                    buffer = dt.read()
                    self.assertEqual(buffer.shape, attrs[k][0].shape)
                    for i in range(6):
                        fimage = attrs[k][0][i]
                        image = buffer[i, :, :]
                        self.assertTrue((image == fimage).all())
                    nxsfile.close()
                    os.remove(filename)

            finally:
                pass
                for i in range(6):
                    os.remove("h5test1_%05d.nxs" % i)

    def test_test_file_withpostrun_tif(self):
        """ test nxsconfig test file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append --test  %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r -s %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file0.tif', './test1_00000.tif')
            shutil.copy2('test/files/test_file1.tif', './test1_00001.tif')
            shutil.copy2('test/files/test_file2.tif', './test1_00002.tif')
            shutil.copy2('test/files/test_file3.tif', './test1_00003.tif')
            shutil.copy2('test/files/test_file4.tif', './test1_00004.tif')
            shutil.copy2('test/files/test_file5.tif', './test1_00005.tif')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                # er =
                mystderr.getvalue()

                # self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 2)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.tif:0:5']")

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.tif')
            os.remove('./test1_00001.tif')
            os.remove('./test1_00002.tif')
            os.remove('./test1_00003.tif')
            os.remove('./test1_00004.tif')
            os.remove('./test1_00005.tif')

    def test_test_file_withpostrun_tif_pilatus300k(self):
        """ test nxsconfig test file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append --test  %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r -s %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            shutil.copy2('test/files/test_file0.tif',
                         './testcollect/pilatus300k/test1_00000.tif')
            shutil.copy2('test/files/test_file1.tif',
                         './testcollect/pilatus300k/test1_00001.tif')
            shutil.copy2('test/files/test_file2.tif',
                         './testcollect/pilatus300k/test1_00002.tif')
            shutil.copy2('test/files/test_file3.tif',
                         './testcollect/pilatus300k/test1_00003.tif')
            shutil.copy2('test/files/test_file4.tif',
                         './testcollect/pilatus300k/test1_00004.tif')
            shutil.copy2('test/files/test_file5.tif',
                         './testcollect/pilatus300k/test1_00005.tif')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 2)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.tif:0:5']")
                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./testcollect/pilatus300k/test1_00000.tif')
            os.remove('./testcollect/pilatus300k/test1_00001.tif')
            os.remove('./testcollect/pilatus300k/test1_00002.tif')
            os.remove('./testcollect/pilatus300k/test1_00003.tif')
            os.remove('./testcollect/pilatus300k/test1_00004.tif')
            os.remove('./testcollect/pilatus300k/test1_00005.tif')
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_test_file_withpostrun_tif_pilatus300k_skip(self):
        """ test nxsconfig test file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append --test  %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r -s %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            shutil.copy2('test/files/test_file0.tif',
                         './testcollect/pilatus300k/test1_00000.tif')
            shutil.copy2('test/files/test_file1.tif',
                         './testcollect/pilatus300k/test1_00001.tif')
            # shutil.copy2('test/files/test_file2.tif',
            #              './testcollect/pilatus300k/test1_00002.tif')
            shutil.copy2('test/files/test_file3.tif',
                         './testcollect/pilatus300k/test1_00003.tif')
            # shutil.copy2('test/files/test_file4.tif',
            #              './testcollect/pilatus300k/test1_00004.tif')
            shutil.copy2('test/files/test_file5.tif',
                         './testcollect/pilatus300k/test1_00005.tif')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                print(svl)
                self.assertEqual(len(svl), 4)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.tif:0:5']")

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./testcollect/pilatus300k/test1_00000.tif')
            os.remove('./testcollect/pilatus300k/test1_00001.tif')
            # os.remove('./testcollect/pilatus300k/test1_00002.tif')
            os.remove('./testcollect/pilatus300k/test1_00003.tif')
            # os.remove('./testcollect/pilatus300k/test1_00004.tif')
            os.remove('./testcollect/pilatus300k/test1_00005.tif')
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_test_file_withpostrun_tif_pilatus300k_wait(self):
        """ test nxsconfig test file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append --test  %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r -s %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                shutil.copy2('test/files/test_file0.tif',
                             './testcollect/pilatus300k/test1_00000.tif')
                shutil.copy2('test/files/test_file1.tif',
                             './testcollect/pilatus300k/test1_00001.tif')
                shutil.copy2('test/files/test_file2.tif',
                             './testcollect/pilatus300k/test1_00002.tif')

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()

                shutil.copy2('test/files/test_file3.tif',
                             './testcollect/pilatus300k/test1_00003.tif')
                shutil.copy2('test/files/test_file4.tif',
                             './testcollect/pilatus300k/test1_00004.tif')

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()

                os.remove('./testcollect/pilatus300k/test1_00000.tif')
                os.remove('./testcollect/pilatus300k/test1_00001.tif')
                os.remove('./testcollect/pilatus300k/test1_00002.tif')
                os.remove('./testcollect/pilatus300k/test1_00003.tif')
                os.remove('./testcollect/pilatus300k/test1_00004.tif')
                os.remove(filename)

        finally:
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_test_file_withpostrun_tif_pilatus300k_missing(self):
        """ test nxsconfig test file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append --test  %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            shutil.copy2('test/files/test_file0.tif',
                         './testcollect/pilatus300k/test1_00000.tif')
            shutil.copy2('test/files/test_file1.tif',
                         './testcollect/pilatus300k/test1_00001.tif')
            shutil.copy2('test/files/test_file2.tif',
                         './testcollect/pilatus300k/test1_00002.tif')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 3)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.tif:0:5']")

                # if '-r' not in cmd:
                #      os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./testcollect/pilatus300k/test1_00000.tif')
            os.remove('./testcollect/pilatus300k/test1_00001.tif')
            os.remove('./testcollect/pilatus300k/test1_00002.tif')
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_test_file_withpostrun_cbf(self):
        """ test nxsconfig test file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append --test  %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r -s %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file.cbf', './test1_00000.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00001.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00002.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00003.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00004.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00005.cbf')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 2)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.cbf:0:5']")

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.cbf')
            os.remove('./test1_00001.cbf')
            os.remove('./test1_00002.cbf')
            os.remove('./test1_00003.cbf')
            os.remove('./test1_00004.cbf')
            os.remove('./test1_00005.cbf')

    def test_test_file_withpostrun_cbf_pilatus300k(self):
        """ test nxsconfig test file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append --test  %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r -s %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00000.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00001.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00002.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00003.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00004.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00005.cbf')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 2)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.cbf:0:5']")

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./testcollect/pilatus300k/test1_00000.cbf')
            os.remove('./testcollect/pilatus300k/test1_00001.cbf')
            os.remove('./testcollect/pilatus300k/test1_00002.cbf')
            os.remove('./testcollect/pilatus300k/test1_00003.cbf')
            os.remove('./testcollect/pilatus300k/test1_00004.cbf')
            os.remove('./testcollect/pilatus300k/test1_00005.cbf')
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_test_file_withpostrun_cbf_pilatus300k_skip(self):
        """ test nxsconfig test file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append --test  %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r -s %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00000.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00001.cbf')
            # shutil.copy2('test/files/test_file.cbf',
            #              './testcollect/pilatus300k/test1_00002.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00003.cbf')
            # shutil.copy2('test/files/test_file.cbf',
            #              './testcollect/pilatus300k/test1_00004.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00005.cbf')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 4)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.cbf:0:5']")
                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./testcollect/pilatus300k/test1_00000.cbf')
            os.remove('./testcollect/pilatus300k/test1_00001.cbf')
            # os.remove('./testcollect/pilatus300k/test1_00002.cbf')
            os.remove('./testcollect/pilatus300k/test1_00003.cbf')
            # os.remove('./testcollect/pilatus300k/test1_00004.cbf')
            os.remove('./testcollect/pilatus300k/test1_00005.cbf')
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_test_file_withpostrun_cbf_pilatus300k_wait(self):
        """ test nxsconfig test file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append --test  %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r -s %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                shutil.copy2('test/files/test_file.cbf',
                             './testcollect/pilatus300k/test1_00000.cbf')
                shutil.copy2('test/files/test_file.cbf',
                             './testcollect/pilatus300k/test1_00001.cbf')
                shutil.copy2('test/files/test_file.cbf',
                             './testcollect/pilatus300k/test1_00002.cbf')

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 5)

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()

                shutil.copy2('test/files/test_file.cbf',
                             './testcollect/pilatus300k/test1_00003.cbf')
                shutil.copy2('test/files/test_file.cbf',
                             './testcollect/pilatus300k/test1_00004.cbf')

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()

                os.remove('./testcollect/pilatus300k/test1_00000.cbf')
                os.remove('./testcollect/pilatus300k/test1_00001.cbf')
                os.remove('./testcollect/pilatus300k/test1_00002.cbf')
                os.remove('./testcollect/pilatus300k/test1_00003.cbf')
                os.remove('./testcollect/pilatus300k/test1_00004.cbf')
                os.remove(filename)

        finally:
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_test_file_withpostrun_cbf_pilatus300k_missing(self):
        """ test nxsconfig test file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect append --test  %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        dircreated = False
        try:
            if not os.path.exists("./testcollect/pilatus300k"):
                os.makedirs("./testcollect/pilatus300k")
                dircreated = True

            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00000.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00001.cbf')
            shutil.copy2('test/files/test_file.cbf',
                         './testcollect/pilatus300k/test1_00002.cbf')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                col = det.create_group("collection", "NXcollection")
                postrun = col.create_field("postrun", "string")
                postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                self.assertEqual(len(svl), 3)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.cbf:0:5']")
                # if '-r' not in cmd:
                #      os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./testcollect/pilatus300k/test1_00000.cbf')
            os.remove('./testcollect/pilatus300k/test1_00001.cbf')
            os.remove('./testcollect/pilatus300k/test1_00002.cbf')
            if dircreated:
                shutil.rmtree("./testcollect")

    def test_test_file_withpostrun_raw(self):
        """ test nxsconfig test file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
            "int8": [12, "NX_INT8", "int8", (1,)],
            "int16": [-123, "NX_INT16", "int16", (1,)],
            "int32": [12345, "NX_INT32", "int32", (1,)],
            "int64": [-12345, "NX_INT64", "int64", (1,)],
            "uint": [123, "NX_UINT", "uint64", (1,)],
            "uint8": [12, "NX_UINT8", "uint8", (1,)],
            "uint16": [123, "NX_UINT16", "uint16", (1,)],
            "uint32": [12345, "NX_UINT32", "uint32", (1,)],
            "uint64": [12345, "NX_UINT64", "uint64", (1,)],
            "float": [-12.345, "NX_FLOAT", "float64", (1,), 1.e-14],
            "number": [-12.345e+2, "NX_NUMBER", "float64", (1,), 1.e-14],
            "float32": [-12.345e-1, "NX_FLOAT32", "float32", (1,), 1.e-5],
            "float64": [-12.345, "NX_FLOAT64", "float64", (1,), 1.e-14],
        }

        commands = [
            ('nxscollect append --test  %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r -s %s' %
             (filename, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]

            attrs[k][0] = np.array(
                [[[attrs[k][0] * self.__rnd.randint(0, 3)
                   for c in range(mlen[1])]
                  for i in range(mlen[0])]
                 for _ in range(6)],
                dtype=attrs[k][2]
                )
            try:
                for i in range(6):
                    with open("rawtest1_%05d.dat" % i, "w") as fl:
                        attrs[k][0][i].tofile(fl)
                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    ins = entry.create_group("instrument", "NXinstrument")
                    det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    col = det.create_group("collection", "NXcollection")
                    postrun = col.create_field("postrun", "string")
                    postrun.write("rawtest1_%05d.dat:0:5")
                    atts = postrun.attributes
                    atts.create("fielddtype", "string").write(attrs[k][2])
                    atts.create("fieldshape", "string").write(
                        json.dumps(attrs[k][0].shape[1:]))
                    nxsfile.close()

                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = cmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    self.assertEqual(len(svl), 2)
                    self.assertTrue(
                        svl[0],
                        "populate: /entry12345:NXentry/"
                        "instrument:NXinstrument/pilatus300k:NXdetector"
                        "/data with ['test1_%05d.cbf:0:5']")

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    det = ins.open("pilatus300k")
                    self.assertTrue('data' not in det.names())
                    nxsfile.close()
                    os.remove(filename)

            finally:
                for i in range(6):
                    os.remove("rawtest1_%05d.dat" % i)

    def test_test_file_withpostrun_h5(self):
        """ test nxsconfig test file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
            "int8": [12, "NX_INT8", "int8", (1,)],
            "int16": [-123, "NX_INT16", "int16", (1,)],
            "int32": [12345, "NX_INT32", "int32", (1,)],
            "int64": [-12345, "NX_INT64", "int64", (1,)],
            "uint": [123, "NX_UINT", "uint64", (1,)],
            "uint8": [12, "NX_UINT8", "uint8", (1,)],
            "uint16": [123, "NX_UINT16", "uint16", (1,)],
            "uint32": [12345, "NX_UINT32", "uint32", (1,)],
            "uint64": [12345, "NX_UINT64", "uint64", (1,)],
            "float": [-12.345, "NX_FLOAT", "float64", (1,), 1.e-14],
            "number": [-12.345e+2, "NX_NUMBER", "float64", (1,), 1.e-14],
            "float32": [-12.345e-1, "NX_FLOAT32", "float32", (1,), 1.e-5],
            "float64": [-12.345, "NX_FLOAT64", "float64", (1,), 1.e-14],
        }

        commands = [
            ('nxscollect append --test  %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r -s %s' %
             (filename, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]

            attrs[k][0] = np.array(
                [[[attrs[k][0] * self.__rnd.randint(0, 3)
                   for c in range(mlen[1])]
                  for i in range(mlen[0])]
                 for _ in range(6)],
                dtype=attrs[k][2]
                )
            try:
                for i in range(6):
                    fl = filewriter.create_file("h5test1_%05d.h5" % i,
                                                overwrite=True)
                    rt = fl.root()
                    shp = attrs[k][0][i].shape
                    data = rt.create_field("data", attrs[k][2], shp, shp)
                    data.write(attrs[k][0][i])
                    data.close()
                    fl.close()
                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    ins = entry.create_group("instrument", "NXinstrument")
                    det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    col = det.create_group("collection", "NXcollection")
                    postrun = col.create_field("postrun", "string")
                    postrun.write("h5test1_%05d.h5:0:5")
                    nxsfile.close()

                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = cmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    self.assertEqual(len(svl), 2)
                    self.assertTrue(
                        svl[0],
                        "populate: /entry12345:NXentry/"
                        "instrument:NXinstrument/pilatus300k:NXdetector"
                        "/data with ['test1_%05d.cbf:0:5']")

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    det = ins.open("pilatus300k")
                    self.assertTrue('data' not in det.names())
                    nxsfile.close()
                    os.remove(filename)

            finally:
                pass
                for i in range(6):
                    os.remove("h5test1_%05d.h5" % i)

    def test_test_file_parameters_tif(self):
        """ test nxsconfig append file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        ifiles = 'test1_%05d.tif:0:5'
        path = '/entry12345/instrument/pilatus300k/data'
        commands = [
            ('nxscollect append --test  %s %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -r %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -r %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -s %s --input-files %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -r -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -r -s %s --input-files %s --path %s'
             % (filename, self.flags, ifiles, path)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file0.tif', './test1_00000.tif')
            shutil.copy2('test/files/test_file1.tif', './test1_00001.tif')
            shutil.copy2('test/files/test_file2.tif', './test1_00002.tif')
            shutil.copy2('test/files/test_file3.tif', './test1_00003.tif')
            shutil.copy2('test/files/test_file4.tif', './test1_00004.tif')
            shutil.copy2('test/files/test_file5.tif', './test1_00005.tif')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                # er =
                mystderr.getvalue()

                # self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 2:
                    print(svl)
                self.assertEqual(len(svl), 2)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.tif:0:5']")

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.tif')
            os.remove('./test1_00001.tif')
            os.remove('./test1_00002.tif')
            os.remove('./test1_00003.tif')
            os.remove('./test1_00004.tif')
            os.remove('./test1_00005.tif')

    def test_test_file_parameters_tif_list(self):
        """ test nxsconfig test file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        ifiles = 'test1_00000.tif,test1_00001.tif,test1_00002.tif,' \
            'test1_00003.tif,test1_00004.tif,test1_00005.tif'
        path = '/entry12345/instrument/pilatus300k/data'
        commands = [
            ('nxscollect append --test  %s %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -r %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -r %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -s %s --input-files %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -r -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -r -s %s --input-files %s --path %s'
             % (filename, self.flags, ifiles, path)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file0.tif', './test1_00000.tif')
            shutil.copy2('test/files/test_file1.tif', './test1_00001.tif')
            shutil.copy2('test/files/test_file2.tif', './test1_00002.tif')
            shutil.copy2('test/files/test_file3.tif', './test1_00003.tif')
            shutil.copy2('test/files/test_file4.tif', './test1_00004.tif')
            shutil.copy2('test/files/test_file5.tif', './test1_00005.tif')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                # er =
                mystderr.getvalue()

                # self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 2:
                    print(svl)
                self.assertEqual(len(svl), 2)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.tif:0:5']")

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.tif')
            os.remove('./test1_00001.tif')
            os.remove('./test1_00002.tif')
            os.remove('./test1_00003.tif')
            os.remove('./test1_00004.tif')
            os.remove('./test1_00005.tif')

    def test_test_file_parameters_tif_list_sep(self):
        """ test nxsconfig test file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        ifiles = 'test1_00000.tif:test1_00001.tif:test1_00002.tif:' \
            'test1_00003.tif:test1_00004.tif:test1_00005.tif'
        path = '/entry12345/instrument/pilatus300k/data'
        commands = [
            ('nxscollect append --test  %s %s -i %s -p %s --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s %s -i %s --path %s --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -r %s -i %s -p %s --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -r %s -i %s --path %s --separator :'
             % (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -s %s --input-files %s -p %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -s %s --input-files %s --path %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -r -s %s --input-files %s -p %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -r -s %s --input-files %s --path %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file0.tif', './test1_00000.tif')
            shutil.copy2('test/files/test_file1.tif', './test1_00001.tif')
            shutil.copy2('test/files/test_file2.tif', './test1_00002.tif')
            shutil.copy2('test/files/test_file3.tif', './test1_00003.tif')
            shutil.copy2('test/files/test_file4.tif', './test1_00004.tif')
            shutil.copy2('test/files/test_file5.tif', './test1_00005.tif')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("test1_%05d.tif:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                # er =
                mystderr.getvalue()

                # self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 2:
                    print(svl)
                self.assertEqual(len(svl), 2)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.tif:0:5']")
                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.tif')
            os.remove('./test1_00001.tif')
            os.remove('./test1_00002.tif')
            os.remove('./test1_00003.tif')
            os.remove('./test1_00004.tif')
            os.remove('./test1_00005.tif')

    def test_test_file_parameters_cbf(self):
        """ test nxsconfig test file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        ifiles = 'test1_%05d.cbf:0:5'
        path = '/entry12345/instrument/pilatus300k/data'
        commands = [
            ('nxscollect append --test  %s %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -r %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -r %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -s %s --input-files %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -r -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -r -s %s --input-files %s --path %s'
             % (filename, self.flags, ifiles, path)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file.cbf', './test1_00000.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00001.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00002.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00003.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00004.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00005.cbf')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                # er =
                mystderr.getvalue()

                # self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 2:
                    print(svl)
                self.assertEqual(len(svl), 2)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.cbf:0:5']")

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.cbf')
            os.remove('./test1_00001.cbf')
            os.remove('./test1_00002.cbf')
            os.remove('./test1_00003.cbf')
            os.remove('./test1_00004.cbf')
            os.remove('./test1_00005.cbf')

    def test_test_file_parameters_cbf_list(self):
        """ test nxsconfig test file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        ifiles = 'test1_00000.cbf,test1_00001.cbf,test1_00002.cbf,' \
            'test1_00003.cbf,test1_00004.cbf,test1_00005.cbf'
        path = '/entry12345/instrument/pilatus300k/data'
        commands = [
            ('nxscollect append --test  %s %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -r %s -i %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -r %s -i %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -s %s --input-files %s --path %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -r -s %s --input-files %s -p %s' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -r -s %s --input-files %s --path %s'
             % (filename, self.flags, ifiles, path)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file.cbf', './test1_00000.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00001.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00002.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00003.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00004.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00005.cbf')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                # er =
                mystderr.getvalue()

                # self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 2:
                    print(svl)
                self.assertEqual(len(svl), 2)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.cbf:0:5']")

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.cbf')
            os.remove('./test1_00001.cbf')
            os.remove('./test1_00002.cbf')
            os.remove('./test1_00003.cbf')
            os.remove('./test1_00004.cbf')
            os.remove('./test1_00005.cbf')

    def test_test_file_parameters_cbf_list_sep(self):
        """ test nxsconfig test file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        ifiles = 'test1_00000.cbf:test1_00001.cbf:test1_00002.cbf:' \
            'test1_00003.cbf:test1_00004.cbf:test1_00005.cbf'
        path = '/entry12345/instrument/pilatus300k/data'
        commands = [
            ('nxscollect append --test  %s %s -i %s -p %s --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s %s -i %s --path %s --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -r %s -i %s -p %s --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -r %s -i %s --path %s --separator :'
             % (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -s %s --input-files %s -p %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -s %s --input-files %s --path %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test  %s -r -s %s --input-files %s -p %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
            ('nxscollect append --test %s -r -s %s --input-files %s --path %s'
             ' --separator :' %
             (filename, self.flags, ifiles, path)).split(),
        ]

        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule

        try:
            shutil.copy2('test/files/test_file.cbf', './test1_00000.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00001.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00002.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00003.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00004.cbf')
            shutil.copy2('test/files/test_file.cbf', './test1_00005.cbf')
            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("test1_%05d.cbf:0:5")
                nxsfile.close()

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                # er =
                mystderr.getvalue()

                # self.assertEqual('', er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 2:
                    print(svl)
                self.assertEqual(len(svl), 2)
                self.assertTrue(
                    svl[0],
                    "populate: /entry12345:NXentry/instrument:NXinstrument/"
                    "pilatus300k:NXdetector/data with ['test1_%05d.cbf:0:5']")

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                self.assertTrue('data' not in det.names())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove('./test1_00000.cbf')
            os.remove('./test1_00001.cbf')
            os.remove('./test1_00002.cbf')
            os.remove('./test1_00003.cbf')
            os.remove('./test1_00004.cbf')
            os.remove('./test1_00005.cbf')

    def test_test_file_parameters_raw(self):
        """ test nxsconfig test file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
            "int8": [12, "NX_INT8", "int8", (1,)],
            "int16": [-123, "NX_INT16", "int16", (1,)],
            "int32": [12345, "NX_INT32", "int32", (1,)],
            "int64": [-12345, "NX_INT64", "int64", (1,)],
            "uint": [123, "NX_UINT", "uint64", (1,)],
            "uint8": [12, "NX_UINT8", "uint8", (1,)],
            "uint16": [123, "NX_UINT16", "uint16", (1,)],
            "uint32": [12345, "NX_UINT32", "uint32", (1,)],
            "uint64": [12345, "NX_UINT64", "uint64", (1,)],
            "float": [-12.345, "NX_FLOAT", "float64", (1,), 1.e-14],
            "number": [-12.345e+2, "NX_NUMBER", "float64", (1,), 1.e-14],
            "float32": [-12.345e-1, "NX_FLOAT32", "float32", (1,), 1.e-5],
            "float64": [-12.345, "NX_FLOAT64", "float64", (1,), 1.e-14],
        }

        commands = [
            ('nxscollect append --test  %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test   %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r -s %s' %
             (filename, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]

            attrs[k][0] = np.array(
                [[[attrs[k][0] * self.__rnd.randint(0, 3)
                   for c in range(mlen[1])]
                  for i in range(mlen[0])]
                 for _ in range(6)],
                dtype=attrs[k][2]
                )
            try:
                for i in range(6):
                    with open("rawtest1_%05d.dat" % i, "w") as fl:
                        attrs[k][0][i].tofile(fl)
                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    # to be created
                    # ins = entry.create_group("instrument", "NXinstrument")
                    # det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    nxsfile.close()
                    pcmd = cmd
                    pcmd.extend(["-i", "rawtest1_%05d.dat:0:5"])
                    pcmd.extend(
                        ["-p", '/entry12345/instrument/pilatus300k/data'])
                    pcmd.extend(
                        ["--shape", json.dumps(attrs[k][0].shape[1:])])
                    pcmd.extend(
                        ["--dtype", attrs[k][2]])

                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = pcmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    # print(svl)
                    self.assertEqual(len(svl), 2)

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    self.assertTrue('instrument' not in entry.names())
                    # ins = entry.open("instrument")
                    # det = ins.open("pilatus300k")
                    # dt = det.open("data")
                    nxsfile.close()
                    os.remove(filename)

            finally:
                for i in range(6):
                    os.remove("rawtest1_%05d.dat" % i)

    def test_test_file_parameters_nxs(self):
        """ test nxsconfig test file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
            "int8": [12, "NX_INT8", "int8", (1,)],
            "int16": [-123, "NX_INT16", "int16", (1,)],
            "int32": [12345, "NX_INT32", "int32", (1,)],
            "int64": [-12345, "NX_INT64", "int64", (1,)],
            "uint": [123, "NX_UINT", "uint64", (1,)],
            "uint8": [12, "NX_UINT8", "uint8", (1,)],
            "uint16": [123, "NX_UINT16", "uint16", (1,)],
            "uint32": [12345, "NX_UINT32", "uint32", (1,)],
            "uint64": [12345, "NX_UINT64", "uint64", (1,)],
            "float": [-12.345, "NX_FLOAT", "float64", (1,), 1.e-14],
            "number": [-12.345e+2, "NX_NUMBER", "float64", (1,), 1.e-14],
            "float32": [-12.345e-1, "NX_FLOAT32", "float32", (1,), 1.e-5],
            "float64": [-12.345, "NX_FLOAT64", "float64", (1,), 1.e-14],
        }

        commands = [
            ('nxscollect append --test  %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r -s %s' %
             (filename, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]

            attrs[k][0] = np.array(
                [[[attrs[k][0] * self.__rnd.randint(0, 3)
                   for c in range(mlen[1])]
                  for i in range(mlen[0])]
                 for _ in range(6)],
                dtype=attrs[k][2]
                )
            try:
                for i in range(6):
                    fl = filewriter.create_file("h5test1_%05d.nxs" % i,
                                                overwrite=True)
                    rt = fl.root()

                    at = rt.attributes.create("default", "string")
                    at.write("entry12345")
                    at.close()

                    entry = rt.create_group("entry12345", "NXentry")
                    at = entry.attributes.create("default", "string")
                    at.write("data")
                    at.close()

                    dt = entry.create_group("data", "NXdata")
                    at = dt.attributes.create("signal", "string")
                    at.write("data")
                    at.close()

                    shp = attrs[k][0][i].shape
                    data = dt.create_field("data", attrs[k][2], shp, shp)
                    data.write(attrs[k][0][i])
                    data.close()

                    dt.close()
                    entry.close()
                    fl.close()

                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    ins = entry.create_group("instrument", "NXinstrument")
                    # det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    # col = det.create_group("collection", "NXcollection")
                    # postrun = col.create_field("postrun", "string")
                    # postrun.write("h5test1_%05d.h5:0:5")
                    nxsfile.close()

                    pcmd = cmd
                    pcmd.extend(["-i", "h5test1_%05d.nxs:0:5"])
                    pcmd.extend(
                        ["-p", '/entry12345/instrument/pilatus300k/data'])

                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = pcmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    if len(svl) != 2:
                        print(svl)
                    self.assertEqual(len(svl), 2)
                    self.assertTrue(
                        svl[0],
                        "populate: /entry12345:NXentry/"
                        "instrument:NXinstrument/pilatus300k:NXdetector"
                        "/data with ['test1_%05d.cbf:0:5']")

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    self.assertTrue('pilatus300k' not in ins.names())
                    # det = ins.open("pilatus300k")
                    # dt = det.open("data")
                    nxsfile.close()
                    os.remove(filename)

            finally:
                pass
                for i in range(6):
                    os.remove("h5test1_%05d.nxs" % i)

    def test_test_file_parameters_nxs_path(self):
        """ test nxsconfig test file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
            "int8": [12, "NX_INT8", "int8", (1,)],
            "int16": [-123, "NX_INT16", "int16", (1,)],
            "int32": [12345, "NX_INT32", "int32", (1,)],
            "int64": [-12345, "NX_INT64", "int64", (1,)],
            "uint": [123, "NX_UINT", "uint64", (1,)],
            "uint8": [12, "NX_UINT8", "uint8", (1,)],
            "uint16": [123, "NX_UINT16", "uint16", (1,)],
            "uint32": [12345, "NX_UINT32", "uint32", (1,)],
            "uint64": [12345, "NX_UINT64", "uint64", (1,)],
            "float": [-12.345, "NX_FLOAT", "float64", (1,), 1.e-14],
            "number": [-12.345e+2, "NX_NUMBER", "float64", (1,), 1.e-14],
            "float32": [-12.345e-1, "NX_FLOAT32", "float32", (1,), 1.e-5],
            "float64": [-12.345, "NX_FLOAT64", "float64", (1,), 1.e-14],
        }

        commands = [
            ('nxscollect append --test  %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect append --test %s -r -s %s' %
             (filename, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]

            attrs[k][0] = np.array(
                [[[attrs[k][0] * self.__rnd.randint(0, 3)
                   for c in range(mlen[1])]
                  for i in range(mlen[0])]
                 for _ in range(6)],
                dtype=attrs[k][2]
                )
            try:
                for i in range(6):
                    fl = filewriter.create_file("h5test1_%05d.nxs" % i,
                                                overwrite=True)
                    rt = fl.root()
                    entry = rt.create_group("entry345", "NXentry")

                    dt = entry.create_group("data", "NXdata")

                    shp = attrs[k][0][i].shape
                    data = dt.create_field("data", attrs[k][2], shp, shp)
                    data.write(attrs[k][0][i])
                    data.close()

                    dt.close()
                    entry.close()
                    fl.close()

                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    ins = entry.create_group("instrument", "NXinstrument")
                    # det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    # col = det.create_group("collection", "NXcollection")
                    # postrun = col.create_field("postrun", "string")
                    # postrun.write("h5test1_%05d.h5:0:5")
                    nxsfile.close()

                    pcmd = cmd
                    pcmd.extend(
                        ["-i", "h5test1_%05d.nxs://entry345/data/data:0:5"])
                    pcmd.extend(
                        ["-p", '/entry12345/instrument/pilatus300k/data'])

                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = pcmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    if len(svl) != 2:
                        print(svl)
                    self.assertEqual(len(svl), 2)
                    self.assertTrue(
                        svl[0],
                        "populate: /entry12345:NXentry/"
                        "instrument:NXinstrument/pilatus300k:NXdetector"
                        "/data with ['test1_%05d.nxs:0:5']")

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    self.assertTrue('pilatus300k' not in ins.names())
                    # det = ins.open("pilatus300k")
                    # dt = det.open("data")
                    nxsfile.close()
                    os.remove(filename)

            finally:
                pass
                for i in range(6):
                    os.remove("h5test1_%05d.nxs" % i)

    def test_link_external_nxs(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
        }

        commands = [
            ('nxscollect link %s' % (self.flags)).split(),
            ('nxscollect link -r %s' % (self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]

            attrs[k][0] = np.array(
                [[attrs[k][0] * self.__rnd.randint(0, 3)
                  for c in range(mlen[1])]
                 for i in range(mlen[0])],
                dtype=attrs[k][2]
                )
            try:
                fl = filewriter.create_file("h5test1_00001.nxs",
                                            overwrite=True)
                rt = fl.root()

                entry = rt.create_group("entry345", "NXentry")
                dt = entry.create_group("data", "NXdata")
                shp = attrs[k][0].shape
                data = dt.create_field("data", attrs[k][2], shp, shp)
                data.write(attrs[k][0])
                data.close()

                dt.close()
                entry.close()
                fl.close()

                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    ins = entry.create_group("instrument", "NXinstrument")
                    # det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    # col = det.create_group("collection", "NXcollection")
                    # postrun = col.create_field("postrun", "string")
                    # postrun.write("h5test1_%05d.h5:0:5")
                    nxsfile.close()

                    pcmd = cmd
                    pcmd.extend(
                        ['%s://entry12345/instrument/pilatus300k:NXdetector'
                         % filename])
                    pcmd.extend(["--target",
                                 "h5test1_00001.nxs://entry345/data/data"])
                    pcmd.extend(["--name", "data"])

                    # print(pcmd)
                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = pcmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    if len(svl) != 2:
                        print(svl)
                    self.assertEqual(len(svl), 2)
                    self.assertTrue(
                        svl[0],
                        "populate: /entry12345:NXentry/"
                        "instrument:NXinstrument/pilatus300k:NXdetector"
                        "/data with ['test1_%05d.cbf:0:5']")
                    # print(svl)
                    self.assertTrue(svl[0].startswith('link: '))
                    self.assertTrue('h5test1_00001.nxs://' in svl[0])

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    det = ins.open("pilatus300k")
                    dt = det.open("data")
                    buffer = dt.read()
                    self.assertEqual(buffer.shape, attrs[k][0].shape)
                    fimage = attrs[k][0]
                    image = buffer[:, :]
                    self.assertTrue((image == fimage).all())
                    nxsfile.close()
                    os.remove(filename)

            finally:
                os.remove("h5test1_00001.nxs")

    def test_link_external_nxs_noname(self):
        """ test nxsconfig append file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
        }

        commands = [
            ('nxscollect link %s' % (self.flags)).split(),
            ('nxscollect link -r %s' % (self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]

            attrs[k][0] = np.array(
                [[attrs[k][0] * self.__rnd.randint(0, 3)
                  for c in range(mlen[1])]
                 for i in range(mlen[0])],
                dtype=attrs[k][2]
                )
            try:
                fl = filewriter.create_file("h5test1_00001.nxs",
                                            overwrite=True)
                rt = fl.root()

                entry = rt.create_group("entry345", "NXentry")
                dt = entry.create_group("data", "NXdata")
                shp = attrs[k][0].shape
                data = dt.create_field("data", attrs[k][2], shp, shp)
                data.write(attrs[k][0])
                data.close()

                dt.close()
                entry.close()
                fl.close()

                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    ins = entry.create_group("instrument", "NXinstrument")
                    # det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    # col = det.create_group("collection", "NXcollection")
                    # postrun = col.create_field("postrun", "string")
                    # postrun.write("h5test1_%05d.h5:0:5")
                    nxsfile.close()

                    pcmd = cmd
                    pcmd.extend(
                        ['%s://entry12345/instrument/pilatus300k:NXdetector'
                         % filename])
                    pcmd.extend(["--target",
                                 "h5test1_00001.nxs://entry345/data/data"])

                    # print(pcmd)
                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = pcmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    if len(svl) != 2:
                        print(svl)
                    self.assertEqual(len(svl), 2)
                    self.assertTrue(
                        svl[0],
                        "populate: /entry12345:NXentry/"
                        "instrument:NXinstrument/pilatus300k:NXdetector"
                        "/data with ['test1_%05d.cbf:0:5']")
                    print(svl)
                    self.assertTrue(svl[0].startswith('link: '))
                    self.assertTrue('h5test1_00001.nxs://' in svl[0])

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    det = ins.open("pilatus300k")
                    dt = det.open("data")
                    buffer = dt.read()
                    self.assertEqual(buffer.shape, attrs[k][0].shape)
                    fimage = attrs[k][0]
                    image = buffer[:, :]
                    self.assertTrue((image == fimage).all())
                    nxsfile.close()
                    os.remove(filename)

            finally:
                os.remove("h5test1_00001.nxs")

    def test_vds_single(self):
        """ test nxscollect vds
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        if self.writer == "h5py":
            import nxstools.h5pywriter as H5PYWriter
            if not H5PYWriter.is_vds_supported():
                print("VDS not supported: skipping the test")
                return

        filename = 'testcollect.nxs'
        filename = '%s/%s%s.nxs' % (os.getcwd(),
                                    self.__class__.__name__, fun)
        attrs = {
            "int": [-123, "NX_INT", "int64", (1,)],
        }

        commands = [
            ('nxscollect vds %s' % (self.flags)).split(),
            ('nxscollect vds -r %s' % (self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        for k in attrs.keys():
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]
            print(mlen)
            attrs[k][0] = np.array(
                [[attrs[k][0] * self.__rnd.randint(0, 3)
                  for c in range(mlen[1])]
                 for i in range(mlen[0])],
                dtype=attrs[k][2]
                )
            try:
                fl = filewriter.create_file("h5test1_00001.nxs",
                                            overwrite=True)
                rt = fl.root()

                entry = rt.create_group("entry345", "NXentry")
                dt = entry.create_group("data", "NXdata")
                shp = attrs[k][0].shape
                data = dt.create_field("data", attrs[k][2], shp, shp)
                data.write(attrs[k][0])
                data.close()

                dt.close()
                entry.close()
                fl.close()

                for cmd in commands:
                    nxsfile = filewriter.create_file(
                        filename, overwrite=True)
                    rt = nxsfile.root()
                    entry = rt.create_group("entry12345", "NXentry")
                    ins = entry.create_group("instrument", "NXinstrument")
                    # det = ins.create_group("pilatus300k", "NXdetector")
                    entry.create_group("data", "NXdata")
                    # col = det.create_group("collection", "NXcollection")
                    # postrun = col.create_field("postrun", "string")
                    # postrun.write("h5test1_%05d.h5:0:5")
                    nxsfile.close()

                    pcmd = cmd
                    pcmd.extend(
                        ['%s://entry12345/instrument/pilatus300k:NXdetector/'
                         'data' % filename])
                    pcmd.extend(["--target-fields",
                                 "h5test1_00001.nxs://entry345/data/data"])
                    pcmd.extend(["--shape",
                                 "%s" % ','.join([str(s) for s in shp])])
                    pcmd.extend(["--shapes",
                                 "%s" % ','.join([str(s) for s in shp])])
                    pcmd.extend(["--dtype",
                                 "%s" % attrs[k][2]])

                    # print(pcmd)
                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = mystdout = StringIO()
                    sys.stderr = mystderr = StringIO()
                    old_argv = sys.argv
                    sys.argv = pcmd
                    nxscollect.main()

                    sys.argv = old_argv
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    vl = mystdout.getvalue()
                    er = mystderr.getvalue()

                    self.assertTrue(vl)
                    svl = vl.split("\n")
                    if len(svl) != 2:
                        print(svl)
                    print(svl)
                    self.assertEqual(len(svl), 2)
                    self.assertEqual('', er)
                    self.assertTrue(svl[0].startswith('vds: '))
                    self.assertTrue('h5test1_00001.nxs' in svl[0])

                    if '-r' not in cmd:
                        os.remove("%s.__nxscollect_old__" % filename)
                    nxsfile = filewriter.open_file(filename, readonly=True)
                    rt = nxsfile.root()
                    entry = rt.open("entry12345")
                    ins = entry.open("instrument")
                    det = ins.open("pilatus300k")
                    dt = det.open("data")
                    buffer = dt.read()
                    self.assertEqual(buffer.shape, attrs[k][0].shape)
                    fimage = attrs[k][0]
                    image = buffer[:, :]
                    self.assertTrue((image == fimage).all())
                    nxsfile.close()
                    os.remove(filename)

            finally:
                os.remove("h5test1_00001.nxs")

    def test_vds_concatinate(self):
        """ test nxscollect vds
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        if self.writer == "h5py":
            import nxstools.h5pywriter as H5PYWriter
            if not H5PYWriter.is_vds_supported():
                print("VDS not supported: skipping the test")
                return

        filename = 'testcollect.nxs'
        filename = '%s/%s%s.nxs' % (os.getcwd(),
                                    self.__class__.__name__, fun)
        attrs = {
            "int1": [-123, "NX_INT", "int64", (1,)],
            "int2": [12, "NX_INT", "int64", (1,)],
            "int3": [52, "NX_INT", "int64", (1,)],
        }

        commands = [
            ('nxscollect vds %s' % (self.flags)).split(),
            ('nxscollect vds -r %s' % (self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        try:
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]
            # print(mlen)
            for ii, k in enumerate(sorted(attrs.keys())):
                attrs[k][0] = np.array(
                    [[attrs[k][0] * self.__rnd.randint(0, 3)
                      for c in range(mlen[1])]
                     for i in range(mlen[0])],
                    dtype=attrs[k][2]
                )
                fl = filewriter.create_file("eh5test1_%05d.nxs" % (ii + 1),
                                            overwrite=True)
                rt = fl.root()

                entry = rt.create_group("entry345", "NXentry")
                dt = entry.create_group("data", "NXdata")
                shp = attrs[k][0].shape
                data = dt.create_field("data", attrs[k][2], shp, shp)
                data.write(attrs[k][0])
                data.close()

                dt.close()
                entry.close()
                fl.close()

            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                # det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("h5test1_%05d.h5:0:5")
                nxsfile.close()

                pcmd = cmd
                pcmd.extend(
                    ['%s://entry12345/instrument/pilatus300k:NXdetector/'
                     'data' % filename])
                tfields = ",".join(
                    ["eh5test1_%05d.nxs://entry345/data/data" %
                     (i + 1) for i in range(len(attrs))])
                pcmd.extend(["--target-fields", "%s" % tfields])
                pcmd.extend(["--shape",
                             "%s,%s" % (shp[0] * len(attrs), shp[1])])
                pcmd.extend(["--dtype",
                             "%s" % attrs["int1"][2]])
                tshapes = ";".join(
                    [("%s,%s" % (shp[0], shp[1])) for _ in range(len(attrs))])
                pcmd.extend(["--shapes", "%s" % tshapes])
                offsets = ";".join(
                    [('%s,%s' % (shp[0] * i, 0)) for i in range(len(attrs))])

                pcmd.extend(["--offsets", "%s" % offsets])
                # print(pcmd)
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = pcmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 2:
                    print(svl)
                print(svl)
                self.assertEqual(len(svl), 4)
                self.assertEqual('', er)
                self.assertTrue(svl[0].startswith('vds: '))
                self.assertTrue('h5test1_0000' in svl[0])

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                ibuffer = dt.read()
                # print(attrs["int1"][0].shape)
                # print(ibuffer.shape)
                tshape = (attrs["int1"][0].shape[0] * len(attrs),
                          attrs["int1"][0].shape[1])

                self.assertEqual(ibuffer.shape, tshape)
                fimage = np.concatenate(
                    (attrs["int1"][0], attrs["int2"][0], attrs["int3"][0]))
                image = ibuffer[:, :]
                self.assertTrue((image == fimage).all())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove("eh5test1_00001.nxs")
            os.remove("eh5test1_00002.nxs")
            os.remove("eh5test1_00003.nxs")

    def test_vds_append(self):
        """ test nxscollect vds
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        if self.writer == "h5py":
            import nxstools.h5pywriter as H5PYWriter
            if not H5PYWriter.is_vds_supported():
                print("VDS not supported: skipping the test")
                return

        # filename = 'testcollect.nxs'
        filename = '%s/%s%s.nxs' % (os.getcwd(),
                                    self.__class__.__name__, fun)
        attrs = {
            "int1": [-123, "NX_INT", "int64", (1,)],
            "int2": [12, "NX_INT", "int64", (1,)],
            "int3": [52, "NX_INT", "int64", (1,)],
        }

        commands = [
            ('nxscollect vds %s' % (self.flags)).split(),
            ('nxscollect vds -r %s' % (self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        try:
            mlen = [self.__rnd.randint(10, 200),
                    self.__rnd.randint(10, 200)]
            # print(mlen)
            for ii, k in enumerate(sorted(attrs.keys())):
                attrs[k][0] = np.array(
                    [[attrs[k][0] * self.__rnd.randint(0, 3)
                      for c in range(mlen[1])]
                     for i in range(mlen[0])],
                    dtype=attrs[k][2]
                )
                fl = filewriter.create_file("eh5test1_%05d.nxs" % (ii + 1),
                                            overwrite=True)
                rt = fl.root()

                entry = rt.create_group("entry345", "NXentry")
                dt = entry.create_group("data", "NXdata")
                shp = attrs[k][0].shape
                data = dt.create_field("data", attrs[k][2], shp, shp)
                data.write(attrs[k][0])
                data.close()

                dt.close()
                entry.close()
                fl.close()

            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                # det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("h5test1_%05d.h5:0:5")
                nxsfile.close()

                pcmd = cmd
                pcmd.extend(
                    ['%s://entry12345/instrument/pilatus300k:NXdetector/'
                     'data' % filename])
                tfields = ",".join(
                    ["eh5test1_%05d.nxs://entry345/data/data" %
                     (i + 1) for i in range(len(attrs))])
                pcmd.extend(["--target-fields", "%s" % tfields])
                pcmd.extend(["--shape",
                             "%s,%s,%s" % (len(attrs), shp[0], shp[1])])
                pcmd.extend(["--dtype",
                             "%s" % attrs["int1"][2]])
                tshapes = ";".join(
                    [("1,%s,%s" % (shp[0], shp[1]))
                     for _ in range(len(attrs))])
                pcmd.extend(["--shapes", "%s" % tshapes])
                offsets = ";".join(
                    [('%s,0,0' % i) for i in range(len(attrs))])

                pcmd.extend(["--offsets", "%s" % offsets])
                # print(pcmd)
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = pcmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                # print(er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 2:
                    print(svl)
                print(svl)
                self.assertEqual(len(svl), 4)
                self.assertEqual('', er)
                self.assertTrue(svl[0].startswith('vds: '))
                self.assertTrue('h5test1_0000' in svl[0])

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                ibuffer = dt.read()
                tshape = (len(attrs),
                          attrs["int1"][0].shape[0],
                          attrs["int1"][0].shape[1])

                self.assertEqual(ibuffer.shape, tshape)
                image = ibuffer[:, :, :]
                self.assertTrue((image[0, :, :] == attrs["int1"][0]).all())
                self.assertTrue((image[1, :, :] == attrs["int2"][0]).all())
                self.assertTrue((image[2, :, :] == attrs["int3"][0]).all())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove("eh5test1_00001.nxs")
            os.remove("eh5test1_00002.nxs")
            os.remove("eh5test1_00003.nxs")

    def test_vds_append_gap(self):
        """ test nxscollect vds
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        if self.writer == "h5py":
            import nxstools.h5pywriter as H5PYWriter
            if not H5PYWriter.is_vds_supported():
                print("VDS not supported: skipping the test")
                return

        # filename = 'testcollect.nxs'
        filename = '%s/%s%s.nxs' % (os.getcwd(),
                                    self.__class__.__name__, fun)
        attrs = {
            "int1": [-123, "NX_INT", "int64", (1,)],
            "int2": [12, "NX_INT", "int64", (1,)],
            "int3": [52, "NX_INT", "int64", (1,)],
        }

        fval = 1
        commands = [
            ('nxscollect vds -f %s %s' % (fval, self.flags)).split(),
            ('nxscollect vds -r -f %s %s' % (fval, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        try:
            mlen = [self.__rnd.randint(3, 10),
                    self.__rnd.randint(3, 10),
                    self.__rnd.randint(3, 10)]
            gap = 3
            imnr = len(list(attrs.keys()))
            lsh = list(mlen)
            lsh[1] = imnr * lsh[1] + (imnr - 1) * gap
            lsh = tuple(lsh)

            garr = np.array(
                [[[fval
                   for j in range(mlen[2])]
                  for c in range(gap)]
                 for i in range(mlen[0])],
                dtype=attrs['int1'][2]
            )

            # print(mlen)
            for ii, k in enumerate(sorted(attrs.keys())):
                attrs[k][0] = np.array(
                    [[[attrs[k][0] * self.__rnd.randint(0, 3)
                       for j in range(mlen[2])]
                      for c in range(mlen[1])]
                     for i in range(mlen[0])],
                    dtype=attrs[k][2]
                )
                fl = filewriter.create_file(
                    "eh5test1_%05d.nxs" % (ii + 1),
                    overwrite=True)
                rt = fl.root()

                entry = rt.create_group("entry345", "NXentry")
                dt = entry.create_group("data", "NXdata")
                shp = attrs[k][0].shape
                chk = list(shp)
                chk[0] = 1
                chk = tuple(chk)
                data = dt.create_field("data", attrs[k][2], shp, chk)
                data.write(attrs[k][0])
                data.close()

                dt.close()
                entry.close()
                fl.close()

            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                # det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("h5test1_%05d.h5:0:5")
                nxsfile.close()

                pcmd = cmd
                pcmd.extend(
                    ['%s://entry12345/instrument/pilatus300k:NXdetector/'
                     'data' % filename])
                tfields = ",".join(
                    ["eh5test1_%05d.nxs://entry345/data/data" %
                     (i + 1) for i in range(len(attrs))])
                pcmd.extend(["--target-fields", "%s" % tfields])
                pcmd.extend(["--shape",
                             "%s,%s,%s" % (lsh[0], lsh[1], lsh[2])])
                pcmd.extend(["--dtype",
                             "%s" % attrs["int1"][2]])
                tshapes = ";".join(
                    [("%s,%s,%s" % (shp[0], shp[1], shp[2]))
                     for _ in range(len(attrs))])
                pcmd.extend(["--shapes", "%s" % tshapes])
                offsets = ";".join(
                    [('0,%s,0' % (i*(mlen[1] + gap)))
                     for i in range(len(attrs))])

                pcmd.extend(["--offsets", "%s" % offsets])
                # print(pcmd)
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = pcmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                # print(er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 2:
                    print(svl)
                print(svl)
                self.assertEqual(len(svl), 4)
                self.assertEqual('', er)
                self.assertTrue(svl[0].startswith('vds: '))
                self.assertTrue('h5test1_0000' in svl[0])

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                ibuffer = dt.read()

                self.assertEqual(ibuffer.shape, lsh)
                image = ibuffer[:, :, :]
                fimage = np.concatenate(
                    (attrs["int1"][0], garr,
                     attrs["int2"][0], garr,
                     attrs["int3"][0]), 1)
                self.assertTrue((image == fimage).all())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove("eh5test1_00001.nxs")
            os.remove("eh5test1_00002.nxs")
            os.remove("eh5test1_00003.nxs")

    def test_vds_append_inter(self):
        """ test nxscollect vds
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        if self.writer == "h5py":
            import nxstools.h5pywriter as H5PYWriter
            if not H5PYWriter.is_vds_supported():
                print("VDS not supported: skipping the test")
                return

        # filename = 'testcollect.nxs'
        filename = '%s/%s%s.nxs' % (os.getcwd(),
                                    self.__class__.__name__, fun)
        attrs = {
            "int1": [-123, "NX_FLOAT", "float64", (1,)],
            "int2": [12, "NX_FLOAT", "float64", (1,)],
            "int3": [52, "NX_FLOAT", "float64", (1,)],
            "int4": [22, "NX_FLOAT", "float64", (1,)],
        }

        commands = [
            ('nxscollect vds  %s' % (self.flags)).split(),
            ('nxscollect vds -r %s' % (self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        try:
            mlen = [self.__rnd.randint(3, 10),
                    self.__rnd.randint(3, 10),
                    self.__rnd.randint(3, 10)]
            # mlen = [3,3,4]
            imnr = len(list(attrs.keys()))
            lsh = list(mlen)
            lsh[0] = imnr * lsh[0]
            lsh = tuple(lsh)

            # print(mlen)
            for ii, k in enumerate(sorted(attrs.keys())):
                attrs[k][0] = np.array(
                    [[[attrs[k][0] * self.__rnd.randint(0, 3)
                       for j in range(mlen[2])]
                      for c in range(mlen[1])]
                     for i in range(mlen[0])],
                    dtype=attrs[k][2]
                )
                fl = filewriter.create_file(
                    "eh5test1_%05d.nxs" % (ii + 1),
                    overwrite=True)
                rt = fl.root()

                entry = rt.create_group("entry345", "NXentry")
                dt = entry.create_group("data", "NXdata")
                shp = attrs[k][0].shape
                chk = list(shp)
                chk[0] = 1
                chk = tuple(chk)
                data = dt.create_field("data", attrs[k][2], shp, chk)
                data.write(attrs[k][0])
                data.close()

                dt.close()
                entry.close()
                fl.close()

            fimage = np.array(
                [[[0
                   for j in range(mlen[2])]
                  for c in range(mlen[1])]
                 for i in range(4 * mlen[0])],
                dtype=attrs["int1"][2]
                )
            fimage[0:lsh[0]:4, :, :] = attrs["int1"][0]
            fimage[1:lsh[0]:4, :, :] = attrs["int2"][0]
            fimage[2:lsh[0]:4, :, :] = attrs["int3"][0]
            fimage[3:lsh[0]:4, :, :] = attrs["int4"][0]

            for cmd in commands:
                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                # det = ins.create_group("pilatus300k", "NXdetector")
                entry.create_group("data", "NXdata")
                # col = det.create_group("collection", "NXcollection")
                # postrun = col.create_field("postrun", "string")
                # postrun.write("h5test1_%05d.h5:0:5")
                nxsfile.close()

                pcmd = cmd
                pcmd.extend(
                    ['%s://entry12345/instrument/pilatus300k:NXdetector/'
                     'data' % filename])
                tfields = "eh5test1_%05d.nxs://entry345/data/data:1:4"
                pcmd.extend(["--target-fields", "%s" % tfields])
                pcmd.extend(["--shape",
                             "%s,%s,%s" % (lsh[0], lsh[1], lsh[2])])
                pcmd.extend(["--dtype",
                             "%s" % attrs["int1"][2]])
                tshapes = ";".join(
                    [("%s,%s,%s" % (shp[0], shp[1], shp[2]))
                     for _ in range(len(attrs))])
                pcmd.extend(["--shapes", "%s" % tshapes])
                offsets = ";".join(
                    [('%s,,' % i) for i in range(imnr)])
                pcmd.extend(["--offsets", "%s" % offsets])
                strides = ";".join(
                    [('4,,') for _ in range(imnr)])
                pcmd.extend(["--strides", "%s" % strides])

                # print(pcmd)
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = pcmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                # print(er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 2:
                    print(svl)
                print(svl)
                self.assertEqual(len(svl), 5)
                self.assertEqual('', er)
                self.assertTrue(svl[0].startswith('vds: '))
                self.assertTrue('h5test1_0000' in svl[0])

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dt = det.open("data")
                ibuffer = dt.read()

                self.assertEqual(ibuffer.shape, lsh)
                self.assertTrue((ibuffer == fimage).all())
                nxsfile.close()
                os.remove(filename)

        finally:
            os.remove("eh5test1_00001.nxs")
            os.remove("eh5test1_00002.nxs")
            os.remove("eh5test1_00003.nxs")
            os.remove("eh5test1_00004.nxs")

    def test_vds_append_unlimited(self):
        """ test nxscollect vds
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        if self.writer == "h5py":
            import nxstools.h5pywriter as H5PYWriter
            if not H5PYWriter.is_unlimited_vds_supported():
                print("VDS not supported: skipping the test")
                return

        # filename = 'testcollect.nxs'
        filename = '%s/%s%s.nxs' % (os.getcwd(),
                                    self.__class__.__name__, fun)
        attrs = {
            "int1": [-123, "NX_INT", "int64", (1,), 3],
            "int2": [12, "NX_INT", "int64", (1,), -2],
        }

        fval = 1
        commands = [
            ('nxscollect vds -f %s %s' % (fval, self.flags)).split(),
            # second command hangs on reading vds
            ('nxscollect vds -r -f %s %s' % (fval, self.flags)).split(),
        ]
        wrmodule = WRITERS[self.writer]
        filewriter.writer = wrmodule
        mlen = [self.__rnd.randint(3, 10),
                self.__rnd.randint(3, 10),
                self.__rnd.randint(3, 10)]
        imnr = len(list(attrs.keys()))
        lsh = list(mlen)
        lsh[1] = imnr * lsh[1]
        lsh = tuple(lsh)
        for ck, cmd in enumerate(commands):
            filename = '%s/%s%s_%s.nxs' % (
                os.getcwd(),
                self.__class__.__name__, fun, ck)

            filenames = []
            try:
                for ii, k in enumerate(sorted(attrs.keys())):
                    attrs[k][0] = np.array(
                        [[[self.__rnd.randint(0, 3)
                           for j in range(mlen[2])]
                          for c in range(mlen[1])]
                         for i in range(mlen[0])],
                        dtype=attrs[k][2]
                    )
                    filenames.append(
                        "eh5test1_%05d_%s.nxs" % (ii + 1, ck))
                    fl = filewriter.create_file(filenames[-1],
                                                overwrite=True)
                    rt = fl.root()

                    entry = rt.create_group("entry345", "NXentry")
                    dt = entry.create_group("data", "NXdata")
                    shp = attrs[k][0].shape
                    chk = list(shp)
                    chk[0] = 1
                    chk = tuple(chk)
                    data = dt.create_field("data", attrs[k][2], shp, chk)
                    data.write(attrs[k][0])
                    data.close()
                    dt.close()
                    entry.close()
                    fl.close()

                nxsfile = filewriter.create_file(
                    filename, overwrite=True)
                rt = nxsfile.root()
                entry = rt.create_group("entry12345", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                dt = entry.create_group("data", "NXdata")
                dt.close()
                ins.close()
                entry.close()
                rt.close()
                nxsfile.close()

                pcmd = cmd
                pcmd.extend(
                    ['%s://entry12345/instrument/pilatus300k:NXdetector/'
                     'data' % filename])
                tfields = ",".join(
                    ["%s://entry345/data/data" %
                     (filenames[i]) for i in range(len(attrs))])
                pcmd.extend(["--target-fields", "%s" % tfields])
                pcmd.extend(["--shape",
                             "%s,%s,%s" % (lsh[0], lsh[1], lsh[2])])
                pcmd.extend(["--dtype",
                             "%s" % attrs["int1"][2]])
                tshapes = ":".join(
                    [(",%s," % (shp[1]))
                     for _ in range(len(attrs))])
                pcmd.extend(["--shapes", "%s" % tshapes])
                offsets = ":".join(
                    [('0,%s,0' % (i*(mlen[1])))
                     for i in range(len(attrs))])
                pcmd.extend(["--offsets", "%s" % offsets])
                counts = ":".join(
                    ['U,,' for i in range(len(attrs))])
                pcmd.extend(["--counts", "%s" % counts])

                # print(pcmd)
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = pcmd
                nxscollect.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                vl = mystdout.getvalue()
                er = mystderr.getvalue()

                # print(er)
                self.assertTrue(vl)
                svl = vl.split("\n")
                if len(svl) != 3:
                    print(svl)
                print(svl)
                self.assertEqual(len(svl), 3)
                self.assertEqual('', er)
                self.assertTrue(svl[0].startswith('vds: '))
                self.assertTrue('h5test1_0000' in svl[0])

                if '-r' not in cmd:
                    os.remove("%s.__nxscollect_old__" % filename)
                nxsfile = filewriter.open_file(
                    filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dat = det.open("data")

                self.assertEqual(dat.shape, lsh)
                fimage = np.concatenate(
                    (attrs["int1"][0],
                     attrs["int2"][0]), 1)

                # second times read hangs
                # ibuffer = dat.read()

                image = dat[:, :, :]
                self.assertTrue(np.array_equal(image, fimage))

                dat.close()
                ins.close()
                entry.close()
                rt.close()
                nxsfile.close()

                for ii, k in enumerate(sorted(attrs.keys())):
                    attrs[k][4] = np.array(
                        [[[self.__rnd.randint(0, 30)
                           for j in range(mlen[2])]
                          for c in range(mlen[1])]
                         for i in range(mlen[0])],
                        dtype=attrs[k][2]
                    )
                    fl = filewriter.open_file(
                        filenames[ii],
                        readonly=False)
                    rt = fl.root()

                    entry = rt.open("entry345")
                    dt = entry.open("data")
                    shp = attrs[k][4].shape
                    chk = list(shp)
                    chk[0] = 1
                    chk = tuple(chk)
                    data = dt.open("data")
                    data.grow(0, shp[0])
                    data[shp[0]:, :, :] = attrs[k][4]
                    data.close()

                    dt.close()
                    entry.close()
                    fl.close()

                nxsfile = filewriter.open_file(filename, readonly=True)
                rt = nxsfile.root()
                entry = rt.open("entry12345")
                ins = entry.open("instrument")
                det = ins.open("pilatus300k")
                dat = det.open("data")
                ibuffer = dat.read()

                self.assertEqual(ibuffer.shape,
                                 (2 * lsh[0], lsh[1], lsh[2]))
                image = ibuffer[:, :, :]
                fimage1 = np.concatenate(
                    (
                        attrs["int1"][0],
                        attrs["int2"][0],
                    ), 1)
                fimage2 = np.concatenate(
                    (
                        attrs["int1"][4],
                        attrs["int2"][4],
                    ), 1)
                fimage = np.concatenate((fimage1, fimage2), 0)
                self.assertTrue((image == fimage).all())
                dat.close()
                ins.close()
                entry.close()
                rt.close()

            finally:
                os.remove(filename)
                for fn in filenames:
                    os.remove(fn)


if __name__ == '__main__':
    unittest.main()
