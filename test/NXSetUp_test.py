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
import socket
import subprocess
try:
    import tango
except Exception:
    import PyTango as tango
from nxstools import nxsetup

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

try:
    import MacroServerSetUp
except Exception:
    from . import MacroServerSetUp

try:
    import TestPoolSetUp
except Exception:
    from . import TestPoolSetUp

try:
    import TestServerSetUp
except ImportError:
    from . import TestServerSetUp


try:
    import whichcraft
    WHICHCRAFT = True
except Exception:
    WHICHCRAFT = False

try:
    __import__("nxsconfigserver")
    if not WHICHCRAFT or whichcraft.which("NXSConfigServer"):
        CNFSRV = True
    else:
        CNFSRV = False
except Exception:
    CNFSRV = False

try:
    __import__("nxswriter")
    if not WHICHCRAFT or whichcraft.which("NXSDataWriter"):
        DTWRITER = True
    else:
        DTWRITER = False
except Exception:
    DTWRITER = False

try:
    __import__("nxsrecconfig")
    if not WHICHCRAFT or whichcraft.which("NXSRecSelector"):
        RECSEL = True
    else:
        RECSEL = False
except Exception:
    RECSEL = False


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
class NXSetUpTest(unittest.TestCase):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

        self.helperror = "Error: too few arguments\n"
        self.maxDiff = None
        self.helpinfo = """usage: nxsetup [-h]
               {set,restart,start,stop,wait,move-prop,change-prop,add-recorder-path}
               ...

Command-line tool for setting up  NeXus Tango Servers

positional arguments:
  {set,restart,start,stop,wait,move-prop,change-prop,add-recorder-path}
                        sub-command help
    set                 set up NXSConfigServer NXSDataWriter and
                        NXSRecSelector servers
    restart             restart tango server
    start               start tango server
    stop                stop tango server
    wait                wait for tango server
    move-prop           change property name
    change-prop         change property value
    add-recorder-path   add-recorder-path into MacroServer(s) property

optional arguments:
  -h, --help            show this help message and exit

For more help:
  nxsetup <sub-command> -h
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

        self.__args = '{"db":"nxsconfig", ' \
                      '"read_default_file":"/etc/my.cnf", "use_unicode":true}'
        self.__cmps = []
        self.__ds = []
        self.__man = []
        self.children = ("record", "doc", "device", "database", "query",
                         "datasource", "result")

        from os.path import expanduser
        home = expanduser("~")
        self.__args2 = '{"db":"nxsconfig", ' \
                       '"read_default_file":"%s/.my.cnf", ' \
                       '"use_unicode":true}' % home
        self.db = tango.Database()
        self.tghost = self.db.get_db_host().split(".")[0]
        self.tgport = self.db.get_db_port()
        self.host = socket.gethostname()
        self._ms = MacroServerSetUp.MacroServerSetUp()
        self._pool = TestPoolSetUp.TestPoolSetUp()

    def checkDevice(self, dvname):

        found = False
        cnt = 0
        while not found and cnt < 100:
            try:
                sys.stdout.write(".")
                dp = tango.DeviceProxy(dvname)
                time.sleep(0.01)
                dp.ping()
                if dp.state() == tango.DevState.ON:
                    found = True
                found = True
            except Exception as e:
                print("%s %s" % (dvname, e))
                found = False
            except Exception:
                found = False

            cnt += 1
        self.assertTrue(found)

    def serverPid(self, svname):
        pid = None
        svname, instance = svname.split("/")
        if sys.version_info > (3,):
            with subprocess.Popen(
                    "ps -ef | grep '%s %s' | grep -v grep" %
                    (svname, instance),
                    stdout=subprocess.PIPE, shell=True) as proc:

                pipe = proc.stdout
                res = str(pipe.read(), "utf-8").split("\n")
                # print(res)
                for r in res:
                    sr = r.split()
                    if len(sr) > 2:
                        pid = sr[1]
                pipe.close()
        else:
            pipe = subprocess.Popen(
                "ps -ef | grep '%s %s' | grep -v grep" %
                (svname, instance),
                stdout=subprocess.PIPE, shell=True).stdout

            res = str(pipe.read()).split("\n")
            print(res)
            for r in res:
                sr = r.split()
                if len(sr) > 2:
                    pid = sr[1]
            pipe.close()
        return pid

    def getProperty(self, dvname, prname):
        res = self.db.get_device_property(dvname, prname)[prname]
        if res:
            res = [p for p in res if p]
        else:
            res = []
        return res

    def stopServer(self, svname):
        # HardKillServer does not work
        try:
            admin = nxsetup.SetUp().getStarterName(self.host)
            adp = tango.DeviceProxy(admin)
            adp.UpdateServersInfo()
            adp.HardKillServer(svname)
        except Exception:
            pass

        svname, instance = svname.split("/")
        if sys.version_info > (3,):
            with subprocess.Popen(
                    "ps -ef | grep '%s %s' | grep -v grep" %
                    (svname, instance),
                    stdout=subprocess.PIPE, shell=True) as proc:

                pipe = proc.stdout
                res = str(pipe.read(), "utf-8").split("\n")
                for r in res:
                    sr = r.split()
                    if len(sr) > 2:
                        subprocess.call(
                            "kill -9 %s" % sr[1], stderr=subprocess.PIPE,
                            shell=True)
                pipe.close()
        else:
            pipe = subprocess.Popen(
                "ps -ef | grep '%s %s' | grep -v grep" %
                (svname, instance),
                stdout=subprocess.PIPE, shell=True).stdout

            res = str(pipe.read()).split("\n")
            for r in res:
                sr = r.split()
                if len(sr) > 2:
                    subprocess.call(
                        "kill -9 %s" % sr[1], stderr=subprocess.PIPE,
                        shell=True)
            pipe.close()

    def unregisterServer(self, svname, dvname=None):
        if dvname is not None:
            self.db.delete_device(dvname)
        self.db.delete_server(svname)

    # test starter
    # \brief Common set up
    def setUp(self):
        print("\nsetting up...")
        # self._sv.setUp()
        self._ms.setUp()
        self._pool.setUp()
        print("SEED = %s" % self.seed)

    # test closer
    # \brief Common tear down
    def tearDown(self):
        print("tearing down ...")
        self._pool.tearDown()
        self._ms.tearDown(True)

    def runtest(self, argv):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = mystdout = StringIO()
        sys.stderr = mystderr = StringIO()

        old_argv = sys.argv
        sys.argv = argv
        etxt = None
        try:
            nxsetup.main()
        except Exception as e:
            etxt = str(e)
        except SystemExit as e:
            etxt = str(e)
        sys.argv = old_argv

        sys.stdout = old_stdout
        sys.stderr = old_stderr
        vl = mystdout.getvalue()
        er = mystderr.getvalue()
        print(vl)
        print(er)
        if etxt:
            print(etxt)
        self.assertTrue(etxt is None)
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
            nxsetup.main()
        except exception as e:
            etxt = str(e)
            error = True
        self.assertEqual(error, True)

        sys.argv = old_argv

        sys.stdout = old_stdout
        sys.stderr = old_stderr
        vl = mystdout.getvalue()
        er = mystderr.getvalue()
        return vl, er, etxt

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

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_default(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        vl, er, et = self.runtestexcept(['nxsetup'], SystemExit)
        h1 = "".join(self.helpinfo.split()).replace(
            "optionalarguments:", "options:")
        h2 = "".join(vl.split()).replace(
            "optionalarguments:", "options:").replace(
                "usage:python3", "usage:").replace(
                    "usage:python", "usage:")
        if len(h2) > len(h1):
            self.assertEqual(h2[:len(h1)], h1)
        else:
            self.assertEqual(h2, h1)
        self.assertEqual(self.helperror, er)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_help(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        helps = ['-h', '--help']
        for hl in helps:
            vl, er, et = self.runtestexcept(['nxsetup', hl], SystemExit)
            h1 = "".join(self.helpinfo.split()).replace(
                "optionalarguments:", "options:")
            h2 = "".join(vl.split()).replace(
                "optionalarguments:", "options:").replace(
                    "usage:python3", "usage:").replace(
                        "usage:python", "usage:")
            if len(h2) > len(h1):
                self.assertEqual(h2[:len(h1)], h1)
            else:
                self.assertEqual(h2, h1)
            self.assertEqual('', er)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_set(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if self.host in nxsetup.knownHosts.keys():
            cnf = nxsetup.knownHosts[self.host]
        else:
            cnf = {'beamline': 'nxs',
                   'masterhost': '%s' % self.host,
                   'user': 'tango',
                   'dbname': 'nxsconfig'}

        cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
        dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
        rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
        cfdvname = "%s/nxsconfigserver/%s" % \
            (cnf['beamline'], cnf["masterhost"])
        dwdvname = "%s/nxsdatawriter/%s" % \
            (cnf['beamline'], cnf["masterhost"])
        rsdvname = "%s/nxsrecselector/%s" % \
            (cnf['beamline'], cnf["masterhost"])

        cfservers = self.db.get_server_list(cfsvname).value_string
        dwservers = self.db.get_server_list(dwsvname).value_string
        rsservers = self.db.get_server_list(rssvname).value_string

        dwdevices = self.db.get_device_exported_for_class(
            "NXSDataWriter").value_string
        cfdevices = self.db.get_device_exported_for_class(
            "NXSConfigServer").value_string
        rsdevices = self.db.get_device_exported_for_class(
            "NXSRecSelector").value_string
        skiptest = False
        if cfsvname in cfservers:
            skiptest = True
        if dwsvname in dwservers:
            skiptest = True
        if rssvname in rsservers:
            skiptest = True
        if cfdvname in cfdevices:
            skiptest = True
        if dwdvname in dwdevices:
            skiptest = True
        if rsdvname in rsdevices:
            skiptest = True

        skiptest = skiptest or not CNFSRV or not DTWRITER or not RECSEL

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)

        commands = ['nxsetup set'.split()]
        for cmd in commands:
            if not skiptest:
                try:
                    vl, er = self.runtest(cmd)
                    self.assertEqual('', er)
                    # print(vl)
                    # print(er)
                    cfservers = self.db.get_server_list(cfsvname).value_string
                    dwservers = self.db.get_server_list(dwsvname).value_string
                    rsservers = self.db.get_server_list(rssvname).value_string
                    self.assertTrue(cfsvname in cfservers)
                    self.assertTrue(dwsvname in dwservers)
                    self.assertTrue(rssvname in rsservers)

                    cfdevices = self.db.get_device_exported_for_class(
                        "NXSConfigServer").value_string
                    dwdevices = self.db.get_device_exported_for_class(
                        "NXSDataWriter").value_string
                    rsdevices = self.db.get_device_exported_for_class(
                        "NXSRecSelector").value_string
                    self.assertTrue(cfdvname in cfdevices)
                    self.assertTrue(dwdvname in dwdevices)
                    self.assertTrue(rsdvname in rsdevices)
                    self.checkDevice(cfdvname)
                    self.checkDevice(dwdvname)
                    self.checkDevice(rsdvname)
                finally:
                    try:
                        self.stopServer(rssvname)
                    except Exception:
                        pass
                    finally:
                        try:
                            self.unregisterServer(rssvname, rsdvname)
                        except Exception:
                            pass
                    try:
                        self.stopServer(cfsvname)
                    except Exception:
                        pass
                    finally:
                        try:
                            self.unregisterServer(cfsvname, cfdvname)
                        except Exception:
                            pass
                    try:
                        self.stopServer(dwsvname)
                    except Exception:
                        pass
                    finally:
                        try:
                            self.unregisterServer(dwsvname, dwdvname)
                        except Exception:
                            pass
                    setup = nxsetup.SetUp()
                    setup.waitServerNotRunning(
                        cfsvname, cfdvname,  adminproxy, verbose=False,
                        waitforproc=False)
                    setup.waitServerNotRunning(
                        dwsvname, dwdvname, adminproxy, verbose=False,
                        waitforproc=False)
                    setup.waitServerNotRunning(
                        rssvname, rsdvname, adminproxy, verbose=False)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_set_master_beamline(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if self.host in nxsetup.knownHosts.keys():
            dfcnf = nxsetup.knownHosts[self.host]
        else:
            dfcnf = {'beamline': 'nxs',
                     'masterhost': '%s' % self.host,
                     'user': 'tango',
                     'dbname': 'nxsconfig'}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['beamline'] = 'testnxs'
        cnfs[0]['masterhost'] = 'haso000'
        cnfs[1]['beamline'] = 'testnxs2'
        cnfs[1]['masterhost'] = 'hasoo12'
        cnfs[2]['beamline'] = 'test2nxs'
        cnfs[2]['masterhost'] = 'hasoo12'
        cnfs[3]['beamline'] = 'testnxs3'
        cnfs[3]['masterhost'] = 'hasoo000'

        for cnf in cnfs:
            cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
            dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
            rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
            cfdvname = "%s/nxsconfigserver/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            dwdvname = "%s/nxsdatawriter/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            rsdvname = "%s/nxsrecselector/%s" % \
                (cnf['beamline'], cnf["masterhost"])

            cfservers = self.db.get_server_list(cfsvname).value_string
            dwservers = self.db.get_server_list(dwsvname).value_string
            rsservers = self.db.get_server_list(rssvname).value_string

            dwdevices = self.db.get_device_exported_for_class(
                "NXSDataWriter").value_string
            cfdevices = self.db.get_device_exported_for_class(
                "NXSConfigServer").value_string
            rsdevices = self.db.get_device_exported_for_class(
                "NXSRecSelector").value_string
            skiptest = False
            if cfsvname in cfservers:
                skiptest = True
            if dwsvname in dwservers:
                skiptest = True
            if rssvname in rsservers:
                skiptest = True
            if cfdvname in cfdevices:
                skiptest = True
            if dwdvname in dwdevices:
                skiptest = True
            if rsdvname in rsdevices:
                skiptest = True

            skiptest = skiptest or not CNFSRV or not DTWRITER or not RECSEL

            admin = nxsetup.SetUp().getStarterName(self.host)
            if not admin:
                skiptest = True
                adminproxy = None
            else:
                adminproxy = tango.DeviceProxy(admin)

            commands = [
                ('nxsetup set -b %s -m %s ' %
                 (cnf['beamline'], cnf['masterhost'])).split(),
                ('nxsetup set --beamline %s --masterhost %s ' %
                 (cnf['beamline'], cnf['masterhost'])).split(),
            ]
            for cmd in commands:
                if not skiptest:
                    try:
                        vl, er = self.runtest(cmd)
                        self.assertEqual('', er)
                        self.assertTrue(vl)
                        cfservers = self.db.get_server_list(
                            cfsvname).value_string
                        dwservers = self.db.get_server_list(
                            dwsvname).value_string
                        rsservers = self.db.get_server_list(
                            rssvname).value_string
                        self.assertTrue(cfsvname in cfservers)
                        self.assertTrue(dwsvname in dwservers)
                        self.assertTrue(rssvname in rsservers)

                        cfdevices = self.db.get_device_exported_for_class(
                            "NXSConfigServer").value_string
                        dwdevices = self.db.get_device_exported_for_class(
                            "NXSDataWriter").value_string
                        rsdevices = self.db.get_device_exported_for_class(
                            "NXSRecSelector").value_string
                        self.assertTrue(cfdvname in cfdevices)
                        self.assertTrue(dwdvname in dwdevices)
                        self.assertTrue(rsdvname in rsdevices)
                        self.checkDevice(cfdvname)
                        self.checkDevice(dwdvname)
                        self.checkDevice(rsdvname)
                    finally:
                        try:
                            self.stopServer(rssvname)
                        except Exception:
                            pass
                        finally:
                            try:
                                self.unregisterServer(rssvname, rsdvname)
                            except Exception:
                                pass
                        try:
                            self.stopServer(cfsvname)
                        except Exception:
                            pass
                        finally:
                            try:
                                self.unregisterServer(cfsvname, cfdvname)
                            except Exception:
                                pass
                        try:
                            self.stopServer(dwsvname)
                        except Exception:
                            pass
                        finally:
                            try:
                                self.unregisterServer(dwsvname, dwdvname)
                            except Exception:
                                pass
                        setup = nxsetup.SetUp()
                        setup.waitServerNotRunning(
                            cfsvname, cfdvname,  adminproxy, verbose=False,
                            waitforproc=False)
                        setup.waitServerNotRunning(
                            dwsvname, dwdvname, adminproxy, verbose=False,
                            waitforproc=False)
                        setup.waitServerNotRunning(
                            rssvname, rsdvname, adminproxy, verbose=False)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_set_all(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if self.host in nxsetup.knownHosts.keys():
            dfcnf = nxsetup.knownHosts[self.host]
        else:
            dfcnf = {'beamline': 'nxs',
                     'masterhost': '%s' % self.host,
                     'user': 'tango',
                     'dbname': 'nxsconfig'}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['beamline'] = 'testnxs'
        cnfs[0]['masterhost'] = 'haso000'
        cnfs[1]['beamline'] = 'testnxs2'
        cnfs[1]['masterhost'] = 'hasoo12'
        cnfs[2]['beamline'] = 'test2nxs'
        cnfs[2]['masterhost'] = 'hasoo12'
        cnfs[3]['beamline'] = 'testnxs3'
        cnfs[3]['masterhost'] = 'hasoo000'

        for cnf in cnfs:
            cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
            dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
            rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
            cfdvname = "%s/nxsconfigserver/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            dwdvname = "%s/nxsdatawriter/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            rsdvname = "%s/nxsrecselector/%s" % \
                (cnf['beamline'], cnf["masterhost"])

            cfservers = self.db.get_server_list(cfsvname).value_string
            dwservers = self.db.get_server_list(dwsvname).value_string
            rsservers = self.db.get_server_list(rssvname).value_string

            dwdevices = self.db.get_device_exported_for_class(
                "NXSDataWriter").value_string
            cfdevices = self.db.get_device_exported_for_class(
                "NXSConfigServer").value_string
            rsdevices = self.db.get_device_exported_for_class(
                "NXSRecSelector").value_string
            skiptest = False
            if cfsvname in cfservers:
                skiptest = True
            if dwsvname in dwservers:
                skiptest = True
            if rssvname in rsservers:
                skiptest = True
            if cfdvname in cfdevices:
                skiptest = True
            if dwdvname in dwdevices:
                skiptest = True
            if rsdvname in rsdevices:
                skiptest = True

            skiptest = skiptest or not CNFSRV or not DTWRITER or not RECSEL

            admin = nxsetup.SetUp().getStarterName(self.host)
            if not admin:
                skiptest = True
                adminproxy = None
            else:
                adminproxy = tango.DeviceProxy(admin)

            commands = [
                ('nxsetup set '
                 ' -b %s '
                 ' -m %s '
                 ' -u %s '
                 ' -d %s '
                 % (cnf['beamline'], cnf['masterhost'],
                    cnf['user'], cnf['dbname'])).split(),
                ('nxsetup set '
                 ' --beamline %s '
                 ' --masterhost %s '
                 ' --user %s '
                 ' --database %s '
                 % (cnf['beamline'], cnf['masterhost'],
                    cnf['user'], cnf['dbname'])).split(),
            ]
            for cmd in commands:
                if not skiptest:
                    try:
                        vl, er = self.runtest(cmd)
                        # print(vl)
                        # print(el)
                        self.assertEqual('', er)
                        self.assertTrue(vl)
                        cfservers = self.db.get_server_list(
                            cfsvname).value_string
                        dwservers = self.db.get_server_list(
                            dwsvname).value_string
                        rsservers = self.db.get_server_list(
                            rssvname).value_string
                        self.assertTrue(cfsvname in cfservers)
                        self.assertTrue(dwsvname in dwservers)
                        self.assertTrue(rssvname in rsservers)

                        cfdevices = self.db.get_device_exported_for_class(
                            "NXSConfigServer").value_string
                        dwdevices = self.db.get_device_exported_for_class(
                            "NXSDataWriter").value_string
                        rsdevices = self.db.get_device_exported_for_class(
                            "NXSRecSelector").value_string
                        self.assertTrue(cfdvname in cfdevices)
                        self.assertTrue(dwdvname in dwdevices)
                        self.assertTrue(rsdvname in rsdevices)
                        self.checkDevice(cfdvname)
                        self.checkDevice(dwdvname)
                        self.checkDevice(rsdvname)

                    finally:
                        try:
                            self.stopServer(rssvname)
                        except Exception:
                            pass
                        finally:
                            try:
                                self.unregisterServer(rssvname, rsdvname)
                            except Exception:
                                pass
                        try:
                            self.stopServer(cfsvname)
                        except Exception:
                            pass
                        finally:
                            try:
                                self.unregisterServer(cfsvname, cfdvname)
                            except Exception:
                                pass
                        try:
                            self.stopServer(dwsvname)
                        except Exception:
                            pass
                        finally:
                            try:
                                self.unregisterServer(dwsvname, dwdvname)
                            except Exception:
                                pass
                        setup = nxsetup.SetUp()
                        setup.waitServerNotRunning(
                            cfsvname, cfdvname,  adminproxy, verbose=False,
                            waitforproc=False)
                        setup.waitServerNotRunning(
                            dwsvname, dwdvname, adminproxy, verbose=False,
                            waitforproc=False)
                        setup.waitServerNotRunning(
                            rssvname, rsdvname, adminproxy, verbose=False)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_set_nxsconfigserver(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if self.host in nxsetup.knownHosts.keys():
            dfcnf = nxsetup.knownHosts[self.host]
        else:
            dfcnf = {'beamline': 'nxs',
                     'masterhost': '%s' % self.host,
                     'user': 'tango',
                     'dbname': 'nxsconfig'}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['beamline'] = 'testnxs'
        cnfs[0]['masterhost'] = 'haso000'
        cnfs[1]['beamline'] = 'testnxs2'
        cnfs[1]['masterhost'] = 'hasoo12'
        cnfs[2]['beamline'] = 'test2nxs'
        cnfs[2]['masterhost'] = 'hasoo12'
        cnfs[3]['beamline'] = 'testnxs3'
        cnfs[3]['masterhost'] = 'hasoo000'
        
        for cnf in cnfs:
          for _ in range(100):
            cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
            dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
            rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
            cfdvname = "%s/nxsconfigserver/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            dwdvname = "%s/nxsdatawriter/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            rsdvname = "%s/nxsrecselector/%s" % \
                (cnf['beamline'], cnf["masterhost"])

            cfservers = self.db.get_server_list(cfsvname).value_string
            dwservers = self.db.get_server_list(dwsvname).value_string
            rsservers = self.db.get_server_list(rssvname).value_string

            dwdevices = self.db.get_device_exported_for_class(
                "NXSDataWriter").value_string
            cfdevices = self.db.get_device_exported_for_class(
                "NXSConfigServer").value_string
            rsdevices = self.db.get_device_exported_for_class(
                "NXSRecSelector").value_string
            skiptest = False
            if cfsvname in cfservers:
                skiptest = True
            if dwsvname in dwservers:
                skiptest = True
            if rssvname in rsservers:
                skiptest = True
            if cfdvname in cfdevices:
                skiptest = True
            if dwdvname in dwdevices:
                skiptest = True
            if rsdvname in rsdevices:
                skiptest = True

            skiptest = skiptest or not CNFSRV or not DTWRITER or not RECSEL

            admin = nxsetup.SetUp().getStarterName(self.host)
            if not admin:
                skiptest = True
                adminproxy = None
            else:
                adminproxy = tango.DeviceProxy(admin)
            commands = [
                ('nxsetup set NXSConfigServer '
                 ' -b %s '
                 ' -m %s '
                 ' -u %s '
                 ' -d %s '
                 % (cnf['beamline'], cnf['masterhost'],
                    cnf['user'], cnf['dbname'])).split(),
                ('nxsetup set NXSConfigServer '
                 ' --beamline %s '
                 ' --masterhost %s '
                 ' --user %s '
                 ' --database %s '
                 % (cnf['beamline'], cnf['masterhost'],
                    cnf['user'], cnf['dbname'])).split(),
            ]
            for cmd in commands:
                if not skiptest:
                    try:
                        print(cmd)
                        vl, er = self.runtest(cmd)
                        self.assertEqual('', er)
                        self.assertTrue(vl)
                        cfservers = self.db.get_server_list(
                            cfsvname).value_string
                        dwservers = self.db.get_server_list(
                            dwsvname).value_string
                        rsservers = self.db.get_server_list(
                            rssvname).value_string
                        self.assertTrue(cfsvname in cfservers)
                        self.assertTrue(dwsvname not in dwservers)
                        self.assertTrue(rssvname not in rsservers)

                        cfdevices = self.db.get_device_exported_for_class(
                            "NXSConfigServer").value_string
                        dwdevices = self.db.get_device_exported_for_class(
                            "NXSDataWriter").value_string
                        rsdevices = self.db.get_device_exported_for_class(
                            "NXSRecSelector").value_string
                        self.assertTrue(cfdvname in cfdevices)
                        self.assertTrue(dwdvname not in dwdevices)
                        self.assertTrue(rsdvname not in rsdevices)
                        self.checkDevice(cfdvname)
                    finally:
                        try:
                            self.stopServer(cfsvname)
                        except Exception:
                            pass
                        finally:
                            try:
                                self.unregisterServer(cfsvname, cfdvname)
                            except Exception:
                                pass
                        setup = nxsetup.SetUp()
                        setup.waitServerNotRunning(
                            cfsvname, cfdvname,  adminproxy, verbose=False)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_set_csjson(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if self.host in nxsetup.knownHosts.keys():
            dfcnf = nxsetup.knownHosts[self.host]
        else:
            dfcnf = {'beamline': 'nxs',
                     'masterhost': '%s' % self.host,
                     'user': 'tango',
                     'dbname': 'nxsconfig'}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['beamline'] = 'testnxs'
        cnfs[0]['masterhost'] = 'haso000'
        cnfs[1]['beamline'] = 'testnxs2'
        cnfs[1]['masterhost'] = 'hasoo12'
        cnfs[2]['beamline'] = 'test2nxs'
        cnfs[2]['masterhost'] = 'hasoo12'
        cnfs[3]['beamline'] = 'testnxs3'
        cnfs[3]['masterhost'] = 'hasoo000'

        for cnf in cnfs:
            cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
            dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
            rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
            cfdvname = "%s/nxsconfigserver/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            dwdvname = "%s/nxsdatawriter/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            rsdvname = "%s/nxsrecselector/%s" % \
                (cnf['beamline'], cnf["masterhost"])

            cfservers = self.db.get_server_list(cfsvname).value_string
            dwservers = self.db.get_server_list(dwsvname).value_string
            rsservers = self.db.get_server_list(rssvname).value_string

            dwdevices = self.db.get_device_exported_for_class(
                "NXSDataWriter").value_string
            cfdevices = self.db.get_device_exported_for_class(
                "NXSConfigServer").value_string
            rsdevices = self.db.get_device_exported_for_class(
                "NXSRecSelector").value_string
            skiptest = False
            if cfsvname in cfservers:
                skiptest = True
            if dwsvname in dwservers:
                skiptest = True
            if rssvname in rsservers:
                skiptest = True
            if cfdvname in cfdevices:
                skiptest = True
            if dwdvname in dwdevices:
                skiptest = True
            if rsdvname in rsdevices:
                skiptest = True

            skiptest = skiptest or not CNFSRV or not DTWRITER or not RECSEL

            admin = nxsetup.SetUp().getStarterName(self.host)
            if not admin:
                skiptest = True
                adminproxy = None
            else:
                adminproxy = tango.DeviceProxy(admin)
            if not os.path.isfile("/home/%s/.my.cnf" % cnf['user']):
                skiptest = True
            csjson = '{"db":"%s",' \
                     '"use_unicode":true,'\
                     '"read_default_file":"/home/%s/.my.cnf"}' % \
                     (cnf['dbname'], cnf['user'])
            commands = [
                ('nxsetup set '
                 ' -b %s '
                 ' -m %s '
                 ' -j %s '
                 % (cnf['beamline'], cnf['masterhost'], csjson)).split(),
                ('nxsetup set '
                 ' --beamline %s '
                 ' --masterhost %s '
                 ' --csjson %s '
                 % (cnf['beamline'], cnf['masterhost'], csjson)).split(),
            ]
            for cmd in commands:
                if not skiptest:
                    try:
                        vl, er = self.runtest(cmd)
                        self.assertEqual('', er)
                        self.assertTrue(vl)
                        cfservers = self.db.get_server_list(
                            cfsvname).value_string
                        dwservers = self.db.get_server_list(
                            dwsvname).value_string
                        rsservers = self.db.get_server_list(
                            rssvname).value_string
                        self.assertTrue(cfsvname in cfservers)
                        self.assertTrue(dwsvname in dwservers)
                        self.assertTrue(rssvname in rsservers)

                        cfdevices = self.db.get_device_exported_for_class(
                            "NXSConfigServer").value_string
                        dwdevices = self.db.get_device_exported_for_class(
                            "NXSDataWriter").value_string
                        rsdevices = self.db.get_device_exported_for_class(
                            "NXSRecSelector").value_string
                        self.assertTrue(cfdvname in cfdevices)
                        self.assertTrue(dwdvname in dwdevices)
                        self.assertTrue(rsdvname in rsdevices)
                        self.checkDevice(cfdvname)
                        self.checkDevice(dwdvname)
                        self.checkDevice(rsdvname)
                    finally:
                        try:
                            self.stopServer(rssvname)
                        except Exception:
                            pass
                        finally:
                            try:
                                self.unregisterServer(rssvname, rsdvname)
                            except Exception:
                                pass
                        try:
                            self.stopServer(cfsvname)
                        except Exception:
                            pass
                        finally:
                            try:
                                self.unregisterServer(cfsvname, cfdvname)
                            except Exception:
                                pass
                        try:
                            self.stopServer(dwsvname)
                        except Exception:
                            pass
                        finally:
                            try:
                                self.unregisterServer(dwsvname, dwdvname)
                            except Exception:
                                pass
                        setup = nxsetup.SetUp()
                        setup.waitServerNotRunning(
                            cfsvname, cfdvname,  adminproxy, verbose=False,
                            waitforproc=False)
                        setup.waitServerNotRunning(
                            dwsvname, dwdvname, adminproxy, verbose=False,
                            waitforproc=False)
                        setup.waitServerNotRunning(
                            rssvname, rsdvname, adminproxy, verbose=False)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_set_all_loop(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if self.host in nxsetup.knownHosts.keys():
            dfcnf = nxsetup.knownHosts[self.host]
        else:
            dfcnf = {'beamline': 'nxs',
                     'masterhost': '%s' % self.host,
                     'user': 'tango',
                     'dbname': 'nxsconfig'}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['beamline'] = 'testnxs'
        cnfs[0]['masterhost'] = 'haso000'
        cnfs[1]['beamline'] = 'testnxs2'
        cnfs[1]['masterhost'] = 'hasoo12'
        cnfs[2]['beamline'] = 'test2nxs'
        cnfs[2]['masterhost'] = 'hasoo12'
        cnfs[3]['beamline'] = 'testnxs3'
        cnfs[3]['masterhost'] = 'hasoo000'

        for i in range(1):
            # print(i)
            for cnf in cnfs:
                cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                cfdvname = "%s/nxsconfigserver/%s" % \
                    (cnf['beamline'], cnf["masterhost"])
                dwdvname = "%s/nxsdatawriter/%s" % \
                    (cnf['beamline'], cnf["masterhost"])
                rsdvname = "%s/nxsrecselector/%s" % \
                    (cnf['beamline'], cnf["masterhost"])

                cfservers = self.db.get_server_list(cfsvname).value_string
                dwservers = self.db.get_server_list(dwsvname).value_string
                rsservers = self.db.get_server_list(rssvname).value_string

                dwdevices = self.db.get_device_exported_for_class(
                    "NXSDataWriter").value_string
                cfdevices = self.db.get_device_exported_for_class(
                    "NXSConfigServer").value_string
                rsdevices = self.db.get_device_exported_for_class(
                    "NXSRecSelector").value_string
                skiptest = False
                if cfsvname in cfservers:
                    skiptest = True
                if dwsvname in dwservers:
                    skiptest = True
                if rssvname in rsservers:
                    skiptest = True
                if cfdvname in cfdevices:
                    skiptest = True
                if dwdvname in dwdevices:
                    skiptest = True
                if rsdvname in rsdevices:
                    skiptest = True

                skiptest = skiptest or not CNFSRV or not DTWRITER or not RECSEL

                admin = nxsetup.SetUp().getStarterName(self.host)
                if not admin:
                    skiptest = True
                    adminproxy = None
                else:
                    adminproxy = tango.DeviceProxy(admin)

                commands = [
                    ('nxsetup set '
                     ' -b %s '
                     ' -m %s '
                     ' -u %s '
                     ' -d %s '
                     % (cnf['beamline'], cnf['masterhost'],
                        cnf['user'], cnf['dbname'])).split(),
                    ('nxsetup set '
                     ' --beamline %s '
                     ' --masterhost %s '
                     ' --user %s '
                     ' --database %s '
                     % (cnf['beamline'], cnf['masterhost'],
                        cnf['user'], cnf['dbname'])).split(),
                ]
                for cmd in commands:
                    if not skiptest:
                        # print(cmd)
                        try:
                            vl, er = self.runtest(cmd)
                            # print(vl)
                            # print(er)
                            self.assertEqual('', er)
                            self.assertTrue(vl)
                            cfservers = self.db.get_server_list(
                                cfsvname).value_string
                            dwservers = self.db.get_server_list(
                                dwsvname).value_string
                            rsservers = self.db.get_server_list(
                                rssvname).value_string
                            self.assertTrue(cfsvname in cfservers)
                            self.assertTrue(dwsvname in dwservers)
                            self.assertTrue(rssvname in rsservers)

                            cfdevices = self.db.get_device_exported_for_class(
                                "NXSConfigServer").value_string
                            dwdevices = self.db.get_device_exported_for_class(
                                "NXSDataWriter").value_string
                            rsdevices = self.db.get_device_exported_for_class(
                                "NXSRecSelector").value_string
                            self.assertTrue(cfdvname in cfdevices)
                            self.assertTrue(dwdvname in dwdevices)
                            self.assertTrue(rsdvname in rsdevices)
                            self.checkDevice(cfdvname)
                            self.checkDevice(dwdvname)
                            self.checkDevice(rsdvname)
                        finally:
                            try:
                                self.stopServer(rssvname)
                            except Exception:
                                pass
                            finally:
                                try:
                                    self.unregisterServer(rssvname, rsdvname)
                                except Exception:
                                    pass
                            try:
                                self.stopServer(cfsvname)
                            except Exception:
                                pass
                            finally:
                                try:
                                    self.unregisterServer(cfsvname, cfdvname)
                                except Exception:
                                    pass
                            try:
                                self.stopServer(dwsvname)
                            except Exception:
                                pass
                            finally:
                                try:
                                    self.unregisterServer(dwsvname, dwdvname)
                                except Exception:
                                    pass
                            setup = nxsetup.SetUp()
                            setup.waitServerNotRunning(
                                cfsvname, cfdvname,  adminproxy, verbose=False,
                                waitforproc=False)
                            setup.waitServerNotRunning(
                                dwsvname, dwdvname, adminproxy, verbose=False,
                                waitforproc=False)
                            setup.waitServerNotRunning(
                                rssvname, rsdvname, adminproxy, verbose=False)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_set_all_loop2(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if self.host in nxsetup.knownHosts.keys():
            dfcnf = nxsetup.knownHosts[self.host]
        else:
            dfcnf = {'beamline': 'nxs',
                     'masterhost': '%s' % self.host,
                     'user': 'tango',
                     'dbname': 'nxsconfig'}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['beamline'] = 'testnxs'
        cnfs[0]['masterhost'] = 'haso000'
        cnfs[1]['beamline'] = 'testnxs2'
        cnfs[1]['masterhost'] = 'hasoo12'
        cnfs[2]['beamline'] = 'test2nxs'
        cnfs[2]['masterhost'] = 'hasoo12'
        cnfs[3]['beamline'] = 'testnxs3'
        cnfs[3]['masterhost'] = 'hasoo000'

        for _ in range(1):
            for cnf in cnfs:
                cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                cfdvname = "%s/nxsconfigserver/%s" % \
                    (cnf['beamline'], cnf["masterhost"])
                dwdvname = "%s/nxsdatawriter/%s" % \
                    (cnf['beamline'], cnf["masterhost"])
                rsdvname = "%s/nxsrecselector/%s" % \
                    (cnf['beamline'], cnf["masterhost"])

                cfservers = self.db.get_server_list(cfsvname).value_string
                dwservers = self.db.get_server_list(dwsvname).value_string
                rsservers = self.db.get_server_list(rssvname).value_string

                dwdevices = self.db.get_device_exported_for_class(
                    "NXSDataWriter").value_string
                cfdevices = self.db.get_device_exported_for_class(
                    "NXSConfigServer").value_string
                rsdevices = self.db.get_device_exported_for_class(
                    "NXSRecSelector").value_string
                skiptest = False
                if cfsvname in cfservers:
                    skiptest = True
                if dwsvname in dwservers:
                    skiptest = True
                if rssvname in rsservers:
                    skiptest = True
                if cfdvname in cfdevices:
                    skiptest = True
                if dwdvname in dwdevices:
                    skiptest = True
                if rsdvname in rsdevices:
                    skiptest = True

                skiptest = skiptest or not CNFSRV or not DTWRITER or not RECSEL

                admin = nxsetup.SetUp().getStarterName(self.host)
                if not admin:
                    skiptest = True
                    adminproxy = None
                else:
                    adminproxy = tango.DeviceProxy(admin)

                commands = [
                    ('nxsetup set '
                     ' NXSDataWriter NXSConfigServer NXSRecSelector '
                     ' -b %s '
                     ' -m %s '
                     ' -u %s '
                     ' -d %s '
                     % (cnf['beamline'], cnf['masterhost'],
                        cnf['user'], cnf['dbname'])).split(),
                    ('nxsetup set '
                     ' NXSDataWriter NXSConfigServer NXSRecSelector '
                     ' --beamline %s '
                     ' --masterhost %s '
                     ' --user %s '
                     ' --database %s '
                     % (cnf['beamline'], cnf['masterhost'],
                        cnf['user'], cnf['dbname'])).split(),
                ]
                for cmd in commands:
                    if not skiptest:
                        try:
                            vl, er = self.runtest(cmd)
                            self.assertEqual('', er)
                            self.assertTrue(vl)
                            cfservers = self.db.get_server_list(
                                cfsvname).value_string
                            dwservers = self.db.get_server_list(
                                dwsvname).value_string
                            rsservers = self.db.get_server_list(
                                rssvname).value_string
                            self.assertTrue(cfsvname in cfservers)
                            self.assertTrue(dwsvname in dwservers)
                            self.assertTrue(rssvname in rsservers)

                            cfdevices = self.db.get_device_exported_for_class(
                                "NXSConfigServer").value_string
                            dwdevices = self.db.get_device_exported_for_class(
                                "NXSDataWriter").value_string
                            rsdevices = self.db.get_device_exported_for_class(
                                "NXSRecSelector").value_string
                            self.assertTrue(cfdvname in cfdevices)
                            self.assertTrue(dwdvname in dwdevices)
                            self.assertTrue(rsdvname in rsdevices)
                            self.checkDevice(cfdvname)
                            self.checkDevice(dwdvname)
                            self.checkDevice(rsdvname)
                        finally:
                            try:
                                self.stopServer(rssvname)
                            except Exception:
                                pass
                            finally:
                                try:
                                    self.unregisterServer(rssvname, rsdvname)
                                except Exception:
                                    pass
                            try:
                                self.stopServer(cfsvname)
                            except Exception:
                                pass
                            finally:
                                try:
                                    self.unregisterServer(cfsvname, cfdvname)
                                except Exception:
                                    pass
                            try:
                                self.stopServer(dwsvname)
                            except Exception:
                                pass
                            finally:
                                try:
                                    self.unregisterServer(dwsvname, dwdvname)
                                except Exception:
                                    pass
                            setup = nxsetup.SetUp()
                            setup.waitServerNotRunning(
                                cfsvname, cfdvname,  adminproxy, verbose=False,
                                waitforproc=False)
                            setup.waitServerNotRunning(
                                dwsvname, dwdvname, adminproxy, verbose=False,
                                waitforproc=False)
                            setup.waitServerNotRunning(
                                rssvname, rsdvname, adminproxy, verbose=False)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_set_nxsdatawriter_nxsconfigserver(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if self.host in nxsetup.knownHosts.keys():
            dfcnf = nxsetup.knownHosts[self.host]
        else:
            dfcnf = {'beamline': 'nxs',
                     'masterhost': '%s' % self.host,
                     'user': 'tango',
                     'dbname': 'nxsconfig'}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['beamline'] = 'testnxs'
        cnfs[0]['masterhost'] = 'haso000'
        cnfs[1]['beamline'] = 'testnxs2'
        cnfs[1]['masterhost'] = 'hasoo12'
        cnfs[2]['beamline'] = 'test2nxs'
        cnfs[2]['masterhost'] = 'hasoo12'
        cnfs[3]['beamline'] = 'testnxs3'
        cnfs[3]['masterhost'] = 'hasoo000'

        for _ in range(1):
            for cnf in cnfs:
                cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                cfdvname = "%s/nxsconfigserver/%s" % \
                    (cnf['beamline'], cnf["masterhost"])
                dwdvname = "%s/nxsdatawriter/%s" % \
                    (cnf['beamline'], cnf["masterhost"])
                rsdvname = "%s/nxsrecselector/%s" % \
                    (cnf['beamline'], cnf["masterhost"])

                cfservers = self.db.get_server_list(cfsvname).value_string
                dwservers = self.db.get_server_list(dwsvname).value_string
                rsservers = self.db.get_server_list(rssvname).value_string

                dwdevices = self.db.get_device_exported_for_class(
                    "NXSDataWriter").value_string
                cfdevices = self.db.get_device_exported_for_class(
                    "NXSConfigServer").value_string
                rsdevices = self.db.get_device_exported_for_class(
                    "NXSRecSelector").value_string
                skiptest = False
                if cfsvname in cfservers:
                    skiptest = True
                if dwsvname in dwservers:
                    skiptest = True
                if rssvname in rsservers:
                    skiptest = True
                if cfdvname in cfdevices:
                    skiptest = True
                if dwdvname in dwdevices:
                    skiptest = True
                if rsdvname in rsdevices:
                    skiptest = True

                skiptest = skiptest or not CNFSRV or not DTWRITER or not RECSEL

                admin = nxsetup.SetUp().getStarterName(self.host)
                if not admin:
                    skiptest = True
                    adminproxy = None
                else:
                    adminproxy = tango.DeviceProxy(admin)

                commands = [
                    ('nxsetup set NXSDataWriter NXSConfigServer '
                     ' -b %s '
                     ' -m %s '
                     ' -u %s '
                     ' -d %s '
                     % (cnf['beamline'], cnf['masterhost'],
                        cnf['user'], cnf['dbname'])).split(),
                    ('nxsetup set NXSDataWriter NXSConfigServer '
                     ' --beamline %s '
                     ' --masterhost %s '
                     ' --user %s '
                     ' --database %s '
                     % (cnf['beamline'], cnf['masterhost'],
                        cnf['user'], cnf['dbname'])).split(),
                ]
                for cmd in commands:
                    if not skiptest:
                        try:
                            vl, er = self.runtest(cmd)
                            self.assertEqual('', er)
                            self.assertTrue(vl)
                            cfservers = self.db.get_server_list(
                                cfsvname).value_string
                            dwservers = self.db.get_server_list(
                                dwsvname).value_string
                            rsservers = self.db.get_server_list(
                                rssvname).value_string
                            self.assertTrue(cfsvname in cfservers)
                            self.assertTrue(dwsvname in dwservers)
                            self.assertTrue(rssvname not in rsservers)

                            cfdevices = self.db.get_device_exported_for_class(
                                "NXSConfigServer").value_string
                            dwdevices = self.db.get_device_exported_for_class(
                                "NXSDataWriter").value_string
                            rsdevices = self.db.get_device_exported_for_class(
                                "NXSRecSelector").value_string
                            self.assertTrue(cfdvname in cfdevices)
                            self.assertTrue(dwdvname in dwdevices)
                            self.assertTrue(rsdvname not in rsdevices)
                            self.checkDevice(cfdvname)
                            self.checkDevice(dwdvname)
                            # self.checkDevice(rsdvname)

                        finally:
                            try:
                                self.stopServer(cfsvname)
                            except Exception:
                                pass
                            finally:
                                try:
                                    self.unregisterServer(cfsvname, cfdvname)
                                except Exception:
                                    pass
                            try:
                                self.stopServer(dwsvname)
                            except Exception:
                                pass
                            finally:
                                try:
                                    self.unregisterServer(dwsvname, dwdvname)
                                except Exception:
                                    pass
                            setup = nxsetup.SetUp()
                            setup.waitServerNotRunning(
                                cfsvname, cfdvname,  adminproxy, verbose=False,
                                waitforproc=False)
                            setup.waitServerNotRunning(
                                dwsvname, dwdvname, adminproxy, verbose=False)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_set_nxsdatawriter(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if self.host in nxsetup.knownHosts.keys():
            dfcnf = nxsetup.knownHosts[self.host]
        else:
            dfcnf = {'beamline': 'nxs',
                     'masterhost': '%s' % self.host,
                     'user': 'tango',
                     'dbname': 'nxsconfig'}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['beamline'] = 'testnxs'
        cnfs[0]['masterhost'] = 'haso000'
        cnfs[1]['beamline'] = 'testnxs2'
        cnfs[1]['masterhost'] = 'hasoo12'
        cnfs[2]['beamline'] = 'test2nxs'
        cnfs[2]['masterhost'] = 'hasoo12'
        cnfs[3]['beamline'] = 'testnxs3'
        cnfs[3]['masterhost'] = 'hasoo000'

        for _ in range(1):
            for cnf in cnfs:
                cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                cfdvname = "%s/nxsconfigserver/%s" % \
                    (cnf['beamline'], cnf["masterhost"])
                dwdvname = "%s/nxsdatawriter/%s" % \
                    (cnf['beamline'], cnf["masterhost"])
                rsdvname = "%s/nxsrecselector/%s" % \
                    (cnf['beamline'], cnf["masterhost"])

                cfservers = self.db.get_server_list(cfsvname).value_string
                dwservers = self.db.get_server_list(dwsvname).value_string
                rsservers = self.db.get_server_list(rssvname).value_string

                dwdevices = self.db.get_device_exported_for_class(
                    "NXSDataWriter").value_string
                cfdevices = self.db.get_device_exported_for_class(
                    "NXSConfigServer").value_string
                rsdevices = self.db.get_device_exported_for_class(
                    "NXSRecSelector").value_string
                skiptest = False
                if cfsvname in cfservers:
                    skiptest = True
                if dwsvname in dwservers:
                    skiptest = True
                if rssvname in rsservers:
                    skiptest = True
                if cfdvname in cfdevices:
                    skiptest = True
                if dwdvname in dwdevices:
                    skiptest = True
                if rsdvname in rsdevices:
                    skiptest = True

                skiptest = skiptest or not CNFSRV or not DTWRITER or not RECSEL

                admin = nxsetup.SetUp().getStarterName(self.host)
                if not admin:
                    skiptest = True
                    adminproxy = None
                else:
                    adminproxy = tango.DeviceProxy(admin)

                commands = [
                    ('nxsetup set NXSDataWriter '
                     ' -b %s '
                     ' -m %s '
                     ' -u %s '
                     ' -d %s '
                     % (cnf['beamline'], cnf['masterhost'],
                        cnf['user'], cnf['dbname'])).split(),
                    ('nxsetup set NXSDataWriter '
                     ' --beamline %s '
                     ' --masterhost %s '
                     ' --user %s '
                     ' --database %s '
                     % (cnf['beamline'], cnf['masterhost'],
                        cnf['user'], cnf['dbname'])).split(),
                ]
                for cmd in commands:
                    if not skiptest:
                        try:
                            vl, er = self.runtest(cmd)
                            self.assertEqual('', er)
                            self.assertTrue(vl)
                            cfservers = self.db.get_server_list(
                                cfsvname).value_string
                            dwservers = self.db.get_server_list(
                                dwsvname).value_string
                            rsservers = self.db.get_server_list(
                                rssvname).value_string
                            self.assertTrue(cfsvname not in cfservers)
                            self.assertTrue(dwsvname in dwservers)
                            self.assertTrue(rssvname not in rsservers)

                            cfdevices = self.db.get_device_exported_for_class(
                                "NXSConfigServer").value_string
                            dwdevices = self.db.get_device_exported_for_class(
                                "NXSDataWriter").value_string
                            rsdevices = self.db.get_device_exported_for_class(
                                "NXSRecSelector").value_string
                            self.assertTrue(cfdvname not in cfdevices)
                            self.assertTrue(dwdvname in dwdevices)
                            self.assertTrue(rsdvname not in rsdevices)
                            self.checkDevice(dwdvname)
                        finally:
                            try:
                                self.stopServer(dwsvname)
                            except Exception:
                                pass
                            finally:
                                try:
                                    self.unregisterServer(dwsvname, dwdvname)
                                except Exception:
                                    pass
                            setup = nxsetup.SetUp()
                            setup.waitServerNotRunning(
                                dwsvname, dwdvname, adminproxy, verbose=False)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_set_nxsrecselector(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if self.host in nxsetup.knownHosts.keys():
            dfcnf = nxsetup.knownHosts[self.host]
        else:
            dfcnf = {'beamline': 'nxs',
                     'masterhost': '%s' % self.host,
                     'user': 'tango',
                     'dbname': 'nxsconfig'}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['beamline'] = 'testnxs'
        cnfs[0]['masterhost'] = 'haso000'
        cnfs[1]['beamline'] = 'testnxs2'
        cnfs[1]['masterhost'] = 'hasoo12'
        cnfs[2]['beamline'] = 'test2nxs'
        cnfs[2]['masterhost'] = 'hasoo12'
        cnfs[3]['beamline'] = 'testnxs3'
        cnfs[3]['masterhost'] = 'hasoo000'
        for _ in range(1):
            for cnf in cnfs:
                cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                cfdvname = "%s/nxsconfigserver/%s" % \
                    (cnf['beamline'], cnf["masterhost"])
                dwdvname = "%s/nxsdatawriter/%s" % \
                    (cnf['beamline'], cnf["masterhost"])
                rsdvname = "%s/nxsrecselector/%s" % \
                    (cnf['beamline'], cnf["masterhost"])

                cfservers = self.db.get_server_list(cfsvname).value_string
                dwservers = self.db.get_server_list(dwsvname).value_string
                rsservers = self.db.get_server_list(rssvname).value_string

                dwdevices = self.db.get_device_exported_for_class(
                    "NXSDataWriter").value_string
                cfdevices = self.db.get_device_exported_for_class(
                    "NXSConfigServer").value_string
                rsdevices = self.db.get_device_exported_for_class(
                    "NXSRecSelector").value_string
                skiptest = False
                if cfsvname in cfservers:
                    skiptest = True
                if dwsvname in dwservers:
                    skiptest = True
                if rssvname in rsservers:
                    skiptest = True
                if cfdvname in cfdevices:
                    skiptest = True
                if dwdvname in dwdevices:
                    skiptest = True
                if rsdvname in rsdevices:
                    skiptest = True

                skiptest = skiptest or not CNFSRV or not DTWRITER or not RECSEL

                admin = nxsetup.SetUp().getStarterName(self.host)
                if not admin:
                    skiptest = True
                    adminproxy = None
                else:
                    adminproxy = tango.DeviceProxy(admin)

                dwcfsvs = ['NXSDataWriter', 'NXSConfigServer']
                rssvs = ['NXSRecSelector']
                commands = [
                    ('nxsetup set '
                     ' -b %s '
                     ' -m %s '
                     ' -u %s '
                     ' -d %s '
                     % (cnf['beamline'], cnf['masterhost'],
                        cnf['user'], cnf['dbname'])).split(),
                    ('nxsetup set '
                     ' --beamline %s '
                     ' --masterhost %s '
                     ' --user %s '
                     ' --database %s '
                     % (cnf['beamline'], cnf['masterhost'],
                        cnf['user'], cnf['dbname'])).split(),
                ]
                for cmd in commands:
                    if not skiptest:
                        try:
                            acmd = list(cmd)
                            acmd.extend(dwcfsvs)
                            vl, er = self.runtest(acmd)

                            cfservers = self.db.get_server_list(
                                cfsvname).value_string
                            dwservers = self.db.get_server_list(
                                dwsvname).value_string
                            rsservers = self.db.get_server_list(
                                rssvname).value_string
                            self.assertTrue(cfsvname in cfservers)
                            self.assertTrue(dwsvname in dwservers)
                            self.assertTrue(rssvname not in rsservers)

                            cfdevices = self.db.get_device_exported_for_class(
                                "NXSConfigServer").value_string
                            dwdevices = self.db.get_device_exported_for_class(
                                "NXSDataWriter").value_string
                            rsdevices = self.db.get_device_exported_for_class(
                                "NXSRecSelector").value_string
                            self.assertTrue(cfdvname in cfdevices)
                            self.assertTrue(dwdvname in dwdevices)
                            self.assertTrue(rsdvname not in rsdevices)
                            self.checkDevice(cfdvname)
                            self.checkDevice(dwdvname)
                            # self.checkDevice(rsdvname)

                            acmd = list(cmd)
                            acmd.extend(rssvs)
                            vl, er = self.runtest(acmd)
                            self.assertEqual('', er)
                            self.assertTrue(vl)
                            cfservers = self.db.get_server_list(
                                cfsvname).value_string
                            dwservers = self.db.get_server_list(
                                dwsvname).value_string
                            rsservers = self.db.get_server_list(
                                rssvname).value_string
                            self.assertTrue(cfsvname in cfservers)
                            self.assertTrue(dwsvname in dwservers)
                            self.assertTrue(rssvname in rsservers)

                            cfdevices = self.db.get_device_exported_for_class(
                                "NXSConfigServer").value_string
                            dwdevices = self.db.get_device_exported_for_class(
                                "NXSDataWriter").value_string
                            rsdevices = self.db.get_device_exported_for_class(
                                "NXSRecSelector").value_string
                            self.assertTrue(cfdvname in cfdevices)
                            self.assertTrue(dwdvname in dwdevices)
                            self.assertTrue(rsdvname in rsdevices)
                            self.checkDevice(cfdvname)
                            self.checkDevice(dwdvname)
                            self.checkDevice(rsdvname)

                        finally:
                            try:
                                self.stopServer(rssvname)
                            except Exception:
                                pass
                            finally:
                                try:
                                    self.unregisterServer(rssvname, rsdvname)
                                except Exception:
                                    pass
                            try:
                                self.stopServer(cfsvname)
                            except Exception:
                                pass
                            finally:
                                try:
                                    self.unregisterServer(cfsvname, cfdvname)
                                except Exception:
                                    pass
                            try:
                                self.stopServer(dwsvname)
                            except Exception:
                                pass
                            finally:
                                try:
                                    self.unregisterServer(dwsvname, dwdvname)
                                except Exception:
                                    pass
                            setup = nxsetup.SetUp()
                            setup.waitServerNotRunning(
                                cfsvname, cfdvname,  adminproxy, verbose=False,
                                waitforproc=False)
                            setup.waitServerNotRunning(
                                dwsvname, dwdvname, adminproxy, verbose=False,
                                waitforproc=False)
                            setup.waitServerNotRunning(
                                rssvname, rsdvname, adminproxy, verbose=False)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_set_stop_start_restart(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if self.host in nxsetup.knownHosts.keys():
            dfcnf = nxsetup.knownHosts[self.host]
        else:
            dfcnf = {'beamline': 'nxs',
                     'masterhost': '%s' % self.host,
                     'user': 'tango',
                     'dbname': 'nxsconfig'}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['beamline'] = 'testnxs'
        cnfs[0]['masterhost'] = 'haso000'
        cnfs[1]['beamline'] = 'testnxs2'
        cnfs[1]['masterhost'] = 'hasoo12'
        cnfs[2]['beamline'] = 'test2nxs'
        cnfs[2]['masterhost'] = 'hasooo12'
        cnfs[3]['beamline'] = 'testnxs3'
        cnfs[3]['masterhost'] = 'hasoo000'

        for cnf in cnfs:
            # print(cnf)
            cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
            dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
            rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
            cfdvname = "%s/nxsconfigserver/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            dwdvname = "%s/nxsdatawriter/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            rsdvname = "%s/nxsrecselector/%s" % \
                (cnf['beamline'], cnf["masterhost"])

            cfservers = self.db.get_server_list(cfsvname).value_string
            dwservers = self.db.get_server_list(dwsvname).value_string
            rsservers = self.db.get_server_list(rssvname).value_string

            dwdevices = self.db.get_device_exported_for_class(
                "NXSDataWriter").value_string
            cfdevices = self.db.get_device_exported_for_class(
                "NXSConfigServer").value_string
            rsdevices = self.db.get_device_exported_for_class(
                "NXSRecSelector").value_string
            skiptest = False
            if cfsvname in cfservers:
                skiptest = True
            if dwsvname in dwservers:
                skiptest = True
            if rssvname in rsservers:
                skiptest = True
            if cfdvname in cfdevices:
                skiptest = True
            if dwdvname in dwdevices:
                skiptest = True
            if rsdvname in rsdevices:
                skiptest = True
            acfdevices = self.db.get_device_exported_for_class(
                "NXSConfigServer").value_string
            adwdevices = self.db.get_device_exported_for_class(
                "NXSDataWriter").value_string
            arsdevices = self.db.get_device_exported_for_class(
                "NXSRecSelector").value_string
            if acfdevices:
                skiptest = True
            if adwdevices:
                skiptest = True
            if arsdevices:
                skiptest = True

            skiptest = skiptest or not CNFSRV or not DTWRITER or not RECSEL
            admin = nxsetup.SetUp().getStarterName(self.host)
            if not admin:
                skiptest = True
                adminproxy = None
            else:
                adminproxy = tango.DeviceProxy(admin)

        skiptests = skiptest

        if not skiptest:
            rservers = []
            try:
                for cnf in cnfs:
                    commands = [
                        ('nxsetup set '
                         ' -b %s '
                         ' -m %s '
                         ' -u %s '
                         ' -d %s '
                         % (cnf['beamline'], cnf['masterhost'],
                            cnf['user'], cnf['dbname'])).split(),
                    ]
                    cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                    dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                    rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                    cfdvname = "%s/nxsconfigserver/%s" % \
                               (cnf['beamline'], cnf["masterhost"])
                    dwdvname = "%s/nxsdatawriter/%s" % \
                               (cnf['beamline'], cnf["masterhost"])
                    rsdvname = "%s/nxsrecselector/%s" % \
                               (cnf['beamline'], cnf["masterhost"])

                    for cmd in commands:
                        try:

                            rservers.append((cfsvname, cfdvname))
                            rservers.append((dwsvname, dwdvname))
                            rservers.append((rssvname, rsdvname))
                            vl, er = self.runtest(cmd)
                            self.assertEqual('', er)
                            self.assertTrue(vl)
                            cfservers = self.db.get_server_list(
                                cfsvname).value_string
                            dwservers = self.db.get_server_list(
                                dwsvname).value_string
                            rsservers = self.db.get_server_list(
                                rssvname).value_string
                            self.assertTrue(cfsvname in cfservers)
                            self.assertTrue(dwsvname in dwservers)
                            self.assertTrue(rssvname in rsservers)

                            cfdevices = self.db.get_device_exported_for_class(
                                "NXSConfigServer").value_string
                            dwdevices = self.db.get_device_exported_for_class(
                                "NXSDataWriter").value_string
                            rsdevices = self.db.get_device_exported_for_class(
                                "NXSRecSelector").value_string
                            self.assertTrue(cfdvname in cfdevices)
                            self.assertTrue(dwdvname in dwdevices)
                            self.assertTrue(rsdvname in rsdevices)
                            self.checkDevice(cfdvname)
                            self.checkDevice(dwdvname)
                            self.checkDevice(rsdvname)
                        except Exception as e:
                            print(str(e))
                            skiptests = True
                # time.sleep(5)
                if not skiptests:
                    print("\nTEST STOP")
                    vl, er = self.runtest(["nxsetup", "stop"])
                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    for cnf in cnfs:
                        cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                        dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                        rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                        cfdvname = "%s/nxsconfigserver/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])
                        dwdvname = "%s/nxsdatawriter/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])
                        rsdvname = "%s/nxsrecselector/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])

                        cfservers = self.db.get_server_list(
                            cfsvname).value_string
                        dwservers = self.db.get_server_list(
                            dwsvname).value_string
                        rsservers = self.db.get_server_list(
                            rssvname).value_string
                        self.assertTrue(cfsvname in cfservers)
                        self.assertTrue(dwsvname in dwservers)
                        self.assertTrue(rssvname in rsservers)

                        cfdevices = self.db.get_device_exported_for_class(
                            "NXSConfigServer").value_string
                        dwdevices = self.db.get_device_exported_for_class(
                            "NXSDataWriter").value_string
                        rsdevices = self.db.get_device_exported_for_class(
                            "NXSRecSelector").value_string
                        self.assertTrue(cfdvname not in cfdevices)
                        self.assertTrue(dwdvname not in dwdevices)
                        self.assertTrue(rsdvname not in rsdevices)
                    print("\nTEST START")
                    vl, er = self.runtest(["nxsetup", "start"])
                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    for cnf in cnfs:
                        # print(cnf)
                        cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                        dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                        rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                        cfdvname = "%s/nxsconfigserver/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])
                        dwdvname = "%s/nxsdatawriter/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])
                        rsdvname = "%s/nxsrecselector/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])

                        cfservers = self.db.get_server_list(
                            cfsvname).value_string
                        dwservers = self.db.get_server_list(
                            dwsvname).value_string
                        rsservers = self.db.get_server_list(
                            rssvname).value_string
                        self.assertTrue(cfsvname in cfservers)
                        self.assertTrue(dwsvname in dwservers)
                        self.assertTrue(rssvname in rsservers)

                        cfdevices = self.db.get_device_exported_for_class(
                            "NXSConfigServer").value_string
                        dwdevices = self.db.get_device_exported_for_class(
                            "NXSDataWriter").value_string
                        rsdevices = self.db.get_device_exported_for_class(
                            "NXSRecSelector").value_string
                        self.assertTrue(cfdvname in cfdevices)
                        self.assertTrue(dwdvname in dwdevices)
                        self.assertTrue(rsdvname in rsdevices)
                        self.checkDevice(cfdvname)
                        self.checkDevice(dwdvname)
                        self.checkDevice(rsdvname)
                    print("\nTEST RESTART")
                    svpids = {}
                    for sv, dv in rservers:
                        svpids[sv] = self.serverPid(sv)
                    vl, er = self.runtest(["nxsetup", "restart"])
                    self.assertEqual('', er)
                    for sv, pid in svpids.items():
                        self.assertTrue(self.serverPid(sv) != pid)
                    self.assertTrue(vl)
                    for cnf in cnfs:
                        cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                        dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                        rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                        cfdvname = "%s/nxsconfigserver/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])
                        dwdvname = "%s/nxsdatawriter/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])
                        rsdvname = "%s/nxsrecselector/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])

                        cfservers = self.db.get_server_list(
                            cfsvname).value_string
                        dwservers = self.db.get_server_list(
                            dwsvname).value_string
                        rsservers = self.db.get_server_list(
                            rssvname).value_string
                        self.assertTrue(cfsvname in cfservers)
                        self.assertTrue(dwsvname in dwservers)
                        self.assertTrue(rssvname in rsservers)

                        cfdevices = self.db.get_device_exported_for_class(
                            "NXSConfigServer").value_string
                        dwdevices = self.db.get_device_exported_for_class(
                            "NXSDataWriter").value_string
                        rsdevices = self.db.get_device_exported_for_class(
                            "NXSRecSelector").value_string
                        self.assertTrue(cfdvname in cfdevices)
                        self.assertTrue(dwdvname in dwdevices)
                        self.assertTrue(rsdvname in rsdevices)
                        self.checkDevice(cfdvname)
                        self.checkDevice(dwdvname)
                        self.checkDevice(rsdvname)
            finally:
                try:
                    if not skiptest:
                        vl, er = self.runtest(["nxsetup", "stop"])
                except Exception:
                    pass
                # print(rservers)
                for svname, dvname in set(rservers):
                    try:
                        self.stopServer(svname)
                    except Exception:
                        # print(str(e))
                        pass
                    try:
                        self.unregisterServer(svname, dvname)
                    except Exception:
                        # print(str(e))
                        pass
                setup = nxsetup.SetUp()
                sservers = list(set(rservers))
                waitforproc = False
                for svname, dvname in sservers:
                    if dvname == sservers[-1][1]:
                        waitforproc = True
                    setup.waitServerNotRunning(
                        svname, dvname, adminproxy, verbose=False,
                        waitforproc=waitforproc)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_set_stop_start_restart_all(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if self.host in nxsetup.knownHosts.keys():
            dfcnf = nxsetup.knownHosts[self.host]
        else:
            dfcnf = {'beamline': 'nxs',
                     'masterhost': '%s' % self.host,
                     'user': 'tango',
                     'dbname': 'nxsconfig'}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['beamline'] = 'testnxs'
        cnfs[0]['masterhost'] = 'haso000'
        cnfs[1]['beamline'] = 'testnxs2'
        cnfs[1]['masterhost'] = 'hasoo12'
        cnfs[2]['beamline'] = 'test2nxs'
        cnfs[2]['masterhost'] = 'hasooo12'
        cnfs[3]['beamline'] = 'testnxs3'
        cnfs[3]['masterhost'] = 'hasoo000'

        for cnf in cnfs:
            # print(cnf)
            cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
            dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
            rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
            cfdvname = "%s/nxsconfigserver/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            dwdvname = "%s/nxsdatawriter/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            rsdvname = "%s/nxsrecselector/%s" % \
                (cnf['beamline'], cnf["masterhost"])

            cfservers = self.db.get_server_list(cfsvname).value_string
            dwservers = self.db.get_server_list(dwsvname).value_string
            rsservers = self.db.get_server_list(rssvname).value_string

            dwdevices = self.db.get_device_exported_for_class(
                "NXSDataWriter").value_string
            cfdevices = self.db.get_device_exported_for_class(
                "NXSConfigServer").value_string
            rsdevices = self.db.get_device_exported_for_class(
                "NXSRecSelector").value_string
            skiptest = False
            if cfsvname in cfservers:
                skiptest = True
            if dwsvname in dwservers:
                skiptest = True
            if rssvname in rsservers:
                skiptest = True
            if cfdvname in cfdevices:
                skiptest = True
            if dwdvname in dwdevices:
                skiptest = True
            if rsdvname in rsdevices:
                skiptest = True
            acfdevices = self.db.get_device_exported_for_class(
                "NXSConfigServer").value_string
            adwdevices = self.db.get_device_exported_for_class(
                "NXSDataWriter").value_string
            arsdevices = self.db.get_device_exported_for_class(
                "NXSRecSelector").value_string
            if acfdevices:
                skiptest = True
            if adwdevices:
                skiptest = True
            if arsdevices:
                skiptest = True

            skiptest = skiptest or not CNFSRV or not DTWRITER or not RECSEL
            admin = nxsetup.SetUp().getStarterName(self.host)
            if not admin:
                skiptest = True
                adminproxy = None
            else:
                adminproxy = tango.DeviceProxy(admin)

        skiptests = skiptest

        if not skiptest:
            rservers = []
            try:
                for cnf in cnfs:
                    commands = [
                        ('nxsetup set '
                         ' -b %s '
                         ' -m %s '
                         ' -u %s '
                         ' -d %s '
                         % (cnf['beamline'], cnf['masterhost'],
                            cnf['user'], cnf['dbname'])).split(),
                    ]
                    cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                    dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                    rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                    cfdvname = "%s/nxsconfigserver/%s" % \
                               (cnf['beamline'], cnf["masterhost"])
                    dwdvname = "%s/nxsdatawriter/%s" % \
                               (cnf['beamline'], cnf["masterhost"])
                    rsdvname = "%s/nxsrecselector/%s" % \
                               (cnf['beamline'], cnf["masterhost"])

                    for cmd in commands:
                        try:

                            rservers.append((cfsvname, cfdvname))
                            rservers.append((dwsvname, dwdvname))
                            rservers.append((rssvname, rsdvname))
                            vl, er = self.runtest(cmd)
                            self.assertEqual('', er)
                            self.assertTrue(vl)
                            cfservers = self.db.get_server_list(
                                cfsvname).value_string
                            dwservers = self.db.get_server_list(
                                dwsvname).value_string
                            rsservers = self.db.get_server_list(
                                rssvname).value_string
                            self.assertTrue(cfsvname in cfservers)
                            self.assertTrue(dwsvname in dwservers)
                            self.assertTrue(rssvname in rsservers)

                            cfdevices = self.db.get_device_exported_for_class(
                                "NXSConfigServer").value_string
                            dwdevices = self.db.get_device_exported_for_class(
                                "NXSDataWriter").value_string
                            rsdevices = self.db.get_device_exported_for_class(
                                "NXSRecSelector").value_string
                            self.assertTrue(cfdvname in cfdevices)
                            self.assertTrue(dwdvname in dwdevices)
                            self.assertTrue(rsdvname in rsdevices)
                            self.checkDevice(cfdvname)
                            self.checkDevice(dwdvname)
                            self.checkDevice(rsdvname)
                        except Exception as e:
                            print(str(e))
                            skiptests = True
                # time.sleep(5)
                if not skiptests:
                    print("\nTEST STOP")
                    vl, er = self.runtest(
                        ["nxsetup", "stop",
                         "NXSDataWriter", "NXSConfigServer", "NXSRecSelector"])
                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    for cnf in cnfs:
                        cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                        dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                        rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                        cfdvname = "%s/nxsconfigserver/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])
                        dwdvname = "%s/nxsdatawriter/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])
                        rsdvname = "%s/nxsrecselector/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])

                        cfservers = self.db.get_server_list(
                            cfsvname).value_string
                        dwservers = self.db.get_server_list(
                            dwsvname).value_string
                        rsservers = self.db.get_server_list(
                            rssvname).value_string
                        self.assertTrue(cfsvname in cfservers)
                        self.assertTrue(dwsvname in dwservers)
                        self.assertTrue(rssvname in rsservers)

                        cfdevices = self.db.get_device_exported_for_class(
                            "NXSConfigServer").value_string
                        dwdevices = self.db.get_device_exported_for_class(
                            "NXSDataWriter").value_string
                        rsdevices = self.db.get_device_exported_for_class(
                            "NXSRecSelector").value_string
                        self.assertTrue(cfdvname not in cfdevices)
                        self.assertTrue(dwdvname not in dwdevices)
                        self.assertTrue(rsdvname not in rsdevices)
                    print("\nTEST START")
                    vl, er = self.runtest(
                        ["nxsetup", "start",
                         "NXSDataWriter", "NXSConfigServer", "NXSRecSelector"])
                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    for cnf in cnfs:
                        # print(cnf)
                        cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                        dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                        rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                        cfdvname = "%s/nxsconfigserver/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])
                        dwdvname = "%s/nxsdatawriter/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])
                        rsdvname = "%s/nxsrecselector/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])

                        cfservers = self.db.get_server_list(
                            cfsvname).value_string
                        dwservers = self.db.get_server_list(
                            dwsvname).value_string
                        rsservers = self.db.get_server_list(
                            rssvname).value_string
                        self.assertTrue(cfsvname in cfservers)
                        self.assertTrue(dwsvname in dwservers)
                        self.assertTrue(rssvname in rsservers)

                        cfdevices = self.db.get_device_exported_for_class(
                            "NXSConfigServer").value_string
                        dwdevices = self.db.get_device_exported_for_class(
                            "NXSDataWriter").value_string
                        rsdevices = self.db.get_device_exported_for_class(
                            "NXSRecSelector").value_string
                        self.assertTrue(cfdvname in cfdevices)
                        self.assertTrue(dwdvname in dwdevices)
                        self.assertTrue(rsdvname in rsdevices)
                        self.checkDevice(cfdvname)
                        self.checkDevice(dwdvname)
                        self.checkDevice(rsdvname)
                    print("\nTEST RESTART")
                    svpids = {}
                    for sv, dv in rservers:
                        svpids[sv] = self.serverPid(sv)
                    vl, er = self.runtest(
                        ["nxsetup", "restart",
                         "NXSDataWriter", "NXSConfigServer", "NXSRecSelector"])
                    self.assertEqual('', er)
                    for sv, pid in svpids.items():
                        self.assertTrue(self.serverPid(sv) != pid)
                    self.assertTrue(vl)
                    for cnf in cnfs:
                        cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                        dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                        rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                        cfdvname = "%s/nxsconfigserver/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])
                        dwdvname = "%s/nxsdatawriter/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])
                        rsdvname = "%s/nxsrecselector/%s" % \
                                   (cnf['beamline'], cnf["masterhost"])

                        cfservers = self.db.get_server_list(
                            cfsvname).value_string
                        dwservers = self.db.get_server_list(
                            dwsvname).value_string
                        rsservers = self.db.get_server_list(
                            rssvname).value_string
                        self.assertTrue(cfsvname in cfservers)
                        self.assertTrue(dwsvname in dwservers)
                        self.assertTrue(rssvname in rsservers)

                        cfdevices = self.db.get_device_exported_for_class(
                            "NXSConfigServer").value_string
                        dwdevices = self.db.get_device_exported_for_class(
                            "NXSDataWriter").value_string
                        rsdevices = self.db.get_device_exported_for_class(
                            "NXSRecSelector").value_string
                        self.assertTrue(cfdvname in cfdevices)
                        self.assertTrue(dwdvname in dwdevices)
                        self.assertTrue(rsdvname in rsdevices)
                        self.checkDevice(cfdvname)
                        self.checkDevice(dwdvname)
                        self.checkDevice(rsdvname)
            finally:
                try:
                    if not skiptest:
                        vl, er = self.runtest(["nxsetup", "stop"])
                except Exception:
                    pass
                # print(rservers)
                for svname, dvname in set(rservers):
                    try:
                        self.stopServer(svname)
                    except Exception:
                        # print(str(e))
                        pass
                    try:
                        self.unregisterServer(svname, dvname)
                    except Exception:
                        # print(str(e))
                        pass
                setup = nxsetup.SetUp()
                sservers = list(set(rservers))
                waitforproc = False
                for svname, dvname in sservers:
                    if dvname == sservers[-1][1]:
                        waitforproc = True
                    setup.waitServerNotRunning(
                        svname, dvname, adminproxy, verbose=False,
                        waitforproc=waitforproc)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_server_set_stop_start_restart(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if self.host in nxsetup.knownHosts.keys():
            dfcnf = nxsetup.knownHosts[self.host]
        else:
            dfcnf = {'beamline': 'nxs',
                     'masterhost': '%s' % self.host,
                     'user': 'tango',
                     'dbname': 'nxsconfig'}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['beamline'] = 'testnxs'
        cnfs[0]['masterhost'] = 'haso000'
        cnfs[1]['beamline'] = 'testnxs2'
        cnfs[1]['masterhost'] = 'hasoo12'
        cnfs[2]['beamline'] = 'test2nxs'
        cnfs[2]['masterhost'] = 'hasooo12'
        cnfs[3]['beamline'] = 'testnxs3'
        cnfs[3]['masterhost'] = 'hasoo000'

        for cnf in cnfs:
            # print(cnf)
            cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
            dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
            rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
            cfdvname = "%s/nxsconfigserver/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            dwdvname = "%s/nxsdatawriter/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            rsdvname = "%s/nxsrecselector/%s" % \
                (cnf['beamline'], cnf["masterhost"])

            cfservers = self.db.get_server_list(cfsvname).value_string
            dwservers = self.db.get_server_list(dwsvname).value_string
            rsservers = self.db.get_server_list(rssvname).value_string

            dwdevices = self.db.get_device_exported_for_class(
                "NXSDataWriter").value_string
            cfdevices = self.db.get_device_exported_for_class(
                "NXSConfigServer").value_string
            rsdevices = self.db.get_device_exported_for_class(
                "NXSRecSelector").value_string
            skiptest = False
            if cfsvname in cfservers:
                skiptest = True
            if dwsvname in dwservers:
                skiptest = True
            if rssvname in rsservers:
                skiptest = True
            if cfdvname in cfdevices:
                skiptest = True
            if dwdvname in dwdevices:
                skiptest = True
            if rsdvname in rsdevices:
                skiptest = True
            acfdevices = self.db.get_device_exported_for_class(
                "NXSConfigServer").value_string
            adwdevices = self.db.get_device_exported_for_class(
                "NXSDataWriter").value_string
            arsdevices = self.db.get_device_exported_for_class(
                "NXSRecSelector").value_string
            if acfdevices:
                skiptest = True
            if adwdevices:
                skiptest = True
            if arsdevices:
                skiptest = True

            skiptest = skiptest or not CNFSRV or not DTWRITER or not RECSEL
            admin = nxsetup.SetUp().getStarterName(self.host)
            if not admin:
                skiptest = True
                adminproxy = None
            else:
                adminproxy = tango.DeviceProxy(admin)

        skiptests = skiptest

        if not skiptest:
            rservers = []
            try:
                for cnf in cnfs:
                    commands = [
                        ('nxsetup set '
                         ' -b %s '
                         ' -m %s '
                         ' -u %s '
                         ' -d %s '
                         % (cnf['beamline'], cnf['masterhost'],
                            cnf['user'], cnf['dbname'])).split(),
                    ]
                    cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                    dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                    rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                    cfdvname = "%s/nxsconfigserver/%s" % \
                               (cnf['beamline'], cnf["masterhost"])
                    dwdvname = "%s/nxsdatawriter/%s" % \
                               (cnf['beamline'], cnf["masterhost"])
                    rsdvname = "%s/nxsrecselector/%s" % \
                               (cnf['beamline'], cnf["masterhost"])

                    for cmd in commands:
                        try:

                            rservers.append((cfsvname, cfdvname))
                            rservers.append((dwsvname, dwdvname))
                            rservers.append((rssvname, rsdvname))
                            vl, er = self.runtest(cmd)
                            self.assertEqual('', er)
                            self.assertTrue(vl)
                            cfservers = self.db.get_server_list(
                                cfsvname).value_string
                            dwservers = self.db.get_server_list(
                                dwsvname).value_string
                            rsservers = self.db.get_server_list(
                                rssvname).value_string
                            self.assertTrue(cfsvname in cfservers)
                            self.assertTrue(dwsvname in dwservers)
                            self.assertTrue(rssvname in rsservers)

                            cfdevices = self.db.get_device_exported_for_class(
                                "NXSConfigServer").value_string
                            dwdevices = self.db.get_device_exported_for_class(
                                "NXSDataWriter").value_string
                            rsdevices = self.db.get_device_exported_for_class(
                                "NXSRecSelector").value_string
                            self.assertTrue(cfdvname in cfdevices)
                            self.assertTrue(dwdvname in dwdevices)
                            self.assertTrue(rsdvname in rsdevices)
                            self.checkDevice(cfdvname)
                            self.checkDevice(dwdvname)
                            self.checkDevice(rsdvname)
                        except Exception as e:
                            print(str(e))
                            skiptests = True
                # time.sleep(5)
                if not skiptests:
                    print("\nTEST STOP")
                    nservers = ["NXSConfigServer",
                                "NXSDataWriter",
                                "NXSRecSelector"]
                    slservers = []
                    for nsv in nservers:
                        vl, er = self.runtest(["nxsetup", "stop", nsv])
                        slservers.append(nsv)
                        self.assertEqual('', er)
                        self.assertTrue(vl)
                        for cnf in cnfs:
                            for slsv in nservers:
                                svname = "%s/%s" % (slsv, cnf["masterhost"])
                                dvname = "%s/%s/%s" % \
                                         (cnf['beamline'],
                                          slsv.lower(), cnf["masterhost"])

                                servers = self.db.get_server_list(
                                    svname).value_string
                                self.assertTrue(svname in servers)

                                devices = self.db.\
                                    get_device_exported_for_class(
                                        slsv).value_string
                                if slsv in slservers:
                                    self.assertTrue(dvname not in devices)
                                else:
                                    self.assertTrue(dvname in devices)
                    print("\nTEST START")
                    slservers = []
                    for nsv in nservers:
                        slservers.append(nsv)
                        vl, er = self.runtest(["nxsetup", "start", nsv])
                        self.assertEqual('', er)
                        self.assertTrue(vl)
                        for cnf in cnfs:
                            # print(cnf)
                            for slsv in nservers:
                                svname = "%s/%s" % (slsv, cnf["masterhost"])
                                dvname = "%s/%s/%s" % \
                                         (cnf['beamline'],
                                          slsv.lower(), cnf["masterhost"])

                                servers = self.db.get_server_list(
                                    svname).value_string
                                self.assertTrue(svname in servers)

                                devices = self.db.\
                                    get_device_exported_for_class(
                                        slsv).value_string

                                if slsv in slservers:
                                    self.assertTrue(dvname in devices)
                                    self.checkDevice(dvname)
                                else:
                                    self.assertTrue(dvname not in devices)
                    print("\nTEST RESTART")
                    slservers = []
                    for nsv in nservers:
                        slservers.append(nsv)
                        svpids = {}
                        for sv, dv in rservers:
                            if sv.startswith(nsv):
                                svpids[sv] = self.serverPid(sv)
                        vl, er = self.runtest(["nxsetup", "restart", nsv])
                        for sv, pid in svpids.items():
                            self.assertTrue(self.serverPid(sv) != pid)
                        self.assertEqual('', er)
                        self.assertTrue(vl)
                        for cnf in cnfs:
                            # print(cnf)
                            for slsv in nservers:
                                svname = "%s/%s" % (slsv, cnf["masterhost"])
                                dvname = "%s/%s/%s" % \
                                    (cnf['beamline'],
                                     slsv.lower(), cnf["masterhost"])

                                servers = self.db.get_server_list(
                                    svname).value_string
                                self.assertTrue(svname in servers)

                                devices = self.db.\
                                    get_device_exported_for_class(
                                        slsv).value_string

                                self.assertTrue(dvname in devices)
                                self.checkDevice(dvname)
            finally:
                try:
                    if not skiptest:
                        vl, er = self.runtest(["nxsetup", "stop"])
                except Exception:
                    pass
                # print(rservers)
                for svname, dvname in set(rservers):
                    try:
                        self.stopServer(svname)
                    except Exception:
                        # print(str(e))
                        pass
                    try:
                        self.unregisterServer(svname, dvname)
                    except Exception:
                        # print(str(e))
                        pass
                setup = nxsetup.SetUp()
                sservers = list(set(rservers))
                waitforproc = False
                for svname, dvname in sservers:
                    if dvname == sservers[-1][1]:
                        waitforproc = True
                    setup.waitServerNotRunning(
                        svname, dvname, adminproxy, verbose=False,
                        waitforproc=waitforproc)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_instance_set_stop_start_restart(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if self.host in nxsetup.knownHosts.keys():
            dfcnf = nxsetup.knownHosts[self.host]
        else:
            dfcnf = {'beamline': 'nxs',
                     'masterhost': '%s' % self.host,
                     'user': 'tango',
                     'dbname': 'nxsconfig'}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['beamline'] = 'testnxs'
        cnfs[0]['masterhost'] = 'haso000'
        cnfs[1]['beamline'] = 'testnxs2'
        cnfs[1]['masterhost'] = 'hasoo12'
        cnfs[2]['beamline'] = 'test2nxs'
        cnfs[2]['masterhost'] = 'hasooo12'
        cnfs[3]['beamline'] = 'testnxs3'
        cnfs[3]['masterhost'] = 'hasoo000'

        for cnf in cnfs:
            # print(cnf)
            cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
            dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
            rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
            cfdvname = "%s/nxsconfigserver/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            dwdvname = "%s/nxsdatawriter/%s" % \
                (cnf['beamline'], cnf["masterhost"])
            rsdvname = "%s/nxsrecselector/%s" % \
                (cnf['beamline'], cnf["masterhost"])

            cfservers = self.db.get_server_list(cfsvname).value_string
            dwservers = self.db.get_server_list(dwsvname).value_string
            rsservers = self.db.get_server_list(rssvname).value_string

            dwdevices = self.db.get_device_exported_for_class(
                "NXSDataWriter").value_string
            cfdevices = self.db.get_device_exported_for_class(
                "NXSConfigServer").value_string
            rsdevices = self.db.get_device_exported_for_class(
                "NXSRecSelector").value_string
            skiptest = False
            if cfsvname in cfservers:
                skiptest = True
            if dwsvname in dwservers:
                skiptest = True
            if rssvname in rsservers:
                skiptest = True
            if cfdvname in cfdevices:
                skiptest = True
            if dwdvname in dwdevices:
                skiptest = True
            if rsdvname in rsdevices:
                skiptest = True

            skiptest = skiptest or not CNFSRV or not DTWRITER or not RECSEL
            admin = nxsetup.SetUp().getStarterName(self.host)
            if not admin:
                skiptest = True
                adminproxy = None
            else:
                adminproxy = tango.DeviceProxy(admin)

        skiptests = skiptest

        if not skiptest:
            rservers = []
            try:
                for cnf in cnfs:
                    commands = [
                        ('nxsetup set '
                         ' -b %s '
                         ' -m %s '
                         ' -u %s '
                         ' -d %s '
                         % (cnf['beamline'], cnf['masterhost'],
                            cnf['user'], cnf['dbname'])).split(),
                    ]
                    cfsvname = "NXSConfigServer/%s" % cnf["masterhost"]
                    dwsvname = "NXSDataWriter/%s" % cnf["masterhost"]
                    rssvname = "NXSRecSelector/%s" % cnf["masterhost"]
                    cfdvname = "%s/nxsconfigserver/%s" % \
                               (cnf['beamline'], cnf["masterhost"])
                    dwdvname = "%s/nxsdatawriter/%s" % \
                               (cnf['beamline'], cnf["masterhost"])
                    rsdvname = "%s/nxsrecselector/%s" % \
                               (cnf['beamline'], cnf["masterhost"])

                    for cmd in commands:
                        try:

                            rservers.append((cfsvname, cfdvname))
                            rservers.append((dwsvname, dwdvname))
                            rservers.append((rssvname, rsdvname))
                            vl, er = self.runtest(cmd)
                            self.assertEqual('', er)
                            self.assertTrue(vl)
                            cfservers = self.db.get_server_list(
                                cfsvname).value_string
                            dwservers = self.db.get_server_list(
                                dwsvname).value_string
                            rsservers = self.db.get_server_list(
                                rssvname).value_string
                            self.assertTrue(cfsvname in cfservers)
                            self.assertTrue(dwsvname in dwservers)
                            self.assertTrue(rssvname in rsservers)

                            cfdevices = self.db.get_device_exported_for_class(
                                "NXSConfigServer").value_string
                            dwdevices = self.db.get_device_exported_for_class(
                                "NXSDataWriter").value_string
                            rsdevices = self.db.get_device_exported_for_class(
                                "NXSRecSelector").value_string
                            self.assertTrue(cfdvname in cfdevices)
                            self.assertTrue(dwdvname in dwdevices)
                            self.assertTrue(rsdvname in rsdevices)
                            self.checkDevice(cfdvname)
                            self.checkDevice(dwdvname)
                            self.checkDevice(rsdvname)
                        except Exception as e:
                            print(str(e))
                            skiptests = True
                # time.sleep(5)
                if not skiptests:
                    print("\nTEST STOP")
                    nservers = ["NXSConfigServer",
                                "NXSDataWriter",
                                "NXSRecSelector"]
                    slservers = []
                    for nsv in nservers:
                        for cnf in cnfs:
                            nsvname = "%s/%s" % (nsv, cnf["masterhost"])
                            slservers.append(nsvname)
                            vl, er = self.runtest(["nxsetup", "stop", nsvname])
                            self.assertEqual('', er)
                            self.assertTrue(vl)
                            for slsv in nservers:
                                for tcnf in cnfs:
                                    svname = "%s/%s" % (
                                        slsv, tcnf["masterhost"])
                                    dvname = "%s/%s/%s" % \
                                             (tcnf['beamline'],
                                              slsv.lower(), tcnf["masterhost"])

                                    servers = self.db.get_server_list(
                                        svname).value_string
                                    self.assertTrue(svname in servers)

                                    devices = self.db.\
                                        get_device_exported_for_class(
                                            slsv).value_string
                                    if svname in slservers:
                                        self.assertTrue(dvname not in devices)
                                    else:
                                        self.assertTrue(dvname in devices)
                    print("\nTEST START")
                    slservers = []
                    for nsv in nservers:
                        for cnf in cnfs:
                            # print(cnf)
                            nsvname = "%s/%s" % (nsv, cnf["masterhost"])
                            slservers.append(nsvname)
                            vl, er = self.runtest(
                                ["nxsetup", "start", nsvname])
                            self.assertEqual('', er)
                            self.assertTrue(vl)
                            for slsv in nservers:
                                for tcnf in cnfs:
                                    svname = "%s/%s" % (
                                        slsv, tcnf["masterhost"])
                                    dvname = "%s/%s/%s" % \
                                             (tcnf['beamline'],
                                              slsv.lower(), tcnf["masterhost"])

                                    servers = self.db.get_server_list(
                                        svname).value_string
                                    self.assertTrue(svname in servers)

                                    devices = self.db.\
                                        get_device_exported_for_class(
                                            slsv).value_string

                                    if svname in slservers:
                                        self.assertTrue(dvname in devices)
                                        self.checkDevice(dvname)
                                    else:
                                        self.assertTrue(dvname not in devices)
                    print("\nTEST RESTART")
                    slservers = []
                    for nsv in nservers:
                        for cnf in cnfs:
                            # print(cnf)
                            nsvname = "%s/%s" % (nsv, cnf["masterhost"])
                            slservers.append(nsvname)
                            svpids = {}
                            for sv, dv in rservers:
                                if sv == nsv:
                                    svpids[sv] = self.serverPid(sv)
                            vl, er = self.runtest(
                                ["nxsetup", "restart", nsvname])
                            for sv, pid in svpids.items():
                                self.assertTrue(self.serverPid(sv) != pid)
                            self.assertEqual('', er)
                            self.assertTrue(vl)
                            for slsv in nservers:
                                for tcnf in cnfs:
                                    svname = "%s/%s" % (
                                        slsv, tcnf["masterhost"])
                                    dvname = "%s/%s/%s" % \
                                        (tcnf['beamline'],
                                         slsv.lower(), tcnf["masterhost"])

                                    servers = self.db.get_server_list(
                                        svname).value_string
                                    self.assertTrue(svname in servers)

                                    devices = self.db.\
                                        get_device_exported_for_class(
                                            slsv).value_string

                                    self.assertTrue(dvname in devices)
                                    self.checkDevice(dvname)
            finally:
                for svname, dvname in set(rservers):
                    try:
                        self.stopServer(svname)
                    except Exception:
                        pass
                    try:
                        self.unregisterServer(svname, dvname)
                    except Exception:
                        pass
                setup = nxsetup.SetUp()
                sservers = list(set(rservers))
                waitforproc = False
                for svname, dvname in sservers:
                    if dvname == sservers[-1][1]:
                        waitforproc = True
                    setup.waitServerNotRunning(
                        svname, dvname, adminproxy, verbose=False,
                        waitforproc=waitforproc)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_server_stop_start_restart(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        dfcnf = {}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['device'] = 'tttest/testnxsteststs/mytest123'
        cnfs[0]['instance'] = 'haso000'
        cnfs[1]['device'] = 'ttest/testnxsteststs/mytest123s'
        cnfs[1]['instance'] = 'haso000t'
        cnfs[2]['device'] = 'ttest/testnxsteststs/mytest123r'
        cnfs[2]['instance'] = 'haso000tt'
        cnfs[3]['device'] = 'ttest/testnxsteststs/mytest123t'
        cnfs[3]['instance'] = 'haso000ttt'
        admin = None
        skiptest = False
        for cnf in cnfs:
            # print(cnf)
            svname = "TestServer/%s" % cnf["instance"]
            dvname = cnf["device"]

            servers = self.db.get_server_list(svname).value_string

            devices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if svname in servers:
                skiptest = True
            if dvname in devices:
                skiptest = True
            adevices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if adevices:
                skiptest = True

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)
        startdspaths = self.getProperty(admin, "StartDsPath")

        rservers = []
        if not skiptest:
            newpath = os.path.abspath(
                os.path.dirname(TestServerSetUp.__file__))
            newstartdspaths = list(startdspaths)
            newstartdspaths.append("/usr/local/bin")
            newstartdspaths.append(newpath)
            self.db.put_device_property(
                admin, {"StartDsPath": newstartdspaths})
            adminproxy.Init()

            tsvs = []
            for cnf in cnfs:
                tsv = TestServerSetUp.TestServerSetUp(
                    cnf["device"], cnf["instance"])
                tsv.setUp()
                tsvs.append(tsv)
                rservers.append(
                    ("TestServer/%s" % cnf["instance"], cnf["device"]))

            setup = nxsetup.SetUp()

            waitforproc = False
            for cnf in cnfs:
                if cnf == cnfs[-1]:
                    waitforproc = True
                setup.waitServerRunning(
                    "TestServer/%s" % cnf["instance"],
                    cnf["device"], adminproxy,
                    waitforproc=waitforproc)
            try:
                if not skiptest:
                    # time.sleep(5)
                    print("\nTEST STOP")
                    vl, er = self.runtest(["nxsetup", "stop", "TestServer"])
                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    for cnf in cnfs:
                        svname = "TestServer/%s" % cnf["instance"]
                        dvname = cnf["device"]

                        servers = self.db.get_server_list(
                            svname).value_string
                        self.assertTrue(svname in servers)

                        devices = self.db.get_device_exported_for_class(
                            "TestServer").value_string
                        self.assertTrue(dvname not in devices)
                    print("\nTEST START")
                    vl, er = self.runtest(["nxsetup", "start", "TestServer"])
                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    for cnf in cnfs:
                        svname = "TestServer/%s" % cnf["instance"]
                        dvname = cnf["device"]

                        servers = self.db.get_server_list(
                            svname).value_string
                        self.assertTrue(svname in servers)

                        devices = self.db.get_device_exported_for_class(
                            "TestServer").value_string
                        self.assertTrue(dvname in devices)

                        self.checkDevice(dvname)
                    print("\nTEST RESTART")
                    svpids = {}
                    for sv, dv in rservers:
                        svpids[sv] = self.serverPid(sv)
                    vl, er = self.runtest(["nxsetup", "restart", "TestServer"])
                    for sv, pid in svpids.items():
                        self.assertTrue(self.serverPid(sv) != pid)
                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    for cnf in cnfs:
                        svname = "TestServer/%s" % cnf["instance"]
                        dvname = cnf["device"]

                        servers = self.db.get_server_list(
                            svname).value_string
                        self.assertTrue(svname in servers)

                        devices = self.db.get_device_exported_for_class(
                            "TestServer").value_string
                        self.assertTrue(dvname in devices)
                        self.checkDevice(dvname)
            finally:
                self.db.put_device_property(
                    admin, {"StartDsPath": startdspaths})
                adminproxy.Init()
                try:
                    if not skiptest:
                        for tsv in tsvs:
                            tsv.tearDown()
                        vl, er = self.runtest(
                            ["nxsetup", "stop", "TestServer"])
                except Exception:
                    pass
                # print(rservers)
                for svname, dvname in set(rservers):
                    try:
                        self.stopServer(svname)
                    except Exception:
                        # print(str(e))
                        pass
                    try:
                        self.unregisterServer(svname, dvname)
                    except Exception:
                        # print(str(e))
                        pass
                setup = nxsetup.SetUp()
                sservers = list(set(rservers))
                waitforproc = False
                for svname, dvname in sservers:
                    if dvname == sservers[-1][1]:
                        waitforproc = True
                    setup.waitServerNotRunning(
                        svname, dvname, adminproxy, verbose=False,
                        waitforproc=waitforproc)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_instance_stop_start_restart(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        dfcnf = {}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['device'] = 'tttest/testnxsteststs/mytest123'
        cnfs[0]['instance'] = 'haso000'
        cnfs[1]['device'] = 'ttest/testnxsteststs/mytest123s'
        cnfs[1]['instance'] = 'haso000t'
        cnfs[2]['device'] = 'ttest/testnxsteststs/mytest123r'
        cnfs[2]['instance'] = 'haso000tt'
        cnfs[3]['device'] = 'ttest/testnxsteststs/mytest123t'
        cnfs[3]['instance'] = 'haso000ttt'
        admin = None
        skiptest = False
        for cnf in cnfs:
            # print(cnf)
            svname = "TestServer/%s" % cnf["instance"]
            dvname = cnf["device"]

            servers = self.db.get_server_list(svname).value_string

            devices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if svname in servers:
                skiptest = True
            if dvname in devices:
                skiptest = True

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)
        startdspaths = self.getProperty(admin, "StartDsPath")

        rservers = []
        if not skiptest:
            newpath = os.path.abspath(
                os.path.dirname(TestServerSetUp.__file__))
            newstartdspaths = list(startdspaths)
            newstartdspaths.append("/usr/local/bin")
            newstartdspaths.append(newpath)
            self.db.put_device_property(
                admin, {"StartDsPath": newstartdspaths})
            adminproxy.Init()

            tsvs = []
            for cnf in cnfs:
                tsv = TestServerSetUp.TestServerSetUp(
                    cnf["device"], cnf["instance"])
                tsv.setUp()
                tsvs.append(tsv)
                rservers.append(
                    ("TestServer/%s" % cnf["instance"], cnf["device"]))

            setup = nxsetup.SetUp()
            waitforproc = False
            for cnf in cnfs:
                if cnf == cnfs[-1]:
                    waitforproc = True
                setup.waitServerRunning(
                    "TestServer/%s" % cnf["instance"],
                    cnf["device"], adminproxy,
                    waitforproc=waitforproc)
            try:
                slservers = []
                print("\nTEST STOP")
                for cnf in cnfs:
                    nsvname = "%s/%s" % ("TestServer", cnf["instance"])
                    slservers.append(nsvname)
                    vl, er = self.runtest(["nxsetup", "stop", nsvname])
                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    for tcnf in cnfs:
                        svname = "TestServer/%s" % tcnf["instance"]
                        dvname = tcnf["device"]

                        servers = self.db.get_server_list(
                            svname).value_string
                        self.assertTrue(svname in servers)

                        devices = self.db.get_device_exported_for_class(
                            "TestServer").value_string
                        if svname in slservers:
                            self.assertTrue(dvname not in devices)
                        else:
                            self.assertTrue(dvname in devices)

                print("\nTEST START")
                slservers = []
                for cnf in cnfs:
                    nsvname = "%s/%s" % ("TestServer", cnf["instance"])
                    slservers.append(nsvname)
                    vl, er = self.runtest(["nxsetup", "start", nsvname])
                    print(vl)
                    print(er)
                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    for tcnf in cnfs:
                        svname = "TestServer/%s" % tcnf["instance"]
                        dvname = tcnf["device"]

                        servers = self.db.get_server_list(
                            svname).value_string
                        self.assertTrue(svname in servers)

                        devices = self.db.get_device_exported_for_class(
                            "TestServer").value_string
                        if svname in slservers:
                            self.assertTrue(dvname in devices)
                            self.checkDevice(dvname)
                        else:
                            self.assertTrue(dvname not in devices)

                slservers = []
                print("\nTEST RESTART")
                for cnf in cnfs:
                    nsvname = "%s/%s" % ("TestServer", cnf["instance"])
                    slservers.append(nsvname)
                    svpids = {}
                    for sv, dv in rservers:
                        if sv == nsvname:
                            svpids[sv] = self.serverPid(sv)
                    vl, er = self.runtest(["nxsetup", "restart", nsvname])
                    for sv, pid in svpids.items():
                        self.assertTrue(self.serverPid(sv) != pid)
                    self.assertEqual('', er)
                    self.assertTrue(vl)
                    for tcnf in cnfs:
                        svname = "TestServer/%s" % tcnf["instance"]
                        dvname = tcnf["device"]

                        servers = self.db.get_server_list(
                            svname).value_string
                        self.assertTrue(svname in servers)

                        devices = self.db.get_device_exported_for_class(
                            "TestServer").value_string
                        self.assertTrue(dvname in devices)
                        self.checkDevice(dvname)
            finally:
                try:
                    for cnf in cnfs:
                        nsvname = "%s/%s" % ("TestServer", cnf["instance"])
                        vl, er = self.runtest(["nxsetup", "stop", nsvname])
                except Exception:
                    pass

                self.db.put_device_property(
                    admin, {"StartDsPath": startdspaths})
                adminproxy.Init()
                try:
                    if not skiptest:
                        for tsv in tsvs:
                            tsv.tearDown()
                except Exception:
                    pass
                # print(rservers)
                for svname, dvname in set(rservers):
                    try:
                        self.stopServer(svname)
                    except Exception:
                        # print(str(e))
                        pass
                    try:
                        self.unregisterServer(svname, dvname)
                    except Exception:
                        # print(str(e))
                        pass
                setup = nxsetup.SetUp()
                sservers = list(set(rservers))
                waitforproc = False
                for svname, dvname in sservers:
                    if dvname == sservers[-1][1]:
                        waitforproc = True
                    setup.waitServerNotRunning(
                        svname, dvname, adminproxy, verbose=False,
                        waitforproc=waitforproc)

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_addrecorderpath_instance(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        ins2 = "MSMTESTS2"
        msdv2 = "msmtestp09/testts/t2r228"
        ms2 = MacroServerSetUp.MacroServerSetUp(
            instance=ins2,
            msdevices=[msdv2],
            doordevices=["doormtestp09/testts/t2r228"])
        try:
            ms2.setUp()
            setup = nxsetup.SetUp()
            admin = setup.getStarterName(self.host)
            startdspaths = self.getProperty(admin, "StartDsPath")
            adp = tango.DeviceProxy(admin)
            setup.waitServerRunning("MacroServer/%s" % ins2,
                                    msdv2,  adp)
            newpath = os.path.abspath(
                os.path.dirname(TestServerSetUp.__file__))
            newstartdspaths = list(startdspaths)
            newstartdspaths.append("/usr/local/bin")
            newstartdspaths.append(newpath)
            self.db.put_device_property(
                admin, {"StartDsPath": newstartdspaths})
            adp.Init()
            recorderpaths = self.getProperty(msdv2, "RecorderPath")
            pid = self.serverPid("MacroServer/%s" % ins2)
            # print("PD1:", pid)
            path1 = "/tmp/"
            vl, er = self.runtest(
                ["nxsetup", "add-recorder-path", path1, "-i", ins2])
            # print(vl)
            self.assertEqual('', er)
            self.assertTrue(self.serverPid("MacroServer/%s" % ins2) != pid)
            # print("PD2:", self.serverPid("MacroServer/%s" % ins2))

            recorderpaths1 = self.getProperty(msdv2, "RecorderPath")
            df1 = list(set(recorderpaths1) - set(recorderpaths))
            self.assertTrue(df1, [path1])

            pid = self.serverPid("MacroServer/%s" % ins2)
            # print("PD3:", pid)
            path2 = "/usr/share/"
            vl, er = self.runtest(
                ["nxsetup", "add-recorder-path", path2, "--instance", ins2])
            # print(vl)
            self.assertEqual('', er)
            # print("PD4:", self.serverPid("MacroServer/%s" % ins2))
            self.assertTrue(self.serverPid("MacroServer/%s" % ins2) != pid)

            recorderpaths2 = self.getProperty(msdv2, "RecorderPath")
            df2 = list(set(recorderpaths2) - set(recorderpaths1))
            self.assertTrue(df2, [path2])

            pid = self.serverPid("MacroServer/%s" % ins2)
            path2 = "/usr/share/"
            vl, er = self.runtest(
                ["nxsetup", "add-recorder-path", path2, "--instance", ins2])
            self.assertEqual('', er)
            self.assertTrue(self.serverPid("MacroServer/%s" % ins2) == pid)

            recorderpaths3 = self.getProperty(msdv2, "RecorderPath")
            df3 = list(set(recorderpaths3) - set(recorderpaths2))
            self.assertTrue(df3 == [])

        finally:
            self.db.put_device_property(
                admin, {"StartDsPath": startdspaths})
            adp.Init()
            self.db.put_device_property(
                msdv2, {"RecorderPath": recorderpaths})
            try:
                self.stopServer("MacroServer/%s" % ins2)
            except Exception:
                pass

            ms2.tearDown()

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_addrecorderpath_instance_postpone(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        ins2 = "MSMTESTS2"
        msdv2 = "msmtestp09/testts/t2r228"
        ms2 = MacroServerSetUp.MacroServerSetUp(
            instance=ins2,
            msdevices=[msdv2],
            doordevices=["doormtestp09/testts/t2r228"])
        try:
            ms2.setUp()
            setup = nxsetup.SetUp()
            admin = setup.getStarterName(self.host)
            adp = tango.DeviceProxy(admin)
            setup.waitServerRunning("MacroServer/%s" % ins2,
                                    msdv2,  adp)

            recorderpaths = self.getProperty(msdv2, "RecorderPath")

            pid = self.serverPid("MacroServer/%s" % ins2)
            path1 = "/tmp/"
            vl, er = self.runtest(
                ["nxsetup", "add-recorder-path", path1, "-t", "-i", ins2])
            self.assertEqual('', er)
            self.assertTrue(self.serverPid("MacroServer/%s" % ins2) == pid)

            recorderpaths1 = self.getProperty(msdv2, "RecorderPath")
            df1 = list(set(recorderpaths1) - set(recorderpaths))
            self.assertTrue(df1, [path1])

            pid = self.serverPid("MacroServer/%s" % ins2)
            path2 = "/usr/share/"
            vl, er = self.runtest(
                ["nxsetup", "add-recorder-path", path2, "--instance", ins2,
                 "--postpone"])
            self.assertEqual('', er)
            self.assertTrue(self.serverPid("MacroServer/%s" % ins2) == pid)

            recorderpaths2 = self.getProperty(msdv2, "RecorderPath")
            df2 = list(set(recorderpaths2) - set(recorderpaths1))
            self.assertTrue(df2, [path2])

        finally:
            self.db.put_device_property(
                msdv2, {"RecorderPath": recorderpaths})

            ms2.tearDown()

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_addrecorderpath_all(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        ins1 = "MSTESTS1"
        msdv1 = "mstestp09/testts/t1r228"
        ins2 = "MSMTESTS2"
        msdv2 = "msmtestp09/testts/t2r228"
        ms2 = MacroServerSetUp.MacroServerSetUp(
            instance=ins2,
            msdevices=[msdv2],
            doordevices=["doormtestp09/testts/t2r228"])
        ms2.setUp()
        mss = self.db.get_server_list("MacroServer/*").value_string
        skiptest = True
        if len(mss) == 2:
            skiptest = False
        if skiptest:
            ms2.tearDown()
        else:
            try:
                setup = nxsetup.SetUp()
                admin = setup.getStarterName(self.host)
                startdspaths = self.getProperty(admin, "StartDsPath")
                adp = tango.DeviceProxy(admin)

                setup.waitServerRunning("MacroServer/%s" % ins2,
                                        msdv2,  adp, waitforproc=False)
                setup.waitServerRunning("MacroServer/%s" % ins1,
                                        msdv1,  adp)
                newpath = os.path.abspath(
                    os.path.dirname(TestServerSetUp.__file__))
                newstartdspaths = list(startdspaths)
                newstartdspaths.append("/usr/local/bin")
                newstartdspaths.append(newpath)
                self.db.put_device_property(
                    admin, {"StartDsPath": newstartdspaths})
                adp.Init()

                recorder2paths = self.getProperty(msdv2, "RecorderPath")
                recorder1paths = self.getProperty(msdv1, "RecorderPath")
                self.assertEqual(recorder1paths, [])
                self.assertEqual(recorder2paths, [])

                pid2 = self.serverPid("MacroServer/%s" % ins2)
                pid1 = self.serverPid("MacroServer/%s" % ins1)
                path1 = "/tmp/"
                vl, er = self.runtest(
                    ["nxsetup", "add-recorder-path", path1])
                self.assertEqual('', er)
                self.assertTrue(
                    self.serverPid("MacroServer/%s" % ins1) != pid1)
                self.assertTrue(
                    self.serverPid("MacroServer/%s" % ins2) != pid2)

                recorder2paths1 = self.getProperty(msdv2, "RecorderPath")
                recorder1paths1 = self.getProperty(msdv1, "RecorderPath")

                df1 = list(set(recorder1paths1) - set(recorder1paths))
                self.assertEqual(df1, [path1])
                df1 = list(set(recorder2paths1) - set(recorder2paths))
                self.assertEqual(df1, [path1])

                pid2 = self.serverPid("MacroServer/%s" % ins2)
                pid1 = self.serverPid("MacroServer/%s" % ins1)
                path2 = "/usr/share/"
                vl, er = self.runtest(
                    ["nxsetup", "add-recorder-path", path2])
                self.assertEqual('', er)
                self.assertTrue(
                    self.serverPid("MacroServer/%s" % ins1) != pid1)
                self.assertTrue(
                    self.serverPid("MacroServer/%s" % ins2) != pid2)

                recorder2paths2 = self.getProperty(msdv2, "RecorderPath")
                recorder1paths2 = self.getProperty(msdv1, "RecorderPath")
                df2 = list(set(recorder1paths2) - set(recorder1paths1))
                self.assertEqual(df2, [path2])
                df2 = list(set(recorder2paths2) - set(recorder2paths1))
                self.assertEqual(df2, [path2])

                pid2 = self.serverPid("MacroServer/%s" % ins2)
                pid1 = self.serverPid("MacroServer/%s" % ins1)
                path2 = "/usr/share/"
                vl, er = self.runtest(
                    ["nxsetup", "add-recorder-path", path2])
                self.assertEqual('', er)
                self.assertTrue(
                    self.serverPid("MacroServer/%s" % ins1) == pid1)
                self.assertTrue(
                    self.serverPid("MacroServer/%s" % ins2) == pid2)

                recorder2paths3 = self.getProperty(msdv2, "RecorderPath")
                recorder1paths3 = self.getProperty(msdv1, "RecorderPath")
                df2 = list(set(recorder1paths3) - set(recorder1paths2))
                self.assertEqual(df2, [])
                df2 = list(set(recorder2paths3) - set(recorder2paths2))
                self.assertEqual(df2, [])

            finally:
                try:
                    self.stopServer("MacroServer/%s" % ins1)
                except Exception:
                    pass
                try:
                    self.stopServer("MacroServer/%s" % ins2)
                except Exception:
                    pass
                self.db.put_device_property(
                    admin, {"StartDsPath": startdspaths})
                adp.Init()
                self.db.put_device_property(
                    msdv2, {"RecorderPath": recorder2paths})
                self.db.put_device_property(
                    msdv1, {"RecorderPath": recorder1paths})
                ms2.tearDown()

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_addrecorderpath_all_postpone(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        ins1 = "MSTESTS1"
        msdv1 = "mstestp09/testts/t1r228"
        ins2 = "MSMTESTS2"
        msdv2 = "msmtestp09/testts/t2r228"
        ms2 = MacroServerSetUp.MacroServerSetUp(
            instance=ins2,
            msdevices=[msdv2],
            doordevices=["doormtestp09/testts/t2r228"])
        ms2.setUp()
        mss = self.db.get_server_list("MacroServer/*").value_string
        skiptest = True
        if len(mss) == 2:
            skiptest = False
        if skiptest:
            ms2.tearDown()
        else:
            try:
                setup = nxsetup.SetUp()
                admin = setup.getStarterName(self.host)
                adp = tango.DeviceProxy(admin)

                setup.waitServerRunning("MacroServer/%s" % ins2,
                                        msdv2,  adp, waitforproc=False)
                setup.waitServerRunning("MacroServer/%s" % ins1,
                                        msdv1,  adp)

                recorder2paths = self.getProperty(msdv2, "RecorderPath")
                recorder1paths = self.getProperty(msdv1, "RecorderPath")
                self.assertEqual(recorder1paths, [])
                self.assertEqual(recorder2paths, [])

                pid2 = self.serverPid("MacroServer/%s" % ins2)
                pid1 = self.serverPid("MacroServer/%s" % ins1)
                path1 = "/tmp/"
                vl, er = self.runtest(
                    ["nxsetup", "add-recorder-path", path1, "-t"])
                self.assertEqual('', er)
                self.assertTrue(
                    self.serverPid("MacroServer/%s" % ins1) == pid1)
                self.assertTrue(
                    self.serverPid("MacroServer/%s" % ins2) == pid2)

                recorder2paths1 = self.getProperty(msdv2, "RecorderPath")
                recorder1paths1 = self.getProperty(msdv1, "RecorderPath")

                df1 = list(set(recorder1paths1) - set(recorder1paths))
                self.assertEqual(df1, [path1])
                df1 = list(set(recorder2paths1) - set(recorder2paths))
                self.assertEqual(df1, [path1])

                pid2 = self.serverPid("MacroServer/%s" % ins2)
                pid1 = self.serverPid("MacroServer/%s" % ins1)
                path2 = "/usr/share/"
                vl, er = self.runtest(
                    ["nxsetup", "add-recorder-path", path2, "--postpone"])
                self.assertEqual('', er)
                self.assertTrue(
                    self.serverPid("MacroServer/%s" % ins1) == pid1)
                self.assertTrue(
                    self.serverPid("MacroServer/%s" % ins2) == pid2)

                recorder2paths2 = self.getProperty(msdv2, "RecorderPath")
                recorder1paths2 = self.getProperty(msdv1, "RecorderPath")
                df2 = list(set(recorder1paths2) - set(recorder1paths1))
                self.assertEqual(df2, [path2])
                df2 = list(set(recorder2paths2) - set(recorder2paths1))
                self.assertEqual(df2, [path2])

            finally:
                self.db.put_device_property(
                    msdv2, {"RecorderPath": recorder2paths})
                self.db.put_device_property(
                    msdv1, {"RecorderPath": recorder1paths})

                ms2.tearDown()

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_addrecorderpath_instance_multi(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        ins2 = "MSMTESTS2"
        msdv2 = ["msmtestp09/testts/t1r228", "msmtestp09/testts/t2r228"]
        ms2 = MacroServerSetUp.MacroServerSetUp(
            instance=ins2,
            msdevices=msdv2,
            doordevices=["doormtestp09/testts/t2r228"])
        try:
            ms2.setUp()
            setup = nxsetup.SetUp()
            admin = setup.getStarterName(self.host)
            startdspaths = self.getProperty(admin, "StartDsPath")
            adp = tango.DeviceProxy(admin)
            setup.waitServerRunning("MacroServer/%s" % ins2,
                                    msdv2[0],  adp)
            newpath = os.path.abspath(
                os.path.dirname(TestServerSetUp.__file__))
            newstartdspaths = list(startdspaths)
            newstartdspaths.append("/usr/local/bin")
            newstartdspaths.append(newpath)
            self.db.put_device_property(
                admin, {"StartDsPath": newstartdspaths})
            adp.Init()
            recorder1paths = self.getProperty(msdv2[0], "RecorderPath")
            recorder2paths = self.getProperty(msdv2[1], "RecorderPath")
            self.assertEqual(recorder1paths, [])
            self.assertEqual(recorder2paths, [])

            pid = self.serverPid("MacroServer/%s" % ins2)
            path1 = "/tmp/"
            vl, er = self.runtest(
                ["nxsetup", "add-recorder-path", path1, "-i", ins2])
            self.assertEqual('', er)
            self.assertTrue(self.serverPid("MacroServer/%s" % ins2) != pid)

            recorder1paths1 = self.getProperty(msdv2[0], "RecorderPath")
            recorder2paths1 = self.getProperty(msdv2[1], "RecorderPath")
            df1 = list(set(recorder1paths1) - set(recorder1paths))
            self.assertEqual(df1, [path1])
            df1 = list(set(recorder2paths1) - set(recorder2paths))
            self.assertEqual(df1, [path1])

            pid = self.serverPid("MacroServer/%s" % ins2)
            path2 = "/usr/share/"
            vl, er = self.runtest(
                ["nxsetup", "add-recorder-path", path2, "--instance", ins2])
            self.assertEqual('', er)
            self.assertTrue(self.serverPid("MacroServer/%s" % ins2) != pid)

            recorder1paths2 = self.getProperty(msdv2[0], "RecorderPath")
            recorder2paths2 = self.getProperty(msdv2[1], "RecorderPath")
            df2 = list(set(recorder1paths2) - set(recorder1paths1))
            self.assertEqual(df2, [path2])
            df2 = list(set(recorder2paths2) - set(recorder2paths1))
            self.assertEqual(df2, [path2])

            pid = self.serverPid("MacroServer/%s" % ins2)
            path2 = "/usr/share/"
            vl, er = self.runtest(
                ["nxsetup", "add-recorder-path", path2, "--instance", ins2])
            self.assertEqual('', er)
            self.assertTrue(self.serverPid("MacroServer/%s" % ins2) == pid)

            recorder1paths3 = self.getProperty(msdv2[0], "RecorderPath")
            recorder2paths3 = self.getProperty(msdv2[1], "RecorderPath")
            df2 = list(set(recorder1paths3) - set(recorder1paths2))
            self.assertEqual(df2, [])
            df2 = list(set(recorder2paths3) - set(recorder2paths2))
            self.assertEqual(df2, [])

        finally:
            self.db.put_device_property(
                admin, {"StartDsPath": startdspaths})
            adp.Init()
            self.db.put_device_property(
                msdv2[1], {"RecorderPath": recorder2paths})
            self.db.put_device_property(
                msdv2[0], {"RecorderPath": recorder1paths})
            try:
                self.stopServer("MacroServer/%s" % ins2)
            except Exception:
                pass

            ms2.tearDown()

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_addrecorderpath_instance_multi_postpone(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        ins2 = "MSMTESTS2"
        msdv2 = ["msmtestp09/testts/t1r228", "msmtestp09/testts/t2r228"]
        ms2 = MacroServerSetUp.MacroServerSetUp(
            instance=ins2,
            msdevices=msdv2,
            doordevices=["doormtestp09/testts/t2r228"])
        try:
            ms2.setUp()
            setup = nxsetup.SetUp()
            admin = setup.getStarterName(self.host)
            startdspaths = self.getProperty(admin, "StartDsPath")
            adp = tango.DeviceProxy(admin)
            setup.waitServerRunning("MacroServer/%s" % ins2,
                                    msdv2[0],  adp)
            newpath = os.path.abspath(
                os.path.dirname(TestServerSetUp.__file__))
            newstartdspaths = list(startdspaths)
            newstartdspaths.append("/usr/local/bin")
            newstartdspaths.append(newpath)
            self.db.put_device_property(
                admin, {"StartDsPath": newstartdspaths})
            adp.Init()
            recorder1paths = self.getProperty(msdv2[0], "RecorderPath")
            recorder2paths = self.getProperty(msdv2[1], "RecorderPath")
            self.assertEqual(recorder1paths, [])
            self.assertEqual(recorder2paths, [])

            pid = self.serverPid("MacroServer/%s" % ins2)
            path1 = "/tmp/"
            vl, er = self.runtest(
                ["nxsetup", "add-recorder-path", path1, "-i", ins2, "-t"])
            self.assertEqual('', er)
            self.assertTrue(self.serverPid("MacroServer/%s" % ins2) == pid)

            recorder1paths1 = self.getProperty(msdv2[0], "RecorderPath")
            recorder2paths1 = self.getProperty(msdv2[1], "RecorderPath")
            df1 = list(set(recorder1paths1) - set(recorder1paths))
            self.assertEqual(df1, [path1])
            df1 = list(set(recorder2paths1) - set(recorder2paths))
            self.assertEqual(df1, [path1])

            pid = self.serverPid("MacroServer/%s" % ins2)
            path2 = "/usr/share/"
            vl, er = self.runtest(
                ["nxsetup", "add-recorder-path", path2, "--instance", ins2,
                 "--postpone"])
            self.assertEqual('', er)
            self.assertTrue(self.serverPid("MacroServer/%s" % ins2) == pid)

            recorder1paths2 = self.getProperty(msdv2[0], "RecorderPath")
            recorder2paths2 = self.getProperty(msdv2[1], "RecorderPath")
            df2 = list(set(recorder1paths2) - set(recorder1paths1))
            self.assertEqual(df2, [path2])
            df2 = list(set(recorder2paths2) - set(recorder2paths1))
            self.assertEqual(df2, [path2])

        finally:
            self.db.put_device_property(
                admin, {"StartDsPath": startdspaths})
            adp.Init()
            self.db.put_device_property(
                msdv2[1], {"RecorderPath": recorder2paths})
            self.db.put_device_property(
                msdv2[0], {"RecorderPath": recorder1paths})

            ms2.tearDown()

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_moveprop_instance(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tss = self.db.get_server_list("TestServer/*").value_string
        print(tss)
        dvname = "ttestp09/testts/t1r228"
        dfcnf = {}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['device'] = 'tttest/testnxsteststs/mytest123'
        cnfs[0]['instance'] = 'haso000'
        cnfs[0]['oldname'] = "MyOldProp1"
        cnfs[0]['newname'] = "MyNewProp1"
        cnfs[0]['value'] = ["MyNp", "asda", "aasd"]
        cnfs[1]['device'] = 'ttest/testnxsteststs/mytest123s'
        cnfs[1]['instance'] = 'haso000t'
        cnfs[1]['oldname'] = "MyOldProp2"
        cnfs[1]['newname'] = "MyNewProp2"
        cnfs[1]['value'] = ["MyNpsdf", "asddf"]
        cnfs[2]['device'] = 'ttest/testnxsteststs/mytest123r'
        cnfs[2]['instance'] = 'haso000tt'
        cnfs[2]['oldname'] = "MyOldProp3"
        cnfs[2]['newname'] = "MyNewProp3"
        cnfs[2]['value'] = ["MyNp", "asda", "aasd", "asdsad"]
        cnfs[3]['device'] = 'ttest/testnxsteststs/mytest123t'
        cnfs[3]['instance'] = 'haso000ttt'
        cnfs[3]['oldname'] = "MyOldProp4"
        cnfs[3]['newname'] = "MyNewProp4"
        cnfs[3]['value'] = ["MyNadsas"]
        admin = None
        skiptest = False
        if tss:
            skiptest = True
        for cnf in cnfs:
            # print(cnf)
            svname = "TestServer/%s" % cnf["instance"]
            dvname = cnf["device"]

            servers = self.db.get_server_list(svname).value_string

            devices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if svname in servers:
                skiptest = True
            if dvname in devices:
                skiptest = True

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)
        startdspaths = self.getProperty(admin, "StartDsPath")

        rservers = []

        if not skiptest:
            newpath = os.path.abspath(
                os.path.dirname(TestServerSetUp.__file__))
            newstartdspaths = list(startdspaths)
            newstartdspaths.append("/usr/local/bin")
            newstartdspaths.append(newpath)
            self.db.put_device_property(
                admin, {"StartDsPath": newstartdspaths})
            adminproxy.Init()
            tsvs = []
            for cnf in cnfs:
                tsv = TestServerSetUp.TestServerSetUp(
                    cnf["device"], cnf["instance"])

                tsv.setUp()
                tsvs.append(tsv)
                rservers.append(
                    ("TestServer/%s" % cnf["instance"], cnf["device"]))
                self.db.put_device_property(
                    cnf["device"], {cnf["oldname"]: cnf["value"]})

            setup = nxsetup.SetUp()
            waitforproc = False
            for cnf in cnfs:
                if cnf == cnfs[-1]:
                    waitforproc = True
                setup.waitServerRunning(
                    "TestServer/%s" % cnf["instance"],
                    cnf["device"], adminproxy,
                    waitforproc=waitforproc)
            try:
                for cnf in cnfs:
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        cnf["value"]
                    )
                    cmd = [
                        'nxsetup', 'move-prop',
                        '-o', cnf['oldname'],
                        '-n', cnf['newname'],
                        'TestServer/%s' % cnf['instance']
                        # 'TestServer'
                    ]
                    pid = self.serverPid("TestServer/%s" % cnf["instance"])
                    vl, er = self.runtest(cmd)
                    pid2 = self.serverPid("TestServer/%s" % cnf["instance"])
                    self.assertTrue(pid != pid2)
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["newname"]),
                        cnf["value"]
                    )
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        []
                    )

            finally:
                self.db.put_device_property(
                    admin, {"StartDsPath": startdspaths})
                adminproxy.Init()
                for cnf in cnfs:
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["newname"])
                    except Exception:
                        pass
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["oldname"])
                    except Exception:
                        pass
                try:
                    if not skiptest:
                        for tsv in tsvs:
                            tsv.tearDown()
                except Exception:
                    pass

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_moveprop_instance_long(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tss = self.db.get_server_list("TestServer/*").value_string
        print(tss)
        dvname = "ttestp09/testts/t1r228"
        dfcnf = {}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['device'] = 'tttest/testnxsteststs/mytest123'
        cnfs[0]['instance'] = 'haso000'
        cnfs[0]['oldname'] = "MyOldProp1"
        cnfs[0]['newname'] = "MyNewProp1"
        cnfs[0]['value'] = ["MyNp", "asda", "aasd"]
        cnfs[1]['device'] = 'ttest/testnxsteststs/mytest123s'
        cnfs[1]['instance'] = 'haso000t'
        cnfs[1]['oldname'] = "MyOldProp2"
        cnfs[1]['newname'] = "MyNewProp2"
        cnfs[1]['value'] = ["MyNpsdf", "asddf"]
        cnfs[2]['device'] = 'ttest/testnxsteststs/mytest123r'
        cnfs[2]['instance'] = 'haso000tt'
        cnfs[2]['oldname'] = "MyOldProp3"
        cnfs[2]['newname'] = "MyNewProp3"
        cnfs[2]['value'] = ["MyNp", "asda", "aasd", "asdsad"]
        cnfs[3]['device'] = 'ttest/testnxsteststs/mytest123t'
        cnfs[3]['instance'] = 'haso000ttt'
        cnfs[3]['oldname'] = "MyOldProp4"
        cnfs[3]['newname'] = "MyNewProp4"
        cnfs[3]['value'] = ["MyNadsas"]
        admin = None
        skiptest = False
        if tss:
            skiptest = True
        for cnf in cnfs:
            # print(cnf)
            svname = "TestServer/%s" % cnf["instance"]
            dvname = cnf["device"]

            servers = self.db.get_server_list(svname).value_string

            devices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if svname in servers:
                skiptest = True
            if dvname in devices:
                skiptest = True

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)
        startdspaths = self.getProperty(admin, "StartDsPath")

        rservers = []

        if not skiptest:
            newpath = os.path.abspath(
                os.path.dirname(TestServerSetUp.__file__))
            newstartdspaths = list(startdspaths)
            newstartdspaths.append("/usr/local/bin")
            newstartdspaths.append(newpath)
            self.db.put_device_property(
                admin, {"StartDsPath": newstartdspaths})
            adminproxy.Init()
            tsvs = []
            for cnf in cnfs:
                tsv = TestServerSetUp.TestServerSetUp(
                    cnf["device"], cnf["instance"])

                tsv.setUp()
                tsvs.append(tsv)
                rservers.append(
                    ("TestServer/%s" % cnf["instance"], cnf["device"]))
                self.db.put_device_property(
                    cnf["device"], {cnf["oldname"]: cnf["value"]})

            setup = nxsetup.SetUp()
            waitforproc = False
            for cnf in cnfs:
                if cnf == cnfs[-1]:
                    waitforproc = True
                setup.waitServerRunning(
                    "TestServer/%s" % cnf["instance"],
                    cnf["device"], adminproxy,
                    waitforproc=waitforproc)
            try:
                for cnf in cnfs:
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        cnf["value"]
                    )
                    cmd = [
                        'nxsetup', 'move-prop',
                        '--oldname', cnf['oldname'],
                        '--newname', cnf['newname'],
                        'TestServer/%s' % cnf['instance']
                        # 'TestServer'
                    ]
                    pid = self.serverPid("TestServer/%s" % cnf["instance"])
                    vl, er = self.runtest(cmd)
                    pid2 = self.serverPid("TestServer/%s" % cnf["instance"])
                    self.assertTrue(pid != pid2)
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["newname"]),
                        cnf["value"]
                    )
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        []
                    )

            finally:
                self.db.put_device_property(
                    admin, {"StartDsPath": startdspaths})
                adminproxy.Init()
                for cnf in cnfs:
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["newname"])
                    except Exception:
                        pass
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["oldname"])
                    except Exception:
                        pass
                try:
                    if not skiptest:
                        for tsv in tsvs:
                            tsv.tearDown()
                except Exception:
                    pass

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_moveprop_instance_postpone(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tss = self.db.get_server_list("TestServer/*").value_string
        print(tss)
        dvname = "ttestp09/testts/t1r228"
        dfcnf = {}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['device'] = 'tttest/testnxsteststs/mytest123'
        cnfs[0]['instance'] = 'haso000'
        cnfs[0]['oldname'] = "MyOldProp1"
        cnfs[0]['newname'] = "MyNewProp1"
        cnfs[0]['value'] = ["MyNp", "asda", "aasd"]
        cnfs[1]['device'] = 'ttest/testnxsteststs/mytest123s'
        cnfs[1]['instance'] = 'haso000t'
        cnfs[1]['oldname'] = "MyOldProp2"
        cnfs[1]['newname'] = "MyNewProp2"
        cnfs[1]['value'] = ["MyNpsdf", "asddf"]
        cnfs[2]['device'] = 'ttest/testnxsteststs/mytest123r'
        cnfs[2]['instance'] = 'haso000tt'
        cnfs[2]['oldname'] = "MyOldProp3"
        cnfs[2]['newname'] = "MyNewProp3"
        cnfs[2]['value'] = ["MyNp", "asda", "aasd", "asdsad"]
        cnfs[3]['device'] = 'ttest/testnxsteststs/mytest123t'
        cnfs[3]['instance'] = 'haso000ttt'
        cnfs[3]['oldname'] = "MyOldProp4"
        cnfs[3]['newname'] = "MyNewProp4"
        cnfs[3]['value'] = ["MyNadsas"]
        admin = None
        skiptest = False
        if tss:
            skiptest = True
        for cnf in cnfs:
            # print(cnf)
            svname = "TestServer/%s" % cnf["instance"]
            dvname = cnf["device"]

            servers = self.db.get_server_list(svname).value_string

            devices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if svname in servers:
                skiptest = True
            if dvname in devices:
                skiptest = True

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)

        rservers = []

        if not skiptest:
            tsvs = []
            for cnf in cnfs:
                tsv = TestServerSetUp.TestServerSetUp(
                    cnf["device"], cnf["instance"])

                tsv.setUp()
                tsvs.append(tsv)
                rservers.append(
                    ("TestServer/%s" % cnf["instance"], cnf["device"]))
                self.db.put_device_property(
                    cnf["device"], {cnf["oldname"]: cnf["value"]})

            setup = nxsetup.SetUp()
            waitforproc = False
            for cnf in cnfs:
                if cnf == cnfs[-1]:
                    waitforproc = True
                setup.waitServerRunning(
                    "TestServer/%s" % cnf["instance"],
                    cnf["device"], adminproxy,
                    waitforproc=waitforproc)
            try:
                for cnf in cnfs:
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        cnf["value"]
                    )
                    cmd = [
                        'nxsetup', 'move-prop',
                        '-o', cnf['oldname'],
                        '-n', cnf['newname'], '-t',
                        'TestServer/%s' % cnf['instance']
                        # 'TestServer'
                    ]
                    pid = self.serverPid("TestServer/%s" % cnf["instance"])
                    vl, er = self.runtest(cmd)
                    pid2 = self.serverPid("TestServer/%s" % cnf["instance"])
                    self.assertTrue(pid == pid2)
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["newname"]),
                        cnf["value"]
                    )
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        []
                    )

            finally:
                for cnf in cnfs:
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["newname"])
                    except Exception:
                        pass
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["oldname"])
                    except Exception:
                        pass
                try:
                    if not skiptest:
                        for tsv in tsvs:
                            tsv.tearDown()
                except Exception:
                    pass

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_moveprop_instance_postpone_long(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tss = self.db.get_server_list("TestServer/*").value_string
        dvname = "ttestp09/testts/t1r228"
        dfcnf = {}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['device'] = 'tttest/testnxsteststs/mytest123'
        cnfs[0]['instance'] = 'haso000'
        cnfs[0]['oldname'] = "MyOldProp1"
        cnfs[0]['newname'] = "MyNewProp1"
        cnfs[0]['value'] = ["MyNp", "asda", "aasd"]
        cnfs[1]['device'] = 'ttest/testnxsteststs/mytest123s'
        cnfs[1]['instance'] = 'haso000t'
        cnfs[1]['oldname'] = "MyOldProp2"
        cnfs[1]['newname'] = "MyNewProp2"
        cnfs[1]['value'] = ["MyNpsdf", "asddf"]
        cnfs[2]['device'] = 'ttest/testnxsteststs/mytest123r'
        cnfs[2]['instance'] = 'haso000tt'
        cnfs[2]['oldname'] = "MyOldProp3"
        cnfs[2]['newname'] = "MyNewProp3"
        cnfs[2]['value'] = ["MyNp", "asda", "aasd", "asdsad"]
        cnfs[3]['device'] = 'ttest/testnxsteststs/mytest123t'
        cnfs[3]['instance'] = 'haso000ttt'
        cnfs[3]['oldname'] = "MyOldProp4"
        cnfs[3]['newname'] = "MyNewProp4"
        cnfs[3]['value'] = ["MyNadsas"]
        admin = None
        skiptest = False
        if tss:
            skiptest = True
        for cnf in cnfs:
            # print(cnf)
            svname = "TestServer/%s" % cnf["instance"]
            dvname = cnf["device"]

            servers = self.db.get_server_list(svname).value_string

            devices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if svname in servers:
                skiptest = True
            if dvname in devices:
                skiptest = True

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)

        rservers = []

        if not skiptest:
            tsvs = []
            for cnf in cnfs:
                tsv = TestServerSetUp.TestServerSetUp(
                    cnf["device"], cnf["instance"])

                tsv.setUp()
                tsvs.append(tsv)
                rservers.append(
                    ("TestServer/%s" % cnf["instance"], cnf["device"]))
                self.db.put_device_property(
                    cnf["device"], {cnf["oldname"]: cnf["value"]})

            setup = nxsetup.SetUp()
            waitforproc = False
            for cnf in cnfs:
                if cnf == cnfs[-1]:
                    waitforproc = True
                setup.waitServerRunning(
                    "TestServer/%s" % cnf["instance"],
                    cnf["device"], adminproxy,
                    waitforproc=waitforproc)
            try:
                for cnf in cnfs:
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        cnf["value"]
                    )
                    cmd = [
                        'nxsetup', 'move-prop',
                        '--oldname', cnf['oldname'],
                        '--newname', cnf['newname'], '--postpone',
                        'TestServer/%s' % cnf['instance']
                        # 'TestServer'
                    ]
                    pid = self.serverPid("TestServer/%s" % cnf["instance"])
                    vl, er = self.runtest(cmd)
                    pid2 = self.serverPid("TestServer/%s" % cnf["instance"])
                    self.assertTrue(pid == pid2)
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["newname"]),
                        cnf["value"]
                    )
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        []
                    )

            finally:
                for cnf in cnfs:
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["newname"])
                    except Exception:
                        pass
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["oldname"])
                    except Exception:
                        pass
                try:
                    if not skiptest:
                        for tsv in tsvs:
                            tsv.tearDown()
                except Exception:
                    pass

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_moveprop_server(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tss = self.db.get_server_list("TestServer/*").value_string
        print(tss)
        dvname = "ttestp09/testts/t1r228"
        dfcnf = {}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['device'] = 'tttest/testnxsteststs/mytest123'
        cnfs[0]['instance'] = 'haso000'
        cnfs[0]['oldname'] = "MyOldProp1"
        cnfs[0]['newname'] = "MyNewProp1"
        cnfs[0]['value'] = ["MyNp", "asda", "aasd"]
        cnfs[1]['device'] = 'ttest/testnxsteststs/mytest123s'
        cnfs[1]['instance'] = 'haso000t'
        cnfs[1]['oldname'] = "MyOldProp2"
        cnfs[1]['newname'] = "MyNewProp2"
        cnfs[1]['value'] = ["MyNpsdf", "asddf"]
        cnfs[2]['device'] = 'ttest/testnxsteststs/mytest123r'
        cnfs[2]['instance'] = 'haso000tt'
        cnfs[2]['oldname'] = "MyOldProp3"
        cnfs[2]['newname'] = "MyNewProp3"
        cnfs[2]['value'] = ["MyNp", "asda", "aasd", "asdsad"]
        cnfs[3]['device'] = 'ttest/testnxsteststs/mytest123t'
        cnfs[3]['instance'] = 'haso000ttt'
        cnfs[3]['oldname'] = "MyOldProp4"
        cnfs[3]['newname'] = "MyNewProp4"
        cnfs[3]['value'] = ["MyNadsas"]
        admin = None
        skiptest = False
        if tss:
            skiptest = True
        for cnf in cnfs:
            # print(cnf)
            svname = "TestServer/%s" % cnf["instance"]
            dvname = cnf["device"]

            servers = self.db.get_server_list(svname).value_string

            devices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if svname in servers:
                skiptest = True
            if dvname in devices:
                skiptest = True

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)
        startdspaths = self.getProperty(admin, "StartDsPath")

        rservers = []

        if not skiptest:
            newpath = os.path.abspath(
                os.path.dirname(TestServerSetUp.__file__))
            newstartdspaths = list(startdspaths)
            newstartdspaths.append("/usr/local/bin")
            newstartdspaths.append(newpath)
            self.db.put_device_property(
                admin, {"StartDsPath": newstartdspaths})
            adminproxy.Init()
            tsvs = []
            for cnf in cnfs:
                tsv = TestServerSetUp.TestServerSetUp(
                    cnf["device"], cnf["instance"])

                tsv.setUp()
                tsvs.append(tsv)
                rservers.append(
                    ("TestServer/%s" % cnf["instance"], cnf["device"]))
                self.db.put_device_property(
                    cnf["device"], {cnf["oldname"]: cnf["value"]})

            setup = nxsetup.SetUp()
            waitforproc = False
            for cnf in cnfs:
                if cnf == cnfs[-1]:
                    waitforproc = True
                setup.waitServerRunning(
                    "TestServer/%s" % cnf["instance"],
                    cnf["device"], adminproxy,
                    waitforproc=waitforproc)
            try:
                for cnf in cnfs:
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        cnf["value"]
                    )
                    cmd = [
                        'nxsetup', 'move-prop',
                        '-o', cnf['oldname'],
                        '-n', cnf['newname'],
                        'TestServer'
                    ]
                    pid = self.serverPid("TestServer/%s" % cnf["instance"])
                    vl, er = self.runtest(cmd)
                    pid2 = self.serverPid("TestServer/%s" % cnf["instance"])
                    self.assertTrue(pid != pid2)
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["newname"]),
                        cnf["value"]
                    )
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        []
                    )

            finally:
                self.db.put_device_property(
                    admin, {"StartDsPath": startdspaths})
                adminproxy.Init()
                for cnf in cnfs:
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["newname"])
                    except Exception:
                        pass
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["oldname"])
                    except Exception:
                        pass
                try:
                    if not skiptest:
                        for tsv in tsvs:
                            tsv.tearDown()
                except Exception:
                    pass

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_moveprop_server_long(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tss = self.db.get_server_list("TestServer/*").value_string
        print(tss)
        dvname = "ttestp09/testts/t1r228"
        dfcnf = {}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['device'] = 'tttest/testnxsteststs/mytest123'
        cnfs[0]['instance'] = 'haso000'
        cnfs[0]['oldname'] = "MyOldProp1"
        cnfs[0]['newname'] = "MyNewProp1"
        cnfs[0]['value'] = ["MyNp", "asda", "aasd"]
        cnfs[1]['device'] = 'ttest/testnxsteststs/mytest123s'
        cnfs[1]['instance'] = 'haso000t'
        cnfs[1]['oldname'] = "MyOldProp2"
        cnfs[1]['newname'] = "MyNewProp2"
        cnfs[1]['value'] = ["MyNpsdf", "asddf"]
        cnfs[2]['device'] = 'ttest/testnxsteststs/mytest123r'
        cnfs[2]['instance'] = 'haso000tt'
        cnfs[2]['oldname'] = "MyOldProp3"
        cnfs[2]['newname'] = "MyNewProp3"
        cnfs[2]['value'] = ["MyNp", "asda", "aasd", "asdsad"]
        cnfs[3]['device'] = 'ttest/testnxsteststs/mytest123t'
        cnfs[3]['instance'] = 'haso000ttt'
        cnfs[3]['oldname'] = "MyOldProp4"
        cnfs[3]['newname'] = "MyNewProp4"
        cnfs[3]['value'] = ["MyNadsas"]
        admin = None
        skiptest = False
        if tss:
            skiptest = True
        for cnf in cnfs:
            # print(cnf)
            svname = "TestServer/%s" % cnf["instance"]
            dvname = cnf["device"]

            servers = self.db.get_server_list(svname).value_string

            devices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if svname in servers:
                skiptest = True
            if dvname in devices:
                skiptest = True

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)
        startdspaths = self.getProperty(admin, "StartDsPath")

        rservers = []

        if not skiptest:
            newpath = os.path.abspath(
                os.path.dirname(TestServerSetUp.__file__))
            newstartdspaths = list(startdspaths)
            newstartdspaths.append("/usr/local/bin")
            newstartdspaths.append(newpath)
            self.db.put_device_property(
                admin, {"StartDsPath": newstartdspaths})
            adminproxy.Init()
            tsvs = []
            for cnf in cnfs:
                tsv = TestServerSetUp.TestServerSetUp(
                    cnf["device"], cnf["instance"])

                tsv.setUp()
                tsvs.append(tsv)
                rservers.append(
                    ("TestServer/%s" % cnf["instance"], cnf["device"]))
                self.db.put_device_property(
                    cnf["device"], {cnf["oldname"]: cnf["value"]})

            setup = nxsetup.SetUp()
            waitforproc = False
            for cnf in cnfs:
                if cnf == cnfs[-1]:
                    waitforproc = True
                setup.waitServerRunning(
                    "TestServer/%s" % cnf["instance"],
                    cnf["device"], adminproxy,
                    waitforproc=waitforproc)
            try:
                for cnf in cnfs:
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        cnf["value"]
                    )
                    cmd = [
                        'nxsetup', 'move-prop',
                        '--oldname', cnf['oldname'],
                        '--newname', cnf['newname'],
                        'TestServer'
                    ]
                    pid = self.serverPid("TestServer/%s" % cnf["instance"])
                    vl, er = self.runtest(cmd)
                    pid2 = self.serverPid("TestServer/%s" % cnf["instance"])
                    self.assertTrue(pid != pid2)
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["newname"]),
                        cnf["value"]
                    )
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        []
                    )

            finally:
                self.db.put_device_property(
                    admin, {"StartDsPath": startdspaths})
                adminproxy.Init()
                for cnf in cnfs:
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["newname"])
                    except Exception:
                        pass
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["oldname"])
                    except Exception:
                        pass
                try:
                    if not skiptest:
                        for tsv in tsvs:
                            tsv.tearDown()
                except Exception:
                    pass

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_moveprop_server_postpone(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tss = self.db.get_server_list("TestServer/*").value_string
        print(tss)
        dvname = "ttestp09/testts/t1r228"
        dfcnf = {}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['device'] = 'tttest/testnxsteststs/mytest123'
        cnfs[0]['instance'] = 'haso000'
        cnfs[0]['oldname'] = "MyOldProp1"
        cnfs[0]['newname'] = "MyNewProp1"
        cnfs[0]['value'] = ["MyNp", "asda", "aasd"]
        cnfs[1]['device'] = 'ttest/testnxsteststs/mytest123s'
        cnfs[1]['instance'] = 'haso000t'
        cnfs[1]['oldname'] = "MyOldProp2"
        cnfs[1]['newname'] = "MyNewProp2"
        cnfs[1]['value'] = ["MyNpsdf", "asddf"]
        cnfs[2]['device'] = 'ttest/testnxsteststs/mytest123r'
        cnfs[2]['instance'] = 'haso000tt'
        cnfs[2]['oldname'] = "MyOldProp3"
        cnfs[2]['newname'] = "MyNewProp3"
        cnfs[2]['value'] = ["MyNp", "asda", "aasd", "asdsad"]
        cnfs[3]['device'] = 'ttest/testnxsteststs/mytest123t'
        cnfs[3]['instance'] = 'haso000ttt'
        cnfs[3]['oldname'] = "MyOldProp4"
        cnfs[3]['newname'] = "MyNewProp4"
        cnfs[3]['value'] = ["MyNadsas"]
        admin = None
        skiptest = False
        if tss:
            skiptest = True
        for cnf in cnfs:
            # print(cnf)
            svname = "TestServer/%s" % cnf["instance"]
            dvname = cnf["device"]

            servers = self.db.get_server_list(svname).value_string

            devices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if svname in servers:
                skiptest = True
            if dvname in devices:
                skiptest = True

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)

        rservers = []

        if not skiptest:
            tsvs = []
            for cnf in cnfs:
                tsv = TestServerSetUp.TestServerSetUp(
                    cnf["device"], cnf["instance"])

                tsv.setUp()
                tsvs.append(tsv)
                rservers.append(
                    ("TestServer/%s" % cnf["instance"], cnf["device"]))
                self.db.put_device_property(
                    cnf["device"], {cnf["oldname"]: cnf["value"]})

            setup = nxsetup.SetUp()
            waitforproc = False
            for cnf in cnfs:
                if cnf == cnfs[-1]:
                    waitforproc = True
                setup.waitServerRunning(
                    "TestServer/%s" % cnf["instance"],
                    cnf["device"], adminproxy,
                    waitforproc=waitforproc)
            try:
                for cnf in cnfs:
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        cnf["value"]
                    )
                    cmd = [
                        'nxsetup', 'move-prop',
                        '-o', cnf['oldname'],
                        '-n', cnf['newname'], '-t',
                        'TestServer'
                    ]
                    pid = self.serverPid("TestServer/%s" % cnf["instance"])
                    vl, er = self.runtest(cmd)
                    pid2 = self.serverPid("TestServer/%s" % cnf["instance"])
                    self.assertTrue(pid == pid2)
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["newname"]),
                        cnf["value"]
                    )
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        []
                    )

            finally:
                for cnf in cnfs:
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["newname"])
                    except Exception:
                        pass
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["oldname"])
                    except Exception:
                        pass
                try:
                    if not skiptest:
                        for tsv in tsvs:
                            tsv.tearDown()
                except Exception:
                    pass

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_moveprop_server_postpone_long(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tss = self.db.get_server_list("TestServer/*").value_string
        dvname = "ttestp09/testts/t1r228"
        dfcnf = {}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['device'] = 'tttest/testnxsteststs/mytest123'
        cnfs[0]['instance'] = 'haso000'
        cnfs[0]['oldname'] = "MyOldProp1"
        cnfs[0]['newname'] = "MyNewProp1"
        cnfs[0]['value'] = ["MyNp", "asda", "aasd"]
        cnfs[1]['device'] = 'ttest/testnxsteststs/mytest123s'
        cnfs[1]['instance'] = 'haso000t'
        cnfs[1]['oldname'] = "MyOldProp2"
        cnfs[1]['newname'] = "MyNewProp2"
        cnfs[1]['value'] = ["MyNpsdf", "asddf"]
        cnfs[2]['device'] = 'ttest/testnxsteststs/mytest123r'
        cnfs[2]['instance'] = 'haso000tt'
        cnfs[2]['oldname'] = "MyOldProp3"
        cnfs[2]['newname'] = "MyNewProp3"
        cnfs[2]['value'] = ["MyNp", "asda", "aasd", "asdsad"]
        cnfs[3]['device'] = 'ttest/testnxsteststs/mytest123t'
        cnfs[3]['instance'] = 'haso000ttt'
        cnfs[3]['oldname'] = "MyOldProp4"
        cnfs[3]['newname'] = "MyNewProp4"
        cnfs[3]['value'] = ["MyNadsas"]
        admin = None
        skiptest = False
        if tss:
            skiptest = True
        for cnf in cnfs:
            # print(cnf)
            svname = "TestServer/%s" % cnf["instance"]
            dvname = cnf["device"]

            servers = self.db.get_server_list(svname).value_string

            devices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if svname in servers:
                skiptest = True
            if dvname in devices:
                skiptest = True

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)

        rservers = []

        if not skiptest:
            tsvs = []
            for cnf in cnfs:
                tsv = TestServerSetUp.TestServerSetUp(
                    cnf["device"], cnf["instance"])

                tsv.setUp()
                tsvs.append(tsv)
                rservers.append(
                    ("TestServer/%s" % cnf["instance"], cnf["device"]))
                self.db.put_device_property(
                    cnf["device"], {cnf["oldname"]: cnf["value"]})

            setup = nxsetup.SetUp()
            waitforproc = False
            for cnf in cnfs:
                if cnf == cnfs[-1]:
                    waitforproc = True
                setup.waitServerRunning(
                    "TestServer/%s" % cnf["instance"],
                    cnf["device"], adminproxy,
                    waitforproc=waitforproc)
            try:
                for cnf in cnfs:
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        cnf["value"]
                    )
                    cmd = [
                        'nxsetup', 'move-prop',
                        '--oldname', cnf['oldname'],
                        '--newname', cnf['newname'], '--postpone',
                        'TestServer'
                    ]
                    pid = self.serverPid("TestServer/%s" % cnf["instance"])
                    vl, er = self.runtest(cmd)
                    pid2 = self.serverPid("TestServer/%s" % cnf["instance"])
                    self.assertTrue(pid == pid2)
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["newname"]),
                        cnf["value"]
                    )
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        []
                    )

            finally:
                for cnf in cnfs:
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["newname"])
                    except Exception:
                        pass
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["oldname"])
                    except Exception:
                        pass
                try:
                    if not skiptest:
                        for tsv in tsvs:
                            tsv.tearDown()
                except Exception:
                    pass

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_moveprop_server_multi(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tss = self.db.get_server_list("TestServer/*").value_string
        print(tss)
        dvname = "ttestp09/testts/t1r228"
        dfcnf = {}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['device'] = 'tttest/testnxsteststs/mytest123'
        cnfs[0]['instance'] = 'haso000'
        cnfs[0]['oldname'] = "MyOldProp"
        cnfs[0]['newname'] = "MyNewProp"
        cnfs[0]['value'] = ["MyNp", "asda", "aasd"]
        cnfs[1]['device'] = 'ttest/testnxsteststs/mytest123s'
        cnfs[1]['instance'] = 'haso000t'
        cnfs[1]['oldname'] = "MyOldProp"
        cnfs[1]['newname'] = "MyNewProp"
        cnfs[1]['value'] = ["MyNpsdf", "asddf"]
        cnfs[2]['device'] = 'ttest/testnxsteststs/mytest123r'
        cnfs[2]['instance'] = 'haso000tt'
        cnfs[2]['oldname'] = "MyOldProp"
        cnfs[2]['newname'] = "MyNewProp"
        cnfs[2]['value'] = ["MyNp", "asda", "aasd", "asdsad"]
        cnfs[3]['device'] = 'ttest/testnxsteststs/mytest123t'
        cnfs[3]['instance'] = 'haso000ttt'
        cnfs[3]['oldname'] = "MyOldProp"
        cnfs[3]['newname'] = "MyNewProp"
        cnfs[3]['value'] = ["MyNadsas"]
        admin = None
        skiptest = False
        if tss:
            skiptest = True
        for cnf in cnfs:
            # print(cnf)
            svname = "TestServer/%s" % cnf["instance"]
            dvname = cnf["device"]

            servers = self.db.get_server_list(svname).value_string

            devices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if svname in servers:
                skiptest = True
            if dvname in devices:
                skiptest = True

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)
        startdspaths = self.getProperty(admin, "StartDsPath")

        rservers = []

        if not skiptest:
            newpath = os.path.abspath(
                os.path.dirname(TestServerSetUp.__file__))
            newstartdspaths = list(startdspaths)
            newstartdspaths.append("/usr/local/bin")
            newstartdspaths.append(newpath)
            self.db.put_device_property(
                admin, {"StartDsPath": newstartdspaths})
            adminproxy.Init()
            tsvs = []
            for cnf in cnfs:
                tsv = TestServerSetUp.TestServerSetUp(
                    cnf["device"], cnf["instance"])

                tsv.setUp()
                tsvs.append(tsv)
                rservers.append(
                    ("TestServer/%s" % cnf["instance"], cnf["device"]))
                self.db.put_device_property(
                    cnf["device"], {cnf["oldname"]: cnf["value"]})

            setup = nxsetup.SetUp()
            waitforproc = False
            for cnf in cnfs:
                if cnf == cnfs[-1]:
                    waitforproc = True
                setup.waitServerRunning(
                    "TestServer/%s" % cnf["instance"],
                    cnf["device"], adminproxy,
                    waitforproc=waitforproc)
            try:
                svpids = {}
                for cnf in cnfs:
                    sv = "TestServer/%s" % cnf["instance"]
                    svpids[sv] = self.serverPid(sv)
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        cnf["value"]
                    )
                cmd = [
                    'nxsetup', 'move-prop',
                    '-o', cnfs[0]['oldname'],
                    '-n', cnfs[0]['newname'],
                    'TestServer'
                ]
                vl, er = self.runtest(cmd)
                for sv, pid in svpids.items():
                    self.assertTrue(self.serverPid(sv) != pid)
                for cnf in cnfs:
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["newname"]),
                        cnf["value"]
                    )
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        []
                    )

            finally:
                self.db.put_device_property(
                    admin, {"StartDsPath": startdspaths})
                adminproxy.Init()
                for cnf in cnfs:
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["newname"])
                    except Exception:
                        pass
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["oldname"])
                    except Exception:
                        pass
                try:
                    if not skiptest:
                        for tsv in tsvs:
                            tsv.tearDown()
                except Exception:
                    pass

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_moveprop_server_multi_long(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tss = self.db.get_server_list("TestServer/*").value_string
        print(tss)
        dvname = "ttestp09/testts/t1r228"
        dfcnf = {}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['device'] = 'tttest/testnxsteststs/mytest123'
        cnfs[0]['instance'] = 'haso000'
        cnfs[0]['oldname'] = "MyOldProp"
        cnfs[0]['newname'] = "MyNewProp"
        cnfs[0]['value'] = ["MyNp", "asda", "aasd"]
        cnfs[1]['device'] = 'ttest/testnxsteststs/mytest123s'
        cnfs[1]['instance'] = 'haso000t'
        cnfs[1]['oldname'] = "MyOldProp"
        cnfs[1]['newname'] = "MyNewProp"
        cnfs[1]['value'] = ["MyNpsdf", "asddf"]
        cnfs[2]['device'] = 'ttest/testnxsteststs/mytest123r'
        cnfs[2]['instance'] = 'haso000tt'
        cnfs[2]['oldname'] = "MyOldProp"
        cnfs[2]['newname'] = "MyNewProp"
        cnfs[2]['value'] = ["MyNp", "asda", "aasd", "asdsad"]
        cnfs[3]['device'] = 'ttest/testnxsteststs/mytest123t'
        cnfs[3]['instance'] = 'haso000ttt'
        cnfs[3]['oldname'] = "MyOldProp"
        cnfs[3]['newname'] = "MyNewProp"
        cnfs[3]['value'] = ["MyNadsas"]
        admin = None
        skiptest = False
        if tss:
            skiptest = True
        for cnf in cnfs:
            # print(cnf)
            svname = "TestServer/%s" % cnf["instance"]
            dvname = cnf["device"]

            servers = self.db.get_server_list(svname).value_string

            devices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if svname in servers:
                skiptest = True
            if dvname in devices:
                skiptest = True

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)
        startdspaths = self.getProperty(admin, "StartDsPath")

        rservers = []

        if not skiptest:
            newpath = os.path.abspath(
                os.path.dirname(TestServerSetUp.__file__))
            newstartdspaths = list(startdspaths)
            newstartdspaths.append("/usr/local/bin")
            newstartdspaths.append(newpath)
            self.db.put_device_property(
                admin, {"StartDsPath": newstartdspaths})
            adminproxy.Init()
            tsvs = []
            for cnf in cnfs:
                tsv = TestServerSetUp.TestServerSetUp(
                    cnf["device"], cnf["instance"])

                tsv.setUp()
                tsvs.append(tsv)
                rservers.append(
                    ("TestServer/%s" % cnf["instance"], cnf["device"]))
                self.db.put_device_property(
                    cnf["device"], {cnf["oldname"]: cnf["value"]})

            setup = nxsetup.SetUp()
            waitforproc = False
            for cnf in cnfs:
                if cnf == cnfs[-1]:
                    waitforproc = True
                setup.waitServerRunning(
                    "TestServer/%s" % cnf["instance"],
                    cnf["device"], adminproxy,
                    waitforproc=waitforproc)
            try:
                svpids = {}
                for cnf in cnfs:
                    sv = "TestServer/%s" % cnf["instance"]
                    svpids[sv] = self.serverPid(sv)
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        cnf["value"]
                    )
                cmd = [
                    'nxsetup', 'move-prop',
                    '--oldname', cnfs[0]['oldname'],
                    '--newname', cnfs[0]['newname'],
                    'TestServer'
                ]
                vl, er = self.runtest(cmd)
                for sv, pid in svpids.items():
                    self.assertTrue(self.serverPid(sv) != pid)
                for cnf in cnfs:
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["newname"]),
                        cnf["value"]
                    )
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        []
                    )

            finally:
                self.db.put_device_property(
                    admin, {"StartDsPath": startdspaths})
                adminproxy.Init()
                for cnf in cnfs:
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["newname"])
                    except Exception:
                        pass
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["oldname"])
                    except Exception:
                        pass
                try:
                    if not skiptest:
                        for tsv in tsvs:
                            tsv.tearDown()
                except Exception:
                    pass

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_moveprop_server_postpone_multi(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tss = self.db.get_server_list("TestServer/*").value_string
        print(tss)
        dvname = "ttestp09/testts/t1r228"
        dfcnf = {}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['device'] = 'tttest/testnxsteststs/mytest123'
        cnfs[0]['instance'] = 'haso000'
        cnfs[0]['oldname'] = "MyOldProp"
        cnfs[0]['newname'] = "MyNewProp"
        cnfs[0]['value'] = ["MyNp", "asda", "aasd"]
        cnfs[1]['device'] = 'ttest/testnxsteststs/mytest123s'
        cnfs[1]['instance'] = 'haso000t'
        cnfs[1]['oldname'] = "MyOldProp"
        cnfs[1]['newname'] = "MyNewProp"
        cnfs[1]['value'] = ["MyNpsdf", "asddf"]
        cnfs[2]['device'] = 'ttest/testnxsteststs/mytest123r'
        cnfs[2]['instance'] = 'haso000tt'
        cnfs[2]['oldname'] = "MyOldProp"
        cnfs[2]['newname'] = "MyNewProp"
        cnfs[2]['value'] = ["MyNp", "asda", "aasd", "asdsad"]
        cnfs[3]['device'] = 'ttest/testnxsteststs/mytest123t'
        cnfs[3]['instance'] = 'haso000ttt'
        cnfs[3]['oldname'] = "MyOldProp"
        cnfs[3]['newname'] = "MyNewProp"
        cnfs[3]['value'] = ["MyNadsas"]
        admin = None
        skiptest = False
        if tss:
            skiptest = True
        for cnf in cnfs:
            # print(cnf)
            svname = "TestServer/%s" % cnf["instance"]
            dvname = cnf["device"]

            servers = self.db.get_server_list(svname).value_string

            devices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if svname in servers:
                skiptest = True
            if dvname in devices:
                skiptest = True

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)

        rservers = []

        if not skiptest:
            tsvs = []
            for cnf in cnfs:
                tsv = TestServerSetUp.TestServerSetUp(
                    cnf["device"], cnf["instance"])

                tsv.setUp()
                tsvs.append(tsv)
                rservers.append(
                    ("TestServer/%s" % cnf["instance"], cnf["device"]))
                self.db.put_device_property(
                    cnf["device"], {cnf["oldname"]: cnf["value"]})

            setup = nxsetup.SetUp()
            waitforproc = False
            for cnf in cnfs:
                if cnf == cnfs[-1]:
                    waitforproc = True
                setup.waitServerRunning(
                    "TestServer/%s" % cnf["instance"],
                    cnf["device"], adminproxy,
                    waitforproc=waitforproc)
            try:
                svpids = {}
                for cnf in cnfs:
                    sv = "TestServer/%s" % cnf["instance"]
                    svpids[sv] = self.serverPid(sv)
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        cnf["value"]
                    )
                cmd = [
                    'nxsetup', 'move-prop', '-t',
                    '-o', cnfs[0]['oldname'],
                    '-n', cnfs[0]['newname'],
                    'TestServer'
                ]
                vl, er = self.runtest(cmd)
                for sv, pid in svpids.items():
                    self.assertTrue(self.serverPid(sv) == pid)
                for cnf in cnfs:
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["newname"]),
                        cnf["value"]
                    )
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        []
                    )

            finally:
                for cnf in cnfs:
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["newname"])
                    except Exception:
                        pass
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["oldname"])
                    except Exception:
                        pass
                try:
                    if not skiptest:
                        for tsv in tsvs:
                            tsv.tearDown()
                except Exception:
                    pass

    # comp_available test
    # \brief It tests XMLConfigurator
    def test_moveprop_server_postpone_multi_long(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        tss = self.db.get_server_list("TestServer/*").value_string
        print(tss)
        dvname = "ttestp09/testts/t1r228"
        dfcnf = {}

        cnfs = [dict(dfcnf) for _ in range(4)]

        cnfs[0]['device'] = 'tttest/testnxsteststs/mytest123'
        cnfs[0]['instance'] = 'haso000'
        cnfs[0]['oldname'] = "MyOldProp"
        cnfs[0]['newname'] = "MyNewProp"
        cnfs[0]['value'] = ["MyNp", "asda", "aasd"]
        cnfs[1]['device'] = 'ttest/testnxsteststs/mytest123s'
        cnfs[1]['instance'] = 'haso000t'
        cnfs[1]['oldname'] = "MyOldProp"
        cnfs[1]['newname'] = "MyNewProp"
        cnfs[1]['value'] = ["MyNpsdf", "asddf"]
        cnfs[2]['device'] = 'ttest/testnxsteststs/mytest123r'
        cnfs[2]['instance'] = 'haso000tt'
        cnfs[2]['oldname'] = "MyOldProp"
        cnfs[2]['newname'] = "MyNewProp"
        cnfs[2]['value'] = ["MyNp", "asda", "aasd", "asdsad"]
        cnfs[3]['device'] = 'ttest/testnxsteststs/mytest123t'
        cnfs[3]['instance'] = 'haso000ttt'
        cnfs[3]['oldname'] = "MyOldProp"
        cnfs[3]['newname'] = "MyNewProp"
        cnfs[3]['value'] = ["MyNadsas"]
        admin = None
        skiptest = False
        if tss:
            skiptest = True
        for cnf in cnfs:
            # print(cnf)
            svname = "TestServer/%s" % cnf["instance"]
            dvname = cnf["device"]

            servers = self.db.get_server_list(svname).value_string

            devices = self.db.get_device_exported_for_class(
                "TestServer").value_string
            if svname in servers:
                skiptest = True
            if dvname in devices:
                skiptest = True

        admin = nxsetup.SetUp().getStarterName(self.host)
        if not admin:
            skiptest = True
            adminproxy = None
        else:
            adminproxy = tango.DeviceProxy(admin)

        rservers = []

        if not skiptest:
            tsvs = []
            for cnf in cnfs:
                tsv = TestServerSetUp.TestServerSetUp(
                    cnf["device"], cnf["instance"])

                tsv.setUp()
                tsvs.append(tsv)
                rservers.append(
                    ("TestServer/%s" % cnf["instance"], cnf["device"]))
                self.db.put_device_property(
                    cnf["device"], {cnf["oldname"]: cnf["value"]})

            setup = nxsetup.SetUp()
            waitforproc = False
            for cnf in cnfs:
                if cnf == cnfs[-1]:
                    waitforproc = True
                setup.waitServerRunning(
                    "TestServer/%s" % cnf["instance"],
                    cnf["device"], adminproxy,
                    waitforproc=waitforproc)
            try:
                svpids = {}
                for cnf in cnfs:
                    sv = "TestServer/%s" % cnf["instance"]
                    svpids[sv] = self.serverPid(sv)
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        cnf["value"]
                    )
                cmd = [
                    'nxsetup', 'move-prop', '--postpone',
                    '--oldname', cnfs[0]['oldname'],
                    '--newname', cnfs[0]['newname'],
                    'TestServer'
                ]
                vl, er = self.runtest(cmd)
                for sv, pid in svpids.items():
                    self.assertTrue(self.serverPid(sv) == pid)
                for cnf in cnfs:
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["newname"]),
                        cnf["value"]
                    )
                    self.assertEqual(
                        self.getProperty(cnf["device"], cnf["oldname"]),
                        []
                    )

            finally:
                for cnf in cnfs:
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["newname"])
                    except Exception:
                        pass
                    try:
                        self.db.delete_device_property(
                            cnf["device"], cnf["oldname"])
                    except Exception:
                        pass
                try:
                    if not skiptest:
                        for tsv in tsvs:
                            tsv.tearDown()
                except Exception:
                    pass


if __name__ == '__main__':
    unittest.main()
