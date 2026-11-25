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


try:
    import NXSCreateCompFS2_test
except Exception:
    from . import NXSCreateCompFS2_test


# test fixture
class NXSCreateCompFS3Test(
        NXSCreateCompFS2_test.NXSCreateCompFS2Test):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        NXSCreateCompFS2_test.NXSCreateCompFS2Test.__init__(
            self, methodName)

        self.flags = " --directory %s" % self.directory


if __name__ == '__main__':
    unittest.main()
