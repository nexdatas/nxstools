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
import socket
import pickle
# import time
# import threading
try:
    import tango
except Exception:
    import PyTango as tango
# import json
# import nxstools
# from nxstools import nxscreate
# from nxstools import nxsdevicetools

import nxstools.h5cppwriter as H5CppWriter

from nxstools.pyeval import scdataset

try:
    import TestServerSetUp
except ImportError:
    from . import TestServerSetUp

if sys.version_info > (3,):
    unicode = str
    long = int


# if 64-bit machione
IS64BIT = (struct.calcsize("P") == 8)


class TstRoot(object):

    filename = ""


class TstRoot2(object):

    filename = ""
    stepsperfile = 0
    currentfileid = 0


class TstMacro(object):
    """ test macro """

    def __init__(self):
        """ constructor
        """
        self.env = {}
        self.log = []

    def getEnv(self, name):
        """ mocked get variable

        :param name: variable name
        :type name: :obj:`str`
        """
        return self.env[name]

    def setEnv(self, name, value):
        """ mocked get variable

        :param name: variable name
        :type name: :obj:`str`
        """
        print("ww", name, value)
        self.env[name] = value

    def output(self, text):
        """ mocked output function

        :param text: output text
        :type text: :obj:`str`
        """
        self.log.append(text)


