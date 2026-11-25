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
# \file RedisWriterMocked_test.py
# unittests for nxstools.rediswriter with a mocked blissdata datastore
#
import unittest
import os
import sys
import time

import nxstools.rediswriter as rediswriter


# a mocked blissdata scan recording the lifecycle commands it receives
class MockScan(object):

    # constructor
    def __init__(self):
        #: (:obj:`dict`) scan info
        self.info = {}
        #: (:obj:`list` <:obj:`str`>) received lifecycle commands
        self.commands = []

    def prepare(self):
        self.commands.append("prepare")

    def start(self):
        self.commands.append("start")

    def stop(self):
        self.commands.append("stop")

    def close(self):
        self.commands.append("close")


# a mocked blissdata datastore replacing the one built from a redis url.
# It never connects to redis so it can be injected in tests.
class MockDataStore(object):

    # constructor
    def __init__(self):
        #: (:obj:`list`) create_scan call arguments
        self.created = []
        #: (:class:`MockScan`) the last created scan
        self.scan = None

    # mocked create_scan
    # \param identity scan identity dictionary
    # \param info scan info dictionary
    def create_scan(self, identity, info=None):
        self.created.append((identity, info))
        scan = MockScan()
        if info:
            scan.info.update(info)
        self.scan = scan
        return scan


# test fixture
class RedisWriterMockedTest(unittest.TestCase):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

        self.seed = int(time.time() * 256)  # use fractional seconds

        #: (:obj:`str`) a unique redis url - never contacted, only a cache key
        self.__url = "redis://localhost:6399/nxstools_mock_%s" % os.getpid()

    # test starter
    # \brief Common set up - inject the mocked datastore
    def setUp(self):
        print("\nsetting up...")
        print("SEED = %s" % self.seed)
        self.__ds = MockDataStore()
        # RedisFile picks up an already-cached datastore for the url, so
        # pre-seeding the global cache injects the mock without a real redis.
        rediswriter.RedisFile.global_data_stores[self.__url] = self.__ds
        self.__fname = "/tmp/nxstools_rediswriter_mock_%s.h5" % os.getpid()

    # test closer
    # \brief Common tear down
    def tearDown(self):
        print("tearing down ...")
        rediswriter.RedisFile.global_data_stores.pop(self.__url, None)
        if os.path.exists(self.__fname):
            os.remove(self.__fname)

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

    # creates a RedisFile wired to the injected mocked datastore
    # \returns a RedisFile instance
    def __create(self):
        return rediswriter.create_file(
            self.__fname, overwrite=True,
            redisurl=self.__url, session="mock_session")

    # datastore injection test
    # \brief prepare() creates a scan through the mocked datastore
    def test_datastore_injected(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not rediswriter.REDIS:
            self.skipTest("blissdata / redis_om not available")

        fl = self.__create()
        try:
            rt = fl.root()
            entry = rt.create_group("entry_00042", "NXentry")
            entry.create_group("instrument", "NXinstrument")
            fl.prepare()

            # exactly one scan was created through the injected datastore
            self.assertEqual(len(self.__ds.created), 1)
            identity = self.__ds.created[0][0]
            self.assertEqual(identity["session"], "mock_session")
            # the entry number is parsed into the scan identity
            self.assertEqual(identity["number"], 42)
            self.assertTrue(self.__ds.scan is not None)
        finally:
            fl.close()

    # scan lifecycle test
    # \brief prepare/start/finish drive the scan prepare/start/stop/close
    def test_scan_lifecycle(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if not rediswriter.REDIS:
            self.skipTest("blissdata / redis_om not available")

        fl = self.__create()
        try:
            rt = fl.root()
            entry = rt.create_group("entry_00001", "NXentry")
            entry.create_group("instrument", "NXinstrument")

            fl.prepare()
            fl.start()
            fl.finish()

            scan = self.__ds.scan
            # the whole blissdata scan lifecycle is exercised in order
            self.assertEqual(
                scan.commands, ["prepare", "start", "stop", "close"])
            # start() fills the scan info with the acquisition chain and plots
            self.assertTrue("acquisition_chain" in scan.info)
            self.assertTrue("plots" in scan.info)
            # finish() records a successful end reason
            self.assertEqual(scan.info["end_reason"], "SUCCESS")
        finally:
            fl.close()


if __name__ == '__main__':
    unittest.main()
