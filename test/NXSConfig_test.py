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
import numpy as np
import threading
try:
    import tango
except Exception:
    import PyTango as tango
from nxstools import nxsconfig
import shutil

import docutils.parsers.rst
import docutils.utils
# import dateutil.parser

try:
    from checks import checkxmls
except ImportError:
    from .checks import checkxmls

try:
    import ServerSetUp
except ImportError:
    from . import ServerSetUp


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
class NXSConfigTest(unittest.TestCase):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

        self.helperror = "Error: too few arguments\n"

        self.helpinfo = """usage: nxsconfig [-h]
                 {list,show,get,delete,upload,variables,sources,record,merge,components,data,describe,info,geometry,servers}
                 ...

Command-line tool for reading NeXus configuration from NXSConfigServer

positional arguments:
  {list,show,get,delete,upload,variables,sources,record,merge,components,data,describe,info,geometry,servers}
                        sub-command help
    list                list names of available components, datasources or
                        profiles
    show                show (or write to files) components, datasources or
                        profiles with given names
    get                 get full configuration of components
    delete              delete components, datasources or profiles with given
                        names from ConfigServer
    upload              upload components, datasources or profiles with given
                        names from locale filesystem into ConfigServer
    variables           get a list of component variables
    sources             get a list of component datasources
    record              get a list of datasource record names for components
                        or datasources
    merge               get merged configuration of components or datasources
    components          get a list of dependent components
    data                get/set values of component variables
    describe            show all parameters of given components or datasources
    info                show general parameters of given components,
                        datasources or profile
    geometry            show transformation parameters of given components or
                        datasources
    servers             get a list of configuration servers from the current
                        tango host

optional arguments:
  -h, --help            show this help message and exit

For more help:
  nxsconfig <sub-command> -h

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
        self.__profs = []
        self.maxDiff = None
        self.__ds = []
        self.__sels = []
        self.__man = []
        self.children = ("record", "doc", "device", "database", "query",
                         "datasource", "result")

        from os.path import expanduser
        home = expanduser("~")
        self.__args2 = '{"db":"nxsconfig", ' \
                       '"read_default_file":"%s/.my.cnf", ' \
                       '"use_unicode":true}' % home
        self._sv = ServerSetUp.ServerSetUp()

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
            nxsconfig.main()
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
            nxsconfig.main()
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

    def parseRST(self, text):
        parser = docutils.parsers.rst.Parser()
        component = docutils.parsers.rst.Parser
        if hasattr(docutils.frontend, 'get_default_settings'):
            settings = docutils.frontend.get_default_settings(component)
        else:
            settings = docutils.frontend.OptionParser(
                components=(component,)).get_default_values()
        document = docutils.utils.new_document(
            '<rst-doc>', settings=settings)
        parser.parse(text, document)
        return document

    def checkRSTTable(self, section, header, result, sort=False):
        table = section
        self.assertEqual(table.tagname, 'table')
        self.assertEqual(len(table), 1)
        self.assertEqual(table[0].tagname, 'tgroup')
        if header:
            self.assertEqual(len(table[0]), len(result[0]) + 2)
        else:
            self.assertEqual(len(table[0]), len(result[0]) + 1)
        for i in range(len(result[0])):
            self.assertEqual(table[0][i].tagname, 'colspec')
        if header:
            self.assertEqual(table[0][len(result[0])].tagname, 'thead')
            self.assertEqual(
                str(table[0][len(result[0])]),
                header
            )
            tbody = table[0][len(result[0])+1]
        else:
            tbody = table[0][len(result[0])]
        self.assertEqual(tbody.tagname, 'tbody')
        self.assertEqual(len(tbody), len(result))
        self.assertEqual(len(tbody[0]), len(result[0]))
        if sort:
            rix = [int(el)
                   for el in np.argsort([el[0] for el in result])]
            tix = [int(el)
                   for el in np.argsort([
                           (str(el[0][0][0])
                            if '@' not in str(el[0][0][0])
                            else str(el[0][0][0][0]))
                           for el in tbody])]
        else:
            rix = range(len(result))
            tix = rix
        for i in range(len(result)):
            self.assertEqual(len(tbody[tix[i]]), len(result[rix[i]]))
            self.assertEqual(tbody[tix[i]].tagname, 'row')
            for j in range(len(result[rix[i]])):
                if len(tbody[tix[i]][j]):
                    self.assertEqual(tbody[tix[i]][j].tagname, 'entry')
                    self.assertEqual(
                        tbody[tix[i]][j][0].tagname, 'paragraph')
                    if result[rix[i]][j] and '@' in result[rix[i]][j]:
                        if tbody[tix[i]][j][0][0].tagname == 'reference':
                            self.assertEqual(
                                tbody[tix[i]][j][0][0].tagname, 'reference')
                            self.assertEqual(len(tbody[tix[i]][j][0][0]), 1)
                            self.assertEqual(
                                str(tbody[tix[i]][j][0][0][0]),
                                result[rix[i]][j])
                        else:
                            self.assertEqual(
                                tbody[tix[i]][j][0][0].tagname, '#text')
                            self.assertEqual(
                                str(tbody[tix[i]][j][0][0]), result[rix[i]][j])
                    else:
                        self.assertEqual(
                            tbody[tix[i]][j][0][0].tagname, '#text')
                        self.assertEqual(
                            str(tbody[tix[i]][j][0][0]), result[rix[i]][j])
                else:
                    self.assertTrue(result[rix[i]][j] is None)

    def checkRSTSection(self, section, title, header, result, sort=False):
        self.assertEqual(section.tagname, 'section')
        self.assertTrue(len(section) > 0)
        self.assertEqual(len(section[0]), 1)
        self.assertEqual(str(section[0]), '<title>%s</title>' % title)
        if result:
            self.assertEqual(len(section[1]), 1)
            self.assertEqual(len(section), 2)
            table = section[1]
            self.checkRSTTable(table, header, result, sort)
        else:
            self.assertEqual(len(section), 1)

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
    def closeConfig(self, xmlc):
        self.assertEqual(xmlc.state(), tango.DevState.OPEN)

        xmlc.Close()
        self.assertEqual(xmlc.state(), tango.DevState.ON)

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
        self._sv.setUp()
        print("SEED = %s" % self.seed)

    # test closer
    # \brief Common tear down
    def tearDown(self):
        print("tearing down ...")
        if self.__cmps:
            el = self.openConf()
            for cp in self.__cmps:
                el.deleteComponent(cp)
            el.close()
        if self.__ds:
            el = self.openConf()
            for ds in self.__ds:
                el.deleteDataSource(ds)
            el.close()

        if self.__sels:
            el = self.openConf()
            for sel in self.__sels:
                el.deleteSelection(sel)
            el.close()

        if self.__man:
            el = self.openConf()
            el.setMandatoryComponents(self.__man)
            el.close()
        self._sv.tearDown()

    def openConf(self):
        try:
            el = self.openConfig(self.__args)
        except Exception:
            el = self.openConfig(self.__args2)
        return el

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
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        vl, er, et = self.runtestexcept(['nxsconfig'], SystemExit)
        self.assertEqual(
            "".join(self.helpinfo.split()).replace(
                "optionalarguments:", "options:"),
            "".join(vl.split()).replace("optionalarguments:", "options:"))
        self.assertEqual(self.helperror, er)

    def test_help(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        helps = ['-h', '--help']
        for hl in helps:
            vl, er, et = self.runtestexcept(['nxsconfig', hl], SystemExit)
            self.assertEqual(
                "".join(self.helpinfo[0:-1].split()).replace(
                    "optionalarguments:", "options:"),
                "".join(vl.split()).replace("optionalarguments:", "options:"))
            self.assertEqual('', er)

    def test_servers(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        commands = [
            ('nxsconfig servers -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig servers -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig servers --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig servers -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig servers -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig servers --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig servers --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig servers --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cmd in commands:

            vl, er = self.runtest(cmd)

            if "-n" in cmd or "--no-newlines" in cmd:
                avc3 = [ec.strip() for ec in vl.split(' ') if ec.strip()]
            else:
                avc3 = vl.strip().split('\n')
            server = self._sv.new_device_info_writer.name
            for cp in avc3:
                if cp:
                    self.assertTrue(server in avc3)

            self.assertEqual('', er)

        el.close()

    def test_servers_2(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        server2 = "aatestp09/testmcs2/testr228"
        sv2 = ServerSetUp.ServerSetUp(instance="AMCSTEST2",
                                      dvname=server2)
        sv2.setUp()
        el = self.openConf()
        commands = [
            ('nxsconfig servers -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig servers -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig servers --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig servers -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig servers -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig servers --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig servers --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig servers --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cmd in commands:
            vl, er = self.runtest(cmd)

            if "-n" in cmd or "--no-newlines" in cmd:
                avc3 = [ec.strip() for ec in vl.split(' ') if ec.strip()]
            else:
                avc3 = vl.strip().split('\n')
            server = self._sv.new_device_info_writer.name
            for cp in avc3:
                if cp:
                    self.assertTrue(server in avc3)
                    self.assertTrue(server2 in avc3)

            self.assertEqual('', er)

        el.close()
        sv2.tearDown()

    def test_list_comp_available(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
#        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            ('nxsconfig list -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cmd in commands:
            vl, er = self.runtest(cmd)

            if "-n" in cmd or "--no-newlines" in cmd:
                avc3 = [ec.strip() for ec in vl.split(' ') if ec.strip()]
            else:
                avc3 = vl.split('\n')

            for cp in avc3:
                if cp:
                    self.assertTrue(cp in avc2)

            for cp in avc2:
                if not cp.startswith("__"):
                    self.assertTrue(cp in avc3)

            self.assertEqual('', er)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()

        avc3 = el.availableComponents()
        self.assertTrue(isinstance(avc3, list))
        for cp in avc:
            self.assertTrue(cp in avc3)
        self.assertTrue(name not in avc3)

        el.close()

    def test_components(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "</definition>"
        xml3 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry3'/>" \
               "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        name3 = name + '_3'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        self.setXML(el, xml3)
        self.assertEqual(el.storeComponent(name3), None)
        self.__cmps.append(name3)
        names = [name, name2, name3]
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        commands = [
            ('nxsconfig components -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
        for cmd in commands:
            for nm in names:
                cd = list(cmd)
                cd.append(nm)
                vl, er = self.runtest(cd)

                if "-n" in cmd or "--no-newlines" in cmd:
                    avc3 = [ec.strip() for ec in vl.split(' ')
                            if ec.strip()]
                else:
                    avc3 = vl.strip().split('\n')

                self.assertTrue(nm in avc3)
                self.assertEqual(len(avc3), 1)

                self.assertEqual('', er)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop(-1)
        self.assertEqual(el.deleteComponent(name3), None)
        self.__cmps.pop()

        el.close()

    def test_components_dependent(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "$components.%s</definition>"
        xml3 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry3'/>" \
               "$components.%s</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        name3 = name + '_3'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2 % name)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        self.setXML(el, xml3 % name)
        self.assertEqual(el.storeComponent(name3), None)
        self.__cmps.append(name3)
        names = [name2, name3]
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        commands = [
            ('nxsconfig components -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
        for cmd in commands:
            for nm in names:
                cd = list(cmd)
                cd.append(nm)
                vl, er = self.runtest(cd)

                if "-n" in cmd or "--no-newlines" in cmd:
                    avc3 = [ec.strip() for ec in vl.split(' ')
                            if ec.strip()]
                else:
                    avc3 = vl.strip().split('\n')

                self.assertTrue(nm in avc3)
                self.assertTrue(name in avc3)
                self.assertEqual(len(avc3), 2)

                self.assertEqual('', er)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop(-1)
        self.assertEqual(el.deleteComponent(name3), None)
        self.__cmps.pop()

        el.close()

    def test_data_read(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()

        vrs = [
            '{"myentry":"entry1"}',
            '{"myentry":"entry2", "sample_name":"water"}',
            '{"formula":"H20", "sample_name":"water"}',
        ]

        commands = [
            ('nxsconfig data -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig data --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
        for cmd in commands:
            for i, vr in enumerate(vrs):
                el.variables = vr
                vl, er = self.runtest(cmd)

                avc3 = vl.strip()
                self.assertEqual(vr, avc3)

                self.assertEqual('', er)

        el.close()

    def test_data_write(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()

        vrs = [
            '{"myentry":"entry1"}',
            '{"myentry":"entry2", "sample_name":"water"}',
            '{"formula":"H20", "sample_name":"water"}',
        ]

        commands = [
            ('nxsconfig data -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig data --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
        for cmd in commands:
            for i, vr in enumerate(vrs):
                cd = list(cmd)
                cd.append(vr)
                vl, er = self.runtest(cd)

                rvr = el.variables.strip()
                self.assertEqual(vr, rvr)

                self.assertEqual('', er)
                self.assertEqual(vr, vl.strip())

        el.close()

    def test_variables(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
            "<definition><group name=\"$var.entryname#'scan'$var.serialno\" " \
            " type=\"NXentry\"/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'>$var.myfield" \
               "</group>" \
               "</definition>"
        xml3 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry3'/>" \
               "</definition>"
        var = ["entryname", "serialno"]
        var2 = ["myfield"]
        var3 = []
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        name3 = name + '_3'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        self.setXML(el, xml3)
        self.assertEqual(el.storeComponent(name3), None)
        self.__cmps.append(name3)
        names = [name, name2, name3]
        vrs = [var, var2, var3]
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        commands = [
            ('nxsconfig variables -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
        for cmd in commands:
            for i, nm in enumerate(names):
                cd = list(cmd)
                cd.append(nm)
                vl, er = self.runtest(cd)

                if "-n" in cmd or "--no-newlines" in cmd:
                    avc3 = [ec.strip() for ec in vl.split(' ')
                            if ec.strip()]
                else:
                    avc3 = [ec for ec in vl.strip().split('\n') if ec]

                self.assertEqual(sorted(avc3), sorted(vrs[i]))

                self.assertEqual('', er)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop(-1)
        self.assertEqual(el.deleteComponent(name3), None)
        self.__cmps.pop()

        el.close()

    def test_variables_man(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()
        man = el.mandatoryComponents()
        if man:
            return

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
            "<definition><group name=\"$var.entryname#'scan'$var.serialno\" " \
            " type=\"NXentry\"/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'>$var.myfield" \
               "</group>" \
               "</definition>"
        xml3 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry3'/>" \
               "</definition>"
        var = ["entryname", "serialno"]
        var2 = ["myfield"]
        var3 = []
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        name3 = name + '_3'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        self.setXML(el, xml3)
        self.assertEqual(el.storeComponent(name3), None)
        self.__cmps.append(name3)
        names = ['', name2, name3]
        vrs = [[], var2, var3]
        avc2 = el.availableComponents()
        self.assertEqual(el.setMandatoryComponents([name]), None)
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        commands = [
            ('nxsconfig variables -m -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables -m -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables -m --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables -m -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables -m -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables -m --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables -m --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables -m --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables --mandatory -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables --mandatory -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables --mandatory --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables --mandatory -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables --mandatory -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables --mandatory --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables --mandatory --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig variables --mandatory --no-newlines'
             '  --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
        for cmd in commands:
            for i, nm in enumerate(names):
                cd = list(cmd)
                if nm:
                    cd.append(nm)
                vl, er = self.runtest(cd)

                if "-n" in cmd or "--no-newlines" in cmd:
                    avc3 = [ec.strip() for ec in vl.split(' ')
                            if ec.strip()]
                else:
                    avc3 = [ec for ec in vl.strip().split('\n') if ec]
                res = list(vrs[i])
                res.extend(var)
                self.assertEqual(sorted(avc3), sorted(res))

                self.assertEqual('', er)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop(-1)
        self.assertEqual(el.deleteComponent(name3), None)
        self.__cmps.pop()

        el.close()

    def test_components_two_dependent(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "$components.%s</definition>"
        xml3 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry3'/>" \
               "$components.%s</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        name3 = name + '_3'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2 % name)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        self.setXML(el, xml3 % name2)
        self.assertEqual(el.storeComponent(name3), None)
        self.__cmps.append(name3)
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        commands = [
            ('nxsconfig components -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
        nm = name3
        for cmd in commands:
            cd = list(cmd)
            cd.append(nm)
            vl, er = self.runtest(cd)

            if "-n" in cmd or "--no-newlines" in cmd:
                avc3 = [ec.strip() for ec in vl.split(' ')
                        if ec.strip()]
            else:
                avc3 = vl.strip().split('\n')

            self.assertTrue(nm in avc3)
            self.assertTrue(name in avc3)
            self.assertTrue(name2 in avc3)
            self.assertEqual(len(avc3), 3)

            self.assertEqual('', er)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop(-1)
        self.assertEqual(el.deleteComponent(name3), None)
        self.__cmps.pop()

        el.close()

    def test_components_cyclic_dependent(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "$components.%s</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "$components.%s</definition>"
        xml3 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry3'/>" \
               "$components.%s</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        name3 = name + '_3'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
        self.setXML(el, xml % name3)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2 % name)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        self.setXML(el, xml3 % name2)
        self.assertEqual(el.storeComponent(name3), None)
        self.__cmps.append(name3)
        names = [name, name2, name3]
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        commands = [
            ('nxsconfig components -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig components --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
        for cmd in commands:
            for nm in names:
                cd = list(cmd)
                cd.append(nm)
                vl, er = self.runtest(cd)

                if "-n" in cmd or "--no-newlines" in cmd:
                    avc3 = [ec.strip() for ec in vl.split(' ')
                            if ec.strip()]
                else:
                    avc3 = vl.strip().split('\n')

                self.assertTrue(name in avc3)
                self.assertTrue(name2 in avc3)
                self.assertTrue(name3 in avc3)
                self.assertEqual(len(avc3), 3)

                self.assertEqual('', er)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop(-1)
        self.assertEqual(el.deleteComponent(name3), None)
        self.__cmps.pop()

        el.close()

    def test_delete_comp(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        #        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)

        commands = [
            ('nxsconfig delete -f  -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete -f  --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cmd in commands:
            self.setXML(el, xml2)
            self.assertEqual(el.storeComponent(name2), None)
            self.__cmps.append(name2)
            avc2 = el.availableComponents()
            vl, er = self.runtest(cmd)
            avc3 = el.availableComponents()
            self.assertEqual((list(set(avc2) - set(avc3))), [name2])

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop()

        el.close()

    def test_delete_profile(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableSelections()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_profile"
        jsn = '{"DataSourceSelection": ' \
              '"{\\"lmbd01\\": false, \\"exp_mca01\\": true}"}'
        jsn2 = '{"ComponentSelection": "{\\"pilatus\\": true}"}'
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        #        print avc
        self.setSelection(el, jsn)
        self.assertEqual(el.storeSelection(name), None)
        self.__cmps.append(name)

        commands = [
            ('nxsconfig delete -f -r  -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete -f --profiles --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cmd in commands:
            self.setSelection(el, jsn2)
            self.assertEqual(el.storeSelection(name2), None)
            self.__cmps.append(name2)
            avc2 = el.availableSelections()
            vl, er = self.runtest(cmd)
            avc3 = el.availableSelections()
            self.assertEqual((list(set(avc2) - set(avc3))), [name2])

        self.assertEqual(el.deleteSelection(name), None)
        self.__cmps.pop()

        el.close()

    def test_delete_ds(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableDataSources()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_datasource"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        #        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeDataSource(name), None)
        self.__ds.append(name)

        commands = [
            ('nxsconfig delete -f -d -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete -f -d --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete -f --datasource -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete -f --datasource --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cmd in commands:
            self.setXML(el, xml2)
            self.assertEqual(el.storeDataSource(name2), None)
            self.__ds.append(name2)
            avc2 = el.availableDataSources()
            vl, er = self.runtest(cmd)
            avc3 = el.availableDataSources()
            self.assertEqual((list(set(avc2) - set(avc3))), [name2])

        self.assertEqual(el.deleteDataSource(name), None)
        self.__ds.pop()

        el.close()

    def test_delete_comp_noforce_pipe(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        #        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)

        commands = [
            ('nxsconfig delete -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
        ]
        answers = ['\n', 'Y\n', 'y\n'',N\n', 'n\n']
        for cmd in commands:
            for ans in answers:
                self.setXML(el, xml2)
                self.assertEqual(el.storeComponent(name2), None)
                self.__cmps.append(name2)
                avc2 = el.availableComponents()
                vl, er, etxt = self.runtestexcept(cmd, SystemExit)
                self.assertEqual(vl[:17], 'Remove Component ')
                self.assertEqual(
                    er,
                    "Error: EOF when reading a line. "
                    "Consider to use the --force option \n")
                avc3 = el.availableComponents()
                self.assertEqual((list(set(avc2) - set(avc3))), [])

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop()

        el.close()

    def test_delete_ds_noforce_pipe(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableDataSources()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_datasource"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        #        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeDataSource(name), None)
        self.__ds.append(name)

        commands = [
            ('nxsconfig delete -d -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete -d --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --datasource -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --datasource --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
        ]
        answers = ['\n', 'Y\n', 'y\n'',N\n', 'n\n']
        for cmd in commands:
            for ans in answers:
                self.setXML(el, xml2)
                self.assertEqual(el.storeDataSource(name2), None)
                self.__cmps.append(name2)
                avc2 = el.availableDataSources()
                vl, er, etxt = self.runtestexcept(cmd, SystemExit)
                self.assertEqual(vl[:17], 'Remove DataSource')
                self.assertEqual(
                    er,
                    "Error: EOF when reading a line. "
                    "Consider to use the --force option \n")
                avc3 = el.availableDataSources()
                self.assertEqual((list(set(avc2) - set(avc3))), [])

        self.assertEqual(el.deleteDataSource(name), None)
        self.__ds.pop()

        el.close()

    def test_delete_profile_noforce_pipe(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableSelections()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_profile"
        jsn = '{"DataSourceSelection": ' \
              '"{\\"lmbd01\\": false, \\"exp_mca01\\": true}"}'
        jsn2 = '{"ComponentSelection": "{\\"pilatus\\": true}"}'
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        #        print avc
        self.setSelection(el, jsn)
        self.assertEqual(el.storeSelection(name), None)
        self.__sels.append(name)

        commands = [
            ('nxsconfig delete -r -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete -r --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --profiles -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --profiles --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
        ]
        answers = ['\n', 'Y\n', 'y\n'',N\n', 'n\n']
        for cmd in commands:
            for ans in answers:
                self.setXML(el, jsn2)
                self.assertEqual(el.storeSelection(name2), None)
                self.__cmps.append(name2)
                avc2 = el.availableSelections()
                vl, er, etxt = self.runtestexcept(cmd, SystemExit)
                self.assertEqual(vl[:14], 'Remove Profile')
                self.assertEqual(
                    er,
                    "Error: EOF when reading a line. "
                    "Consider to use the --force option \n")
                avc3 = el.availableSelections()
                self.assertEqual((list(set(avc2) - set(avc3))), [])

        self.assertEqual(el.deleteSelection(name), None)
        self.__sels.pop()

        el.close()

    def test_delete_comp_noforce(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        #        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)

        commands = [
            ('nxsconfig delete -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
        ]
        answers = ['\n', 'Y\n', 'y\n']
        for cmd in commands:
            for ans in answers:
                self.setXML(el, xml2)
                self.assertEqual(el.storeComponent(name2), None)
                self.__cmps.append(name2)
                avc2 = el.availableComponents()
                vl, er = self.runtest(cmd, ans)
                self.assertEqual(vl[:17], 'Remove Component ')
                self.assertEqual('', er)
                avc3 = el.availableComponents()
                self.assertEqual((list(set(avc2) - set(avc3))), [name2])

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop()

        el.close()

    def test_delete_ds_noforce(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableDataSources()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_datasource"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        #        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeDataSource(name), None)
        self.__ds.append(name)

        commands = [
            ('nxsconfig delete -d -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete -d --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --datasource -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --datasource --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
        ]
        answers = ['\n', 'Y\n', 'y\n']
        for cmd in commands:
            for ans in answers:
                self.setXML(el, xml2)
                self.assertEqual(el.storeDataSource(name2), None)
                self.__cmps.append(name2)
                avc2 = el.availableDataSources()
                vl, er = self.runtest(cmd, ans)
                self.assertEqual(vl[:17], 'Remove DataSource')
                self.assertEqual('', er)
                avc3 = el.availableDataSources()
                self.assertEqual((list(set(avc2) - set(avc3))), [name2])

        self.assertEqual(el.deleteDataSource(name), None)
        self.__ds.pop()

        el.close()

    def test_delete_profile_noforce(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableSelections()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_profile"
        jsn = '{"DataSourceSelection": ' \
              '"{\\"lmbd01\\": false, \\"exp_mca01\\": true}"}'
        jsn2 = '{"ComponentSelection": "{\\"pilatus\\": true}"}'
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        #        print avc
        self.setSelection(el, jsn)
        self.assertEqual(el.storeSelection(name), None)
        self.__sels.append(name)

        commands = [
            ('nxsconfig delete -r -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete -r --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --profiles -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --profiles --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
        ]
        answers = ['\n', 'Y\n', 'y\n']
        for cmd in commands:
            for ans in answers:
                self.setSelection(el, jsn2)
                self.assertEqual(el.storeSelection(name2), None)
                self.__cmps.append(name2)
                avc2 = el.availableSelections()
                vl, er = self.runtest(cmd, ans)
                self.assertEqual(vl[:14], 'Remove Profile')
                self.assertEqual('', er)
                avc3 = el.availableSelections()
                self.assertEqual((list(set(avc2) - set(avc3))), [name2])

        self.assertEqual(el.deleteSelection(name), None)
        self.__sels.pop()

        el.close()

    def test_delete_comp_noforce_no(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        #        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)

        commands = [
            ('nxsconfig delete -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
        ]
        answers = ['N\n', 'n\n']
        for cmd in commands:
            for ans in answers:
                self.setXML(el, xml2)
                self.assertEqual(el.storeComponent(name2), None)
                self.__cmps.append(name2)
                avc2 = el.availableComponents()
                vl, er = self.runtest(cmd, ans)
                self.assertEqual(vl[:17], 'Remove Component ')
                self.assertEqual('', er)
                avc3 = el.availableComponents()
                self.assertEqual((list(set(avc2) - set(avc3))), [])

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop()

        el.close()

    def test_delete_ds_noforce_no(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableDataSources()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        #        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeDataSource(name), None)
        self.__ds.append(name)

        commands = [
            ('nxsconfig delete -d -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete -d --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --datasource -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --datasource --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
        ]
        answers = ['N\n', 'n\n']
        for cmd in commands:
            for ans in answers:
                self.setXML(el, xml2)
                self.assertEqual(el.storeDataSource(name2), None)
                self.__cmps.append(name2)
                avc2 = el.availableDataSources()
                vl, er = self.runtest(cmd, ans)
                self.assertEqual(vl[:17], 'Remove DataSource')
                self.assertEqual('', er)
                avc3 = el.availableDataSources()
                self.assertEqual((list(set(avc2) - set(avc3))), [])

        self.assertEqual(el.deleteDataSource(name), None)
        self.__ds.pop()

        el.close()

    # \brief It tests XMLConfigurator
    def test_delete_profile_noforce_no(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableSelections()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_profile"
        jsn = '{"DataSourceSelection": ' \
              '"{\\"lmbd01\\": false, \\"exp_mca01\\": true}"}'
        jsn2 = '{"ComponentSelection": "{\\"pilatus\\": true}"}'
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        #        print avc
        self.setSelection(el, jsn)
        self.assertEqual(el.storeSelection(name), None)
        self.__sels.append(name)

        commands = [
            ('nxsconfig delete -r -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete -r --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --profiles -s %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
            ('nxsconfig delete --profiles --server %s %s'
             % (self._sv.new_device_info_writer.name, name2)).split(),
        ]
        answers = ['N\n', 'n\n']
        for cmd in commands:
            for ans in answers:
                self.setSelection(el, jsn2)
                self.assertEqual(el.storeSelection(name2), None)
                self.__cmps.append(name2)
                avc2 = el.availableSelections()
                vl, er = self.runtest(cmd, ans)
                self.assertEqual(vl[:14], 'Remove Profile')
                self.assertEqual('', er)
                avc3 = el.availableSelections()
                self.assertEqual((list(set(avc2) - set(avc3))), [])

        self.assertEqual(el.deleteSelection(name), None)
        self.__sels.pop()

        el.close()

    def test_list_comp_available_private(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "__mcs_test_component__"
        name2 = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "</definition>"
        while name in avc:
            name = name + '_1__'
        while name2 in avc:
            name2 = name2 + '_2'
#        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            ('nxsconfig list -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cmd in commands:
            vl, er = self.runtest(cmd)

            if "-n" in cmd or "--no-newlines" in cmd:
                avc3 = [ec.strip() for ec in vl.split(' ') if ec.strip()]
            else:
                avc3 = vl.split('\n')

            for cp in avc3:
                if cp:
                    self.assertTrue(cp in avc2)

            for cp in avc2:
                if not cp.startswith("__"):
                    self.assertTrue(cp in avc3)

            self.assertEqual('', er)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()

        avc3 = el.availableComponents()
        self.assertTrue(isinstance(avc3, list))
        for cp in avc:
            self.assertTrue(cp in avc3)
        self.assertTrue(name not in avc3)

        el.close()

    def test_list_comp_available_private2(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "__mcs_test_component__"
        name2 = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "</definition>"
        while name in avc:
            name = name + '_1__'
        while name2 in avc:
            name2 = name2 + '_2'
#        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            ('nxsconfig list -p -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -p -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -p --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -p -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -p -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -p --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -p --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -p --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --private -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --private -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --private --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --private -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --private -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --private --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --private --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --private --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cmd in commands:
            vl, er = self.runtest(cmd)

            if "-n" in cmd or "--no-newlines" in cmd:
                avc3 = [ec.strip() for ec in vl.split(' ') if ec.strip()]
            else:
                avc3 = vl.split('\n')

            for cp in avc3:
                if cp:
                    self.assertTrue(cp in avc2)

            for cp in avc2:
                if cp.startswith("__"):
                    self.assertTrue(cp in avc3)

            self.assertEqual('', er)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()

        avc3 = el.availableComponents()
        self.assertTrue(isinstance(avc3, list))
        for cp in avc:
            self.assertTrue(cp in avc3)
        self.assertTrue(name not in avc3)

        el.close()

    def test_list_comp_available_mandatory(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        # man =

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_1'
        while name2 in avc:
            name2 = name2 + '_2'
#        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        avc2 = el.availableComponents()
        self.assertEqual(el.setMandatoryComponents([name]), None)
        man2 = el.mandatoryComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            ('nxsconfig list -m -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -m -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -m --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -m -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -m -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -m --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -m --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -m --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --mandatory -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --mandatory -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --mandatory --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --mandatory -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --mandatory -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --mandatory --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --mandatory --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --mandatory --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cmd in commands:
            vl, er = self.runtest(cmd)

            if "-n" in cmd or "--no-newlines" in cmd:
                avc3 = [ec.strip() for ec in vl.split(' ') if ec.strip()]
            else:
                avc3 = vl.split('\n')

            for cp in avc3:
                if cp:
                    self.assertTrue(cp in man2)

            for cp in man2:
                self.assertTrue(cp in avc3)

            self.assertEqual('', er)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()

        el.close()

    def test_list_datasources_available(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableDataSources()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_datasource"
        xml = "<?xml version='1.0' encoding='utf-8'?><definition>" \
              "<datasource type='TANGO' name='testds1'/></definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?><definition>" \
               "<datasource type='CLIENT' name='testds1'/></definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
#        print avc
        self.setXML(el, xml)
        self.assertEqual(el.storeDataSource(name), None)
        self.__ds.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeDataSource(name2), None)
        self.__ds.append(name2)
        avc2 = el.availableDataSources()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.datasources([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            ('nxsconfig list -d -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -d -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -d --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -d -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -d -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -d --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -d --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -d --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --datasources -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --datasources -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --datasources --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --datasources -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --datasources -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --datasources --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --datasources --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --datasources --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
        for cmd in commands:
            vl, er = self.runtest(cmd)

            if "-n" in cmd or "--no-newlines" in cmd:
                avc3 = [ec.strip() for ec in vl.split(' ') if ec.strip()]
            else:
                avc3 = vl.split('\n')

            for cp in avc3:
                if cp:
                    self.assertTrue(cp in avc2)

            for cp in avc2:
                self.assertTrue(cp in avc3)

            self.assertEqual('', er)

        self.assertEqual(el.deleteDataSource(name), None)
        self.__ds.pop(-2)
        self.assertEqual(el.deleteDataSource(name2), None)
        self.__ds.pop()

        el.close()

    def test_list_profiles_available(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableSelections()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_profile"
        jsn = '{"DataSourceSelection": ' \
              '"{\\"lmbd01\\": false, \\"exp_mca01\\": true}"}'
        jsn2 = '{"ComponentSelection": "{\\"pilatus\\": true}"}'
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
#        print avc
        self.setSelection(el, jsn)
        self.assertEqual(el.storeSelection(name), None)
        self.__sels.append(name)
        self.setSelection(el, jsn2)
        self.assertEqual(el.storeSelection(name2), None)
        self.__sels.append(name2)
        avc2 = el.availableSelections()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.selections([name])
        self.assertEqual(cpx[0], jsn)

        commands = [
            ('nxsconfig list -r -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -r -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -r --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -r -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -r -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -r --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -r --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list -r --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --profiles -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --profiles -n -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --profiles --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --profiles -n --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --profiles -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --profiles --no-newlines  -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --profiles --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig list --profiles --no-newlines  --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
        for cmd in commands:
            vl, er = self.runtest(cmd)

            if "-n" in cmd or "--no-newlines" in cmd:
                avc3 = [ec.strip() for ec in vl.split(' ') if ec.strip()]
            else:
                avc3 = vl.split('\n')

            for cp in avc3:
                if cp:
                    self.assertTrue(cp in avc2)

            for cp in avc2:
                self.assertTrue(cp in avc3)

            self.assertEqual('', er)

        self.assertEqual(el.deleteSelection(name), None)
        self.__sels.pop(-1)
        self.assertEqual(el.deleteSelection(name2), None)
        self.__sels.pop()

        el.close()

    def test_show_comp_av(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<definition><group type='NXentry'/>" \
              "\n</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field type='NXentry2'/>" \
               "$datasources.sl1right</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
#        print avc
        cmps = {name: xml, name2: xml2}

        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            'nxsconfig show %s -s %s',
            'nxsconfig show %s --server %s',
            'nxsconfig show %s -s %s',
            'nxsconfig show %s --server %s',
        ]
        for scmd in commands:
            for nm in cmps.keys():
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                self.assertEqual(vl.strip(), cmps[nm])
                self.assertEqual(er, "")

        for scmd in commands:
            nm = name3
            cmd = (scmd % (nm, self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            er = er.strip()

            self.assertEqual(vl, "")
            self.assertEqual(
                er,
                "Error: Component '%s' not stored in the configuration server"
                % name3)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2),
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()

            self.assertEqual(vl.replace(">\n<", "><").replace("> <", "><"),
                             ("%s\n%s" % (cmps[name], cmps[name2])).replace(
                                 ">\n<", "><").replace("> <", "><"))
            self.assertEqual(er, "")

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name3),
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            er = er.strip()

            self.assertEqual(vl, "")
            self.assertEqual(
                er,
                "Error: Component '%s' not stored in the configuration server"
                % name3)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()

        el.close()

    def test_record(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<definition><group type='NXentry'/>" \
              "\n</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field name='data'>" \
               "<datasource name='sl1right' type='CLIENT'>" \
               "<record name='motor_1'/>" \
               "</datasource>" \
               "<strategy mode='INIT'/>" \
               "</field>" \
               "</definition>"
        xml3 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition>" \
               "<field name='data'>" \
               "<strategy mode='STEP'/>" \
               "<datasource name='sl2bottom' type='CLIENT'>" \
               "<record name='motor_2'/>" \
               "</datasource>" \
               "</field>" \
               "<field name='data2'>" \
               "<datasource name='sl2top' type='TANGO'>" \
               "<device hostname='haso.desy.de' member='attribute' " \
               "name='p09/motor/exp.01' port='10000' " \
               "encoding='LIMA_VIDEO_IMAGE'/>" \
               "<record name='Position'/>" \
               "</datasource>" \
               "<strategy mode='FINAL'/>" \
               "</field>" \
               "</definition>"
        xml4 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field name='data'>" \
               "<datasource name='sl3right' type='PYEVAL'>" \
               "<result>ds.result = 25.6" \
               "</result>" \
               "</datasource>" \
               "<strategy mode='INIT'/>" \
               "</field>" \
               "</definition>"
        xml5 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field name='data'>" \
               "<datasource name='sl1right' type='DB'>" \
               "<database dbname='mydb' dbtype='PGSQL'/>" \
               "<query format='IMAGE'>SELECT * from weather limit 3" \
               "</query>" \
               "</datasource>" \
               "<strategy mode='FINAL'/>" \
               "</field>" \
               "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        name4 = name + '_4'
        name5 = name + '_5'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
        while name4 in avc:
            name4 = name4 + '_4'
        while name5 in avc:
            name5 = name5 + '_5'
            #        print avc
        dss = {
            name: [],
            name2: ["motor_1"],
            name3: ["motor_2",
                    "haso.desy.de:10000/p09/motor/exp.01/Position"],
            name4: ["25.6"],
            name5: ['SELECT * from weather limit 3'],
        }

        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        self.setXML(el, xml3)
        self.assertEqual(el.storeComponent(name3), None)
        self.__cmps.append(name3)
        self.setXML(el, xml4)
        self.assertEqual(el.storeComponent(name4), None)
        self.__cmps.append(name4)
        self.setXML(el, xml5)
        self.assertEqual(el.storeComponent(name5), None)
        self.__cmps.append(name5)

        commands = [
            'nxsconfig record %s -s %s',
            'nxsconfig record %s --server %s',
            'nxsconfig record %s --no-newlines -s %s',
            'nxsconfig record %s -n --server %s',
            'nxsconfig record %s -n -s %s',
            'nxsconfig record %s --no-newlines --server %s',
        ]
        for scmd in commands:
            for nm in dss.keys():
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                if "-n" in cmd or "--no-newlines" in cmd:
                    if len(dss[nm]) > 1:
                        avc3 = [ec.strip() for ec in vl.split(' ')
                                if ec.strip()]
                    else:
                        avc3 = [ec.strip() for ec in [vl]
                                if ec.strip()]
                else:
                    avc3 = [ec for ec in vl.split('\n') if ec]
                self.assertEqual(sorted(avc3), sorted(dss[nm]))
                self.assertEqual(er, "")

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-3)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name3), None)
        self.__cmps.pop(-1)
        self.assertEqual(el.deleteComponent(name4), None)
        self.__cmps.pop()

        el.close()

    def test_record_sep(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()
        dsavc = el.availableDatasources()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        dname = "mcs_test_datasources"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
            "<definition><field name='data'>" \
            "<strategy mode='INIT'/>" \
            "$datasources.%s" \
            "</field>" \
            "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
            "<definition>" \
            "<field name='data'>" \
            "<strategy mode='STEP'/>" \
            "$datasources.%s" \
            "</field>" \
            "<field name='data2'>" \
            "<strategy mode='FINAL'/>" \
            "$datasources.%s" \
            "</field>" \
            "</definition>"
        xml3 = "<?xml version='1.0' encoding='utf-8'?>" \
            "<definition><field name='data'>" \
            "<strategy mode='INIT'/>" \
            "$datasources.%s" \
            "</field>" \
            "</definition>"
        xml4 = "<?xml version='1.0' encoding='utf-8'?>" \
            "<definition><field name='data'>" \
            "$datasources.%s" \
            "<strategy mode='FINAL'/>" \
            "</field>" \
            "</definition>"

        xds = [
            "<datasource name='%s' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>",
            "<datasource name='%s' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>",
            "<datasource name='%s' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' "
            "encoding='LIMA_VIDEO_IMAGE'/>"
            "<record name='Position'/>"
            "</datasource>",
            "<datasource name='%s' type='PYEVAL'>"
            "<result>ds.result = 25.6"
            "</result>"
            "</datasource>",
            "<datasource name='%s' type='DB'>"
            "<database dbname='mydb' dbtype='PGSQL'/>"
            "<query format='IMAGE'>SELECT * from weather limit 3"
            "</query>"
            "</datasource>"
        ]

        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        name4 = name + '_4'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
        while name4 in avc:
            name4 = name4 + '_4'
            #        print avc
        dsname = [dname] * 5
        while dsname[0] in dsavc:
            dsname[0] = dsname[0] + '_1'
        dsname[1] = dsname[0] + '_2'
        dsname[2] = dsname[0] + '_3'
        dsname[3] = dsname[0] + '_4'
        dsname[4] = dsname[0] + '_5'
        while dsname[1] in dsavc:
            dsname[1] = dsname[1] + '_2'
        while dsname[2] in dsavc:
            dsname[2] = dsname[2] + '_2'
        while dsname[3] in dsavc:
            dsname[3] = dsname[3] + '_3'
        while dsname[4] in dsavc:
            dsname[4] = dsname[4] + '_4'
        dss = {
            name: [dsname[0]],
            name2: [dsname[1], dsname[2]],
            name3: [dsname[3]],
            name4: [dsname[4]],
        }
        rec = {
            name: ["motor_1"],
            name2: ["motor_2",
                    "haso.desy.de:10000/p09/motor/exp.01/Position"],
            name3: ["25.6"],
            name4: ['SELECT * from weather limit 3'],
        }

        self.setXML(el, xml % dss[name])
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2 % tuple(dss[name2]))
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        self.setXML(el, xml3 % dss[name3])
        self.assertEqual(el.storeComponent(name3), None)
        self.__cmps.append(name3)
        self.setXML(el, xml4 % dss[name4])
        self.assertEqual(el.storeComponent(name4), None)
        self.__cmps.append(name4)

        dsnp = len(xds)
        for i in range(dsnp):
            self.setXML(el, xds[i] % dsname[i])
            self.assertEqual(el.storeDataSource(dsname[i]), None)
            self.__ds.append(dsname[i])

        commands = [
            'nxsconfig record %s -s %s',
            'nxsconfig record %s --server %s',
            'nxsconfig record %s --no-newlines -s %s',
            'nxsconfig record %s -n --server %s',
            'nxsconfig record %s -n -s %s',
            'nxsconfig record %s --no-newlines --server %s',
        ]
        for scmd in commands:
            for nm in dss.keys():
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                if "-n" in cmd or "--no-newlines" in cmd:
                    if len(dss[nm]) > 1:
                        avc3 = [ec.strip() for ec in vl.split(' ')
                                if ec.strip()]
                    else:
                        avc3 = [ec.strip() for ec in [vl]
                                if ec.strip()]
                else:
                    avc3 = [ec for ec in vl.split('\n') if ec]
                self.assertEqual(sorted(avc3), sorted(rec[nm]))
                self.assertEqual(er, "")

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-3)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name3), None)
        self.__cmps.pop(-1)
        self.assertEqual(el.deleteComponent(name4), None)
        self.__cmps.pop()

        el.close()

    def test_record_dss(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        dsavc = el.availableDatasources()

        dname = "mcs_test_datasources"
        xds = [
            "<datasource name='%s' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>",
            "<datasource name='%s' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>",
            "<datasource name='%s' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' "
            "encoding='LIMA_VIDEO_IMAGE'/>"
            "<record name='Position'/>"
            "</datasource>",
            "<datasource name='%s' type='PYEVAL'>"
            "<result>ds.result = 25.6"
            "</result>"
            "</datasource>",
            "<datasource name='%s' type='DB'>"
            "<database dbname='mydb' dbtype='PGSQL'/>"
            "<query format='IMAGE'>SELECT * from weather limit 3"
            "</query>"
            "</datasource>"
        ]

        dsname = [dname] * 5
        while dsname[0] in dsavc:
            dsname[0] = dsname[0] + '_1'
        dsname[1] = dsname[0] + '_2'
        dsname[2] = dsname[0] + '_3'
        dsname[3] = dsname[0] + '_4'
        dsname[4] = dsname[0] + '_5'
        while dsname[1] in dsavc:
            dsname[1] = dsname[1] + '_2'
        while dsname[2] in dsavc:
            dsname[2] = dsname[2] + '_2'
        while dsname[3] in dsavc:
            dsname[3] = dsname[3] + '_3'
        while dsname[4] in dsavc:
            dsname[4] = dsname[4] + '_4'
        rec = {
            dsname[0]: ["motor_1"],
            dsname[1]: ["motor_2"],
            dsname[2]: [
                "haso.desy.de:10000/p09/motor/exp.01/Position"],
            dsname[3]: ["25.6"],
            dsname[4]: ['SELECT * from weather limit 3'],
        }

        dsnp = len(xds)
        for i in range(dsnp):
            self.setXML(el, xds[i] % dsname[i])
            self.assertEqual(el.storeDataSource(dsname[i]), None)
            self.__ds.append(dsname[i])

        commands = [
            'nxsconfig record %s -d -s %s',
            'nxsconfig record %s -d --server %s',
            'nxsconfig record %s -d --no-newlines -s %s',
            'nxsconfig record %s -d -n --server %s',
            'nxsconfig record %s -d -n -s %s',
            'nxsconfig record %s -d --no-newlines --server %s',
            'nxsconfig record %s --datasources -s %s',
            'nxsconfig record %s --datasources --server %s',
            'nxsconfig record %s --datasources --no-newlines -s %s',
            'nxsconfig record %s --datasources -n --server %s',
            'nxsconfig record %s --datasources -n -s %s',
            'nxsconfig record %s --datasources --no-newlines --server %s',
        ]
        for scmd in commands:
            for nm in dsname:
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                if "-n" in cmd or "--no-newlines" in cmd:
                    if len(rec[nm]) > 1:
                        avc3 = [ec.strip() for ec in vl.split(' ')
                                if ec.strip()]
                    else:
                        avc3 = [ec.strip() for ec in [vl]
                                if ec.strip()]
                else:
                    avc3 = [ec for ec in vl.split('\n') if ec]
                self.assertEqual(sorted(avc3), sorted(rec[nm]))
                self.assertEqual(er, "")

        el.close()

    def test_sources(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<definition><group type='NXentry'/>" \
              "\n</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field name='data'>" \
               "<datasource name='sl1right' type='client'>" \
               "</datasource>" \
               "</field>" \
               "</definition>"
        xml3 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition>" \
               "<field name='data'>" \
               "<datasource name='sl2bottom' type='client'>" \
               "</datasource>" \
               "</field>" \
               "<field name='data2'>" \
               "<datasource name='sl2top' type='tango'>" \
               "</datasource>" \
               "</field>" \
               "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
        dss = {
            name: [],
            name2: ["sl1right"],
            name3: ["sl2top", "sl2bottom"],
        }

        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        self.setXML(el, xml3)
        self.assertEqual(el.storeComponent(name3), None)
        self.__cmps.append(name3)

        commands = [
            'nxsconfig sources %s -s %s',
            'nxsconfig sources %s --server %s',
            'nxsconfig sources %s -s %s',
            'nxsconfig sources %s --server %s',
            'nxsconfig sources %s --no-newlines -s %s',
            'nxsconfig sources %s -n --server %s',
            'nxsconfig sources %s -n -s %s',
            'nxsconfig sources %s --no-newlines --server %s',
        ]
        for scmd in commands:
            for nm in dss.keys():
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                if "-n" in cmd or "--no-newlines" in cmd:
                    avc3 = [ec.strip() for ec in vl.split(' ')
                            if ec.strip()]
                else:
                    avc3 = [ec for ec in vl.split('\n') if ec]
                self.assertEqual(sorted(avc3), sorted(dss[nm]))
                self.assertEqual(er, "")

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop(-1)
        self.assertEqual(el.deleteComponent(name3), None)
        self.__cmps.pop()

        el.close()

    def test_sources_sep(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()
        dsavc = el.availableDatasources()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        dname = "mcs_test_datasources"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
            "<definition><field name='data0'>" \
            "$datasources.%s" \
            "</field>" \
            "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
            "<definition><field name='data'>" \
            "$datasources.%s" \
            "</field>" \
            "</definition>"
        xml3 = "<?xml version='1.0' encoding='utf-8'?>" \
            "<definition>" \
            "<field name='data'>" \
            "$datasources.%s" \
            "</field>" \
            "<field name='data2'>" \
            "$datasources.%s" \
            "</field>" \
            "</definition>"
        xds = [
            '<datasource name="%s" type="CLIENT"><record name="r1" />'
            '</datasource>',
            '<datasource name="%s" type="CLIENT"><record name="r2" />'
            '</datasource>',
            '<datasource name="%s" type="CLIENT"><record name="r3" />'
            '</datasource>',
            '<datasource name="%s" type="CLIENT"><record name="r4" />'
            '</datasource>'
        ]

        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc

        dsname = [dname] * 4
        while dsname[0] in dsavc:
            dsname[0] = dsname[0] + '_1'
        dsname[1] = dsname[0] + '_2'
        dsname[2] = dsname[0] + '_3'
        dsname[3] = dsname[0] + '_4'
        while dsname[1] in dsavc:
            dsname[1] = dsname[1] + '_2'
        while dsname[2] in dsavc:
            dsname[2] = dsname[2] + '_2'
        while dsname[3] in dsavc:
            dsname[3] = dsname[3] + '_3'
        dss = {
            name: [dsname[0]],
            name2: [dsname[1]],
            name3: [dsname[2], dsname[3]],
        }

        self.setXML(el, xml % dss[name])
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2 % dss[name2])
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        self.setXML(el, xml3 % tuple(dss[name3]))
        self.assertEqual(el.storeComponent(name3), None)
        self.__cmps.append(name3)

        dsnp = len(xds)
        for i in range(dsnp):
            self.setXML(el, xds[i] % dsname[i])
            self.assertEqual(el.storeDataSource(dsname[i]), None)
            self.__ds.append(dsname[i])

        commands = [
            'nxsconfig sources %s -s %s',
            'nxsconfig sources %s --server %s',
            'nxsconfig sources %s --no-newlines -s %s',
            'nxsconfig sources %s -n --server %s',
            'nxsconfig sources %s -n -s %s',
            'nxsconfig sources %s --no-newlines --server %s',
        ]
        for scmd in commands:
            for nm in dss.keys():
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                if "-n" in cmd or "--no-newlines" in cmd:
                    avc3 = [ec.strip() for ec in vl.split(' ')
                            if ec.strip()]
                else:
                    avc3 = [ec for ec in vl.split('\n') if ec]
                self.assertEqual(sorted(avc3), sorted(dss[nm]))
                self.assertEqual(er, "")

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop(-1)
        self.assertEqual(el.deleteComponent(name3), None)
        self.__cmps.pop()

        el.close()

    def test_sources_nods(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()
        dsavc = el.availableDatasources()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        dname = "mcs_test_datasources"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
            "<definition><field name='data0'>" \
            "$datasources.%s" \
            "</field>" \
            "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
            "<definition><field name='data'>" \
            "$datasources.%s" \
            "</field>" \
            "</definition>"
        xml3 = "<?xml version='1.0' encoding='utf-8'?>" \
            "<definition>" \
            "<field name='data'>" \
            "$datasources.%s" \
            "</field>" \
            "<field name='data2'>" \
            "$datasources.%s" \
            "</field>" \
            "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc

        dsname = [dname] * 4
        while dsname[0] in dsavc:
            dsname[0] = dsname[0] + '_1'
        dsname[1] = dsname[0] + '_2'
        dsname[2] = dsname[0] + '_3'
        dsname[3] = dsname[0] + '_4'
        while dsname[1] in dsavc:
            dsname[1] = dsname[1] + '_2'
        while dsname[2] in dsavc:
            dsname[2] = dsname[2] + '_2'
        while dsname[3] in dsavc:
            dsname[3] = dsname[3] + '_3'
        dss = {
            name: [dsname[0]],
            name2: [dsname[1]],
            name3: [dsname[2], dsname[3]],
        }

        self.setXML(el, xml % dss[name])
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2 % dss[name2])
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        self.setXML(el, xml3 % tuple(dss[name3]))
        self.assertEqual(el.storeComponent(name3), None)
        self.__cmps.append(name3)

        commands = [
            'nxsconfig sources %s -s %s',
            'nxsconfig sources %s --server %s',
            'nxsconfig sources %s --no-newlines -s %s',
            'nxsconfig sources %s -n --server %s',
            'nxsconfig sources %s -n -s %s',
            'nxsconfig sources %s --no-newlines --server %s',
        ]
        for scmd in commands:
            for nm in dss.keys():
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                vl, er, et = self.runtestexcept(cmd, SystemExit)
                vl = vl.strip()

                self.assertTrue(er.startswith("Error: Datasource "))
                self.assertEqual(vl, "")

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop(-1)
        self.assertEqual(el.deleteComponent(name3), None)
        self.__cmps.pop()

        el.close()

    def test_sources_mand(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
            "<definition><field name='data'>" \
            "<datasource name='sl1right' type='client'>" \
            "</datasource>" \
            "</field>" \
            "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>\n" \
            "<definition><group type='NXentry'/>" \
            "\n</definition>"
        xml3 = "<?xml version='1.0' encoding='utf-8'?>" \
            "<definition>" \
            "<field name='data2'>" \
            "<datasource name='sl2bottom' type='client'>" \
            "</datasource>" \
            "</field>" \
            "<field name='data2'>" \
            "<datasource name='sl2top' type='tango'>" \
            "</datasource>" \
            "</field>" \
            "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
        dss = {
            name2: ["sl1right"],
            name3: ["sl2top", "sl2bottom", "sl1right"],
        }

        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        self.setXML(el, xml3)
        self.assertEqual(el.storeComponent(name3), None)
        self.__cmps.append(name3)
        self.assertEqual(el.setMandatoryComponents([name]), None)
        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<definition><group type='NXentry'/>" \
              "\n</definition>"

        commands = [
            'nxsconfig sources %s -m -s %s',
            'nxsconfig sources %s -m --server %s',
            'nxsconfig sources %s -m --no-newlines -s %s',
            'nxsconfig sources %s -m -n --server %s',
            'nxsconfig sources %s -m -n -s %s',
            'nxsconfig sources %s -m --no-newlines --server %s',
            'nxsconfig sources %s --mandatory -s %s',
            'nxsconfig sources %s --mandatory --server %s',
            'nxsconfig sources %s --mandatory --no-newlines -s %s',
            'nxsconfig sources %s --mandatory -n --server %s',
            'nxsconfig sources %s --mandatory -n -s %s',
            'nxsconfig sources %s --mandatory --no-newlines --server %s',
        ]
        for scmd in commands:
            for nm in dss.keys():
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                if "-n" in cmd or "--no-newlines" in cmd:
                    avc3 = [ec.strip() for ec in vl.split(' ')
                            if ec.strip()]
                else:
                    avc3 = [ec for ec in vl.split('\n') if ec]
                self.assertEqual(sorted(avc3), sorted(dss[nm]))
                self.assertEqual(er, "")

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop(-1)
        self.assertEqual(el.deleteComponent(name3), None)
        self.__cmps.pop()

        el.close()

    def test_upload_comp_av(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<definition><group type='NXentry'/>" \
              "\n</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field type='NXentry2'/>" \
               "$datasources.sl1right</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
#        print avc
        cmps = {name: xml, name2: xml2}

        with open("%s.xml" % (name), "w") as fl:
            fl.write(xml)
        with open("%s.xml" % (name2), "w") as fl:
            fl.write(xml2)
        with open("%s.xml" % (name3), "w") as fl:
            fl.write(xml)

        self.__cmps.append(name)
        self.__cmps.append(name2)

        commands = [
            'nxsconfig upload %s -s %s',
            'nxsconfig upload %s  --server %s',
            'nxsconfig upload %s  -s %s',
            'nxsconfig upload %s  --server %s',
        ]
        for scmd in commands:
            for nm, fvl in cmps.items():
                cmd = (scmd % (
                    nm,
                    self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                self.assertEqual(vl.strip(), "")
                self.assertEqual(er, "")

                avc2 = el.availableComponents()
                self.assertTrue(isinstance(avc2, list))
                for cp in avc:
                    self.assertTrue(cp in avc2)

                self.assertTrue(nm in avc2)
                cpx = el.components([nm])
                self.assertEqual(cpx[0], fvl)

                self.assertEqual(el.deleteComponent(nm), None)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2),
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()

            self.assertEqual(vl, "")
            self.assertEqual(er, "")

            avc2 = el.availableComponents()
            self.assertTrue(isinstance(avc2, list))
            for cp in avc:
                self.assertTrue(cp in avc2)

            self.assertTrue(name in avc2)
            self.assertTrue(name2 in avc2)
            self.assertTrue(name3 not in avc2)
            cpx = el.components([name])
            self.assertEqual(cpx[0], xml)
            cpx = el.components([name2])
            self.assertEqual(cpx[0], xml2)

            self.assertEqual(el.deleteComponent(name), None)
            self.assertEqual(el.deleteComponent(name2), None)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()

        os.remove("%s.xml" % name)
        os.remove("%s.xml" % name2)
        os.remove("%s.xml" % name3)
        el.close()

    def test_upload_comp_av_directory(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        dirname = "test_comp_dir"
        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<definition><group type='NXentry'/>" \
              "\n</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field type='NXentry2'/>" \
               "$datasources.sl1right</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
#        print avc
        cmps = {name: xml, name2: xml2}

        while os.path.exists(dirname):
            dirname = dirname + '_1'
        os.mkdir(dirname)
        with open("%s/%s.xml" % (dirname, name), "w") as fl:
            fl.write(xml)
        with open("%s/%s.xml" % (dirname, name2), "w") as fl:
            fl.write(xml2)
        with open("%s/%s.xml" % (dirname, name3), "w") as fl:
            fl.write(xml)

        self.__cmps.append(name)
        self.__cmps.append(name2)

        commands = [
            'nxsconfig upload %s -i %s -s %s',
            'nxsconfig upload %s -i %s  --server %s',
            'nxsconfig upload %s -i %s  -s %s',
            'nxsconfig upload %s -i %s  --server %s',
            'nxsconfig upload %s --directory %s -s %s',
            'nxsconfig upload %s --directory %s  --server %s',
            'nxsconfig upload %s --directory %s  -s %s',
            'nxsconfig upload %s --directory %s  --server %s',
        ]
        for scmd in commands:
            for nm, fvl in cmps.items():
                cmd = (scmd % (
                    nm, dirname,
                    self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                self.assertEqual(vl.strip(), "")
                self.assertEqual(er, "")

                avc2 = el.availableComponents()
                self.assertTrue(isinstance(avc2, list))
                for cp in avc:
                    self.assertTrue(cp in avc2)

                self.assertTrue(nm in avc2)
                cpx = el.components([nm])
                self.assertEqual(cpx[0], fvl)

                self.assertEqual(el.deleteComponent(nm), None)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2), dirname,
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()

            self.assertEqual(vl, "")
            self.assertEqual(er, "")

            avc2 = el.availableComponents()
            self.assertTrue(isinstance(avc2, list))
            for cp in avc:
                self.assertTrue(cp in avc2)

            self.assertTrue(name in avc2)
            self.assertTrue(name2 in avc2)
            self.assertTrue(name3 not in avc2)
            cpx = el.components([name])
            self.assertEqual(cpx[0], xml)
            cpx = el.components([name2])
            self.assertEqual(cpx[0], xml2)

            self.assertEqual(el.deleteComponent(name), None)
            self.assertEqual(el.deleteComponent(name2), None)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()

        shutil.rmtree(dirname)
        el.close()

    def test_upload_ds_av(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableDataSources()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_datasource"
        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<definition><group type='NXentry'/>" \
              "\n</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field type='NXentry2'/>" \
               "$datasources.sl1right</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
#        print avc
        cmps = {name: xml, name2: xml2}

        with open("%s.ds.xml" % (name), "w") as fl:
            fl.write(xml)
        with open("%s.ds.xml" % (name2), "w") as fl:
            fl.write(xml2)
        with open("%s.ds.xml" % (name3), "w") as fl:
            fl.write(xml)

        self.__ds.append(name)
        self.__ds.append(name2)

        commands = [
            'nxsconfig upload %s -d -s %s',
            'nxsconfig upload %s -d  --server %s',
            'nxsconfig upload %s -d  -s %s',
            'nxsconfig upload %s -d  --server %s',
            'nxsconfig upload %s --datasources -s %s',
            'nxsconfig upload %s --datasources  --server %s',
            'nxsconfig upload %s --datasources  -s %s',
            'nxsconfig upload %s --datasources  --server %s',
        ]
        for scmd in commands:
            for nm, fvl in cmps.items():
                cmd = (scmd % (
                    nm,
                    self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                self.assertEqual(vl.strip(), "")
                self.assertEqual(er, "")

                avc2 = el.availableDataSources()
                self.assertTrue(isinstance(avc2, list))
                for cp in avc:
                    self.assertTrue(cp in avc2)

                self.assertTrue(nm in avc2)
                cpx = el.datasources([nm])
                self.assertEqual(cpx[0], fvl)

                self.assertEqual(el.deleteDataSource(nm), None)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2),
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()

            self.assertEqual(vl, "")
            self.assertEqual(er, "")

            avc2 = el.availableDataSources()
            self.assertTrue(isinstance(avc2, list))
            for cp in avc:
                self.assertTrue(cp in avc2)

            self.assertTrue(name in avc2)
            self.assertTrue(name2 in avc2)
            self.assertTrue(name3 not in avc2)
            cpx = el.datasources([name])
            self.assertEqual(cpx[0], xml)
            cpx = el.datasources([name2])
            self.assertEqual(cpx[0], xml2)

            self.assertEqual(el.deleteDataSource(name), None)
            self.assertEqual(el.deleteDataSource(name2), None)

        self.assertEqual(el.deleteDataSource(name), None)
        self.__ds.pop(-2)
        self.assertEqual(el.deleteDataSource(name2), None)
        self.__ds.pop()

        os.remove("%s.ds.xml" % name)
        os.remove("%s.ds.xml" % name2)
        os.remove("%s.ds.xml" % name3)
        el.close()

    def test_upload_ds_av_directory(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableDataSources()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_datasource"
        dirname = "test_comp_dir"
        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<definition><group type='NXentry'/>" \
              "\n</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field type='NXentry2'/>" \
               "$datasources.sl1right</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
#        print avc
        cmps = {name: xml, name2: xml2}

        while os.path.exists(dirname):
            dirname = dirname + '_1'
        os.mkdir(dirname)
        with open("%s/%s.ds.xml" % (dirname, name), "w") as fl:
            fl.write(xml)
        with open("%s/%s.ds.xml" % (dirname, name2), "w") as fl:
            fl.write(xml2)
        with open("%s/%s.ds.xml" % (dirname, name3), "w") as fl:
            fl.write(xml)

        self.__ds.append(name)
        self.__ds.append(name2)

        commands = [
            'nxsconfig upload %s --datasources -i %s -s %s',
            'nxsconfig upload %s --datasources -i %s  --server %s',
            'nxsconfig upload %s --datasources -i %s  -s %s',
            'nxsconfig upload %s --datasources -i %s  --server %s',
            'nxsconfig upload %s --datasources --directory %s -s %s',
            'nxsconfig upload %s --datasources --directory %s  --server %s',
            'nxsconfig upload %s --datasources --directory %s  -s %s',
            'nxsconfig upload %s --datasources --directory %s  --server %s',
            'nxsconfig upload %s -d -i %s -s %s',
            'nxsconfig upload %s -d -i %s  --server %s',
            'nxsconfig upload %s -d -i %s  -s %s',
            'nxsconfig upload %s -d -i %s  --server %s',
            'nxsconfig upload %s -d --directory %s -s %s',
            'nxsconfig upload %s -d --directory %s  --server %s',
            'nxsconfig upload %s -d --directory %s  -s %s',
            'nxsconfig upload %s -d --directory %s  --server %s',
        ]
        for scmd in commands:
            for nm, fvl in cmps.items():
                cmd = (scmd % (
                    nm, dirname,
                    self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                self.assertEqual(vl.strip(), "")
                self.assertEqual(er, "")

                avc2 = el.availableDataSources()
                self.assertTrue(isinstance(avc2, list))
                for cp in avc:
                    self.assertTrue(cp in avc2)

                self.assertTrue(nm in avc2)
                cpx = el.datasources([nm])
                self.assertEqual(cpx[0], fvl)

                self.assertEqual(el.deleteDataSource(nm), None)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2), dirname,
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()

            self.assertEqual(vl, "")
            self.assertEqual(er, "")

            avc2 = el.availableDataSources()
            self.assertTrue(isinstance(avc2, list))
            for cp in avc:
                self.assertTrue(cp in avc2)

            self.assertTrue(name in avc2)
            self.assertTrue(name2 in avc2)
            self.assertTrue(name3 not in avc2)
            cpx = el.datasources([name])
            self.assertEqual(cpx[0], xml)
            cpx = el.datasources([name2])
            self.assertEqual(cpx[0], xml2)

            self.assertEqual(el.deleteDataSource(name), None)
            self.assertEqual(el.deleteDataSource(name2), None)

        self.assertEqual(el.deleteDataSource(name), None)
        self.__ds.pop(-2)
        self.assertEqual(el.deleteDataSource(name2), None)
        self.__ds.pop()

        shutil.rmtree(dirname)
        el.close()

    def test_upload_profile_av(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableSelections()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_profile"
        jsn = '{"DataSourceSelection": ' \
              '"{\\"lmbd01\\": false, \\"exp_mca01\\": true}"}'
        jsn2 = '{"ComponentSelection": "{\\"pilatus\\": true}"}'
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
#        print avc
        cmps = {name: jsn, name2: jsn2}

        with open("%s.json" % (name), "w") as fl:
            fl.write(jsn)
        with open("%s.json" % (name2), "w") as fl:
            fl.write(jsn2)
        with open("%s.json" % (name3), "w") as fl:
            fl.write(jsn)

        self.__profs.append(name)
        self.__profs.append(name2)

        commands = [
            'nxsconfig upload %s -r -s %s',
            'nxsconfig upload %s -r  --server %s',
            'nxsconfig upload %s -r -s %s',
            'nxsconfig upload %s -r  --server %s',
            'nxsconfig upload %s --profiles -s %s',
            'nxsconfig upload %s --profiles  --server %s',
            'nxsconfig upload %s --profiles  -s %s',
            'nxsconfig upload %s --profiles  --server %s',
        ]
        for scmd in commands:
            for nm, fvl in cmps.items():
                cmd = (scmd % (
                    nm,
                    self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                self.assertEqual(vl.strip(), "")
                self.assertEqual(er, "")

                avc2 = el.availableSelections()
                self.assertTrue(isinstance(avc2, list))
                for cp in avc:
                    self.assertTrue(cp in avc2)

                self.assertTrue(nm in avc2)
                cpx = el.selections([nm])
                self.assertEqual(cpx[0], fvl)

                self.assertEqual(el.deleteSelection(nm), None)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2),
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()

            self.assertEqual(vl, "")
            self.assertEqual(er, "")

            avc2 = el.availableSelections()
            self.assertTrue(isinstance(avc2, list))
            for cp in avc:
                self.assertTrue(cp in avc2)

            self.assertTrue(name in avc2)
            self.assertTrue(name2 in avc2)
            self.assertTrue(name3 not in avc2)
            cpx = el.selections([name])
            self.assertEqual(cpx[0], jsn)
            cpx = el.selections([name2])
            self.assertEqual(cpx[0], jsn2)

            self.assertEqual(el.deleteSelection(name), None)
            self.assertEqual(el.deleteSelection(name2), None)

        self.assertEqual(el.deleteSelection(name), None)
        self.__profs.pop(-2)
        self.assertEqual(el.deleteSelection(name2), None)
        self.__profs.pop()

        os.remove("%s.json" % name)
        os.remove("%s.json" % name2)
        os.remove("%s.json" % name3)
        el.close()

    def test_upload_profile_av_directory(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableSelections()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_profile"
        dirname = "test_profile_dir"
        jsn = '{"DataSourceSelection": ' \
              '"{\\"lmbd01\\": false, \\"exp_mca01\\": true}"}'
        jsn2 = '{"ComponentSelection": "{\\"pilatus\\": true}"}'
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
#        print avc
        cmps = {name: jsn, name2: jsn2}

        while os.path.exists(dirname):
            dirname = dirname + '_1'
        os.mkdir(dirname)
        with open("%s/%s.json" % (dirname, name), "w") as fl:
            fl.write(jsn)
        with open("%s/%s.json" % (dirname, name2), "w") as fl:
            fl.write(jsn2)
        with open("%s/%s.json" % (dirname, name3), "w") as fl:
            fl.write(jsn)

        self.__profs.append(name)
        self.__profs.append(name2)

        commands = [
            'nxsconfig upload %s --profiles -i %s -s %s',
            'nxsconfig upload %s --profiles -i %s  --server %s',
            'nxsconfig upload %s --profiles -i %s  -s %s',
            'nxsconfig upload %s --profiles -i %s  --server %s',
            'nxsconfig upload %s --profiles --directory %s -s %s',
            'nxsconfig upload %s --profiles --directory %s  --server %s',
            'nxsconfig upload %s --profiles --directory %s  -s %s',
            'nxsconfig upload %s --profiles --directory %s  --server %s',
            'nxsconfig upload %s -r -i %s -s %s',
            'nxsconfig upload %s -r -i %s  --server %s',
            'nxsconfig upload %s -r -i %s  -s %s',
            'nxsconfig upload %s -r -i %s  --server %s',
            'nxsconfig upload %s -r --directory %s -s %s',
            'nxsconfig upload %s -r --directory %s  --server %s',
            'nxsconfig upload %s -r --directory %s  -s %s',
            'nxsconfig upload %s -r --directory %s  --server %s',
        ]
        for scmd in commands:
            for nm, fvl in cmps.items():
                cmd = (scmd % (
                    nm, dirname,
                    self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                self.assertEqual(vl.strip(), "")
                self.assertEqual(er, "")

                avc2 = el.availableSelections()
                self.assertTrue(isinstance(avc2, list))
                for cp in avc:
                    self.assertTrue(cp in avc2)

                self.assertTrue(nm in avc2)
                cpx = el.selections([nm])
                self.assertEqual(cpx[0], fvl)

                self.assertEqual(el.deleteSelection(nm), None)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2), dirname,
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()

            self.assertEqual(vl, "")
            self.assertEqual(er, "")

            avc2 = el.availableSelections()
            self.assertTrue(isinstance(avc2, list))
            for cp in avc:
                self.assertTrue(cp in avc2)

            self.assertTrue(name in avc2)
            self.assertTrue(name2 in avc2)
            self.assertTrue(name3 not in avc2)
            cpx = el.selections([name])
            self.assertEqual(cpx[0], jsn)
            cpx = el.selections([name2])
            self.assertEqual(cpx[0], jsn2)

            self.assertEqual(el.deleteSelection(name), None)
            self.assertEqual(el.deleteSelection(name2), None)

        self.assertEqual(el.deleteSelection(name), None)
        self.__profs.pop(-2)
        self.assertEqual(el.deleteSelection(name2), None)
        self.__profs.pop()

        shutil.rmtree(dirname)
        el.close()

    def test_upload_ds_av_noexist(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableDataSources()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_ds"
        dirname = "test_ds_dir"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
#        print avc
        cmps = [name, name2]

        while os.path.exists(dirname):
            dirname = dirname + '_1'
        os.mkdir(dirname)

        commands = [
            'nxsconfig upload %s --datasources -i %s -s %s',
            'nxsconfig upload %s --datasources -i %s  --server %s',
            'nxsconfig upload %s --datasources -i %s  -s %s',
            'nxsconfig upload %s --datasources -i %s  --server %s',
            'nxsconfig upload %s --datasources --directory %s -s %s',
            'nxsconfig upload %s --datasources --directory %s  --server %s',
            'nxsconfig upload %s --datasources --directory %s  -s %s',
            'nxsconfig upload %s --datasources --directory %s  --server %s',
            'nxsconfig upload %s -d -i %s -s %s',
            'nxsconfig upload %s -d -i %s  --server %s',
            'nxsconfig upload %s -d -i %s  -s %s',
            'nxsconfig upload %s -d -i %s  --server %s',
            'nxsconfig upload %s -d --directory %s -s %s',
            'nxsconfig upload %s -d --directory %s  --server %s',
            'nxsconfig upload %s -d --directory %s  -s %s',
            'nxsconfig upload %s -d --directory %s  --server %s',
        ]
        for scmd in commands:
            for nm in cmps:
                cmd = (scmd % (
                    nm, dirname,
                    self._sv.new_device_info_writer.name)).split()
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                old_stdin = sys.stdin
                sys.stdin = StringIO()
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                with self.assertRaises(SystemExit):
                    nxsconfig.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stdin = old_stdin
                sys.stderr = old_stderr
                vl = mystdout.getvalue().strip()
                er = mystderr.getvalue()
                self.assertTrue(er)
                self.assertEqual('', vl)

        shutil.rmtree(dirname)
        el.close()

    def test_upload_comp_av_noexist(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableDataSources()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        dirname = "test_comp_dir"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
#        print avc
        cmps = [name, name2]

        while os.path.exists(dirname):
            dirname = dirname + '_1'
        os.mkdir(dirname)

        commands = [
            'nxsconfig upload %s -i %s -s %s',
            'nxsconfig upload %s -i %s  --server %s',
            'nxsconfig upload %s -i %s  -s %s',
            'nxsconfig upload %s -i %s  --server %s',
            'nxsconfig upload %s --directory %s -s %s',
            'nxsconfig upload %s --directory %s  --server %s',
            'nxsconfig upload %s --directory %s  -s %s',
            'nxsconfig upload %s --directory %s  --server %s',
        ]
        for scmd in commands:
            for nm in cmps:
                cmd = (scmd % (
                    nm, dirname,
                    self._sv.new_device_info_writer.name)).split()
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                old_stdin = sys.stdin
                sys.stdin = StringIO()
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                with self.assertRaises(SystemExit):
                    nxsconfig.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                sys.stdin = old_stdin
                vl = mystdout.getvalue().strip()
                er = mystderr.getvalue()
                self.assertTrue(er)
                self.assertEqual('', vl)

        shutil.rmtree(dirname)
        el.close()

    def test_upload_profile_av_noexist(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableSelections()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_profile"
        dirname = "test_profile_dir"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
#        print avc
        cmps = [name, name2]

        while os.path.exists(dirname):
            dirname = dirname + '_1'
        os.mkdir(dirname)

        commands = [
            'nxsconfig upload %s --profiles -i %s -s %s',
            'nxsconfig upload %s --profiles -i %s  --server %s',
            'nxsconfig upload %s --profiles -i %s  -s %s',
            'nxsconfig upload %s --profiles -i %s  --server %s',
            'nxsconfig upload %s --profiles --directory %s -s %s',
            'nxsconfig upload %s --profiles --directory %s  --server %s',
            'nxsconfig upload %s --profiles --directory %s  -s %s',
            'nxsconfig upload %s --profiles --directory %s  --server %s',
            'nxsconfig upload %s -r -i %s -s %s',
            'nxsconfig upload %s -r -i %s  --server %s',
            'nxsconfig upload %s -r -i %s  -s %s',
            'nxsconfig upload %s -r -i %s  --server %s',
            'nxsconfig upload %s -r --directory %s -s %s',
            'nxsconfig upload %s -r --directory %s  --server %s',
            'nxsconfig upload %s -r --directory %s  -s %s',
            'nxsconfig upload %s -r --directory %s  --server %s',
        ]
        for scmd in commands:
            for nm in cmps:
                cmd = (scmd % (
                    nm, dirname,
                    self._sv.new_device_info_writer.name)).split()
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                old_stdin = sys.stdin
                sys.stdin = StringIO()
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                with self.assertRaises(SystemExit):
                    nxsconfig.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stdin = old_stdin
                sys.stderr = old_stderr
                vl = mystdout.getvalue().strip()
                er = mystderr.getvalue()
                self.assertTrue(er)
                self.assertEqual('', vl)

        shutil.rmtree(dirname)
        el.close()

    def test_show_comp_av_directory(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        dirname = "test_comp_dir"
        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<definition><group type='NXentry'/>" \
              "\n</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field type='NXentry2'/>" \
               "$datasources.sl1right</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
#        print avc
        cmps = {name: xml, name2: xml2}
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)
        while os.path.exists(dirname):
            dirname = dirname + '_1'
        os.mkdir(dirname)

        commands = [
            'nxsconfig show %s -o %s -s %s',
            'nxsconfig show %s -o %s --server %s',
            'nxsconfig show %s -o %s -s %s',
            'nxsconfig show %s -o %s --server %s',
            'nxsconfig show %s --directory %s -s %s',
            'nxsconfig show %s --directory %s --server %s',
            'nxsconfig show %s --directory %s -s %s',
            'nxsconfig show %s --directory %s --server %s',
        ]
        for scmd in commands:
            for nm in cmps.keys():
                cmd = (scmd % (
                    nm, dirname,
                    self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                with open("%s/%s.xml" % (dirname, nm), "r") as fl:
                    fvl = fl.read()
                self.assertEqual(fvl.strip(), cmps[nm])
                self.assertEqual(vl.strip(), "")
                self.assertEqual(er, "")

        shutil.rmtree(dirname)
        os.mkdir(dirname)
        for scmd in commands:
            nm = name3
            cmd = (scmd % (nm, dirname,
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            er = er.strip()

            self.assertEqual(vl, "")
            self.assertTrue(not os.path.exists("%s/%s.xml" % (nm, dirname)))
            self.assertEqual(
                er,
                "Error: Component '%s' not stored in the configuration server"
                % name3)

        shutil.rmtree(dirname)
        os.mkdir(dirname)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2), dirname,
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()

            with open("%s/%s.xml" % (dirname, name), "r") as fl:
                fvl = fl.read()
            self.assertEqual(fvl.replace(">\n<", "><").replace("> <", "><"),
                             cmps[name].replace(
                                 ">\n<", "><").replace("> <", "><"))
            with open("%s/%s.xml" % (dirname, name2), "r") as fl:
                fvl = fl.read()
            self.assertEqual(fvl.replace(">\n<", "><").replace("> <", "><"),
                             cmps[name2].replace(
                                 ">\n<", "><").replace("> <", "><"))
            self.assertEqual(vl.strip(), "")
            self.assertEqual(er, "")

        shutil.rmtree(dirname)
        os.mkdir(dirname)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name3), dirname,
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            er = er.strip()

            self.assertTrue(not os.path.exists("%s/%s.xml" % (nm, dirname)))
            self.assertEqual(vl, "")
            self.assertEqual(
                er,
                "Error: Component '%s' not stored in the configuration server"
                % name3)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()

        shutil.rmtree(dirname)
        el.close()

    def test_show_ds_av_directory(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableDataSources()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_datasource"
        dirname = "test_ds_dir"
        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<definition><group type='NXentry'/>" \
              "\n</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field type='NXentry2'/>" \
               "$datasources.sl1right</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
#        print avc
        cmps = {name: xml, name2: xml2}
        self.setXML(el, xml)
        self.assertEqual(el.storeDataSource(name), None)
        self.__ds.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeDataSource(name2), None)
        self.__ds.append(name2)
        avc2 = el.availableDataSources()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.datasources([name])
        self.assertEqual(cpx[0], xml)
        while os.path.exists(dirname):
            dirname = dirname + '_1'
        os.mkdir(dirname)

        commands = [
            'nxsconfig show %s -d -o %s -s %s',
            'nxsconfig show %s -d -o %s --server %s',
            'nxsconfig show %s -d -o %s -s %s',
            'nxsconfig show %s -d -o %s --server %s',
            'nxsconfig show %s -d --directory %s -s %s',
            'nxsconfig show %s -d --directory %s --server %s',
            'nxsconfig show %s -d --directory %s -s %s',
            'nxsconfig show %s -d --directory %s --server %s',
            'nxsconfig show %s --datasources -o %s -s %s',
            'nxsconfig show %s --datasources -o %s --server %s',
            'nxsconfig show %s --datasources -o %s -s %s',
            'nxsconfig show %s --datasources -o %s --server %s',
            'nxsconfig show %s --datasources --directory %s -s %s',
            'nxsconfig show %s --datasources --directory %s --server %s',
            'nxsconfig show %s --datasources --directory %s -s %s',
            'nxsconfig show %s --datasources --directory %s --server %s',
        ]
        for scmd in commands:
            for nm in cmps.keys():
                cmd = (scmd % (
                    nm, dirname,
                    self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                with open("%s/%s.ds.xml" % (dirname, nm), "r") as fl:
                    fvl = fl.read()
                self.assertEqual(fvl.strip(), cmps[nm])
                self.assertEqual(vl.strip(), "")
                self.assertEqual(er, "")

        shutil.rmtree(dirname)
        os.mkdir(dirname)
        for scmd in commands:
            nm = name3
            cmd = (scmd % (nm, dirname,
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            er = er.strip()

            self.assertEqual(vl, "")
            self.assertTrue(not os.path.exists("%s/%s.ds.xml" % (nm, dirname)))
            self.assertEqual(
                er,
                "Error: DataSource '%s' not stored in the configuration server"
                % name3)

        shutil.rmtree(dirname)
        os.mkdir(dirname)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2), dirname,
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()

            with open("%s/%s.ds.xml" % (dirname, name), "r") as fl:
                fvl = fl.read()
            self.assertEqual(fvl.replace(">\n<", "><").replace("> <", "><"),
                             cmps[name].replace(
                                 ">\n<", "><").replace("> <", "><"))
            with open("%s/%s.ds.xml" % (dirname, name2), "r") as fl:
                fvl = fl.read()
            self.assertEqual(fvl.replace(">\n<", "><").replace("> <", "><"),
                             cmps[name2].replace(
                                 ">\n<", "><").replace("> <", "><"))
            self.assertEqual(vl.strip(), "")
            self.assertEqual(er, "")

        shutil.rmtree(dirname)
        os.mkdir(dirname)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name3), dirname,
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            er = er.strip()

            self.assertTrue(not os.path.exists("%s/%s.ds.xml" % (nm, dirname)))
            self.assertEqual(vl, "")
            self.assertEqual(
                er,
                "Error: DataSource '%s' not stored in the configuration server"
                % name3)

        self.assertEqual(el.deleteDataSource(name), None)
        self.__ds.pop(-2)
        self.assertEqual(el.deleteDataSource(name2), None)
        self.__ds.pop()

        shutil.rmtree(dirname)
        el.close()

    def test_show_profile_av_directory(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableSelections()

        self.assertTrue(isinstance(avc, list))
        dirname = "test_profile_dir"
        name = "mcs_test_profile"
        jsn = '{"DataSourceSelection": ' \
              '"{\\"lmbd01\\": false, \\"exp_mca01\\": true}"}'
        jsn2 = '{"ComponentSelection": "{\\"pilatus\\": true}"}'
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
#        print avc
        profs = {name: jsn, name2: jsn2}
        self.setSelection(el, jsn)
        self.assertEqual(el.storeSelection(name), None)
        self.__profs.append(name)
        self.setSelection(el, jsn2)
        self.assertEqual(el.storeSelection(name2), None)
        self.__profs.append(name2)
        avc2 = el.availableSelections()
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.selections([name])
        self.assertEqual(cpx[0], jsn)
        while os.path.exists(dirname):
            dirname = dirname + '_1'
        os.mkdir(dirname)

        commands = [
            'nxsconfig show %s -r -o %s -s %s',
            'nxsconfig show %s -r -o %s --server %s',
            'nxsconfig show %s -r -o %s -s %s',
            'nxsconfig show %s -r -o %s --server %s',
            'nxsconfig show %s -r --directory %s -s %s',
            'nxsconfig show %s -r --directory %s --server %s',
            'nxsconfig show %s -r --directory %s -s %s',
            'nxsconfig show %s -r --directory %s --server %s',
            'nxsconfig show %s --profiles -o %s -s %s',
            'nxsconfig show %s --profiles -o %s --server %s',
            'nxsconfig show %s --profiles -o %s -s %s',
            'nxsconfig show %s --profiles -o %s --server %s',
            'nxsconfig show %s --profiles --directory %s -s %s',
            'nxsconfig show %s --profiles --directory %s --server %s',
            'nxsconfig show %s --profiles --directory %s -s %s',
            'nxsconfig show %s --profiles --directory %s --server %s',
        ]
        for scmd in commands:
            for nm in profs.keys():
                cmd = (scmd % (
                    nm, dirname,
                    self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                with open("%s/%s.json" % (dirname, nm), "r") as fl:
                    fvl = fl.read()
                self.assertEqual(fvl.strip(), profs[nm])
                self.assertEqual(vl.strip(), "")
                self.assertEqual(er, "")

        shutil.rmtree(dirname)
        os.mkdir(dirname)
        for scmd in commands:
            nm = name3
            cmd = (scmd % (nm, dirname,
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            er = er.strip()

            self.assertEqual(vl, "")
            self.assertTrue(not os.path.exists("%s/%s.json" % (nm, dirname)))
            self.assertEqual(
                er,
                "Error: Profile '%s' not stored in the configuration server"
                % name3)

        shutil.rmtree(dirname)
        os.mkdir(dirname)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2), dirname,
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()

            with open("%s/%s.json" % (dirname, name), "r") as fl:
                fvl = fl.read()
            self.assertEqual(fvl.replace(">\n<", "><").replace("> <", "><"),
                             profs[name].replace(
                                 ">\n<", "><").replace("> <", "><"))
            with open("%s/%s.json" % (dirname, name2), "r") as fl:
                fvl = fl.read()
            self.assertEqual(fvl.replace(">\n<", "><").replace("> <", "><"),
                             profs[name2].replace(
                                 ">\n<", "><").replace("> <", "><"))
            self.assertEqual(vl.strip(), "")
            self.assertEqual(er, "")

        shutil.rmtree(dirname)
        os.mkdir(dirname)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name3), dirname,
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            er = er.strip()

            self.assertTrue(not os.path.exists("%s/%s.json" % (nm, dirname)))
            self.assertEqual(vl, "")
            self.assertEqual(
                er,
                "Error: Profile '%s' not stored in the configuration server"
                % name3)

        self.assertEqual(el.deleteSelection(name), None)
        self.__profs.pop(-2)
        self.assertEqual(el.deleteSelection(name2), None)
        self.__profs.pop()

        shutil.rmtree(dirname)
        el.close()

    def test_show_profile_av(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableSelections()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_profile"
        jsn = '{"DataSourceSelection": ' \
              '"{\\"lmbd01\\": false, \\"exp_mca01\\": true}"}'
        jsn2 = '{"ComponentSelection": "{\\"pilatus\\": true}"}'
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
        profs = {name: jsn, name2: jsn2}

        self.setSelection(el, jsn)
        self.assertEqual(el.storeSelection(name), None)
        self.__profs.append(name)
        self.setSelection(el, jsn2)
        self.assertEqual(el.storeSelection(name2), None)
        self.__profs.append(name2)
        avc2 = el.availableSelections()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.selections([name])
        self.assertEqual(cpx[0], jsn)

        commands = [
            'nxsconfig show %s -r -s %s',
            'nxsconfig show %s -r --server %s',
            'nxsconfig show %s -r -s %s',
            'nxsconfig show %s -r --server %s',
            'nxsconfig show %s --profiles -s %s',
            'nxsconfig show %s --profiles --server %s',
            'nxsconfig show %s --profiles -s %s',
            'nxsconfig show %s --profiles --server %s',
        ]
        for scmd in commands:
            for nm in profs.keys():
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                self.assertEqual(vl.strip(), profs[nm])
                self.assertEqual(er, "")

        for scmd in commands:
            nm = name3
            cmd = (scmd % (nm, self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            er = er.strip()

            self.assertEqual(vl, "")
            self.assertEqual(
                er,
                "Error: Profile '%s' not stored in the configuration server"
                % name3)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2),
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()

            self.assertEqual(vl,
                             ("%s\n%s" % (profs[name], profs[name2])))
            self.assertEqual(er, "")

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name3),
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            er = er.strip()

            self.assertEqual(vl, "")
            self.assertEqual(
                er,
                "Error: Profile '%s' not stored in the configuration server"
                % name3)

        self.assertEqual(el.deleteSelection(name), None)
        self.__profs.pop(-2)
        self.assertEqual(el.deleteSelection(name2), None)
        self.__profs.pop()

        el.close()

    def test_show_datasources_av(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableDataSources()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?><definition>" \
              "<datasource type='TANGO' name='testds1'/></definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?><definition>" \
               "<datasource type='CLIENT' name='testds1'/></definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
        cmps = {name: xml, name2: xml2}

        self.setXML(el, xml)
        self.assertEqual(el.storeDataSource(name), None)
        self.__ds.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeDataSource(name2), None)
        self.__ds.append(name2)
        avc2 = el.availableDataSources()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.datasources([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            'nxsconfig show %s -d -s %s',
            'nxsconfig show %s -d --server %s',
            'nxsconfig show %s -d -s %s',
            'nxsconfig show %s -d --server %s',
            'nxsconfig show %s --datasources -s %s',
            'nxsconfig show %s --datasources --server %s',
            'nxsconfig show %s --datasources -s %s',
            'nxsconfig show %s --datasources --server %s',
        ]
        for scmd in commands:
            for nm in cmps.keys():
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                self.assertEqual(vl, cmps[nm])
                self.assertEqual(er, "")

        for scmd in commands:
            nm = name3
            cmd = (scmd % (nm, self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            er = er.strip()

            self.assertEqual(vl, "")
            self.assertEqual(
                er,
                "Error: DataSource '%s' not stored in the configuration server"
                % name3)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2),
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()

            self.assertEqual(vl.replace(">\n<", "><").replace("> <", "><"),
                             ("%s\n%s" % (cmps[name], cmps[name2])).replace(
                                 ">\n<", "><").replace("> <", "><"))
            self.assertEqual(er, "")

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name3),
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            er = er.strip()

            self.assertEqual(vl, "")
            self.assertEqual(
                er,
                "Error: DataSource '%s' not stored in the configuration server"
                % name3)

        self.assertEqual(el.deleteDataSource(name), None)
        self.__ds.pop(-2)
        self.assertEqual(el.deleteDataSource(name2), None)
        self.__ds.pop()

        el.close()

    def test_get_comp_av(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()
        man = el.mandatoryComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<definition><group type='NXentry'/>" \
              "\n</definition>\n"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field type='NXentry2'/>" \
               "$datasources.sl1right</definition>\n"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field type='NXentry2'/>" \
               "</definition>\n"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
        cmps = {name: xml, name2: xml2}

        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
        ]
        for scmd in commands:
            for nm in cmps.keys():
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()
                el.createConfiguration(man + [nm])
                cpxml = el.xmlstring
                cpxml = cpxml.strip("\n")
                self.assertEqual(vl.strip(), cpxml.strip())
                self.assertEqual(er, "")

        for scmd in commands:
            nm = name3
            cmd = (scmd % (nm, self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            er = er.strip()

            self.assertEqual(vl, "")
            self.assertEqual(
                er,
                "Error: Component '%s' not stored in the configuration server"
                % name3)

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2),
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            el.createConfiguration(man + [name, name2])
            cpxml = el.xmlstring
            cpxml = cpxml.strip("\n")
            self.assertEqual(vl.strip(), cpxml)

            self.assertEqual(er, "")

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name3),
                           self._sv.new_device_info_writer.name)).split()
            vl, er = self.runtest(cmd)
            vl = vl.strip()
            er = er.strip()
            cpxml = cpxml.strip("\n")

            self.assertEqual(vl, "")
            self.assertEqual(
                er,
                "Error: Component '%s' not stored in the configuration server"
                % name3)

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()

        el.close()

    def test_get_comp_incompnodes_groups(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()
        # man =
        el.mandatoryComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>\n<definition>" \
              "<group type='NXentry' name='test'/>\n</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?><definition>" \
               "<group type='NXentry2' name='test'/>" \
               "$datasources.sl1right</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
            # cmps = {name: xml, name2: xml2}

        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
        ]

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2),
                           self._sv.new_device_info_writer.name)).split()
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            old_stdin = sys.stdin
            sys.stdin = StringIO()
            sys.stdout = mystdout = StringIO()
            sys.stderr = mystderr = StringIO()
            old_argv = sys.argv
            sys.argv = cmd
            with self.assertRaises(SystemExit):
                nxsconfig.main()

            sys.argv = old_argv
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            sys.stdin = old_stdin
            vl = mystdout.getvalue().strip()
            # er =
            mystderr.getvalue()
            self.assertEqual(vl.strip(), "")

            # self.assertTrue(er.startswith(
            #     'Error: "Incompatible element attributes'))

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()

        el.close()

    def test_get_comp_incompnodes_fields(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()
        # man =
        el.mandatoryComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>\n<definition>" \
              "<field type='NXentry' name='test'/>\n</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?><definition>" \
               "<field type='NXentry2' name='test'/>" \
               "$datasources.sl1right</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
            # cmps = {name: xml, name2: xml2}

        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
        ]

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2),
                           self._sv.new_device_info_writer.name)).split()
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            old_stdin = sys.stdin
            sys.stdin = StringIO()
            sys.stdout = mystdout = StringIO()
            sys.stderr = mystderr = StringIO()
            old_argv = sys.argv
            sys.argv = cmd
            with self.assertRaises(SystemExit):
                nxsconfig.main()

            sys.argv = old_argv
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            sys.stdin = old_stdin
            vl = mystdout.getvalue().strip()
            # er =
            mystderr.getvalue()
            self.assertEqual(vl.strip(), "")

            # self.assertTrue(er.startswith(
            #     'Error: "Incompatible element attributes'))

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()

        el.close()

    def test_get_comp_incompnodes_tags(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()
        # man =
        el.mandatoryComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<field type='NXentry' name='test' />\n"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<field type='NXentry' name='test2'/>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
            # cmps = {name: xml, name2: xml2}

        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
        ]

        for scmd in commands:
            cmd = (scmd % ("%s %s" % (name, name2),
                           self._sv.new_device_info_writer.name)).split()
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            old_stdin = sys.stdin
            sys.stdin = StringIO()
            sys.stdout = mystdout = StringIO()
            sys.stderr = mystderr = StringIO()
            old_argv = sys.argv
            sys.argv = cmd
            with self.assertRaises(SystemExit):
                nxsconfig.main()

            sys.argv = old_argv
            sys.stdout = old_stdout
            sys.stdin = old_stdin
            sys.stderr = old_stderr
            #            el.createConfiguration(man + [name, name2])
            #            cpxml = el.xmlstring
            vl = mystdout.getvalue().strip()
            er = mystderr.getvalue()
            self.assertEqual(vl.strip(), "")
            self.assertEqual(str(er)[:5], "Error")

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()

        el.close()

    def test_get_comp_nods(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()
        avds = el.availableDataSources()
        # man =
        el.mandatoryComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        dsname = "mcs_test_datasource"
        dsname2 = "mcs_test_datasource2"
        while dsname in avds:
            dsname = dsname + '_1'

        while dsname2 in avds:
            dsname2 = dsname2 + '_2'

        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<definition><group type='NXentry'/>" \
              "$datasources.%s</definition>" % dsname
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field type='NXentry2'/>" \
               "$datasources.%s</definition>" % dsname2
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
        cmps = {name: xml, name2: xml2}
        dss = {name: dsname, name2: dsname2}
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        avc2 = el.availableComponents()
        # avdss = el.availableDataSources()
        # print(avc2)
        # print(avdss)
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
        ]
        for scmd in commands:
            for nm in cmps.keys():
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                # print(cmd)
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                old_stdin = sys.stdin
                sys.stdin = StringIO()
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                with self.assertRaises(SystemExit):
                    nxsconfig.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                sys.stdin = old_stdin
                vl = mystdout.getvalue().strip()
                er = mystderr.getvalue()
                # print(vl)
                # print(er)
                self.assertEqual(vl.strip(), "")
                self.assertEqual(
                    er,
                    "Error: Datasource %s not stored in "
                    "Configuration Server\n" % dss[nm])

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()

    def test_get_comp_nocp(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()
        # man =
        el.mandatoryComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        dsname = "mcs_test_subcp"
        dsname2 = "mcs_test_subcp2"
        while dsname in avc:
            dsname = dsname + '_1'

        while dsname2 in avc:
            dsname2 = dsname2 + '_2'

        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<definition><group type='NXentry'/>" \
              "$components.%s\n</definition>" % dsname
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field type='NXentry2'/>" \
               "$components.%s</definition>" % dsname2
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
        cmps = {name: xml, name2: xml2}
        dss = {name: dsname, name2: dsname2}
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
        ]
        for scmd in commands:
            for nm in cmps.keys():
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                old_stdin = sys.stdin
                sys.stdin = StringIO()
                sys.stdout = mystdout = StringIO()
                sys.stderr = mystderr = StringIO()
                old_argv = sys.argv
                sys.argv = cmd
                with self.assertRaises(SystemExit):
                    nxsconfig.main()

                sys.argv = old_argv
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                sys.stdin = old_stdin
                vl = mystdout.getvalue().strip()
                er = mystderr.getvalue()
                self.assertEqual(vl.strip(), "")
                self.assertEqual(
                    er,
                    "Error: Component %s not stored "
                    "in Configuration Server\n" % dss[nm])

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()

        el.close()

    def test_get_comp_ds(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()
        avds = el.availableDataSources()
        man = el.mandatoryComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        dsname = "mcs_test_datasource"
        dsname2 = "mcs_test_datasource2"
        while dsname in avds:
            dsname = dsname + '_1'

        while dsname2 in avds:
            dsname2 = dsname2 + '_2'

        xml = "<?xml version='1.0' encoding='utf-8'?>\n<definition>" \
              "<attribute type='NXentry'>$datasources.%s\n</attribute>" \
              "</definition>" % dsname
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field type='NXentry2'>" \
               "$datasources.%s</field></definition>" % dsname2
        dsxml = "<?xml version='1.0' encoding='utf-8'?><definition>" \
                "<datasource name='%s' type='TANGO'><datasource/>" \
                "</datasource></definition>" % dsname
        dsxml2 = "<?xml version='1.0' encoding='utf-8'?><definition>" \
                 "<datasource name='%s' type='CLIENT'><datasource/>" \
                 "</datasource></definition>" % dsname2
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
        cmps = {name: xml, name2: xml2}
        # dss = {name: dsname, name2: dsname2}
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        self.setXML(el, dsxml)
        self.assertEqual(el.storeDataSource(dsname), None)
        self.__ds.append(dsname)
        self.setXML(el, dsxml2)
        self.assertEqual(el.storeDataSource(dsname2), None)
        self.__ds.append(dsname2)
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
        ]
        for scmd in commands:
            for nm in cmps.keys():
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()

                el.createConfiguration(man + [nm])
                cpxml = el.xmlstring
                cpxml = cpxml.strip("\n")

                self.assertEqual(vl.strip(), cpxml)
                self.assertEqual(er.strip(), "")

        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop(-2)
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()
        self.assertEqual(el.deleteDataSource(dsname), None)
        self.__ds.pop(-2)
        self.assertEqual(el.deleteDataSource(dsname2), None)
        self.__ds.pop()

    def test_get_comp_cp(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        avc = el.availableComponents()
        man = el.mandatoryComponents()

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        dsname = "mcs_test_subcp"
        dsname2 = "mcs_test_subcp2"
        while dsname in avc:
            dsname = dsname + '_1'

        while dsname2 in avc:
            dsname2 = dsname2 + '_2'

        xml = "<?xml version='1.0' encoding='utf-8'?>\n" \
              "<definition><group type='NXentry'/>" \
              "$components.%s\n</definition>" % dsname
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><field type='NXentry2'/>" \
               "$components.%s</definition>" % dsname2
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        name3 = name + '_3'
        while name2 in avc:
            name2 = name2 + '_2'
        while name3 in avc:
            name3 = name3 + '_3'
            #        print avc
        cmps = {name: xml, name2: xml2}
        dss = {name: dsname, name2: dsname2}
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(dsname), None)
        self.__cmps.append(dsname)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(dsname2), None)
        self.__cmps.append(dsname2)
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
            'nxsconfig get %s -s %s',
            'nxsconfig get %s --server %s',
        ]
        for scmd in commands:
            for nm in cmps.keys():
                cmd = (scmd % (
                    nm, self._sv.new_device_info_writer.name)).split()
                vl, er = self.runtest(cmd)
                vl = vl.strip()
                el.createConfiguration(man + [nm, dss[nm]])
                cpxml = el.xmlstring
                cpxml = cpxml.strip("\n")
                self.assertEqual(vl.strip(), cpxml)
                self.assertEqual(er, "")

        self.assertEqual(el.deleteComponent(dsname2), None)
        self.__cmps.pop()
        self.assertEqual(el.deleteComponent(dsname), None)
        self.__cmps.pop()
        self.assertEqual(el.deleteComponent(name2), None)
        self.__cmps.pop()
        self.assertEqual(el.deleteComponent(name), None)
        self.__cmps.pop()

        el.close()

    # creatConf test
    def test_merge_default(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man

        commands = [
            ('nxsconfig merge -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig merge --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cmd in commands:
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()

            self.assertEqual('', er)
            self.assertEqual('', avc3)
        el.close()

    def test_merge_default_2(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        self.__man += man

        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = ["<definition><group type='NXentry'><field type='field'/>"
               "</group></definition>"]
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig merge -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig merge --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            cmd = list(cd)
            cmd.extend(name)
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()

            self.assertEqual('', er)
            checkxmls(self, xml[0], avc3)
        el.close()

    def test_merge_default_2_var(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        self.__man += man

        avc = el.availableComponents()
        el.variables = '{"myentry":"entry1"}'

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = ["<?xml version='1.0' encoding='utf-8'?><definition>"
               "<group type='NXentry' name='$var.myentry'/></definition>"]
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        result = "<?xml version='1.0' encoding='utf-8'?><definition>" \
            "<group type='NXentry' name='entry1'/></definition>"
        commands = [
            ('nxsconfig merge -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig merge --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            cmd = list(cd)
            cmd.extend(name)
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()

            self.assertEqual('', er)
            checkxmls(self, result, avc3)
        el.close()

    def test_merge_default_2_var_cp(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        self.__man += man

        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = ["<?xml version='1.0' encoding='utf-8'?><definition>"
               "<group type='NXentry' name='$var.myentry'/></definition>",
               "<?xml version='1.0' encoding='utf-8'?><definition><doc>"
               "$var(myentry=entry2)</doc></definition>"]

        result = '<?xml version="1.0" ?><definition>' \
            '<group name="entry2" type="NXentry"/>' \
            '<doc>$var(myentry=entry2)</doc></definition>'
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig merge -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig merge --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            cmd = list(cd)
            cmd.extend(name)
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()

            self.assertEqual('', er)
            checkxmls(self, result, avc3)
        el.close()

    def test_merge_2(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        result = "<?xml version='1.0' encoding='utf-8'?><definition>" \
            "<group type='NXentry'/>" \
            "<group type='NXentry2'/>" \
            "</definition>"

        self.assertTrue(isinstance(avc, list))
        name = "mcs_test_component"
        xml = "<?xml version='1.0' encoding='utf-8'?>" \
              "<definition><group type='NXentry'/>" \
              "</definition>"
        xml2 = "<?xml version='1.0' encoding='utf-8'?>" \
               "<definition><group type='NXentry2'/>" \
               "</definition>"
        while name in avc:
            name = name + '_1'
        name2 = name + '_2'
        while name2 in avc:
            name2 = name2 + '_2'
        self.setXML(el, xml)
        self.assertEqual(el.storeComponent(name), None)
        self.__cmps.append(name)
        self.setXML(el, xml2)
        self.assertEqual(el.storeComponent(name2), None)
        self.__cmps.append(name2)
        avc2 = el.availableComponents()
        # print avc2
        self.assertTrue(isinstance(avc2, list))
        for cp in avc:
            self.assertTrue(cp in avc2)

        self.assertTrue(name in avc2)
        cpx = el.components([name])
        self.assertEqual(cpx[0], xml)

        commands = [
            ('nxsconfig merge -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig merge --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            cmd = list(cd)
            cmd.extend([name, name2])
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()

            self.assertEqual('', er)
            checkxmls(self, avc3, result)
        el.close()

    def test_merge_group_field_3(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        self.__man += man

        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = ["<definition><group type='NXentry'><field type='field'/>"
               "</group></definition>"] * 3
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig merge -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig merge --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            cmd = list(cd)
            cmd.extend(name)
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()

            self.assertEqual('', er)
            checkxmls(self, xml[0], avc3)
        el.close()

    def test_merge_group_5(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        self.__man += man

        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = ["<definition><group type='NXentry'>"
               "</group></definition>"] * 5
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig merge -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig merge --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            cmd = list(cd)
            cmd.extend(name)
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()

            self.assertEqual('', er)
            checkxmls(self, xml[0], avc3)
        el.close()

    def test_merge_group_group(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        self.__man += man

        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = ["<definition><group type='NXentry'/></definition>",
               "<definition><group type='NXentry2'/></definition>"]
        np = len(xml)

        result = '<?xml version="1.0" ?>' \
            '<definition><group type="NXentry"/><group type="NXentry2"/>' \
            '</definition>'
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig merge -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig merge --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            cmd = list(cd)
            cmd.extend(name)
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()

            self.assertEqual('', er)
            checkxmls(self, result, avc3)
        el.close()

    def test_merge_group_group_2(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        self.__man += man

        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = ["<definition><group name='entry'/></definition>",
               "<definition><group type='NXentry2'/></definition>"]
        np = len(xml)

        result = '<?xml version="1.0" ?><definition>' \
            '<group name="entry" type="NXentry2"/></definition>'
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig merge -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig merge --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            cmd = list(cd)
            cmd.extend(name)
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()

            self.assertEqual('', er)
            checkxmls(self, result, avc3)
        el.close()

    def test_merge_group_group_3(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        self.__man += man

        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = ["<definition><group name='entry'/></definition>",
               "<definition><group name='entry' type='NXentry2'/>"
               "</definition>"]
        np = len(xml)

        result = '<?xml version="1.0" ?><definition>' \
            '<group name="entry" type="NXentry2"/></definition>'
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig merge -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig merge --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            cmd = list(cd)
            cmd.extend(name)
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()

            self.assertEqual('', er)
            checkxmls(self, result, avc3)
        el.close()

    def test_merge_group_group_4(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        self.__man += man

        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = ["<definition><group name='entry2'/></definition>",
               "<definition><group name='entry' type='NXentry'/>"
               "</definition>"]
        np = len(xml)

        result = '<?xml version="1.0" ?>' \
            '<definition><group name="entry" type="NXentry"/>' \
            '<group name="entry2"/></definition>'
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig merge -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig merge --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
        #        commands = [['nxsconfig', 'list']]
        for cd in commands:
            cmd = list(cd)
            cmd.extend(name)
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()

            self.assertEqual('', er)
            checkxmls(self, result, avc3)
        el.close()

    def test_merge_group_group_field(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        self.__man += man

        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = [
            "<definition><group type='NXentry'><field name='field1'/>"
            "</group></definition>",
            "<definition><group type='NXentry2'/><field name='field1'/>"
            "</definition>"]
        result = "<definition><group type='NXentry'><field name='field1'/>" \
            "</group><group type='NXentry2'/><field name='field1'/>" \
            "</definition>"
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig merge -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig merge --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            cmd = list(cd)
            cmd.extend(name)
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()

            self.assertEqual('', er)
            checkxmls(self, avc3, result)
        el.close()

    def test_merge_group_field_4(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        self.__man += man

        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = [
            "<definition><group type='NXentry'><field type='field'/>"
            "</group></definition>"] * 15
        result = '<?xml version="1.0" ?><definition><group type="NXentry">' \
            '<field type="field"/></group></definition>'
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig merge -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig merge --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            cmd = list(cd)
            cmd.extend(name)
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()

            self.assertEqual('', er)
            checkxmls(self, avc3, result)
        el.close()

    def test_merge_group_group_mandatory(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        self.__man += man

        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = ["<definition><group type='NXentry'/></definition>",
               "<definition><group type='NXentry2'/></definition>"]
        result = '<?xml version="1.0" ?>' \
            '<definition><group type="NXentry2"/><group type="NXentry"/>' \
            '</definition>'
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])
        el.setMandatoryComponents([name[0]])

        commands = [
            ('nxsconfig merge -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig merge --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            cmd = list(cd)
            cmd.append(name[1])
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()

            self.assertEqual('', er)
            checkxmls(self, avc3, result)
        el.close()

    def test_info_default(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = ["<definition><group type='NXentry'><field type='field'/>"
               "</group></definition>"]
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig info -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig info --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            cmd = list(cd)
            cmd.extend(name)
            vl, er = self.runtest(cmd)

            avc3 = vl.strip()
            doc = self.parseRST(avc3)
            self.assertEqual(len(doc), 1)
            section = doc[0]
            title = "Component: 'mcs_test_component_0'"
            self.assertEqual(section.tagname, 'section')
            self.assertEqual(len(section), 1)
            self.assertEqual(len(section[0]), 1)
            self.assertEqual(str(section[0]), '<title>%s</title>' % title)
            self.assertEqual('', er)
        el.close()

    def test_info_components(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = [
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition><field name='data' type='NX_FLOAT'>"
            "<datasource name='sl1right' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>"
            "<strategy mode='INIT'/>"
            "</field>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<field name='data'>"
            "<strategy mode='STEP'/>"
            "<datasource name='sl2bottom' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>"
            "</field>"
            "<field name='data2'>"
            "<datasource name='sl2top' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' "
            "encoding='LIMA_VIDEO_IMAGE'/>"
            "<record name='Position'/>"
            "</datasource>"
            "<strategy mode='FINAL'/>"
            "</field>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition><field name='data'>"
            "<datasource name='sl3right' type='PYEVAL'>"
            "<result>ds.result = 25.6"
            "</result>"
            "</datasource>"
            "<dimensions rank='1'>"
            "<dim index='0'  value='20'/>"
            "</dimensions>"
            "<strategy mode='INIT'/>"
            "</field>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition><field name='data' type='NX_CHAR'>"
            "<datasource name='sl1right' type='DB'>"
            "<database dbname='mydb' dbtype='PGSQL'/>"
            "<query format='IMAGE'>SELECT * from weather limit 3"
            "</query>"
            "</datasource>"
            "<dimensions rank='2' />"
            "<strategy mode='FINAL'/>"
            "</field>"
            "</definition>"
        ]
        header = '<thead><row>' \
            '<entry><paragraph>source_name</paragraph></entry>' \
            '<entry><paragraph>source_type</paragraph></entry>' \
            '<entry><paragraph>nexus_type</paragraph></entry>' \
            '<entry><paragraph>shape</paragraph></entry>' \
            '<entry><paragraph>strategy</paragraph></entry>' \
            '<entry><paragraph>source</paragraph></entry>' \
            '</row></thead>'

        result = [
            [
                ["sl1right", "CLIENT", "NX_FLOAT", None, "INIT", "motor_1"],
            ],
            [
                ["sl2bottom", "CLIENT", None, None, "STEP", "motor_2"],
                ["sl2top", "TANGO", None, None, "FINAL",
                 "haso.desy.de:10000/p09/motor/exp.01/Position"],
            ],
            [
                ["sl3right", "PYEVAL", None, "[20]", "INIT", "25.6"],
            ],
            [
                ["sl1right", "DB",  "NX_CHAR", "['*', '*']", "FINAL",
                 "SELECT * from weather limit 3"],
            ],
        ]
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig info -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig info --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            for ni, nm in enumerate(name):
                cmd = list(cd)
                cmd.append(nm)
                vl, er = self.runtest(cmd)
                self.assertEqual('', er)
                avc3 = vl.strip()
                doc = self.parseRST(avc3)
                self.assertEqual(len(doc), 1)
                section = doc[0]
                title = "Component: '%s'" % nm
                self.checkRSTSection(section, title, header, result[ni])
        el.close()

    def test_info_components_mandatory(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = [
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition><field name='datax' type='NX_FLOAT'>"
            "<datasource name='sl2right' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>"
            "<strategy mode='INIT'/>"
            "</field>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<field name='data'>"
            "<strategy mode='STEP'/>"
            "<datasource name='sl2bottom' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>"
            "</field>"
            "<field name='data2'>"
            "<datasource name='sl2top' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' "
            "encoding='LIMA_VIDEO_IMAGE'/>"
            "<record name='Position'/>"
            "</datasource>"
            "<strategy mode='FINAL'/>"
            "</field>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition><field name='data'>"
            "<datasource name='sl3right' type='PYEVAL'>"
            "<result>ds.result = 25.6"
            "</result>"
            "</datasource>"
            "<dimensions rank='1'>"
            "<dim index='0'  value='20'/>"
            "</dimensions>"
            "<strategy mode='INIT'/>"
            "</field>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition><field name='data' type='NX_CHAR'>"
            "<datasource name='sl1right' type='DB'>"
            "<database dbname='mydb' dbtype='PGSQL'/>"
            "<query format='IMAGE'>SELECT * from weather limit 3"
            "</query>"
            "</datasource>"
            "<dimensions rank='2' />"
            "<strategy mode='FINAL'/>"
            "</field>"
            "</definition>"
        ]
        header = '<thead><row>' \
            '<entry><paragraph>source_name</paragraph></entry>' \
            '<entry><paragraph>source_type</paragraph></entry>' \
            '<entry><paragraph>nexus_type</paragraph></entry>' \
            '<entry><paragraph>shape</paragraph></entry>' \
            '<entry><paragraph>strategy</paragraph></entry>' \
            '<entry><paragraph>source</paragraph></entry>' \
            '</row></thead>'

        result = [
            [
                ["sl2bottom", "CLIENT", None, None, "STEP", "motor_2"],
                ["sl2top", "TANGO", None, None, "FINAL",
                 "haso.desy.de:10000/p09/motor/exp.01/Position"],
                ["sl2right", "CLIENT", "NX_FLOAT", None, "INIT", "motor_1"],
            ],
            [
                ["sl3right", "PYEVAL", None, "[20]", "INIT", '25.6'],
                ["sl2right", "CLIENT", "NX_FLOAT", None, "INIT", "motor_1"],
            ],
            [
                ["sl1right", "DB",  "NX_CHAR", "['*', '*']", "FINAL",
                 "SELECT * from weather limit 3"],
                ["sl2right", "CLIENT", "NX_FLOAT", None, "INIT", "motor_1"],
            ],
        ]
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])
        self.assertEqual(el.setMandatoryComponents([name[0]]), None)

        commands = [
            ('nxsconfig info -m -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig info -m --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig info --mandatory -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig info --mandatory --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            for ni, nm in enumerate(name[1:]):
                cmd = list(cd)
                cmd.append(nm)
                vl, er = self.runtest(cmd)
                self.assertEqual('', er)
                avc3 = vl.strip()
                doc = self.parseRST(avc3)
                self.assertEqual(len(doc), 1)
                section = doc[0]
                self.checkRSTTable(section, header, result[ni], sort=True)
        el.close()

    def test_info_components_external(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()
        avds = el.availableDataSources()

        oname = "mcs_test_component"
        odsname = "mcs_test_datasource"
        self.assertTrue(isinstance(avc, list))
        xml = [
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition><field name='data' type='NX_FLOAT'>"
            "$datasources.%s"
            "<strategy mode='INIT'/>"
            "</field>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<field name='data'>"
            "<strategy mode='STEP'/>"
            "$datasources.%s"
            "</field>"
            "<field name='data2'>"
            "$datasources.%s"
            "<strategy mode='FINAL'/>"
            "</field>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition><field name='data'>"
            "$datasources.%s"
            "<dimensions rank='1'>"
            "<dim index='0'  value='20'/>"
            "</dimensions>"
            "<strategy mode='INIT'/>"
            "</field>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition><field name='data' type='NX_CHAR'>"
            "$datasources.%s"
            "<dimensions rank='2' />"
            "<strategy mode='FINAL'/>"
            "</field>"
            "</definition>"
        ]
        xds = [
            "<datasource name='%s' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>",
            "<datasource name='%s' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>",
            "<datasource name='%s' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' "
            "encoding='LIMA_VIDEO_IMAGE'/>"
            "<record name='Position'/>"
            "</datasource>",
            "<datasource name='%s' type='PYEVAL'>"
            "<result>ds.result = 25.6"
            "</result>"
            "</datasource>",
            "<datasource name='%s' type='DB'>"
            "<database dbname='mydb' dbtype='PGSQL'/>"
            "<query format='IMAGE'>SELECT * from weather limit 3"
            "</query>"
            "</datasource>",
        ]

        header = '<thead><row>' \
            '<entry><paragraph>source_name</paragraph></entry>' \
            '<entry><paragraph>source_type</paragraph></entry>' \
            '<entry><paragraph>nexus_type</paragraph></entry>' \
            '<entry><paragraph>shape</paragraph></entry>' \
            '<entry><paragraph>strategy</paragraph></entry>' \
            '<entry><paragraph>source</paragraph></entry>' \
            '</row></thead>'

        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        dsname = []
        for i in range(len(xds)):

            dsname.append(odsname + '_%s' % i)
            while dsname[i] in avds:
                dsname[i] = dsname[i] + '_%s' % i
        dss = {
            name[0]: [dsname[0]],
            name[1]: [dsname[1], dsname[2]],
            name[2]: [dsname[3]],
            name[3]: [dsname[4]],
        }

        result = [
            [
                [dsname[0], "CLIENT", "NX_FLOAT", None, "INIT", "motor_1"],
            ],
            [
                [dsname[1], "CLIENT", None, None, "STEP", "motor_2"],
                [dsname[2], "TANGO", None, None, "FINAL",
                 "haso.desy.de:10000/p09/motor/exp.01/Position"],
            ],
            [
                [dsname[3], "PYEVAL", None, "[20]", "INIT", "25.6"],
            ],
            [
                [dsname[4], "DB",  "NX_CHAR", "['*', '*']", "FINAL",
                 "SELECT * from weather limit 3"],
            ],
        ]
        for i in range(np):
            self.setXML(el, xml[i] % tuple(dss[name[i]]))
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        dsnp = len(xds)
        for i in range(dsnp):
            self.setXML(el, xds[i] % dsname[i])
            self.assertEqual(el.storeDataSource(dsname[i]), None)
            self.__ds.append(dsname[i])

        commands = [
            ('nxsconfig info -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig info --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            for ni, nm in enumerate(name):
                cmd = list(cd)
                cmd.append(nm)
                vl, er = self.runtest(cmd)
                self.assertEqual('', er)
                avc3 = vl.strip()
                doc = self.parseRST(avc3)
                self.assertEqual(len(doc), 1)
                section = doc[0]
                title = "Component: '%s'" % nm
                self.checkRSTSection(section, title, header, result[ni])
        el.close()

    def test_info_datasources(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()

        odsname = "mcs_test_datasource"
        avds = el.availableDataSources()
        xds = [
            "<datasource name='%s' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>",
            "<datasource name='%s' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>",
            "<datasource name='%s' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' "
            "encoding='LIMA_VIDEO_IMAGE'/>"
            "<record name='Position'/>"
            "</datasource>",
            "<datasource name='%s' type='PYEVAL'>"
            "<result>ds.result = 25.6"
            "</result>"
            "</datasource>",
            "<datasource name='%s' type='DB'>"
            "<database dbname='mydb' dbtype='PGSQL'/>"
            "<query format='IMAGE'>SELECT * from weather limit 3"
            "</query>"
            "</datasource>",
        ]

        header = '<thead><row>' \
            '<entry><paragraph>source_type</paragraph></entry>' \
            '<entry><paragraph>source</paragraph></entry>' \
            '</row></thead>'
        dsname = []
        for i in range(len(xds)):
            dsname.append(odsname + '_%s' % i)
            while dsname[i] in avds:
                dsname[i] = dsname[i] + '_%s' % i

        result = [
            [
                ["CLIENT", "motor_1"]
            ],
            [
                ["CLIENT", "motor_2"]
            ],
            [
                ["TANGO",
                 "haso.desy.de:10000/p09/motor/exp.01/Position"]
            ],
            [
                ["PYEVAL", "25.6"]
            ],
            [
                ["DB", "SELECT * from weather limit 3"]
            ],
        ]
        dsnp = len(xds)
        for i in range(dsnp):
            self.setXML(el, xds[i] % dsname[i])
            self.assertEqual(el.storeDataSource(dsname[i]), None)
            self.__ds.append(dsname[i])

        commands = [
            ('nxsconfig info -d -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig info -d --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig info --datasources -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig info --datasources --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            for ni, nm in enumerate(dsname):
                cmd = list(cd)
                cmd.append(nm)
                vl, er = self.runtest(cmd)
                self.assertEqual('', er)
                avc3 = vl.strip()
                doc = self.parseRST(avc3)
                self.assertEqual(len(doc), 1)
                section = doc[0]
                title = "DataSource: '%s'" % nm
                self.checkRSTSection(section, title, header, result[ni])
        el.close()

    def test_info_profiles(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()

        oslname = "mcs_test_profile"
        avds = el.availableSelections()
        xds = [
            '{"Timer": "[\\"ct01\\"]", "DataSourceSelection": '
            '"{\\"exp_mca01\\": true}"}',
            '{"ComponentSelection": "{\\"pilatus\\": true}"}',
            '{"UnplottedComponents": "[\\"exp_c01\\"]", '
            '"DataSourceSelection": "{\\"exp_c01\\": true, '
            '\\"exp_c02\\": true, \\"exp_c03\\": false}", '
            '"DataSourcePreselection": '
            '"{\\"exp_mot04\\": true, \\"exp_mot03\\": false, '
            '\\"nexdatas_configuration\\": false}", '
            '"Version": "3.12.4", '
            '"DefaultDynamicLinks": true, '
            '"ConfigVariables": "{}", '
            '"ComponentPreselection": '
            '"{\\"beamtime_id\\": true, \\"slit2\\": true, '
            '\\"slit1\\": false}", '
            '"TimeZone": "Europe/Berlin", '
            '"ComponentsFromMntGrp": false, '
            '"Timer": "[\\"exp_t01\\"]", '
            '"UserData": "{\\"sample_name\\": \\"\\", '
            '\\"chemical_formula\\": \\"\\", \\"title\\": \\"\\"}", '
            '"Door": "p09/door/haso228jk.01", '
            '"ConfigDevice": "p09/nxsconfigserver/haso228jk", '
            '"DynamicComponents": true, '
            '"AppendEntry": false, '
            '"MntGrp": "mg_test01", '
            '"WriterDevice": "p00/nxsdatawriter/haso228", '
            '"OptionalComponents": "[\\"slit5\\"]", '
            '"ComponentSelection": '
            '"{\\"lmbd01\\": true, \\"lmbd02\\": false}", '
            '"DefaultDynamicPath": '
            '"/$var.entryname#\'scan\'$var.serialno:NXentry/'
            'NXinstrument/collection"}',
            '{"DataSourceSelection": '
            '"{\\"exp_c01\\": true, \\"exp_c02\\": true, '
            '\\"exp_c03\\": true, \\"exp_c04\\": true}", '
            '"DataSourcePreselection": '
            '"{\\"exp_mot04\\": true, \\"exp_mot03\\": true, '
            '\\"exp_mot05\\": true, \\"exp_mot06\\": true, '
            '\\"nexdatas_configuration\\": false}", '
            '"ComponentPreselection": '
            '"{\\"beamtime_id\\": true, \\"slit2\\": true, '
            '\\"slit1\\": true, \\"slit3\\": true}", '
            '"ComponentSelection": '
            '"{\\"lmbd01\\": true, \\"lmbd02\\": true, '
            '\\"lmbd03\\": true, \\"lmbd04\\": true}", '
            '"OrderedChannels": '
            '"['
            '\\"exp_c03\\", \\"exp_c02\\", '
            '\\"lmbd04\\", \\"lmbd03\\", '
            '\\"exp_mot06\\", \\"exp_mot04\\", '
            '\\"slit2\\", \\"slit1\\" '
            ']", '
            '"DefaultDynamicPath": '
            '"/$var.entryname#\'scan\'$var.serialno:NXentry/'
            'NXinstrument/collection"}'
        ]

        header = None
        slname = []
        for i in range(len(xds)):
            slname.append(oslname + '_%s' % i)
            while slname[i] in avds:
                slname[i] = slname[i] + '_%s' % i

        result = [
            [
                ["Timer(s):", "ct01"],
                ["Pool/Dynamic Detector Components:", "exp_mca01"],
            ],
            [
                ["Detector Components:", "pilatus"]
            ],
            [
                ["Timer(s):", "exp_t01"],
                ["Pool/Dynamic Detector Components:", "exp_c01, exp_c02"],
                ["Detector Components:", "lmbd01"],
                ["Descriptive Components:", "beamtime_id, slit2"],
                ["Descriptive Dynamic Components:", 'exp_mot04'],
                ["User Data:",
                 "{\"sample_name\": \"\", \"chemical_formula\": \"\", "
                 "\"title\": \"\"}"],
                ["AppendEntry:", "False"],
                ["ConfigDevice:", "p09/nxsconfigserver/haso228jk"],
                ["WriterDevice:", "p00/nxsdatawriter/haso228"],
                ["Door:", "p09/door/haso228jk.01"],
                ["DynamicComponents:", "True"],
                ["ComponentsFromMntGrp:", "False"],
                ["DefaultDynamicLinks:", "True"],
                ["DefaultDynamicPath:",
                 "/$var.entryname#'scan'$var.serialno:NXentry/"
                 "NXinstrument/collection"],
                ["Unplotted Components:", "exp_c01"],
                ["OptionalComponents:", "slit5"],
                ["ConfigVariables:", "{}"]
            ],
            [
                ["Pool/Dynamic Detector Components:",
                 "exp_c03, exp_c02, exp_c01, exp_c04"],
                ["Detector Components:",
                 "lmbd04, lmbd03, lmbd01, lmbd02"],
                ["Descriptive Components:",
                 "slit2, slit1, beamtime_id, slit3"],
                ["Descriptive Dynamic Components:",
                 'exp_mot06, exp_mot04, exp_mot03, exp_mot05'],
                ["DefaultDynamicPath:",
                 "/$var.entryname#'scan'$var.serialno:NXentry/"
                 "NXinstrument/collection"]
            ],
        ]
        dsnp = len(xds)
        for i in range(dsnp):
            self.setSelection(el, xds[i])
            self.assertEqual(el.storeSelection(slname[i]), None)
            self.__sels.append(slname[i])

        commands = [
            ('nxsconfig info -r -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig info -r --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig info --profiles -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig info --profiles --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            for ni, nm in enumerate(slname):
                cmd = list(cd)
                cmd.append(nm)
                vl, er = self.runtest(cmd)
                self.assertEqual('', er)
                # print(vl)
                avc3 = vl.strip()
                doc = self.parseRST(avc3)
                self.assertEqual(len(doc), 1)
                section = doc[0]
                title = "Profile: '%s'" % nm
                self.checkRSTSection(section, title, header, result[ni])
        el.close()

    def test_geometry_components(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = [
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='data' type='NXdata'>"
            "<field name='slit1' type='NX_FLOAT' units='mm'>"
            "<datasource name='sl1right' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>"
            "<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='instrument' type='NXinstrument'>"
            "<group name='slit2' type='NXslit'>"
            "<field name='y_gap' type='NX_FLOAT' units='mm'>"
            "<strategy mode='STEP' />"
            "<datasource name='ygap' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_CHAR' name='depends_on'>"
            "transformations/yoffset'<strategy mode='INIT'/>"
            "</field>"
            "<group name='transformations' type='NXtransformations'>"
            "<field depends_on='rot' name='yoffset'  "
            "type='NX_FLOAT64' units='m' >"
            "<attribute type='NX_CHAR' name='transformation_type'>"
            "translation<strategy mode='INIT'/></attribute>"
            "<attribute type='NX_FLOAT64' name='vector'>0 1 0"
            "<dimensions rank='1'><dim value='3' index='1'/>"
            "</dimensions><strategy mode='INIT'/>"
            "</attribute>"
            "<attribute type='NX_FLOAT64' name='offset'>2.3 0.3 3.4"
            "<dimensions rank='1'><dim value='3' index='1'/>"
            "</dimensions><strategy mode='INIT'/>"
            "</attribute>"
            "<datasource name='y_offset' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' />"
            "<record name='Position'/>"
            "</datasource>"
            "<strategy mode='INIT'/>"
            "</field>"
            "<field type='NX_FLOAT' name='rot' units='deg' "
            "transformation_type='rotation' vector='0 1 0' >"
            "4.5<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</group>"
            "</group>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='instrument' type='NXinstrument'>"
            "<group name='pinhole' type='NXpinhole'>"
            "<field name='diameter' type='NX_FLOAT' units='mm'>"
            "<strategy mode='STEP' />"
            "<datasource name='phdiameter' type='CLIENT'>"
            "<record name='ph_diameter'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_CHAR' name='depends_on'>"
            "transformations/y'<strategy mode='INIT'/>"
            "</field>"
            "<group name='transformations' type='NXtransformations'>"
            "<field type='NX_FLOAT' depends_on='x' name='y' units='mm' "
            "transformation_type='translation' vector='0 1 0' >"
            "<strategy mode='STEP' />"
            "<datasource name='phy' type='CLIENT'>"
            "<record name='ph_y'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_FLOAT' name='x' units='mm' "
            "transformation_type='translation' vector='1 0 0' >"
            "14.5<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</group>"
            "</group>"
            "</definition>"
        ]
        header = '<thead><row>' \
            '<entry><paragraph>nexus_path</paragraph></entry>' \
            '<entry><paragraph>source_name</paragraph></entry>' \
            '<entry><paragraph>units</paragraph></entry><entry>' \
            '<paragraph>trans_type</paragraph></entry><entry>' \
            '<paragraph>trans_vector</paragraph></entry><entry>' \
            '<paragraph>trans_offset</paragraph></entry><entry>' \
            '<paragraph>depends_on</paragraph></entry>' \
            '</row></thead>'

        result = [
            [
                ["entry/data/slit1",
                 "sl1right", "mm", None, None, None, None],
            ],
            [
                ["entry/instrument/slit2/y_gap",
                 "ygap", "mm", None, None, None, None],
                ["entry/instrument/slit2/depends_on",
                 None, None, None, None, None, "[transformations/yoffset']"],
                ["entry/instrument/slit2/transformations/yoffset",
                 "y_offset", "m", "translation", "0 1 0",
                 "2.3 0.3 3.4", "rot"],
                ["entry/instrument/slit2/transformations/rot",
                 None, "deg", "rotation", "0 1 0",
                 None, None],
            ],
            [
                ["entry/instrument/pinhole/diameter",
                 "phdiameter", "mm", None, None, None, None],
                ["entry/instrument/pinhole/depends_on",
                 None, None, None, None, None, "[transformations/y']"],
                ["entry/instrument/pinhole/transformations/y",
                 "phy", "mm", "translation", "0 1 0", None, "x"],
                ["entry/instrument/pinhole/transformations/x",
                 None, "mm", "translation", "1 0 0", None, None],
            ],
        ]
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig geometry -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig geometry --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            for ni, nm in enumerate(name):
                cmd = list(cd)
                cmd.append(nm)
                vl, er = self.runtest(cmd)
                print(vl)
                self.assertEqual('', er)
                avc3 = vl.strip()
                doc = self.parseRST(avc3)
                self.assertEqual(len(doc), 1)
                section = doc[0]
                title = "Component: '%s'" % nm
                self.checkRSTSection(section, title, header, result[ni])
        el.close()

    def test_geometry_components_mandatory(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = [
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='data' type='NXdata'>"
            "<field name='slit1' type='NX_FLOAT' units='mm'>"
            "<datasource name='sl1right' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>"
            "<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='instrument' type='NXinstrument'>"
            "<group name='slit2' type='NXslit'>"
            "<field name='y_gap' type='NX_FLOAT' units='mm'>"
            "<strategy mode='STEP' />"
            "<datasource name='ygap' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_CHAR' name='depends_on'>"
            "transformations/yoffset<strategy mode='INIT'/>"
            "</field>"
            "<group name='transformations' type='NXtransformations'>"
            "<field depends_on='rot' name='yoffset'  "
            "type='NX_FLOAT64' units='m' >"
            "<attribute type='NX_CHAR' name='transformation_type'>"
            "translation<strategy mode='INIT'/></attribute>"
            "<attribute type='NX_FLOAT64' name='vector'>0 1 0"
            "<dimensions rank='1'><dim value='3' index='1'/>"
            "</dimensions><strategy mode='INIT'/>"
            "</attribute>"
            "<attribute type='NX_FLOAT64' name='offset'>2.3 0.3 3.4"
            "<dimensions rank='1'><dim value='3' index='1'/>"
            "</dimensions><strategy mode='INIT'/>"
            "</attribute>"
            "<datasource name='y_offset' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' />"
            "<record name='Position'/>"
            "</datasource>"
            "<strategy mode='INIT'/>"
            "</field>"
            "<field type='NX_FLOAT' name='rot' units='deg' "
            "transformation_type='rotation' vector='0 1 0' >"
            "4.5<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</group>"
            "</group>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='instrument' type='NXinstrument'>"
            "<group name='pinhole' type='NXpinhole'>"
            "<field name='diameter' type='NX_FLOAT' units='mm'>"
            "<strategy mode='STEP' />"
            "<datasource name='phdiameter' type='CLIENT'>"
            "<record name='ph_diameter'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_CHAR' name='depends_on'>"
            "transformations/y<strategy mode='INIT'/>"
            "</field>"
            "<group name='transformations' type='NXtransformations'>"
            "<field type='NX_FLOAT' depends_on='x' name='y' units='mm' "
            "transformation_type='translation' vector='0 1 0' >"
            "<strategy mode='STEP' />"
            "<datasource name='phy' type='CLIENT'>"
            "<record name='ph_y'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_FLOAT' name='x' units='mm' "
            "transformation_type='translation' vector='1 0 0' >"
            "14.5<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</group>"
            "</group>"
            "</definition>"
        ]
        header = '<thead><row>' \
            '<entry><paragraph>nexus_path</paragraph></entry>' \
            '<entry><paragraph>source_name</paragraph></entry>' \
            '<entry><paragraph>units</paragraph></entry><entry>' \
            '<paragraph>trans_type</paragraph></entry><entry>' \
            '<paragraph>trans_vector</paragraph></entry><entry>' \
            '<paragraph>trans_offset</paragraph></entry><entry>' \
            '<paragraph>depends_on</paragraph></entry>' \
            '</row></thead>'

        result = [
            [
                ["entry/data/slit1",
                 "sl1right", "mm", None, None, None, None],
                ["entry/instrument/slit2/y_gap",
                 "ygap", "mm", None, None, None, None],
                ["entry/instrument/slit2/depends_on",
                 None, None, None, None, None, "[transformations/yoffset]"],
                ["entry/instrument/slit2/transformations/yoffset",
                 "y_offset", "m", "translation", "0 1 0",
                 "2.3 0.3 3.4", "rot"],
                ["entry/instrument/slit2/transformations/rot",
                 None, "deg", "rotation", "0 1 0",
                 None, None],
            ],
            [
                ["entry/data/slit1",
                 "sl1right", "mm", None, None, None, None],
                ["entry/instrument/pinhole/diameter",
                 "phdiameter", "mm", None, None, None, None],
                ["entry/instrument/pinhole/depends_on",
                 None, None, None, None, None, "[transformations/y]"],
                ["entry/instrument/pinhole/transformations/y",
                 "phy", "mm", "translation", "0 1 0", None, "x"],
                ["entry/instrument/pinhole/transformations/x",
                 None, "mm", "translation", "1 0 0", None, None],
            ],
        ]
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])
        self.assertEqual(el.setMandatoryComponents([name[0]]), None)

        commands = [
            ('nxsconfig geometry -m -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig geometry -m --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig geometry --mandatory -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig geometry --mandatory --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            for ni, nm in enumerate(name[1:]):
                cmd = list(cd)
                cmd.append(nm)
                vl, er = self.runtest(cmd)
                self.assertEqual('', er)
                avc3 = vl.strip()
                doc = self.parseRST(avc3)
                self.assertEqual(len(doc), 1)
                section = doc[0]
                self.checkRSTTable(section, header, result[ni], sort=True)
        el.close()

    def test_describe_datasources(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()

        odsname = "mcs_test_datasource"
        avds = el.availableDataSources()
        xds = [
            "<datasource name='%s' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>",
            "<datasource name='%s' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>",
            "<datasource name='%s' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' "
            "encoding='LIMA_VIDEO_IMAGE'/>"
            "<record name='Position'/>"
            "</datasource>",
            "<datasource name='%s' type='PYEVAL'>"
            "<result>ds.result = 25.6"
            "</result>"
            "</datasource>",
            "<datasource name='%s' type='DB'>"
            "<database dbname='mydb' dbtype='PGSQL'/>"
            "<query format='IMAGE'>SELECT * from weather limit 3"
            "</query>"
            "</datasource>",
        ]

        header = '<thead><row>' \
            '<entry><paragraph>source_type</paragraph></entry>' \
            '<entry><paragraph>source</paragraph></entry>' \
            '</row></thead>'
        dsname = []
        for i in range(len(xds)):
            dsname.append(odsname + '_%s' % i)
            while dsname[i] in avds:
                dsname[i] = dsname[i] + '_%s' % i

        result = [
            [
                ["CLIENT", "motor_1"]
            ],
            [
                ["CLIENT", "motor_2"]
            ],
            [
                ["TANGO",
                 "haso.desy.de:10000/p09/motor/exp.01/Position"]
            ],
            [
                ["PYEVAL", "25.6"]
            ],
            [
                ["DB", "SELECT * from weather limit 3"]
            ],
        ]
        dsnp = len(xds)
        for i in range(dsnp):
            self.setXML(el, xds[i] % dsname[i])
            self.assertEqual(el.storeDataSource(dsname[i]), None)
            self.__ds.append(dsname[i])

        commands = [
            ('nxsconfig describe -d -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig describe -d --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig describe --datasources -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig describe --datasources --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            for ni, nm in enumerate(dsname):
                cmd = list(cd)
                cmd.append(nm)
                vl, er = self.runtest(cmd)
                self.assertEqual('', er)
                avc3 = vl.strip()
                doc = self.parseRST(avc3)
                self.assertEqual(len(doc), 1)
                section = doc[0]
                title = "DataSource: '%s'" % nm
                self.checkRSTSection(section, title, header, result[ni])
        el.close()

    def test_describe_datasources_filters(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()

        odsname = "mcs_test_datasource"
        avds = el.availableDataSources()
        xds = [
            "<datasource name='%s' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>",
            "<datasource name='%s' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>",
            "<datasource name='%s' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' "
            "encoding='LIMA_VIDEO_IMAGE'/>"
            "<record name='Position'/>"
            "</datasource>",
            "<datasource name='%s' type='PYEVAL'>"
            "<result>ds.result = 25.6"
            "</result>"
            "</datasource>",
            "<datasource name='%s' type='DB'>"
            "<database dbname='mydb' dbtype='PGSQL'/>"
            "<query format='IMAGE'>SELECT * from weather limit 3"
            "</query>"
            "</datasource>",
        ]

        header = '<thead><row>' \
            '<entry><paragraph>source_type</paragraph></entry>' \
            '<entry><paragraph>source</paragraph></entry>' \
            '</row></thead>'
        dsname = []
        for i in range(len(xds)):
            dsname.append(odsname + '_%s' % i)
            while dsname[i] in avds:
                dsname[i] = dsname[i] + '_%s' % i

        result = [
            [
                ["CLIENT", "motor_1"]
            ],
            [
                ["CLIENT", "motor_2"]
            ],
            [
                # ["TANGO",
                #  "haso.desy.de:10000/p09/motor/exp.01/Position"]
            ],
            [
                # ["PYEVAL", None]
            ],
            [
                # ["DB", None]
            ],
        ]
        dsnp = len(xds)
        for i in range(dsnp):
            self.setXML(el, xds[i] % dsname[i])
            self.assertEqual(el.storeDataSource(dsname[i]), None)
            self.__ds.append(dsname[i])

        commands = [
            ('nxsconfig describe -d -s %s -f *CLIENT* '
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig describe -d --server %s  --filters *CLIENT* '
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig describe --datasources -s %s -f *CLIENT* '
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig describe --datasources --server %s  --filters *CLIENT*'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            for ni, nm in enumerate(dsname):
                cmd = list(cd)
                cmd.append(nm)
                vl, er = self.runtest(cmd)
                self.assertEqual('', er)
                avc3 = vl.strip()
                doc = self.parseRST(avc3)
                self.assertEqual(len(doc), 1)
                section = doc[0]
                title = "DataSource: '%s'" % nm
                self.checkRSTSection(section, title, header, result[ni])
        el.close()

    def test_describe_components(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = [
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='data' type='NXdata'>"
            "<field name='slit1' type='NX_FLOAT' units='mm'>"
            "<datasource name='sl1right' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>"
            "<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='instrument' type='NXinstrument'>"
            "<group name='slit2' type='NXslit'>"
            "<field name='y_gap' type='NX_FLOAT' units='mm'>"
            "<strategy mode='STEP' />"
            "<datasource name='ygap' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_CHAR' name='depends_on'>"
            "transformations/yoffset<strategy mode='INIT'/>"
            "</field>"
            "<group name='transformations' type='NXtransformations'>"
            "<field depends_on='rot' name='yoffset'  "
            "type='NX_FLOAT64' units='m' >"
            "<attribute type='NX_CHAR' name='transformation_type'>"
            "translation<strategy mode='INIT'/></attribute>"
            "<attribute type='NX_FLOAT64' name='vector'>0 1 0"
            "<dimensions rank='1'><dim value='3' index='1'/>"
            "</dimensions><strategy mode='INIT'/>"
            "</attribute>"
            "<attribute type='NX_FLOAT64' name='offset'>2.3 0.3 3.4"
            "<dimensions rank='1'><dim value='3' index='1'/>"
            "</dimensions><strategy mode='INIT'/>"
            "</attribute>"
            "<datasource name='y_offset' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' />"
            "<record name='Position'/>"
            "</datasource>"
            "<strategy mode='INIT'/>"
            "</field>"
            "<field type='NX_FLOAT' name='rot' units='deg' "
            "transformation_type='rotation' vector='0 1 0' >"
            "4.5<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</group>"
            "</group>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='instrument' type='NXinstrument'>"
            "<group name='pinhole' type='NXpinhole'>"
            "<field name='diameter' type='NX_FLOAT' units='mm'>"
            "<strategy mode='STEP' />"
            "<datasource name='phdiameter' type='CLIENT'>"
            "<record name='ph_diameter'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_CHAR' name='depends_on'>"
            "transformations/y<strategy mode='INIT'/>"
            "</field>"
            "<group name='transformations' type='NXtransformations'>"
            "<field type='NX_FLOAT' depends_on='x' name='y' units='mm' "
            "transformation_type='translation' vector='0 1 0' >"
            "<strategy mode='STEP' />"
            "<datasource name='phy' type='CLIENT'>"
            "<record name='ph_y'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_FLOAT' name='x' units='mm' "
            "transformation_type='translation' vector='1 0 0' >"
            "14.5<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</group>"
            "</group>"
            "</definition>"
        ]
        header = '<thead><row>' \
            '<entry><paragraph>nexus_path</paragraph></entry>' \
            '<entry><paragraph>nexus_type</paragraph></entry>' \
            '<entry><paragraph>strategy</paragraph></entry>' \
            '<entry><paragraph>shape</paragraph></entry>' \
            '<entry><paragraph>units</paragraph></entry>' \
            '<entry><paragraph>depends_on</paragraph></entry>' \
            '<entry><paragraph>trans_type</paragraph></entry>' \
            '<entry><paragraph>trans_vector</paragraph></entry>' \
            '<entry><paragraph>trans_offset</paragraph></entry>' \
            '<entry><paragraph>source_name</paragraph></entry>' \
            '<entry><paragraph>source_type</paragraph></entry>' \
            '<entry><paragraph>source</paragraph></entry>' \
            '<entry><paragraph>value</paragraph></entry>' \
            '</row></thead>'

        result = [
            [
                ["entry/data/slit1",
                 "NX_FLOAT", "INIT", None, "mm",
                 None, None, None, None,
                 "sl1right", "CLIENT", "motor_1", None],
            ],
            [
                ["entry/instrument/slit2/y_gap",
                 "NX_FLOAT", "STEP", None, "mm",
                 None, None, None, None,
                 "ygap", "CLIENT", "motor_2", None],
                ["entry/instrument/slit2/depends_on",
                 "NX_CHAR", "INIT", None, None,
                 "[transformations/yoffset]", None, None, None,
                 None, None, None, "transformations/yoffset"],
                ["entry/instrument/slit2/transformations/yoffset",
                 "NX_FLOAT64", "INIT", None, "m",
                 "rot", "translation", "0 1 0", "2.3 0.3 3.4",
                 "y_offset", "TANGO",
                 "haso.desy.de:10000/p09/motor/exp.01/Position", None],
                ["entry/instrument/slit2/transformations/rot",
                 "NX_FLOAT", "INIT", None, "deg",
                 None, "rotation", "0 1 0",  None,
                 None, None, None, "4.5"],
                ["entry/instrument/slit2/transformations/"
                 "yoffset@transformation_type",
                 "NX_CHAR", "INIT", None, None,
                 None, "translation", None, None,
                 None, None, None, "translation"],
                ["entry/instrument/slit2/transformations/yoffset@vector",
                 "NX_FLOAT64", "INIT", "[3]", None,
                 None, None, "0 1 0", None,
                 None, None, None, "0 1 0"],
                ["entry/instrument/slit2/transformations/yoffset@offset",
                 "NX_FLOAT64", "INIT", "[3]", None,
                 None, None, None, "2.3 0.3 3.4",
                 None, None, None, "2.3 0.3 3.4"],
            ],
            [
                ["entry/instrument/pinhole/diameter",
                 "NX_FLOAT", "STEP", None, "mm",
                 None, None, None, None,
                 "phdiameter", "CLIENT", "ph_diameter", None],
                ["entry/instrument/pinhole/depends_on",
                 "NX_CHAR", "INIT",  None, None,
                 "[transformations/y]", None, None, None,
                 None, None, None, "transformations/y"],
                ["entry/instrument/pinhole/transformations/y",
                 "NX_FLOAT", "STEP", None, "mm",
                 "x", "translation", "0 1 0", None,
                 "phy", "CLIENT", "ph_y", None],
                ["entry/instrument/pinhole/transformations/x",
                 "NX_FLOAT", "INIT", None, "mm",
                 None, "translation", "1 0 0", None,
                 None, None, None, "14.5"],
            ],
        ]
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig describe -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig describe --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            for ni, nm in enumerate(name):
                cmd = list(cd)
                cmd.append(nm)
                vl, er = self.runtest(cmd)
                self.assertEqual('', er)
                avc3 = vl.strip()
                doc = self.parseRST(avc3)
                self.assertEqual(len(doc), 1)
                section = doc[0]
                title = "Component: '%s'" % nm
                self.checkRSTSection(section, title, header, result[ni])
        el.close()

    def test_describe_components_columns(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = [
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='data' type='NXdata'>"
            "<field name='slit1' type='NX_FLOAT' units='mm'>"
            "<datasource name='sl1right' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>"
            "<strategy mode='INIT'/>"
            "<doc>horizontal position of the right slit</doc>"
            "</field>"
            "</group>"
            "</group>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='instrument' type='NXinstrument'>"
            "<group name='slit2' type='NXslit'>"
            "<field name='y_gap' type='NX_FLOAT' units='mm'>"
            "<strategy mode='STEP' />"
            "<datasource name='ygap' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_CHAR' name='depends_on'>"
            "transformations/yoffset<strategy mode='INIT'/>"
            "</field>"
            "<group name='transformations' type='NXtransformations'>"
            "<field depends_on='rot' name='yoffset'  "
            "type='NX_FLOAT64' units='m' >"
            "<attribute type='NX_CHAR' name='transformation_type'>"
            "translation<strategy mode='INIT'/></attribute>"
            "<attribute type='NX_FLOAT64' name='vector'>0 1 0"
            "<dimensions rank='1'><dim value='3' index='1'/>"
            "</dimensions><strategy mode='INIT'/>"
            "</attribute>"
            "<attribute type='NX_FLOAT64' name='offset'>2.3 0.3 3.4"
            "<dimensions rank='1'><dim value='3' index='1'/>"
            "</dimensions><strategy mode='INIT'/>"
            "</attribute>"
            "<datasource name='y_offset' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' />"
            "<record name='Position'/>"
            "</datasource>"
            "<strategy mode='INIT'/>"
            "</field>"
            "<field type='NX_FLOAT' name='rot' units='deg' "
            "transformation_type='rotation' vector='0 1 0' >"
            "4.5<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</group>"
            "</group>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='instrument' type='NXinstrument'>"
            "<group name='pinhole' type='NXpinhole'>"
            "<field name='diameter' type='NX_FLOAT' units='mm'>"
            "<strategy mode='STEP' />"
            "<datasource name='phdiameter' type='CLIENT'>"
            "<record name='ph_diameter'/>"
            "</datasource>"
            "<doc>pinhole diameter</doc>"
            "</field>"
            "<field type='NX_CHAR' name='depends_on'>"
            "transformations/y<strategy mode='INIT'/>"
            "</field>"
            "<group name='transformations' type='NXtransformations'>"
            "<field type='NX_FLOAT' depends_on='x' name='y' units='mm' "
            "transformation_type='translation' vector='0 1 0' >"
            "<strategy mode='STEP' />"
            "<datasource name='phy' type='CLIENT'>"
            "<record name='ph_y'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_FLOAT' name='x' units='mm' "
            "transformation_type='translation' vector='1 0 0' >"
            "14.5<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</group>"
            "</group>"
            "</definition>"
        ]
        header = '<thead><row>' \
            '<entry><paragraph>full_nexus_path</paragraph></entry>' \
            '<entry><paragraph>nexus_type</paragraph></entry>' \
            '<entry><paragraph>strategy</paragraph></entry>' \
            '<entry><paragraph>source_name</paragraph></entry>' \
            '<entry><paragraph>value</paragraph></entry>' \
            '<entry><paragraph>doc</paragraph></entry>' \
            '</row></thead>'

        result = [
            [
                ["entry:NXentry/data:NXdata/slit1",
                 "NX_FLOAT", "INIT",
                 "sl1right", None,
                 "horizontal position of the right slit"],
            ],
            [
                ["entry:NXentry/instrument:NXinstrument/slit2:NXslit/y_gap",
                 "NX_FLOAT", "STEP", "ygap", None, None],
                ["entry:NXentry/instrument:NXinstrument/slit2:NXslit/"
                 "depends_on",
                 "NX_CHAR", "INIT", None,
                 "transformations/yoffset",
                 None],
                ["entry:NXentry/instrument:NXinstrument/slit2:NXslit"
                 "/transformations:NXtransformations/yoffset",
                 "NX_FLOAT64", "INIT", "y_offset", None, None],
                ["entry:NXentry/instrument:NXinstrument/slit2:NXslit"
                 "/transformations:NXtransformations/rot",
                 "NX_FLOAT", "INIT",
                 None, "4.5", None],
                ["entry:NXentry/instrument:NXinstrument/slit2:NXslit"
                 "/transformations:NXtransformations/"
                 "yoffset@transformation_type",
                 "NX_CHAR", "INIT",
                 None,  "translation", None],
                ["entry:NXentry/instrument:NXinstrument/slit2:NXslit/"
                 "transformations:NXtransformations/yoffset@vector",
                 "NX_FLOAT64", "INIT",
                 None, "0 1 0", None],
                ["entry:NXentry/instrument:NXinstrument/slit2:NXslit"
                 "/transformations:NXtransformations/yoffset@offset",
                 "NX_FLOAT64", "INIT",  None, "2.3 0.3 3.4", None],
            ],
            [
                ["entry:NXentry/instrument:NXinstrument/pinhole:NXpinhole/"
                 "diameter",
                 "NX_FLOAT", "STEP", "phdiameter", None, "pinhole diameter"],
                ["entry:NXentry/instrument:NXinstrument/pinhole:NXpinhole/"
                 "depends_on",
                 "NX_CHAR", "INIT",  None,
                 "transformations/y", None],
                ["entry:NXentry/instrument:NXinstrument/pinhole:NXpinhole/"
                 "transformations:NXtransformations/y",
                 "NX_FLOAT", "STEP", "phy", None, None],
                ["entry:NXentry/instrument:NXinstrument/pinhole:NXpinhole/"
                 "transformations:NXtransformations/x",
                 "NX_FLOAT", "INIT", None, "14.5", None],
            ],
        ]
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
        # print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig describe -s %s '
             '-c full_nexus_path,nexus_type,strategy,source_name,value,doc'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig describe --server %s'
             ' --columns full_nexus_path,nexus_type,strategy,source_name,'
             'value,doc'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            for ni, nm in enumerate(name):
                cmd = list(cd)
                cmd.append(nm)
                vl, er = self.runtest(cmd)
                self.assertEqual('', er)
                avc3 = vl.strip()
                # print(vl)
                doc = self.parseRST(avc3)
                self.assertEqual(len(doc), 1)
                section = doc[0]
                title = "Component: '%s'" % nm
                self.checkRSTSection(section, title, header, result[ni])
        el.close()

    def test_describe_components_filters(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = [
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='data' type='NXdata'>"
            "<field name='beamstop' type='NX_FLOAT' units='mm' />"
            "<field name='slit1' type='NX_FLOAT' units='mm'>"
            "<datasource name='sl1right' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>"
            "<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='instrument' type='NXinstrument'>"
            "<group name='slit2' type='NXslit'>"
            "<field name='y_gap' type='NX_FLOAT' units='mm'>"
            "<strategy mode='STEP' />"
            "<datasource name='ygap' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_CHAR' name='depends_on'>"
            "transformations/yoffset<strategy mode='INIT'/>"
            "</field>"
            "<group name='transformations' type='NXtransformations'>"
            "<field depends_on='rot' name='yoffset'  "
            "type='NX_FLOAT64' units='m' >"
            "<attribute type='NX_CHAR' name='transformation_type'>"
            "translation<strategy mode='INIT'/></attribute>"
            "<attribute type='NX_FLOAT64' name='vector'>0 1 0"
            "<dimensions rank='1'><dim value='3' index='1'/>"
            "</dimensions><strategy mode='INIT'/>"
            "</attribute>"
            "<attribute type='NX_FLOAT64' name='offset'>2.3 0.3 3.4"
            "<dimensions rank='1'><dim value='3' index='1'/>"
            "</dimensions><strategy mode='INIT'/>"
            "</attribute>"
            "<datasource name='y_offset' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' />"
            "<record name='Position'/>"
            "</datasource>"
            "<strategy mode='INIT'/>"
            "</field>"
            "<field type='NX_FLOAT' name='rot' units='deg' "
            "transformation_type='rotation' vector='0 1 0' >"
            "4.5<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</group>"
            "</group>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='instrument' type='NXinstrument'>"
            "<group name='pinhole' type='NXpinhole'>"
            "<field name='diameter' type='NX_FLOAT' units='mm'>"
            "<strategy mode='STEP' />"
            "<datasource name='phdiameter' type='CLIENT'>"
            "<record name='ph_diameter'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_CHAR' name='depends_on'>"
            "transformations/y<strategy mode='INIT'/>"
            "</field>"
            "<group name='transformations' type='NXtransformations'>"
            "<field type='NX_FLOAT' depends_on='x' name='y' units='mm' "
            "transformation_type='translation' vector='0 1 0' >"
            "<strategy mode='STEP' />"
            "<datasource name='phy' type='CLIENT'>"
            "<record name='ph_y'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_FLOAT' name='x' units='mm' "
            "transformation_type='translation' vector='1 0 0' >"
            "14.5<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</group>"
            "</group>"
            "</definition>"
        ]
        header = '<thead><row>' \
            '<entry><paragraph>nexus_path</paragraph></entry>' \
            '<entry><paragraph>nexus_type</paragraph></entry>' \
            '<entry><paragraph>strategy</paragraph></entry>' \
            '<entry><paragraph>shape</paragraph></entry>' \
            '<entry><paragraph>units</paragraph></entry>' \
            '<entry><paragraph>depends_on</paragraph></entry>' \
            '<entry><paragraph>trans_type</paragraph></entry>' \
            '<entry><paragraph>trans_vector</paragraph></entry>' \
            '<entry><paragraph>trans_offset</paragraph></entry>' \
            '<entry><paragraph>source_name</paragraph></entry>' \
            '<entry><paragraph>source_type</paragraph></entry>' \
            '<entry><paragraph>source</paragraph></entry>' \
            '<entry><paragraph>value</paragraph></entry>' \
            '</row></thead>'

        result = [
            [
                ["entry/data/slit1",
                 "NX_FLOAT", "INIT", None, "mm",
                 None, None, None, None,
                 "sl1right", "CLIENT", "motor_1", None],
            ],
            [
                ["entry/instrument/slit2/y_gap",
                 "NX_FLOAT", "STEP", None, "mm",
                 None, None, None, None,
                 "ygap", "CLIENT", "motor_2", None],
                ["entry/instrument/slit2/depends_on",
                 "NX_CHAR", "INIT", None, None,
                 "[transformations/yoffset]", None, None, None,
                 None, None, None, "transformations/yoffset"],
                ["entry/instrument/slit2/transformations/yoffset",
                 "NX_FLOAT64", "INIT", None, "m",
                 "rot", "translation", "0 1 0", "2.3 0.3 3.4",
                 "y_offset", "TANGO",
                 "haso.desy.de:10000/p09/motor/exp.01/Position", None],
                ["entry/instrument/slit2/transformations/rot",
                 "NX_FLOAT", "INIT", None, "deg",
                 None, "rotation", "0 1 0",  None,
                 None, None, None, "4.5"],
                ["entry/instrument/slit2/transformations/"
                 "yoffset@transformation_type",
                 "NX_CHAR", "INIT", None, None,
                 None, "translation", None, None,
                 None, None, None, "translation"],
                ["entry/instrument/slit2/transformations/yoffset@vector",
                 "NX_FLOAT64", "INIT", "[3]", None,
                 None, None, "0 1 0", None,
                 None, None, None, "0 1 0"],
                ["entry/instrument/slit2/transformations/yoffset@offset",
                 "NX_FLOAT64", "INIT", "[3]", None,
                 None, None, None, "2.3 0.3 3.4",
                 None, None, None, "2.3 0.3 3.4"],
            ],
            [
                # ["entry/instrument/pinhole/diameter",
                #  "NX_FLOAT", "STEP", None, "mm",
                #  None, None, None, None,
                #  "phdiameter", "CLIENT", "ph_diameter", None],
                # ["entry/instrument/pinhole/depends_on",
                #  "NX_CHAR", "INIT",  None, None,
                #  "[transformations/y]", None, None, None,
                #  None, None, None, "transformations/y"],
                # ["entry/instrument/pinhole/transformations/y",
                #  "NX_FLOAT", "STEP", None, "mm",
                #  "x", "translation", "0 1 0", None,
                #  "phy", "CLIENT", "ph_y", None],
                # ["entry/instrument/pinhole/transformations/x",
                #  "NX_FLOAT", "INIT", None, "mm",
                #  None, "translation", "1 0 0", None,
                #  None, None, None, "14.5"],
            ],
        ]
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        commands = [
            ('nxsconfig describe -s %s -f *slit*'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig describe --server %s --filters *slit*'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            for ni, nm in enumerate(name):
                cmd = list(cd)
                cmd.append(nm)
                vl, er = self.runtest(cmd)
                self.assertEqual('', er)
                avc3 = vl.strip()
                doc = self.parseRST(avc3)
                self.assertEqual(len(doc), 1)
                section = doc[0]
                title = "Component: '%s'" % nm
                self.checkRSTSection(section, title, header, result[ni])
        el.close()

    def test_describe_components_mandatory(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()

        oname = "mcs_test_component"
        self.assertTrue(isinstance(avc, list))
        xml = [
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='data' type='NXdata'>"
            "<field name='slit1' type='NX_FLOAT' units='mm'>"
            "<datasource name='sl1right' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>"
            "<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='instrument' type='NXinstrument'>"
            "<group name='slit2' type='NXslit'>"
            "<field name='y_gap' type='NX_FLOAT' units='mm'>"
            "<strategy mode='STEP' />"
            "<datasource name='ygap' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_CHAR' name='depends_on'>"
            "transformations/yoffset<strategy mode='INIT'/>"
            "</field>"
            "<group name='transformations' type='NXtransformations'>"
            "<field depends_on='rot' name='yoffset'  "
            "type='NX_FLOAT64' units='m' >"
            "<attribute type='NX_CHAR' name='transformation_type'>"
            "translation<strategy mode='INIT'/></attribute>"
            "<attribute type='NX_FLOAT64' name='vector'>0 1 0"
            "<dimensions rank='1'><dim value='3' index='1'/>"
            "</dimensions><strategy mode='INIT'/>"
            "</attribute>"
            "<attribute type='NX_FLOAT64' name='offset'>2.3 0.3 3.4"
            "<dimensions rank='1'><dim value='3' index='1'/>"
            "</dimensions><strategy mode='INIT'/>"
            "</attribute>"
            "<datasource name='y_offset' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' />"
            "<record name='Position'/>"
            "</datasource>"
            "<strategy mode='INIT'/>"
            "</field>"
            "<field type='NX_FLOAT' name='rot' units='deg' "
            "transformation_type='rotation' vector='0 1 0' >"
            "4.5<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</group>"
            "</group>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<group name='entry' type='NXentry'>"
            "<group name='instrument' type='NXinstrument'>"
            "<group name='pinhole' type='NXpinhole'>"
            "<field name='diameter' type='NX_FLOAT' units='mm'>"
            "<strategy mode='STEP' />"
            "<datasource name='phdiameter' type='CLIENT'>"
            "<record name='ph_diameter'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_CHAR' name='depends_on'>"
            "transformations/y<strategy mode='INIT'/>"
            "</field>"
            "<group name='transformations' type='NXtransformations'>"
            "<field type='NX_FLOAT' depends_on='x' name='y' units='mm' "
            "transformation_type='translation' vector='0 1 0' >"
            "<strategy mode='STEP' />"
            "<datasource name='phy' type='CLIENT'>"
            "<record name='ph_y'/>"
            "</datasource>"
            "</field>"
            "<field type='NX_FLOAT' name='x' units='mm' "
            "transformation_type='translation' vector='1 0 0' >"
            "14.5<strategy mode='INIT'/>"
            "</field>"
            "</group>"
            "</group>"
            "</group>"
            "</group>"
            "</definition>"
        ]
        header = '<thead><row>' \
            '<entry><paragraph>nexus_path</paragraph></entry>' \
            '<entry><paragraph>nexus_type</paragraph></entry>' \
            '<entry><paragraph>strategy</paragraph></entry>' \
            '<entry><paragraph>shape</paragraph></entry>' \
            '<entry><paragraph>units</paragraph></entry>' \
            '<entry><paragraph>depends_on</paragraph></entry>' \
            '<entry><paragraph>trans_type</paragraph></entry>' \
            '<entry><paragraph>trans_vector</paragraph></entry>' \
            '<entry><paragraph>trans_offset</paragraph></entry>' \
            '<entry><paragraph>source_name</paragraph></entry>' \
            '<entry><paragraph>source_type</paragraph></entry>' \
            '<entry><paragraph>source</paragraph></entry>' \
            '<entry><paragraph>value</paragraph></entry>' \
            '</row></thead>'

        result = [
            [
                ["entry/data/slit1",
                 "NX_FLOAT", "INIT", None, "mm",
                 None, None, None, None,
                 "sl1right", "CLIENT", "motor_1", None],
                ["entry/instrument/slit2/transformations/yoffset@offset",
                 "NX_FLOAT64", "INIT", "[3]", None,
                 None, None, None, "2.3 0.3 3.4",
                 None, None, None, "2.3 0.3 3.4"],
                ["entry/instrument/slit2/transformations/yoffset",
                 "NX_FLOAT64", "INIT", None, "m",
                 "rot", "translation", "0 1 0", "2.3 0.3 3.4",
                 "y_offset", "TANGO",
                 "haso.desy.de:10000/p09/motor/exp.01/Position", None],
                ["entry/instrument/slit2/y_gap",
                 "NX_FLOAT", "STEP", None, "mm",
                 None, None, None, None,
                 "ygap", "CLIENT", "motor_2", None],
                ["entry/instrument/slit2/depends_on",
                 "NX_CHAR", "INIT", None, None,
                 "[transformations/yoffset]", None, None, None,
                 None, None, None, "transformations/yoffset"],
                ["entry/instrument/slit2/transformations/rot",
                 "NX_FLOAT", "INIT", None, "deg",
                 None, "rotation", "0 1 0",  None,
                 None, None, None, "4.5"],
                ["entry/instrument/slit2/transformations/"
                 "yoffset@transformation_type",
                 "NX_CHAR", "INIT", None, None,
                 None, "translation", None, None,
                 None, None, None, "translation"],
                ["entry/instrument/slit2/transformations/yoffset@vector",
                 "NX_FLOAT64", "INIT", "[3]", None,
                 None, None, "0 1 0", None,
                 None, None, None, "0 1 0"],
            ],
            [
                ["entry/data/slit1",
                 "NX_FLOAT", "INIT", None, "mm",
                 None, None, None, None,
                 "sl1right", "CLIENT", "motor_1", None],
                ["entry/instrument/pinhole/diameter",
                 "NX_FLOAT", "STEP", None, "mm",
                 None, None, None, None,
                 "phdiameter", "CLIENT", "ph_diameter", None],
                ["entry/instrument/pinhole/depends_on",
                 "NX_CHAR", "INIT",  None, None,
                 "[transformations/y]", None, None, None,
                 None, None, None, "transformations/y"],
                ["entry/instrument/pinhole/transformations/y",
                 "NX_FLOAT", "STEP", None, "mm",
                 "x", "translation", "0 1 0", None,
                 "phy", "CLIENT", "ph_y", None],
                ["entry/instrument/pinhole/transformations/x",
                 "NX_FLOAT", "INIT", None, "mm",
                 None, "translation", "1 0 0", None,
                 None, None, None, "14.5"],
            ],
        ]
        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i
#        print avc

        for i in range(np):
            self.setXML(el, xml[i])
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])
        self.assertEqual(el.setMandatoryComponents([name[0]]), None)

        commands = [
            ('nxsconfig describe -m -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig describe -m --server %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig describe --mandatory -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig describe --mandatory --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            for ni, nm in enumerate(name[1:]):
                cmd = list(cd)
                cmd.append(nm)
                vl, er = self.runtest(cmd)
                self.assertEqual('', er)
                avc3 = vl.strip()
                doc = self.parseRST(avc3)
                self.assertEqual(len(doc), 1)
                section = doc[0]
                self.checkRSTTable(section, header, result[ni], sort=True)
        el.close()

    def test_describe_components_external(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        el = self.openConf()
        man = el.mandatoryComponents()
        el.unsetMandatoryComponents(man)
        self.__man += man
        avc = el.availableComponents()
        avds = el.availableDataSources()

        oname = "mcs_test_component"
        odsname = "mcs_test_datasource"
        self.assertTrue(isinstance(avc, list))
        xml = [
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition><field name='data' type='NX_FLOAT'>"
            "$datasources.%s"
            "<strategy mode='INIT'/>"
            "</field>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition>"
            "<field name='data'>"
            "<strategy mode='STEP'/>"
            "$datasources.%s"
            "</field>"
            "<field name='data2'>"
            "$datasources.%s"
            "<strategy mode='FINAL'/>"
            "</field>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition><field name='data'>"
            "$datasources.%s"
            "<dimensions rank='1'>"
            "<dim index='0'  value='20'/>"
            "</dimensions>"
            "<strategy mode='INIT'/>"
            "</field>"
            "</definition>",
            "<?xml version='1.0' encoding='utf-8'?>"
            "<definition><field name='data' type='NX_CHAR'>"
            "$datasources.%s"
            "<dimensions rank='2' />"
            "<strategy mode='FINAL'/>"
            "</field>"
            "</definition>"
        ]
        xds = [
            "<datasource name='%s' type='CLIENT'>"
            "<record name='motor_1'/>"
            "</datasource>",
            "<datasource name='%s' type='CLIENT'>"
            "<record name='motor_2'/>"
            "</datasource>",
            "<datasource name='%s' type='TANGO'>"
            "<device hostname='haso.desy.de' member='attribute' "
            "name='p09/motor/exp.01' port='10000' "
            "encoding='LIMA_VIDEO_IMAGE'/>"
            "<record name='Position'/>"
            "</datasource>",
            "<datasource name='%s' type='PYEVAL'>"
            "<result>ds.result = 25.6"
            "</result>"
            "</datasource>",
            "<datasource name='%s' type='DB'>"
            "<database dbname='mydb' dbtype='PGSQL'/>"
            "<query format='IMAGE'>SELECT * from weather limit 3"
            "</query>"
            "</datasource>",
        ]

        header = '<thead><row>' \
            '<entry><paragraph>nexus_path</paragraph></entry>' \
            '<entry><paragraph>nexus_type</paragraph></entry>' \
            '<entry><paragraph>strategy</paragraph></entry>' \
            '<entry><paragraph>shape</paragraph></entry>' \
            '<entry><paragraph>units</paragraph></entry>' \
            '<entry><paragraph>depends_on</paragraph></entry>' \
            '<entry><paragraph>trans_type</paragraph></entry>' \
            '<entry><paragraph>trans_vector</paragraph></entry>' \
            '<entry><paragraph>trans_offset</paragraph></entry>' \
            '<entry><paragraph>source_name</paragraph></entry>' \
            '<entry><paragraph>source_type</paragraph></entry>' \
            '<entry><paragraph>source</paragraph></entry>' \
            '<entry><paragraph>value</paragraph></entry>' \
            '</row></thead>'

        np = len(xml)
        name = []
        for i in range(np):

            name.append(oname + '_%s' % i)
            while name[i] in avc:
                name[i] = name[i] + '_%s' % i

        dsname = []
        for i in range(len(xds)):

            dsname.append(odsname + '_%s' % i)
            while dsname[i] in avds:
                dsname[i] = dsname[i] + '_%s' % i
        dss = {
            name[0]: [dsname[0]],
            name[1]: [dsname[1], dsname[2]],
            name[2]: [dsname[3]],
            name[3]: [dsname[4]],
        }

        result = [
            [
                ["data", "NX_FLOAT", "INIT",
                 None, None, None, None, None, None,
                 dsname[0], "CLIENT", "motor_1", None],
            ],
            [
                ["data", None, "STEP",
                 None, None, None, None, None, None,
                 dsname[1], "CLIENT", "motor_2", None],
                ["data2", None, "FINAL",
                 None, None, None, None, None, None,
                 dsname[2], "TANGO",
                 "haso.desy.de:10000/p09/motor/exp.01/Position", None],
            ],
            [
                ["data", None, "INIT",
                 "[20]", None, None, None, None, None,
                 dsname[3], "PYEVAL", "25.6", None],
            ],
            [
                ["data", "NX_CHAR", "FINAL",
                 "['*', '*']", None, None, None, None, None,
                 dsname[4], "DB", "SELECT * from weather limit 3", None],
            ],
        ]
        for i in range(np):
            self.setXML(el, xml[i] % tuple(dss[name[i]]))
            self.assertEqual(el.storeComponent(name[i]), None)
            self.__cmps.append(name[i])

        dsnp = len(xds)
        for i in range(dsnp):
            self.setXML(el, xds[i] % dsname[i])
            self.assertEqual(el.storeDataSource(dsname[i]), None)
            self.__ds.append(dsname[i])

        commands = [
            ('nxsconfig describe -s %s'
             % self._sv.new_device_info_writer.name).split(),
            ('nxsconfig describe --server %s'
             % self._sv.new_device_info_writer.name).split(),
        ]
#        commands = [['nxsconfig', 'list']]
        for cd in commands:
            for ni, nm in enumerate(name):
                cmd = list(cd)
                cmd.append(nm)
                vl, er = self.runtest(cmd)
                self.assertEqual('', er)
                avc3 = vl.strip()
                doc = self.parseRST(avc3)
                self.assertEqual(len(doc), 1)
                section = doc[0]
                title = "Component: '%s'" % nm
                self.checkRSTSection(section, title, header, result[ni])
        el.close()


if __name__ == '__main__':
    unittest.main()
