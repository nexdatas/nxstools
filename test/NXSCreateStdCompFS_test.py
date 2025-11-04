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
# import time
# import threading
try:
    import tango
except Exception:
    import PyTango as tango
# import json
from nxstools import nxscreate
from nxstools.xmltemplates import standardComponentVariables

try:
    from .checks import checkxmls
except Exception:
    from checks import checkxmls

try:
    import nxsextrasp00
except ImportError:
    from . import nxsextrasp00


try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

try:
    import ServerSetUp
except ImportError:
    from . import ServerSetUp


if sys.version_info > (3,):
    unicode = str
    long = int

if "nxsextrasp00" not in sys.modules:
    sys.modules["nxsextrasp00"] = nxsextrasp00

# if 64-bit machione
IS64BIT = (struct.calcsize("P") == 8)


# test fixture
class NXSCreateStdCompFSTest(unittest.TestCase):

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
        self._sv = ServerSetUp.ServerSetUp()
        self.maxDiff = None
        self.directory = "."
        self.flags = " -r testp09/testmcs/testr228 "
        self.device = 'testp09/testmcs/testr228'

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
        print("SEED = %s" % self.seed)
        self._sv.setUp()

    # test closer
    # \brief Common tear down
    def tearDown(self):
        print("tearing down ...")
        self._sv.tearDown()

    def dsexists(self, name):
        return os.path.isfile("%s/%s.ds.xml" % (self.directory, name))

    def cpexists(self, name):
        return os.path.isfile("%s/%s.xml" % (self.directory, name))

    def checkmandatory(self, name, mandat):
        pass

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
        # try:
        #    err = False
        nxscreate.main()
        # except Exception as e:
        #     print(str(e))
        #     err = True
        sys.argv = old_argv

        sys.stdout = old_stdout
        sys.stderr = old_stderr
        vl = mystdout.getvalue()
        er = mystderr.getvalue()
        # print(vl)
        # print(er)
        # if err:
        #     raise
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
            etxt = None
        except exception as e:
            error = True
            etxt = str(e)
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
        except exception:
            error = True
        self.assertEqual(error, True)

    def checkxmls(self, args, mandatory=False):
        """ check xmls of components and datasources
        """

        dstotest = []
        cptotest = []
        try:
            for arg in args:
                skip = False
                for cp in arg[1][0]:
                    if self.cpexists(cp):
                        skip = True
                for ds in arg[1][1]:
                    if self.dsexists(ds):
                        skip = True
                if not skip:
                    for ds in arg[1][1]:
                        dstotest.append(ds)
                    for cp in arg[1][0]:
                        cptotest.append(cp)
                    # print(arg[0])
                    vl, er = self.runtest(arg[0])
                    # print(vl)
                    if er:
                        self.assertEqual(
                            "Info: NeXus hasn't been setup yet. \n\n", er)
                    else:
                        self.assertEqual('', er)
                    self.assertTrue(vl)

                    for i, ds in enumerate(arg[1][1]):
                        xml = self.getds(ds)
                        checkxmls(
                            self,
                            arg[2][1][i], xml)
                    for i, cp in enumerate(arg[1][0]):
                        xml = self.getcp(cp)
                        checkxmls(
                            self,
                            arg[2][0][i], xml)
                        self.checkmandatory(cp, mandatory)

                    for ds in arg[1][1]:
                        self.deleteds(ds)
                    for cp in arg[1][0]:
                        self.deletecp(cp)

        finally:
            pass
            for cp in cptotest:
                if self.cpexists(cp):
                    self.deletecp(cp)
            for ds in dstotest:
                if self.dsexists(ds):
                    self.deleteds(ds)

    def test_stdcomp_typelist(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate stdcomp %s' % self.flags).split(),
            ],
        ]

        try:
            for arg in args:
                vl, er = self.runtest(arg[0])

                if er:
                    self.assertEqual(
                        "Info: NeXus hasn't been setup yet. \n\n", er)
                else:
                    self.assertEqual('', er)
                self.assertTrue(vl)
                lines = vl.split("\n")
                self.assertEqual(lines[-3], "POSSIBLE COMPONENT TYPES: ")
                self.assertEqual(
                    lines[-2].split(),
                    ["absorber", "beamstop", "beamtimefname",
                     "beamtimeid", "chcut", "coboldhisto",
                     "collect2", "collect3",
                     "collect4", "collect5", "collect6",
                     "common2", "common3",
                     "dataaxessignal",
                     "datasignal", "dcm", "default", "defaultcollection",
                     "defaultinstrument",
                     "defaultsample", "defaultsampleidentifier", "description",
                     "descriptiontext", "detectorlive",
                     "empty", "groupsecop", "keithley", "maia",
                     "maiadimension", "maiaflux", "msnsar", "mssar",
                     "parametercopymap", "pinhole",
                     "pointdet", "qbpm", "sampledescription",
                     "sampledescriptiontext", "samplehkl", "secop",
                     "secoplinks",
                     "singlesecop", "slit", "source", "starttime",
                     "tango", "undulator"])
                self.assertEqual(lines[-1], "")
        finally:
            pass

    def test_stdcomp_type_parameters(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        types = ["absorber", "beamstop", "beamtimeid", "chcut",
                 "coboldhisto", "collect2", "collect3",
                 "collect4", "collect5", "collect6",
                 "common2", "common3",
                 "dataaxessignal",
                 "datasignal", "dcm", "default", "defaultcollection",
                 "defaultinstrument",
                 "defaultsample", "defaultsampleidentifier", "description",
                 "descriptiontext", "detectorlive",
                 "empty", "groupsecop", "keithley", "maia",
                 "maiadimension", "maiaflux",
                 "parametercopymap", "pinhole",
                 "pointdet", "qbpm", "sampledescription",
                 "sampledescriptiontext", "samplehkl",
                 "secop", "secoplinks", "singlesecop", "slit",
                 "source", "starttime", "tango", "undulator"]
        args = [
                ('nxscreate stdcomp %s -t ' % self.flags).split(),
                ('nxscreate stdcomp %s --type ' % self.flags).split(),
        ]

        try:
            for tp in types:
                for arg in args:
                    cmd = list(arg)
                    cmd.append(tp)
                    vl, er = self.runtest(cmd)

                    if er:
                        self.assertEqual(
                            "Info: NeXus hasn't been setup yet. \n\n", er)
                    else:
                        self.assertEqual('', er)
                    self.assertTrue(vl)

                    lines = vl.split("\n")
                    self.assertEqual(lines[0], "")
                    self.assertEqual(lines[-1], "")
                    self.assertEqual(lines[1], "COMPONENT VARIABLES:")
                    var = lines[2:-1]

                    self.assertEqual(
                        len(var),
                        len([st for st in standardComponentVariables[tp].keys()
                             if not st.startswith("__")]))
                    for vr in var:
                        vname = vr.split()[0]
                        self.assertTrue(
                             vname in standardComponentVariables[tp].keys())
                        self.assertTrue(
                            standardComponentVariables[tp][vname]['doc'] in vr)
                        default = \
                            standardComponentVariables[tp][vname]['default']
                        if default is None:
                            default = 'None'
                        self.assertTrue(
                            vr.endswith(" [default: '%s']" % default))
        finally:
            pass

    def test_stdcomp_missing_parameters(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        types = [
            # "absorber",           # +-
            # "beamstop",           # +
            # "beamtimeid",         #
            # "chcut",              #
            "collect2",             # +
            "collect3",             # +
            "common2",              #
            "common3",              #
            # "datasignal",         #
            # "dcm",                #
            # "default",            # +
            # "defaultinstrument",  # .
            # "defaultsample",
            # "defaultsampleidentifier",      # .
            # "empty",              #
            # "keithley",           #
            # "maia",               #
            # "maiadimension",      #
            # "maiaflux",           #
            # "pinhole",            #
            # "pointdet",           #
            # "qbpm",               #
            # "samplehkl",          #
            # "slit",               #
            # "source",             # +
            # "undulator"           #
        ]

        args = [
            ('nxscreate stdcomp %s -c cptest -t ' % self.flags).split(),
            ('nxscreate stdcomp %s --component cptest --type '
             % self.flags).split(),
        ]

        totest = []
        try:
            for tp in types:
                for arg in args:
                    cp = "cptest"
                    skip = False
                    if self.cpexists(cp):
                        skip = True
                    if not skip:
                        totest.append(cp)

                        cmd = list(arg)
                        cmd.append(tp)
                        # print(tp)
                        vl, er, txt = self.runtestexcept(cmd, SystemExit)
                        if er:
                            self.assertEqual(
                                "Info: NeXus hasn't been setup yet. \n\n", er)
                        else:
                            self.assertEqual('', er)
                        self.assertTrue(vl)
                        # print(txt)
                        lines = vl.split("\n")
                        # self.assertEqual(lines[0], "OUTPUT DIR: .")
                        self.assertEqual(lines[-1], "")
                        self.assertTrue("MISSING" in vl)
                        self.assertTrue("WARNING: " in vl)
                        self.assertTrue(" cannot be created without " in vl)
                        if self.cpexists(cp):
                            self.deletecp(cp)
        finally:
            for cp in totest:
                if self.cpexists(cp):
                    self.deletecp(cp)

    def test_stdcomp_missing_mand_parameters(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        types = [
            "absorber",             # +-
            # "beamstop",           # +
            # "beamtimeid",         #
            # "chcut",              #
            # "collect2",           # +
            # "collect3",           # +
            # "common2",            #
            # "common3",            #
            # "datasignal",         #
            # "dcm",                #
            # "default",            # +
            # "defaultinstrument",  # .
            # "defaultsample",
            # "defaultsampleidentifier",      # .
            # "empty",              #
            # "keithley",           #
            # "maia",               #
            # "maiadimension",      #
            # "maiaflux",           #
            # "pinhole",            #
            # "pointdet",           #
            "qbpm",                 #
            # "samplehkl",          #
            # "slit",               #
            # "source",             # +
            # "undulator"           #
        ]

        args = [
            ('nxscreate stdcomp %s -c cptest -t ' % self.flags).split(),
            ('nxscreate stdcomp %s --component cptest --type '
             % self.flags).split(),
        ]

        totest = []
        try:
            for tp in types:
                for arg in args:
                    cp = "cptest"
                    skip = False
                    if self.cpexists(cp):
                        skip = True
                    if not skip:
                        totest.append(cp)

                        cmd = list(arg)
                        cmd.append(tp)
                        # print(tp)
                        vl, er = self.runtest(cmd)
                        if er:
                            self.assertEqual(
                                "Info: NeXus hasn't been setup yet. \n\n", er)
                        else:
                            self.assertEqual('', er)
                        self.assertTrue(vl)
                        # print(txt)
                        lines = vl.split("\n")
                        # self.assertEqual(lines[0], "OUTPUT DIR: .")
                        self.assertEqual(lines[-1], "")
                        self.assertTrue("MISSING" in vl)
                        self.assertTrue("WARNING: " in vl)
                        self.assertTrue(" cannot be created without " in vl)
                        if self.cpexists(cp):
                            self.deletecp(cp)
        finally:
            for cp in totest:
                if self.cpexists(cp):
                    self.deletecp(cp)

    def test_stdcomp_absorber(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate stdcomp -t absorber -c absorber1 '
                 ' position mot01 '
                 ' %s' % self.flags).split(),
                [
                    ['absorber1'],
                    ['absorber1_foil', 'absorber1_thickness']
                ],
                [
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <group name="$var.entryname#\'scan\'$var.serialno"'
                     ' type="NXentry">\n'
                     '    <group name="instrument" type="NXinstrument">\n'
                     '      <group name="absorber1" type="NXattenuator">\n'
                     '        <group name="collection" type="NXcollection">\n'
                     '          <field name="slidersin_position" '
                     'type="NX_FLOAT64" units="">\n'
                     '          <strategy mode="INIT" />'
                     '$datasources.mot01</field>\n'
                     '\t</group>\n'
                     '        </group>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>'],
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="absorber1_foil" type="PYEVAL">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import absorber\n'
                     'ds.result = absorber.foil('
                     'ds.mot01, \'["Ag", "Ag", "Ag", "Ag", "", "Al", "Al", '
                     '"Al", "Al"]\')'
                     '\n    </result>\n'
                     ' $datasources.mot01</datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="absorber1_thickness"'
                     ' type="PYEVAL">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import absorber\n'
                     'ds.result = absorber.thickness('
                     'ds.mot01, '
                     '\'[0.5, 0.05, 0.025, 0.0125, 0, 0.1, 0.3, 0.5, 1.0]\')\n'
                     '    </result>\n'
                     ' $datasources.mot01</datasource>\n'
                     '</definition>'],
                ],
            ],
            [
                ('nxscreate stdcomp --type absorber --component absorber1 '
                 ' position mot01 '
                 ' y y '
                 ' attenfactor afactor '
                 ' foil myfoil '
                 ' thickness tkns '
                 ' foillist ["Ag","","Al"] '
                 ' thicknesslist  [0.5,0,1.0] '
                 ' distance 0.5 '
                 ' distanceoffset [0,1,2] '
                 ' dependstop distance '
                 ' transformations transformations '
                 ' %s' % self.flags).split(),
                [
                    ['absorber1'],
                    ['absorber1_foil', 'absorber1_thickness']
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <group type="NXentry" '
                     'name="$var.entryname#\'scan\'$var.serialno">\n'
                     '    <group type="NXinstrument" name="instrument">\n'
                     '      <group type="NXattenuator" name="absorber1">\n'
                     '        <field type="NX_CHAR" name="type">\n'
                     '          <strategy mode="INIT"/>$datasources.myfoil'
                     '<dimensions rank="1"/>\n'
                     '\t</field>\n'
                     '        <field type="NX_CHAR" name="thickness">\n'
                     '          <strategy mode="INIT"/>$datasources.tkns'
                     '<dimensions rank="1"/>\n'
                     '\t</field>\n'
                     '        <field units="" type="NX_FLOAT" '
                     'name="attenuator_transmission">\n'
                     '          <strategy mode="INIT"/>$datasources.afactor'
                     '</field>\n'
                     '\t<group type="NXcollection" name="collection">\n'
                     '          <field units="" type="NX_FLOAT64" '
                     'name="slidersin_position">\n'
                     '          <strategy mode="INIT"/>$datasources.mot01'
                     '</field>\n'
                     '\t</group>\n'
                     '        <group type="NXtransformations" '
                     'name="transformations">\n'
                     '          <field depends_on="distance" units="mm" '
                     'type="NX_FLOAT64" name="y">\n'
                     '            <strategy mode="INIT"/>$datasources.y\n'
                     '\t    '
                     '<attribute type="NX_CHAR" name="transformation_type">'
                     'translation<strategy mode="INIT"/>\n'
                     '            </attribute>\n'
                     '            <attribute type="NX_FLOAT64" name="vector">'
                     '0 1 0\n'
                     '\t    <strategy mode="INIT"/>\n'
                     '            <dimensions rank="1">\n'
                     '\t      <dim value="3" index="1"/>\n'
                     '            </dimensions>\n'
                     '            </attribute>\n'
                     '          </field>\n'
                     '          <field offset_units="m" units="m" '
                     'type="NX_FLOAT64" name="distance" '
                     'transformation_type="translation">0.5'
                     '<strategy mode="INIT"/>\n'
                     '            <attribute type="NX_FLOAT64" name="vector">'
                     '0 0 1<dimensions rank="1">\n'
                     '                <dim value="3" index="1"/>\n'
                     '              </dimensions>\n'
                     '              <strategy mode="INIT"/>\n'
                     '            </attribute>\n'
                     '            <attribute type="NX_FLOAT64" name="offset">'
                     '[0,1,2]<dimensions rank="1">\n'
                     '                <dim value="3" index="1"/>\n'
                     '              </dimensions>\n'
                     '              <strategy mode="INIT"/>\n'
                     '            </attribute>\n'
                     '          </field>\n'
                     '        </group>\n'
                     '        <field type="NX_CHAR" name="depends_on">'
                     'transformations/distance<strategy mode="INIT"/>\n'
                     '        </field>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>\n'],
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" name="absorber1_foil">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import absorber\n'
                     'ds.result = absorber.foil('
                     'ds.mot01, \'["Ag","","Al"]\')\n'
                     '    </result>\n'
                     ' $datasources.mot01</datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL"'
                     ' name="absorber1_thickness">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import absorber\n'
                     'ds.result = absorber.thickness('
                     'ds.mot01, \'[0.5,0,1.0]\')\n'
                     '    </result>\n'
                     ' $datasources.mot01</datasource>\n'
                     '</definition>\n'],
                ],
            ],
        ]

        self.checkxmls(args)

    def test_stdcomp_beamstop(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate stdcomp -t beamstop -c testbeamstop1 %s' %
                 self.flags).split(),
                [
                    ['testbeamstop1'],
                    []
                ],
                [
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <group name="$var.entryname#\'scan\'$var.serialno" '
                     'type="NXentry">\n'
                     '    <group name="instrument" type="NXinstrument">\n'
                     '      <group name="testbeamstop1" type="NXbeam_stop">\n'
                     '\t<field name="description" type="NX_CHAR">\n'
                     '            <strategy mode="INIT" />circular</field>\n'
                     '        <field name="depends_on" type="NX_CHAR">'
                     'transformations/y<strategy mode="INIT" />\n'
                     '        </field>\n'
                     '        <group name="transformations" '
                     'type="NXtransformations">\n'
                     '          </group>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>'],
                    [],
                ],
            ],
            [
                ('nxscreate stdcomp --type beamstop '
                 ' --entryname myentry '
                 ' --insname myinstrument '
                 '--component testbeamstop2 %s' %
                 self.flags).split(),
                [
                    ['testbeamstop2'],
                    []
                ],
                [
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <group name="$var.entryname#\'myentry\'$var.serialno" '
                     'type="NXentry">\n'
                     '    <group name="myinstrument" type="NXinstrument">\n'
                     '      <group name="testbeamstop2" type="NXbeam_stop">\n'
                     '\t<field name="description" type="NX_CHAR">\n'
                     '            <strategy mode="INIT" />circular</field>\n'
                     '        <field name="depends_on" type="NX_CHAR">'
                     'transformations/y<strategy mode="INIT" />\n'
                     '        </field>\n'
                     '        <group name="transformations" '
                     'type="NXtransformations">\n'
                     '          </group>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>'],
                    [],
                ],
            ],
            [
                ('nxscreate stdcomp -t beamstop -c testbeamstop3 '
                 ' -y myentry '
                 ' -i myinstrument '
                 ' description linear '
                 ' x mot01 '
                 ' xsign -'
                 ' y mot02 '
                 ' z mot03 '
                 ' %s' % self.flags).split(),
                [
                    ['testbeamstop3'],
                    []
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <group type="NXentry" '
                     'name="$var.entryname#\'myentry\'$var.serialno">\n'
                     '    <group type="NXinstrument" name="myinstrument">\n'
                     '      <group type="NXbeam_stop" name="testbeamstop3">\n'
                     '\t<field type="NX_CHAR" name="description">\n'
                     '            <strategy mode="INIT"/>linear</field>\n'
                     '        <field type="NX_CHAR" name="depends_on">'
                     'transformations/y<strategy mode="INIT"/>\n'
                     '        </field>\n'
                     '        <group type="NXtransformations" '
                     'name="transformations">\n'
                     '          <field depends_on="x" units="mm" '
                     'type="NX_FLOAT64" name="y">\n'
                     '            <strategy mode="INIT"/>$datasources.mot02\n'
                     '\t    '
                     '<attribute type="NX_CHAR" name="transformation_type">'
                     'translation<strategy mode="INIT"/>\n'
                     '            </attribute>\n'
                     '            <attribute type="NX_FLOAT64" name="vector">'
                     '0 1 0\n'
                     '\t    <strategy mode="INIT"/>\n'
                     '            <dimensions rank="1">\n'
                     '\t      <dim value="3" index="1"/>\n'
                     '            </dimensions>\n'
                     '            </attribute>\n'
                     '          </field>\n'
                     '          <field depends_on="z" units="mm" '
                     'type="NX_FLOAT64" name="x">\n'
                     '            <strategy mode="INIT"/>$datasources.mot01\n'
                     '\t    '
                     '<attribute type="NX_CHAR" name="transformation_type">'
                     'translation<strategy mode="INIT"/>\n'
                     '            </attribute>\n'
                     '            <attribute type="NX_FLOAT64" name="vector">'
                     '-1 0 0\n\t    <strategy mode="INIT"/>\n'
                     '            <dimensions rank="1">\n'
                     '\t      <dim value="3" index="1"/>\n'
                     '            </dimensions>\n'
                     '            </attribute>\n'
                     '          </field>\n'
                     '          '
                     '<field units="mm" type="NX_FLOAT64" name="z">\n'
                     '            <strategy mode="INIT"/>$datasources.mot03\n'
                     '\t    '
                     '<attribute type="NX_CHAR" name="transformation_type">'
                     'translation<strategy mode="INIT"/>\n'
                     '            </attribute>\n'
                     '            <attribute type="NX_FLOAT64" name="vector">'
                     '0 0 1\n\t    <strategy mode="INIT"/>\n'
                     '            <dimensions rank="1">\n'
                     '\t      <dim value="3" index="1"/>\n'
                     '            </dimensions>\n'
                     '            </attribute>\n'
                     '          </field>\n'
                     '        </group>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>\n'],
                    [],
                ],
            ],
        ]

        self.checkxmls(args)

    def test_stdcomp_default_mandatory(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate stdcomp -t default -c default -m '
                 ' %s' % self.flags).split(),
                [
                    ['default', 'defaultinstrument', 'defaultsample'],
                    ['title', 'start_time', 'sample_name',
                     'nexdatas_version', 'nexdatas_configuration',
                     'end_time', 'chemical_formula', 'beamtime_id',
                     'beamtime_filename']
                ],
                [
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <group name="$var.entryname#\'scan\'$var.serialno"'
                     ' type="NXentry" />\n'
                     '  $components.defaultinstrument\n'
                     '  $components.defaultsample\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <group name="$var.entryname#\'scan\'$var.serialno"'
                     ' type="NXentry">\n'
                     '    <field name="experiment_identifier" '
                     'type="NX_CHAR">\n'
                     '      <doc>Beamtime ID. From this ID everything else '
                     'can be derived from the DESY databases including the '
                     'Proposal as well as the scientists performing '
                     'the experiment, the local contact, and so on.\n'
                     'The beamtime ID at DESY is an 8 digit number.R</doc>\n'
                     '      <strategy mode="INIT" />$datasources.beamtime_id\n'
                     '      <attribute type="NX_CHAR" '
                     'name="beamtime_filename">'
                     '        <strategy mode="INIT" />'
                     '$datasources.beamtime_filename</attribute>\n'
                     '</field>\n'
                     '    <field name="start_time" type="NX_DATE_TIME">\n'
                     '      <doc>time stamp when the experiment has started.'
                     '</doc>\n'
                     '      <strategy mode="INIT" />$datasources.start_time'
                     '</field>\n'
                     '    <field name="end_time" type="NX_DATE_TIME">\n'
                     '      <doc>'
                     'end time - timestamp when the experiment stopped.'
                     '</doc>\n'
                     '      <strategy mode="FINAL" />$datasources.end_time'
                     '</field>\n'
                     '    <group name="instrument" type="NXinstrument">\n'
                     '      <group name="source" type="NXsource">\n'
                     '        <doc>'
                     'generic description of the PETRA III storage ring'
                     '</doc>\n'
                     '        <field name="name" short_name="PETRAIII"'
                     ' type="NX_CHAR">\n'
                     '          <strategy mode="INIT" />PETRA III</field>\n'
                     '        <field name="type" type="NX_CHAR">'
                     'Synchrotron X-ray Source<strategy mode="INIT" />\n'
                     '        </field>\n'
                     '        <field name="probe" type="NX_CHAR">'
                     'x-ray<strategy mode="INIT" />\n'
                     '        </field>\n'
                     '      </group>\n'
                     '      <field name="name" '
                     'short_name="P09" type="NX_CHAR">'
                     'P09 Resonant Scattering and Diffraction beamline'
                     '<strategy mode="INIT" />\n'
                     '      </field>\n'
                     '    </group>\n'
                     '    <field name="program_name" '
                     'scan_command="$var.scan_title" scan_id="$var.scan_id" '
                     'npoints="$var.npoints" count_time="$var.count_time" '
                     'beamtime_id="$var.beamtime_id" '
                     'measurement_group="$var.measurement_group" '
                     'measurement_group_channels="$var.mgchannels" '
                     'nexus_components="$var.nexus_components" '
                     'nexus_step_datasources="$var.nexus_step_datasources" '
                     'nexus_init_datasources="$var.nexus_init_datasources" '
                     'type="NX_CHAR">NexDaTaS<attribute name="version" '
                     'type="NX_CHAR">\n'
                     '        <strategy mode="INIT" />'
                     '$datasources.nexdatas_version</attribute>\n'
                     '      <attribute name="configuration" type="NX_CHAR">\n'
                     '        <strategy mode="INIT" />'
                     '$datasources.nexdatas_configuration</attribute>\n'
                     '      <strategy mode="INIT"/>\n'
                     '    </field>\n'
                     '    <field name="title" type="NX_CHAR">\n'
                     '      <strategy mode="INIT" />$datasources.title'
                     '</field>\n'
                     '  </group>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <group name="$var.entryname#\'scan\'$var.serialno"'
                     ' type="NXentry">\n'
                     '    <group name="sample" type="NXsample">\n'
                     '      <field name="name" type="NX_CHAR">\n'
                     '\t<strategy mode="INIT" />$datasources.sample_name\n'
                     '      </field>\n'
                     '      <field name="chemical_formula" type="NX_CHAR">\n'
                     '        <strategy mode="INIT" />'
                     '$datasources.chemical_formula\n'
                     '      </field>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>'],
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="title" type="CLIENT">\n'
                     '    <record name="title" />\n'
                     '  </datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="start_time" type="CLIENT">\n'
                     '    <record name="start_time" />\n'
                     '    <doc>'
                     'The start time is provided by the control client.'
                     '</doc>\n'
                     '  </datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="sample_name" type="CLIENT">\n'
                     '    <record name="sample_name" />\n'
                     '    <doc>'
                     'Data source providing the name of the sample.</doc>\n'
                     '  </datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="nexdatas_version" type="PYEVAL">\n'
                     '    <result name="result">\n'
                     'from nxswriter import __version__\n'
                     'ds.result = __version__   # from nxswriter\n'
                     '    </result>\n'
                     '  </datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource '
                     'name="nexdatas_configuration" type="TANGO">\n'
                     '    <record name="Version" />\n'
                     '    <device hostname="%s" member="attribute" '
                     'name="%s" port="%s" />\n'
                     '  </datasource>\n'
                     '</definition>' %
                     (self.host, self.device, self.port),
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="end_time" type="CLIENT">\n'
                     '    <record name="end_time" />\n'
                     '    <doc>'
                     'The end time is provided by the client after '
                     'the experiment is finished.</doc>\n'
                     '  </datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="chemical_formula" type="CLIENT">\n'
                     '    <record name="chemical_formula" />\n'
                     '  </datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="beamtime_id" type="CLIENT">\n'
                     '    <record name="beamtime_id" />\n'
                     '  </datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" name="beamtime_filename">\n'
                     '    <result name="result">\n'
                     'ds.result = ""\n</result>\n'
                     '  </datasource>\n'
                     '</definition>']
                ],
            ],
            [
                ('nxscreate stdcomp --type default --component default'
                 ' --mandatory'
                 ' %s' % self.flags).split(),
                [
                    ['default', 'defaultinstrument', 'defaultsample'],
                    ['title', 'start_time', 'sample_name',
                     'nexdatas_version', 'nexdatas_configuration',
                     'end_time', 'chemical_formula', 'beamtime_id',
                     'beamtime_filename']
                ],
                [
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <group name="$var.entryname#\'scan\'$var.serialno"'
                     ' type="NXentry" />\n'
                     '  $components.defaultinstrument\n'
                     '  $components.defaultsample\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <group name="$var.entryname#\'scan\'$var.serialno"'
                     ' type="NXentry">\n'
                     '    <field name="experiment_identifier" '
                     'type="NX_CHAR">\n'
                     '      <doc>Beamtime ID. From this ID everything else '
                     'can be derived from the DESY databases including the '
                     'Proposal as well as the scientists performing '
                     'the experiment, the local contact, and so on.\n'
                     'The beamtime ID at DESY is an 8 digit number.R</doc>\n'
                     '      <strategy mode="INIT" />$datasources.beamtime_id\n'
                     '      <attribute type="NX_CHAR" '
                     'name="beamtime_filename">'
                     '        <strategy mode="INIT" />'
                     '$datasources.beamtime_filename</attribute>\n'
                     '</field>\n'
                     '    <field name="start_time" type="NX_DATE_TIME">\n'
                     '      <doc>time stamp when the experiment has started.'
                     '</doc>\n'
                     '      <strategy mode="INIT" />$datasources.start_time'
                     '</field>\n'
                     '    <field name="end_time" type="NX_DATE_TIME">\n'
                     '      <doc>'
                     'end time - timestamp when the experiment stopped.'
                     '</doc>\n'
                     '      <strategy mode="FINAL" />$datasources.end_time'
                     '</field>\n'
                     '    <group name="instrument" type="NXinstrument">\n'
                     '      <group name="source" type="NXsource">\n'
                     '        <doc>'
                     'generic description of the PETRA III storage ring'
                     '</doc>\n'
                     '        <field name="name" short_name="PETRAIII"'
                     ' type="NX_CHAR">\n'
                     '          <strategy mode="INIT" />PETRA III</field>\n'
                     '        <field name="type" type="NX_CHAR">'
                     'Synchrotron X-ray Source<strategy mode="INIT" />\n'
                     '        </field>\n'
                     '        <field name="probe" type="NX_CHAR">'
                     'x-ray<strategy mode="INIT" />\n'
                     '        </field>\n'
                     '      </group>\n'
                     '      <field name="name" '
                     'short_name="P09" type="NX_CHAR">'
                     'P09 Resonant Scattering and Diffraction beamline'
                     '<strategy mode="INIT" />\n'
                     '      </field>\n'
                     '    </group>\n'
                     '    <field name="program_name" '
                     'scan_command="$var.scan_title" scan_id="$var.scan_id" '
                     'npoints="$var.npoints" count_time="$var.count_time" '
                     'beamtime_id="$var.beamtime_id" '
                     'measurement_group="$var.measurement_group" '
                     'measurement_group_channels="$var.mgchannels" '
                     'nexus_components="$var.nexus_components" '
                     'nexus_step_datasources="$var.nexus_step_datasources" '
                     'nexus_init_datasources="$var.nexus_init_datasources" '
                     'type="NX_CHAR">NexDaTaS<attribute name="version" '
                     'type="NX_CHAR">\n'
                     '        <strategy mode="INIT" />'
                     '$datasources.nexdatas_version</attribute>\n'
                     '      <attribute name="configuration" type="NX_CHAR">\n'
                     '        <strategy mode="INIT" />'
                     '$datasources.nexdatas_configuration</attribute>\n'
                     '      <strategy mode="INIT"/>\n'
                     '    </field>\n'
                     '    <field name="title" type="NX_CHAR">\n'
                     '      <strategy mode="INIT" />$datasources.title'
                     '</field>\n'
                     '  </group>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <group name="$var.entryname#\'scan\'$var.serialno"'
                     ' type="NXentry">\n'
                     '    <group name="sample" type="NXsample">\n'
                     '      <field name="name" type="NX_CHAR">\n'
                     '\t<strategy mode="INIT" />$datasources.sample_name\n'
                     '      </field>\n'
                     '      <field name="chemical_formula" type="NX_CHAR">\n'
                     '        <strategy mode="INIT" />'
                     '$datasources.chemical_formula\n'
                     '      </field>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>'],
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="title" type="CLIENT">\n'
                     '    <record name="title" />\n'
                     '  </datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="start_time" type="CLIENT">\n'
                     '    <record name="start_time" />\n'
                     '    <doc>'
                     'The start time is provided by the control client.'
                     '</doc>\n'
                     '  </datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="sample_name" type="CLIENT">\n'
                     '    <record name="sample_name" />\n'
                     '    <doc>'
                     'Data source providing the name of the sample.</doc>\n'
                     '  </datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="nexdatas_version" type="PYEVAL">\n'
                     '    <result name="result">\n'
                     'from nxswriter import __version__\n'
                     'ds.result = __version__   # from nxswriter\n'
                     '    </result>\n'
                     '  </datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource '
                     'name="nexdatas_configuration" type="TANGO">\n'
                     '    <record name="Version" />\n'
                     '    <device hostname="%s" member="attribute" '
                     'name="%s" port="%s" />\n'
                     '  </datasource>\n'
                     '</definition>' %
                     (self.host, self.device, self.port),
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="end_time" type="CLIENT">\n'
                     '    <record name="end_time" />\n'
                     '    <doc>'
                     'The end time is provided by the client after '
                     'the experiment is finished.</doc>\n'
                     '  </datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="chemical_formula" type="CLIENT">\n'
                     '    <record name="chemical_formula" />\n'
                     '  </datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource name="beamtime_id" type="CLIENT">\n'
                     '    <record name="beamtime_id" />\n'
                     '  </datasource>\n'
                     '</definition>',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" name="beamtime_filename">\n'
                     '    <result name="result">\n'
                     'ds.result = ""\n</result>\n'
                     '  </datasource>\n'
                     '</definition>']
                ],
            ],
        ]

        self.checkxmls(args, True)

    def test_stdcomp_source_nolower(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate stdcomp -t source -c Source '
                 ' %s' % self.flags).split(),
                [
                    ['source'],
                    []
                ],
                [
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <group name="$var.entryname#\'scan\'$var.serialno" '
                     'type="NXentry">\n'
                     '    <group name="instrument" type="NXinstrument">\n'
                     '      <group name="source" type="NXsource">\n'
                     '        <doc>generic description of the storage ring'
                     '</doc>\n'
                     '        <field name="mode" type="NX_CHAR">'
                     'Multi Bunch<strategy mode="INIT" />\n'
                     '        </field>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>'],
                    [],
                ],
            ],
            [
                ('nxscreate stdcomp --type source --component Source '
                 ' --nolower '
                 ' beamcurrent bcurrent '
                 ' bunchmode Single_Bunch '
                 ' numberofbunches nob '
                 ' sourceenergy senergy '
                 ' %s' % self.flags).split(),
                [
                    ['Source'],
                    []
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <group type="NXentry" '
                     'name="$var.entryname#\'scan\'$var.serialno">\n'
                     '    <group type="NXinstrument" name="instrument">\n'
                     '      <group type="NXsource" name="source">\n'
                     '        <doc>generic description of the storage ring'
                     '</doc>\n'
                     '        <field units="mA" type="NX_FLOAT" '
                     'name="current">\n'
                     '          <doc>storage ring current</doc>\n'
                     '          <strategy mode="INIT" '
                     'canfail="true"/>$datasources.bcurrent\n'
                     '\t</field>\n'
                     '        <field units="GeV" type="NX_FLOAT" '
                     'name="energy">\n'
                     '\t  <doc>beam energy</doc>\n'
                     '          <strategy mode="INIT" canfail="true"/>'
                     '$datasources.senergy\n'
                     '\t</field>\n'
                     '\t<field type="NX_INT64" name="number_of_bunches">\n'
                     '          <strategy mode="INIT" canfail="true"/>'
                     '$datasources.nob\n'
                     '\t</field>\n'
                     '        <field type="NX_CHAR" name="mode">Single_Bunch'
                     '<strategy mode="INIT"/>\n'
                     '        </field>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>\n'
                     ''],
                    [],
                ],
            ],
            [
                ('nxscreate stdcomp -t source -c Source -n '
                 ' beamcurrent bcurrent '
                 ' bunchmode Single_Bunch '
                 ' numberofbunches nob '
                 ' sourceenergy senergy '
                 ' %s' % self.flags).split(),
                [
                    ['Source'],
                    []
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <group type="NXentry" '
                     'name="$var.entryname#\'scan\'$var.serialno">\n'
                     '    <group type="NXinstrument" name="instrument">\n'
                     '      <group type="NXsource" name="source">\n'
                     '        <doc>generic description of the storage ring'
                     '</doc>\n'
                     '        <field units="mA" type="NX_FLOAT" '
                     'name="current">\n'
                     '          <doc>storage ring current</doc>\n'
                     '          <strategy mode="INIT" '
                     'canfail="true"/>$datasources.bcurrent\n'
                     '\t</field>\n'
                     '        <field units="GeV" type="NX_FLOAT" '
                     'name="energy">\n'
                     '\t  <doc>beam energy</doc>\n'
                     '          <strategy mode="INIT" canfail="true"/>'
                     '$datasources.senergy\n'
                     '\t</field>\n'
                     '\t<field type="NX_INT64" name="number_of_bunches">\n'
                     '          <strategy mode="INIT" canfail="true"/>'
                     '$datasources.nob\n'
                     '\t</field>\n'
                     '        <field type="NX_CHAR" name="mode">Single_Bunch'
                     '<strategy mode="INIT"/>\n'
                     '        </field>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>\n'
                     ''],
                    [],
                ],
            ],
        ]

        self.checkxmls(args)

    def test_stdcomp_collect2_overwrite_false(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate stdcomp -t collect2 -c myslits '
                 ' first slit1 '
                 ' second slit2 '
                 ' %s' % self.flags).split(),
                [
                    ['myslits'],
                    []
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  $components.slit1\n'
                     '  $components.slit2\n'
                     '</definition>\n'],
                    [''],
                ],
                ('nxscreate stdcomp -t collect2 -c myslits '
                 ' first mslit1 '
                 ' second mslit2 '
                 ' %s' % self.flags).split(),
                ('nxscreate stdcomp --type collect2 --component myslits '
                 ' first slit1 '
                 ' second slit2 '
                 ' %s' % self.flags).split(),
                [
                    ['myslits'],
                    []
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  $components.slit1\n'
                     '  $components.slit2\n'
                     '</definition>\n'],
                    [''],
                ],
                ('nxscreate stdcomp -t collect2 -c myslits '
                 ' first mslit1 '
                 ' second mslit2 '
                 ' %s' % self.flags).split(),
            ],
        ]

        dstotest = []
        cptotest = []
        try:
            for arg in args:
                skip = False
                for cp in arg[1][0]:
                    if self.cpexists(cp):
                        skip = True
                for ds in arg[1][1]:
                    if self.dsexists(ds):
                        skip = True
                if not skip:
                    for ds in arg[1][1]:
                        dstotest.append(ds)
                    for cp in arg[1][0]:
                        cptotest.append(cp)

                    vl, er = self.runtest(arg[0])
                    # print(vl)
                    if er:
                        self.assertEqual(
                            "Info: NeXus hasn't been setup yet. \n\n", er)
                    else:
                        self.assertEqual('', er)
                    self.assertTrue(vl)

                    for i, ds in enumerate(arg[1][1]):
                        xml = self.getds(ds)
                        self.assertEqual(arg[2][1][i], xml)
                    for i, cp in enumerate(arg[1][0]):
                        xml = self.getcp(cp)
                        self.assertEqual(arg[2][0][i], xml)

                    vl, er, txt = self.runtestexcept(arg[3], SystemExit)

                    for i, ds in enumerate(arg[1][1]):
                        xml = self.getds(ds)
                        self.assertEqual(arg[2][1][i], xml)
                    for i, cp in enumerate(arg[1][0]):
                        xml = self.getcp(cp)
                        self.assertEqual(arg[2][0][i], xml)

                    for ds in arg[1][1]:
                        self.deleteds(ds)
                    for cp in arg[1][0]:
                        self.deletecp(cp)

        finally:
            pass
            for cp in cptotest:
                if self.cpexists(cp):
                    self.deletecp(cp)
            for ds in dstotest:
                if self.dsexists(ds):
                    self.deleteds(ds)

    def test_stdcomp_collect3_overwrite_true(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate stdcomp -t collect3 -c myslits '
                 ' first mslit1 '
                 ' second mslit2 '
                 ' third mslit3 '
                 ' %s' % self.flags).split(),
                [
                    ['myslits'],
                    []
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  $components.slit1\n'
                     '  $components.slit2\n'
                     '  $components.slit3\n'
                     '</definition>\n'],
                    [''],
                ],
                ('nxscreate stdcomp -t collect3 -c myslits -o '
                 ' first slit1 '
                 ' second slit2 '
                 ' third slit3 '
                 ' %s' % self.flags).split(),
            ],
            [
                ('nxscreate stdcomp --type collect3 --component myslits '
                 ' first mslit1 '
                 ' second mslit2 '
                 ' third mslit3 '
                 ' %s' % self.flags).split(),
                [
                    ['myslits'],
                    []
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  $components.slit1\n'
                     '  $components.slit2\n'
                     '  $components.slit3\n'
                     '</definition>\n'],
                    [''],
                ],
                ('nxscreate stdcomp --type collect3 --component myslits '
                 ' --overwrite '
                 ' first slit1 '
                 ' second slit2 '
                 ' third slit3 '
                 ' %s' % self.flags).split(),
            ],
        ]

        dstotest = []
        cptotest = []
        try:
            for arg in args:
                skip = False
                for cp in arg[1][0]:
                    if self.cpexists(cp):
                        skip = True
                for ds in arg[1][1]:
                    if self.dsexists(ds):
                        skip = True
                if not skip:
                    for ds in arg[1][1]:
                        dstotest.append(ds)
                    for cp in arg[1][0]:
                        cptotest.append(cp)

                    vl, er = self.runtest(arg[0])
                    # print(vl)
                    if er:
                        self.assertEqual(
                            "Info: NeXus hasn't been setup yet. \n\n", er)
                    else:
                        self.assertEqual('', er)
                    self.assertTrue(vl)

                    vl, er = self.runtest(arg[3])

                    for i, ds in enumerate(arg[1][1]):
                        xml = self.getds(ds)
                        self.assertEqual(arg[2][1][i], xml)
                    for i, cp in enumerate(arg[1][0]):
                        xml = self.getcp(cp)
                        self.assertEqual(arg[2][0][i], xml)

                    for ds in arg[1][1]:
                        self.deleteds(ds)
                    for cp in arg[1][0]:
                        self.deletecp(cp)

        finally:
            pass
            for cp in cptotest:
                if self.cpexists(cp):
                    self.deletecp(cp)
            for ds in dstotest:
                if self.dsexists(ds):
                    self.deleteds(ds)

    def test_stdcomp_missing_parameters_package(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        types = [
            "collect4",
            "common4",
        ]

        if __name__ in ['test.NXSCreateStdCompFSTest',
                        'test.NXSCreateStdCompFS_test']:
            args = [
                ('nxscreate stdcomp %s -p test.nxsextrasp00 -c cptest -t '
                 % self.flags).split(),
                ('nxscreate stdcomp %s --xml-package test.nxsextrasp00 '
                 ' --component cptest --type '
                 % self.flags).split(),
            ]
        else:
            args = [
                ('nxscreate stdcomp %s -p nxsextrasp00 -c cptest -t '
                 % self.flags).split(),
                ('nxscreate stdcomp %s --xml-package nxsextrasp00 '
                 ' --component cptest --type '
                 % self.flags).split(),
            ]

        totest = []
        try:
            for tp in types:
                for arg in args:
                    cp = "cptest"
                    skip = False
                    if self.cpexists(cp):
                        skip = True
                    if not skip:
                        totest.append(cp)

                        cmd = list(arg)
                        cmd.append(tp)
                        # print(tp)
                        vl, er, txt = self.runtestexcept(cmd, SystemExit)

                        lines = vl.split("\n")
                        # self.assertEqual(lines[0], "OUTPUT DIR: .")
                        self.assertEqual(lines[-1], "")
                        self.assertTrue("MISSING" in vl)
                        self.assertTrue("WARNING: " in vl)
                        self.assertTrue(" cannot be created without " in vl)
                        if self.cpexists(cp):
                            self.deletecp(cp)
        finally:
            for cp in totest:
                if self.cpexists(cp):
                    self.deletecp(cp)

    def test_stdcomp_collect4(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if __name__ == 'test.NXSCreateStdCompFSTest':
            pname = 'test.nxsextrasp00'
        else:
            pname = 'nxsextrasp00'
        args = [
            [
                ('nxscreate stdcomp -t collect4 -c myslits '
                 '-p %s '
                 ' first slit1 '
                 ' second slit2 '
                 ' third slit3 '
                 ' fourth slit4 '
                 ' %s' % (pname, self.flags)).split(),
                [
                    ['myslits'],
                    []
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  $components.slit1\n'
                     '  $components.slit2\n'
                     '  $components.slit3\n'
                     '  $components.slit4\n'
                     '</definition>\n'],
                    [''],
                ],
            ],
            [
                ('nxscreate stdcomp --type collect4 --component myslits '
                 ' --xml-package %s '
                 ' first slit1 '
                 ' second slit2 '
                 ' third slit3 '
                 ' fourth slit4 '
                 ' %s' % (pname, self.flags)).split(),
                [
                    ['myslits'],
                    []
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  $components.slit1\n'
                     '  $components.slit2\n'
                     '  $components.slit3\n'
                     '  $components.slit4\n'
                     '</definition>\n'],
                    [''],
                ],
            ],
        ]

        self.checkxmls(args)

    def test_stdcomp_common4(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if __name__ == 'test.NXSCreateStdCompFSTest':
            pname = 'test.nxsextrasp00'
        else:
            pname = 'nxsextrasp00'
        args = [
            [
                ('nxscreate stdcomp -t common4 -c myslit '
                 '-p %s '
                 ' dds slit1 '
                 ' ods1 slit2 '
                 ' ods2 slit3 '
                 ' ods3 slit4 '
                 ' %s' % (pname, self.flags)).split(),
                [
                    [],
                    ['myslit_common']
                ],
                [
                    [],
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" name="myslit_common">\n'
                     '    <result name="result">\n'
                     'ds.result = ds.slit1</result>\n'
                     ' $datasources.slit1\n'
                     ' $datasources.slit2\n'
                     ' $datasources.slit3\n'
                     ' $datasources.slit4</datasource>\n'
                     '</definition>\n'],
                ],
            ],
            [
                ('nxscreate stdcomp --type common4 --component myslit '
                 ' --xml-package %s '
                 ' dds slit1 '
                 ' ods1 slit2 '
                 ' ods2 slit3 '
                 ' ods3 slit4 '
                 ' %s' % (pname, self.flags)).split(),
                [
                    [],
                    ['myslit_common']
                ],
                [
                    [],
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" name="myslit_common">\n'
                     '    <result name="result">\n'
                     'ds.result = ds.slit1</result>\n'
                     ' $datasources.slit1\n'
                     ' $datasources.slit2\n'
                     ' $datasources.slit3\n'
                     ' $datasources.slit4</datasource>\n'
                     '</definition>\n'],
                ],
            ],
        ]

        self.checkxmls(args)

    def test_stdcomp_typelist_package(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        if __name__ == 'test.NXSCreateStdCompFSTest':
            pname = 'test.nxsextrasp00'
        else:
            pname = 'nxsextrasp00'
        args = [
            [
                ('nxscreate stdcomp '
                 ' -p %s '
                 ' %s' % (pname, self.flags)).split(),
                ('nxscreate stdcomp '
                 ' --xml-package %s '
                 ' %s' % (pname, self.flags)).split(),
            ],
        ]

        try:
            for arg in args:
                vl, er = self.runtest(arg[0])

                if er:
                    self.assertEqual(
                        "Info: NeXus hasn't been setup yet. \n\n", er)
                else:
                    self.assertEqual('', er)
                self.assertTrue(vl)
                lines = vl.split("\n")
                self.assertEqual(lines[-3], "POSSIBLE COMPONENT TYPES: ")
                self.assertEqual(
                    lines[-2].split(),
                    ["collect4", "common4"])
                self.assertEqual(
                    lines[-2].split(),
                    sorted(nxsextrasp00.standardComponentVariables.keys()))
                self.assertEqual(lines[-1], "")
        finally:
            pass


if __name__ == '__main__':
    unittest.main()
