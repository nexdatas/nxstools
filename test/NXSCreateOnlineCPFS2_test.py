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
# \file XMLConfigurator_test.py
# unittests for field Tags running Tango Server
#
import unittest
import sys
import shutil
import os


try:
    import NXSCreateOnlineCPFS_test
except Exception:
    from . import NXSCreateOnlineCPFS_test


if sys.version_info > (3,):
    unicode = str
    long = int


# test fixture
class NXSCreateOnlineCPFS2Test(
        NXSCreateOnlineCPFS_test.NXSCreateOnlineCPFSTest):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        NXSCreateOnlineCPFS_test.NXSCreateOnlineCPFSTest.__init__(
            self, methodName)

        self.directory = "my_test_nxs"
        self._dircreated = False
        self.flags = " -d %s " % self.directory
        self.maxDiff = None

    # test starter
    # \brief Common set up
    def setUp(self):
        NXSCreateOnlineCPFS_test.NXSCreateOnlineCPFSTest.setUp(self)
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)
            self._dircreated = True

    # test closer
    # \brief Common tear down
    def tearDown(self):
        NXSCreateOnlineCPFS_test.NXSCreateOnlineCPFSTest.tearDown(self)
        if self._dircreated:
            shutil.rmtree(self.directory)
            self._dircreated = False

    def test_onlinecp_eigerdectris_fileprefix(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fname = '%s/%s%s.xml' % (
            os.getcwd(), self.__class__.__name__, fun)

        xml = """<?xml version='1.0' encoding='utf-8'?>
<hw>
<device>
 <name>myeigerdectris</name>
 <type>type_tango</type>
 <module>eigerdectris</module>
 <device>p09/eigerdectris/exp.01</device>
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
                    ('nxscreate onlinecp -c myeigerdectris -x ts_ '
                     ' %s %s ' % (fname, self.flags)).split(),
                    ('nxscreate onlinecp --file-prefix ts_ '
                     ' --component myeigerdectris '
                     ' %s %s ' % (fname, self.flags)).split(),
                ],
                [
                    ['ts_myeigerdectris'],
                    ['ts_myeigerdectris_autosummationenabled',
                     'ts_myeigerdectris_bitdepth',
                     'ts_myeigerdectris_counttime',
                     'ts_myeigerdectris_description_cb',
                     'ts_myeigerdectris_description',
                     'ts_myeigerdectris_energythreshold',
                     'ts_myeigerdectris_flatfieldenabled',
                     'ts_myeigerdectris_frametime',
                     'ts_myeigerdectris_humidity',
                     'ts_myeigerdectris_nbimages_cb',
                     'ts_myeigerdectris_nbtriggers',
                     'ts_myeigerdectris_photonenergy',
                     'ts_myeigerdectris_ratecorrectionenabled',
                     'ts_myeigerdectris_readouttime',
                     'ts_myeigerdectris_stepindex',
                     'ts_myeigerdectris_temperature',
                     'ts_myeigerdectris_triggermode_cb',
                     'ts_myeigerdectris_triggermode',
                     'ts_myeigerdectris_wavelength'],
                ],
                [
                    ['<?xml version=\'1.0\'?>\n'
                     ''
                     '<definition>\n'
                     '  <group type="NXentry" '
                     'name="$var.entryname#\'scan\'$var.serialno">\n'
                     '    <group type="NXinstrument" name="instrument">\n'
                     '      <group type="NXdetector" name="myeigerdectris">\n'
                     '        <field units="um" type="NX_FLOAT64" '
                     'name="x_pixel_size">75</field>\n'
                     '        <field units="um" type="NX_FLOAT64" '
                     'name="y_pixel_size">75</field>\n'
                     '        <field type="NX_CHAR" name="layout">area'
                     '</field>\n'
                     '        <field type="NX_CHAR" name="description">'
                     '$datasources.myeigerdectris_description_cb'
                     '<strategy mode="INIT"/>\n'
                     '        </field>\n'
                     '        <field type="NX_INT" name="bit_depth_readout">'
                     '$datasources.myeigerdectris_bitdepth<strategy '
                     'mode="FINAL"/>\n'
                     '        </field>\n'
                     '        <field units="s" type="NX_FLOAT64" '
                     'name="detector_readout_time">'
                     '$datasources.myeigerdectris_readouttime'
                     '<strategy mode="FINAL"/>\n'
                     '        </field>\n'
                     '        <field units="s" type="NX_FLOAT64" '
                     'name="count_time">'
                     '$datasources.myeigerdectris_counttime'
                     '<strategy mode="FINAL"/>\n'
                     '        </field>\n'
                     '        <field units="s" type="NX_FLOAT64" '
                     'name="frame_time">$datasources.myeigerdectris_frametime'
                     '<strategy mode="FINAL"/>\n'
                     '        </field>\n'
                     '        <field units="eV" type="NX_FLOAT64" '
                     'name="threshold_energy">'
                     '$datasources.myeigerdectris_energythreshold'
                     '<strategy mode="FINAL"/>\n'
                     '        </field>\n'
                     '        <field type="NX_BOOLEAN" '
                     'name="flatfield_applied">'
                     '$datasources.myeigerdectris_flatfieldenabled'
                     '<strategy mode="FINAL"/>\n'
                     '        </field>\n'
                     '        <field type="NX_BOOLEAN" '
                     'name="countrate_correction_applied">'
                     '$datasources.myeigerdectris_ratecorrectionenabled'
                     '<strategy mode="FINAL"/>\n'
                     '        </field>\n'
                     '        <group type="NXcollection" name="collection">\n'
                     '          <field type="NX_UINT64" name="nb_images">\n'
                     '            <strategy mode="STEP"/>'
                     '$datasources.myeigerdectris_nbimages_cb</field>\n'
                     '          <field type="NX_UINT64" name="nb_triggers">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.myeigerdectris_nbtriggers</field>\n'
                     '          <field type="NX_CHAR" name="triggermode">\n'
                     '            <strategy mode="FINAL"/>'
                     '$datasources.myeigerdectris_triggermode_cb</field>\n'
                     '          <field type="NX_UINT64" name="stepindex">\n'
                     '            <strategy mode="STEP"/>'
                     '$datasources.myeigerdectris_stepindex</field>\n'
                     '          <field type="NX_BOOLEAN" '
                     'name="auto_summation_applied">'
                     '$datasources.myeigerdectris_autosummationenabled'
                     '<strategy mode="FINAL"/>\n'
                     '          </field>\n'
                     '        </group>\n'
                     '      </group>\n'
                     '    </group>\n'
                     '    <group type="NXdata" name="data">\n'
                     '    </group>\n'
                     '  </group>\n'
                     '</definition>\n'],
                    ['<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="myeigerdectris_autosummationenabled"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="AutoSummationEnabled"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="myeigerdectris_bitdepth"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="BitDepth"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="myeigerdectris_counttime"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="CountTime"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" '
                     'name="myeigerdectris_description">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import common\n'
                     'common.blockitem_rm(commonblock, '
                     '["myeigerdectris_stepindex"])\n'
                     'ds.result = ds.myeigerdectris_description\n'
                     '</result>\n'
                     '  $datasources.myeigerdectris_description\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="myeigerdectris_description"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="Description"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="myeigerdectris_energythreshold"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="EnergyThreshold"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="myeigerdectris_flatfieldenabled"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="FlatFieldEnabled"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="myeigerdectris_frametime"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="FrameTime"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="myeigerdectris_humidity"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="Humidity"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL"'
                     ' name="myeigerdectris_nbimages_cb"'
                     '>\n'
                     '    <result name="result">\n'
                     'ds.result = ds.myeigerdectris_nbimages\n'
                     '    </result>\n'
                     '    $datasources.myeigerdectris_nbimages\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="myeigerdectris_nbtriggers"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="NbTriggers"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="myeigerdectris_photonenergy"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="PhotonEnergy"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO" '
                     'name="myeigerdectris_ratecorrectionenabled"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="RateCorrectionEnabled"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="myeigerdectris_readouttime"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="ReadoutTime"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" '
                     'name="myeigerdectris_stepindex">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import common\n'
                     'ds.result = common.blockitem_addint('
                     'commonblock, "myeigerdectris_stepindex", '
                     'ds.myeigerdectris_nbimages)\n'
                     'ds.result = len(commonblock['
                     '"myeigerdectris_stepindex"])\n'
                     '    </result>\n'
                     '    $datasources.myeigerdectris_nbimages\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="myeigerdectris_temperature"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="Temperature"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\'?>\n'
                     '<definition>\n'
                     '  <datasource type="PYEVAL" '
                     'name="myeigerdectris_triggermode_cb">\n'
                     '    <result name="result">\n'
                     'from nxstools.pyeval import eigerdectris\n'
                     'ds.result = eigerdectris.triggermode_cb('
                     'commonblock,'
                     ' "myeigerdectris",'
                     ' ds.myeigerdectris_triggermode,'
                     ' ds.myeigerdectris_nbimages,'
                     ' "haso000:10000",'
                     ' "p09/eigerdectris/exp.01",'
                     ' "$var.filename",'
                     ' "myeigerdectris_stepindex",'
                     ' "$var.entryname#\'scan\'$var.serialno",'
                     ' "instrument",'
                     ' "EigerDectris",'
                     ' "EigerFilewriter"'
                     ')\n'
                     '    </result>\n'
                     '    $datasources.myeigerdectris_triggermode\n'
                     '    $datasources.myeigerdectris_nbimages\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="myeigerdectris_triggermode"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="TriggerMode"/>\n'
                     '  </datasource>\n'
                     '</definition>\n',
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <datasource type="TANGO"'
                     ' name="myeigerdectris_wavelength"'
                     '>\n'
                     '    <device name="p09/eigerdectris/exp.01" '
                     'member="attribute" hostname="haso000" '
                     'port="10000" group="myeigerdectris_"/>\n'
                     '    <record name="Wavelength"/>\n'
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
