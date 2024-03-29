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
# \file ElementTest.py
# unittests for field Tags running Tango Server
#
import unittest
import os
import sys
import struct
import random
import binascii
import string
import time

import nxstools.filewriter as FileWriter
import nxstools.h5cppwriter as H5CppWriter
from pninexus import h5cpp
# import h5py


# if 64-bit machione
IS64BIT = (struct.calcsize("P") == 8)

if sys.version_info > (3,):
    long = int


class testwriter(object):
    def __init__(self):
        self.commands = []
        self.params = []
        self.result = None

    def open_file(self, filename, readonly=False, libver=None):
        """ open the new file
        """
        self.commands.append("open_file")
        self.params.append([filename, readonly, libver])
        return self.result

    def create_file(self, filename, overwrite=False, libver=None):
        """ create a new file
        """
        self.commands.append("create_file")
        self.params.append([filename, overwrite, libver])
        return self.result

    def link(self, target, parent, name):
        """ create link
        """
        self.commands.append("link")
        self.params.append([target, parent, name])
        return self.result

    def data_filter(self):
        self.commands.append("data_filter")
        self.params.append([])
        return self.result


class FTCloser(FileWriter.FTObject):

    def __init__(self, h5object, tparent=None):
        FileWriter.FTObject.__init__(self, h5object, tparent)
        self.commands = []
        self._is_valid = True

    def close(self):
        """ close the new file
        """
        self.commands.append("close")
        self._is_valid = False
        FileWriter.FTObject.close(self)

    def reopen(self):
        """ reopen the new file
        """
        self.commands.append("reopen")
        self._is_valid = True
        self._reopen()

    def create(self):
        self.commands.append("create")
        return FTCloser(self.commands, self)

    @property
    def is_valid(self):
        """ check if field is valid

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        return self._is_valid


def createClass(classname, basecls=FileWriter.FTObject):

    def __init__(self, h5object, tparent=None):
        basecls.__init__(self, h5object, tparent)
        self.commands = []
        self._is_valid = True

    def close(self):
        """ close the new file
        """
        self.commands.append("close")
        self._is_valid = False
        basecls.close(self)

    def reopen(self):
        """ reopen the new file
        """
        basecls.reopen(self)
        self.commands.append("reopen")
        self._is_valid = True

    def create(self, objectclass):
        self.commands.append("create")
        return objectclass(self.commands, self)

    @property
    def is_valid(self):
        return self._is_valid

    newclass = type(
        classname, (basecls,),
        {
            "__init__": __init__,
            "close": close,
            "reopen": reopen,
            "create": create,
            "is_valid": is_valid
        }
    )
    return newclass


TAttribute = createClass("TAttribute", FileWriter.FTAttribute)
TGroup = createClass("TGroup", FileWriter.FTGroup)
TFile = createClass("TFile", FileWriter.FTFile)
TField = createClass("TField", FileWriter.FTField)
TAttributeManager = createClass(
    "TAttributeManager", FileWriter.FTAttributeManager)
TLink = createClass("TLink", FileWriter.FTLink)


# test fixture
class FileWriterH5CppTest(unittest.TestCase):

    # constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

        try:
            self.__seed = long(binascii.hexlify(os.urandom(16)), 16)
        except NotImplementedError:
            self.__seed = long(time.time() * 256)
#        self.__seed =241361343400098333007607831038323262554

        self.__rnd = random.Random(self.__seed)

    # test starter
    # \brief Common set up
    def setUp(self):
        print("\nsetting up...")
        print("SEED = %s" % self.__seed)

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
                            print(
                                "EL %s %s %s" % (
                                    image1[i][j][k], image2[i][j][k], error))
                        self.assertTrue(
                            abs(image1[i][j][k] - image2[i][j][k]) < error)
                    else:
                        self.assertEqual(image1[i][j][k], image2[i][j][k])

    # constructor test
    # \brief It tests default settings
    def test_constructor(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        w = "weerew"
        el = FileWriter.FTObject(w)

        self.assertEqual(el.h5object, w)

    # test
    # \brief It tests default settings
    def test_openfile(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        tw = testwriter()
        FileWriter.writer = tw
        for _ in range(10):
            res = self.__rnd.randint(1, 10)
            tw.result = res
            chars = string.ascii_uppercase + string.digits
            fn = ''.join(self.__rnd.choice(chars) for _ in range(res))
            tres = FileWriter.open_file(fn)
            self.assertEqual(tres, res)
            self.assertEqual(tw.commands[-1], "open_file")
            self.assertEqual(tw.params[-1], [fn, False, None])
        for _ in range(10):
            res = self.__rnd.randint(1, 10)
            tw.result = res
            chars = string.ascii_uppercase + string.digits
            fn = ''.join(self.__rnd.choice(chars) for _ in range(res))
            rb = bool(self.__rnd.randint(0, 1))
            tres = FileWriter.open_file(fn, rb)
            self.assertEqual(tres, res)
            self.assertEqual(tw.commands[-1], "open_file")
            self.assertEqual(tw.params[-1], [fn, rb, None])

    # test
    # \brief It tests default settings
    def test_createfile(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        tw = testwriter()
        FileWriter.writer = tw
        for _ in range(10):
            res = self.__rnd.randint(1, 10)
            tw.result = res
            chars = string.ascii_uppercase + string.digits
            fn = ''.join(self.__rnd.choice(chars) for _ in range(res))
            tres = FileWriter.create_file(fn)
            self.assertEqual(tres, res)
            self.assertEqual(tw.commands[-1], "create_file")
            self.assertEqual(tw.params[-1], [fn, False, None])
        for _ in range(10):
            res = self.__rnd.randint(1, 10)
            tw.result = res
            chars = string.ascii_uppercase + string.digits
            fn = ''.join(self.__rnd.choice(chars) for _ in range(res))
            rb = bool(self.__rnd.randint(0, 1))
            tres = FileWriter.create_file(fn, rb)
            self.assertEqual(tres, res)
            self.assertEqual(tw.commands[-1], "create_file")
            self.assertEqual(tw.params[-1], [fn, rb, None])

    # test
    # \brief It tests default settings
    def test_link(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        tw = testwriter()
        FileWriter.writer = tw
        for _ in range(10):
            res = self.__rnd.randint(1, 10)
            tw.result = res
            chars = string.ascii_uppercase + string.digits
            fn = ''.join(self.__rnd.choice(chars) for _ in range(res))
            fn2 = ''.join(self.__rnd.choice(chars) for _ in range(res * 2))
            fn3 = ''.join(self.__rnd.choice(chars) for _ in range(res * 3))
            tres = FileWriter.link(fn, fn2, fn3)
            self.assertEqual(tres, res)
            self.assertEqual(tw.commands[-1], "link")
            self.assertEqual(tw.params[-1], [fn, fn2, fn3])
            self.assertEqual(tres, res)

    # test
    # \brief It tests default settings
    def test_data_filter(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        tw = testwriter()
        FileWriter.writer = tw
        for _ in range(10):
            res = self.__rnd.randint(1, 10)
            tw.result = res
            tres = FileWriter.data_filter()
            self.assertEqual(tres, res)
            self.assertEqual(tw.commands[-1], "data_filter")
            self.assertEqual(tw.params[-1], [])
            self.assertEqual(tres, res)

    # default createfile test
    # \brief It tests default settings
    def test_default_createfile_h5cpp(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        self._fname = '%s/%s%s.h5' % (
            os.getcwd(), self.__class__.__name__, fun)
        try:
            FileWriter.writer = H5CppWriter
            fl = FileWriter.create_file(self._fname)
            fl.close()
            fl = FileWriter.create_file(self._fname, True)
            fl.close()

            fl = H5CppWriter.open_file(self._fname, readonly=True)
            f = fl.root()
            self.assertEqual(5, len(f.attributes))
            self.assertEqual(
                f.attributes["file_name"][...],
                self._fname)
            self.assertTrue(f.attributes["NX_class"][...], "NXroot")
            self.assertEqual(f.size, 0)
            f.close()
            fl.close()

            fl = FileWriter.open_file(self._fname, readonly=True)
            f = fl.root()
            self.assertEqual(5, len(f.attributes))
            self.assertEqual(
                f.attributes["file_name"][...],
                self._fname)
            self.assertTrue(f.attributes["NX_class"][...], "NXroot")
            self.assertEqual(f.size, 0)
            fl.close()
            fl.reopen()
            self.assertEqual(5, len(f.attributes))
            # atts = []
            for at in f.attributes:
                print("%s %s %s" % (at.name, at.read(), at.dtype))
            self.assertEqual(
                f.attributes["file_name"][...],
                self._fname)
            self.assertTrue(f.attributes["NX_class"][...], "NXroot")
            self.assertEqual(f.size, 0)
            fl.close()

            self.myAssertRaise(
                Exception, FileWriter.create_file, self._fname)

            self.myAssertRaise(
                Exception, FileWriter.create_file, self._fname,
                False)

            fl2 = FileWriter.create_file(self._fname, True)
            fl2.close()

        finally:
            os.remove(self._fname)

    # default createfile test
    # \brief It tests default settings
    def test_ftobject(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fto = FileWriter.FTObject(None)
        self.assertEqual(fto._h5object, None)
        self.assertEqual(fto.h5object, None)
        self.assertEqual(fto._tparent, None)
        self.assertEqual(fto.parent, None)
        self.assertEqual(fto.is_valid, True)
        fto2 = FileWriter.FTObject(fto)
        self.assertEqual(fto2._h5object, fto)
        self.assertEqual(fto2.h5object, fto)
        self.assertEqual(fto2._tparent, None)
        self.assertEqual(fto2.parent, None)
        self.assertEqual(fto.is_valid, True)
        fto3 = FileWriter.FTObject(fto2, fto)
        self.assertEqual(fto3._h5object, fto2)
        self.assertEqual(fto3.h5object, fto2)
        self.assertEqual(fto3._tparent, fto)
        self.assertEqual(fto3.parent, fto)
        self.assertEqual(fto.is_valid, True)

    # default createfile test
    # \brief It tests default settings
    def test_ftcloser(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fto = FTCloser(None)
        self.assertEqual(fto._h5object, None)
        self.assertEqual(fto.h5object, None)
        self.assertEqual(fto._tparent, None)
        self.assertEqual(fto.parent, None)
        self.assertEqual(fto.is_valid, True)
        fto2 = fto.create()
        self.assertEqual(fto2._h5object, fto.commands)
        self.assertEqual(fto2.h5object, fto.commands)
        self.assertEqual(fto2._tparent, fto)
        self.assertEqual(fto2.parent, fto)
        self.assertEqual(fto.is_valid, True)
        fto3 = fto2.create()
        self.assertEqual(fto3._h5object, fto2.commands)
        self.assertEqual(fto3.h5object, fto2.commands)
        self.assertEqual(fto3._tparent, fto2)
        self.assertEqual(fto3.parent, fto2)
        self.assertEqual(fto.is_valid, True)
        fto4 = fto2.create()
        self.assertEqual(fto4._h5object, fto2.commands)
        self.assertEqual(fto4.h5object, fto2.commands)
        self.assertEqual(fto4._tparent, fto2)
        self.assertEqual(fto4.parent, fto2)
        self.assertEqual(fto.is_valid, True)

        self.assertEqual(fto.commands, ['create'])
        self.assertEqual(fto2.commands, ['create', 'create'])
        self.assertEqual(fto3.commands, [])
        self.assertEqual(fto4.commands, [])
        self.assertEqual(fto.is_valid, True)
        self.assertEqual(fto2.is_valid, True)
        self.assertEqual(fto3.is_valid, True)
        self.assertEqual(fto4.is_valid, True)
        fto.close()
        self.assertEqual(fto.commands, ['create', 'close'])
        self.assertEqual(fto2.commands, ['create', 'create', 'close'])
        self.assertEqual(fto3.commands, ['close'])
        self.assertEqual(fto4.commands, ['close'])
        self.assertEqual(fto.is_valid, False)
        self.assertEqual(fto2.is_valid, False)
        self.assertEqual(fto3.is_valid, False)
        self.assertEqual(fto4.is_valid, False)
        fto.reopen()
        self.assertEqual(fto.commands, ['create', 'close', 'reopen'])
        self.assertEqual(fto2.commands,
                         ['create', 'create', 'close', 'reopen'])
        self.assertEqual(fto3.commands, ['close', 'reopen'])
        self.assertEqual(fto4.commands, ['close', 'reopen'])
        self.assertEqual(fto.is_valid, True)
        self.assertEqual(fto2.is_valid, True)
        self.assertEqual(fto3.is_valid, True)
        self.assertEqual(fto4.is_valid, True)

    # default createfile test
    # \brief It tests default settings
    def test_ftobjects(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))

        fto = FileWriter.FTObject(None)
        self.assertEqual(fto.is_valid, True)
        self.assertEqual(fto.h5object, None)
        self.assertEqual(fto.parent, None)
        self.assertEqual(fto.is_valid, True)

        tf = TFile(fto, "myfile.txt")
        self.assertEqual(tf.is_valid, True)
        self.assertEqual(tf.h5object, fto)
        self.assertEqual(tf.parent, None)
        self.assertEqual(tf.is_valid, True)
        self.assertEqual(tf.name, "myfile.txt")
        self.assertTrue(hasattr(tf.root, "__call__"))
        self.assertTrue(hasattr(tf.flush, "__call__"))
        self.assertTrue(hasattr(tf, "readonly"))
        self.assertTrue(hasattr(tf.reopen, "__call__"))

        ta = tf.create(TAttribute)
        self.assertEqual(ta._h5object, tf.commands)
        self.assertEqual(ta.h5object, tf.commands)
        self.assertEqual(ta._tparent, tf)
        self.assertEqual(ta.parent, tf)
        self.assertEqual(ta.is_valid, True)
        self.assertTrue(hasattr(ta.read, "__call__"))
        self.assertTrue(hasattr(ta.write, "__call__"))
        self.assertTrue(hasattr(ta.__setitem__, "__call__"))
        self.assertTrue(hasattr(ta.__getitem__, "__call__"))
        self.assertTrue(hasattr(ta, "dtype"))
        self.assertTrue(hasattr(ta, "shape"))
        self.assertTrue(hasattr(ta.reopen, "__call__"))

        tg = tf.create(TGroup)
        self.assertEqual(tg._h5object, tf.commands)
        self.assertEqual(tg.h5object, tf.commands)
        self.assertEqual(tg._tparent, tf)
        self.assertEqual(tg.parent, tf)
        self.assertEqual(tg.is_valid, True)
        self.assertTrue(hasattr(tg.open, "__call__"))
        self.assertTrue(hasattr(tg.create_group, "__call__"))
        self.assertTrue(hasattr(tg.create_field, "__call__"))
        self.assertTrue(hasattr(tg, "size"))
        self.assertTrue(hasattr(tg, "parent"))
        self.assertTrue(hasattr(tg, "attributes"))
        self.assertTrue(hasattr(tg.exists, "__call__"))
        self.assertTrue(hasattr(tg.reopen, "__call__"))

        td = tf.create(TField)
        self.assertEqual(td._h5object, tf.commands)
        self.assertEqual(td.h5object, tf.commands)
        self.assertEqual(td._tparent, tf)
        self.assertEqual(td.parent, tf)
        self.assertEqual(td.is_valid, True)
        self.assertTrue(hasattr(td, "attributes"))
        self.assertTrue(hasattr(td.grow, "__call__"))
        self.assertTrue(hasattr(td.read, "__call__"))
        self.assertTrue(hasattr(td.write, "__call__"))
        self.assertTrue(hasattr(td.__setitem__, "__call__"))
        self.assertTrue(hasattr(td.__getitem__, "__call__"))
        self.assertTrue(hasattr(td, "dtype"))
        self.assertTrue(hasattr(td, "shape"))
        self.assertTrue(hasattr(td, "size"))
        self.assertTrue(hasattr(td, "parent"))
        self.assertTrue(hasattr(td.reopen, "__call__"))

        td2 = tg.create(TField)
        self.assertEqual(td2._h5object, tg.commands)
        self.assertEqual(td2.h5object, tg.commands)
        self.assertEqual(td2._tparent, tg)
        self.assertEqual(td2.parent, tg)
        self.assertEqual(td2.is_valid, True)

        tl = tf.create(TLink)
        self.assertEqual(tl._h5object, tf.commands)
        self.assertEqual(tl.h5object, tf.commands)
        self.assertEqual(tl._tparent, tf)
        self.assertEqual(tl.parent, tf)
        self.assertEqual(tl.is_valid, True)

        tm = tg.create(TAttributeManager)
        self.assertEqual(tm._h5object, tg.commands)
        self.assertEqual(tm.h5object, tg.commands)
        self.assertEqual(tm._tparent, tg)
        self.assertEqual(tm.parent, tg)
        self.assertEqual(tm.is_valid, True)

        ta2 = tg.create(TAttribute)
        self.assertEqual(ta2._h5object, tg.commands)
        self.assertEqual(ta2.h5object, tg.commands)
        self.assertEqual(ta2._tparent, tg)
        self.assertEqual(ta2.parent, tg)
        self.assertEqual(ta2.is_valid, True)

        self.assertTrue(isinstance(tf, FileWriter.FTObject))
        self.assertTrue(isinstance(tf, FileWriter.FTFile))
        self.assertEqual(tf.is_valid, True)
        self.assertEqual(tf.h5object, fto)
        self.assertEqual(tf.parent, None)
        self.assertEqual(tf.commands, ['create', 'create', 'create', 'create'])

        self.assertTrue(isinstance(ta, FileWriter.FTObject))
        self.assertTrue(isinstance(ta, FileWriter.FTAttribute))
        self.assertEqual(ta.is_valid, True)
        self.assertEqual(ta.h5object, tf.commands)
        self.assertEqual(ta.parent, tf)
        self.assertEqual(ta.commands, [])

        self.assertTrue(isinstance(td, FileWriter.FTObject))
        self.assertTrue(isinstance(td, FileWriter.FTField))
        self.assertEqual(td.is_valid, True)
        self.assertEqual(td.h5object, tf.commands)
        self.assertEqual(td.parent, tf)
        self.assertEqual(td.commands, [])

        self.assertTrue(isinstance(tl, FileWriter.FTObject))
        self.assertTrue(isinstance(tl, FileWriter.FTLink))
        self.assertEqual(tl.is_valid, True)
        self.assertEqual(tl.h5object, tf.commands)
        self.assertEqual(tl.parent, tf)
        self.assertEqual(tl.commands, [])

        self.assertTrue(isinstance(tg, FileWriter.FTObject))
        self.assertTrue(isinstance(tg, FileWriter.FTGroup))
        self.assertEqual(tg.is_valid, True)
        self.assertEqual(tg.h5object, tf.commands)
        self.assertEqual(tg.parent, tf)
        self.assertEqual(tg.commands, ['create', 'create', 'create'])

        self.assertTrue(isinstance(td2, FileWriter.FTObject))
        self.assertTrue(isinstance(td2, FileWriter.FTField))
        self.assertEqual(td2.is_valid, True)
        self.assertEqual(td2.h5object, tg.commands)
        self.assertEqual(td2.parent, tg)
        self.assertEqual(td2.commands, [])

        self.assertTrue(isinstance(tm, FileWriter.FTObject))
        self.assertTrue(isinstance(tm, FileWriter.FTAttributeManager))
        self.assertEqual(tm.is_valid, True)
        self.assertEqual(tm.h5object, tg.commands)
        self.assertEqual(tm.parent, tg)
        self.assertEqual(tm.commands, [])

        self.assertTrue(isinstance(ta2, FileWriter.FTObject))
        self.assertTrue(isinstance(ta2, FileWriter.FTAttribute))
        self.assertEqual(ta2.is_valid, True)
        self.assertEqual(ta2.h5object, tg.commands)
        self.assertEqual(ta2.parent, tg)
        self.assertEqual(ta2.commands, [])

        tf.close()

        self.assertTrue(isinstance(tf, FileWriter.FTObject))
        self.assertTrue(isinstance(tf, FileWriter.FTFile))
        self.assertEqual(tf.is_valid, False)
        self.assertEqual(tf.h5object, fto)
        self.assertEqual(tf.parent, None)
        self.assertEqual(
            tf.commands,
            ['create', 'create', 'create', 'create', 'close'])

        self.assertTrue(isinstance(ta, FileWriter.FTObject))
        self.assertTrue(isinstance(ta, FileWriter.FTAttribute))
        self.assertEqual(ta.is_valid, False)
        self.assertEqual(ta.h5object, tf.commands)
        self.assertEqual(ta.parent, tf)
        self.assertEqual(ta.commands, ['close'])

        self.assertTrue(isinstance(td, FileWriter.FTObject))
        self.assertTrue(isinstance(td, FileWriter.FTField))
        self.assertEqual(td.is_valid, False)
        self.assertEqual(td.h5object, tf.commands)
        self.assertEqual(td.parent, tf)
        self.assertEqual(td.commands, ['close'])

        self.assertTrue(isinstance(tl, FileWriter.FTObject))
        self.assertTrue(isinstance(tl, FileWriter.FTLink))
        self.assertEqual(tl.is_valid, False)
        self.assertEqual(tl.h5object, tf.commands)
        self.assertEqual(tl.parent, tf)
        self.assertEqual(tl.commands, ['close'])

        self.assertTrue(isinstance(tg, FileWriter.FTObject))
        self.assertTrue(isinstance(tg, FileWriter.FTGroup))
        self.assertEqual(tg.is_valid, False)
        self.assertEqual(tg.h5object, tf.commands)
        self.assertEqual(tg.parent, tf)
        self.assertEqual(
            tg.commands, ['create', 'create', 'create', 'close'])

        self.assertTrue(isinstance(td2, FileWriter.FTObject))
        self.assertTrue(isinstance(td2, FileWriter.FTField))
        self.assertEqual(td2.is_valid, False)
        self.assertEqual(td2.h5object, tg.commands)
        self.assertEqual(td2.parent, tg)
        self.assertEqual(td2.commands, ['close'])

        self.assertTrue(isinstance(tm, FileWriter.FTObject))
        self.assertTrue(isinstance(tm, FileWriter.FTAttributeManager))
        self.assertEqual(tm.is_valid, False)
        self.assertEqual(tm.h5object, tg.commands)
        self.assertEqual(tm.parent, tg)
        self.assertEqual(tm.commands, ['close'])

        self.assertTrue(isinstance(ta2, FileWriter.FTObject))
        self.assertTrue(isinstance(ta2, FileWriter.FTAttribute))
        self.assertEqual(ta2.is_valid, False)
        self.assertEqual(ta2.h5object, tg.commands)
        self.assertEqual(ta2.parent, tg)
        self.assertEqual(ta2.commands, ['close'])

        tf.reopen()

        self.assertTrue(isinstance(tf, FileWriter.FTObject))
        self.assertTrue(isinstance(tf, FileWriter.FTFile))
        self.assertEqual(tf.is_valid, True)
        self.assertEqual(tf.h5object, fto)
        self.assertEqual(tf.parent, None)
        self.assertEqual(
            tf.commands,
            ['create', 'create', 'create', 'create', 'close', 'reopen'])

        self.assertTrue(isinstance(ta, FileWriter.FTObject))
        self.assertTrue(isinstance(ta, FileWriter.FTAttribute))
        self.assertEqual(ta.is_valid, True)
        self.assertEqual(ta.h5object, tf.commands)
        self.assertEqual(ta.parent, tf)
        self.assertEqual(ta.commands, ['close', 'reopen'])

        self.assertTrue(isinstance(td, FileWriter.FTObject))
        self.assertTrue(isinstance(td, FileWriter.FTField))
        self.assertEqual(td.is_valid, True)
        self.assertEqual(td.h5object, tf.commands)
        self.assertEqual(td.parent, tf)
        self.assertEqual(td.commands, ['close', 'reopen'])

        self.assertTrue(isinstance(tl, FileWriter.FTObject))
        self.assertTrue(isinstance(tl, FileWriter.FTLink))
        self.assertEqual(tl.is_valid, True)
        self.assertEqual(tl.h5object, tf.commands)
        self.assertEqual(tl.parent, tf)
        self.assertEqual(tl.commands, ['close', 'reopen'])

        self.assertTrue(isinstance(tg, FileWriter.FTObject))
        self.assertTrue(isinstance(tg, FileWriter.FTGroup))
        self.assertEqual(tg.is_valid, True)
        self.assertEqual(tg.h5object, tf.commands)
        self.assertEqual(tg.parent, tf)
        self.assertEqual(
            tg.commands, ['create', 'create', 'create', 'close', 'reopen'])

        self.assertTrue(isinstance(td2, FileWriter.FTObject))
        self.assertTrue(isinstance(td2, FileWriter.FTField))
        self.assertEqual(td2.is_valid, True)
        self.assertEqual(td2.h5object, tg.commands)
        self.assertEqual(td2.parent, tg)
        self.assertEqual(td2.commands, ['close', 'reopen'])

        self.assertTrue(isinstance(tm, FileWriter.FTObject))
        self.assertTrue(isinstance(tm, FileWriter.FTAttributeManager))
        self.assertEqual(tm.is_valid, True)
        self.assertEqual(tm.h5object, tg.commands)
        self.assertEqual(tm.parent, tg)
        self.assertEqual(tm.commands, ['close', 'reopen'])

        self.assertTrue(isinstance(ta2, FileWriter.FTObject))
        self.assertTrue(isinstance(ta2, FileWriter.FTAttribute))
        self.assertEqual(ta2.is_valid, True)
        self.assertEqual(ta2.h5object, tg.commands)
        self.assertEqual(ta2.parent, tg)
        self.assertEqual(ta2.commands, ['close', 'reopen'])

    # default createfile test
    # \brief It tests default settings
    def test_h5cppfile(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        self._fname = '%s/%s%s.h5' % (
            os.getcwd(), self.__class__.__name__, fun)

        # overwrite = False

        try:
            FileWriter.writer = H5CppWriter
            fl = FileWriter.create_file(self._fname)
            self.assertTrue(
                isinstance(fl, FileWriter.FTFile))

            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)

            rt = fl.root()
            fl.flush()
            print(dir(fl.h5object.root()))
            self.assertEqual(
                fl.h5object.root().link.path,
                rt.h5object.link.path)
            self.assertEqual(
                len(fl.h5object.root().attributes),
                len(rt.h5object.attributes))
            self.assertEqual(fl.is_valid, True)
            self.assertEqual(
                fl.h5object.root().link.path.name is not None, True)
            self.assertEqual(fl.readonly, False)
            self.assertEqual(fl.readonly, False)
            self.assertEqual(
                fl.h5object.intent == h5cpp.file.AccessFlags.READONLY, False)
            rt.close()
            fl.close()
            self.assertEqual(fl.is_valid, False)
            self.assertEqual(fl.readonly, None)

            fl.reopen()
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, False)
            self.assertEqual(
                fl.h5object.intent == h5cpp.file.AccessFlags.READONLY, False)
            fl.close()

            fl.reopen(True)
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, True)
            self.assertEqual(fl.readonly, True)
            self.assertEqual(
                fl.h5object.intent == h5cpp.file.AccessFlags.READONLY, True)

            fl.close()

            #            self.myAssertRaise(
            #                Exception, fl.reopen, True, True)
            # self.myAssertRaise(
            #    Exception, fl.reopen, False, True)

            fl = H5CppWriter.open_file(self._fname, readonly=True)
            f = fl.root()
            self.assertEqual(5, len(f.attributes))
            # atts = []
            for at in f.attributes:
                print("%s %s %s" % (at.name, at.read(), at.dtype))
            self.assertEqual(
                f.attributes["file_name"][...],
                self._fname)
            self.assertTrue(
                f.attributes["NX_class"][...], "NXroot")
            self.assertEqual(f.size, 0)
            fl.close()
        finally:
            os.remove(self._fname)

    # default createfile test
    # \brief It tests default settings
    def test_h5cppgroup(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        self._fname = '%s/%s%s.h5' % (
            os.getcwd(), self.__class__.__name__, fun)

        try:
            # overwrite = False
            FileWriter.writer = H5CppWriter
            fl = FileWriter.create_file(self._fname)

            rt = fl.root()
            nt = rt.create_group("notype")
            entry = rt.create_group("entry12345", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("detector", "NXdetector")
            dt = entry.create_group("data", "NXdata")

            df0 = FileWriter.data_filter()
            df1 = FileWriter.data_filter()
            df1.rate = 2
            df2 = FileWriter.data_filter()
            df2.rate = 4
            df2.shuffle = 6

            strscalar = entry.create_field("strscalar", "string")
            floatscalar = entry.create_field("floatscalar", "float64")
            intscalar = entry.create_field("intscalar", "uint64")
            strspec = ins.create_field("strspec", "string", [10], [6])
            floatspec = ins.create_field("floatspec", "float32", [20], [16])
            intspec = ins.create_field("intspec", "int64", [30], [5])
            strimage = det.create_field("strimage", "string", [2, 2], [2, 1])
            floatimage = det.create_field(
                "floatimage", "float64", [20, 10], dfilter=df0)
            intimage = det.create_field("intimage", "uint32", [0, 30], [1, 30])
            strvec = det.create_field("strvec", "string", [0, 2, 2], [1, 2, 2])
            floatvec = det.create_field(
                "floatvec", "float64", [1, 20, 10], [1, 10, 10], dfilter=df1)
            intvec = det.create_field(
                "intvec", "uint32", [0, 2, 30], dfilter=df2)

            lkintimage = FileWriter.link(
                "/entry12345/instrument/detector/intimage", dt, "lkintimage")
            lkfloatvec = FileWriter.link(
                "/entry12345/instrument/detector/floatvec", dt, "lkfloatvec")
            lkintspec = FileWriter.link(
                "/entry12345/instrument/intspec", dt, "lkintspec")
            lkdet = FileWriter.link(
                "/entry12345/instrument/detector", dt, "lkdet")
            lkno = FileWriter.link(
                "/notype/unknown", dt, "lkno")

            attr0 = rt.attributes
            attr1 = entry.attributes

            print(attr0.h5object)
            self.assertTrue(
                isinstance(attr0, H5CppWriter.H5CppAttributeManager))
            print(type(attr0.h5object))
            self.assertTrue(
                isinstance(attr0.h5object, h5cpp._attribute.AttributeManager))
            self.assertTrue(
                isinstance(attr1, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attr1.h5object, h5cpp._attribute.AttributeManager))

            print(dir(rt))
            self.assertTrue(
                isinstance(rt, H5CppWriter.H5CppGroup))
            self.assertEqual(rt.name, ".")
            #           self.assertEqual(rt.name, "/")
            self.assertEqual(rt.path, "/")
            attr = rt.attributes
            self.assertEqual(attr["NX_class"][...], "NXroot")
            self.assertTrue(
                isinstance(attr, H5CppWriter.H5CppAttributeManager))
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(rt.parent, fl)
            self.assertEqual(rt.size, 2)
            self.assertEqual(rt.exists("entry12345"), True)
            self.assertEqual(rt.exists("notype"), True)
            self.assertEqual(rt.exists("strument"), False)

            for rr in rt:
                print(rr.name)

            self.assertTrue(
                isinstance(entry, H5CppWriter.H5CppGroup))
            self.assertEqual(entry.name, "entry12345")
            self.assertEqual(entry.path, "/entry12345:NXentry")
            self.assertEqual(
                len(entry.h5object.attributes), 1)
            attr = entry.attributes
            self.assertEqual(attr["NX_class"][...], "NXentry")
            self.assertTrue(
                isinstance(attr, H5CppWriter.H5CppAttributeManager))
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(entry.parent, rt)
            self.assertEqual(entry.size, 5)
            self.assertEqual(entry.exists("instrument"), True)
            self.assertEqual(entry.exists("data"), True)
            self.assertEqual(entry.exists("floatscalar"), True)
            self.assertEqual(entry.exists("intscalar"), True)
            self.assertEqual(entry.exists("strscalar"), True)
            self.assertEqual(entry.exists("strument"), False)

            self.assertTrue(
                isinstance(nt, H5CppWriter.H5CppGroup))
            self.assertEqual(nt.name, "notype")
            self.assertEqual(nt.path, "/notype")
            self.assertEqual(
                len(nt.h5object.attributes), 0)
            attr = nt.attributes
            self.assertTrue(
                isinstance(attr, H5CppWriter.H5CppAttributeManager))
            self.assertEqual(nt.is_valid, True)
            self.assertEqual(nt.parent, rt)
            self.assertEqual(nt.size, 0)
            self.assertEqual(nt.exists("strument"), False)

            self.assertTrue(
                isinstance(ins, H5CppWriter.H5CppGroup))
            self.assertEqual(ins.name, "instrument")
            self.assertEqual(
                ins.path, "/entry12345:NXentry/instrument:NXinstrument")
            self.assertEqual(
                len(ins.h5object.attributes), 1)
            attr = ins.attributes
            self.assertEqual(attr["NX_class"][...], "NXinstrument")
            self.assertTrue(
                isinstance(attr, H5CppWriter.H5CppAttributeManager))
            self.assertEqual(ins.is_valid, True)
            self.assertEqual(ins.parent, entry)
            self.assertEqual(ins.size, 4)
            self.assertEqual(ins.exists("detector"), True)
            self.assertEqual(ins.exists("floatspec"), True)
            self.assertEqual(ins.exists("intspec"), True)
            self.assertEqual(ins.exists("strspec"), True)
            self.assertEqual(ins.exists("strument"), False)

            kids = set()
            for en in ins:
                kids.add(en.name)

            self.assertEqual(kids, set(["detector", "floatspec",
                                        "intspec", "strspec"]))

            ins_op = entry.open("instrument")
            self.assertTrue(
                isinstance(ins_op, H5CppWriter.H5CppGroup))
            self.assertEqual(ins_op.name, "instrument")
            self.assertEqual(
                ins_op.path, "/entry12345:NXentry/instrument:NXinstrument")
            self.assertEqual(
                len(ins_op.h5object.attributes), 1)
            attr = ins_op.attributes
            self.assertEqual(attr["NX_class"][...], "NXinstrument")
            self.assertTrue(
                isinstance(attr, H5CppWriter.H5CppAttributeManager))
            self.assertEqual(ins_op.is_valid, True)
            self.assertEqual(ins_op.parent, entry)
            self.assertEqual(ins_op.size, 4)
            self.assertEqual(ins_op.exists("detector"), True)
            self.assertEqual(ins_op.exists("floatspec"), True)
            self.assertEqual(ins_op.exists("intspec"), True)
            self.assertEqual(ins_op.exists("strspec"), True)
            self.assertEqual(ins_op.exists("strument"), False)

            kids = set()
            for en in ins_op:
                kids.add(en.name)

            self.assertEqual(kids, set(["detector", "floatspec",
                                        "intspec", "strspec"]))

            ins_lk = entry.open_link("instrument")
            self.assertTrue(
                isinstance(ins_lk, H5CppWriter.H5CppLink))
            self.assertEqual(ins_lk.name, "instrument")
            self.assertEqual(
                ins_lk.path, "/entry12345:NXentry/instrument")
            self.assertEqual(ins_lk.is_valid, True)
            self.assertEqual(ins_lk.parent, entry)

            self.assertTrue(
                isinstance(det, H5CppWriter.H5CppGroup))
            self.assertEqual(det.name, "detector")
            self.assertEqual(
                det.path,
                "/entry12345:NXentry/instrument:NXinstrument/"
                "detector:NXdetector")
            self.assertEqual(
                len(det.h5object.attributes), 1)
            attr = det.attributes
            self.assertEqual(attr["NX_class"][...], "NXdetector")
            self.assertTrue(
                isinstance(attr, H5CppWriter.H5CppAttributeManager))
            self.assertEqual(det.is_valid, True)
            self.assertEqual(det.parent, ins)
            self.assertEqual(det.size, 6)
            self.assertEqual(det.exists("strimage"), True)
            self.assertEqual(det.exists("intvec"), True)
            self.assertEqual(det.exists("floatimage"), True)
            self.assertEqual(det.exists("floatvec"), True)
            self.assertEqual(det.exists("intimage"), True)
            self.assertEqual(det.exists("strvec"), True)
            self.assertEqual(det.exists("strument"), False)

            kids = set()
            for en in det:
                kids.add(en.name)
            print(kids)

            self.assertEqual(
                kids,
                set(['strimage', 'intvec', 'floatimage',
                     'floatvec', 'intimage', 'strvec']))

            self.assertTrue(isinstance(strscalar, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(strscalar.h5object, h5cpp._node.Dataset))
            self.assertEqual(strscalar.name, 'strscalar')
            self.assertEqual(strscalar.path, '/entry12345:NXentry/strscalar')
            self.assertEqual(strscalar.dtype, 'string')
            self.assertEqual(strscalar.shape, ())

            self.assertTrue(isinstance(floatscalar, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(floatscalar.h5object, h5cpp._node.Dataset))
            self.assertEqual(floatscalar.name, 'floatscalar')
            self.assertEqual(
                floatscalar.path, '/entry12345:NXentry/floatscalar')
            self.assertEqual(floatscalar.dtype, 'float64')
            self.assertEqual(floatscalar.shape, (1,))

            self.assertTrue(isinstance(intscalar, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(intscalar.h5object, h5cpp._node.Dataset))
            self.assertEqual(intscalar.name, 'intscalar')
            self.assertEqual(intscalar.path, '/entry12345:NXentry/intscalar')
            self.assertEqual(intscalar.dtype, 'uint64')
            self.assertEqual(intscalar.shape, (1,))

            self.assertTrue(isinstance(strspec, H5CppWriter.H5CppField))
            self.assertTrue(isinstance(strspec.h5object, h5cpp._node.Dataset))
            self.assertEqual(strspec.name, 'strspec')
            self.assertEqual(
                strspec.path,
                '/entry12345:NXentry/instrument:NXinstrument/strspec')
            self.assertEqual(strspec.dtype, 'string')
            self.assertEqual(strspec.shape, (10,))

            self.assertTrue(isinstance(floatspec, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(floatspec.h5object, h5cpp._node.Dataset))
            self.assertEqual(floatspec.name, 'floatspec')
            self.assertEqual(
                floatspec.path,
                '/entry12345:NXentry/instrument:NXinstrument/floatspec')
            self.assertEqual(floatspec.dtype, 'float32')
            self.assertEqual(floatspec.shape, (20,))

            self.assertTrue(isinstance(intspec, H5CppWriter.H5CppField))
            self.assertTrue(isinstance(intspec.h5object, h5cpp._node.Dataset))
            self.assertEqual(intspec.name, 'intspec')
            self.assertEqual(
                intspec.path,
                '/entry12345:NXentry/instrument:NXinstrument/intspec')
            self.assertEqual(intspec.dtype, 'int64')
            self.assertEqual(intspec.shape, (30,))

            self.assertTrue(isinstance(strimage, H5CppWriter.H5CppField))
            self.assertTrue(isinstance(strimage.h5object, h5cpp._node.Dataset))
            self.assertEqual(strimage.name, 'strimage')
            self.assertEqual(
                strimage.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/strimage')
            self.assertEqual(strimage.dtype, 'string')
            self.assertEqual(strimage.shape, (2, 2))

            self.assertTrue(isinstance(floatimage, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(floatimage.h5object, h5cpp._node.Dataset))
            self.assertEqual(floatimage.name, 'floatimage')
            self.assertEqual(
                floatimage.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/floatimage')
            self.assertEqual(floatimage.dtype, 'float64')
            self.assertEqual(floatimage.shape, (20, 10))

            self.assertTrue(isinstance(intimage, H5CppWriter.H5CppField))
            self.assertTrue(isinstance(intimage.h5object, h5cpp._node.Dataset))
            self.assertEqual(intimage.name, 'intimage')
            self.assertEqual(
                intimage.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/intimage')
            self.assertEqual(intimage.dtype, 'uint32')
            self.assertEqual(intimage.shape, (0, 30))

            self.assertTrue(isinstance(strvec, H5CppWriter.H5CppField))
            self.assertTrue(isinstance(strvec.h5object, h5cpp._node.Dataset))
            self.assertEqual(strvec.name, 'strvec')
            self.assertEqual(
                strvec.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/strvec')
            self.assertEqual(strvec.dtype, 'string')
            self.assertEqual(strvec.shape, (0, 2, 2))

            self.assertTrue(isinstance(floatvec, H5CppWriter.H5CppField))
            self.assertTrue(isinstance(floatvec.h5object, h5cpp._node.Dataset))
            self.assertEqual(floatvec.name, 'floatvec')
            self.assertEqual(
                floatvec.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/floatvec')
            self.assertEqual(floatvec.dtype, 'float64')
            self.assertEqual(floatvec.shape, (1, 20, 10))

            self.assertTrue(isinstance(intvec, H5CppWriter.H5CppField))
            self.assertTrue(isinstance(intvec.h5object, h5cpp._node.Dataset))
            self.assertEqual(intvec.name, 'intvec')
            self.assertEqual(
                intvec.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/intvec')
            self.assertEqual(intvec.dtype, 'uint32')
            self.assertEqual(intvec.shape, (0, 2, 30))

            strscalar_op = entry.open("strscalar")
            floatscalar_op = entry.open("floatscalar")
            intscalar_op = entry.open("intscalar")
            strspec_op = ins.open("strspec")
            floatspec_op = ins.open("floatspec")
            intspec_op = ins.open("intspec")
            strimage_op = det.open("strimage")
            floatimage_op = det.open("floatimage")
            intimage_op = det.open("intimage")
            strvec_op = det.open("strvec")
            floatvec_op = det.open("floatvec")
            intvec_op = det.open("intvec")

            self.assertTrue(isinstance(strscalar_op, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(strscalar_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(strscalar_op.name, 'strscalar')
            self.assertEqual(
                strscalar_op.path, '/entry12345:NXentry/strscalar')
            self.assertEqual(strscalar_op.dtype, 'string')
            self.assertEqual(strscalar_op.shape, ())

            self.assertTrue(
                isinstance(floatscalar_op, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(floatscalar_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(floatscalar_op.name, 'floatscalar')
            self.assertEqual(
                floatscalar_op.path, '/entry12345:NXentry/floatscalar')
            self.assertEqual(floatscalar_op.dtype, 'float64')
            self.assertEqual(floatscalar_op.shape, (1,))

            self.assertTrue(isinstance(intscalar_op, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(intscalar_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(intscalar_op.name, 'intscalar')
            self.assertEqual(
                intscalar_op.path, '/entry12345:NXentry/intscalar')
            self.assertEqual(intscalar_op.dtype, 'uint64')
            self.assertEqual(intscalar_op.shape, (1,))

            self.assertTrue(isinstance(strspec_op, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(strspec_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(strspec_op.name, 'strspec')
            self.assertEqual(
                strspec_op.path,
                '/entry12345:NXentry/instrument:NXinstrument/strspec')
            self.assertEqual(strspec_op.dtype, 'string')
            self.assertEqual(strspec_op.shape, (10,))

            self.assertTrue(isinstance(floatspec_op, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(floatspec_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(floatspec_op.name, 'floatspec')
            self.assertEqual(
                floatspec_op.path,
                '/entry12345:NXentry/instrument:NXinstrument/floatspec')
            self.assertEqual(floatspec_op.dtype, 'float32')
            self.assertEqual(floatspec_op.shape, (20,))

            self.assertTrue(isinstance(intspec_op, H5CppWriter.H5CppField))
            self.assertTrue(isinstance
                            (intspec_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(intspec_op.name, 'intspec')
            self.assertEqual(
                intspec_op.path,
                '/entry12345:NXentry/instrument:NXinstrument/intspec')
            self.assertEqual(intspec_op.dtype, 'int64')
            self.assertEqual(intspec_op.shape, (30,))

            self.assertTrue(isinstance(strimage_op, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(strimage_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(strimage_op.name, 'strimage')
            self.assertEqual(
                strimage_op.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/strimage')
            self.assertEqual(strimage_op.dtype, 'string')
            self.assertEqual(strimage_op.shape, (2, 2))

            self.assertTrue(isinstance(floatimage_op, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(floatimage_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(floatimage_op.name, 'floatimage')
            self.assertEqual(
                floatimage_op.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/floatimage')
            self.assertEqual(floatimage_op.dtype, 'float64')
            self.assertEqual(floatimage_op.shape, (20, 10))

            self.assertTrue(isinstance(intimage_op, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(intimage_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(intimage_op.name, 'intimage')
            self.assertEqual(
                intimage_op.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/intimage')
            self.assertEqual(intimage_op.dtype, 'uint32')
            self.assertEqual(intimage_op.shape, (0, 30))

            self.assertTrue(isinstance(strvec_op, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(strvec_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(strvec_op.name, 'strvec')
            self.assertEqual(
                strvec_op.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/strvec')
            self.assertEqual(strvec_op.dtype, 'string')
            self.assertEqual(strvec_op.shape, (0, 2, 2))

            self.assertTrue(isinstance(floatvec_op, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(floatvec_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(floatvec_op.name, 'floatvec')
            self.assertEqual(
                floatvec_op.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/floatvec')
            self.assertEqual(floatvec_op.dtype, 'float64')
            self.assertEqual(floatvec_op.shape, (1, 20, 10))

            self.assertTrue(isinstance(intvec_op, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(intvec_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(intvec_op.name, 'intvec')
            self.assertEqual(
                intvec_op.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/intvec')
            self.assertEqual(intvec_op.dtype, 'uint32')
            self.assertEqual(intvec_op.shape, (0, 2, 30))
            self.assertEqual(intvec_op.parent, det)

            self.assertTrue(isinstance(lkintimage, H5CppWriter.H5CppLink))
            self.assertTrue(isinstance(lkintimage.h5object, h5cpp._node.Link))
            self.assertTrue(lkintimage.target_path.endswith(
                "%s://entry12345/instrument/detector/intimage" % self._fname))
            self.assertEqual(
                lkintimage.path,
                "/entry12345:NXentry/data:NXdata/lkintimage")

            self.assertTrue(isinstance(lkfloatvec, H5CppWriter.H5CppLink))
            self.assertTrue(isinstance(lkfloatvec.h5object, h5cpp._node.Link))
            self.assertTrue(lkfloatvec.target_path.endswith(
                "%s://entry12345/instrument/detector/floatvec" % self._fname))
            self.assertEqual(
                lkfloatvec.path,
                "/entry12345:NXentry/data:NXdata/lkfloatvec")

            self.assertTrue(isinstance(lkintspec, H5CppWriter.H5CppLink))
            self.assertTrue(isinstance(lkintspec.h5object, h5cpp._node.Link))
            self.assertTrue(lkintspec.target_path.endswith(
                "%s://entry12345/instrument/intspec" % self._fname))
            self.assertEqual(
                lkintspec.path,
                "/entry12345:NXentry/data:NXdata/lkintspec")

            self.assertTrue(isinstance(lkdet, H5CppWriter.H5CppLink))
            self.assertTrue(isinstance(lkdet.h5object, h5cpp._node.Link))
            self.assertTrue(lkdet.target_path.endswith(
                "%s://entry12345/instrument/detector" % self._fname))
            self.assertEqual(
                lkdet.path,
                "/entry12345:NXentry/data:NXdata/lkdet")

            self.assertTrue(isinstance(lkno, H5CppWriter.H5CppLink))
            self.assertTrue(isinstance(lkno.h5object, h5cpp._node.Link))
            self.assertTrue(lkno.target_path.endswith(
                "%s://notype/unknown" % self._fname))
            self.assertEqual(
                lkno.path,
                "/entry12345:NXentry/data:NXdata/lkno")

            lkintimage_op = dt.open("lkintimage")
            lkfloatvec_op = dt.open("lkfloatvec")
            lkintspec_op = dt.open("lkintspec")
            # lkdet_op =
            dt.open("lkdet")
            lkno_op = dt.open("lkno")

            self.assertTrue(isinstance(lkintimage_op, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(lkintimage_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(lkintimage_op.name, 'lkintimage')
            self.assertEqual(
                lkintimage_op.path,
                '/entry12345:NXentry/data:NXdata/lkintimage')
            self.assertEqual(lkintimage_op.dtype, 'uint32')
            self.assertEqual(lkintimage_op.shape, (0, 30))

            self.assertTrue(isinstance(lkfloatvec_op, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(lkfloatvec_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(lkfloatvec_op.name, 'lkfloatvec')
            self.assertEqual(lkfloatvec_op.path,
                             '/entry12345:NXentry/data:NXdata/lkfloatvec')
            self.assertEqual(lkfloatvec_op.dtype, 'float64')
            self.assertEqual(lkfloatvec_op.shape, (1, 20, 10))

            self.assertTrue(
                isinstance(lkintspec_op, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(lkintspec_op.h5object, h5cpp._node.Dataset))
            self.assertEqual(lkintspec_op.name, 'lkintspec')
            self.assertEqual(lkintspec_op.path,
                             '/entry12345:NXentry/data:NXdata/lkintspec')
            self.assertEqual(lkintspec_op.dtype, 'int64')
            self.assertEqual(lkintspec_op.shape, (30,))

            self.assertTrue(isinstance(lkno_op, H5CppWriter.H5CppLink))
            self.assertTrue(isinstance(lkno_op.h5object, h5cpp._node.Link))
            self.assertTrue(lkno_op.target_path.endswith(
                "%s://notype/unknown" % self._fname))
            self.assertEqual(
                lkno_op.path,
                "/entry12345:NXentry/data:NXdata/lkno")

            entry.close()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, False)
            self.assertEqual(dt.is_valid, False)

            entry.reopen()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)

            fl.reopen()
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, False)

            fl.close()

            fl.reopen(True)
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, True)

            fl.close()

            # self.myAssertRaise(
            #     Exception, fl.reopen, True, True)
            # self.myAssertRaise(
            #     Exception, fl.reopen, False, True)

            fl = H5CppWriter.open_file(self._fname, readonly=True)
            f = fl.root()
            self.assertEqual(5, len(f.attributes))
            # atts = []
            for at in f.attributes:
                print("%s %s %s" % (at.name, at.read(), at.dtype))
            self.assertEqual(
                f.attributes["file_name"][...],
                self._fname)
            self.assertTrue(
                f.attributes["NX_class"][...], "NXroot")
            self.assertEqual(f.size, 2)
            fl.close()

        finally:
            os.remove(self._fname)

    # default createfile test
    # \brief It tests default settings
    def test_h5cppfield_scalar(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        self._fname = '%s/%s%s.h5' % (
            os.getcwd(), self.__class__.__name__, fun)

        try:
            # overwrite = False
            FileWriter.writer = H5CppWriter
            fl = FileWriter.create_file(self._fname)

            rt = fl.root()
            # nt =
            rt.create_group("notype")
            entry = rt.create_group("entry12345", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("detector", "NXdetector")
            dt = entry.create_group("data", "NXdata")

            df0 = FileWriter.data_filter()
            df1 = FileWriter.data_filter()
            df1.rate = 2
            df2 = FileWriter.data_filter()
            df2.rate = 4
            df2.shuffle = 6

            strscalar = entry.create_field("strscalar", "string")
            floatscalar = entry.create_field("floatscalar", "float64")
            intscalar = entry.create_field("intscalar", "uint64")
            # strspec =
            ins.create_field("strspec", "string", [10], [6])
            # floatspec =
            ins.create_field("floatspec", "float32", [20], [16])
            # intspec =
            ins.create_field("intspec", "int64", [30], [5])
            # strimage =
            det.create_field("strimage", "string", [2, 2], [2, 1])
            # floatimage =
            det.create_field(
                "floatimage", "float64", [20, 10], dfilter=df0)
            # intimage =
            det.create_field("intimage", "uint32", [0, 30], [1, 30])
            # strvec =
            det.create_field("strvec", "string", [0, 2, 2], [1, 2, 2])
            # floatvec =
            det.create_field(
                "floatvec", "float64", [1, 20, 10], [1, 10, 10], dfilter=df1)
            # intvec =
            det.create_field(
                "intvec", "uint32", [0, 2, 30], dfilter=df2)

            self.assertTrue(isinstance(strscalar, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(strscalar.h5object, h5cpp._node.Dataset))
            self.assertEqual(strscalar.name, 'strscalar')
            self.assertEqual(strscalar.h5object.link.path.name, 'strscalar')
            self.assertEqual(
                str(strscalar.h5object.link.path), '/entry12345/strscalar')
            self.assertEqual(strscalar.path, '/entry12345:NXentry/strscalar')
            self.assertEqual(strscalar.dtype, 'string')
            self.assertEqual(strscalar.h5object.datatype.type.name, 'STRING')
            self.assertEqual(strscalar.shape, ())
            # self.assertEqual(
            #     strscalar.h5object.dataspace.current_dimensions, (1,))
            self.assertEqual(strscalar.is_valid, True)
            self.assertEqual(strscalar.shape, ())
            # self.assertEqual(
            #     strscalar.h5object.dataspace.current_dimensions, (1,))

            vl = ["1234", "Somethin to test 1234", "2342;23ml243",
                  "sd", "q234", "12 123 ", "aqds ", "Aasdas"]
            strscalar[()] = vl[0]
            self.assertEqual(strscalar.read(), vl[0])
            strscalar.write(vl[1])
            self.assertEqual(strscalar[()], vl[1])
            strscalar[()] = vl[2]
            self.assertEqual(strscalar[()], vl[2])
            strscalar[()] = vl[0]

            # strscalar.grow()
            # self.assertEqual(strscalar.shape, (2,))
            # self.assertEqual(
            #     strscalar.h5object.dataspace.current_dimensions, (2,))

            # self.assertEqual(strscalar[0], vl[0])
            # strscalar[1] = vl[3]
            # self.assertEqual(list(strscalar[...]), [vl[0], vl[3]])

            # strscalar.grow(ext=2)
            # self.assertEqual(strscalar.shape, (4,))
            # self.assertEqual(
            #     strscalar.h5object.dataspace.current_dimensions, (4,))
            # strscalar[1:4] = vl[1:4]
            # self.assertEqual(list(strscalar.read()), vl[0:4])
            # self.assertEqual(list(strscalar[0:2]), vl[0:2])

            # strscalar.grow(0, 3)
            # self.assertEqual(strscalar.shape, (7,))
            # self.assertEqual(
            #     strscalar.h5object.dataspace.current_dimensions, (7,))
            # strscalar.write(vl[0:7])
            # self.assertEqual(list(strscalar.read()), vl[0:7])
            # self.assertEqual(list(strscalar[...]), vl[0:7])

            attrs = strscalar.attributes
            self.assertTrue(
                isinstance(attrs, H5CppWriter.H5CppAttributeManager))
            print(type(attrs.h5object))
            self.assertTrue(
                isinstance(attrs.h5object, h5cpp._attribute.AttributeManager))
            self.assertEqual(attrs.parent, strscalar)
            self.assertEqual(len(attrs), 0)

            self.assertTrue(isinstance(floatscalar, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(floatscalar.h5object, h5cpp._node.Dataset))
            self.assertEqual(floatscalar.name, 'floatscalar')
            self.assertEqual(
                floatscalar.h5object.link.path.name, 'floatscalar')
            self.assertEqual(
                str(floatscalar.h5object.link.path), '/entry12345/floatscalar')

            self.assertEqual(floatscalar.dtype, 'float64')
            self.assertEqual(floatscalar.h5object.datatype.type.name, 'FLOAT')
            self.assertEqual(floatscalar.shape, (1,))
            self.assertEqual(
                floatscalar.h5object.dataspace.current_dimensions, (1,))

            vl = [1123.34, 3234.3, 234.33, -4.4, 34, 0.0, 4.3, 434.5, 23.0, 0]

            floatscalar[...] = vl[0]
            self.assertEqual(floatscalar.read(), vl[0])
            floatscalar.write(vl[1])
            self.assertEqual(floatscalar[0], vl[1])
            floatscalar[0] = vl[2]
            self.assertEqual(floatscalar[...], vl[2])
            floatscalar[0] = vl[0]

            floatscalar.grow()
            self.assertEqual(floatscalar.shape, (2,))
            self.assertEqual(
                floatscalar.h5object.dataspace.current_dimensions, (2,))

            self.assertEqual(floatscalar[0], vl[0])
            floatscalar[1] = vl[3]
            self.assertEqual(list(floatscalar[...]), [vl[0], vl[3]])

            floatscalar.grow(ext=2)
            self.assertEqual(floatscalar.shape, (4,))
            self.assertEqual(
                floatscalar.h5object.dataspace.current_dimensions, (4,))
            floatscalar[1:4] = vl[1:4]
            self.assertEqual(list(floatscalar.read()), vl[0:4])
            self.assertEqual(list(floatscalar[0:2]), vl[0:2])

            floatscalar.grow(0, 3)
            self.assertEqual(floatscalar.shape, (7,))
            self.assertEqual(
                floatscalar.h5object.dataspace.current_dimensions, (7,))
            floatscalar.write(vl[0:7])
            self.assertEqual(list(floatscalar.read()), vl[0:7])
            self.assertEqual(list(floatscalar[...]), vl[0:7])

            attrs = floatscalar.attributes
            self.assertTrue(
                isinstance(attrs, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attrs.h5object, h5cpp._attribute.AttributeManager))
            self.assertEqual(attrs.parent, floatscalar)
            self.assertEqual(len(attrs), 0)

            self.assertTrue(isinstance(intscalar, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(intscalar.h5object, h5cpp._node.Dataset))
            self.assertEqual(intscalar.name, 'intscalar')
            self.assertEqual(intscalar.h5object.link.path.name, 'intscalar')
            self.assertEqual(
                str(intscalar.h5object.link.path), '/entry12345/intscalar')
            self.assertEqual(intscalar.path, '/entry12345:NXentry/intscalar')
            self.assertEqual(intscalar.dtype, 'uint64')
            self.assertEqual(intscalar.h5object.datatype.type.name, 'INTEGER')
            self.assertEqual(intscalar.shape, (1,))
            self.assertEqual(
                intscalar.h5object.dataspace.current_dimensions, (1,))

            vl = [243, 43, 45, 34, 45, 54, 23234]

            intscalar[...] = vl[0]
            self.assertEqual(intscalar.read(), vl[0])
            intscalar.write(vl[1])
            self.assertEqual(intscalar[0], vl[1])
            intscalar[0] = vl[2]
            self.assertEqual(intscalar[...], vl[2])
            intscalar[0] = vl[0]

            intscalar.grow()
            self.assertEqual(intscalar.shape, (2,))
            self.assertEqual(
                intscalar.h5object.dataspace.current_dimensions, (2,))

            self.assertEqual(intscalar[0], vl[0])
            intscalar[1] = vl[3]
            self.assertEqual(list(intscalar[...]), [vl[0], vl[3]])

            intscalar.grow(ext=2)
            self.assertEqual(intscalar.shape, (4,))
            self.assertEqual(
                intscalar.h5object.dataspace.current_dimensions, (4,))
            intscalar[1:4] = vl[1:4]
            self.assertEqual(list(intscalar.read()), vl[0:4])
            self.assertEqual(list(intscalar[0:2]), vl[0:2])

            intscalar.grow(0, 3)
            self.assertEqual(intscalar.shape, (7,))
            self.assertEqual(
                intscalar.h5object.dataspace.current_dimensions, (7,))
            intscalar.write(vl[0:7])
            self.assertEqual(list(intscalar.read()), vl[0:7])
            self.assertEqual(list(intscalar[...]), vl[0:7])

            attrs = intscalar.attributes
            self.assertTrue(
                isinstance(attrs, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attrs.h5object, h5cpp._attribute.AttributeManager))
            self.assertEqual(attrs.parent, intscalar)
            self.assertEqual(len(attrs), 0)

            intscalar.close()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(det.is_valid, True)
            self.assertEqual(intscalar.is_valid, False)
            self.assertEqual(attrs.is_valid, False)

            entry.reopen()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(det.is_valid, True)
            self.assertEqual(intscalar.is_valid, True)
            self.assertEqual(attrs.is_valid, True)

            fl.reopen()
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, False)

            fl.close()

            fl.reopen(True)
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, True)

            fl.close()

            # self.myAssertRaise(
            #     Exception, fl.reopen, True, True)
            # self.myAssertRaise(
            #     Exception, fl.reopen, False, True)

            fl = FileWriter.open_file(self._fname, readonly=True)
            f = fl.root()
            self.assertEqual(5, len(f.attributes))
            # atts = []
            for at in f.attributes:
                print("%s %s %s" % (at.name, at.read(), at.dtype))
            self.assertEqual(
                f.attributes["file_name"][...],
                self._fname)
            self.assertTrue(
                f.attributes["NX_class"][...], "NXroot")
            self.assertEqual(f.size, 2)
            fl.close()

        finally:
            os.remove(self._fname)

    # default createfile test
    # \brief It tests default settings
    def test_h5cppfield_spectrum(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        self._fname = '%s/%s%s.h5' % (
            os.getcwd(), self.__class__.__name__, fun)

        try:
            # overwrite = False
            FileWriter.writer = H5CppWriter
            fl = FileWriter.create_file(self._fname)

            rt = fl.root()
            # nt =
            rt.create_group("notype")
            entry = rt.create_group("entry12345", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("detector", "NXdetector")
            dt = entry.create_group("data", "NXdata")

            df0 = FileWriter.data_filter()
            df1 = FileWriter.data_filter()
            df1.rate = 2
            df2 = FileWriter.data_filter()
            df2.rate = 4
            df2.shuffle = 6

            # strscalar =
            entry.create_field("strscalar", "string")
            # floatscalar =
            entry.create_field("floatscalar", "float64")
            # intscalar =
            entry.create_field("intscalar", "uint64")
            strspec = ins.create_field("strspec", "string", [10], [6])
            floatspec = ins.create_field("floatspec", "float32", [20], [16])
            intspec = ins.create_field("intspec", "int64", [30], [5])
            # strimage =
            det.create_field("strimage", "string", [2, 2], [2, 1])
            # floatimage =
            det.create_field(
                "floatimage", "float64", [20, 10], dfilter=df0)
            # intimage =
            det.create_field("intimage", "uint32", [0, 30], [1, 30])
            # strvec =
            det.create_field("strvec", "string", [0, 2, 2], [1, 2, 2])
            # floatvec =
            det.create_field(
                "floatvec", "float64", [1, 20, 10], [1, 10, 10], dfilter=df1)
            # intvec =
            det.create_field(
                "intvec", "uint32", [0, 2, 30], dfilter=df2)

            self.assertTrue(isinstance(strspec, H5CppWriter.H5CppField))
            self.assertTrue(isinstance(strspec.h5object, h5cpp._node.Dataset))
            self.assertEqual(strspec.name, 'strspec')
            self.assertEqual(
                strspec.path,
                '/entry12345:NXentry/instrument:NXinstrument/strspec')
            self.assertEqual(strspec.h5object.link.path.name, 'strspec')
            self.assertEqual(
                str(strspec.h5object.link.path),
                '/entry12345/instrument/strspec')
            self.assertEqual(strspec.dtype, 'string')
            self.assertEqual(strspec.h5object.datatype.type.name, 'STRING')
            self.assertEqual(strspec.shape, (10,))
            self.assertEqual(
                strspec.h5object.dataspace.current_dimensions, (10,))

            chars = string.ascii_uppercase + string.digits
            vl = [
                ''.join(self.__rnd.choice(chars)
                        for _ in range(self.__rnd.randint(1, 10)))
                for _ in range(40)]

            strspec[...] = vl[0:10]
            self.assertEqual(list(strspec.read()), vl[0:10])
            strspec.write(vl[11:21])
            self.assertEqual(list(strspec[...]), vl[11:21])
            strspec[...] = vl[0:10]

            strspec.grow()
            self.assertEqual(strspec.shape, (11,))
            self.assertEqual(
                strspec.h5object.dataspace.current_dimensions, (11,))

            self.assertEqual(list(strspec[0:10]), vl[0:10])
            strspec[10] = vl[10]
            self.assertEqual(list(strspec[...]), vl[0:11])

            strspec.grow(ext=2)
            self.assertEqual(strspec.shape, (13,))
            self.assertEqual(
                strspec.h5object.dataspace.current_dimensions, (13,))
            strspec[1:13] = vl[1:13]
            self.assertEqual(list(strspec.read()), vl[0:13])
            self.assertEqual(list(strspec[0:2]), vl[0:2])

            strspec.grow(0, 3)
            self.assertEqual(strspec.shape, (16,))
            self.assertEqual(
                strspec.h5object.dataspace.current_dimensions, (16,))
            strspec.write(vl[0:16])
            self.assertEqual(list(strspec.read()), vl[0:16])
            self.assertEqual(list(strspec[...]), vl[0:16])

            attrs = strspec.attributes
            self.assertTrue(
                isinstance(attrs, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attrs.h5object, h5cpp._attribute.AttributeManager))
            self.assertEqual(attrs.parent, strspec)
            self.assertEqual(len(attrs), 0)

            self.assertTrue(isinstance(floatspec, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(floatspec.h5object, h5cpp._node.Dataset))
            self.assertEqual(floatspec.name, 'floatspec')
            self.assertEqual(floatspec.h5object.link.path.name, 'floatspec')
            self.assertEqual(
                str(floatspec.h5object.link.path),
                '/entry12345/instrument/floatspec')
            self.assertEqual(
                floatspec.path,
                '/entry12345:NXentry/instrument:NXinstrument/floatspec')
            self.assertEqual(floatspec.dtype, 'float32')
            self.assertEqual(floatspec.h5object.datatype.type.name, 'FLOAT')
            self.assertEqual(floatspec.shape, (20,))
            self.assertEqual(
                floatspec.h5object.dataspace.current_dimensions, (20,))

            vl = [self.__rnd.uniform(-200.0, 200) for _ in range(80)]

            floatspec[...] = vl[0:20]
            self.myAssertFloatList(list(floatspec.read()), vl[0:20], 1e-4)
            floatspec.write(vl[21:41])
            self.myAssertFloatList(list(floatspec[...]), vl[21:41], 1e-4)
            floatspec[...] = vl[0:20]

            floatspec.grow()
            self.assertEqual(floatspec.shape, (21,))
            self.assertEqual(
                floatspec.h5object.dataspace.current_dimensions, (21,))

            self.myAssertFloatList(list(floatspec[0:20]), vl[0:20], 1e-4)
            floatspec[20] = vl[20]
            self.myAssertFloatList(list(floatspec[...]), vl[0:21], 1e-4)

            floatspec.grow(ext=2)
            self.assertEqual(floatspec.shape, (23,))
            self.assertEqual(
                floatspec.h5object.dataspace.current_dimensions, (23,))
            floatspec[1:23] = vl[1:23]
            self.myAssertFloatList(list(floatspec.read()), vl[0:23], 1e-4)
            self.myAssertFloatList(list(floatspec[0:2]), vl[0:2], 1e-4)

            floatspec.grow(0, 3)
            self.assertEqual(floatspec.shape, (26,))
            self.assertEqual(
                floatspec.h5object.dataspace.current_dimensions, (26,))
            floatspec.write(vl[0:26])
            self.myAssertFloatList(list(floatspec.read()), vl[0:26], 1e-4)
            self.myAssertFloatList(list(floatspec[...]), vl[0:26], 1e-4)

            attrs = floatspec.attributes
            self.assertTrue(
                isinstance(attrs, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attrs.h5object, h5cpp._attribute.AttributeManager))
            self.assertEqual(attrs.parent, floatspec)
            self.assertEqual(len(attrs), 0)

            self.assertTrue(isinstance(intspec, H5CppWriter.H5CppField))
            self.assertTrue(isinstance(intspec.h5object, h5cpp._node.Dataset))
            self.assertEqual(intspec.name, 'intspec')
            self.assertEqual(
                intspec.path,
                '/entry12345:NXentry/instrument:NXinstrument/intspec')
            self.assertEqual(intspec.dtype, 'int64')
            self.assertEqual(intspec.shape, (30,))
            self.assertEqual(intspec.h5object.link.path.name, 'intspec')
            self.assertEqual(
                str(intspec.h5object.link.path),
                '/entry12345/instrument/intspec')
            self.assertEqual(intspec.h5object.datatype.type.name, 'INTEGER')
            self.assertEqual(
                intspec.h5object.dataspace.current_dimensions, (30,))

            vl = [self.__rnd.randint(1, 16000) for _ in range(100)]

            intspec[...] = vl[0:30]
            self.assertEqual(list(intspec.read()), vl[0:30])
            intspec.write(vl[31:61])
            self.assertEqual(list(intspec[...]), vl[31:61])
            intspec[...] = vl[0:30]

            intspec.grow()
            self.assertEqual(intspec.shape, (31,))
            self.assertEqual(
                intspec.h5object.dataspace.current_dimensions, (31,))

            self.assertEqual(list(intspec[0:10]), vl[0:10])
            intspec[30] = vl[30]
            self.assertEqual(list(intspec[...]), vl[0:31])

            intspec.grow(ext=2)
            self.assertEqual(intspec.shape, (33,))
            self.assertEqual(
                intspec.h5object.dataspace.current_dimensions, (33,))
            intspec[1:33] = vl[1:33]
            self.assertEqual(list(intspec.read()), vl[0:33])
            self.assertEqual(list(intspec[0:2]), vl[0:2])

            intspec.grow(0, 3)
            self.assertEqual(intspec.shape, (36,))
            self.assertEqual(
                intspec.h5object.dataspace.current_dimensions, (36,))
            intspec.write(vl[0:36])
            self.assertEqual(list(intspec.read()), vl[0:36])
            self.assertEqual(list(intspec[...]), vl[0:36])

            attrs = intspec.attributes
            self.assertTrue(isinstance(
                attrs, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(isinstance(
                attrs.h5object, h5cpp._attribute.AttributeManager))
            self.assertEqual(attrs.parent, intspec)
            self.assertEqual(len(attrs), 0)

            entry.close()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, False)
            self.assertEqual(dt.is_valid, False)

            entry.reopen()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)

            fl.reopen()
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, False)

            fl.close()

            fl.reopen(True)
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, True)

            fl.close()

            # self.myAssertRaise(
            #     Exception, fl.reopen, True, True)
            # self.myAssertRaise(
            #     Exception, fl.reopen, False, True)

            fl = FileWriter.open_file(self._fname, readonly=True)
            f = fl.root()
            self.assertEqual(5, len(f.attributes))
            # atts = []
            for at in f.attributes:
                print("%s %s %s" % (at.name, at.read(), at.dtype))
            self.assertEqual(
                f.attributes["file_name"][...],
                self._fname)
            self.assertTrue(
                f.attributes["NX_class"][...], "NXroot")
            self.assertEqual(f.size, 2)
            fl.close()

        finally:
            os.remove(self._fname)

    # default createfile test
    # \brief It tests default settings
    def test_h5cppfield_image(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        self._fname = '%s/%s%s.h5' % (
            os.getcwd(), self.__class__.__name__, fun)

        try:
            # overwrite = False
            FileWriter.writer = H5CppWriter
            fl = FileWriter.create_file(self._fname)

            rt = fl.root()
            # nt =
            rt.create_group("notype")
            entry = rt.create_group("entry12345", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("detector", "NXdetector")
            dt = entry.create_group("data", "NXdata")

            df0 = FileWriter.data_filter()
            df1 = FileWriter.data_filter()
            df1.rate = 2
            df2 = FileWriter.data_filter()
            df2.rate = 4
            df2.shuffle = 6

            # strscalar =
            entry.create_field("strscalar", "string")
            # floatscalar =
            entry.create_field("floatscalar", "float64")
            # intscalar =
            entry.create_field("intscalar", "uint64")
            # strspec =
            ins.create_field("strspec", "string", [10], [6])
            # floatspec =
            ins.create_field("floatspec", "float32", [20], [16])
            # intspec =
            ins.create_field("intspec", "int64", [30], [5])
            strimage = det.create_field("strimage", "string", [2, 2], [2, 1])
            floatimage = det.create_field(
                "floatimage", "float64", [20, 10], dfilter=df0)
            intimage = det.create_field("intimage", "uint32", [0, 30], [1, 30])
            # strvec =
            det.create_field("strvec", "string", [0, 2, 2], [1, 2, 2])
            # floatvec =
            det.create_field(
                "floatvec", "float64", [1, 20, 10], [1, 10, 10], dfilter=df1)
            # intvec =
            det.create_field(
                "intvec", "uint32", [0, 2, 30], dfilter=df2)

            self.assertTrue(isinstance(strimage, H5CppWriter.H5CppField))
            self.assertTrue(isinstance(strimage.h5object, h5cpp._node.Dataset))
            self.assertEqual(strimage.name, 'strimage')
            self.assertEqual(
                strimage.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/strimage')
            self.assertEqual(strimage.dtype, 'string')
            self.assertEqual(strimage.shape, (2, 2))
            self.assertEqual(strimage.h5object.link.path.name, 'strimage')
            self.assertEqual(
                str(strimage.h5object.link.path),
                '/entry12345/instrument/detector/strimage')

            self.assertEqual(strimage.h5object.datatype.type.name, 'STRING')
            self.assertEqual(
                strimage.h5object.dataspace.current_dimensions, (2, 2))

            chars = string.ascii_uppercase + string.digits
            vl = [
                [''.join(self.__rnd.choice(chars)
                         for _ in range(self.__rnd.randint(1, 10)))
                 for _ in range(10)]
                for _ in range(30)]

            vv = [[vl[j][i] for i in range(2)] for j in range(2)]
            strimage[...] = vv
            self.myAssertImage(strimage.read(), vv)
            vv2 = [[vl[j + 2][i + 2] for i in range(2)] for j in range(2)]
            strimage.write(vv2)
            self.myAssertImage(list(strimage[...]), vv2)
            strimage[...] = vv

            strimage.grow()
            self.assertEqual(strimage.shape, (3, 2))
            self.assertEqual(
                strimage.h5object.dataspace.current_dimensions, (3, 2))

            iv = [[strimage[j, i] for i in range(2)] for j in range(2)]
            self.myAssertImage(iv, vv)
            strimage[2, :] = [vl[2][0], vl[2][1]]
            vv3 = [[vl[j][i] for i in range(2)] for j in range(3)]
            self.myAssertImage(strimage[...], vv3)

            strimage.grow(ext=2)
            self.assertEqual(strimage.shape, (5, 2))
            self.assertEqual(
                strimage.h5object.dataspace.current_dimensions, (5, 2))
            vv4 = [[vl[j + 2][i] for i in range(2)] for j in range(3)]
            vv5 = [[vl[j][i] for i in range(2)] for j in range(5)]
            strimage[2:5, :] = vv4
            self.myAssertImage(strimage[...], vv5)
            self.myAssertImage(strimage[0:3, :], vv3)

            strimage.grow(1, 4)
            self.assertEqual(strimage.shape, (5, 6))
            self.assertEqual(
                strimage.h5object.dataspace.current_dimensions, (5, 6))

            vv6 = [[vl[j][i] for i in range(6)] for j in range(5)]
            strimage.write(vv6)
            self.myAssertImage(strimage[...], vv6)
            self.myAssertImage(strimage.read(), vv6)

            attrs = strimage.attributes
            self.assertTrue(
                isinstance(attrs, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attrs.h5object, h5cpp._attribute.AttributeManager))
            self.assertEqual(attrs.parent, strimage)
            self.assertEqual(len(attrs), 0)

            self.assertTrue(isinstance(floatimage, H5CppWriter.H5CppField))
            self.assertTrue(
                isinstance(floatimage.h5object, h5cpp._node.Dataset))
            self.assertEqual(floatimage.name, 'floatimage')
            self.assertEqual(
                floatimage.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/floatimage')
            self.assertEqual(floatimage.dtype, 'float64')
            self.assertEqual(floatimage.shape, (20, 10))
            self.assertEqual(floatimage.h5object.link.path.name, 'floatimage')
            self.assertEqual(
                str(floatimage.h5object.link.path),
                '/entry12345/instrument/detector/floatimage')
            self.assertEqual(floatimage.h5object.datatype.type.name, 'FLOAT')
            self.assertEqual(
                floatimage.h5object.dataspace.current_dimensions, (20, 10))

            vl = [
                [self.__rnd.uniform(-20000.0, 20000) for _ in range(50)]
                for _ in range(50)]

            vv = [[vl[j][i] for i in range(10)] for j in range(20)]
            floatimage[...] = vv
            self.myAssertImage(floatimage.read(), vv)
            vv2 = [[vl[j + 20][i + 10] for i in range(10)] for j in range(20)]
            floatimage.write(vv2)
            self.myAssertImage(list(floatimage[...]), vv2)
            floatimage[...] = vv

            floatimage.grow()
            self.assertEqual(floatimage.shape, (21, 10))
            self.assertEqual(
                floatimage.h5object.dataspace.current_dimensions, (21, 10))

            iv = [[floatimage[j, i] for i in range(10)] for j in range(20)]
            self.myAssertImage(iv, vv)
            floatimage[20, :] = [vl[20][i] for i in range(10)]
            vv3 = [[vl[j][i] for i in range(10)] for j in range(21)]
            self.myAssertImage(floatimage[...], vv3)

            floatimage.grow(ext=2)
            self.assertEqual(floatimage.shape, (23, 10))
            self.assertEqual(
                floatimage.h5object.dataspace.current_dimensions, (23, 10))
            vv4 = [[vl[j + 2][i] for i in range(10)] for j in range(21)]
            vv5 = [[vl[j][i] for i in range(10)] for j in range(23)]
            floatimage[2:23, :] = vv4
            self.myAssertImage(floatimage[...], vv5)
            self.myAssertImage(floatimage[0:21, :], vv3)

            floatimage.grow(1, 4)
            self.assertEqual(floatimage.shape, (23, 14))
            self.assertEqual(
                floatimage.h5object.dataspace.current_dimensions, (23, 14))

            vv6 = [[vl[j][i] for i in range(14)] for j in range(23)]
            floatimage.write(vv6)
            self.myAssertImage(floatimage[...], vv6)
            self.myAssertImage(floatimage.read(), vv6)

            self.assertTrue(isinstance(intimage, H5CppWriter.H5CppField))
            self.assertTrue(isinstance(intimage.h5object, h5cpp._node.Dataset))
            self.assertEqual(intimage.name, 'intimage')
            self.assertEqual(
                intimage.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/intimage')
            self.assertEqual(intimage.h5object.link.path.name, 'intimage')
            self.assertEqual(
                str(intimage.h5object.link.path),
                '/entry12345/instrument/detector/intimage')
            self.assertEqual(intimage.dtype, 'uint32')
            self.assertEqual(intimage.shape, (0, 30))
            self.assertEqual(intimage.h5object.datatype.type.name, 'INTEGER')
            self.assertEqual(
                intimage.h5object.dataspace.current_dimensions, (0, 30))

            vl = [
                [self.__rnd.randint(1, 1600) for _ in range(80)]
                for _ in range(80)]

            intimage.grow(0, 20)
            vv = [[vl[j][i] for i in range(30)] for j in range(20)]
            intimage[...] = vv
            self.myAssertImage(intimage.read(), vv)
            vv2 = [[vl[j + 20][i + 10] for i in range(30)] for j in range(20)]
            intimage.write(vv2)
            self.myAssertImage(list(intimage[...]), vv2)
            intimage[...] = vv

            intimage.grow()
            self.assertEqual(intimage.shape, (21, 30))
            self.assertEqual(
                intimage.h5object.dataspace.current_dimensions, (21, 30))

            iv = [[intimage[j, i] for i in range(30)] for j in range(20)]
            self.myAssertImage(iv, vv)
            intimage[20, :] = [vl[20][i] for i in range(30)]
            vv3 = [[vl[j][i] for i in range(30)] for j in range(21)]
            self.myAssertImage(intimage[...], vv3)

            intimage.grow(ext=2)
            self.assertEqual(intimage.shape, (23, 30))
            self.assertEqual(
                intimage.h5object.dataspace.current_dimensions, (23, 30))
            vv4 = [[vl[j + 2][i] for i in range(30)] for j in range(21)]
            vv5 = [[vl[j][i] for i in range(30)] for j in range(23)]
            intimage[2:23, :] = vv4
            self.myAssertImage(intimage[...], vv5)
            self.myAssertImage(intimage[0:21, :], vv3)

            intimage.grow(1, 4)
            self.assertEqual(intimage.shape, (23, 34))
            self.assertEqual(
                intimage.h5object.dataspace.current_dimensions, (23, 34))

            vv6 = [[vl[j][i] for i in range(34)] for j in range(23)]
            intimage.write(vv6)
            self.myAssertImage(intimage[...], vv6)
            self.myAssertImage(intimage.read(), vv6)

            entry.close()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, False)
            self.assertEqual(dt.is_valid, False)

            entry.reopen()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)

            fl.reopen()
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, False)

            fl.close()

            fl.reopen(True)
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, True)

            fl.close()

            # self.myAssertRaise(
            #     Exception, fl.reopen, True, True)
            # self.myAssertRaise(
            #     Exception, fl.reopen, False, True)

            fl = H5CppWriter.open_file(self._fname, readonly=True)
            f = fl.root()
            self.assertEqual(5, len(f.attributes))
            # atts = []
            for at in f.attributes:
                print("%s %s %s" % (at.name, at.read(), at.dtype))
            self.assertEqual(
                f.attributes["file_name"][...],
                self._fname)
            self.assertTrue(
                f.attributes["NX_class"][...], "NXroot")
            self.assertEqual(f.size, 2)
            fl.close()

        finally:
            os.remove(self._fname)

    # default createfile test
    # \brief It tests default settings
    def test_h5cppfield_vec(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        self._fname = '%s/%s%s.h5' % (
            os.getcwd(), self.__class__.__name__, fun)

        try:
            # overwrite = False
            FileWriter.writer = H5CppWriter
            fl = FileWriter.create_file(self._fname)

            rt = fl.root()
            # nt =
            rt.create_group("notype")
            entry = rt.create_group("entry12345", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("detector", "NXdetector")
            dt = entry.create_group("data", "NXdata")

            df0 = FileWriter.data_filter()
            df1 = FileWriter.data_filter()
            df1.rate = 2
            df2 = FileWriter.data_filter()
            df2.rate = 4
            df2.shuffle = 6

            # strscalar =
            entry.create_field("strscalar", "string")
            # floatscalar =
            entry.create_field("floatscalar", "float64")
            # intscalar =
            entry.create_field("intscalar", "uint64")
            # strspec =
            ins.create_field("strspec", "string", [10], [6])
            # floatspec =
            ins.create_field("floatspec", "float32", [20], [16])
            # intspec =
            ins.create_field("intspec", "int64", [30], [5])
            # strimage =
            det.create_field("strimage", "string", [2, 2], [2, 1])
            # floatimage =
            det.create_field(
                "floatimage", "float64", [20, 10], dfilter=df0)
            # intimage =
            det.create_field("intimage", "uint32", [0, 30], [1, 30])
            strvec = det.create_field("strvec", "string", [0, 2, 2], [1, 2, 2])
            floatvec = det.create_field(
                "floatvec", "float64", [1, 20, 10], [1, 10, 10], dfilter=df1)
            intvec = det.create_field(
                "intvec", "uint32", [0, 2, 30], dfilter=df2)

            self.assertTrue(isinstance(strvec, H5CppWriter.H5CppField))
            self.assertTrue(isinstance(strvec.h5object, h5cpp._node.Dataset))
            self.assertEqual(strvec.name, 'strvec')
            self.assertEqual(
                strvec.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/strvec')
            self.assertEqual(strvec.dtype, 'string')
            self.assertEqual(strvec.shape, (0, 2, 2))
            self.assertEqual(strvec.h5object.link.path.name, 'strvec')
            self.assertEqual(
                str(strvec.h5object.link.path),
                '/entry12345/instrument/detector/strvec')
            self.assertEqual(strvec.h5object.datatype.type.name, 'STRING')
            self.assertEqual(
                strvec.h5object.dataspace.current_dimensions, (0, 2, 2))

            chars = string.ascii_uppercase + string.digits
            vl = [[[''.join(self.__rnd.choice(chars)
                            for _ in range(self.__rnd.randint(1, 10)))
                    for _ in range(10)]
                   for _ in range(20)]
                  for _ in range(30)]

            strvec.grow(ext=3)
            vv = [[[vl[k][j][i] for i in range(2)] for j in range(2)]
                  for k in range(3)]
            strvec[...] = vv
            self.myAssertVector(strvec.read(), vv)
            vv2 = [[[vl[k][j + 2][i + 2] for i in range(2)]
                    for j in range(2)] for k in range(3)]
            strvec.write(vv2)
            self.myAssertVector(list(strvec[...]), vv2)
            strvec[...] = vv

            strvec.grow()
            self.assertEqual(strvec.shape, (4, 2, 2))
            self.assertEqual(
                strvec.h5object.dataspace.current_dimensions, (4, 2, 2))

            iv = [[[strvec[k, j, i] for i in range(2)]
                   for j in range(2)] for k in range(3)]
            self.myAssertVector(iv, vv)
            strvec[3, :, :] = [[vl[3][j][i] for i in range(2)]
                               for j in range(2)]
            vv3 = [[[vl[k][j][i] for i in range(2)] for j in range(2)]
                   for k in range(4)]
            self.myAssertVector(strvec[...], vv3)

            strvec.grow(2, 3)
            self.assertEqual(strvec.shape, (4, 2, 5))
            self.assertEqual(
                strvec.h5object.dataspace.current_dimensions, (4, 2, 5))
            vv4 = [[[vl[k][j][i + 2] for i in range(3)] for j in range(2)]
                   for k in range(4)]
            vv5 = [[[vl[k][j][i] for i in range(5)] for j in range(2)]
                   for k in range(4)]

            strvec[:, :, 2:5] = vv4
            self.myAssertVector(strvec[...], vv5)
            self.myAssertVector(strvec[:, :, 0:2], vv3)

            strvec.grow(1, 4)
            self.assertEqual(strvec.shape, (4, 6, 5))
            self.assertEqual(
                strvec.h5object.dataspace.current_dimensions, (4, 6, 5))

            vv6 = [[[vl[k][j][i] for i in range(5)] for j in range(6)]
                   for k in range(4)]
            strvec.write(vv6)
            self.myAssertVector(strvec[...], vv6)
            self.myAssertVector(strvec.read(), vv6)

            attrs = strvec.attributes
            self.assertTrue(
                isinstance(attrs, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attrs.h5object, h5cpp._attribute.AttributeManager))
            self.assertEqual(attrs.parent, strvec)
            self.assertEqual(len(attrs), 0)

            self.assertTrue(isinstance(floatvec, H5CppWriter.H5CppField))
            self.assertTrue(isinstance(floatvec.h5object, h5cpp._node.Dataset))
            self.assertEqual(floatvec.name, 'floatvec')
            self.assertEqual(
                floatvec.path,
                '/entry12345:NXentry/instrument:NXinstrument/'
                'detector:NXdetector/floatvec')
            self.assertEqual(floatvec.dtype, 'float64')
            self.assertEqual(floatvec.shape, (1, 20, 10))

            self.assertEqual(floatvec.h5object.link.path.name, 'floatvec')
            self.assertEqual(str(floatvec.h5object.link.path),
                             '/entry12345/instrument/detector/floatvec')
            self.assertEqual(floatvec.h5object.datatype.type.name, 'FLOAT')
            self.assertEqual(floatvec.h5object.dataspace.current_dimensions,
                             (1, 20, 10))

            vl = [[[self.__rnd.uniform(-20000.0, 20000)
                    for _ in range(70)]
                   for _ in range(80)]
                  for _ in range(80)]

            vv = [[[vl[k][j][i] for i in range(10)] for j in range(20)]
                  for k in range(1)]
            floatvec[...] = vv
            self.myAssertVector(floatvec.read(), vv)
            vv2 = [[[vl[k][j + 2][i + 2] for i in range(10)]
                    for j in range(20)] for k in range(1)]
            floatvec.write(vv2)
            self.myAssertVector(floatvec.read(), vv2)

            # !!! PNI self.myAssertVector([floatvec[...]], vv2)
            self.myAssertVector(floatvec[...], vv2)
            floatvec[...] = vv

            floatvec.grow()
            self.assertEqual(floatvec.shape, (2, 20, 10))
            self.assertEqual(floatvec.h5object.dataspace.current_dimensions,
                             (2, 20, 10))

            iv = [[[floatvec[k, j, i] for i in range(10)]
                   for j in range(20)] for k in range(1)]
            self.myAssertVector(iv, vv)
            floatvec[1, :, :] = [[vl[1][j][i] for i in range(10)]
                                 for j in range(20)]
            vv3 = [[[vl[k][j][i] for i in range(10)] for j in range(20)]
                   for k in range(2)]
            self.myAssertVector(floatvec[...], vv3)

            floatvec.grow(2, 3)
            self.assertEqual(floatvec.shape, (2, 20, 13))
            self.assertEqual(
                floatvec.h5object.dataspace.current_dimensions, (2, 20, 13))
            vv4 = [[[vl[k][j][i + 10] for i in range(3)] for j in range(20)]
                   for k in range(2)]
            vv5 = [[[vl[k][j][i] for i in range(13)] for j in range(20)]
                   for k in range(2)]

            floatvec[:, :, 10:13] = vv4
            self.myAssertVector(floatvec[...], vv5)
            self.myAssertVector(floatvec[:, :, 0:10], vv3)

            floatvec.grow(1, 4)
            self.assertEqual(floatvec.shape, (2, 24, 13))
            self.assertEqual(
                floatvec.h5object.dataspace.current_dimensions, (2, 24, 13))

            vv6 = [[[vl[k][j][i] for i in range(13)] for j in range(24)]
                   for k in range(2)]
            floatvec.write(vv6)
            self.myAssertVector(floatvec[...], vv6)
            self.myAssertVector(floatvec.read(), vv6)

            attrs = floatvec.attributes
            self.assertTrue(
                isinstance(attrs, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attrs.h5object, h5cpp._attribute.AttributeManager))
            self.assertEqual(attrs.parent, floatvec)
            self.assertEqual(len(attrs), 0)

            self.assertTrue(isinstance(intvec, H5CppWriter.H5CppField))
            self.assertTrue(isinstance(intvec.h5object, h5cpp._node.Dataset))
            self.assertEqual(intvec.name, 'intvec')
            self.assertEqual(
                intvec.path,
                '/entry12345:NXentry/instrument:NXinstrument/detector:'
                'NXdetector/intvec')
            self.assertEqual(intvec.dtype, 'uint32')
            self.assertEqual(intvec.shape, (0, 2, 30))
            self.assertEqual(intvec.h5object.link.path.name, 'intvec')
            self.assertEqual(
                str(intvec.h5object.link.path),
                '/entry12345/instrument/detector/intvec')
            self.assertEqual(intvec.h5object.datatype.type.name, 'INTEGER')
            self.assertEqual(intvec.h5object.dataspace.current_dimensions,
                             (0, 2, 30))

            vl = [[[self.__rnd.randint(1, 1600)
                    for _ in range(70)]
                   for _ in range(18)]
                  for _ in range(8)]

            intvec.grow()
            vv = [[[vl[k][j][i] for i in range(30)] for j in range(2)]
                  for k in range(1)]

            intvec[...] = vv
            self.myAssertVector(intvec.read(), vv)
            vv2 = [[[vl[k][j + 2][i + 2] for i in range(30)]
                    for j in range(2)] for k in range(1)]
            intvec.write(vv2)
            self.myAssertVector(intvec.read(), vv2)
            # !!! PNI self.myAssertVector([intvec[...]], vv2)
            self.myAssertVector(intvec[...], vv2)
            intvec[...] = vv

            intvec.grow()
            self.assertEqual(intvec.shape, (2, 2, 30))
            self.assertEqual(
                intvec.h5object.dataspace.current_dimensions, (2, 2, 30))

            iv = [[[intvec[k, j, i] for i in range(30)] for j in range(2)]
                  for k in range(1)]
            self.myAssertVector(iv, vv)
            intvec[1, :, :] = [[vl[1][j][i] for i in range(30)]
                               for j in range(2)]
            vv3 = [[[vl[k][j][i] for i in range(30)] for j in range(2)]
                   for k in range(2)]
            self.myAssertVector(intvec[...], vv3)

            intvec.grow(2, 3)
            self.assertEqual(intvec.shape, (2, 2, 33))
            self.assertEqual(
                intvec.h5object.dataspace.current_dimensions, (2, 2, 33))
            vv4 = [[[vl[k][j][i + 30] for i in range(3)] for j in range(2)]
                   for k in range(2)]
            vv5 = [[[vl[k][j][i] for i in range(33)] for j in range(2)]
                   for k in range(2)]

            intvec[:, :, 30:33] = vv4
            self.myAssertVector(intvec[...], vv5)
            self.myAssertVector(intvec[:, :, 0:30], vv3)

            intvec.grow(1, 4)
            self.assertEqual(intvec.shape, (2, 6, 33))
            self.assertEqual(
                intvec.h5object.dataspace.current_dimensions, (2, 6, 33))

            vv6 = [[[vl[k][j][i] for i in range(33)]
                    for j in range(6)] for k in range(2)]
            intvec.write(vv6)
            self.myAssertVector(intvec[...], vv6)
            self.myAssertVector(intvec.read(), vv6)

            attrs = intvec.attributes
            self.assertTrue(
                isinstance(attrs, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attrs.h5object, h5cpp._attribute.AttributeManager))
            self.assertEqual(attrs.parent, intvec)
            self.assertEqual(len(attrs), 0)

            entry.close()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, False)
            self.assertEqual(dt.is_valid, False)

            entry.reopen()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)

            fl.reopen()
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, False)

            fl.close()

            fl.reopen(True)
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, True)

            fl.close()

            # self.myAssertRaise(
            #     Exception, fl.reopen, True, True)
            # self.myAssertRaise(
            #     Exception, fl.reopen, False, True)

            fl = FileWriter.open_file(self._fname, readonly=True)
            f = fl.root()
            self.assertEqual(5, len(f.attributes))
            # atts = []
            for at in f.attributes:
                print("%s %s %s" % (at.name, at.read(), at.dtype))
            self.assertEqual(
                f.attributes["file_name"][...],
                self._fname)
            self.assertTrue(
                f.attributes["NX_class"][...], "NXroot")
            self.assertEqual(f.size, 2)
            fl.close()

        finally:
            os.remove(self._fname)

    # default createfile test
    # \brief It tests default settings
    def test_h5cppdeflate(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        self._fname = '%s/%s%s.h5' % (
            os.getcwd(), self.__class__.__name__, fun)

        try:
            # overwrite = False
            FileWriter.writer = H5CppWriter
            fl = FileWriter.create_file(self._fname)

            rt = fl.root()
            # nt =
            rt.create_group("notype")
            entry = rt.create_group("entry12345", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("detector", "NXdetector")
            # dt =
            entry.create_group("data", "NXdata")

            df0 = FileWriter.data_filter()
            df1 = FileWriter.data_filter()
            df1.rate = 2
            df2 = FileWriter.data_filter()
            df2.rate = 4
            df2.shuffle = True

            # strscalar =
            entry.create_field("strscalar", "string")
            # floatscalar =
            entry.create_field("floatscalar", "float64")
            # intscalar =
            entry.create_field("intscalar", "uint64")
            # strspec =
            ins.create_field("strspec", "string", [10], [6])
            # floatspec =
            ins.create_field("floatspec", "float32", [20], [16])
            # intspec =
            ins.create_field("intspec", "int64", [30], [5])
            # strimage =
            det.create_field("strimage", "string", [2, 2], [2, 1])
            # floatimage =
            det.create_field(
                "floatimage", "float64", [20, 10], dfilter=df0)
            # intimage =
            det.create_field("intimage", "uint32", [0, 30], [1, 30])
            # strvec =
            det.create_field("strvec", "string", [0, 2, 2], [1, 2, 2])
            # floatvec =
            det.create_field(
                "floatvec", "float64", [1, 20, 10], [1, 10, 10], dfilter=df1)
            # intvec =
            det.create_field(
                "intvec", "uint32", [0, 2, 30], dfilter=df2)

            self.assertEqual(df0.rate, 0)
            self.assertEqual(df0.shuffle, False)
            self.assertEqual(df0.parent, None)
            # self.assertTrue(isinstance(df0.h5object, h5cpp._filter.Deflate))
            self.assertEqual(df1.rate, 2)
            self.assertEqual(df1.shuffle, False)
            self.assertEqual(df1.parent, None)
            # self.assertTrue(isinstance(df1.h5object, h5cpp._filter.Deflate))
            self.assertEqual(df2.rate, 4)
            self.assertEqual(df2.shuffle, True)
            self.assertEqual(df2.parent, None)
            # self.assertTrue(isinstance(df2.h5object, h5cpp._filter.Deflate))
        finally:
            os.remove(self._fname)

    # default createfile test
    # \brief It tests default settings
    def test_h5cppattributemanager(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        self._fname = '%s/%s%s.h5' % (
            os.getcwd(), self.__class__.__name__, fun)

        try:
            # overwrite = False
            FileWriter.writer = H5CppWriter
            fl = FileWriter.create_file(self._fname)

            rt = fl.root()
            # nt =
            rt.create_group("notype")
            entry = rt.create_group("entry12345", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("detector", "NXdetector")
            dt = entry.create_group("data", "NXdata")

            df0 = FileWriter.data_filter()
            df1 = FileWriter.data_filter()
            df1.rate = 2
            df2 = FileWriter.data_filter()
            df2.rate = 4
            df2.shuffle = 6

            # strscalar =
            entry.create_field("strscalar", "string")
            # floatscalar =
            entry.create_field("floatscalar", "float64")
            intscalar = entry.create_field("intscalar", "uint64")
            # strspec =
            ins.create_field("strspec", "string", [10], [6])
            # floatspec =
            ins.create_field("floatspec", "float32", [20], [16])
            # intspec =
            ins.create_field("intspec", "int64", [30], [5])
            # strimage =
            det.create_field("strimage", "string", [2, 2], [2, 1])
            # floatimage =
            det.create_field(
                "floatimage", "float64", [20, 10], dfilter=df0)
            # intimage =
            det.create_field("intimage", "uint32", [0, 30], [1, 30])
            # strvec =
            det.create_field("strvec", "string", [0, 2, 2], [1, 2, 2])
            # floatvec =
            det.create_field(
                "floatvec", "float64", [1, 20, 10], [1, 10, 10], dfilter=df1)
            # intvec =
            det.create_field(
                "intvec", "uint32", [0, 2, 30], dfilter=df2)

            # lkintimage =
            FileWriter.link(
                "/entry12345/instrument/detector/intimage", dt, "lkintimage")
            # lkfloatvec =
            FileWriter.link(
                "/entry12345/instrument/detector/floatvec", dt, "lkfloatvec")
            # lkintspec =
            FileWriter.link(
                "/entry12345/instrument/intspec", dt, "lkintspec")
            # lkdet =
            FileWriter.link(
                "/entry12345/instrument/detector", dt, "lkdet")
            # lkno =
            FileWriter.link(
                "/notype/unknown", dt, "lkno")

            attr0 = rt.attributes
            attr1 = entry.attributes
            attr2 = intscalar.attributes

            print(attr0.h5object)
            self.assertTrue(
                isinstance(attr0, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attr0.h5object, h5cpp._attribute.AttributeManager))
            self.assertTrue(
                isinstance(attr1, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(
                    attr1.h5object, h5cpp._attribute.AttributeManager))
            self.assertTrue(
                isinstance(attr2, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(
                    attr2.h5object, h5cpp._attribute.AttributeManager))

            self.assertEqual(len(attr0), 5)
            self.assertEqual(len(attr1), 1)
            self.assertEqual(len(attr2), 0)

            atintscalar = attr0.create("atintscalar", "int64")
            atfloatspec = attr0.create("atfloatspec", "float32", [12])
            atstrimage = attr0.create("atstrimage", "string", [2, 3])
            atstrscalar = attr1.create("atstrscalar", "string")
            atintspec = attr1.create("atintspec", "uint32", [2])
            atfloatimage = attr1.create("atfloatimage", "float64", [3, 2])
            atfloatscalar = attr2.create("atfloatscalar", "float64")
            atstrspec = attr2.create("atstrspec", "string", [4])
            atintimage = attr2.create("atintimage", "int32", [3, 2])

            self.assertEqual(len(attr0), 8)
            self.assertEqual(len(attr1), 4)
            self.assertEqual(len(attr2), 3)

            print(dir(atintscalar))
            print(dir(atintscalar.h5object))

            self.assertTrue(
                isinstance(atintscalar, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atintscalar.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atintscalar.parent, rt)
            self.assertEqual(atintscalar.name, 'atintscalar')
            self.assertEqual(atintscalar.path, '/@atintscalar')
            self.assertEqual(atintscalar.dtype, 'int64')
            self.assertEqual(atintscalar.shape, ())
            self.assertEqual(atintscalar.is_valid, True)
            self.assertEqual(atintscalar.read(), 0)
            self.assertEqual(atintscalar[...], 0)
            self.assertEqual(
                atintscalar.parent.h5object, rt.h5object)
            # self.assertEqual(
            # atintscalar.h5object, (attr0.h5object, 'atintscalar'))

            self.assertTrue(
                isinstance(atfloatspec, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atfloatspec.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atfloatspec.parent, rt)
            self.assertEqual(atfloatspec.name, 'atfloatspec')
            self.assertEqual(atfloatspec.path, '/@atfloatspec')
            self.assertEqual(atfloatspec.dtype, 'float32')
            self.assertEqual(atfloatspec.shape, (12,))
            self.assertEqual(atfloatspec.is_valid, True)
            self.assertEqual(list(atfloatspec.read()), [0.] * 12)
            self.assertEqual(list(atfloatspec[...]), [0.] * 12)
            self.assertEqual(atfloatspec.parent.h5object, rt.h5object)
            # self.assertEqual(
            # atfloatspec.h5object, (attr0.h5object, 'atfloatspec'))

            self.assertTrue(
                isinstance(atstrimage, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atstrimage.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atstrimage.parent, rt)
            self.assertEqual(atstrimage.name, 'atstrimage')
            self.assertEqual(atstrimage.path, '/@atstrimage')
            self.assertEqual(atstrimage.dtype, 'string')
            self.assertEqual(atstrimage.shape, (2, 3))
            self.assertEqual(atstrimage.is_valid, True)
            self.myAssertImage(atstrimage.read(), [[''] * 3] * 2)
            self.myAssertImage(atstrimage[...], [[''] * 3] * 2)
            self.assertEqual(atstrimage.parent.h5object, rt.h5object)
            # self.assertEqual(
            # atstrimage.h5object, (attr0.h5object, 'atstrimage'))

            self.assertTrue(
                isinstance(atstrscalar, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atstrscalar.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atstrscalar.parent, entry)
            self.assertEqual(atstrscalar.name, 'atstrscalar')
            self.assertEqual(
                atstrscalar.path, '/entry12345:NXentry@atstrscalar')
            self.assertEqual(atstrscalar.dtype, 'string')
            self.assertEqual(atstrscalar.shape, ())
            self.assertEqual(atstrscalar.is_valid, True)
            self.assertEqual(atstrscalar.read(), '')
            self.assertEqual(atstrscalar[()], '')
            self.assertEqual(atstrscalar.parent.h5object, entry.h5object)
            # self.assertEqual(
            # atstrscalar.h5object, (attr1.h5object, 'atstrscalar'))

            self.assertTrue(
                isinstance(atintspec, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atintspec.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atintspec.parent, entry)
            self.assertEqual(atintspec.name, 'atintspec')
            self.assertEqual(atintspec.path, '/entry12345:NXentry@atintspec')
            self.assertEqual(atintspec.dtype, 'uint32')
            self.assertEqual(atintspec.shape, (2,))
            self.assertEqual(atintspec.is_valid, True)
            self.assertEqual(list(atintspec.read()), [0] * 2)
            self.assertEqual(list(atintspec[...]), [0] * 2)
            self.assertEqual(atintspec.parent.h5object, entry.h5object)
            # self.assertEqual(
            # atintspec.h5object, (attr1.h5object, 'atintspec'))

            self.assertTrue(
                isinstance(atfloatimage, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atfloatimage.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atfloatimage.parent, entry)
            self.assertEqual(atfloatimage.name, 'atfloatimage')
            self.assertEqual(
                atfloatimage.path, '/entry12345:NXentry@atfloatimage')
            self.assertEqual(atfloatimage.dtype, 'float64')
            self.assertEqual(atfloatimage.shape, (3, 2))
            self.assertEqual(atfloatimage.is_valid, True)
            self.myAssertImage(atfloatimage.read(), [[0.] * 2] * 3)
            self.myAssertImage(atfloatimage[...], [[0.] * 2] * 3)
            self.assertEqual(atfloatimage.parent.h5object, entry.h5object)
            # self.assertEqual(
            # atfloatimage.h5object, (attr1.h5object, 'atfloatimage'))

            self.assertTrue(
                isinstance(atfloatscalar, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atfloatscalar.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atfloatscalar.parent, intscalar)
            self.assertEqual(atfloatscalar.name, 'atfloatscalar')
            self.assertEqual(atfloatscalar.path,
                             '/entry12345:NXentry/intscalar@atfloatscalar')
            self.assertEqual(atfloatscalar.dtype, 'float64')
            self.assertEqual(atfloatscalar.shape, ())
            self.assertEqual(atfloatscalar.is_valid, True)
            self.assertEqual(atfloatscalar.read(), 0)
            self.assertEqual(atfloatscalar[()], 0)
            self.assertEqual(atfloatscalar.parent.h5object, intscalar.h5object)
            # self.assertEqual(
            # atfloatscalar.h5object, (attr2.h5object, 'atfloatscalar'))

            self.assertTrue(isinstance(atstrspec, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atstrspec.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atstrspec.parent, intscalar)
            self.assertEqual(atstrspec.name, 'atstrspec')
            self.assertEqual(atstrspec.path,
                             '/entry12345:NXentry/intscalar@atstrspec')
            self.assertEqual(atstrspec.dtype, 'string')
            self.assertEqual(atstrspec.shape, (4,))
            self.assertEqual(atstrspec.is_valid, True)
            self.assertEqual(list(atstrspec.read()), [''] * 4)
            self.assertEqual(list(atstrspec[...]), [''] * 4)
            self.assertEqual(atstrspec.parent.h5object, intscalar.h5object)
            # self.assertEqual(
            # atstrspec.h5object, (attr2.h5object, 'atstrspec'))

            self.assertTrue(isinstance(atintimage, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atintimage.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atintimage.parent, intscalar)
            self.assertEqual(atintimage.name, 'atintimage')
            self.assertEqual(atintimage.path,
                             '/entry12345:NXentry/intscalar@atintimage')
            self.assertEqual(atintimage.dtype, 'int32')
            self.assertEqual(atintimage.shape, (3, 2))
            self.assertEqual(atintimage.is_valid, True)
            self.myAssertImage(atintimage.read(), [[0] * 2] * 3)
            self.myAssertImage(atintimage[...], [[0] * 2] * 3)
            self.assertEqual(atintimage.parent.h5object, intscalar.h5object)
            # self.assertEqual(
            # atintimage.h5object, (attr2.h5object, 'atintimage'))

            print("WW %s" % attr1["NX_class"].name)

            for at in attr0:
                print(at.name)
            for at in attr1:
                print(at.name)
            for at in attr2:
                print(at.name)

            at = None

            atintscalar = attr0["atintscalar"]
            atfloatspec = attr0["atfloatspec"]
            atstrimage = attr0["atstrimage"]
            atstrscalar = attr1["atstrscalar"]
            atintspec = attr1["atintspec"]
            atfloatimage = attr1["atfloatimage"]
            atfloatscalar = attr2["atfloatscalar"]
            atstrspec = attr2["atstrspec"]
            atintimage = attr2["atintimage"]

            self.assertTrue(
                isinstance(atintscalar, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atintscalar.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atintscalar.parent, rt)
            self.assertEqual(atintscalar.name, 'atintscalar')
            self.assertEqual(atintscalar.path, '/@atintscalar')
            self.assertEqual(atintscalar.dtype, 'int64')
            self.assertEqual(atintscalar.shape, ())
            self.assertEqual(atintscalar.is_valid, True)
            self.assertEqual(atintscalar.read(), 0)
            self.assertEqual(atintscalar[()], 0)
            self.assertEqual(atintscalar.parent.h5object, rt.h5object)
            # self.assertEqual(
            # atintscalar.h5object, (attr0.h5object, 'atintscalar'))

            self.assertTrue(
                isinstance(atfloatspec, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atfloatspec.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atfloatspec.parent, rt)
            self.assertEqual(atfloatspec.name, 'atfloatspec')
            self.assertEqual(atfloatspec.path, '/@atfloatspec')
            self.assertEqual(atfloatspec.dtype, 'float32')
            self.assertEqual(atfloatspec.shape, (12,))
            self.assertEqual(atfloatspec.is_valid, True)
            self.assertEqual(list(atfloatspec.read()), [0.] * 12)
            self.assertEqual(list(atfloatspec[...]), [0.] * 12)
            self.assertEqual(atfloatspec.parent.h5object, rt.h5object)
            # self.assertEqual(
            # atfloatspec.h5object, (attr0.h5object, 'atfloatspec'))

            self.assertTrue(
                isinstance(atstrimage, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atstrimage.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atstrimage.parent, rt)
            self.assertEqual(atstrimage.name, 'atstrimage')
            self.assertEqual(atstrimage.path, '/@atstrimage')
            self.assertEqual(atstrimage.dtype, 'string')
            self.assertEqual(atstrimage.shape, (2, 3))
            self.assertEqual(atstrimage.is_valid, True)
            self.myAssertImage(atstrimage.read(), [[''] * 3] * 2)
            self.myAssertImage(atstrimage[...], [[''] * 3] * 2)
            self.assertEqual(atstrimage.parent.h5object, rt.h5object)
            # self.assertEqual(
            # atstrimage.h5object, (attr0.h5object, 'atstrimage'))

            self.assertTrue(
                isinstance(atstrscalar, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atstrscalar.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atstrscalar.parent, entry)
            self.assertEqual(atstrscalar.name, 'atstrscalar')
            self.assertEqual(
                atstrscalar.path, '/entry12345:NXentry@atstrscalar')
            self.assertEqual(atstrscalar.dtype, 'string')
            self.assertEqual(atstrscalar.shape, ())
            self.assertEqual(atstrscalar.is_valid, True)
            self.assertEqual(atstrscalar.read(), '')
            self.assertEqual(atstrscalar[()], '')
            self.assertEqual(
                atstrscalar.parent.h5object, entry.h5object)
            # self.assertEqual(
            # atstrscalar.h5object, (attr1.h5object, 'atstrscalar'))

            self.assertTrue(
                isinstance(atintspec, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atintspec.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atintspec.parent, entry)
            self.assertEqual(atintspec.name, 'atintspec')
            self.assertEqual(atintspec.path, '/entry12345:NXentry@atintspec')
            self.assertEqual(atintspec.dtype, 'uint32')
            self.assertEqual(atintspec.shape, (2,))
            self.assertEqual(atintspec.is_valid, True)
            self.assertEqual(list(atintspec.read()), [0] * 2)
            self.assertEqual(list(atintspec[...]), [0] * 2)
            self.assertEqual(atintspec.parent.h5object, entry.h5object)
            # self.assertEqual(atintspec.h5object,
            # (attr1.h5object, 'atintspec'))

            self.assertTrue(
                isinstance(atfloatimage, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atfloatimage.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atfloatimage.parent, entry)
            self.assertEqual(atfloatimage.name, 'atfloatimage')
            self.assertEqual(
                atfloatimage.path, '/entry12345:NXentry@atfloatimage')
            self.assertEqual(atfloatimage.dtype, 'float64')
            self.assertEqual(atfloatimage.shape, (3, 2))
            self.assertEqual(atfloatimage.is_valid, True)
            self.myAssertImage(atfloatimage.read(), [[0.] * 2] * 3)
            self.myAssertImage(atfloatimage[...], [[0.] * 2] * 3)
            self.assertEqual(atfloatimage.parent.h5object, entry.h5object)
            # self.assertEqual(
            # atfloatimage.h5object, (attr1.h5object, 'atfloatimage'))

            self.assertTrue(
                isinstance(atfloatscalar, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atfloatscalar.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atfloatscalar.parent, intscalar)
            self.assertEqual(atfloatscalar.name, 'atfloatscalar')
            self.assertEqual(atfloatscalar.path,
                             '/entry12345:NXentry/intscalar@atfloatscalar')
            self.assertEqual(atfloatscalar.dtype, 'float64')
            self.assertEqual(atfloatscalar.shape, ())
            self.assertEqual(atfloatscalar.is_valid, True)
            self.assertEqual(atfloatscalar.read(), 0)
            self.assertEqual(atfloatscalar[()], 0)
            self.assertEqual(atfloatscalar.parent.h5object, intscalar.h5object)
            # self.assertEqual(
            # atfloatscalar.h5object, (attr2.h5object, 'atfloatscalar'))

            self.assertTrue(isinstance(atstrspec, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atstrspec.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atstrspec.parent, intscalar)
            self.assertEqual(atstrspec.name, 'atstrspec')
            self.assertEqual(atstrspec.path,
                             '/entry12345:NXentry/intscalar@atstrspec')
            self.assertEqual(atstrspec.dtype, 'string')
            self.assertEqual(atstrspec.shape, (4,))
            self.assertEqual(atstrspec.is_valid, True)
            self.assertEqual(list(atstrspec.read()), [''] * 4)
            self.assertEqual(list(atstrspec[...]), [''] * 4)
            self.assertEqual(atstrspec.parent.h5object, intscalar.h5object)
            # self.assertEqual(
            # atstrspec.h5object, (attr2.h5object, 'atstrspec'))

            self.assertTrue(isinstance(atintimage, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atintimage.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atintimage.parent, intscalar)
            self.assertEqual(atintimage.name, 'atintimage')
            self.assertEqual(atintimage.path,
                             '/entry12345:NXentry/intscalar@atintimage')
            self.assertEqual(atintimage.dtype, 'int32')
            self.assertEqual(atintimage.shape, (3, 2))
            self.assertEqual(atintimage.is_valid, True)
            self.myAssertImage(atintimage.read(), [[0] * 2] * 3)
            self.myAssertImage(atintimage[...], [[0] * 2] * 3)
            self.assertEqual(atintimage.parent.h5object, intscalar.h5object)
            # self.assertEqual(
            # atintimage.h5object, (attr2.h5object, 'atintimage'))

            self.myAssertRaise(Exception, attr2.create, "atintimage",
                               "uint64", [4])
            atintimage = attr2.create("atintimage", "uint64", [4], True)

            self.assertTrue(isinstance(atintimage, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atintimage.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atintimage.parent, intscalar)
            self.assertEqual(atintimage.name, 'atintimage')
            self.assertEqual(atintimage.path,
                             '/entry12345:NXentry/intscalar@atintimage')
            self.assertEqual(atintimage.dtype, 'uint64')
            self.assertEqual(atintimage.shape, (4,))
            self.assertEqual(atintimage.is_valid, True)
            self.assertEqual(list(atintimage.read()), [0] * 4)
            self.assertEqual(list(atintimage[...]), [0] * 4)
            self.assertEqual(atintimage.parent.h5object, intscalar.h5object)
            # self.assertEqual(atintimage.h5object,
            # (attr2.h5object, 'atintimage'))

            attr2.close()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, True)
            self.assertEqual(atintimage.is_valid, True)

            attr2.reopen()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, True)
            self.assertEqual(atintimage.is_valid, True)

            intscalar.close()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, False)
            self.assertEqual(atintimage.is_valid, False)

            intscalar.reopen()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, True)
            self.assertEqual(atintimage.is_valid, True)

            fl.reopen()
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, False)

            fl.close()

            fl.reopen(True)
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, True)

            fl.close()

            # self.myAssertRaise(
            #     Exception, fl.reopen, True, True)
            # self.myAssertRaise(
            #     Exception, fl.reopen, False, True)

            fl = FileWriter.open_file(self._fname, readonly=True)
            f = fl.root()
#            self.assertEqual(5, len(f.attributes))
            # atts = []
            for at in f.attributes:
                print("%s %s %s" % (at.name, at.read(), at.dtype))
            self.assertEqual(
                f.attributes["file_name"][...],
                self._fname)
            self.assertTrue(
                f.attributes["NX_class"][...], "NXroot")
            self.assertEqual(f.size, 2)
            fl.close()

        finally:
            os.remove(self._fname)

    # default createfile test
    # \brief It tests default settings
    def test_h5cppattribute_scalar(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        self._fname = '%s/%s%s.h5' % (
            os.getcwd(), self.__class__.__name__, fun)

        try:
            # overwrite = False
            FileWriter.writer = H5CppWriter
            fl = FileWriter.create_file(self._fname)

            rt = fl.root()
            # nt =
            rt.create_group("notype")
            entry = rt.create_group("entry12345", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("detector", "NXdetector")
            dt = entry.create_group("data", "NXdata")

            df0 = FileWriter.data_filter()
            df1 = FileWriter.data_filter()
            df1.rate = 2
            df2 = FileWriter.data_filter()
            df2.rate = 4
            df2.shuffle = 6

            # strscalar =
            entry.create_field("strscalar", "string")
            # floatscalar =
            entry.create_field("floatscalar", "float64")
            intscalar = entry.create_field("intscalar", "uint64")
            # strspec =
            ins.create_field("strspec", "string", [10], [6])
            # floatspec =
            ins.create_field("floatspec", "float32", [20], [16])
            # intspec =
            ins.create_field("intspec", "int64", [30], [5])
            # strimage =
            det.create_field("strimage", "string", [2, 2], [2, 1])
            # floatimage =
            det.create_field(
                "floatimage", "float64", [20, 10], dfilter=df0)
            # intimage =
            det.create_field("intimage", "uint32", [0, 30], [1, 30])
            # strvec =
            det.create_field("strvec", "string", [0, 2, 2], [1, 2, 2])
            # floatvec =
            det.create_field(
                "floatvec", "float64", [1, 20, 10], [1, 10, 10], dfilter=df1)
            # intvec =
            det.create_field(
                "intvec", "uint32", [0, 2, 30], dfilter=df2)

            # lkintimage =
            FileWriter.link(
                "/entry12345/instrument/detector/intimage", dt, "lkintimage")
            # lkfloatvec =
            FileWriter.link(
                "/entry12345/instrument/detector/floatvec", dt, "lkfloatvec")
            # lkintspec =
            FileWriter.link(
                "/entry12345/instrument/intspec", dt, "lkintspec")
            # lkdet =
            FileWriter.link(
                "/entry12345/instrument/detector", dt, "lkdet")
            # lkno =
            FileWriter.link(
                "/notype/unknown", dt, "lkno")

            attr0 = rt.attributes
            attr1 = entry.attributes
            attr2 = intscalar.attributes

            print(attr0.h5object)
            self.assertTrue(isinstance(attr0,
                                       H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attr0.h5object, h5cpp._attribute.AttributeManager))
            self.assertTrue(isinstance(attr1,
                                       H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attr1.h5object, h5cpp._attribute.AttributeManager))
            self.assertTrue(isinstance(attr2,
                                       H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attr2.h5object, h5cpp._attribute.AttributeManager))

            self.assertEqual(len(attr0), 5)
            self.assertEqual(len(attr1), 1)
            self.assertEqual(len(attr2), 0)

            atintscalar = attr0.create("atintscalar", "int64")
            # atfloatspec =
            attr0.create("atfloatspec", "float32", [12])
            # atstrimage =
            attr0.create("atstrimage", "string", [2, 3])
            atstrscalar = attr1.create("atstrscalar", "string")
            # atintspec =
            attr1.create("atintspec", "uint32", [2])
            # atfloatimage =
            attr1.create("atfloatimage", "float64", [3, 2])
            atfloatscalar = attr2.create("atfloatscalar", "float64")
            # atstrspec =
            attr2.create("atstrspec", "string", [4])
            atintimage = attr2.create("atintimage", "int32", [3, 2])

            self.assertEqual(len(attr0), 8)
            self.assertEqual(len(attr1), 4)
            self.assertEqual(len(attr2), 3)

            print(dir(atintscalar))
            print(dir(atintscalar.h5object))

            chars = string.ascii_uppercase + string.digits
            stvl = [
                ''.join(self.__rnd.choice(chars)
                        for _ in range(self.__rnd.randint(1, 10)))
                for _ in range(10)]
            itvl = [self.__rnd.randint(1, 16000) for _ in range(100)]

            flvl = [self.__rnd.uniform(-200.0, 200) for _ in range(80)]

            atintscalar.write(itvl[0])

            self.assertTrue(
                isinstance(atintscalar, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atintscalar.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atintscalar.parent, rt)
            self.assertEqual(atintscalar.name, 'atintscalar')
            self.assertEqual(atintscalar.path, '/@atintscalar')
            self.assertEqual(atintscalar.dtype, 'int64')
            self.assertEqual(atintscalar.shape, ())
            self.assertEqual(atintscalar.is_valid, True)
            self.assertEqual(atintscalar.read(), itvl[0])
            self.assertEqual(atintscalar[()], itvl[0])
            self.assertEqual(atintscalar.parent.h5object, rt.h5object)
            # self.assertEqual(atintscalar.h5object,
            # (attr0.h5object, 'atintscalar'))

            atintscalar[...] = itvl[1]

            self.assertEqual(atintscalar.h5object.read(), itvl[1])
            self.assertEqual(atintscalar.h5object[()], itvl[1])
            self.assertEqual(atintscalar.read(), itvl[1])
            self.assertEqual(atintscalar[...], itvl[1])

            atintscalar[:] = itvl[2]

            self.assertEqual(atintscalar.h5object.read(), itvl[2])
            self.assertEqual(atintscalar.h5object[...], itvl[2])
            self.assertEqual(atintscalar.read(), itvl[2])
            self.assertEqual(atintscalar[...], itvl[2])

            atintscalar[0] = itvl[3]

            self.assertEqual(atintscalar.h5object.read(), itvl[3])
            self.assertEqual(atintscalar.h5object[...], itvl[3])
            self.assertEqual(atintscalar.read(), itvl[3])
            self.assertEqual(atintscalar[...], itvl[3])

            print("%s %s" % (stvl[0], type(stvl[0])))

            atstrscalar.write(stvl[0])

            self.assertTrue(
                isinstance(atstrscalar, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atstrscalar.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atstrscalar.parent, entry)
            self.assertEqual(atstrscalar.name, 'atstrscalar')
            self.assertEqual(
                atstrscalar.path, '/entry12345:NXentry@atstrscalar')
            self.assertEqual(atstrscalar.dtype, 'string')
            self.assertEqual(atstrscalar.shape, ())
            self.assertEqual(atstrscalar.is_valid, True)
            self.assertEqual(atstrscalar.read(), stvl[0])
            self.assertEqual(atstrscalar[()], stvl[0])
            self.assertEqual(atstrscalar.parent.h5object, entry.h5object)

            atstrscalar[...] = stvl[1]

            self.assertEqual(atstrscalar.h5object.read(), stvl[1])
            self.assertEqual(atstrscalar.h5object[()], stvl[1])
            self.assertEqual(atstrscalar.read(), stvl[1])
            self.assertEqual(atstrscalar[()], stvl[1])

            atstrscalar[:] = stvl[2]

            self.assertEqual(atstrscalar.h5object.read(), stvl[2])
            self.assertEqual(atstrscalar.h5object[...], stvl[2])
            self.assertEqual(atstrscalar.read(), stvl[2])
            self.assertEqual(atstrscalar[...], stvl[2])

            atstrscalar[0] = stvl[3]

            self.assertEqual(atstrscalar.h5object.read(), stvl[3])
            self.assertEqual(atstrscalar.h5object[...], stvl[3])
            self.assertEqual(atstrscalar.read(), stvl[3])
            self.assertEqual(atstrscalar[...], stvl[3])

            atfloatscalar.write(flvl[0])

            self.assertTrue(
                isinstance(atfloatscalar, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atfloatscalar.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atfloatscalar.parent, intscalar)
            self.assertEqual(atfloatscalar.name, 'atfloatscalar')
            self.assertEqual(atfloatscalar.path,
                             '/entry12345:NXentry/intscalar@atfloatscalar')
            self.assertEqual(atfloatscalar.dtype, 'float64')
            self.assertEqual(atfloatscalar.shape, ())
            self.assertEqual(atfloatscalar.is_valid, True)
            self.assertEqual(atfloatscalar.read(), flvl[0])
            self.assertEqual(atfloatscalar[()], flvl[0])
            self.assertEqual(atfloatscalar.parent.h5object, intscalar.h5object)

            atfloatscalar[...] = flvl[1]

            self.assertEqual(atfloatscalar.h5object.read(), flvl[1])
            self.assertEqual(atfloatscalar.read(), flvl[1])
            self.assertEqual(atfloatscalar[...], flvl[1])

            atfloatscalar[:] = flvl[2]

            self.assertEqual(atfloatscalar.h5object.read(), flvl[2])
            self.assertEqual(atfloatscalar.read(), flvl[2])
            self.assertEqual(atfloatscalar[...], flvl[2])

            atfloatscalar[0] = flvl[3]

            self.assertEqual(atfloatscalar.h5object.read(), flvl[3])
            self.assertEqual(atfloatscalar.read(), flvl[3])
            self.assertEqual(atfloatscalar[...], flvl[3])

            atfloatscalar.close()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, True)
            self.assertEqual(atfloatscalar.is_valid, False)

            atfloatscalar.reopen()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, True)
            self.assertEqual(atfloatscalar.is_valid, True)

            intscalar.close()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, False)
            self.assertEqual(atintimage.is_valid, False)
            self.assertEqual(atfloatscalar.is_valid, False)

            intscalar.reopen()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, True)
            self.assertEqual(atintimage.is_valid, True)
            self.assertEqual(atfloatscalar.is_valid, True)

            fl.reopen()
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, False)

            fl.close()

            fl.reopen(True)
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, True)

            fl.close()

            # self.myAssertRaise(
            #     Exception, fl.reopen, True, True)
            # self.myAssertRaise(
            #     Exception, fl.reopen, False, True)

            fl = FileWriter.open_file(self._fname, readonly=True)
            f = fl.root()
#            self.assertEqual(5, len(f.attributes))
            for at in f.attributes:
                print("%s %s %s" % (at.name, at.read(), at.dtype))
            self.assertEqual(
                f.attributes["file_name"][...],
                self._fname)
            self.assertTrue(
                f.attributes["NX_class"][...], "NXroot")
            self.assertEqual(f.size, 2)
            fl.close()

        finally:
            os.remove(self._fname)

    # default createfile test
    # \brief It tests default settings
    def test_h5cppattribute_spectrum(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        self._fname = '%s/%s%s.h5' % (
            os.getcwd(), self.__class__.__name__, fun)

        try:
            # overwrite = False
            FileWriter.writer = H5CppWriter
            fl = FileWriter.create_file(self._fname)

            rt = fl.root()
            # nt =
            rt.create_group("notype")
            entry = rt.create_group("entry12345", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("detector", "NXdetector")
            dt = entry.create_group("data", "NXdata")

            df0 = FileWriter.data_filter()
            df1 = FileWriter.data_filter()
            df1.rate = 2
            df2 = FileWriter.data_filter()
            df2.rate = 4
            df2.shuffle = 6

            # strscalar =
            entry.create_field("strscalar", "string")
            # floatscalar =
            entry.create_field("floatscalar", "float64")
            intscalar = entry.create_field("intscalar", "uint64")
            # strspec =
            ins.create_field("strspec", "string", [10], [6])
            # floatspec =
            ins.create_field("floatspec", "float32", [20], [16])
            # intspec =
            ins.create_field("intspec", "int64", [30], [5])
            # strimage =
            det.create_field("strimage", "string", [2, 2], [2, 1])
            # floatimage =
            det.create_field(
                "floatimage", "float64", [20, 10], dfilter=df0)
            # intimage =
            det.create_field("intimage", "uint32", [0, 30], [1, 30])
            # strvec =
            det.create_field("strvec", "string", [0, 2, 2], [1, 2, 2])
            # floatvec =
            det.create_field(
                "floatvec", "float64", [1, 20, 10], [1, 10, 10], dfilter=df1)
            # intvec =
            det.create_field(
                "intvec", "uint32", [0, 2, 30], dfilter=df2)

            # lkintimage =
            FileWriter.link(
                "/entry12345/instrument/detector/intimage", dt, "lkintimage")
            # lkfloatvec =
            FileWriter.link(
                "/entry12345/instrument/detector/floatvec", dt, "lkfloatvec")
            # lkintspec =
            FileWriter.link(
                "/entry12345/instrument/intspec", dt, "lkintspec")
            # lkdet =
            FileWriter.link(
                "/entry12345/instrument/detector", dt, "lkdet")
            # lkno =
            FileWriter.link(
                "/notype/unknown", dt, "lkno")

            attr0 = rt.attributes
            attr1 = entry.attributes
            attr2 = intscalar.attributes

            print(attr0.h5object)
            self.assertTrue(
                isinstance(attr0, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attr0.h5object, h5cpp._attribute.AttributeManager))
            self.assertTrue(
                isinstance(attr1, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attr1.h5object, h5cpp._attribute.AttributeManager))
            self.assertTrue(
                isinstance(attr2, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attr2.h5object, h5cpp._attribute.AttributeManager))

            self.assertEqual(len(attr0), 5)
            self.assertEqual(len(attr1), 1)
            self.assertEqual(len(attr2), 0)

            atintscalar = attr0.create("atintscalar", "int64")
            atfloatspec = attr0.create("atfloatspec", "float32", [12])
            # atstrimage =
            attr0.create("atstrimage", "string", [2, 3])
            # atstrscalar =
            attr1.create("atstrscalar", "string")
            atintspec = attr1.create("atintspec", "uint32", [2])
            # atfloatimage =
            attr1.create("atfloatimage", "float64", [3, 2])
            # atfloatscalar =
            attr2.create("atfloatscalar", "float64")
            atstrspec = attr2.create("atstrspec", "string", [4])
            atintimage = attr2.create("atintimage", "int32", [3, 2])

            self.assertEqual(len(attr0), 8)
            self.assertEqual(len(attr1), 4)
            self.assertEqual(len(attr2), 3)

            print(dir(atintscalar))
            print(dir(atintscalar.h5object))

            chars = string.ascii_uppercase + string.digits
            stvl = [[
                ''.join(self.__rnd.choice(chars)
                        for _ in range(self.__rnd.randint(1, 10)))
                for _ in range(4)]
                    for _ in range(10)]

            itvl = [[self.__rnd.randint(1, 16000)
                     for _ in range(2)] for _ in range(10)]

            flvl = [[self.__rnd.uniform(-200.0, 200)
                     for _ in range(12)] for _ in range(10)]

            atfloatspec.write(flvl[0])

            self.assertTrue(
                isinstance(atfloatspec, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atfloatspec.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atfloatspec.parent, rt)
            self.assertEqual(atfloatspec.name, 'atfloatspec')
            self.assertEqual(atfloatspec.path, '/@atfloatspec')
            self.assertEqual(atfloatspec.dtype, 'float32')
            self.assertEqual(atfloatspec.shape, (12,))
            self.assertEqual(atfloatspec.is_valid, True)
            self.myAssertFloatList(list(atfloatspec.read()), flvl[0], 1e-3)
            self.myAssertFloatList(list(atfloatspec[...]), flvl[0], 1e-3)
            self.assertEqual(atfloatspec.parent.h5object, rt.h5object)

            atfloatspec[...] = flvl[1]

            self.myAssertFloatList(
                list(atfloatspec.h5object.read()), flvl[1], 1e-3)
            self.myAssertFloatList(list(atfloatspec.read()), flvl[1], 1e-3)
            self.myAssertFloatList(list(atfloatspec[...]), flvl[1], 1e-3)

            atfloatspec[:] = flvl[2]

            self.myAssertFloatList(
                list(atfloatspec.h5object.read()), flvl[2], 1e-3)
            self.myAssertFloatList(list(atfloatspec.read()), flvl[2], 1e-3)
            self.myAssertFloatList(list(atfloatspec[...]), flvl[2], 1e-3)

            atfloatspec[0:12] = flvl[3]

            self.myAssertFloatList(
                list(atfloatspec.h5object.read()), flvl[3], 1e-3)
            self.myAssertFloatList(list(atfloatspec.read()), flvl[3], 1e-3)
            self.myAssertFloatList(list(atfloatspec[...]), flvl[3], 1e-3)

            atfloatspec[1:10] = flvl[4][1:10]

            self.myAssertFloatList(list(atfloatspec.h5object.read()[1:10]),
                                   flvl[4][1:10], 1e-3)
            self.myAssertFloatList(
                list(atfloatspec.read()[1:10]), flvl[4][1:10], 1e-3)
            self.myAssertFloatList(
                list(atfloatspec[1:10]), flvl[4][1:10], 1e-3)

            atfloatspec[1:10] = flvl[3][1:10]

            self.myAssertFloatList(
                list(atfloatspec.h5object.read()), flvl[3], 1e-3)
            self.myAssertFloatList(list(atfloatspec.read()), flvl[3], 1e-3)
            self.myAssertFloatList(list(atfloatspec[...]), flvl[3], 1e-3)

            atintspec.write(itvl[0])

            self.assertTrue(isinstance(atintspec, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atintspec.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atintspec.parent, entry)
            self.assertEqual(atintspec.name, 'atintspec')
            self.assertEqual(atintspec.path, '/entry12345:NXentry@atintspec')
            self.assertEqual(atintspec.dtype, 'uint32')
            self.assertEqual(atintspec.shape, (2,))
            self.assertEqual(atintspec.is_valid, True)
            self.assertEqual(list(atintspec.read()), itvl[0])
            self.assertEqual(list(atintspec[...]), itvl[0])
            self.assertEqual(atintspec.parent.h5object, entry.h5object)

            atintspec[...] = itvl[1]

            self.assertEqual(list(atintspec.h5object.read()), itvl[1])
            self.assertEqual(list(atintspec.read()), itvl[1])
            self.assertEqual(list(atintspec[...]), itvl[1])

            atintspec[:] = itvl[2]

            self.assertEqual(list(atintspec.h5object.read()), itvl[2])
            self.assertEqual(list(atintspec.read()), itvl[2])
            self.assertEqual(list(atintspec[...]), itvl[2])

            atintspec[0:2] = itvl[3]

            self.assertEqual(list(atintspec.h5object.read()), itvl[3])
            self.assertEqual(list(atintspec.read()), itvl[3])
            self.assertEqual(list(atintspec[...]), itvl[3])

            atintspec[1:] = itvl[4][1:]

            self.assertEqual(list(atintspec.h5object.read()[1:]), itvl[4][1:])
            self.assertEqual([atintspec.read()[1:]], itvl[4][1:])
            self.assertEqual([atintspec[1:]], itvl[4][1:])

            atintspec[1:] = itvl[3][1:]

            self.assertEqual(list(atintspec.h5object.read()), itvl[3])
            self.assertEqual(list(atintspec.read()), itvl[3])
            self.assertEqual(list(atintspec[...]), itvl[3])

            atstrspec.write(stvl[0])

            self.assertTrue(isinstance(atstrspec, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atstrspec.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atstrspec.parent, intscalar)
            self.assertEqual(atstrspec.name, 'atstrspec')
            self.assertEqual(atstrspec.path,
                             '/entry12345:NXentry/intscalar@atstrspec')
            self.assertEqual(atstrspec.dtype, 'string')
            self.assertEqual(atstrspec.shape, (4,))
            self.assertEqual(atstrspec.is_valid, True)
            self.assertEqual(list(atstrspec.read()), stvl[0])
            self.assertEqual(list(atstrspec[...]), stvl[0])
            self.assertEqual(atstrspec.parent.h5object, intscalar.h5object)

            atstrspec[...] = stvl[1]

            self.assertEqual(list(atstrspec.h5object.read()), stvl[1])
            self.assertEqual(list(atstrspec.read()), stvl[1])
            self.assertEqual(list(atstrspec[...]), stvl[1])

            atstrspec[:] = stvl[2]

            self.assertEqual(list(atstrspec.h5object.read()), stvl[2])
            self.assertEqual(list(atstrspec.read()), stvl[2])
            self.assertEqual(list(atstrspec[...]), stvl[2])

            atstrspec[0:4] = stvl[3]

            self.assertEqual(list(atstrspec.h5object.read()), stvl[3])
            self.assertEqual(list(atstrspec.read()), stvl[3])
            self.assertEqual(list(atstrspec[...]), stvl[3])

            atstrspec[:3] = stvl[4][:3]

            self.assertEqual(list(atstrspec.h5object.read()[:3]), stvl[4][:3])
            self.assertEqual(list(atstrspec.read())[:3], stvl[4][:3])
            self.assertEqual(list(atstrspec[:3]), stvl[4][:3])

            atstrspec[:3] = stvl[3][:3]

            self.assertEqual(list(atstrspec.h5object.read()), stvl[3])
            self.assertEqual(list(atstrspec.read()), stvl[3])
            self.assertEqual(list(atstrspec[...]), stvl[3])

            atfloatspec.close()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, True)
            self.assertEqual(atintimage.is_valid, True)
            self.assertEqual(atfloatspec.is_valid, False)

            atfloatspec.reopen()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, True)
            self.assertEqual(atintimage.is_valid, True)
            self.assertEqual(atfloatspec.is_valid, True)

            intscalar.close()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, False)
            self.assertEqual(atintimage.is_valid, False)
            self.assertEqual(atfloatspec.is_valid, True)

            intscalar.reopen()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, True)
            self.assertEqual(atintimage.is_valid, True)
            self.assertEqual(atfloatspec.is_valid, True)

            fl.reopen()
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, False)

            fl.close()

            fl.reopen(True)
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, True)

            fl.close()

            # self.myAssertRaise(
            #     Exception, fl.reopen, True, True)
            # self.myAssertRaise(
            #     Exception, fl.reopen, False, True)

            fl = FileWriter.open_file(self._fname, readonly=True)
            f = fl.root()
            #            self.assertEqual(5, len(f.attributes))
            # atts = []
            for at in f.attributes:
                print("%s %s %s" % (at.name, at.read(), at.dtype))
            self.assertEqual(
                f.attributes["file_name"][...],
                self._fname)
            self.assertTrue(
                f.attributes["NX_class"][...], "NXroot")
            self.assertEqual(f.size, 2)
            fl.close()

        finally:
            os.remove(self._fname)

    # default createfile test
    # \brief It tests default settings
    def test_h5cppattribute_image(self):
        fun = sys._getframe().f_code.co_name
        print("Run: %s.%s() " % (self.__class__.__name__, fun))
        self._fname = '%s/%s%s.h5' % (
            os.getcwd(), self.__class__.__name__, fun)

        try:
            # overwrite = False
            FileWriter.writer = H5CppWriter
            fl = FileWriter.create_file(self._fname)

            rt = fl.root()
            # nt =
            rt.create_group("notype")
            entry = rt.create_group("entry12345", "NXentry")
            ins = entry.create_group("instrument", "NXinstrument")
            det = ins.create_group("detector", "NXdetector")
            dt = entry.create_group("data", "NXdata")

            df0 = FileWriter.data_filter()
            df1 = FileWriter.data_filter()
            df1.rate = 2
            df2 = FileWriter.data_filter()
            df2.rate = 4
            df2.shuffle = 6

            # strscalar =
            entry.create_field("strscalar", "string")
            # floatscalar =
            entry.create_field("floatscalar", "float64")
            intscalar = entry.create_field("intscalar", "uint64")
            # strspec =
            ins.create_field("strspec", "string", [10], [6])
            # floatspec =
            ins.create_field("floatspec", "float32", [20], [16])
            # intspec =
            ins.create_field("intspec", "int64", [30], [5])
            # strimage =
            det.create_field("strimage", "string", [2, 2], [2, 1])
            # floatimage =
            det.create_field(
                "floatimage", "float64", [20, 10], dfilter=df0)
            # intimage =
            det.create_field("intimage", "uint32", [0, 30], [1, 30])
            # strvec =
            det.create_field("strvec", "string", [0, 2, 2], [1, 2, 2])
            # floatvec =
            det.create_field(
                "floatvec", "float64", [1, 20, 10], [1, 10, 10], dfilter=df1)
            # intvec =
            det.create_field(
                "intvec", "uint32", [0, 2, 30], dfilter=df2)

            # lkintimage =
            FileWriter.link(
                "/entry12345/instrument/detector/intimage", dt, "lkintimage")
            # lkfloatvec =
            FileWriter.link(
                "/entry12345/instrument/detector/floatvec", dt, "lkfloatvec")
            # lkintspec =
            FileWriter.link(
                "/entry12345/instrument/intspec", dt, "lkintspec")
            # lkdet =
            FileWriter.link(
                "/entry12345/instrument/detector", dt, "lkdet")
            # lkno =
            FileWriter.link(
                "/notype/unknown", dt, "lkno")

            attr0 = rt.attributes
            attr1 = entry.attributes
            attr2 = intscalar.attributes

            print(attr0.h5object)
            self.assertTrue(
                isinstance(attr0, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attr0.h5object, h5cpp._attribute.AttributeManager))
            self.assertTrue(
                isinstance(attr1, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attr1.h5object, h5cpp._attribute.AttributeManager))
            self.assertTrue(
                isinstance(attr2, H5CppWriter.H5CppAttributeManager))
            self.assertTrue(
                isinstance(attr2.h5object, h5cpp._attribute.AttributeManager))

            self.assertEqual(len(attr0), 5)
            self.assertEqual(len(attr1), 1)
            self.assertEqual(len(attr2), 0)

            atintscalar = attr0.create("atintscalar", "int64")
            # atfloatspec =
            attr0.create("atfloatspec", "float32", [12])
            atstrimage = attr0.create("atstrimage", "string", [2, 3])
            # atstrscalar =
            attr1.create("atstrscalar", "string")
            # atintspec =
            attr1.create("atintspec", "uint32", [2])
            atfloatimage = attr1.create("atfloatimage", "float64", [3, 2])
            # atfloatscalar =
            attr2.create("atfloatscalar", "float64")
            # atstrspec =
            attr2.create("atstrspec", "string", [4])
            atintimage = attr2.create("atintimage", "int32", [3, 2])

            self.assertEqual(len(attr0), 8)
            self.assertEqual(len(attr1), 4)
            self.assertEqual(len(attr2), 3)

            print(dir(atintscalar))
            print(dir(atintscalar.h5object))

            chars = string.ascii_uppercase + string.digits
            stvl = [[[
                ''.join(self.__rnd.choice(chars)
                        for _ in range(self.__rnd.randint(1, 10)))
                for _ in range(3)]
                    for _ in range(2)] for _ in range(10)]

            itvl = [[[self.__rnd.randint(1, 16000) for _ in range(2)]
                     for _ in range(3)] for _ in range(10)]

            flvl = [[[self.__rnd.uniform(-200.0, 200) for _ in range(2)]
                     for _ in range(3)]
                    for _ in range(10)]

            atstrimage.write(stvl[0])

            self.assertTrue(
                isinstance(atstrimage, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atstrimage.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atstrimage.parent, rt)
            self.assertEqual(atstrimage.name, 'atstrimage')
            self.assertEqual(atstrimage.path, '/@atstrimage')
            self.assertEqual(atstrimage.dtype, 'string')
            self.assertEqual(atstrimage.shape, (2, 3))
            self.assertEqual(atstrimage.is_valid, True)
            self.myAssertImage(atstrimage.read(), stvl[0])
            self.myAssertImage(atstrimage[...], stvl[0])
            self.assertEqual(atstrimage.parent.h5object, rt.h5object)

            atstrimage[...] = stvl[1]

            self.myAssertImage(atstrimage.h5object.read(), stvl[1])
            self.myAssertImage(atstrimage.read(), stvl[1])
            self.myAssertImage(atstrimage[:, :], stvl[1])

            atstrimage[:, :] = stvl[2]

            self.myAssertImage(atstrimage.read(), stvl[2])
            self.myAssertImage(atstrimage[...], stvl[2])
            self.myAssertImage(atstrimage.h5object.read(), stvl[2])

            atstrimage[0:2, :] = stvl[3]

            self.myAssertImage(atstrimage.read(), stvl[3])
            self.myAssertImage(atstrimage[...], stvl[3])
            self.myAssertImage(atstrimage.h5object.read(), stvl[3])

            vv1 = [[stvl[4][j][i] for i in range(2)] for j in range(2)]

            print("TR %s" % str(atstrimage.read()))

            print("TRct", atstrimage[:, 1:])

            atstrimage[:, 1:] = vv1

            print("VV1 %s" % vv1)
            print("TR1 ", atstrimage[:, :])
            print("TR2 ", atstrimage[:, 1:])
            self.myAssertImage(atstrimage.read()[:, 1:], vv1)
            self.myAssertImage(atstrimage[:, 1:], vv1)
            self.myAssertImage(atstrimage.h5object.read()[:, 1:], vv1)

            vv2 = [[stvl[3][j][i + 1] for i in range(2)] for j in range(2)]
            atstrimage[:, 1:] = vv2

            self.myAssertImage(atstrimage.read(), stvl[3])
            self.myAssertImage(atstrimage[...], stvl[3])
            self.myAssertImage(atstrimage.h5object.read(), stvl[3])

            atfloatimage.write(flvl[0])

            self.assertTrue(
                isinstance(atfloatimage, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atfloatimage.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atfloatimage.parent, entry)
            self.assertEqual(atfloatimage.name, 'atfloatimage')
            self.assertEqual(
                atfloatimage.path, '/entry12345:NXentry@atfloatimage')
            self.assertEqual(atfloatimage.dtype, 'float64')
            self.assertEqual(atfloatimage.shape, (3, 2))
            self.assertEqual(atfloatimage.is_valid, True)
            self.myAssertImage(atfloatimage.read(), flvl[0])
            self.myAssertImage(atfloatimage[...], flvl[0])
            self.assertEqual(atfloatimage.parent.h5object, entry.h5object)

            atfloatimage[...] = flvl[1]

            self.myAssertImage(atfloatimage.read(), flvl[1])
            self.myAssertImage(atfloatimage[:, :], flvl[1])
            self.myAssertImage(atfloatimage.h5object.read(), flvl[1])

            atfloatimage[:, :] = flvl[2]

            self.myAssertImage(atfloatimage.read(), flvl[2])
            self.myAssertImage(atfloatimage[...], flvl[2])
            self.myAssertImage(atfloatimage.h5object.read(), flvl[2])

            atfloatimage[0:3, :] = flvl[3]

            self.myAssertImage(atfloatimage.read(), flvl[3])
            self.myAssertImage(atfloatimage[...], flvl[3])
            self.myAssertImage(atfloatimage.h5object.read(), flvl[3])

            vv1 = [[flvl[4][j][i] for i in range(2)] for j in range(2)]
            atfloatimage[1:, :] = vv1

            self.myAssertImage(atfloatimage.read()[1:, :], vv1)
            self.myAssertImage(atfloatimage[1:, :], vv1)
            self.myAssertImage(atfloatimage.h5object.read()[1:, :], vv1)

            vv2 = [[flvl[3][j + 1][i] for i in range(2)] for j in range(2)]
            atfloatimage[1:, :] = vv2

            self.myAssertImage(atfloatimage.read(), flvl[3])
            self.myAssertImage(atfloatimage[...], flvl[3])
            self.myAssertImage(atfloatimage.h5object.read(), flvl[3])

            atintimage.write(itvl[0])

            self.assertTrue(isinstance(atintimage, H5CppWriter.H5CppAttribute))
            self.assertTrue(
                isinstance(atintimage.h5object, h5cpp._attribute.Attribute))
            self.assertEqual(atintimage.parent, intscalar)
            self.assertEqual(atintimage.name, 'atintimage')
            self.assertEqual(atintimage.path,
                             '/entry12345:NXentry/intscalar@atintimage')
            self.assertEqual(atintimage.dtype, 'int32')
            self.assertEqual(atintimage.shape, (3, 2))
            self.assertEqual(atintimage.is_valid, True)
            self.myAssertImage(atintimage.read(), itvl[0])
            self.myAssertImage(atintimage[...], itvl[0])
            self.assertEqual(atintimage.parent.h5object, intscalar.h5object)

            atintimage[...] = itvl[1]

            self.myAssertImage(atintimage.read(), itvl[1])
            self.myAssertImage(atintimage[:, :], itvl[1])
            self.myAssertImage(atintimage.h5object.read(), itvl[1])

            atintimage[:, :] = itvl[2]

            self.myAssertImage(atintimage.read(), itvl[2])
            self.myAssertImage(atintimage[...], itvl[2])
            self.myAssertImage(atintimage.h5object.read(), itvl[2])

            atintimage[0:3, :] = itvl[3]

            self.myAssertImage(atintimage.read(), itvl[3])
            self.myAssertImage(atintimage[...], itvl[3])
            self.myAssertImage(atintimage.h5object.read(), itvl[3])

            vv1 = [[itvl[4][j][i] for i in range(2)] for j in range(2)]
            atintimage[1:, :] = vv1

            self.myAssertImage(atintimage.read()[1:, :], vv1)
            self.myAssertImage(atintimage[1:, :], vv1)
            self.myAssertImage(atintimage.h5object.read()[1:, :], vv1)

            vv2 = [[itvl[3][j + 1][i] for i in range(2)] for j in range(2)]
            atintimage[1:, :] = vv2

            self.myAssertImage(atintimage.read(), itvl[3])
            self.myAssertImage(atintimage[...], itvl[3])
            self.myAssertImage(atintimage.h5object.read(), itvl[3])

            atintimage.close()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, True)
            self.assertEqual(atintimage.is_valid, False)

            atintimage.reopen()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, True)
            self.assertEqual(atintimage.is_valid, True)

            intscalar.close()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, False)
            self.assertEqual(atintimage.is_valid, False)

            intscalar.reopen()
            self.assertEqual(rt.is_valid, True)
            self.assertEqual(entry.is_valid, True)
            self.assertEqual(dt.is_valid, True)
            self.assertEqual(attr2.is_valid, True)
            self.assertEqual(atintimage.is_valid, True)

            fl.reopen()
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, False)

            fl.close()

            fl.reopen(True)
            self.assertEqual(fl.name, self._fname)
            self.assertEqual(fl.path, self._fname)
            self.assertTrue(
                isinstance(fl.h5object, h5cpp._file.File))
            self.assertEqual(fl.parent, None)
            self.assertEqual(fl.readonly, True)

            fl.close()

            # self.myAssertRaise(
            #     Exception, fl.reopen, True, True)
            # self.myAssertRaise(
            #     Exception, fl.reopen, False, True)

            fl = FileWriter.open_file(self._fname, readonly=True)
            f = fl.root()
#            self.assertEqual(5, len(f.attributes))
            # atts = []
            for at in f.attributes:
                print("%s %s %s" % (at.name, at.read(), at.dtype))
            self.assertEqual(
                f.attributes["file_name"][...],
                self._fname)
            self.assertTrue(
                f.attributes["NX_class"][...], "NXroot")
            self.assertEqual(f.size, 2)
            fl.close()

        finally:
            os.remove(self._fname)


if __name__ == '__main__':
    unittest.main()