# test fixture
class NXSCreatePyEvalH5CppTest(unittest.TestCase):

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
        # self.flags = " -d -r testp09/testmcs/testr228 "
        self.device = 'testp09/testmcs/testr228'
        self.fwriter = H5CppWriter
        self.maxDiff = None

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

    # float list tester
    def myAssertFloatList(self, list1, list2, error=0.0):

        self.assertEqual(len(list1), len(list2))
        for i, el in enumerate(list1):
            if abs(el - list2[i]) >= error:
                print("EL %s %s %s" % (el, list2[i], error))
            self.assertTrue(abs(el - list2[i]) < error)

    # float list tester
    def myAssertList(self, list1, list2, error=0.0):

        self.assertEqual(len(list1), len(list2))
        for i, el in enumerate(list1):
            if el != list2[i]:
                print("EL %s %s %s" % (el, list2[i], error))
            self.assertEqual(el, list2[i])

    # float image tester
    def myAssertImage(self, image1, image2, error=None):

        self.assertEqual(len(image1), len(image2))
        for i in range(len(image1)):
            self.assertEqual(len(image1[i]), len(image2[i]))
            for j in range(len(image1[i])):
                if error is not None:
                    if abs(image1[i][j] - image2[i][j]) >= error:
                        print("EL %s %s %s" % (
                            image1[i][j], image2[i][j], error))
                    self.assertTrue(abs(image1[i][j] - image2[i][j]) < error)
                else:
                    self.assertEqual(image1[i][j], image2[i][j])

    # float image tester
    def myAssertVector(self, image1, image2, error=None):

        self.assertEqual(len(image1), len(image2))
        for i in range(len(image1)):
            self.assertEqual(len(image1[i]), len(image2[i]))
            for j in range(len(image1[i])):
                self.assertEqual(len(image1[i][j]), len(image2[i][j]))
                for k in range(len(image1[i][j])):
                    if error is not None:
                        if abs(image1[i][j][k] - image2[i][j][k]) >= error:
                            print("EL %s %s %s" % (
                                image1[i][j][k], image2[i][j][k], error))
                        self.assertTrue(
                            abs(image1[i][j][k] - image2[i][j][k]) < error)
                    else:
                        self.assertEqual(image1[i][j][k], image2[i][j][k])

    def test_lambdavds_savefilename_cb(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        from nxstools.pyeval import lambdavds
        commonblock = {}

        sfn1 = "myfile1"
        sfn2 = "myfile2"

        fn1 = lambdavds.savefilename_cb(
            commonblock, sfn1, "lmbd_savefilename")
        self.assertEqual(fn1, sfn1)
        self.assertEqual(len(commonblock), 1)
        self.assertTrue("lmbd_savefilename" in commonblock)
        self.assertEqual(len(commonblock["lmbd_savefilename"]), 1)
        self.assertEqual(commonblock["lmbd_savefilename"][0],  sfn1)

        fn2 = lambdavds.savefilename_cb(
            commonblock, sfn2, "lmbd_savefilename")
        self.assertEqual(fn2, sfn2)
        self.assertEqual(len(commonblock), 1)
        self.assertTrue("lmbd_savefilename" in commonblock)
        self.assertEqual(len(commonblock["lmbd_savefilename"]), 2)
        self.assertEqual(commonblock["lmbd_savefilename"][1],  sfn2)

    def test_lambdavds_framenumbers_cb(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        from nxstools.pyeval import lambdavds
        commonblock = {}

        sfn1 = "34"
        sfn2 = 3
        rfn1 = 34
        rfn2 = 3

        fn1 = lambdavds.framenumbers_cb(
            commonblock, sfn1, "lmbd_framenumbers")
        self.assertEqual(fn1, sfn1)
        self.assertEqual(len(commonblock), 1)
        self.assertTrue("lmbd_framenumbers" in commonblock)
        self.assertEqual(len(commonblock["lmbd_framenumbers"]), 1)
        self.assertEqual(commonblock["lmbd_framenumbers"][0],  rfn1)

        fn2 = lambdavds.framenumbers_cb(
            commonblock, sfn2, "lmbd_framenumbers")
        self.assertEqual(fn2, sfn2)
        self.assertEqual(len(commonblock), 1)
        self.assertTrue("lmbd_framenumbers" in commonblock)
        self.assertEqual(len(commonblock["lmbd_framenumbers"]), 2)
        self.assertEqual(commonblock["lmbd_framenumbers"][1],  rfn2)

    def test_common_get_element(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        from nxstools.pyeval import common

        self.assertEqual(common.get_element([1, 2, 3, 4, 5], 3), 4)
        self.assertEqual(common.get_element([2, 3, 4, 5], 1), 3)

    def test_blockitem_int(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        from nxstools.pyeval import common
        commonblock = {}

        sfn1 = "34"
        sfn2 = 3
        rfn1 = 34
        rfn2 = 3

        fn1 = common.blockitem_addint(
            commonblock, "lmbd2_framenumbers", sfn1)
        self.assertEqual(fn1, sfn1)
        self.assertEqual(len(commonblock), 1)
        self.assertTrue("lmbd2_framenumbers" in commonblock)
        self.assertEqual(len(commonblock["lmbd2_framenumbers"]), 1)
        self.assertEqual(commonblock["lmbd2_framenumbers"][0],  rfn1)

        fn2 = common.blockitem_addint(
            commonblock, "lmbd2_framenumbers", sfn2)
        self.assertEqual(fn2, sfn2)
        self.assertEqual(len(commonblock), 1)
        self.assertTrue("lmbd2_framenumbers" in commonblock)
        self.assertEqual(len(commonblock["lmbd2_framenumbers"]), 2)
        self.assertEqual(commonblock["lmbd2_framenumbers"][1],  rfn2)
        fn2 = common.blockitems_rm(
            commonblock, ["lmbd2_framenumbers"])
        self.assertEqual(len(commonblock), 0)

    def test_blockitem(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        from nxstools.pyeval import common
        commonblock = {}

        sfn1 = "myfile1"
        sfn2 = "myfile2"

        fn1 = common.blockitem_add(
            commonblock, "lmbd_filename", sfn1)
        self.assertEqual(fn1, sfn1)
        self.assertEqual(len(commonblock), 1)
        self.assertTrue("lmbd_filename" in commonblock)
        self.assertEqual(len(commonblock["lmbd_filename"]), 1)
        self.assertEqual(commonblock["lmbd_filename"][0],  sfn1)

        fn2 = common.blockitem_add(
            commonblock, "lmbd_filename", sfn2)
        self.assertEqual(fn2, sfn2)
        self.assertEqual(len(commonblock), 1)
        self.assertTrue("lmbd_filename" in commonblock)
        self.assertEqual(len(commonblock["lmbd_filename"]), 2)
        self.assertEqual(commonblock["lmbd_filename"][1],  sfn2)
        fn2 = common.blockitems_rm(
            commonblock, ["lmbd_filename"])
        self.assertEqual(len(commonblock), 0)

    def test_common_filestartnum_cb(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        from nxstools.pyeval import common
        commonblock = {}

        sfn1 = 3
        nbn1 = 2

        fn1 = common.filestartnum_cb(
            commonblock, sfn1, nbn1, "andor_filestartnum")
        self.assertEqual(fn1, sfn1 - nbn1)
        self.assertEqual(len(commonblock), 1)
        self.assertTrue("andor_filestartnum" in commonblock)
        self.assertEqual(
            commonblock["andor_filestartnum"], sfn1 - nbn1 + 1)

    def test_beamtimeid_nodir(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tstroot = TstRoot()
        commonblock = {"__nxroot__": tstroot}
        tstroot.filename = "/mypath"
        start_time = "14:13:12"
        shortname = "P00"
        commissiondir = "/testgpfs/commission"
        currentdir = "/testgpfs/current"
        localdir = "/testgpfs/local"
        currentprefix = "/testgpfs"
        currentpostfix = "current"
        commissionprefix = "/testgpfs"
        commissionpostfix = "commission"
        sgh = socket.gethostname()
        btid = "%s_%s@%s" % (shortname, start_time, sgh)

        from nxstools.pyeval import beamtimeid
        result = beamtimeid.beamtimeid(
            commonblock,  start_time, shortname,
            commissiondir, currentdir, localdir,
            currentprefix, currentpostfix,
            commissionprefix, commissionpostfix)
        self.assertEqual(btid, result)

    def test_beamtimeid_current(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        cwd = os.getcwd()

        tstroot = TstRoot()
        commonblock = {"__nxroot__": tstroot}
        tstroot.filename = "%s/testcurrent/myfile.nxs" % cwd
        start_time = "14:13:12"
        shortname = "P00"
        currentdir = "%s" % cwd
        currentprefix = "beamtime-metadata-"
        currentpostfix = ".json"
        commissiondir = "/testgpfs/commission"
        commissionprefix = "beam-metadata-"
        commissionpostfix = ".jsn"
        localdir = "/testgpfs/local"
        beamtime = "2342342"

        bfn = "%s/%s%s%s" % (cwd, currentprefix, beamtime, currentpostfix)
        try:
            open(bfn, 'a').close()

            from nxstools.pyeval import beamtimeid
            result = beamtimeid.beamtimeid(
                commonblock,  start_time, shortname,
                commissiondir, currentdir, localdir,
                currentprefix, currentpostfix,
                commissionprefix, commissionpostfix)
            self.assertEqual(beamtime, result)
        finally:
            os.remove(bfn)

    def test_beamtimeid_commission(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        cwd = os.getcwd()

        tstroot = TstRoot()
        commonblock = {"__nxroot__": tstroot}
        tstroot.filename = "%s/testcurrent/myfile.nxs" % cwd
        start_time = "14:13:12"
        shortname = "P00"
        currentdir = "/testgpfs/current"
        currentprefix = "bmtime-metadata-"
        currentpostfix = ".jsn"
        commissiondir = "%s" % cwd
        commissionprefix = "beamtime-metadata-"
        commissionpostfix = ".json"
        localdir = "/testgpfs/local"
        beamtime = "2342342"

        bfn = "%s/%s%s%s" % (
            cwd, commissionprefix, beamtime, commissionpostfix)
        try:
            open(bfn, 'a').close()

            from nxstools.pyeval import beamtimeid
            result = beamtimeid.beamtimeid(
                commonblock,  start_time, shortname,
                commissiondir, currentdir, localdir,
                currentprefix, currentpostfix,
                commissionprefix, commissionpostfix)
            self.assertEqual(beamtime, result)
        finally:
            os.remove(bfn)

    def test_beamtimeid_local(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        cwd = os.getcwd()

        tstroot = TstRoot()
        commonblock = {"__nxroot__": tstroot}
        tstroot.filename = "%s/testcurrent/myfile.nxs" % cwd
        start_time = "14:13:12"
        shortname = "P00"
        currentdir = "/testgpfs/current"
        currentprefix = "bmtime-metadata-"
        currentpostfix = ".jsn"
        commissiondir = "/testgpfs/"
        commissionprefix = "beamtime-metadata-"
        commissionpostfix = ".json"
        localdir = "%s" % cwd
        beamtime = "2342342"

        bfn = "%s/%s%s%s" % (
            cwd, commissionprefix, beamtime, commissionpostfix)
        try:
            open(bfn, 'a').close()

            from nxstools.pyeval import beamtimeid
            result = beamtimeid.beamtimeid(
                commonblock,  start_time, shortname,
                commissiondir, currentdir, localdir,
                currentprefix, currentpostfix,
                commissionprefix, commissionpostfix)
            self.assertEqual(beamtime, result)
        finally:
            os.remove(bfn)

    def test_beamtime_filename_nodir(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tstroot = TstRoot()
        commonblock = {"__nxroot__": tstroot}
        tstroot.filename = "/mypath"
        start_time = "14:13:12"
        shortname = "P00"
        commissiondir = "/testgpfs/commission"
        currentdir = "/testgpfs/current"
        localdir = "/testgpfs/local"
        currentprefix = "/testgpfs"
        currentpostfix = "current"
        commissionprefix = "/testgpfs"
        commissionpostfix = "commission"
        btid = ""

        from nxstools.pyeval import beamtimeid
        result = beamtimeid.beamtime_filename(
            commonblock,  start_time, shortname,
            commissiondir, currentdir, localdir,
            currentprefix, currentpostfix,
            commissionprefix, commissionpostfix)
        self.assertEqual(btid, result)

    def test_beamtime_filename_current(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        cwd = os.getcwd()

        tstroot = TstRoot()
        commonblock = {"__nxroot__": tstroot}
        tstroot.filename = "%s/testcurrent/myfile.nxs" % cwd
        start_time = "14:13:12"
        shortname = "P00"
        currentdir = "%s" % cwd
        currentprefix = "beamtime-metadata-"
        currentpostfix = ".json"
        commissiondir = "/testgpfs/commission"
        commissionprefix = "beam-metadata-"
        commissionpostfix = ".jsn"
        localdir = "/testgpfs/local"
        beamtime = "2342342"

        bfn = "%s/%s%s%s" % (cwd, currentprefix, beamtime, currentpostfix)
        try:
            open(bfn, 'a').close()

            from nxstools.pyeval import beamtimeid
            result = beamtimeid.beamtime_filename(
                commonblock,  start_time, shortname,
                commissiondir, currentdir, localdir,
                currentprefix, currentpostfix,
                commissionprefix, commissionpostfix)
            self.assertEqual(bfn, result)
        finally:
            os.remove(bfn)

    def test_beamtime_filename_commission(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        cwd = os.getcwd()

        tstroot = TstRoot()
        commonblock = {"__nxroot__": tstroot}
        tstroot.filename = "%s/testcurrent/myfile.nxs" % cwd
        start_time = "14:13:12"
        shortname = "P00"
        currentdir = "/testgpfs/current"
        currentprefix = "bmtime-metadata-"
        currentpostfix = ".jsn"
        commissiondir = "%s" % cwd
        commissionprefix = "beamtime-metadata-"
        commissionpostfix = ".json"
        localdir = "/testgpfs/local"
        beamtime = "2342342"

        bfn = "%s/%s%s%s" % (
            cwd, commissionprefix, beamtime, commissionpostfix)
        try:
            open(bfn, 'a').close()

            from nxstools.pyeval import beamtimeid
            result = beamtimeid.beamtime_filename(
                commonblock,  start_time, shortname,
                commissiondir, currentdir, localdir,
                currentprefix, currentpostfix,
                commissionprefix, commissionpostfix)
            self.assertEqual(bfn, result)
        finally:
            os.remove(bfn)

    def test_beamtime_filename_local(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        cwd = os.getcwd()

        tstroot = TstRoot()
        commonblock = {"__nxroot__": tstroot}
        tstroot.filename = "%s/testcurrent/myfile.nxs" % cwd
        start_time = "14:13:12"
        shortname = "P00"
        currentdir = "/testgpfs/current"
        currentprefix = "bmtime-metadata-"
        currentpostfix = ".jsn"
        commissiondir = "/testgpfs/"
        commissionprefix = "beamtime-metadata-"
        commissionpostfix = ".json"
        localdir = "%s" % cwd
        beamtime = "2342342"

        bfn = "%s/%s%s%s" % (
            cwd, commissionprefix, beamtime, commissionpostfix)
        try:
            open(bfn, 'a').close()

            from nxstools.pyeval import beamtimeid
            result = beamtimeid.beamtime_filename(
                commonblock,  start_time, shortname,
                commissiondir, currentdir, localdir,
                currentprefix, currentpostfix,
                commissionprefix, commissionpostfix)
            self.assertEqual(bfn, result)
        finally:
            os.remove(bfn)

    def test_lambdavds_triggermode_cb_nosave(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        commonblock = {}
        name = "lmbd"
        triggermode = 0
        saveallimages = False
        framesperfile = 10
        height = 2321
        width = 32
        opmode = 6
        filepostfix = "nxs"

        from nxstools.pyeval import lambdavds
        result = lambdavds.triggermode_cb(
            commonblock,
            name,
            triggermode,
            saveallimages,
            framesperfile,
            height,
            width,
            opmode,
            filepostfix,
            "lmbd_savefilename",
            "lmbd_framenumbers",
            "myfile_24234.nxs",
            "entry1234")
        self.assertEqual(triggermode, result)

    def test_lambdavds_triggermode_cb_onefile(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        fileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "lmbd"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = '%s_00000.nxs' % (fileprefix)
        sfname1 = '%s_00000' % (fileprefix)
        ffname1 = '%s/%s' % (path, fname1)

        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass
            fl1 = self.fwriter.create_file(ffname1, overwrite=True)
            rt = fl1.root()
            entry = rt.create_group("entry", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("detector", "NXdetector")
            intimage = det.create_field(
                "data", "uint32", [30, 10, 20], [1, 10, 20])
            intimage[...] = vl
            intimage.close()
            det.close()
            ins.close()
            entry.close()
            fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")

            commonblock = {
                "lmbd_savefilename": [sfname1],
                "lmbd_framenumbers": [30],
                "__root__": rt,
            }
            triggermode = 0
            saveallimages = True
            framesperfile = 0
            height = 10
            width = 20
            opmode = 24
            filepostfix = "nxs"

            from nxstools.pyeval import lambdavds
            result = lambdavds.triggermode_cb(
                commonblock,
                name,
                triggermode,
                saveallimages,
                framesperfile,
                height,
                width,
                opmode,
                filepostfix,
                "lmbd_savefilename",
                "lmbd_framenumbers",
                filename,
                entryname)
            self.assertEqual(triggermode, result)

            images = det.open("data")
            rw = images.read()
            for i in range(30):
                self.myAssertImage(rw[i], vl[i])
            intimage.close()
            det.close()
            ins.close()
            entry.close()
            fl.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_lambdavds_triggermode_cb_singleframe(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        fileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "lmbd"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['%s_%05d.nxs' % (fileprefix, i) for i in range(30)]
        sfname1 = ['%s_%05d' % (fileprefix, i) for i in range(30)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]

        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass
            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("detector", "NXdetector")
                intimage = det.create_field(
                    "data", "uint32", [1, 10, 20], [1, 10, 20])
                vv = [[[vl[i][jj][ii] for ii in range(20)]
                       for jj in range(10)]]
                intimage[0, :, :] = vv
                intimage.close()
                det.close()
                ins.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")

            commonblock = {
                "lmbd_savefilename": sfname1,
                "lmbd_framenumbers": [1] * 30,
                "__root__": rt,
            }
            triggermode = 0
            saveallimages = True
            framesperfile = 0
            height = 10
            width = 20
            opmode = 24
            filepostfix = "nxs"

            from nxstools.pyeval import lambdavds
            result = lambdavds.triggermode_cb(
                commonblock,
                name,
                triggermode,
                saveallimages,
                framesperfile,
                height,
                width,
                opmode,
                filepostfix,
                "lmbd_savefilename",
                "lmbd_framenumbers",
                filename,
                entryname)
            self.assertEqual(triggermode, result)

            images = det.open("data")
            rw = images.read()
            for i in range(30):
                self.myAssertImage(rw[i], vl[i])
            intimage.close()
            det.close()
            ins.close()
            entry.close()
            fl.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_lambdavds_triggermode_cb_splitmode(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        fileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "lmbd"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['%s_00000_part%05d.nxs' % (fileprefix, i) for i in range(3)]
        sfname1 = ['%s_00000_part%05d' % (fileprefix, i) for i in range(3)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]
        framenumbers = [14, 14, 2]

        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass

            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("detector", "NXdetector")
                intimage = det.create_field(
                    "data", "uint32",
                    [framenumbers[i], 10, 20], [1, 10, 20])
                vv = [[[vl[i * framenumbers[0] + nn][jj][ii]
                        for ii in range(20)]
                       for jj in range(10)]
                      for nn in range(framenumbers[i])]
                intimage[:, :, :] = vv
                intimage.close()
                det.close()
                ins.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")

            commonblock = {
                "lmbd_savefilename": sfname1,
                "lmbd_framenumbers": framenumbers,
                "__root__": rt,
            }
            triggermode = 0
            saveallimages = True
            framesperfile = 14
            height = 10
            width = 20
            opmode = 24
            filepostfix = "nxs"

            from nxstools.pyeval import lambdavds
            result = lambdavds.triggermode_cb(
                commonblock,
                name,
                triggermode,
                saveallimages,
                framesperfile,
                height,
                width,
                opmode,
                filepostfix,
                "lmbd_savefilename",
                "lmbd_framenumbers",
                filename,
                entryname)
            self.assertEqual(triggermode, result)

            images = det.open("data")
            fl.flush()
            rw = images.read()
            for i in range(30):
                self.myAssertImage(rw[i], vl[i])
            intimage.close()
            det.close()
            ins.close()
            entry.close()
            fl.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_minipix_triggermode_cb_nosave(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        commonblock = {}
        name = "minipix1"
        triggermode = 0
        saveallimages = False
        framesperfile = 10
        height = 2321
        width = 32
        opmode = 6
        filepostfix = "nxs"

        from nxstools.pyeval import minipix
        result = minipix.triggermode_cb(
            commonblock,
            name,
            triggermode,
            saveallimages,
            framesperfile,
            height,
            width,
            opmode,
            filepostfix,
            "minipix1_savefilename",
            "minipix1_framenumbers",
            "myfile_24234.nxs",
            "entry1234")
        self.assertEqual(triggermode, result)

    def test_minipix_triggermode_cb_onefile(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        fileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "minipix1"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = '%s_00000.nxs' % (fileprefix)
        sfname1 = '%s_00000' % (fileprefix)
        ffname1 = '%s/%s' % (path, fname1)

        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass
            fl1 = self.fwriter.create_file(ffname1, overwrite=True)
            rt = fl1.root()
            entry = rt.create_group("entry", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("detector", "NXdetector")
            intimage = det.create_field(
                "data", "uint16", [30, 10, 20], [1, 10, 20])
            intimage[...] = vl
            intimage.close()
            det.close()
            ins.close()
            entry.close()
            fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")

            commonblock = {
                "minipix1_savefilename": [sfname1],
                "minipix1_framenumbers": [30],
                "__root__": rt,
            }
            triggermode = 0
            saveallimages = True
            framesperfile = 0
            height = 10
            width = 20
            opmode = 24
            filepostfix = "nxs"

            from nxstools.pyeval import minipix
            result = minipix.triggermode_cb(
                commonblock,
                name,
                triggermode,
                saveallimages,
                framesperfile,
                height,
                width,
                opmode,
                filepostfix,
                "minipix1_savefilename",
                "minipix1_framenumbers",
                filename,
                entryname)
            self.assertEqual(triggermode, result)

            images = det.open("data")
            rw = images.read()
            for i in range(30):
                self.myAssertImage(rw[i], vl[i])
            intimage.close()
            det.close()
            ins.close()
            entry.close()
            fl.close()
        finally:
            # pass
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_minipix_triggermode_cb_singleframe(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        fileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "minipix1"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['%s_%05d.nxs' % (fileprefix, i) for i in range(30)]
        sfname1 = ['%s_%05d' % (fileprefix, i) for i in range(30)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]

        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass
            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("detector", "NXdetector")
                intimage = det.create_field(
                    "data", "uint16", [1, 10, 20], [1, 10, 20])
                vv = [[[vl[i][jj][ii] for ii in range(20)]
                       for jj in range(10)]]
                intimage[0, :, :] = vv
                intimage.close()
                det.close()
                ins.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")

            commonblock = {
                "minipix1_savefilename": sfname1,
                "minipix1_framenumbers": [1] * 30,
                "__root__": rt,
            }
            triggermode = 0
            saveallimages = True
            framesperfile = 0
            height = 10
            width = 20
            opmode = 24
            filepostfix = "nxs"

            from nxstools.pyeval import minipix
            result = minipix.triggermode_cb(
                commonblock,
                name,
                triggermode,
                saveallimages,
                framesperfile,
                height,
                width,
                opmode,
                filepostfix,
                "minipix1_savefilename",
                "minipix1_framenumbers",
                filename,
                entryname)
            self.assertEqual(triggermode, result)

            images = det.open("data")
            rw = images.read()
            for i in range(30):
                self.myAssertImage(rw[i], vl[i])
            intimage.close()
            det.close()
            ins.close()
            entry.close()
            fl.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_minipix_triggermode_cb_splitmode(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        fileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "minipix1"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['%s_00000_part%05d.nxs' % (fileprefix, i) for i in range(3)]
        sfname1 = ['%s_00000_part%05d' % (fileprefix, i) for i in range(3)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]
        framenumbers = [14, 14, 2]

        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass

            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("detector", "NXdetector")
                intimage = det.create_field(
                    "data", "uint16",
                    [framenumbers[i], 10, 20], [1, 10, 20])
                vv = [[[vl[i * framenumbers[0] + nn][jj][ii]
                        for ii in range(20)]
                       for jj in range(10)]
                      for nn in range(framenumbers[i])]
                intimage[:, :, :] = vv
                intimage.close()
                det.close()
                ins.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")

            commonblock = {
                "minipix1_savefilename": sfname1,
                "minipix1_framenumbers": framenumbers,
                "__root__": rt,
            }
            triggermode = 0
            saveallimages = True
            framesperfile = 14
            height = 10
            width = 20
            opmode = 24
            filepostfix = "nxs"

            from nxstools.pyeval import minipix
            result = minipix.triggermode_cb(
                commonblock,
                name,
                triggermode,
                saveallimages,
                framesperfile,
                height,
                width,
                opmode,
                filepostfix,
                "minipix1_savefilename",
                "minipix1_framenumbers",
                filename,
                entryname)
            self.assertEqual(triggermode, result)

            images = det.open("data")
            fl.flush()
            rw = images.read()
            for i in range(30):
                self.myAssertImage(rw[i], vl[i])
            intimage.close()
            det.close()
            ins.close()
            entry.close()
            fl.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_signalname_detector(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345
        self._fname = "%s_%s.nxs" % (mfileprefix, scanid)

        try:

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            fl.writer = self.fwriter
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            dt = entry.create_group("data", "NXdata")
            dt.create_field(
                "pilatus", "uint32", [30, 30, 20], [1, 30, 20]).close()
            dt.create_field(
                "lambda", "uint32", [30, 30, 10], [1, 30, 10]).close()
            dt.create_field("exp_c01", "uint32", [30], [1]).close()
            dt.create_field("exp_t01", "uint32", [30], [1]).close()
            dt.create_field("exp_c02", "uint32", [30], [1]).close()

            signalname = "lambda"

            commonblock = {"__root__": rt}
            detector = "lambda"
            firstchannel = "exp_c01"
            timers = "exp_t01 exp_t02"
            mgchannels = "pilatus exp_c01 exp_c02 ext_t01"
            entryname = "entry123"

            from nxstools.pyeval import datasignal
            result = datasignal.signalname(
                commonblock,
                detector,
                firstchannel,
                timers,
                mgchannels,
                entryname,
                True)
            self.assertEqual(signalname, result)
            self.assertTrue("default" in rt.attributes.names())
            endef = rt.attributes["default"][...]
            self.assertEqual(endef, entryname)
            self.assertTrue("default" in entry.attributes.names())
            dtdef = entry.attributes["default"][...]
            self.assertEqual(dtdef, "data")

            dt.close()
            entry.close()
            fl.close()
        finally:
            if os.path.exists(self._fname):
                os.remove(self._fname)

    def test_signalname_firstchannel(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345
        self._fname = "%s_%s.nxs" % (mfileprefix, scanid)

        try:

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            fl.writer = self.fwriter
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            dt = entry.create_group("data", "NXdata")
            dt.create_field(
                "pilatus", "uint32", [30, 30, 20], [1, 30, 20]).close()
            dt.create_field(
                "lambda", "uint32", [30, 30, 10], [1, 30, 10]).close()
            dt.create_field("exp_c01", "uint32", [30], [1]).close()
            dt.create_field("exp_t01", "uint32", [30], [1]).close()
            dt.create_field("exp_c02", "uint32", [30], [1]).close()

            signalname = "exp_c01"

            commonblock = {"__root__": rt}
            detector = "lambda2"
            firstchannel = "exp_c01"
            timers = "exp_t01 exp_t02"
            mgchannels = "pilatus exp_c01 exp_c02 ext_t01"
            entryname = "entry123"

            from nxstools.pyeval import datasignal
            result = datasignal.signalname(
                commonblock,
                detector,
                firstchannel,
                timers,
                mgchannels,
                entryname,
                False
            )
            self.assertEqual(signalname, result)
            self.assertTrue("default" not in rt.attributes.names())
            self.assertTrue("default" not in entry.attributes.names())

            dt.close()
            entry.close()
            fl.close()
        finally:
            if os.path.exists(self._fname):
                os.remove(self._fname)

    def test_signalname_sardanasignal(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345
        self._fname = "%s_%s.nxs" % (mfileprefix, scanid)

        env = {"new": {
            'NeXusSelectorDevice': 'nxs/nxsrecselector/dellek',
            'ScanFile': ['sdfsdf.nxs', 'sdfsdf.fio'],
            'Signal': 'exp_c02',
            'SignalCounter': 'exp_c01',
            'ScanDir': '/tmp'}}
        penv = pickle.dumps(env)
        varname = "Signal"

        try:

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            fl.writer = self.fwriter
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            dt = entry.create_group("data", "NXdata")
            dt.create_field(
                "pilatus", "uint32", [30, 30, 20], [1, 30, 20]).close()
            dt.create_field(
                "lambda", "uint32", [30, 30, 10], [1, 30, 10]).close()
            dt.create_field("exp_c01", "uint32", [30], [1]).close()
            dt.create_field("exp_t01", "uint32", [30], [1]).close()
            dt.create_field("exp_c02", "uint32", [30], [1]).close()

            signalname = "exp_c02"

            commonblock = {"__root__": rt}
            detector = "lambda2"
            firstchannel = "exp_c01"
            timers = "exp_t01 exp_t02"
            mgchannels = "pilatus exp_c01 exp_c02 ext_t01"
            entryname = "entry123"

            from nxstools.pyeval import datasignal
            result = datasignal.signalname(
                commonblock,
                detector,
                firstchannel,
                timers,
                mgchannels,
                entryname,
                False,
                0,
                penv,
                varname
            )
            self.assertEqual(signalname, result)
            self.assertTrue("default" not in rt.attributes.names())
            self.assertTrue("default" not in entry.attributes.names())

            dt.close()
            entry.close()
            fl.close()
        finally:
            if os.path.exists(self._fname):
                os.remove(self._fname)

    def test_signalname_sardanaenv(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345
        self._fname = "%s_%s.nxs" % (mfileprefix, scanid)

        env = {"new": {
            'NeXusSelectorDevice': 'nxs/nxsrecselector/dellek',
            'ScanFile': ['sdfsdf.nxs', 'sdfsdf.fio'],
            'SignalCounter': 'exp_c02',
            'ScanDir': '/tmp'}}
        penv = pickle.dumps(env)

        try:

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            fl.writer = self.fwriter
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            dt = entry.create_group("data", "NXdata")
            dt.create_field(
                "pilatus", "uint32", [30, 30, 20], [1, 30, 20]).close()
            dt.create_field(
                "lambda", "uint32", [30, 30, 10], [1, 30, 10]).close()
            dt.create_field("exp_c01", "uint32", [30], [1]).close()
            dt.create_field("exp_t01", "uint32", [30], [1]).close()
            dt.create_field("exp_c02", "uint32", [30], [1]).close()

            signalname = "exp_c02"

            commonblock = {"__root__": rt}
            detector = "lambda2"
            firstchannel = "exp_c01"
            timers = "exp_t01 exp_t02"
            mgchannels = "pilatus exp_c01 exp_c02 ext_t01"
            entryname = "entry123"

            from nxstools.pyeval import datasignal
            result = datasignal.signalname(
                commonblock,
                detector,
                firstchannel,
                timers,
                mgchannels,
                entryname,
                False,
                0,
                penv
            )
            self.assertEqual(signalname, result)
            self.assertTrue("default" not in rt.attributes.names())
            self.assertTrue("default" not in entry.attributes.names())

            dt.close()
            entry.close()
            fl.close()
        finally:
            if os.path.exists(self._fname):
                os.remove(self._fname)

    def test_signalname_mgchannels(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345
        self._fname = "%s_%s.nxs" % (mfileprefix, scanid)

        try:

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            fl.writer = self.fwriter
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            dt = entry.create_group("data", "NXdata")
            dt.create_field(
                "pilatus", "uint32", [30, 30, 20], [1, 30, 20]).close()
            dt.create_field(
                "lambda", "uint32", [30, 30, 10], [1, 30, 10]).close()
            dt.create_field("exp_c01", "uint32", [30], [1]).close()
            dt.create_field("exp_t01", "uint32", [30], [1]).close()
            dt.create_field("exp_c02", "uint32", [30], [1]).close()

            signalname = "pilatus"

            commonblock = {"__root__": rt}
            detector = "lambda2"
            firstchannel = "exp_c03"
            timers = "exp_t01 exp_t02"
            mgchannels = "pilatus exp_c01 exp_c02 ext_t01"
            entryname = "entry123"

            from nxstools.pyeval import datasignal
            result = datasignal.signalname(
                commonblock,
                detector,
                firstchannel,
                timers,
                mgchannels,
                entryname)
            self.assertEqual(signalname, result)

            dt.close()
            entry.close()
            fl.close()
        finally:
            if os.path.exists(self._fname):
                os.remove(self._fname)

    def test_signalname_alphabetic(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345
        self._fname = "%s_%s.nxs" % (mfileprefix, scanid)

        try:

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            fl.writer = self.fwriter
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            dt = entry.create_group("data", "NXdata")
            dt.create_field(
                "pilatus", "uint32", [30, 30, 20], [1, 30, 20]).close()
            dt.create_field(
                "lambda", "uint32", [30, 30, 10], [1, 30, 10]).close()
            dt.create_field("exp_c01", "uint32", [30], [1]).close()
            dt.create_field("exp_t01", "uint32", [30], [1]).close()
            dt.create_field("exp_c02", "uint32", [30], [1]).close()

            signalname = "exp_c01"

            commonblock = {"__root__": rt}
            detector = "lambda2"
            firstchannel = "exp_c03"
            timers = "exp_t01 exp_t02"
            mgchannels = "exp_c03"
            entryname = "entry123"

            from nxstools.pyeval import datasignal
            result = datasignal.signalname(
                commonblock,
                detector,
                firstchannel,
                timers,
                mgchannels,
                entryname)
            self.assertEqual(signalname, result)

            dt.close()
            entry.close()
            fl.close()
        finally:
            if os.path.exists(self._fname):
                os.remove(self._fname)

    def test_signalname_nofields(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345
        self._fname = "%s_%s.nxs" % (mfileprefix, scanid)

        try:

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            fl.writer = self.fwriter
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            dt = entry.create_group("data", "NXdata")

            signalname = ""

            commonblock = {"__root__": rt}
            detector = "lambda2"
            firstchannel = "exp_c03"
            timers = "exp_t01 exp_t02"
            mgchannels = "exp_c03"
            entryname = "entry123"

            from nxstools.pyeval import datasignal
            result = datasignal.signalname(
                commonblock,
                detector,
                firstchannel,
                timers,
                mgchannels,
                entryname)
            self.assertEqual(signalname, result)

            dt.close()
            entry.close()
            fl.close()
        finally:
            if os.path.exists(self._fname):
                os.remove(self._fname)

    def test_axesnames_scancommand(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345
        self._fname = "%s_%s.nxs" % (mfileprefix, scanid)

        env = {"new": {
            'NeXusSelectorDevice': 'nxs/nxsrecselector/dellek',
            'ScanFile': ['sdfsdf.nxs', 'sdfsdf.fio'],
            'Signal': 'exp_c02',
            'SignalCounter': 'exp_c01',
            'ScanDir': '/tmp'}}
        penv = pickle.dumps(env)
        varname = "Signal"

        try:

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            fl.writer = self.fwriter
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            dt = entry.create_group("data", "NXdata")
            dt.create_field(
                "pilatus", "uint32", [30, 30, 20], [1, 30, 20]).close()
            dt.create_field(
                "lambda", "uint32", [30, 30, 10], [1, 30, 10]).close()
            dt.create_field("exp_c01", "uint32", [30], [1]).close()
            dt.create_field("exp_t01", "uint32", [30], [1]).close()
            dt.create_field("exp_c02", "uint32", [30], [1]).close()
            dt.create_field("exp_mot01", "uint32", [30], [1]).close()
            dt.create_field("exp_mot02", "uint32", [30], [1]).close()

            axesnames = ["exp_mot02"]

            commonblock = {"__root__": rt}
            detector = "lambda2"
            firstchannel = "exp_c01"
            timers = "exp_t01 exp_t02"
            mgchannels = "pilatus exp_c01 exp_c02 ext_t01"
            stepdss = "exp_mot01 exp_mot02"
            entryname = "entry123"
            scancmd = "ascan exp_mot02 0 10 10 0.1"

            from nxstools.pyeval import datasignal
            result = datasignal.axesnames(
                commonblock,
                detector,
                firstchannel,
                timers,
                mgchannels,
                entryname,
                stepdss,
                0,
                scancmd,
                penv,
                varname
            )
            self.assertEqual(axesnames, result)
            self.assertTrue("default" not in rt.attributes.names())
            self.assertTrue("default" not in entry.attributes.names())

            dt.close()
            entry.close()
            fl.close()
        finally:
            if os.path.exists(self._fname):
                os.remove(self._fname)

    def test_axesnames_stepdss(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345
        self._fname = "%s_%s.nxs" % (mfileprefix, scanid)

        try:

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            fl.writer = self.fwriter
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            dt = entry.create_group("data", "NXdata")
            dt.create_field(
                "pilatus", "uint32", [30, 30, 20], [1, 30, 20]).close()
            dt.create_field(
                "lambda", "uint32", [30, 30, 10], [1, 30, 10]).close()
            dt.create_field("exp_c01", "uint32", [30], [1]).close()
            dt.create_field("exp_t01", "uint32", [30], [1]).close()
            dt.create_field("exp_c02", "uint32", [30], [1]).close()
            dt.create_field("exp_mot01", "uint32", [30], [1]).close()
            dt.create_field("exp_mot02", "uint32", [30], [1]).close()

            axesnames = ["exp_mot01"]

            commonblock = {"__root__": rt}
            detector = "lambda2"
            firstchannel = "exp_c01"
            timers = "exp_t01 exp_t02"
            mgchannels = "pilatus exp_c01 exp_c02 ext_t01"
            stepdss = "exp_mot01 exp_mot02"
            entryname = "entry123"

            from nxstools.pyeval import datasignal
            result = datasignal.axesnames(
                commonblock,
                detector,
                firstchannel,
                timers,
                mgchannels,
                entryname,
                stepdss,
                0
            )
            self.assertEqual(axesnames, result)
            self.assertTrue("default" not in rt.attributes.names())
            self.assertTrue("default" not in entry.attributes.names())

            dt.close()
            entry.close()
            fl.close()
        finally:
            if os.path.exists(self._fname):
                os.remove(self._fname)

    def test_absorber_thickness(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        position = 6
        thicknesslist = "[3.2,23.23,123.4,12345.3]"
        thl = [0, 23.23, 123.4, 0]

        from nxstools.pyeval import absorber
        result = absorber.thickness(position, thicknesslist)
        self.assertEqual(thl, result)

    def test_absorber_foil(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        position = 45
        foillist = '["Ag", "Ag", "Ag", "Ag", "", "Al", "Al", "Al", "Al"]'
        thl = ["Ag", "", "Ag", "Ag", "", "Al", "", "", ""]

        from nxstools.pyeval import absorber
        result = absorber.foil(position, foillist)
        self.assertEqual(thl, result)

    def test_qbpm_foil(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        position = 25
        foildict = '{"Ti": 43, "Ni": 23, "Out": 4}'
        foil = "Ni"

        from nxstools.pyeval import qbpm
        result = qbpm.foil(position, foildict)
        self.assertEqual(foil, result)

    def test_mssar_env(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        env = {"new": {
            'NeXusSelectorDevice': 'nxs/nxsrecselector/dellek',
            'ScanFile': ['sdfsdf.nxs', 'sdfsdf.fio'],
            'ScanDir': '/tmp'}}
        penv = pickle.dumps(env)
        value = "/tmp"
        varname = "ScanDir"

        from nxstools.pyeval import mssar
        result = mssar.mssarenv(penv, varname)
        self.assertEqual(value, result)

    def test_msnsar_env(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        env = {"new": {
            'NeXusSelectorDevice': 'nxs/nxsrecselector/dellek',
            'ScanFile': ['sdfsdf.nxs', 'sdfsdf.fio'],
            'ScanDir': '/tmp'}}
        penv = pickle.dumps(env)
        values = 'sdfsdf.fio'
        varnames = '["ScanFile", 1]'

        from nxstools.pyeval import mssar
        result = mssar.msnsarenv(penv, varnames)
        self.assertEqual(values, result)

    def test_lmbd_m2_external_data(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        commonblock = {}
        name = "lmbd"
        savefilename = "mtest_2342"
        saveallimages = 1
        filepostfix = "nxs"
        filename = "/tmp/scans/mytest_324234.nxs"
        modulename = "m2"
        sfn1 = "mytest_324234/lmbd/mtest_2342_m2.nxs:" \
            "//entry/instrument/detector"
        sfn2 = "lmbd/mtest_2342_m2.nxs://entry/instrument/detector"

        from nxstools.pyeval import lmbd
        fn1 = lmbd.m2_external_data(
            commonblock, name, savefilename, saveallimages,
            filepostfix, filename, modulename)
        self.assertEqual(fn1, sfn1)
        fn1 = lmbd.m2_external_data(
            commonblock, name, savefilename, False,
            filepostfix, filename, modulename)
        self.assertEqual(fn1, "")
        fn2 = lmbd.m2_external_data(
            commonblock, name, savefilename, saveallimages,
            filepostfix, "", modulename)
        self.assertEqual(fn2, sfn2)

    def test_lmbd_m2_external_data_in(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        commonblock = {}
        name = "lmbd"
        savefilename = "mtest_2342"
        saveallimages = 1
        filepostfix = "nxs"
        filename = "/tmp/mytest_324234/mytest_324234.nxs"
        modulename = "m2"
        sfn1 = "lmbd/mtest_2342_m2.nxs:" \
            "//entry/instrument/detector"
        sfn2 = "lmbd/mtest_2342_m2.nxs://entry/instrument/detector"

        from nxstools.pyeval import lmbd
        fn1 = lmbd.m2_external_data(
            commonblock, name, savefilename, saveallimages,
            filepostfix, filename, modulename)
        self.assertEqual(fn1, sfn1)
        fn1 = lmbd.m2_external_data(
            commonblock, name, savefilename, False,
            filepostfix, filename, modulename)
        self.assertEqual(fn1, "")
        fn2 = lmbd.m2_external_data(
            commonblock, name, savefilename, saveallimages,
            filepostfix, "", modulename)
        self.assertEqual(fn2, sfn2)

    def test_lmbd_external_data(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tstroot = TstRoot2()
        commonblock = {"__root__": tstroot}
        name = "lmbd"
        savefilename = "mtest_2342"
        saveallimages = 1
        filepostfix = "nxs"
        framesperfile = 40
        framenumbers = 20
        filename = "/tmp/scans/mytest_324234.nxs"
        sfn1 = "mytest_324234/lmbd/mtest_2342.nxs:" \
            "//entry/instrument/detector"
        sfn2 = "lmbd/mtest_2342.nxs://entry/instrument/detector"
        sfn3 = "lmbd/mtest_2342_part00000.nxs://entry/instrument/detector"
        sfn4 = "mytest_324234/lmbd/mtest_2342_part00002.nxs:" \
            "//entry/instrument/detector"
        sfn5 = "lmbd/mtest_2342_part00002.nxs:" \
            "//entry/instrument/detector"

        from nxstools.pyeval import lmbd
        fn1 = lmbd.external_data(
            commonblock, name, savefilename, saveallimages,
            framesperfile, framenumbers,
            filepostfix, filename)
        self.assertEqual(fn1, sfn1)
        fn1 = lmbd.external_data(
            commonblock, name, savefilename, False,
            framesperfile, framenumbers,
            filepostfix, filename)
        self.assertEqual(fn1, "")
        fn2 = lmbd.external_data(
            commonblock, name, savefilename, saveallimages,
            framesperfile, framenumbers,
            filepostfix, "")
        self.assertEqual(fn2, sfn2)

        framesperfile = 20
        framenumbers = 50
        fn2 = lmbd.external_data(
            commonblock, name, savefilename, saveallimages,
            framesperfile, framenumbers,
            filepostfix, "")
        self.assertEqual(fn2, sfn2)

        framesperfile = 20
        framenumbers = 50
        tstroot.stepsperfile = 20
        tstroot.currentfileid = 1
        fn2 = lmbd.external_data(
            commonblock, name, savefilename, saveallimages,
            framesperfile, framenumbers,
            filepostfix, "")
        self.assertEqual(fn2, sfn3)

        tstroot.stepsperfile = 20
        tstroot.currentfileid = 3
        filename = "/tmp/scans/mytest_324234.nxs"
        fn4 = lmbd.external_data(
            commonblock, name, savefilename, saveallimages,
            framesperfile, framenumbers,
            filepostfix, filename)
        self.assertEqual(fn4, sfn4)

        tstroot.stepsperfile = 20
        tstroot.currentfileid = 3
        filename = "/tmp/scans/mytest_324234.nxs"
        fn5 = lmbd.external_data(
            commonblock, name, savefilename, saveallimages,
            framesperfile, framenumbers,
            filepostfix, filename, shortdetpath=True)
        self.assertEqual(fn5, sfn5)

    def test_lmbd_external_data_in(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tstroot = TstRoot2()
        commonblock = {"__root__": tstroot}
        name = "lmbd"
        savefilename = "mtest_2342"
        saveallimages = 1
        filepostfix = "nxs"
        framesperfile = 40
        framenumbers = 20
        filename = "/tmp/mytest_324234/mytest_324234.nxs"
        sfn1 = "lmbd/mtest_2342.nxs:" \
            "//entry/instrument/detector"
        sfn2 = "lmbd/mtest_2342.nxs://entry/instrument/detector"
        sfn3 = "lmbd/mtest_2342_part00000.nxs://entry/instrument/detector"
        sfn4 = "lmbd/mtest_2342_part00002.nxs:" \
            "//entry/instrument/detector"
        sfn5 = "mytest_324234/lmbd/mtest_2342_part00002.nxs:" \
            "//entry/instrument/detector"

        from nxstools.pyeval import lmbd
        fn1 = lmbd.external_data(
            commonblock, name, savefilename, saveallimages,
            framesperfile, framenumbers,
            filepostfix, filename)
        self.assertEqual(fn1, sfn1)
        fn1 = lmbd.external_data(
            commonblock, name, savefilename, False,
            framesperfile, framenumbers,
            filepostfix, filename)
        self.assertEqual(fn1, "")
        fn2 = lmbd.external_data(
            commonblock, name, savefilename, saveallimages,
            framesperfile, framenumbers,
            filepostfix, "")
        self.assertEqual(fn2, sfn2)

        framesperfile = 20
        framenumbers = 50
        fn2 = lmbd.external_data(
            commonblock, name, savefilename, saveallimages,
            framesperfile, framenumbers,
            filepostfix, "")
        self.assertEqual(fn2, sfn2)

        framesperfile = 20
        framenumbers = 50
        tstroot.stepsperfile = 20
        tstroot.currentfileid = 1
        fn2 = lmbd.external_data(
            commonblock, name, savefilename, saveallimages,
            framesperfile, framenumbers,
            filepostfix, "")
        self.assertEqual(fn2, sfn3)

        tstroot.stepsperfile = 20
        tstroot.currentfileid = 3
        filename = "/tmp/mytest_324234/mytest_324234.nxs"
        fn4 = lmbd.external_data(
            commonblock, name, savefilename, saveallimages,
            framesperfile, framenumbers,
            filepostfix, filename)
        self.assertEqual(fn4, sfn4)

        tstroot.stepsperfile = 20
        tstroot.currentfileid = 3
        filename = "/tmp/mytest_324234/mytest_324234.nxs"
        fn5 = lmbd.external_data(
            commonblock, name, savefilename, saveallimages,
            framesperfile, framenumbers,
            filepostfix, filename, shortdetpath=False)
        self.assertEqual(fn5, sfn5)

    def test_pco_postrun(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        from nxstools.pyeval import pco

        tstroot = TstRoot2()
        commonblock = {"__root__": tstroot}
        filestartnum = 20
        filedir = "/tmp/current/"
        nbframes = 20
        filepostfix = ".tif"
        fileprefix = "scan213123_"
        filestartnum_str = "pco2_filestartnum"
        commonblock[filestartnum_str] = 1

        sfn1 = "/tmp/current/scan213123_%05d.tif:0:19"

        fn1 = pco.postrun(
            commonblock, filestartnum, filedir, nbframes,
            filepostfix, fileprefix, filestartnum_str)
        self.assertEqual(fn1, sfn1)

        tstroot.stepsperfile = 20
        tstroot.currentfileid = 1
        fn1 = pco.postrun(
            commonblock, filestartnum, filedir, nbframes,
            filepostfix, fileprefix, filestartnum_str)
        self.assertEqual(fn1, sfn1)

    def test_marccd_postrun(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        from nxstools.pyeval import marccd

        tstroot = TstRoot2()
        commonblock = {"__root__": tstroot}

        savingdirectory = "/tmp/current/"
        savingprefix = "scan_213123"
        savingpostfix = "tif"
        sfn1 = "/tmp/current/scan_213123.tif"

        fn1 = marccd.postrun(
            commonblock,
            savingdirectory,
            savingprefix,
            savingpostfix)

        self.assertEqual(fn1, sfn1)

    def test_mythen_postrun(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        from nxstools.pyeval import mythen

        tstroot = TstRoot2()
        commonblock = {"__root__": tstroot}
        fileindex = 20
        filedir = "/tmp/current/"
        fileprefix = "scan213123"
        fileindex_str = "mythen_fileindex"
        commonblock[fileindex_str] = 1

        sfn1 = "/tmp/current/scan213123_%d.raw:1:19"

        fn1 = mythen.postrun(
            commonblock,
            fileindex,
            filedir,
            fileprefix,
            fileindex_str)

        self.assertEqual(fn1, sfn1)

        tstroot.stepsperfile = 20
        tstroot.currentfileid = 1
        self.assertEqual(fn1, sfn1)
        fn1 = mythen.postrun(
            commonblock,
            fileindex,
            filedir,
            fileprefix,
            fileindex_str)

        self.assertEqual(fn1, sfn1)

    def test_pilatus_postrun(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        from nxstools.pyeval import pilatus

        tstroot = TstRoot2()
        commonblock = {"__root__": tstroot}
        filestartnum = 20
        filedir = "/tmp/current/"
        nbframes = 20
        filepostfix = ".tif"
        fileprefix = "scan213123_"
        filestartnum_str = "pilatus2_filestartnum"
        commonblock[filestartnum_str] = 1

        sfn1 = "/tmp/current/scan213123_%05d.tif:0:19"

        fn1 = pilatus.postrun(
            commonblock, filestartnum, filedir, nbframes,
            filepostfix, fileprefix, filestartnum_str)
        self.assertEqual(fn1, sfn1)

        tstroot.stepsperfile = 20
        tstroot.currentfileid = 1
        fn1 = pilatus.postrun(
            commonblock, filestartnum, filedir, nbframes,
            filepostfix, fileprefix, filestartnum_str)
        self.assertEqual(fn1, sfn1)

    def test_pilatus_mxparameters(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        fileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "lmbd"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = '%s_00000.nxs' % (fileprefix)
        sfname1 = '%s_00000' % (fileprefix)
        ffname1 = '%s/%s' % (path, fname1)

        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass
            fl1 = self.fwriter.create_file(ffname1, overwrite=True)
            rt = fl1.root()
            entry = rt.create_group("scan_1234", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("pilatus2", "NXdetector")

            commonblock = {
                "lmbd_savefilename": [sfname1],
                "lmbd_framenumbers": [30],
                "__root__": rt,
            }
            mxparameters = "# Wavelength 1.03320 A\r\n" \
                + "# Detector_distance 0.32200 m\r\n" \
                + "# Beam_xy (1261.00, 1242.00) pixels\r\n" \
                + "# Filter_transmission 0.1000\r\n" \
                + "# Start_angle 204.9240 deg.\r\n" \
                + "# Angle_increment 0.1000 deg.\r\n# Phi 404.0470 deg.\r"

            name = "pilatus2"
            entryname = "scan_1234"

            from nxstools.pyeval import pilatus
            result = pilatus.mxparameters_cb(
                commonblock,
                mxparameters, name,
                entryname,
                insname="instrument"
            )
            self.assertEqual(mxparameters, result)

            length = det.open("wavelength")
            dist = det.open("distance")
            beamx = det.open("beam_center_x")
            beamy = det.open("beam_center_y")

            self.assertEqual(length[...][0], 1.0332)
            self.assertEqual(dist[...][0], 0.322)
            self.assertEqual(beamx[...][0], 1261.)
            self.assertEqual(beamy[...][0], 1242.)

            det.close()
            ins.close()
            entry.close()
            fl1.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)

    def test_dcm_unitcalibration(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        dcmdevice = "ttestp09/testts/t1r228"
        braggdevice = "ttestp09/testts/t2r228"
        value = 2187.3755

        try:

            tsv1 = TestServerSetUp.TestServerSetUp(
                dcmdevice, "MYTESTS1")
            tsv1.setUp()
            db = tango.Database()
            db.put_device_property(dcmdevice,
                                   {'BraggDevice': [braggdevice]})
            tsv1.dp.Init()
            tsv2 = TestServerSetUp.TestServerSetUp(
                braggdevice, "MYTESTS2")
            tsv2.setUp()

            from nxstools.pyeval import dcm
            result = dcm.unitcalibration(dcmdevice)
            self.assertEqual(value, result)

        finally:
            if tsv1:
                tsv1.tearDown()
            if tsv2:
                tsv2.tearDown()

    def test_dcm_reflection(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        dcmdevice = "ttestp09/testts/t1r228"
        version = '11'

        try:

            tsv1 = TestServerSetUp.TestServerSetUp(
                dcmdevice, "MYTESTS1")
            tsv1.setUp()
            db = tango.Database()
            db.put_device_property(dcmdevice,
                                   {'Version': [version]})
            tsv1.dp.Init()
            from nxstools.pyeval import dcm
            tsv1.dp.crystal = 1
            result = dcm.reflection(dcmdevice)
            self.assertEqual([2, 2, 0], result)
            tsv1.dp.crystal = 2
            result = dcm.reflection(dcmdevice)
            self.assertEqual([1, 1, 1], result)

            version = "8"
            db.put_device_property(dcmdevice,
                                   {'Version': [version]})
            tsv1.dp.Init()
            from nxstools.pyeval import dcm
            tsv1.dp.Crystal = 1
            result = dcm.reflection(dcmdevice)
            self.assertEqual([3, 1, 1], result)
            tsv1.dp.Crystal = 2
            result = dcm.reflection(dcmdevice)
            self.assertEqual([1, 1, 1], result)

        finally:
            if tsv1:
                tsv1.tearDown()

    def test_dcm_crystal(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        dcmdevice = "ttestp09/testts/t1r228"

        try:

            tsv1 = TestServerSetUp.TestServerSetUp(
                dcmdevice, "MYTESTS1")
            tsv1.setUp()

            from nxstools.pyeval import dcm
            value = 1
            tsv1.dp.crystal = value
            result = dcm.crystal(dcmdevice)
            self.assertEqual(value, result)
            value = 2
            tsv1.dp.crystal = value
            result = dcm.crystal(dcmdevice)
            self.assertEqual(value, result)

        finally:
            if tsv1:
                tsv1.tearDown()

    def test_limaccd_postrun(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        from nxstools.pyeval import limaccd

        tstroot = TstRoot2()
        commonblock = {"__root__": tstroot}

        filestartnum_str = "andor_saving_next_number"
        commonblock[filestartnum_str] = 1

        saving_next_number = 20
        saving_directory = "/tmp/current/"
        saving_suffix = ".tif"
        acq_nb_frames = 20
        saving_format = "_%05d"
        saving_prefix = "scan213123"

        sfn1 = "/tmp/current/scan213123_%05d.tif:0:19"

        fn1 = limaccd.postrun(
            commonblock,
            saving_next_number, saving_directory, saving_suffix,
            acq_nb_frames, saving_format, saving_prefix,
            "andor_saving_next_number")
        self.assertEqual(fn1, sfn1)

        tstroot.stepsperfile = 20
        tstroot.currentfileid = 1
        fn1 = limaccd.postrun(
            commonblock,
            saving_next_number, saving_directory, saving_suffix,
            acq_nb_frames, saving_format, saving_prefix,
            "andor_saving_next_number")
        self.assertEqual(fn1, sfn1)

    def test_pe_fileindex_cb(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        from nxstools.pyeval import pe
        commonblock = {}

        sfn1 = 4

        fn1 = pe.fileindex_cb(
            commonblock, "pe_fileindex", sfn1)
        self.assertEqual(fn1, sfn1 - 1)
        self.assertEqual(len(commonblock), 1)
        self.assertTrue("pe_fileindex" in commonblock)
        self.assertEqual(commonblock["pe_fileindex"],  sfn1)

    def test_pe_postrun(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        from nxstools.pyeval import pe

        tstroot = TstRoot2()
        commonblock = {"__root__": tstroot}

        fileindex_str = "pe_fileindex"
        commonblock[fileindex_str] = 1

        fileindex = 20
        outputdirectory = "/tmp/current/"
        filepattern = "scan213123"
        filename = ".tif"

        sfn1 = "/tmp/current/scan213123-%05d.tif:0:19"

        fn1 = pe.postrun(
            commonblock,
            outputdirectory,
            filepattern,
            filename,
            fileindex,
            "pe_fileindex")

        self.assertEqual(fn1, sfn1)

        tstroot.stepsperfile = 20
        tstroot.currentfileid = 1
        fn1 = pe.postrun(
            commonblock,
            outputdirectory,
            filepattern,
            filename,
            fileindex,
            "pe_fileindex")
        self.assertEqual(fn1, sfn1)

    def test_tangovimba(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tstroot = TstRoot2()
        commonblock = {"__root__": tstroot}
        name = "vimba"
        fileprefix = "scan213123"
        filepostfix = "nx"
        filestartnum = 2
        filename = "/tmp/scans/mytest_324234.nxs"

        sfn1 = "mytest_324234/vimba/scan213123_000002.nx:" \
            "//entry/instrument/detector"
        from nxstools.pyeval import tangovimba
        fn1 = tangovimba.external_data(
            commonblock,
            name,
            fileprefix,
            filepostfix,
            filestartnum,
            filename)
        self.assertEqual(fn1, sfn1)

    def test_dalsa(self):
        """ test
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tstroot = TstRoot2()
        commonblock = {"__root__": tstroot}
        name = "dalsa"
        fileprefix = "scan213123"
        filepostfix = "nx"
        filestartnum = 2
        filename = "/tmp/scans/mytest_324234.nxs"

        sfn1 = "mytest_324234/dalsa/scan213123_000001.nx:" \
            "//entry/instrument/detector"
        from nxstools.pyeval import dalsa
        fn1 = dalsa.external_data(
            commonblock,
            name,
            fileprefix,
            filepostfix,
            filestartnum,
            filename)
        self.assertEqual(fn1, sfn1)

    def test_xspress_triggermode_splitmode(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "vortex"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        filedir = os.path.abspath(path)
        self._fname = filename
        fileprefix = "testscan_data"
        framesperfile = 14
        maskdatatowrite = 10
        savedata = True
        fname1 = ['%s_%05i.nxs' % (fileprefix, i) for i in range(3)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]
        framenumbers = [14, 14, 2]
        devicename = "ttestp09/testts/t1r228"

        vl = [[self._rnd.randint(1, 1600) for _ in range(128)]
              for _ in range(30)]
        vl2 = [[self._rnd.randint(1, 1600) for _ in range(128)]
               for _ in range(30)]
        db = tango.Database()
        try:
            tsv1 = TestServerSetUp.TestServerSetUp(
                devicename, "MYTESTS1")
            tsv1.setUp()
            db.put_device_property(devicename,
                                   {'NbChannels': ['4']})
            tsv1.dp.init()
            try:
                os.makedirs(path)
            except FileExistsError:
                pass

            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("xspress3", "NXdetector")
                chn = det.create_group("channel00")
                intimage = chn.create_field(
                    "histogram", "int32",
                    [framenumbers[i], 128], [1, 128])
                vv = [[vl[i * framenumbers[0] + nn][ii]
                       for ii in range(128)]
                      for nn in range(framenumbers[i])]
                intimage[:, :] = vv
                intimage.close()
                chn = det.create_group("channel02")
                intimage = chn.create_field(
                    "histogram", "int32",
                    [framenumbers[i], 128], [1, 128])
                vv = [[vl2[i * framenumbers[0] + nn][ii]
                       for ii in range(128)]
                      for nn in range(framenumbers[i])]
                intimage[:, :] = vv
                intimage.close()
                det.close()
                ins.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")
            dt = entry.create_group("data", "NXdata")

            commonblock = {
                "__root__": rt,
            }
            triggermode = 0
            name = "vortex"
            nbframes = 30
            mcalength = 128
            hostname = os.environ.get("TANGO_HOST", "localhost:10000")

            device = devicename
            insname = "instrument"

            from nxstools.pyeval import xspress3
            result = xspress3.triggermode_cb(
                commonblock,
                name,
                triggermode,
                nbframes,
                hostname,
                device,
                filename,
                entryname,
                insname,
                filedir,
                fileprefix,
                framesperfile,
                maskdatatowrite,
                mcalength,
                savedata)
            fl.flush()
            self.assertEqual(result, 0)
            inames = ins.names()
            self.assertEqual(
                ['vortex', 'vortex_channel00', 'vortex_channel02'],
                inames)
            colc0 = ins.open("vortex_channel00").open("collection")
            colc2 = ins.open("vortex_channel02").open("collection")
            # print("NAMES", inames)
            for i in range(3):
                spectra = colc0.open("data_%05i" % (i))
                dspectra = dt.open("vortex_channel00_%05i" % (i))
                rw = spectra.read()
                drw = dspectra.read()
                for j in range(framenumbers[i]):
                    self.myAssertList(rw[j], vl[j + framenumbers[0] * i])
                    self.myAssertList(drw[j], vl[j + framenumbers[0] * i])
                # print(colc2.names())
                spectra = colc2.open("data_%05i" % (i))
                dspectra = dt.open("vortex_channel02_%05i" % (i))
                rw = spectra.read()
                drw = dspectra.read()
                for j in range(framenumbers[i]):
                    self.myAssertList(rw[j], vl2[j + framenumbers[0] * i])
                    self.myAssertList(drw[j], vl2[j + framenumbers[0] * i])
            intimage.close()
            dt.close()
            entry.close()
            fl.close()
        finally:
            if tsv1:
                tsv1.tearDown()
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_xspress_triggermode_splitmode_vds(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "vortex"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s" % (name)
        path = "%s" % (name)
        filedir = os.path.abspath(path)
        self._fname = filename
        fileprefix = "testscan_data"
        framesperfile = 14
        maskdatatowrite = 6
        savedata = True
        fname1 = ['%s_%05i.nxs' % (fileprefix, i) for i in range(3)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]
        framenumbers = [14, 14, 2]
        devicename = "ttestp09/testts/t1r228"

        vl = [[self._rnd.randint(1, 1600) for _ in range(128)]
              for _ in range(30)]
        vl2 = [[self._rnd.randint(1, 1600) for _ in range(128)]
               for _ in range(30)]
        db = tango.Database()
        try:
            tsv1 = TestServerSetUp.TestServerSetUp(
                devicename, "MYTESTS1")
            tsv1.setUp()
            db.put_device_property(devicename,
                                   {'NbChannels': ['4']})
            tsv1.dp.init()
            try:
                os.makedirs(path)
            except FileExistsError:
                pass

            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("xspress3", "NXdetector")
                chn = det.create_group("channel00")
                intimage = chn.create_field(
                    "histogram", "int32",
                    [framenumbers[i], 128], [1, 128])
                vv = [[vl[i * framenumbers[0] + nn][ii]
                       for ii in range(128)]
                      for nn in range(framenumbers[i])]
                intimage[:, :] = vv
                intimage.close()
                chn = det.create_group("channel03")
                intimage = chn.create_field(
                    "histogram", "int32",
                    [framenumbers[i], 128], [1, 128])
                vv = [[vl2[i * framenumbers[0] + nn][ii]
                       for ii in range(128)]
                      for nn in range(framenumbers[i])]
                intimage[:, :] = vv
                intimage.close()
                det.close()
                ins.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")
            dt = entry.create_group("data", "NXdata")

            commonblock = {
                "__root__": rt,
            }
            triggermode = 0
            name = "vortex"
            nbframes = 30
            mcalength = 128
            hostname = os.environ.get("TANGO_HOST", "localhost:10000")
            aqmode = 'VDS'

            device = devicename
            insname = "instrument"

            from nxstools.pyeval import xspress3
            result = xspress3.triggermode_cb(
                commonblock,
                name,
                triggermode,
                nbframes,
                hostname,
                device,
                filename,
                entryname,
                insname,
                filedir,
                fileprefix,
                framesperfile,
                maskdatatowrite,
                mcalength,
                savedata, aqmode
            )
            fl.flush()
            self.assertEqual(result, 0)
            inames = ins.names()
            self.assertEqual(
                ['vortex', 'vortex_channel00', 'vortex_channel03'],
                inames)
            detc0 = ins.open("vortex_channel00")
            detc3 = ins.open("vortex_channel03")
            colc0 = detc0.open("collection")
            colc3 = detc3.open("collection")
            # print("NAMES", inames)
            for i in range(3):
                spectra = colc0.open("data_%05i" % (i))
                dspectra = dt.open("vortex_channel00_%05i" % (i))
                rw = spectra.read()
                drw = dspectra.read()
                for j in range(framenumbers[i]):
                    self.myAssertList(rw[j], vl[j + framenumbers[0] * i])
                    self.myAssertList(drw[j], vl[j + framenumbers[0] * i])
                # print(colc3.names())
                spectra = colc3.open("data_%05i" % (i))
                dspectra = dt.open("vortex_channel03_%05i" % (i))
                rw = spectra.read()
                drw = dspectra.read()
                for j in range(framenumbers[i]):
                    self.myAssertList(rw[j], vl2[j + framenumbers[0] * i])
                    self.myAssertList(drw[j], vl2[j + framenumbers[0] * i])

            spectra = detc0.open("data")
            dspectra = dt.open("vortex_channel00")
            rw = spectra.read()
            drw = dspectra.read()
            for j in range(nbframes):
                self.myAssertList(rw[j], vl[j])
                self.myAssertList(drw[j], vl[j])
            # print(colc3.names())
            spectra = detc3.open("data")
            dspectra = dt.open("vortex_channel03")
            rw = spectra.read()
            drw = dspectra.read()
            for j in range(nbframes):
                self.myAssertList(rw[j], vl2[j])
                self.myAssertList(drw[j], vl2[j])

            intimage.close()
            dt.close()
            entry.close()
            fl.close()
        finally:
            if tsv1:
                tsv1.tearDown()
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_xspress_triggermode_splitmode_single(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "vortex"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s" % (name)
        path = "%s" % (name)
        filedir = os.path.abspath(path)
        self._fname = filename
        fileprefix = "testscan_data"
        framesperfile = 32
        maskdatatowrite = 6
        savedata = True
        fname1 = ['%s_%05i.nxs' % (fileprefix, i) for i in range(1)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]
        framenumbers = [30]
        devicename = "ttestp09/testts/t1r228"

        vl = [[self._rnd.randint(1, 1600) for _ in range(128)]
              for _ in range(30)]
        vl2 = [[self._rnd.randint(1, 1600) for _ in range(128)]
               for _ in range(30)]
        db = tango.Database()
        try:
            tsv1 = TestServerSetUp.TestServerSetUp(
                devicename, "MYTESTS1")
            tsv1.setUp()
            db.put_device_property(devicename,
                                   {'NbChannels': ['4']})
            tsv1.dp.init()
            try:
                os.makedirs(path)
            except FileExistsError:
                pass

            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("xspress3", "NXdetector")
                chn = det.create_group("channel00")
                intimage = chn.create_field(
                    "histogram", "int32",
                    [framenumbers[i], 128], [1, 128])
                vv = [[vl[i * framenumbers[0] + nn][ii]
                       for ii in range(128)]
                      for nn in range(framenumbers[i])]
                intimage[:, :] = vv
                intimage.close()
                chn = det.create_group("channel03")
                intimage = chn.create_field(
                    "histogram", "int32",
                    [framenumbers[i], 128], [1, 128])
                vv = [[vl2[i * framenumbers[0] + nn][ii]
                       for ii in range(128)]
                      for nn in range(framenumbers[i])]
                intimage[:, :] = vv
                intimage.close()
                det.close()
                ins.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")
            dt = entry.create_group("data", "NXdata")

            commonblock = {
                "__root__": rt,
            }
            triggermode = 0
            name = "vortex"
            nbframes = 30
            mcalength = 128
            hostname = os.environ.get("TANGO_HOST", "localhost:10000")

            device = devicename
            insname = "instrument"

            from nxstools.pyeval import xspress3
            result = xspress3.triggermode_cb(
                commonblock,
                name,
                triggermode,
                nbframes,
                hostname,
                device,
                filename,
                entryname,
                insname,
                filedir,
                fileprefix,
                framesperfile,
                maskdatatowrite,
                mcalength,
                savedata
            )
            fl.flush()
            self.assertEqual(result, 0)
            inames = ins.names()
            self.assertEqual(
                ['vortex', 'vortex_channel00', 'vortex_channel03'],
                inames)
            detc0 = ins.open("vortex_channel00")
            detc3 = ins.open("vortex_channel03")
            colc0 = detc0.open("collection")
            colc3 = detc3.open("collection")
            # print("NAMES", inames)
            for i in range(1):
                spectra = colc0.open("data_%05i" % (i))
                dspectra = dt.open("vortex_channel00_%05i" % (i))
                rw = spectra.read()
                drw = dspectra.read()
                for j in range(framenumbers[i]):
                    self.myAssertList(rw[j], vl[j + framenumbers[0] * i])
                    self.myAssertList(drw[j], vl[j + framenumbers[0] * i])
                # print(colc3.names())
                spectra = colc3.open("data_%05i" % (i))
                dspectra = dt.open("vortex_channel03_%05i" % (i))
                rw = spectra.read()
                drw = dspectra.read()
                for j in range(framenumbers[i]):
                    self.myAssertList(rw[j], vl2[j + framenumbers[0] * i])
                    self.myAssertList(drw[j], vl2[j + framenumbers[0] * i])

            spectra = detc0.open("data")
            dspectra = dt.open("vortex_channel00")
            rw = spectra.read()
            drw = dspectra.read()
            for j in range(nbframes):
                self.myAssertList(rw[j], vl[j])
                self.myAssertList(drw[j], vl[j])
            # print(colc3.names())
            spectra = detc3.open("data")
            dspectra = dt.open("vortex_channel03")
            rw = spectra.read()
            drw = dspectra.read()
            for j in range(nbframes):
                self.myAssertList(rw[j], vl2[j])
                self.myAssertList(drw[j], vl2[j])

            intimage.close()
            dt.close()
            entry.close()
            fl.close()
        finally:
            if tsv1:
                tsv1.tearDown()
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_limaccdvds_postrun_splitmode(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "andor"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['testscan_data_%06i.h5' % i for i in range(1, 4)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]
        framenumbers = [14, 14, 2]

        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass

            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry_0000", "NXentry")
                dt = entry.create_group("measurement", "NXdata")
                intimage = dt.create_field(
                    "data", "uint32",
                    [framenumbers[i], 10, 20], [1, 10, 20])
                vv = [[[vl[i * framenumbers[0] + nn][jj][ii]
                        for ii in range(20)]
                       for jj in range(10)]
                      for nn in range(framenumbers[i])]
                intimage[:, :, :] = vv
                intimage.close()
                dt.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")
            dt = entry.create_group("data", "NXdata")
            col = det.create_group("collection", "NXcollection")

            commonblock = {
                "andor_saving_next_number": (2 - 30),
                "__root__": rt,
            }
            nbimages = 30

            insname = "instrument"

            saving_next_number = 4
            saving_directory = path
            saving_suffix = ".h5"
            acq_nb_frames = nbimages
            saving_index_format = "%06i"
            saving_prefix = "testscan_data_"
            saving_next_number_str = "andor_saving_next_number"
            saving_format = "HDF5"
            saving_frame_per_file = 14
            image_height = None
            image_width = None
            image_type = None
            acq_trigger_mode = "INTERNAL_TRIGGER_MULTI"
            acq_mode = 'SINGLE'
            acq_modes = ""
            field_path = "/entry_0000/measurement/data"

            from nxstools.pyeval import limaccd
            result = limaccd.postrun(
                commonblock,
                saving_next_number,
                saving_directory,
                saving_suffix,
                acq_nb_frames,
                saving_index_format,
                saving_prefix,
                saving_next_number_str,
                name,
                saving_format,
                saving_frame_per_file,
                image_height,
                image_width,
                image_type,
                acq_trigger_mode,
                acq_mode,
                filename,
                entryname,
                insname,
                acq_modes,
                field_path)
            fl.flush()
            self.assertEqual(result, "")
            for i in range(3):
                images = col.open("data_%05i" % (i + 1))
                rw = images.read()
                for j in range(framenumbers[i]):
                    self.myAssertImage(rw[j], vl[j + framenumbers[0] * i])
                images = dt.open("andor_%05i" % (i + 1))
                rw = images.read()
                for j in range(framenumbers[i]):
                    self.myAssertImage(rw[j], vl[j + framenumbers[0] * i])
            intimage.close()
            dt.close()
            entry.close()
            fl.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_limaccdvds_postrun_splitmode_vds(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345
        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        name = "andor"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['testscan_data_%06i.h5' % i for i in range(1, 4)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]
        framenumbers = [14, 14, 2]

        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass

            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry_0000", "NXentry")
                dt = entry.create_group("measurement", "NXdata")
                intimage = dt.create_field(
                    "data", "uint32",
                    [framenumbers[i], 10, 20], [1, 10, 20])
                vv = [[[vl[i * framenumbers[0] + nn][jj][ii]
                        for ii in range(20)]
                       for jj in range(10)]
                      for nn in range(framenumbers[i])]
                intimage[:, :, :] = vv
                intimage.close()
                dt.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")
            dt = entry.create_group("data", "NXdata")
            col = det.create_group("collection", "NXcollection")

            commonblock = {
                "andor_saving_next_number": (2 - 30),
                "__root__": rt,
            }
            nbimages = 30

            insname = "instrument"

            saving_next_number = 4
            saving_directory = path
            saving_suffix = ".h5"
            acq_nb_frames = nbimages
            saving_index_format = "%06i"
            saving_prefix = "testscan_data_"
            saving_next_number_str = "andor_saving_next_number"
            saving_format = "HDF5"
            saving_frame_per_file = 14
            image_height = 10
            image_width = 20
            image_type = "Bpp32"
            acq_trigger_mode = "INTERNAL_TRIGGER_MULTI"
            acq_mode = 'SINGLE'
            acq_modes = "VDS"
            field_path = "/entry_0000/measurement/data"

            from nxstools.pyeval import limaccd
            result = limaccd.postrun(
                commonblock,
                saving_next_number,
                saving_directory,
                saving_suffix,
                acq_nb_frames,
                saving_index_format,
                saving_prefix,
                saving_next_number_str,
                name,
                saving_format,
                saving_frame_per_file,
                image_height,
                image_width,
                image_type,
                acq_trigger_mode,
                acq_mode,
                filename,
                entryname,
                insname,
                acq_modes,
                field_path)
            fl.flush()
            self.assertEqual(result, "")
            detdt = det.open("data").read()
            dtandor = dt.open("andor").read()
            for j in range(sum(framenumbers)):
                self.myAssertImage(detdt[j], vl[j])
                self.myAssertImage(dtandor[j], vl[j])
            for i in range(3):
                images = col.open("data_%05i" % (i + 1))
                rw = images.read()
                for j in range(framenumbers[i]):
                    self.myAssertImage(rw[j], vl[j + framenumbers[0] * i])
                images = dt.open("andor_%05i" % (i + 1))
                rw = images.read()
                for j in range(framenumbers[i]):
                    self.myAssertImage(rw[j], vl[j + framenumbers[0] * i])
            intimage.close()
            dt.close()
            entry.close()
            fl.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_limaccdvds_postrun_splitmode_one(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "andor"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['testscan_data_%06i.h5' % i for i in range(1, 2)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]
        framenumbers = [30]

        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass

            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry_0000", "NXentry")
                dt = entry.create_group("measurement", "NXdata")
                intimage = dt.create_field(
                    "data", "uint32",
                    [framenumbers[i], 10, 20], [1, 10, 20])
                vv = [[[vl[i * framenumbers[0] + nn][jj][ii]
                        for ii in range(20)]
                       for jj in range(10)]
                      for nn in range(framenumbers[i])]
                intimage[:, :, :] = vv
                intimage.close()
                dt.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")
            dt = entry.create_group("data", "NXdata")
            col = det.create_group("collection", "NXcollection")

            commonblock = {
                "andor_saving_next_number": (2 - 30),
                "__root__": rt,
            }
            nbimages = 30

            insname = "instrument"

            saving_next_number = 2
            saving_directory = path
            saving_suffix = ".h5"
            acq_nb_frames = nbimages
            saving_index_format = "%06i"
            saving_prefix = "testscan_data_"
            saving_next_number_str = "andor_saving_next_number"
            saving_format = "HDF5"
            saving_frame_per_file = 30
            image_height = 10
            image_width = 20
            image_type = "Bpp32"
            acq_trigger_mode = "INTERNAL_TRIGGER_MULTI"
            acq_mode = 'SINGLE'
            acq_modes = ""
            field_path = "/entry_0000/measurement/data"

            from nxstools.pyeval import limaccd
            result = limaccd.postrun(
                commonblock,
                saving_next_number,
                saving_directory,
                saving_suffix,
                acq_nb_frames,
                saving_index_format,
                saving_prefix,
                saving_next_number_str,
                name,
                saving_format,
                saving_frame_per_file,
                image_height,
                image_width,
                image_type,
                acq_trigger_mode,
                acq_mode,
                filename,
                entryname,
                insname,
                acq_modes,
                field_path)
            fl.flush()
            self.assertEqual(result, "")
            detdt = det.open("data").read()
            dtandor = dt.open("andor").read()
            for j in range(sum(framenumbers)):
                self.myAssertImage(detdt[j], vl[j])
                self.myAssertImage(dtandor[j], vl[j])
            for i in range(1):
                images = col.open("data_%05i" % (i + 1))
                rw = images.read()
                for j in range(framenumbers[i]):
                    self.myAssertImage(rw[j], vl[j + framenumbers[0] * i])
                images = dt.open("andor_%05i" % (i + 1))
                rw = images.read()
                for j in range(framenumbers[i]):
                    self.myAssertImage(rw[j], vl[j + framenumbers[0] * i])
            intimage.close()
            dt.close()
            entry.close()
            fl.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_eigetdectris_triggermode_splitmode(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "eiger2"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['testscan_data_%06i.h5' % i for i in range(1, 4)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]
        framenumbers = [14, 14, 2]
        devicename = "ttestp09/testts/t1r228"

        vl = [[[self._rnd.randint(1, 1600) for _ in range(2)]
               for _ in range(1)]
              for _ in range(30)]
        try:
            tsv1 = TestServerSetUp.TestServerSetUp(
                devicename, "MYTESTS1")
            tsv1.setUp()
            try:
                os.makedirs(path)
            except FileExistsError:
                pass

            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                dt = entry.create_group("data", "NXdata")
                intimage = dt.create_field(
                    "data", "uint32",
                    [framenumbers[i], 1, 2], [1, 1, 2])
                vv = [[[vl[i * framenumbers[0] + nn][jj][ii]
                        for ii in range(2)]
                       for jj in range(1)]
                      for nn in range(framenumbers[i])]
                intimage[:, :, :] = vv
                intimage.close()
                dt.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")
            dt = entry.create_group("data", "NXdata")
            col = det.create_group("collection", "NXcollection")

            commonblock = {
                "eiger2_stepindex": [30],
                "__root__": rt,
            }
            triggermode = "splitmode"
            name = "eiger2"
            nbimages = 30
            hostname = os.environ.get("TANGO_HOST", "localhost:10000")

            device = devicename
            stepindex_str = "eiger2_stepindex"
            insname = "instrument"
            eigerdectris_str = "TestServer"
            eigerfilewriter_str = "TestServer"

            from nxstools.pyeval import eigerdectris
            result = eigerdectris.triggermode_cb(
                commonblock,
                name,
                triggermode,
                nbimages,
                hostname,
                device,
                filename,
                stepindex_str,
                entryname,
                insname,
                eigerdectris_str,
                eigerfilewriter_str)
            fl.flush()
            self.assertEqual(result, "splitmode")
            for i in range(3):
                images = col.open("data_%06i" % (i + 1))
                rw = images.read()
                for j in range(framenumbers[i]):
                    self.myAssertImage(rw[j], vl[j + framenumbers[0] * i])
                images = dt.open("eiger2_%06i" % (i + 1))
                rw = images.read()
                for j in range(framenumbers[i]):
                    self.myAssertImage(rw[j], vl[j + framenumbers[0] * i])
            intimage.close()
            dt.close()
            entry.close()
            fl.close()
        finally:
            if tsv1:
                tsv1.tearDown()
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_eigetdectris_triggermode_splitmode_vds(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "eiger2"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['testscan_data_%06i.h5' % i for i in range(1, 4)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]
        framenumbers = [14, 14, 2]
        devicename = "ttestp09/testts/t1r228"

        vl = [[[self._rnd.randint(1, 1600) for _ in range(2)]
               for _ in range(1)]
              for _ in range(30)]
        try:
            tsv1 = TestServerSetUp.TestServerSetUp(
                devicename, "MYTESTS1")
            tsv1.setUp()
            try:
                os.makedirs(path)
            except FileExistsError:
                pass

            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                dt = entry.create_group("data", "NXdata")
                intimage = dt.create_field(
                    "data", "uint32",
                    [framenumbers[i], 1, 2], [1, 1, 2])
                vv = [[[vl[i * framenumbers[0] + nn][jj][ii]
                        for ii in range(2)]
                       for jj in range(1)]
                      for nn in range(framenumbers[i])]
                intimage[:, :, :] = vv
                intimage.close()
                dt.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")
            dt = entry.create_group("data", "NXdata")
            col = det.create_group("collection", "NXcollection")

            commonblock = {
                "eiger2_stepindex": [30],
                "__root__": rt,
            }
            triggermode = "splitmode"
            name = "eiger2"
            nbimages = 30
            hostname = os.environ.get("TANGO_HOST", "localhost:10000")

            device = devicename
            stepindex_str = "eiger2_stepindex"
            insname = "instrument"
            eigerdectris_str = "TestServer"
            eigerfilewriter_str = "TestServer"

            from nxstools.pyeval import eigerdectris
            result = eigerdectris.triggermode_cb(
                commonblock,
                name,
                triggermode,
                nbimages,
                hostname,
                device,
                filename,
                stepindex_str,
                entryname,
                insname,
                eigerdectris_str,
                eigerfilewriter_str, addfilepattern=False,
                shape=[1, 2], dtype="uint32", acq_modes="VDS")
            fl.flush()
            self.assertEqual(result, "splitmode")
            detdt = det.open("data").read()
            dteiger2 = dt.open("eiger2").read()
            for j in range(sum(framenumbers)):
                self.myAssertImage(detdt[j], vl[j])
                self.myAssertImage(dteiger2[j], vl[j])
            for i in range(3):
                images = col.open("data_%06i" % (i + 1))
                rw = images.read()
                for j in range(framenumbers[i]):
                    self.myAssertImage(rw[j], vl[j + framenumbers[0] * i])
                images = dt.open("eiger2_%06i" % (i + 1))
                rw = images.read()
                for j in range(framenumbers[i]):
                    self.myAssertImage(rw[j], vl[j + framenumbers[0] * i])
            intimage.close()
            dt.close()
            entry.close()
            fl.close()
        finally:
            if tsv1:
                tsv1.tearDown()
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_eigetdectris_triggermode_splitmode_in(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "eiger2"
        filename = "%s_%s/%s_%s.nxs" % (
            mfileprefix, scanid, mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['testscan_data_%06i.h5' % i for i in range(1, 4)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]
        framenumbers = [14, 14, 2]
        devicename = "ttestp09/testts/t1r228"

        vl = [[[self._rnd.randint(1, 1600) for _ in range(2)]
               for _ in range(1)]
              for _ in range(30)]
        try:
            tsv1 = TestServerSetUp.TestServerSetUp(
                devicename, "MYTESTS1")
            tsv1.setUp()
            try:
                os.makedirs(path)
            except FileExistsError:
                pass

            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                dt = entry.create_group("data", "NXdata")
                intimage = dt.create_field(
                    "data", "uint32",
                    [framenumbers[i], 1, 2], [1, 1, 2])
                vv = [[[vl[i * framenumbers[0] + nn][jj][ii]
                        for ii in range(2)]
                       for jj in range(1)]
                      for nn in range(framenumbers[i])]
                intimage[:, :, :] = vv
                intimage.close()
                dt.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")
            dt = entry.create_group("data", "NXdata")
            col = det.create_group("collection", "NXcollection")

            commonblock = {
                "eiger2_stepindex": [30],
                "__root__": rt,
            }
            triggermode = "splitmode"
            name = "eiger2"
            nbimages = 30
            hostname = os.environ.get("TANGO_HOST", "localhost:10000")

            device = devicename
            stepindex_str = "eiger2_stepindex"
            insname = "instrument"
            eigerdectris_str = "TestServer"
            eigerfilewriter_str = "TestServer"

            from nxstools.pyeval import eigerdectris
            result = eigerdectris.triggermode_cb(
                commonblock,
                name,
                triggermode,
                nbimages,
                hostname,
                device,
                filename,
                stepindex_str,
                entryname,
                insname,
                eigerdectris_str,
                eigerfilewriter_str)
            fl.flush()
            self.assertEqual(result, "splitmode")
            for i in range(3):
                images = col.open("data_%06i" % (i + 1))
                rw = images.read()
                for j in range(framenumbers[i]):
                    self.myAssertImage(rw[j], vl[j + framenumbers[0] * i])
                images = dt.open("eiger2_%06i" % (i + 1))
                rw = images.read()
                for j in range(framenumbers[i]):
                    self.myAssertImage(rw[j], vl[j + framenumbers[0] * i])
            intimage.close()
            dt.close()
            entry.close()
            fl.close()
        finally:
            if tsv1:
                tsv1.tearDown()
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)

    def test_lambdavdsnm_triggermode_cb(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        fileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "lmbd"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['%s_00000_m%02d.nxs' % (fileprefix, i) for i in range(1, 4)]
        sfname1 = '%s_00000' % fileprefix
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]
        framenumbers = [10, 10, 10]

        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass

            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("detector", "NXdetector")
                intimage = det.create_field(
                    "data", "uint32",
                    [framenumbers[i], 10, 20], [1, 10, 20])
                vv = [[[vl[i * framenumbers[0] + nn][jj][ii]
                        for ii in range(20)]
                       for jj in range(10)]
                      for nn in range(framenumbers[i])]
                intimage[:, :, :] = vv
                intimage.close()
                det.close()
                ins.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")

            commonblock = {
                "__root__": rt,
            }
            triggermode = 0
            translations = '{"m01":[0,0,0], "m02":[0,12,0], "m03":[0,24,0]}'
            saveallimages = True
            height = 10
            width = 20
            opmode = 24
            filepostfix = "nxs"
            framenumbers = 10
            savefilename = sfname1

            from nxstools.pyeval import lambdavds
            result = lambdavds.nm_triggermode_cb(
                commonblock,
                "lmbd",
                triggermode,
                translations,
                saveallimages,
                filepostfix,
                framenumbers,
                height,
                width,
                opmode,
                savefilename,
                filename,
                entryname,
                "instrument")
            self.assertEqual(triggermode, result)

            images = det.open("data")
            fl.flush()
            rw = images.read()
            # print(rw)
            for i in range(10):
                self.myAssertImage(rw[i, 0:10, 0:20], vl[i])
            for i in range(10):
                self.myAssertImage(rw[i, 12:22, 0:20], vl[i + 10])
            for i in range(10):
                self.myAssertImage(rw[i, 24:34, 0:20], vl[i + 20])
            intimage.close()
            det.close()
            ins.close()
            entry.close()
            fl.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_dalsavds_triggermode_nosave(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        commonblock = {}
        name = "dalsa"
        triggermode = 0
        filepostfix = "nxs"

        fileprefix = "scan213123"
        filepostfix = "nx"
        filestartnum = 2
        filedir = "/tmp/scans/"
        filename = "mytest_324234.nxs"
        entryname = "entry123"
        insname = "instrument"

        filesaving = False
        triggermode = "splitmode"
        framespernxfile = 43
        pixelformat = "Mono8"
        height = 2344
        width = 2143
        acquisitionmode = "SingleFrame"
        acquisitionframecount = 43

        from nxstools.pyeval import dalsavds
        result = dalsavds.triggermode(
            commonblock,
            name,
            filedir,
            fileprefix,
            filepostfix,
            filestartnum,
            filesaving,
            triggermode,
            framespernxfile,
            pixelformat,
            height,
            width,
            acquisitionmode,
            acquisitionframecount,
            "dalsa_filestartnum",
            "dalsa_nrexposedframes",
            filename,
            entryname,
            insname)
        self.assertEqual(triggermode, result)

    def test_dalsavds_triggermode_singleframe(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        filepostfix = "nx"
        filestartnum = 0
        filedir = "/tmp/scans/"

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        fileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "dalsa"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['%s_%05d.nx' % (fileprefix, i)
                  for i in range(filestartnum, 30 + filestartnum)]
        # sfname1 = ['%s_%05d' % (fileprefix, i)
        #            for i in range(filestartnum, 30 + filestartnum)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]

        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass
            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("detector", "NXdetector")
                intimage = det.create_field(
                    "data", "uint16", [1, 10, 20], [1, 10, 20])
                vv = [[[vl[i][jj][ii] for ii in range(20)]
                       for jj in range(10)]]
                intimage[0, :, :] = vv
                intimage.close()
                det.close()
                ins.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")

            commonblock = {
                "dalsa_filestartnum": list(range(1, 31)),
                "dalsa_nrexposedframes": list(range(1, 31)),
                "__root__": rt,
            }
            name = "dalsa"
            insname = "instrument"

            filesaving = True
            triggermode = "ExtTrigger"
            framespernxfile = 40
            pixelformat = "Mono16"
            height = 10
            width = 20
            acquisitionmode = "SingleFrame"
            acquisitionframecount = 30

            from nxstools.pyeval import dalsavds
            result = dalsavds.triggermode(
                commonblock,
                name,
                filedir,
                fileprefix,
                filepostfix,
                filestartnum,
                filesaving,
                triggermode,
                framespernxfile,
                pixelformat,
                height,
                width,
                acquisitionmode,
                acquisitionframecount,
                "dalsa_filestartnum",
                "dalsa_nrexposedframes",
                filename,
                entryname,
                insname)
            self.assertEqual(triggermode, result)

            images = det.open("data")
            rw = images.read()
            for i in range(30):
                self.myAssertImage(rw[i], vl[i])
            intimage.close()
            det.close()
            ins.close()
            entry.close()
            fl.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_dalsavds_triggermode_multiframe(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        filepostfix = "nx"
        filestartnum = 0
        filedir = "/tmp/scans/"

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        fileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "dalsa"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['%s_%05d.nx' % (fileprefix, i)
                  for i in range(3)]
        # sfname1 = ['%s_%05d' % (fileprefix, i)
        #            for i in range(filestartnum, 30 + filestartnum)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]

        framenumbers = [10, 10, 10]
        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass
            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("detector", "NXdetector")
                intimage = det.create_field(
                    "data", "uint16",
                    [framenumbers[i], 10, 20], [framenumbers[i], 10, 20])
                vv = [[[vl[i * framenumbers[0] + nn][jj][ii]
                        for ii in range(20)]
                       for jj in range(10)]
                      for nn in range(framenumbers[i])]
                intimage[:, :, :] = vv
                intimage.close()
                det.close()
                ins.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")

            commonblock = {
                "dalsa_filestartnum": [1, 2, 3],
                "dalsa_nrexposedframes": [10, 10, 10],
                "__root__": rt,
            }
            name = "dalsa"
            insname = "instrument"

            filesaving = True
            triggermode = "ExtTrigger"
            framespernxfile = 40
            pixelformat = "Mono16"
            height = 10
            width = 20
            acquisitionmode = "MultiFrame"
            acquisitionframecount = 10

            from nxstools.pyeval import dalsavds
            result = dalsavds.triggermode(
                commonblock,
                name,
                filedir,
                fileprefix,
                filepostfix,
                filestartnum,
                filesaving,
                triggermode,
                framespernxfile,
                pixelformat,
                height,
                width,
                acquisitionmode,
                acquisitionframecount,
                "dalsa_filestartnum",
                "dalsa_nrexposedframes",
                filename,
                entryname,
                insname)
            self.assertEqual(triggermode, result)

            images = det.open("data")
            rw = images.read()
            for i in range(30):
                self.myAssertImage(rw[i], vl[i])
            intimage.close()
            det.close()
            ins.close()
            entry.close()
            fl.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_dalsavds_triggermode_multiframe_split(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        filepostfix = "nx"
        filestartnum = 0
        filedir = "/tmp/scans/"

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        fileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "dalsa"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['%s_%05d.nx' % (fileprefix, i)
                  for i in range(4)]
        # sfname1 = ['%s_%05d' % (fileprefix, i)
        #            for i in range(filestartnum, 30 + filestartnum)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]

        framenumbers = [10, 5, 10, 5]
        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass
            index = 0
            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("detector", "NXdetector")
                intimage = det.create_field(
                    "data", "uint16",
                    [framenumbers[i], 10, 20], [framenumbers[i], 10, 20])
                vv = [[[vl[index + nn][jj][ii]
                        for ii in range(20)]
                       for jj in range(10)]
                      for nn in range(framenumbers[i])]
                index += framenumbers[i]
                intimage[:, :, :] = vv
                intimage.close()
                det.close()
                ins.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")

            commonblock = {
                "dalsa_filestartnum": [2, 4],
                "dalsa_nrexposedframes": [15, 15],
                "__root__": rt,
            }
            name = "dalsa"
            insname = "instrument"

            filesaving = True
            triggermode = "ExtTrigger"
            framespernxfile = 10
            pixelformat = "Mono16"
            height = 10
            width = 20
            acquisitionmode = "MultiFrame"
            acquisitionframecount = 15

            from nxstools.pyeval import dalsavds
            result = dalsavds.triggermode(
                commonblock,
                name,
                filedir,
                fileprefix,
                filepostfix,
                filestartnum,
                filesaving,
                triggermode,
                framespernxfile,
                pixelformat,
                height,
                width,
                acquisitionmode,
                acquisitionframecount,
                "dalsa_filestartnum",
                "dalsa_nrexposedframes",
                filename,
                entryname,
                insname)
            self.assertEqual(triggermode, result)

            images = det.open("data")
            rw = images.read()
            for i in range(30):
                self.myAssertImage(rw[i], vl[i])
            intimage.close()
            det.close()
            ins.close()
            entry.close()
            fl.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_dalsavds_triggermode_continuous(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        filepostfix = "nx"
        filestartnum = 0
        filedir = "/tmp/scans/"

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        fileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "dalsa"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['%s_%05d.nx' % (fileprefix, i)
                  for i in range(1)]
        # sfname1 = ['%s_%05d' % (fileprefix, i)
        #            for i in range(filestartnum, 30 + filestartnum)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]

        framenumbers = [30]
        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass
            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("detector", "NXdetector")
                intimage = det.create_field(
                    "data", "uint16",
                    [framenumbers[i], 10, 20], [framenumbers[i], 10, 20])
                vv = [[[vl[i * framenumbers[0] + nn][jj][ii]
                        for ii in range(20)]
                       for jj in range(10)]
                      for nn in range(framenumbers[i])]
                intimage[:, :, :] = vv
                intimage.close()
                det.close()
                ins.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")

            commonblock = {
                "dalsa_filestartnum": [1],
                "dalsa_nrexposedframes": [30],
                "__root__": rt,
            }
            name = "dalsa"
            insname = "instrument"

            filesaving = True
            triggermode = "ExtTrigger"
            framespernxfile = 40
            pixelformat = "Mono16"
            height = 10
            width = 20
            acquisitionmode = "Continuous"
            acquisitionframecount = 0

            from nxstools.pyeval import dalsavds
            result = dalsavds.triggermode(
                commonblock,
                name,
                filedir,
                fileprefix,
                filepostfix,
                filestartnum,
                filesaving,
                triggermode,
                framespernxfile,
                pixelformat,
                height,
                width,
                acquisitionmode,
                acquisitionframecount,
                "dalsa_filestartnum",
                "dalsa_nrexposedframes",
                filename,
                entryname,
                insname)
            self.assertEqual(triggermode, result)

            images = det.open("data")
            rw = images.read()
            for i in range(30):
                self.myAssertImage(rw[i], vl[i])
            intimage.close()
            det.close()
            ins.close()
            entry.close()
            fl.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_dalsavds_triggermode_continuous_split(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not self.fwriter.is_vds_supported():
            print("Skip the test: VDS not supported")
            return

        filepostfix = "nx"
        filestartnum = 0
        filedir = "/tmp/scans/"

        mfileprefix = "%s%s" % (self.__class__.__name__, fun)
        fileprefix = "%s%s" % (self.__class__.__name__, fun)
        scanid = 12345

        name = "dalsa"
        filename = "%s_%s.nxs" % (mfileprefix, scanid)
        mainpath = "%s_%s" % (mfileprefix, scanid)
        path = "%s_%s/%s" % (mfileprefix, scanid, name)
        self._fname = filename
        fname1 = ['%s_%05d.nx' % (fileprefix, i)
                  for i in range(3)]
        # sfname1 = ['%s_%05d' % (fileprefix, i)
        #            for i in range(filestartnum, 30 + filestartnum)]
        ffname1 = ['%s/%s' % (path, fn) for fn in fname1]

        framenumbers = [14, 14, 2]
        vl = [[[self._rnd.randint(1, 1600) for _ in range(20)]
               for _ in range(10)]
              for _ in range(30)]
        try:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass
            for i, fn in enumerate(ffname1):
                fl1 = self.fwriter.create_file(fn, overwrite=True)
                rt = fl1.root()
                entry = rt.create_group("entry", "NXentry")
                ins = entry.create_group("instrument", "NXinstrument")
                det = ins.create_group("detector", "NXdetector")
                intimage = det.create_field(
                    "data", "uint16",
                    [framenumbers[i], 10, 20], [framenumbers[i], 10, 20])
                vv = [[[vl[i * framenumbers[0] + nn][jj][ii]
                        for ii in range(20)]
                       for jj in range(10)]
                      for nn in range(framenumbers[i])]
                intimage[:, :, :] = vv
                intimage.close()
                det.close()
                ins.close()
                entry.close()
                fl1.close()

            entryname = "entry123"
            fl = self.fwriter.create_file(self._fname, overwrite=True)
            rt = fl.root()
            entry = rt.create_group(entryname, "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group(name, "NXdetector")

            commonblock = {
                "dalsa_filestartnum": [3],
                "dalsa_nrexposedframes": [30],
                "__root__": rt,
            }
            name = "dalsa"
            insname = "instrument"

            filesaving = True
            triggermode = "ExtTrigger"
            framespernxfile = 14
            pixelformat = "Mono16"
            height = 10
            width = 20
            acquisitionmode = "Continuous"
            acquisitionframecount = 0

            from nxstools.pyeval import dalsavds
            result = dalsavds.triggermode(
                commonblock,
                name,
                filedir,
                fileprefix,
                filepostfix,
                filestartnum,
                filesaving,
                triggermode,
                framespernxfile,
                pixelformat,
                height,
                width,
                acquisitionmode,
                acquisitionframecount,
                "dalsa_filestartnum",
                "dalsa_nrexposedframes",
                filename,
                entryname,
                insname)
            self.assertEqual(triggermode, result)

            images = det.open("data")
            rw = images.read()
            for i in range(30):
                self.myAssertImage(rw[i], vl[i])
            intimage.close()
            det.close()
            ins.close()
            entry.close()
            fl.close()
        finally:
            shutil.rmtree(mainpath,
                          ignore_errors=False, onerror=None)
            os.remove(self._fname)

    def test_scingestor_append_scicat_dataset_novar(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        macro = TstMacro()
        macro.env["ScanFile"] = "mytest.nxs"
        macro.env["ScanDir"] = "/gpfs/current/raw"
        macro.env["ScanID"] = 123
        result = scdataset.append_scicat_dataset(macro)
        self.assertEqual("", result)
        self.assertEqual(macro.log, [])

    def test_scingestor_append_scicat_dataset_error(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        try:
            macro = TstMacro()
            macro.env["AppendSciCatDataset"] = True
            scdataset.append_scicat_dataset(macro)
        except Exception:
            error = True
        self.assertTrue(error)

    def test_scingestor_append_scicat_dataset_scanvar(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        macro = TstMacro()
        cwd = os.getcwd()
        macro.env["ScanFile"] = "mytest.nxs"
        macro.env["ScanDir"] = cwd
        macro.env["ScanID"] = 123
        macro.env["AppendSciCatDataset"] = True
        try:
            result = scdataset.append_scicat_dataset(macro)
            self.assertEqual("mytest_00123", result)
            self.assertEqual(macro.log,
                             ["Appending 'mytest_00123' to "
                              "%s/scicat-datasets-00000000.lst" % cwd])
        finally:
            if os.path.isfile("%s/scicat-datasets-00000000.lst" % (cwd)):
                os.remove("%s/scicat-datasets-00000000.lst" % (cwd))

    def test_scingestor_append_scicat_dataset_agroup_new(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        macro = TstMacro()
        cwd = os.getcwd()
        macro.env["ScanFile"] = "mytest.nxs"
        macro.env["ScanDir"] = cwd
        macro.env["ScanID"] = 123
        macro.env["AppendSciCatDataset"] = True
        macro.env["SciCatAutoGrouping"] = True

        try:
            result = scdataset.append_scicat_dataset(macro)
            sres = result.split("\n")
            self.assertEqual("__command__ start mytest", sres[0])
            self.assertEqual("mytest_00123", sres[1])
            self.assertEqual("__command__ stop", sres[2])
            self.assertTrue(sres[3].startswith("mytest:"))
            # self.assertEqual("__command__ start mytest", sres[4])
            sres = macro.log[0].split("\n")
            self.assertEqual("Appending '__command__ start mytest", sres[0])
            self.assertEqual("mytest_00123", sres[1])
            self.assertEqual("__command__ stop", sres[2])
            self.assertTrue(sres[3].startswith("mytest:"))
            # self.assertEqual("__command__ start mytest' to "
            #                  "%s/scicat-datasets-00000000.lst"
            #                  % cwd, sres[4])
        finally:
            if os.path.isfile("%s/scicat-datasets-00000000.lst" % (cwd)):
                os.remove("%s/scicat-datasets-00000000.lst" % (cwd))

    def test_scingestor_append_scicat_dataset_agroup_old(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        macro = TstMacro()
        cwd = os.getcwd()
        macro.env["ScanFile"] = "mytest.nxs"
        macro.env["ScanDir"] = cwd
        macro.env["ScanID"] = 123
        macro.env["AppendSciCatDataset"] = True
        macro.env["SciCatAutoGrouping"] = True
        macro.env["SciCatMeasurements"] = {cwd: "oldtest"}

        try:
            result = scdataset.append_scicat_dataset(macro)
            sres = result.split("\n")
            self.assertEqual("__command__ stop", sres[0])
            self.assertTrue(sres[1].startswith("oldtest:"))
            self.assertEqual("__command__ start mytest", sres[2])
            self.assertEqual("mytest_00123", sres[3])
            self.assertEqual("__command__ stop", sres[4])
            self.assertTrue(sres[5].startswith("mytest:"))
            # self.assertEqual("__command__ start mytest", sres[6])
            sres = macro.log[0].split("\n")
            self.assertEqual("Appending '__command__ stop", sres[0])
            self.assertTrue(sres[1].startswith("oldtest:"))
            self.assertEqual("__command__ start mytest", sres[2])
            self.assertEqual("mytest_00123", sres[3])
            self.assertEqual("__command__ stop", sres[4])
            self.assertTrue(sres[5].startswith("mytest:"))
            # self.assertEqual("__command__ start mytest' to "
            #                  "%s/scicat-datasets-00000000.lst"
            #                  % cwd, sres[6])
        finally:
            if os.path.isfile("%s/scicat-datasets-00000000.lst" % (cwd)):
                os.remove("%s/scicat-datasets-00000000.lst" % (cwd))

    def test_scingestor_append_scicat_dataset_agroup_update(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        macro = TstMacro()
        cwd = os.getcwd()
        macro.env["ScanFile"] = "mytest.nxs"
        macro.env["ScanDir"] = cwd
        macro.env["ScanID"] = 123
        macro.env["AppendSciCatDataset"] = True
        macro.env["SciCatAutoGrouping"] = True
        macro.env["SciCatMeasurements"] = {cwd: "mytest"}

        try:
            result = scdataset.append_scicat_dataset(macro)
            sres = result.split("\n")
            self.assertEqual("mytest_00123", sres[0])
            self.assertEqual("__command__ stop", sres[1])
            self.assertTrue(sres[2].startswith("mytest:"))
            # self.assertEqual("__command__ start mytest", sres[3])
            sres = macro.log[0].split("\n")
            self.assertEqual("Appending 'mytest_00123", sres[0])
            self.assertEqual("__command__ stop", sres[1])
            self.assertTrue(sres[2].startswith("mytest:"))
            # self.assertEqual("__command__ start mytest' to "
            #                  "%s/scicat-datasets-00000000.lst"
            #                  % cwd, sres[3])

        finally:
            if os.path.isfile("%s/scicat-datasets-00000000.lst" % (cwd)):
                os.remove("%s/scicat-datasets-00000000.lst" % (cwd))

    def test_scingestor_append_scicat_dataset_nxsappend(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        macro = TstMacro()
        cwd = os.getcwd()
        macro.env["ScanFile"] = "mytest.nxs"
        macro.env["ScanDir"] = cwd
        macro.env["ScanID"] = 123
        macro.env["AppendSciCatDataset"] = True
        macro.env["NXSAppendSciCatDataset"] = True
        result = scdataset.append_scicat_dataset(macro)
        self.assertEqual("", result)
        self.assertEqual(macro.log, [])

    def test_scingestor_append_scicat_dataset_beamtime(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        macro = TstMacro()
        cwd = os.getcwd()
        macro.env["ScanFile"] = "mytest.nxs"
        macro.env["ScanDir"] = cwd
        macro.env["ScanID"] = 123
        macro.env["AppendSciCatDataset"] = True
        macro.env["NXSAppendSciCatDataset"] = False
        macro.env["BeamtimeFilePath"] = cwd
        # macro.env["BeamtimeFilePrefix"] =
        # macro.env["BeamtimeFileExt"] =
        # macro.env["SciCatDatasetListFileLocal"] =
        # macro.env["SciCatDatasetListFilePrefix"] =
        # macro.env["SciCatDatasetListFileExt"] =

        currentprefix = "beamtime-metadata-"
        currentpostfix = ".json"
        beamtime = "2342342"

        bfn = "%s/%s%s%s" % (cwd, currentprefix, beamtime, currentpostfix)

        try:
            open(bfn, 'a').close()

            result = scdataset.append_scicat_dataset(macro)
            self.assertEqual("mytest_00123", result)
            self.assertEqual(macro.log,
                             ["Appending 'mytest_00123' to "
                              "%s/scicat-datasets-%s.lst" % (cwd, beamtime)])
        finally:
            os.remove(bfn)
            if os.path.isfile("%s/scicat-datasets-%s.lst" % (cwd, beamtime)):
                os.remove("%s/scicat-datasets-%s.lst" % (cwd, beamtime))

    def test_scingestor_append_scicat_dataset_local(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        macro = TstMacro()
        cwd = os.getcwd()
        macro.env["ScanFile"] = "mytest.nxs"
        macro.env["ScanDir"] = cwd
        macro.env["ScanID"] = 12
        macro.env["AppendSciCatDataset"] = True
        macro.env["NXSAppendSciCatDataset"] = False
        macro.env["BeamtimeFilePath"] = cwd
        macro.env["SciCatDatasetListFileLocal"] = True
        hostname = socket.gethostname()
        # macro.env["BeamtimeFilePrefix"] =
        # macro.env["BeamtimeFileExt"] =
        # macro.env["SciCatDatasetListFilePrefix"] =
        # macro.env["SciCatDatasetListFileExt"] =

        currentprefix = "beamtime-metadata-"
        currentpostfix = ".json"
        beamtime = "2342342"

        bfn = "%s/%s%s%s" % (cwd, currentprefix, beamtime, currentpostfix)
        try:
            open(bfn, 'a').close()

            lfname = "%s/scicat-datasets-%s-%s.lst" % (cwd, hostname, beamtime)
            result = scdataset.append_scicat_dataset(macro)
            self.assertEqual("mytest_00012", result)
            self.assertEqual(macro.log,
                             ["Appending 'mytest_00012' to %s" % (lfname)])
        finally:
            os.remove(bfn)
            if os.path.isfile(lfname):
                os.remove(lfname)

    def test_scingestor_append_scicat_dataset_usernames(self):
        """
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        cwd = os.getcwd()
        currentprefix = "bt-mt-"
        currentpostfix = ".jsn"
        currentprefix = "bt-mt-"
        currentpostfix = ".jsn"
        beamtime = "2234231"
        dtlistprefix = 'sc-ds-'
        dtlistpostfix = '.lt'

        macro = TstMacro()
        macro.env["ScanFile"] = "mytest.fio"
        macro.env["ScanDir"] = cwd
        macro.env["ScanID"] = 12
        macro.env["AppendSciCatDataset"] = True
        macro.env["NXSAppendSciCatDataset"] = True
        macro.env["BeamtimeFilePath"] = cwd
        macro.env["SciCatDatasetListFileLocal"] = True
        macro.env["BeamtimeFilePrefix"] = currentprefix
        macro.env["BeamtimeFileExt"] = currentpostfix
        macro.env["SciCatDatasetListFilePrefix"] = dtlistprefix
        macro.env["SciCatDatasetListFileExt"] = dtlistpostfix

        bfn = "%s/%s%s%s" % (cwd, currentprefix, beamtime, currentpostfix)

        try:
            open(bfn, 'a').close()

            result = scdataset.append_scicat_dataset(macro)
            self.assertEqual("mytest_00012", result)
            lfname = "%s/sc-ds-%s.lt" % (cwd, beamtime)
            self.assertEqual(macro.log,
                             ["Appending 'mytest_00012' to %s" % (lfname)])
        finally:
            os.remove(bfn)
            if os.path.isfile(lfname):
                os.remove(lfname)


if __name__ == '__main__':
    unittest.main()
