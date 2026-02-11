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
    import NXSCreateStdCompFS_test
except Exception:
    from . import NXSCreateStdCompFS_test


if sys.version_info > (3,):
    unicode = str
    long = int


# test fixture
class NXSCreateStdCompFS2Test(
        NXSCreateStdCompFS_test.NXSCreateStdCompFSTest):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        NXSCreateStdCompFS_test.NXSCreateStdCompFSTest.__init__(
            self, methodName)

        self.directory = "my_test_nxs"
        self._dircreated = False
        self.flags = " -r testp09/testmcs/testr228  -d %s" % self.directory

    # test starter
    # \brief Common set up
    def setUp(self):
        NXSCreateStdCompFS_test.NXSCreateStdCompFSTest.setUp(self)
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)
            self._dircreated = True

    # test closer
    # \brief Common tear down
    def tearDown(self):
        NXSCreateStdCompFS_test.NXSCreateStdCompFSTest.tearDown(self)
        if self._dircreated:
            shutil.rmtree(self.directory)
            self._dircreated = False

    def test_stdcomp_beamstop_fileprefix(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate stdcomp  -x test_ -t beamstop -c testbeamstop1 '
                 '%s' % self.flags).split(),
                [
                    ['test_testbeamstop1'],
                    []
                ],
                [
                    ['<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
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
                ('nxscreate stdcomp  --file-prefix test_ --type beamstop '
                 '--component testbeamstop2 %s' %
                 self.flags).split(),
                [
                    ['test_testbeamstop2'],
                    []
                ],
                [
                    ['<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
                     '<definition>\n'
                     '  <group name="$var.entryname#\'scan\'$var.serialno" '
                     'type="NXentry">\n'
                     '    <group name="instrument" type="NXinstrument">\n'
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
        ]

        self.checkxmls(args)

    def test_stdcomp_absorber_file_prefix(self):
        """ test nxsccreate stdcomp file system
        """
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        args = [
            [
                ('nxscreate stdcomp -t absorber -c absorber1 -x tst_ '
                 ' position mot01 '
                 ' %s' % self.flags).split(),
                [
                    ['tst_absorber1'],
                    ['tst_absorber1_foil', 'tst_absorber1_thickness']
                ],
                [
                    ['<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
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
                    ['<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
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
                     '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n'
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
                 ' --file-prefix tst_ '
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
                    ['tst_absorber1'],
                    ['tst_absorber1_foil', 'tst_absorber1_thickness']
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


if __name__ == '__main__':
    unittest.main()
