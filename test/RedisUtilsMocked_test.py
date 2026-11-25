#!/usr/bin/env python
#   This file is part of nexdatas - Tango Server for NeXus data writer
#
#    Copyright (C) 2012-2017 DESY, Jan Kotanski <jkotan@mail.desy.de>
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
# \file RedisUtilsMocked_test.py
# unittests for nxstools.redisutils with a mocked blissdata datastore
#
import unittest
import sys
import time

import nxstools.redisutils as redisutils


# test fixture
class RedisUtilsMockedTest(unittest.TestCase):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

        self.seed = int(time.time() * 256)  # use fractional seconds

    # test starter
    # \brief Common set up
    def setUp(self):
        print("\nsetting up...")
        print("SEED = %s" % self.seed)
        #: (:class:`type`) the original DataStore symbol to restore
        self.__orig_datastore = redisutils.DataStore

    # test closer
    # \brief Common tear down
    def tearDown(self):
        print("tearing down ...")
        redisutils.DataStore = self.__orig_datastore

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

    # installs a mocked DataStore that records its constructor calls
    # \param raise_on predicate(init_db) deciding when to raise
    # \returns the mocked DataStore class
    def __install_fake(self, raise_on=None):

        class FakeDataStore(object):
            calls = []

            def __init__(self, url, init_db=None, identity_model_cls=None):
                FakeDataStore.calls.append(
                    {"url": url, "init_db": init_db,
                     "identity_model_cls": identity_model_cls})
                if raise_on is not None and raise_on(init_db):
                    raise RuntimeError("mocked datastore error")
                self.url = url

        redisutils.DataStore = FakeDataStore
        return FakeDataStore

    # getDataStore success test
    # \brief the first (init_db=True) datastore construction is used
    def test_getDataStore_success(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fake = self.__install_fake(raise_on=None)
        ds = redisutils.getDataStore("redis://localhost:6380")
        self.assertTrue(isinstance(ds, fake))
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0]["init_db"], True)
        self.assertEqual(fake.calls[0]["url"], "redis://localhost:6380")

    # getDataStore fallback test
    # \brief when init_db=True fails the plain datastore is returned
    def test_getDataStore_fallback(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        # only the init_db=True construction raises
        fake = self.__install_fake(raise_on=lambda init_db: bool(init_db))
        ds = redisutils.getDataStore("redis://localhost:6380")
        self.assertTrue(isinstance(ds, fake))
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(fake.calls[0]["init_db"], True)
        self.assertEqual(fake.calls[1]["init_db"], None)

    # getDataStore failure test
    # \brief when both constructions fail None is returned
    def test_getDataStore_failure(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fake = self.__install_fake(raise_on=lambda init_db: True)
        ds = redisutils.getDataStore("redis://localhost:6380")
        self.assertTrue(ds is None)
        self.assertEqual(len(fake.calls), 2)

    # build_acq_chain test
    # \brief channels are bucketed and the scanned motor becomes the master
    def test_build_acq_chain(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        devices = {
            "time": {"channels": ["timestamp"]},
            "mg_channels": {"channels": ["det1", "exp_mot01"]},
            "mca": {"channels": ["mca1"]},
            "image": {"channels": ["img1"]},
        }
        res = redisutils.build_acq_chain(
            devices, title="ascan exp_mot01 0 1 10 0.1",
            channels=["det1", "exp_mot01", "mca1", "img1", "timestamp"])

        # without blissdata schemas build_acq_chain is a no-op
        if redisutils.ChainDict is None:
            self.assertEqual(res, {})
            return

        self.assertTrue("axis" in res)
        axis = res["axis"]
        # the scanned motor is the acquisition master, not a scalar counter
        self.assertEqual(list(axis["master"]["scalars"]), ["exp_mot01"])
        self.assertTrue("det1" in axis["scalars"])
        self.assertTrue("exp_mot01" not in axis["scalars"])
        # mca -> spectra, image -> images
        self.assertTrue("mca1" in axis["spectra"])
        self.assertTrue("img1" in axis["images"])


if __name__ == '__main__':
    unittest.main()
