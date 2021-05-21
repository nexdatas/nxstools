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
import PyTango
# import json
# import nxstools
# from nxstools import nxscreate
# from nxstools import nxsdevicetools

import nxstools.h5cppwriter as H5CppWriter


if sys.version_info > (3,):
    unicode = str
    long = int


# if 64-bit machione
IS64BIT = (struct.calcsize("P") == 8)


class TstRoot(object):

    filename = ""


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

        self.__args = '{"host":"localhost", "db":"nxsconfig", ' \
                      '"read_default_file":"/etc/my.cnf", "use_unicode":true}'

        # home = expanduser("~")
        db = PyTango.Database()
        self.host = db.get_db_host().split(".")[0]
        self.port = db.get_db_port()
        self.directory = "."
        self.flags = "-d . "
        # self.flags = " -d -r testp09/testmcs/testr228 "
        self.device = 'testp09/testmcs/testr228'
        self.fwriter = H5CppWriter

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


if __name__ == '__main__':
    unittest.main()
