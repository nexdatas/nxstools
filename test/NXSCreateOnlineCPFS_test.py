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
try:
    import tango
except Exception:
    import PyTango as tango

import nxstools
from nxstools import nxscreate

try:
    import nxsextrasp00
except ImportError:
    from . import nxsextrasp00


try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

try:
    import TestServerSetUp
except ImportError:
    from . import TestServerSetUp


if sys.version_info > (3,):
    unicode = str
    long = int


# if 64-bit machione
IS64BIT = (struct.calcsize("P") == 8)


# test fixture
class NXSCreateOnlineCPFSTest(unittest.TestCase):

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
        self.maxDiff = None

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

    # test closer
    # \brief Common tear down
    def tearDown(self):
        print("tearing down ...")

    def dsexists(self, name):
        return os.path.isfile("%s/%s.ds.xml" % (self.directory, name))

    def cpexists(self, name):
        return os.path.isfile("%s/%s.xml" % (self.directory, name))

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
        nxscreate.main()
        sys.argv = old_argv

        sys.stdout = old_stdout
        sys.stderr = old_stderr
        vl = mystdout.getvalue()
        er = mystderr.getvalue()
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

    def checkxmls(self, args, fname):
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

                    for cmd in arg[0]:
                        vl, er = self.runtest(cmd)
                        # print(vl)
                        # print(er)
                        if er:
                            self.assertTrue(er.startswith("Info: "))
                        else:
                            self.assertEqual('', er)
                        self.assertTrue(vl)

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
            os.remove(fname)
            for cp in cptotest:
                if self.cpexists(cp):
                    self.deletecp(cp)
            for ds in dstotest:
                if self.dsexists(ds):
                    self.deleteds(ds)

    def test_onlinecp_typelist_none(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname = '%s/%s%s.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml = """<?xml version="1.0"?>
<hw>
<device>
 <name>my_exp_mot01</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>p09/motor/exp.01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
<device>
 <name>my_exp_mot02</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>p09/motor/exp.02</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>2</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
<device>
 <name>my_exp_mot03</name>
 <type>stepping_motor</type>
 <module>oms58</module>
 <device>p09/motor/exp.03</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>3</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
</hw>
"""
        args = [
            [
                ('nxscreate onlinecp %s %s'
                 % (fname, self.flags)).split(),
            ],
        ]

        if os.path.isfile(fname):
            raise Exception("Test file %s exists" % fname)
        with open(fname, "w") as fl:
            fl.write(xml)
        try:
            for arg in args:
                vl, er = self.runtest(arg[0])

                # if er:
                #     self.assertTrue(er.startswith("Info: ")
                # else:
                #     self.assertEqual('', er)
                self.assertTrue(vl)
                lines = vl.split("\n")
                self.assertEqual(lines[-6], "POSSIBLE COMPONENTS: ")
                self.assertEqual(
                    lines[-5].split(),
                    [])
                self.assertEqual(lines[-4], "")
                self.assertEqual(lines[-3],
                                 "POSSIBLE COMPONENT TYPES: ")
                self.assertEqual(
                    lines[-2].split(),
                    ["cobold", "dalsa", "dalsavds",
                     "eiger1m16vds", "eiger1m32vds",
                     "eiger4m16vds", "eiger4m32vds", "eiger9m16vds",
                     "eiger9m32vds", "eigerdectris", "eigerdectrismesh",
                     "lambda", "lambda2m",
                     "lambdavds",
                     "lambdavdsnm",
                     "limaccd", "limaccds", "limaccdvds",
                     "marccd", "mca_xia", "minipix",
                     "mythen", "mythen2", "pco", "pco4000", "pcoedge",
                     "pedetector", "perkinelmer",
                     "perkinelmerdetector",
                     "pilatus", "pilatus100k",
                     "pilatus1m", "pilatus2m", "pilatus300k",
                     "pilatus6m", "pilc", "pilctimeid", "pilcvds",
                     "pilcvds4",
                     "tangovimba", "xspress3"])
        finally:
            os.remove(fname)

    def test_onlinecp_typelist_single(self):
        """ test nxsccreate onlinecp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname = '%s/%s%s.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml = '<?xml version="1.0"?>\n' \
              '<hw>\n' \
              '<device>\n' \
              '    <name>%s</name>\n' \
              '    <type>type_tango</type>\n' \
              '    <module>%s</module>\n' \
              '    <device>%s</device>\n' \
              '    <control>tango</control>\n' \
              '    <hostname>%s:%s</hostname>\n' \
              '</device>\n' \
              '</hw>\n'

        command = ('nxscreate onlinecp %s %s'
                   % (fname, self.flags)).split()

        [
            'eigerdectris',         # +
            'pco4000',              #
            'pilatus2m',            #
            'pedetector',           #
            'mythen2',              #
            'perkinelmer',          #
            'mca_xia',              # +
            "minipix",
            'pco',
            'pilatus6m',            #
            "pilc",
            "pilctimeid",
            "pilcvds",
            "pilcvds4",
            'marccd',               # +
            'pcoedge',              #
            'pilatus100k',          #
            'tangovimba',           #
            'xspress3',
            'cobold',
            'mythen',               #
            'pilatus1m',            #
            'pilatus',              # +
            'pilatus300k',          #
            'perkinelmerdetector',  #
            'limaccd',              #
            'lambda2m',             #
            'lambdavds',            #
            'lambdavdsnm',          #
            'limaccds',             #
            'limaccdvds',           #
            'lambda'                # +
        ]

        args = [
            ['my_test_%s' % ky, "mytest/%s/00" % ky, vl, ky]
            for ky, vl in nxstools.xmltemplates.moduleTemplateFiles.items()
        ]

        try:
            for arg in args:
                ds = arg[0]
                dv = arg[1]
                attr = list(arg[2])
                module = arg[3]
                if os.path.isfile(fname):
                    raise Exception("Test file %s exists" % fname)
                with open(fname, "w") as fl:
                    fl.write(xml % (ds, module, dv, self.host, self.port))
                try:

                    skip = False
                    for el in attr:
                        if self.dsexists(
                                "%s_%s" % (ds, el.lower())
                                if el else ds):
                            skip = True
                    if not skip:

                        vl, er = self.runtest(command)

                        if er:
                            self.assertTrue(er.startswith(
                                "Info"))
                        else:
                            self.assertEqual('', er)
                        self.assertTrue(vl)
                        lines = vl.split("\n")
                        self.assertEqual(lines[-6], "POSSIBLE COMPONENTS: ")
                        self.assertEqual(
                            lines[-5].split(), [ds])
                        self.assertEqual(lines[-3],
                                         "POSSIBLE COMPONENT TYPES: ")
                        self.assertEqual(
                            lines[-2].split(),
                            ["cobold", "dalsa", "dalsavds",
                             "eiger1m16vds", "eiger1m32vds",
                             "eiger4m16vds", "eiger4m32vds", "eiger9m16vds",
                             "eiger9m32vds", "eigerdectris",
                             "eigerdectrismesh",
                             "lambda", "lambda2m",
                             "lambdavds", "lambdavdsnm",
                             "limaccd", "limaccds", "limaccdvds",
                             "marccd", "mca_xia", "minipix",
                             "mythen", "mythen2", "pco", "pco4000", "pcoedge",
                             "pedetector", "perkinelmer",
                             "perkinelmerdetector",
                             "pilatus", "pilatus100k",
                             "pilatus1m", "pilatus2m", "pilatus300k",
                             "pilatus6m", "pilc", "pilctimeid", "pilcvds",
                             "pilcvds4",
                             "tangovimba", "xspress3"])
                finally:
                    os.remove(fname)
        finally:
            pass

    def test_onlinecp_typelist_multiple(self):
        """ test nxsccreate onlinecp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname = '%s/%s%s.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        startxml = '<?xml version="1.0"?>\n' \
                   '<hw>\n'

        dsxml = '<device>\n' \
                '    <name>%s</name>\n' \
                '    <type>type_tango</type>\n' \
                '    <module>%s</module>\n' \
                '    <device>%s</device>\n' \
                '    <control>tango</control>\n' \
                '    <hostname>%s:%s</hostname>\n'\
                '</device>\n'
        endxml = '</hw>\n'

        command = ('nxscreate onlinecp %s %s'
                   % (fname, self.flags)).split()

        args = [
            ['my_test_%s' % ky, "mytest/%s/00" % ky, vl, ky]
            for ky, vl in nxstools.xmltemplates.moduleTemplateFiles.items()
        ]
        if os.path.isfile(fname):
            raise Exception("Test file %s exists" % fname)
        with open(fname, "w") as fl:
            fl.write(startxml)
            for arg in args:
                ds = arg[0]
                dv = arg[1]
                module = arg[3]
                fl.write(dsxml % (ds, module, dv, self.host, self.port))
            fl.write(endxml)

        try:
            dss = [arg[0] for arg in args]
            vl, er = self.runtest(command)

            if er:
                self.assertTrue(er.startswith(
                    "Info"))
            else:
                self.assertEqual('', er)
            self.assertTrue(vl)
            lines = vl.split("\n")
            self.assertEqual(lines[-6], "POSSIBLE COMPONENTS: ")
            self.assertEqual(
                sorted(lines[-5].split()), sorted(dss))
            self.assertEqual(lines[-3],
                             "POSSIBLE COMPONENT TYPES: ")
            self.assertEqual(
                lines[-2].split(),
                ["cobold", "dalsa", "dalsavds",
                 "eiger1m16vds", "eiger1m32vds",
                 "eiger4m16vds", "eiger4m32vds", "eiger9m16vds",
                 "eiger9m32vds", "eigerdectris", "eigerdectrismesh",
                 "lambda", "lambda2m",
                 "lambdavds", "lambdavdsnm",
                 "limaccd", "limaccds", "limaccdvds",
                 "marccd", "mca_xia", "minipix",
                 "mythen", "mythen2", "pco", "pco4000", "pcoedge",
                 "pedetector", "perkinelmer",
                 "perkinelmerdetector",
                 "pilatus", "pilatus100k",
                 "pilatus1m", "pilatus2m", "pilatus300k",
                 "pilatus6m", "pilc", "pilctimeid", "pilcvds", "pilcvds4",
                 "tangovimba", "xspress3"])
        finally:
            os.remove(fname)

    def test_onlinecp_pilatus(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname = '%s/%s%s.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml = """<?xml version="1.0"?>
<hw>
<device>
 <name>mypilatus</name>
 <type>type_tango</type>
 <module>pilatus</module>
 <device>p09/pilatus/exp.01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
</hw>
"""
        args = [
            [
                [
                    ('nxscreate onlinecp -c mypilatus '
                     ' %s %s ' % (fname,  self.flags)).split(),
                    ('nxscreate onlinecp --component mypilatus '
                     ' %s %s ' % (fname,  self.flags)).split(),
                ],
                [
                    ['mypilatus'],
                    [
                        'mypilatus_delaytime',
                        'mypilatus_description',
                        'mypilatus_exposureperiod',
                        'mypilatus_exposuretime',
                        'mypilatus_filedir',
                        'mypilatus_filepostfix',
                        'mypilatus_fileprefix',
                        'mypilatus_filestartnum_cb',
                        'mypilatus_filestartnum',
                        'mypilatus_mxparameters_cb',
                        'mypilatus_mxparameters',
                        'mypilatus_lastimagetaken',
                        'mypilatus_nbexposures',
                        'mypilatus_nbframes',
                        'mypilatus_postrun'
                    ],
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <group type="NXentry" '
                     'name="$var.entryname#\'scan\'$var.serialno">\n'
                     '    <group type="NXinstrument" name="instrument">\n'
                     '      <group type="NXdetector" name="mypilatus">\n'
                     '        <field units="um" type="NX_FLOAT64" '
                     'name="x_pixel_size">172</field>\n'
                     '        <field units="um" type="NX_FLOAT64" '
                     'name="y_pixel_size">172</field>\n'
                     '        <field type="NX_CHAR" name="layout">area'
                     '</field>\n'
                     '        <field type="NX_CHAR" name="description">'
                     '$datasources.mypilatus_description'
                     '<strategy mode="INIT"/>\n'
                     '        </field>\n'
                     '        <group type="NXcollection" name="collection">\n'
                     '          <field units="s" type="NX_FLOAT64" '
                     'name="delay_time">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_delaytime</field>\n'
                     '          <field units="s" type="NX_FLOAT64" '
                     'name="exposure_period">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_exposureperiod</field>\n'
                     '          <field units="s" type="NX_FLOAT64" '
                     'name="exposure_time">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_exposuretime</field>\n'
                     '          <field type="NX_UINT64" name="nb_frames">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_nbframes</field>\n'
                     '          <field type="NX_UINT64" name="nb_exposures">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_nbexposures</field>\n'
                     '          <field type="NX_CHAR" name="postrun">'
                     '$datasources.mypilatus_postrun<strategy mode="FINAL"/>\n'
                     '          </field>\n'
                     '          <field type="NX_CHAR" name="file_dir">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_filedir</field>\n'
                     '          <field type="NX_CHAR" name="file_postfix">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_filepostfix</field>\n'
                     '          <field type="NX_CHAR" name="file_prefix">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_fileprefix</field>\n'
                     '          <field type="NX_CHAR" '
                     'name="last_image_taken">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_lastimagetaken</field>\n'
                     '          <field type="NX_UINT" '
                     'name="signal">1</field>\n'
                     '          <field type="NX_CHAR" '
                     'name="file_start_index_num">\n'
                     '            <strategy mode="STEP"/>'
                     '$datasources.mypilatus_filestartnum_cb</field>\n'
                     '          <field type="NX_CHAR" name="mx_parameters">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_mxparameters_cb</field>\n'
                     '        </group>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '    <group type="NXdata" name="data">\n'
                     '      <link '
                     'target="$var.entryname#\'scan\'$var.serialno/'
                     'instrument/mypilatus/data" name="mypilatus"/>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>\n'],
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_delaytime">\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="DelayTime"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" '
                     'name="mypilatus_description">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import common\n'
                     'common.blockitem_rm(commonblock,'
                     ' ["mypilatus_filestartnum"])\n'
                     'ds.result = "mypilatus"\n'
                     '    </result>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="mypilatus_exposureperiod"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="ExposurePeriod"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_exposuretime"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="ExposureTime"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_filedir"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="FileDir"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_filepostfix"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="FilePostfix"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_fileprefix"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="FilePrefix"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" '
                     'name="mypilatus_filestartnum_cb">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import common\n'
                     'ds.result = common.filestartnum_cb('
                     'commonblock, ds.mypilatus_filestartnum,'
                     ' ds.mypilatus_nbframes,'
                     ' "mypilatus_filestartnum")\n'
                     '    </result>\n'
                     '    $datasources.mypilatus_filestartnum\n'
                     '    $datasources.mypilatus_nbframes\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_filestartnum"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="FileStartNum"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\'?>\n<definition>\n'
                     '  <datasource type="PYEVAL" '
                     'name="mypilatus_mxparameters_cb">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import pilatus\n'
                     'ds.result = pilatus.mxparameters_cb('
                     'commonblock, ds.mypilatus_mxparameters,'
                     ' "mypilatus",'
                     ' "$var.entryname#\'scan\'$var.serialno",'
                     ' "instrument")\n'
                     '</result>\n'
                     ' $datasources.mypilatus_mxparameters</datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  '
                     '<datasource type="TANGO" name="mypilatus_mxparameters"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01"'
                     ' member="attribute" hostname="haso000"'
                     ' port="10000" group="mypilatus_"/>\n'
                     '    <record name="MXparameters"/>\n'
                     '  </datasource>\n</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="mypilatus_lastimagetaken"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="LastImageTaken"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_nbexposures"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="NbExposures"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_nbframes"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="NbFrames"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" name="mypilatus_postrun">\n'
                     '   <result name="result">\n'
                     'from nxstools.pyeval import pilatus\n'
                     'ds.result = pilatus.postrun('
                     'commonblock,'
                     ' ds.mypilatus_filestartnum,'
                     ' ds.mypilatus_filedir,'
                     ' ds.mypilatus_nbframes,'
                     ' ds.mypilatus_filepostfix,'
                     ' ds.mypilatus_fileprefix,'
                     ' "mypilatus_filestartnum")\n'
                     '  </result>\n'
                     ' $datasources.mypilatus_filestartnum\n'
                     ' $datasources.mypilatus_filedir\n'
                     ' $datasources.mypilatus_nbframes\n'
                     ' $datasources.mypilatus_filepostfix\n'
                     ' $datasources.mypilatus_fileprefix</datasource>\n'
                     '</definition>\n'],
                ],
            ],
        ]
        if os.path.isfile(fname):
            raise Exception("Test file %s exists" % fname)
        with open(fname, "w") as fl:
            fl.write(xml)

        self.checkxmls(args, fname)

    def test_onlinecp_pilatus_sardananame(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname = '%s/%s%s.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml = """<?xml version="1.0"?>
<hw>
<device>
 <name>p1m</name>
 <sardananame>mypilatus</sardananame>
 <type>type_tango</type>
 <module>pilatus</module>
 <device>p09/pilatus/exp.01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
</hw>
"""
        args = [
            [
                [
                    ('nxscreate onlinecp -c mypilatus '
                     ' %s %s ' % (fname,  self.flags)).split(),
                    ('nxscreate onlinecp --component mypilatus '
                     ' %s %s ' % (fname,  self.flags)).split(),
                ],
                [
                    ['mypilatus'],
                    [
                        'mypilatus_delaytime',
                        'mypilatus_description',
                        'mypilatus_exposureperiod',
                        'mypilatus_exposuretime',
                        'mypilatus_filedir',
                        'mypilatus_filepostfix',
                        'mypilatus_fileprefix',
                        'mypilatus_filestartnum_cb',
                        'mypilatus_filestartnum',
                        'mypilatus_mxparameters_cb',
                        'mypilatus_mxparameters',
                        'mypilatus_lastimagetaken',
                        'mypilatus_nbexposures',
                        'mypilatus_nbframes',
                        'mypilatus_postrun'
                    ],
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <group type="NXentry" '
                     'name="$var.entryname#\'scan\'$var.serialno">\n'
                     '    <group type="NXinstrument" name="instrument">\n'
                     '      <group type="NXdetector" name="mypilatus">\n'
                     '        <field units="um" type="NX_FLOAT64" '
                     'name="x_pixel_size">172</field>\n'
                     '        <field units="um" type="NX_FLOAT64" '
                     'name="y_pixel_size">172</field>\n'
                     '        <field type="NX_CHAR" name="layout">area'
                     '</field>\n'
                     '        <field type="NX_CHAR" name="description">'
                     '$datasources.mypilatus_description'
                     '<strategy mode="INIT"/>\n'
                     '        </field>\n'
                     '        <group type="NXcollection" name="collection">\n'
                     '          <field units="s" type="NX_FLOAT64" '
                     'name="delay_time">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_delaytime</field>\n'
                     '          <field units="s" type="NX_FLOAT64" '
                     'name="exposure_period">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_exposureperiod</field>\n'
                     '          <field units="s" type="NX_FLOAT64" '
                     'name="exposure_time">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_exposuretime</field>\n'
                     '          <field type="NX_UINT64" name="nb_frames">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_nbframes</field>\n'
                     '          <field type="NX_UINT64" name="nb_exposures">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_nbexposures</field>\n'
                     '          <field type="NX_CHAR" name="postrun">'
                     '$datasources.mypilatus_postrun<strategy mode="FINAL"/>\n'
                     '          </field>\n'
                     '          <field type="NX_CHAR" name="file_dir">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_filedir</field>\n'
                     '          <field type="NX_CHAR" name="file_postfix">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_filepostfix</field>\n'
                     '          <field type="NX_CHAR" name="file_prefix">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_fileprefix</field>\n'
                     '          <field type="NX_CHAR" '
                     'name="last_image_taken">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_lastimagetaken</field>\n'
                     '          <field type="NX_UINT" '
                     'name="signal">1</field>\n'
                     '          <field type="NX_CHAR" '
                     'name="file_start_index_num">\n'
                     '            <strategy mode="STEP"/>'
                     '$datasources.mypilatus_filestartnum_cb</field>\n'
                     '          <field type="NX_CHAR" name="mx_parameters">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mypilatus_mxparameters_cb</field>\n'
                     '        </group>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '    <group type="NXdata" name="data">\n'
                     '      <link '
                     'target="$var.entryname#\'scan\'$var.serialno/'
                     'instrument/mypilatus/data" name="mypilatus"/>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>\n'],
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_delaytime">\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="DelayTime"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" '
                     'name="mypilatus_description">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import common\n'
                     'common.blockitem_rm(commonblock,'
                     ' ["mypilatus_filestartnum"])\n'
                     'ds.result = "mypilatus"\n'
                     '    </result>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="mypilatus_exposureperiod"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="ExposurePeriod"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_exposuretime"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="ExposureTime"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_filedir"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="FileDir"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_filepostfix"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="FilePostfix"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_fileprefix"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="FilePrefix"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" '
                     'name="mypilatus_filestartnum_cb">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import common\n'
                     'ds.result = common.filestartnum_cb('
                     'commonblock, ds.mypilatus_filestartnum,'
                     ' ds.mypilatus_nbframes,'
                     ' "mypilatus_filestartnum")\n'
                     '    </result>\n'
                     '    $datasources.mypilatus_filestartnum\n'
                     '    $datasources.mypilatus_nbframes\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_filestartnum"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="FileStartNum"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\'?>\n<definition>\n'
                     '  <datasource type="PYEVAL" '
                     'name="mypilatus_mxparameters_cb">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import pilatus\n'
                     'ds.result = pilatus.mxparameters_cb('
                     'commonblock, ds.mypilatus_mxparameters,'
                     ' "mypilatus",'
                     ' "$var.entryname#\'scan\'$var.serialno",'
                     ' "instrument")\n'
                     '</result>\n'
                     ' $datasources.mypilatus_mxparameters</datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  '
                     '<datasource type="TANGO" name="mypilatus_mxparameters"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01"'
                     ' member="attribute" hostname="haso000"'
                     ' port="10000" group="mypilatus_"/>\n'
                     '    <record name="MXparameters"/>\n'
                     '  </datasource>\n</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="mypilatus_lastimagetaken"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="LastImageTaken"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_nbexposures"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="NbExposures"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mypilatus_nbframes"'
                     '>\n'
                     '    <device name="p09/pilatus/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mypilatus_"/>\n'
                     '    <record name="NbFrames"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" name="mypilatus_postrun">\n'
                     '   <result name="result">\n'
                     'from nxstools.pyeval import pilatus\n'
                     'ds.result = pilatus.postrun('
                     'commonblock,'
                     ' ds.mypilatus_filestartnum,'
                     ' ds.mypilatus_filedir,'
                     ' ds.mypilatus_nbframes,'
                     ' ds.mypilatus_filepostfix,'
                     ' ds.mypilatus_fileprefix,'
                     ' "mypilatus_filestartnum")\n'
                     '  </result>\n'
                     ' $datasources.mypilatus_filestartnum\n'
                     ' $datasources.mypilatus_filedir\n'
                     ' $datasources.mypilatus_nbframes\n'
                     ' $datasources.mypilatus_filepostfix\n'
                     ' $datasources.mypilatus_fileprefix</datasource>\n'
                     '</definition>\n'],
                ],
            ],
        ]
        if os.path.isfile(fname):
            raise Exception("Test file %s exists" % fname)
        with open(fname, "w") as fl:
            fl.write(xml)

        self.checkxmls(args, fname)

    def test_onlinecp_lambda_entry(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname = '%s/%s%s.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml = """<?xml version="1.0"?>
<hw>
<device>
 <name>Mylmbd</name>
 <type>type_tango</type>
 <module>lambda</module>
 <device>p09/lambda/exp.01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
</hw>
"""
        args = [
            [
                [
                    ('nxscreate onlinecp -c mylmbd '
                     ' -y myentry '
                     ' -i myinstrument '
                     ' %s %s ' % (fname,  self.flags)).split(),
                    ('nxscreate onlinecp --component mylmbd '
                     ' --entryname myentry '
                     ' --insname myinstrument '
                     ' %s %s ' % (fname,  self.flags)).split(),
                ],
                [
                    ['mylmbd'],
                    ['mylmbd_compressionrate',
                     'mylmbd_configfilepath',
                     'mylmbd_delaytime',
                     'mylmbd_depth',
                     'mylmbd_distortioncorrection',
                     'mylmbd_energythreshold',
                     'mylmbd_external_data',
                     'mylmbd_filepostfix',
                     'mylmbd_filepreext',
                     'mylmbd_fileprefix',
                     'mylmbd_filestartnum',
                     'mylmbd_framenumbers',
                     'mylmbd_framesperfile',
                     'mylmbd_height',
                     'mylmbd_latestimagenumber',
                     'mylmbd_layout',
                     'mylmbd_liveframeno',
                     'mylmbd_livelastimagedata',
                     'mylmbd_livemode',
                     'mylmbd_nxdata',
                     'mylmbd_operatingmode',
                     'mylmbd_saveallimages',
                     'mylmbd_savefilename',
                     'mylmbd_savefilepath',
                     'mylmbd_shuttertime',
                     'mylmbd_shuttertimemax',
                     'mylmbd_shuttertimemin',
                     'mylmbd_threadno',
                     'mylmbd_totallossframes',
                     'mylmbd_triggermode',
                     'mylmbd_width'],
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <group type="NXentry" '
                     'name="$var.entryname#\'myentry\'$var.serialno">\n'
                     '    <group type="NXinstrument" name="myinstrument">\n'
                     '      <group type="NXdetector" name="mylmbd">\n'
                     '        <field units="um" type="NX_FLOAT64" '
                     'name="x_pixel_size">55<strategy mode="INIT"/>\n'
                     '        </field>\n'
                     '        <field units="um" type="NX_FLOAT64" '
                     'name="y_pixel_size">55<strategy mode="INIT"/>\n'
                     '        </field>\n'
                     '        <field type="NX_CHAR" name="layout">area'
                     '<strategy mode="INIT"/>\n'
                     '        </field>\n'
                     '        <field type="NX_CHAR" name="description">'
                     'mylmbd</field>\n'
                     '        <field units="eV" type="NX_FLOAT32" '
                     'name="threshold_energy">\n'
                     '          <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_energythreshold</field>\n'
                     '        <group type="NXcollection" name="collection">\n'
                     '          <field type="NX_INT16" name="trigger_mode">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_triggermode</field>\n'
                     '          <field units="ms" type="NX_FLOAT64" '
                     'name="shutter_time">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_shuttertime</field>\n'
                     '          <field type="NX_INT64" name="frame_numbers">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_framenumbers</field>\n'
                     '          <field type="NX_BOOLEAN" '
                     'name="save_all_images">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_saveallimages</field>\n'
                     '          <field type="NX_INT64" '
                     'name="lastest_image_number">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_latestimagenumber</field>\n'
                     '          <field type="NX_INT64" '
                     'name="total_loss_frames">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_totallossframes</field>\n'
                     '          <field type="NX_UINT64" name="width">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_width</field>\n'
                     '          <field type="NX_UINT64" name="height">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_height</field>\n'
                     '          <field type="NX_UINT64" name="depth">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_depth</field>\n'
                     '          <field type="NX_UINT16" '
                     'name="distortion_correction">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_distortioncorrection</field>\n'
                     '        </group>\n'
                     '        <group type="NXcollection" '
                     'name="collection_extra">\n'
                     '          <field type="NX_INT64" name="thread_no">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_threadno</field>\n'
                     '          <field type="NX_CHAR" '
                     'name="config_file_path">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_configfilepath</field>\n'
                     '          <field type="NX_CHAR" name="file_prefix">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_fileprefix</field>\n'
                     '          <field type="NX_CHAR" name="file_start_num">\n'
                     '            <strategy mode="INIT"/>'
                     '$datasources.mylmbd_filestartnum</field>\n'
                     '          <field type="NX_CHAR" name="file_pre_ext">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_filepreext</field>\n'
                     '          <field type="NX_CHAR" name="file_postfix">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_filepostfix</field>\n'
                     '          <field type="NX_CHAR" name="save_file_path">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_savefilepath</field>\n'
                     '          <field type="NX_CHAR" name='
                     '"frames_per_file">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_framesperfile</field>\n'
                     '          <field type="NX_CHAR" name="save_file_name">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_savefilename</field>\n'
                     '          <field type="NX_UINT16" '
                     'name="compression_rate">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_compressionrate</field>\n'
                     '          <field type="NX_CHAR" name="layout">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_layout</field>\n'
                     '          <field units="ms" type="NX_FLOAT64" '
                     'name="shutter_time_max">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_shuttertimemax</field>\n'
                     '          <field units="ms" type="NX_FLOAT64" '
                     'name="shutter_time_min">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.mylmbd_shuttertimemin</field>\n'
                     '        </group>\n'
                     '      </group>\n'
                     '      <link name="mylmbd_m1">'
                     '$datasources.mylmbd_external_data<strategy '
                     'mode="FINAL"/>\n'
                     '      </link>\n'
                     '    </group>\n'
                     '    <group type="NXdata" name="data">\n'
                     '      <link name="mylmbd">'
                     '$datasources.mylmbd_nxdata<strategy '
                     'mode="FINAL"/></link>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>\n'],
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_compressionrate"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="CompressionRate"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_configfilepath"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="ConfigFilePath"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_delaytime"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="DelayTime"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_depth"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="Depth"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" '
                     'name="mylmbd_distortioncorrection"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="DistortionCorrection"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="mylmbd_energythreshold"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="EnergyThreshold"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" '
                     'name="mylmbd_external_data">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import lmbd\n'
                     'ds.result = lmbd.external_data('
                     'commonblock,'
                     ' "mylmbd",'
                     ' ds.mylmbd_savefilename,'
                     ' ds.mylmbd_saveallimages,'
                     ' ds.mylmbd_framesperfile,'
                     ' ds.mylmbd_framenumbers,'
                     ' ds.mylmbd_filepostfix,'
                     ' "$var.filename")\n'
                     '  </result>\n'
                     ' $datasources.mylmbd_savefilename\n'
                     ' $datasources.mylmbd_saveallimages\n'
                     ' $datasources.mylmbd_framesperfile\n'
                     ' $datasources.mylmbd_framenumbers\n'
                     ' $datasources.mylmbd_filepostfix</datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_filepostfix"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="FilePostfix"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_filepreext"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="FilePreExt"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_fileprefix"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="FilePrefix"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_filestartnum"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="FileStartNum"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_framenumbers"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="FrameNumbers"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_framesperfile"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="FramesPerFile"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_height"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="Height"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" '
                     'name="mylmbd_latestimagenumber"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="LatestImageNumber"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_layout"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="Layout"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_liveframeno"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="LiveFrameNo"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="mylmbd_livelastimagedata"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="LiveLastImageData"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_livemode"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="LiveMode"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" name="mylmbd_nxdata">\n'
                     '    <result name="result">\n'
                     'ds.result = ""\n'
                     'if ds.mylmbd_saveallimages:\n'
                     '    ds.result += "$var.entryname#\'myentry\''
                     '$var.serialno:NXentry/myinstrument/'
                     'mylmbd_m1:NXdetector/data"</result>\n'
                     ' $datasources.mylmbd_saveallimages</datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="mylmbd_operatingmode"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="OperatingMode"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_saveallimages"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="SaveAllImages"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_savefilename"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="SaveFileName"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_savefilepath"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="SaveFilePath"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_shuttertime"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="ShutterTime"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_shuttertimemax"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="ShutterTimeMax"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_shuttertimemin"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="ShutterTimeMin"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_threadno"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="ThreadNo"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_totallossframes"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="TotalLossFrames"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_triggermode"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="TriggerMode"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mylmbd_width"'
                     '>\n'
                     '    <device name="p09/lambda/exp.01"'
                     ' member="attribute" hostname="haso000" '
                     'port="10000" group="mylmbd_"/>\n'
                     '    <record name="Width"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'],
                ],
            ],
        ]
        if os.path.isfile(fname):
            raise Exception("Test file %s exists" % fname)
        with open(fname, "w") as fl:
            fl.write(xml)

        self.checkxmls(args, fname)

    def test_onlinecp_marccd(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname = '%s/%s%s.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml = """<?xml version="1.0"?>
<hw>
<device>
 <name>MyMarccd</name>
 <type>type_tango</type>
 <module>mard</module>
 <device>p09/mard/exp.01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
</hw>
"""
        args = [
            [
                [
                    ('nxscreate onlinecp -c MyMarccd -t marccd -n '
                     ' %s %s ' % (fname,  self.flags)).split(),
                    ('nxscreate onlinecp --component MyMarccd --type marccd'
                     ' --nolower '
                     ' %s %s ' % (fname,  self.flags)).split(),
                ],
                [
                    ['MyMarccd'],
                    ['MyMarccd_frameshift',
                     'MyMarccd_postrun',
                     'MyMarccd_savingdirectory',
                     'MyMarccd_savingpostfix',
                     'MyMarccd_savingprefix'],
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <group type="NXentry" name="$var.entryname#\'scan\''
                     '$var.serialno">\n'
                     '    <group type="NXinstrument" name="instrument">\n'
                     '      <group type="NXdetector" name="MyMarccd">\n'
                     '        <field type="NX_CHAR" name="layout">area'
                     '</field>\n'
                     '        <field type="NX_CHAR" name="description">'
                     'MyMarccd</field>\n'
                     '        <group type="NXcollection" name="collection">\n'
                     '          <field units="s" type="NX_FLOAT64" '
                     'name="frame_shift">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.MyMarccd_frameshift</field>\n'
                     '          <field type="NX_CHAR" name="postrun">'
                     '$datasources.MyMarccd_postrun<strategy mode="STEP"/>\n'
                     '          </field>\n'
                     '          <field type="NX_CHAR" name="file_dir">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.MyMarccd_savingdirectory</field>\n'
                     '          <field type="NX_CHAR" name="file_prefix">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.MyMarccd_savingprefix</field>\n'
                     '          <field type="NX_CHAR" name="file_postfix">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.MyMarccd_savingpostfix</field>\n'
                     '          <field type="NX_UINT" name="signal">1'
                     '</field>\n'
                     '        </group>\n'
                     '        <field units="um" type="NX_FLOAT64" '
                     'name="x_pixel_size">80</field>\n'
                     '        <field units="um" type="NX_FLOAT64" '
                     'name="y_pixel_size">80</field>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '    <group type="NXdata" name="data">\n'
                     '      <link target="/$var.entryname#\'scan\''
                     '$var.serialno:NXentry/instrument/MyMarccd:NXdetector/'
                     'data" name="MyMarccd"/>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>\n'
                     ''],
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="MyMarccd_frameshift">\n'
                     '    <device name="p09/mard/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mymarccd_"/>\n'
                     '    <record name="FrameShift"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" name="MyMarccd_postrun">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import marccd\n'
                     'ds.result = marccd.postrun('
                     'commonblock,'
                     ' ds.MyMarccd_savingdirectory,'
                     ' ds.MyMarccd_savingprefix,'
                     ' ds.MyMarccd_savingpostfix)\n'
                     '</result>\n'
                     ' $datasources.MyMarccd_savingdirectory\n'
                     ' $datasources.MyMarccd_savingpostfix\n'
                     ' $datasources.MyMarccd_savingprefix</datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="MyMarccd_savingdirectory"'
                     '>\n'
                     '    <device name="p09/mard/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mymarccd_"/>\n'
                     '    <record name="SavingDirectory"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="MyMarccd_savingpostfix"'
                     '>\n'
                     '    <device name="p09/mard/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mymarccd_"/>\n'
                     '    <record name="SavingPostfix"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="MyMarccd_savingprefix"'
                     '>\n'
                     '    <device name="p09/mard/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mymarccd_"/>\n'
                     '    <record name="SavingPrefix"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'],
                ],
            ],
        ]
        if os.path.isfile(fname):
            raise Exception("Test file %s exists" % fname)
        with open(fname, "w") as fl:
            fl.write(xml)

        self.checkxmls(args, fname)

    def test_onlinecp_marccd_wo_online(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname = '%s/%s%s.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml = """<?xml version="1.0"?>
<hw>
<device>
 <name>MyMarccd</name>
 <type>type_tango</type>
 <module>mard</module>
 <device>p09/mard/exp.01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
</hw>
"""
        args = [
            [
                [
                    ('nxscreate onlinecp -c MyMarccd -t marccd -n '
                     '-v p09/mard/exp.01 -u haso000 -w 10000'
                     ' %s ' % (self.flags)).split(),
                    ('nxscreate onlinecp --component MyMarccd --type marccd'
                     ' -v p09/mard/exp.01 -u haso000 -w 10000 '
                     ' --nolower '
                     ' %s ' % (self.flags)).split(),
                ],
                [
                    ['MyMarccd'],
                    ['MyMarccd_frameshift',
                     'MyMarccd_postrun',
                     'MyMarccd_savingdirectory',
                     'MyMarccd_savingpostfix',
                     'MyMarccd_savingprefix'],
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <group type="NXentry" name="$var.entryname#\'scan\''
                     '$var.serialno">\n'
                     '    <group type="NXinstrument" name="instrument">\n'
                     '      <group type="NXdetector" name="MyMarccd">\n'
                     '        <field type="NX_CHAR" name="layout">area'
                     '</field>\n'
                     '        <field type="NX_CHAR" name="description">'
                     'MyMarccd</field>\n'
                     '        <group type="NXcollection" name="collection">\n'
                     '          <field units="s" type="NX_FLOAT64" '
                     'name="frame_shift">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.MyMarccd_frameshift</field>\n'
                     '          <field type="NX_CHAR" name="postrun">'
                     '$datasources.MyMarccd_postrun<strategy mode="STEP"/>\n'
                     '          </field>\n'
                     '          <field type="NX_CHAR" name="file_dir">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.MyMarccd_savingdirectory</field>\n'
                     '          <field type="NX_CHAR" name="file_prefix">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.MyMarccd_savingprefix</field>\n'
                     '          <field type="NX_CHAR" name="file_postfix">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.MyMarccd_savingpostfix</field>\n'
                     '          <field type="NX_UINT" name="signal">1'
                     '</field>\n'
                     '        </group>\n'
                     '        <field units="um" type="NX_FLOAT64" '
                     'name="x_pixel_size">80</field>\n'
                     '        <field units="um" type="NX_FLOAT64" '
                     'name="y_pixel_size">80</field>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '    <group type="NXdata" name="data">\n'
                     '      <link target="/$var.entryname#\'scan\''
                     '$var.serialno:NXentry/instrument/MyMarccd:NXdetector/'
                     'data" name="MyMarccd"/>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>\n'
                     ''],
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="MyMarccd_frameshift">\n'
                     '    <device name="p09/mard/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mymarccd_"/>\n'
                     '    <record name="FrameShift"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" name="MyMarccd_postrun">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import marccd\n'
                     'ds.result = marccd.postrun('
                     'commonblock,'
                     ' ds.MyMarccd_savingdirectory,'
                     ' ds.MyMarccd_savingprefix,'
                     ' ds.MyMarccd_savingpostfix)\n'
                     '</result>\n'
                     ' $datasources.MyMarccd_savingdirectory\n'
                     ' $datasources.MyMarccd_savingpostfix\n'
                     ' $datasources.MyMarccd_savingprefix</datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="MyMarccd_savingdirectory"'
                     '>\n'
                     '    <device name="p09/mard/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mymarccd_"/>\n'
                     '    <record name="SavingDirectory"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="MyMarccd_savingpostfix"'
                     '>\n'
                     '    <device name="p09/mard/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mymarccd_"/>\n'
                     '    <record name="SavingPostfix"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="MyMarccd_savingprefix"'
                     '>\n'
                     '    <device name="p09/mard/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mymarccd_"/>\n'
                     '    <record name="SavingPrefix"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'],
                ],
            ],
        ]
        if os.path.isfile(fname):
            raise Exception("Test file %s exists" % fname)
        with open(fname, "w") as fl:
            fl.write(xml)

        self.checkxmls(args, fname)

    def test_onlinecp_mcaxia_overwrite_false(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname1 = '%s/%s%s1.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml1 = """<?xml version="1.0"?>
<hw>
<device>
 <name>mymcaxia</name>
 <type>type_tango</type>
 <module>mca_xia</module>
 <device>p09/mcaxia/exp.01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
</hw>
"""
        fname2 = '%s/%s%s2.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml2 = """<?xml version="1.0"?>
<hw>
<device>
 <name>mymcaxia</name>
 <type>type_tango</type>
 <module>mca_xia</module>
 <device>p09/mcaxia/e01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
</hw>
"""
        args = [
            [
                [
                    ('nxscreate onlinecp -c mymcaxia '
                     ' %s %s ' % (fname1,  self.flags)).split(),
                    ('nxscreate onlinecp --component mymcaxia '
                     ' %s %s ' % (fname1,  self.flags)).split(),
                ],
                [
                    ['mymcaxia'],
                    ['mymcaxia_countsroi',
                     'mymcaxia_icr',
                     'mymcaxia_ocr',
                     'mymcaxia_roiend',
                     'mymcaxia_roistart'],
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <group type="NXentry" name="$var.entryname#\'scan\''
                     '$var.serialno">\n'
                     '    <group type="NXinstrument" name="instrument">\n'
                     '      <group type="NXdetector" name="mymcaxia">\n'
                     '        <field type="NX_FLOAT64" name="data">'
                     '$datasources.mymcaxia<strategy mode="STEP"/>\n'
                     '          <dimensions rank="1"/>\n'
                     '        </field>\n'
                     '        <group type="NXcollection" name="collection">\n'
                     '          <field type="NX_FLOAT64" name="countsroi">'
                     '$datasources.mymcaxia_countsroi<strategy mode="STEP"/>\n'
                     '          </field>\n'
                     '          <field type="NX_FLOAT64" name="roistart">'
                     '$datasources.mymcaxia_roistart<strategy mode="INIT"/>\n'
                     '          </field>\n'
                     '          <field type="NX_FLOAT64" name="roiend">'
                     '$datasources.mymcaxia_roiend<strategy mode="INIT"/>\n'
                     '          </field>\n'
                     '          <field type="NX_FLOAT64" name="icr">'
                     '$datasources.mymcaxia_icr<strategy mode="STEP"/>\n'
                     '          </field>\n'
                     '          <field type="NX_FLOAT64" name="ocr">'
                     '$datasources.mymcaxia_ocr<strategy mode="STEP"/>\n'
                     '          </field>\n'
                     '        </group>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '    <group type="NXdata" name="data">\n'
                     '      <link target="$var.entryname#\'scan\'$var.serialno'
                     '/instrument/mymcaxia/data" name="mymcaxia"/>\n'
                     '      <link target="$var.entryname#\'scan\'$var.serialno'
                     '/instrument/mymcaxia/collection/countsroi" '
                     'name="mymcaxia_countsroi"/>\n'
                     '      <link target="$var.entryname#\'scan\'$var.serialno'
                     '/instrument/mymcaxia/collection/icr" '
                     'name="mymcaxia_icr"/>\n'
                     '      <link target="$var.entryname#\'scan\'$var.serialno'
                     '/instrument/mymcaxia/collection/ocr" '
                     'name="mymcaxia_ocr"/>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>\n'
                     ''],
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mymcaxia_countsroi">\n'
                     '    <device name="p09/mcaxia/exp.01" '
                     'member="attribute" hostname="%s" '
                     'port="%s" group="mymcaxia_"/>\n'
                     '    <record name="CountsRoI"/>\n'
                     '  </datasource>\n'
                     '</definition>\n' % (self.host, self.port),
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mymcaxia_icr">\n'
                     '    <device name="p09/mcaxia/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mymcaxia_"/>\n'
                     '    <record name="ICR"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mymcaxia_ocr">\n'
                     '    <device name="p09/mcaxia/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mymcaxia_"/>\n'
                     '    <record name="OCR"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mymcaxia_roiend">\n'
                     '    <device name="p09/mcaxia/exp.01" '
                     'member="attribute" hostname="%s" '
                     'port="%s" group="mymcaxia_"/>\n'
                     '    <record name="RoIEnd"/>\n'
                     '  </datasource>\n'
                     '</definition>\n' % (self.host, self.port),
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mymcaxia_roistart">\n'
                     '    <device name="p09/mcaxia/exp.01" '
                     'member="attribute" hostname="%s" '
                     'port="%s" group="mymcaxia_"/>\n'
                     '    <record name="RoIStart"/>\n'
                     '  </datasource>\n'
                     '</definition>\n' % (self.host, self.port)],
                ],
                [
                    ('nxscreate onlinecp -c mymcaxia '
                     ' %s %s ' % (fname2,  self.flags)).split(),
                    ('nxscreate onlinecp --component mymcaxia '
                     ' %s %s ' % (fname2,  self.flags)).split(),
                ],
            ],
        ]
        if os.path.isfile(fname1):
            raise Exception("Test file %s exists" % fname1)
        if os.path.isfile(fname2):
            raise Exception("Test file %s exists" % fname2)
        with open(fname1, "w") as fl:
            fl.write(xml1)
        with open(fname2, "w") as fl:
            fl.write(xml2)

        dstotest = []
        cptotest = []
        try:
            tsv = TestServerSetUp.TestServerSetUp(
                'p09/mcaxia/exp.01', "MYTESTS1",
                'mymcaxia'
            )
            tsv.setUp()
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

                    for ci, cmd in enumerate(arg[0]):
                        vl, er = self.runtest(cmd)
                        # print(vl)
                        # print(er)
                        if er:
                            self.assertTrue(er.startswith("Info: "))
                        else:
                            self.assertEqual('', er)
                        self.assertTrue(vl)

                        for i, ds in enumerate(arg[1][1]):
                            xml = self.getds(ds)
                            self.assertEqual(arg[2][1][i], xml)
                        for i, cp in enumerate(arg[1][0]):
                            xml = self.getcp(cp)
                            self.assertEqual(arg[2][0][i], xml)

                        vl, er, etxt = self.runtestexcept(
                            arg[3][ci], SystemExit)

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
            os.remove(fname2)
            os.remove(fname1)
            for cp in cptotest:
                if self.cpexists(cp):
                    self.deletecp(cp)
            for ds in dstotest:
                if self.dsexists(ds):
                    self.deleteds(ds)
            if tsv:
                tsv.tearDown()

    def test_onlinecp_mcaxia_overwrite_true(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname1 = '%s/%s%s1.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml1 = """<?xml version="1.0"?>
<hw>
<device>
 <name>mymcaxia</name>
 <type>type_tango</type>
 <module>mca_xia</module>
 <device>p09/mcaxia/exp.01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
</hw>
"""
        fname2 = '%s/%s%s2.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml2 = """<?xml version="1.0"?>
<hw>
<device>
 <name>mymcaxia</name>
 <type>type_tango</type>
 <module>mca_xia</module>
 <device>p09/mcaxia/e01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
</hw>
"""
        args = [
            [
                [
                    ('nxscreate onlinecp -c mymcaxia -o '
                     ' %s %s ' % (fname2,  self.flags)).split(),
                    ('nxscreate onlinecp --overwrite --component mymcaxia '
                     ' %s %s ' % (fname2,  self.flags)).split(),
                ],
                [
                    ['mymcaxia'],
                    ['mymcaxia_countsroi',
                     'mymcaxia_icr',
                     'mymcaxia_ocr',
                     'mymcaxia_roiend',
                     'mymcaxia_roistart'],
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <group type="NXentry" name="$var.entryname#\'scan\''
                     '$var.serialno">\n'
                     '    <group type="NXinstrument" name="instrument">\n'
                     '      <group type="NXdetector" name="mymcaxia">\n'
                     '        <field type="NX_FLOAT64" name="data">'
                     '$datasources.mymcaxia<strategy mode="STEP"/>\n'
                     '          <dimensions rank="1"/>\n'
                     '        </field>\n'
                     '        <group type="NXcollection" name="collection">\n'
                     '          <field type="NX_FLOAT64" name="countsroi">'
                     '$datasources.mymcaxia_countsroi<strategy mode="STEP"/>\n'
                     '          </field>\n'
                     '          <field type="NX_FLOAT64" name="roistart">'
                     '$datasources.mymcaxia_roistart<strategy mode="INIT"/>\n'
                     '          </field>\n'
                     '          <field type="NX_FLOAT64" name="roiend">'
                     '$datasources.mymcaxia_roiend<strategy mode="INIT"/>\n'
                     '          </field>\n'
                     '          <field type="NX_FLOAT64" name="icr">'
                     '$datasources.mymcaxia_icr<strategy mode="STEP"/>\n'
                     '          </field>\n'
                     '          <field type="NX_FLOAT64" name="ocr">'
                     '$datasources.mymcaxia_ocr<strategy mode="STEP"/>\n'
                     '          </field>\n'
                     '        </group>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '    <group type="NXdata" name="data">\n'
                     '      <link target="$var.entryname#\'scan\'$var.serialno'
                     '/instrument/mymcaxia/data" name="mymcaxia"/>\n'
                     '      <link target="$var.entryname#\'scan\'$var.serialno'
                     '/instrument/mymcaxia/collection/countsroi" '
                     'name="mymcaxia_countsroi"/>\n'
                     '      <link target="$var.entryname#\'scan\'$var.serialno'
                     '/instrument/mymcaxia/collection/icr" '
                     'name="mymcaxia_icr"/>\n'
                     '      <link target="$var.entryname#\'scan\'$var.serialno'
                     '/instrument/mymcaxia/collection/ocr" '
                     'name="mymcaxia_ocr"/>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>\n'
                     ''],
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mymcaxia_countsroi">\n'
                     '    <device name="p09/mcaxia/exp.01" '
                     'member="attribute" hostname="%s" '
                     'port="%s" group="mymcaxia_"/>\n'
                     '    <record name="CountsRoI"/>\n'
                     '  </datasource>\n'
                     '</definition>\n' % (self.host, self.port),
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mymcaxia_icr">\n'
                     '    <device name="p09/mcaxia/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mymcaxia_"/>\n'
                     '    <record name="ICR"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mymcaxia_ocr">\n'
                     '    <device name="p09/mcaxia/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="mymcaxia_"/>\n'
                     '    <record name="OCR"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'
                     '',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mymcaxia_roiend">\n'
                     '    <device name="p09/mcaxia/exp.01" '
                     'member="attribute" hostname="%s" '
                     'port="%s" group="mymcaxia_"/>\n'
                     '    <record name="RoIEnd"/>\n'
                     '  </datasource>\n'
                     '</definition>\n' % (self.host, self.port),
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="mymcaxia_roistart">\n'
                     '    <device name="p09/mcaxia/exp.01" '
                     'member="attribute" hostname="%s" '
                     'port="%s" group="mymcaxia_"/>\n'
                     '    <record name="RoIStart"/>\n'
                     '  </datasource>\n'
                     '</definition>\n' % (self.host, self.port)],
                ],
                [
                    ('nxscreate onlinecp -c mymcaxia -o '
                     ' %s %s ' % (fname1,  self.flags)).split(),
                    ('nxscreate onlinecp --overwrite --component mymcaxia '
                     ' %s %s ' % (fname1,  self.flags)).split(),
                ],
            ],
        ]
        if os.path.isfile(fname1):
            raise Exception("Test file %s exists" % fname1)
        if os.path.isfile(fname2):
            raise Exception("Test file %s exists" % fname2)
        with open(fname1, "w") as fl:
            fl.write(xml1)
        with open(fname2, "w") as fl:
            fl.write(xml2)

        dstotest = []
        cptotest = []
        try:
            tsv = TestServerSetUp.TestServerSetUp(
                'p09/mcaxia/exp.01', "MYTESTS1",
                'mymcaxia'
            )
            tsv.setUp()
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

                    for ci, cmd in enumerate(arg[0]):
                        vl, er = self.runtest(cmd)
                        # print(vl)
                        # print(er)
                        if er:
                            self.assertTrue(er.startswith("Info: "))
                        else:
                            self.assertEqual('', er)
                        self.assertTrue(vl)

                        vl, er = self.runtest(arg[3][ci])

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
            os.remove(fname2)
            os.remove(fname1)
            for cp in cptotest:
                if self.cpexists(cp):
                    self.deletecp(cp)
            for ds in dstotest:
                if self.dsexists(ds):
                    self.deleteds(ds)
            if tsv:
                tsv.tearDown()

    def test_onlinecp_typelist_single_module(self):
        """ test nxsccreate onlinecp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname = '%s/%s%s.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml = '<?xml version="1.0"?>\n' \
              '<hw>\n' \
              '<device>\n' \
              '    <name>%s</name>\n' \
              '    <type>type_tango</type>\n' \
              '    <module>%s</module>\n' \
              '    <device>%s</device>\n' \
              '    <control>tango</control>\n' \
              '    <hostname>%s:%s</hostname>\n' \
              '</device>\n' \
              '</hw>\n'

        if __name__ == 'test.NXSCreateOnlineCPFS_test':
            pname = 'test.nxsextrasp00'
        else:
            pname = 'nxsextrasp00'

        command = ('nxscreate onlinecp %s %s'
                   ' -p %s '
                   % (fname, self.flags, pname)).split()

        args = [
            ['my_test_%s' % ky, "mytest/%s/00" % ky, vl, ky]
            for ky, vl in nxsextrasp00.moduleTemplateFiles.items()
        ]

        try:
            for arg in args:
                ds = arg[0]
                dv = arg[1]
                attr = list(arg[2])
                module = arg[3]
                if os.path.isfile(fname):
                    raise Exception("Test file %s exists" % fname)
                with open(fname, "w") as fl:
                    fl.write(xml % (ds, module, dv, self.host, self.port))
                try:

                    skip = False
                    for el in attr:
                        if self.dsexists(
                                "%s_%s" % (ds, el.lower())
                                if el else ds):
                            skip = True
                    if not skip:

                        vl, er = self.runtest(command)

                        if er:
                            self.assertTrue(er.startswith(
                                "Info"))
                        else:
                            self.assertEqual('', er)
                        self.assertTrue(vl)
                        lines = vl.split("\n")
                        self.assertEqual(lines[-6], "POSSIBLE COMPONENTS: ")
                        self.assertEqual(
                            lines[-5].split(), [ds])
                        self.assertEqual(lines[-3],
                                         "POSSIBLE COMPONENT TYPES: ")
                        self.assertEqual(
                            lines[-2].split(), ["mymca"])
                finally:
                    os.remove(fname)
        finally:
            pass

    def test_onlinecp_mymca_module(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname = '%s/%s%s.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml = """<?xml version="1.0"?>
<hw>
<device>
 <name>testmymca</name>
 <type>type_tango</type>
 <module>mymca</module>
 <device>p09/mymca/exp.01</device>
 <control>tango</control>
 <hostname>haso000:10000</hostname>
 <controller>oms58_exp</controller>
 <channel>1</channel>
 <rootdevicename>p09/motor/exp</rootdevicename>
</device>
</hw>
"""
        if __name__ == 'test.NXSCreateOnlineCPFS_test':
            pname = 'test.nxsextrasp00'
        else:
            pname = 'nxsextrasp00'
        args = [
            [
                [
                    ('nxscreate onlinecp -c testmymca '
                     ' -p %s '
                     ' %s %s ' % (pname, fname, self.flags)).split(),
                    ('nxscreate onlinecp --component testmymca '
                     ' --xml-package %s '
                     ' %s %s ' % (pname, fname, self.flags)).split(),
                ],
                [
                    ['testmymca'],
                    [
                        'testmymca_data',
                        'testmymca_mode'
                    ],
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <group type="NXentry" name="$var.entryname#\'scan\''
                     '$var.serialno">\n'
                     '    <group type="NXinstrument" name="instrument">\n'
                     '      <group type="NXdetector" name="testmymca">\n'
                     '        <field type="NX_FLOAT64" name="data">'
                     '$datasources.testmymca_data<strategy mode="STEP"/>\n'
                     '        </field>\n'
                     '        <group type="NXcollection" name="collection">\n'
                     '          <field type="NX_FLOAT64" name="mode">'
                     '$datasources.testmymca_mode<strategy mode="INIT"/>\n'
                     '          </field>\n'
                     '        </group>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>\n'],
                    ['<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="testmymca_data">\n'
                     '    <device name="p09/mymca/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="testmymca_"/>\n'
                     '    <record name="Data"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" name="testmymca_mode">\n'
                     '    <device name="p09/mymca/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="testmymca_"/>\n'
                     '    <record name="Mode"/>\n'
                     '  </datasource>\n'
                     '</definition>\n'],
                ],
            ],
        ]
        if os.path.isfile(fname):
            raise Exception("Test file %s exists" % fname)
        with open(fname, "w") as fl:
            fl.write(xml)

        self.checkxmls(args, fname)


if __name__ == '__main__':
    unittest.main()
