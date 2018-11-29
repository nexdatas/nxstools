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
# import time
# import threading
# import PyTango
import json
from nxstools import nxscollect
from nxstools import filewriter

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO


if sys.version_info > (3,):
    unicode = str
    long = int

WRITERS = {}
try:
    from nxstools import pniwriter
    WRITERS["pni"] = pniwriter
except Exception:
    pass

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


class mytty(object):

    def __init__(self, underlying):
        #        underlying.encoding = 'cp437'
        self.__underlying = underlying

    def __getattr__(self, name):
        return getattr(self.__underlying, name)

    def isatty(self):
        return True


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

        self.helperror = "Error: too few arguments\n"

        self.helpinfo = """usage: nxscollect [-h] {execute,test} ...

  Command-line tool to merge images of external file-formats """ + \
            """into the master NeXus file

positional arguments:
  {execute,test}  sub-command help
    execute       execute the collection process
    test          execute the process in the test mode without changing any
                  files

optional arguments:
  -h, --help      show this help message and exit

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

        if "h5cpp" in WRITERS.keys():
            self.writer = "h5cpp"
        elif "h5py" in WRITERS.keys():
            self.writer = "h5py"
        else:
            self.writer = "pni"

        self.flags = ""

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
        except Exception:
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
        self.assertEqual(self.helpinfo, vl)
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
            self.assertEqual(self.helpinfo[0:-1], vl)
            self.assertEqual('', er)

    def test_execute_test_emptyfile(self):
        """ test nxsconfig execute empty file
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'

        commands = [
            ('nxscollect execute %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect test %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect execute %s -s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect -x %s -s -r %s' % (filename, self.flags)).split(),
            ('nxscollect test %s -s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s -r %s' % (filename, self.flags)).split(),
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

    def test_execute_test_nofile(self):
        """ test nxsconfig execute empty file
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect execute %s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s %s' % (filename, self.flags)).split(),
            ('nxscollect test %s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s %s' % (filename, self.flags)).split(),
            ('nxscollect execute -s %s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect test %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect execute %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect test %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect execute -s %s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect -x %s -s -r %s' % (filename, self.flags)).split(),
            ('nxscollect test %s -s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s -r %s' % (filename, self.flags)).split(),
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

    def test_execute_test_file_withdata(self):
        """ test nxsconfig execute file with data field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect execute %s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s %s' % (filename, self.flags)).split(),
            ('nxscollect test %s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s %s' % (filename, self.flags)).split(),
            ('nxscollect execute %s -s  %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s %s' % (filename, self.flags)).split(),
            ('nxscollect test %s -s  %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect execute %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect test %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect execute %s -s -r %s' %
             (filename, self.flags)).split(),
            ('nxscollect -x %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect test %s -s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s -r %s' % (filename, self.flags)).split(),
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

    def test_execute_test_file_withpostrun_nofile(self):
        """ test nxsconfig execute file with data field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect execute  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s %s' % (filename, self.flags)).split(),
            ('nxscollect test %s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s %s' % (filename, self.flags)).split(),
            ('nxscollect execute -r %s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -x -r %s %s' % (filename, self.flags)).split(),
            ('nxscollect test -r %s %s' % (filename, self.flags)).split(),
            ('nxscollect -t -r %s %s' % (filename, self.flags)).split(),
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

    def test_execute_file_withpostrun_tif(self):
        """ test nxsconfig execute file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect execute  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -x %s -r -s %s' % (filename, self.flags)).split(),
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

    def test_execute_file_withpostrun_tif_pilatus300k(self):
        """ test nxsconfig execute file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect execute  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -x %s -r -s %s' % (filename, self.flags)).split(),
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

    def test_execute_file_withpostrun_tif_pilatus300k_skip(self):
        """ test nxsconfig execute file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect execute  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -x %s -r -s %s' % (filename, self.flags)).split(),
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

    def test_execute_file_withpostrun_tif_pilatus300k_wait(self):
        """ test nxsconfig execute file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect execute  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -x %s -r -s %s' % (filename, self.flags)).split(),
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

    def test_execute_file_withpostrun_tif_pilatus300k_missing(self):
        """ test nxsconfig execute file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect execute  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -r %s' % (filename, self.flags)).split(),
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

    def test_execute_file_withpostrun_cbf(self):
        """ test nxsconfig execute file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect execute  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -x %s -r -s %s' % (filename, self.flags)).split(),
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

    def test_execute_file_withpostrun_cbf_pilatus300k(self):
        """ test nxsconfig execute file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect execute  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -x %s -r -s %s' % (filename, self.flags)).split(),
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

    def test_execute_file_withpostrun_cbf_pilatus300k_skip(self):
        """ test nxsconfig execute file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect execute  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -x %s -r -s %s' % (filename, self.flags)).split(),
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

    def test_execute_file_withpostrun_cbf_pilatus300k_wait(self):
        """ test nxsconfig execute file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect execute  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -x %s -r -s %s' % (filename, self.flags)).split(),
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

    def test_execute_file_withpostrun_cbf_pilatus300k_missing(self):
        """ test nxsconfig execute file with a cbf postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect execute  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -r %s' % (filename, self.flags)).split(),
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

    def test_execute_file_withpostrun_raw(self):
        """ test nxsconfig execute file with a cbf postrun field
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
            ('nxscollect execute  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -x %s -r -s %s' % (filename, self.flags)).split(),
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

    def test_execute_file_withpostrun_h5(self):
        """ test nxsconfig execute file with a cbf postrun field
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
            ('nxscollect execute  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -x %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect execute  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -x %s -r -s %s' % (filename, self.flags)).split(),
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
                    fl = filewriter.create_file("h5test1_%05d.h5" % i, )
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

    def test_test_file_withpostrun_tif(self):
        """ test nxsconfig test file with a tif postrun field
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        filename = 'testcollect.nxs'
        commands = [
            ('nxscollect test  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -t %s -r -s %s' % (filename, self.flags)).split(),
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
            ('nxscollect test  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -t %s -r -s %s' % (filename, self.flags)).split(),
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
            ('nxscollect test  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -t %s -r -s %s' % (filename, self.flags)).split(),
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
            ('nxscollect test  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -t %s -r -s %s' % (filename, self.flags)).split(),
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
            ('nxscollect test  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -r %s' % (filename, self.flags)).split(),
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
            ('nxscollect test  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -t %s -r -s %s' % (filename, self.flags)).split(),
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
            ('nxscollect test  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -t %s -r -s %s' % (filename, self.flags)).split(),
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
            ('nxscollect test  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -t %s -r -s %s' % (filename, self.flags)).split(),
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
            ('nxscollect test  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -t %s -r -s %s' % (filename, self.flags)).split(),
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
            ('nxscollect test  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -r %s' % (filename, self.flags)).split(),
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
            ('nxscollect test  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -t %s -r -s %s' % (filename, self.flags)).split(),
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
            ('nxscollect test  %s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -r %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect -t %s -s %s' % (filename, self.flags)).split(),
            ('nxscollect test  %s -r -s %s' %
             (filename, self.flags)).split(),
            ('nxscollect -t %s -r -s %s' % (filename, self.flags)).split(),
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
                    fl = filewriter.create_file("h5test1_%05d.h5" % i, )
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


if __name__ == '__main__':
    unittest.main()