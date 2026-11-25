#!/usr/bin/env python
#   This file is part of nexdatas - Tango Server for NeXus data writer
#
#    Copyright (C) 2026 DESY, Jan Kotanski <jkotan@mail.desy.de>
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
#
# \file H5MapWriter_test.py
# unittests for the h5map writer
#
import json
import os
import tempfile
import unittest

import h5py
import numpy as np

import nxstools.filewriter as FileWriter
import nxstools.h5mapwriter as H5MapWriter

try:
    from blissdata.h5map import HDF5Item
    BLISSDATA_H5MAP = True
except Exception:
    BLISSDATA_H5MAP = False

try:
    from nxswriter import TangoDataWriter as TDW
    NXSWRITER = True
except Exception:
    NXSWRITER = False


STEP_SOURCE = '<datasource type="CLIENT" name="c01">' \
    '<record name="exp_c01"/></datasource>'


XML = """<definition>
 <group type="NXentry" name="entry1">
  <group type="NXinstrument" name="instrument">
   <group type="NXdetector" name="det">
    <field units="m" type="NX_FLOAT32" name="counter">
     <strategy mode="STEP"/>
     <datasource type="CLIENT" name="c01"><record name="exp_c01"/></datasource>
    </field>
    <field type="NX_INT64" name="init_val">
     <strategy mode="INIT"/>
     <datasource type="CLIENT" name="ival"><record name="ival"/></datasource>
    </field>
    <field type="NX_CHAR" name="end_time">
     <strategy mode="FINAL"/>
     <datasource type="CLIENT" name="end_time">
      <record name="end_time"/>
     </datasource>
    </field>
    <field type="NX_FLOAT64" name="final_arr">
     <dimensions rank="1"><dim index="1" value="3"/></dimensions>
     <strategy mode="FINAL"/>
     <datasource type="CLIENT" name="farr"><record name="farr"/></datasource>
    </field>
    <field type="NX_CHAR" name="const">hello<attribute name="note"
      type="NX_CHAR">abc</attribute></field>
   </group>
  </group>
  <group type="NXdata" name="data">
   <link name="counter" target="/entry1/instrument/det/counter"/>
  </group>
 </group>
</definition>"""


class H5MapWriterTest(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._fname = os.path.join(self._tmpdir, "h5map_test.nxs")

    def tearDown(self):
        if os.path.exists(self._fname):
            os.remove(self._fname)
        os.rmdir(self._tmpdir)

    def validate(self, h5map):
        """ checks JSON serialization and the blissdata h5map schema
        """
        json.dumps(h5map, allow_nan=False)
        if BLISSDATA_H5MAP:
            HDF5Item.validate_python(h5map)

    def test_data_item(self):
        di = H5MapWriter.data_item
        self.assertEqual(di("abc"), "abc")
        self.assertEqual(di(b"abc"), "abc")
        self.assertEqual(di(np.array("abc", dtype=object)), "abc")
        self.assertEqual(
            di(np.array([b"a", b"b"], dtype=object)), ["a", "b"])
        self.assertEqual(
            di(np.array([[1, 2]], dtype="int16")),
            {"type": "inline", "dtype": "int16", "value": [[1, 2]]})
        self.assertEqual(
            di(np.float32(1.5)),
            {"type": "inline", "dtype": "float32", "value": 1.5})
        self.assertEqual(
            di(np.array([1.0, np.nan, -np.inf])),
            {"type": "inline", "dtype": "float64",
             "value": [1.0, "nan", "-inf"]})
        self.assertEqual(
            di(np.array([True, False])),
            {"type": "inline", "dtype": "bool", "value": [True, False]})
        empty = di(np.zeros((0, 4), dtype="uint8"))
        self.assertEqual(empty["type"], "inline_b64")
        self.assertEqual(empty["dtype"], "|u1")
        self.assertEqual(empty["shape"], [0, 4])
        cplx = di(np.array([1 + 2j], dtype="complex128"))
        self.assertEqual(cplx["type"], "inline_b64")
        self.assertEqual(cplx["dtype"], "<c16")
        for item in [empty, cplx, di(np.array([1.0, np.nan]))]:
            self.validate({"type": "dataset", "value": item})

    def test_create_file_nothing_on_disk(self):
        fl = FileWriter.create_file(self._fname, writer=H5MapWriter)
        self.assertTrue(isinstance(fl, H5MapWriter.H5MapFile))
        self.assertEqual(fl.writer, H5MapWriter)
        rt = fl.root()
        rt.create_group("entry", "NXentry")
        fl.flush()
        fl.close()
        self.assertFalse(os.path.exists(self._fname))

        h5map = fl.h5map()
        self.validate(h5map)
        self.assertEqual(h5map["attributes"]["NX_class"], "NXroot")
        self.assertEqual(h5map["attributes"]["file_name"], self._fname)
        self.assertEqual(
            h5map["children"]["entry"],
            {"type": "group", "attributes": {"NX_class": "NXentry"}})
        self.assertEqual(list(fl.h5maps().keys()), [self._fname])

    def test_open_file_does_not_read_disk(self):
        with h5py.File(self._fname, "w") as fl:
            fl.create_group("existing")
        fl = FileWriter.open_file(self._fname, writer=H5MapWriter)
        self.assertEqual(fl.root().names(), [])
        fl.root().create_group("new")
        fl.close()
        with h5py.File(self._fname, "r") as hf:
            self.assertEqual(list(hf.keys()), ["existing"])

    def test_tree(self):
        fl = FileWriter.create_file(self._fname, writer=H5MapWriter)
        rt = fl.root()
        entry = rt.create_group("entry", "NXentry")
        data = entry.create_group("data", "NXdata")
        fld = data.create_field("arr", "float32", [2, 3], [1, 3])
        fld[...] = np.arange(6, dtype="float32").reshape(2, 3)
        at = fld.attributes.create("units", "string")
        at[...] = "mm"
        at = data.attributes.create("signal", "string")
        at[...] = "arr"
        sfld = data.create_field("title", "string")
        sfld.write("my title")
        FileWriter.link("/entry/data/arr", entry, "alink")
        FileWriter.link("other.h5:/entry/x", entry, "elink")
        fl.close()

        h5map = fl.h5map()
        self.validate(h5map)
        ech = h5map["children"]["entry"]["children"]
        self.assertEqual(
            ech["alink"],
            {"type": "soft_link", "target_path": "/entry/data/arr"})
        self.assertEqual(
            ech["elink"],
            {"type": "external_link", "target_file": "other.h5",
             "target_path": "entry/x"})
        dgrp = ech["data"]
        self.assertEqual(
            dgrp["attributes"], {"NX_class": "NXdata", "signal": "arr"})
        self.assertEqual(
            dgrp["children"]["arr"],
            {"type": "dataset",
             "value": {"type": "inline", "dtype": "float32",
                       "value": [[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]},
             "attributes": {"units": "mm"}})
        self.assertEqual(
            dgrp["children"]["title"],
            {"type": "dataset", "value": "my title"})

    def _step_file(self, streams=None):
        fl = FileWriter.create_file(
            self._fname, writer=H5MapWriter, streams=streams)
        det = fl.root().create_group("entry", "NXentry").create_group(
            "det", "NXdetector")
        fld = det.create_field("counter", "float64", [0], [1])
        fld.attributes.create(
            "nexdatas_strategy", "string")[...] = "STEP"
        fld.attributes.create(
            "nexdatas_source", "string")[...] = STEP_SOURCE
        fin = det.create_field("end_time", "string")
        fin.attributes.create(
            "nexdatas_strategy", "string")[...] = "FINAL"
        return fl

    def test_step_streams(self):
        fl = self._step_file()
        path = "/entry/det/counter"

        # no stream names: the (empty) value is exported
        h5map = fl.h5map()
        self.validate(h5map)
        det = h5map["children"]["entry"]["children"]["det"]["children"]
        self.assertEqual(det["counter"]["value"]["type"], "inline_b64")
        self.assertEqual(det["counter"]["value"]["shape"], [0])

        for streams in [{"c01": "scan:c01"},
                        {"exp_c01": "scan:c01"},
                        {path: "scan:c01"}]:
            h5map = fl.h5map(streams=streams)
            self.validate(h5map)
            det = h5map["children"]["entry"]["children"]["det"]["children"]
            self.assertEqual(
                det["counter"]["value"],
                {"type": "stream", "stream": "scan:c01"})
            self.assertEqual(
                det["counter"]["attributes"]["nexdatas_strategy"], "STEP")

        calls = []

        def resolver(fpath, dsname, record, strategy):
            calls.append((fpath, dsname, record, strategy))
            return "stream_" + record

        h5map = fl.h5map(streams=resolver)
        det = h5map["children"]["entry"]["children"]["det"]["children"]
        self.assertEqual(
            det["counter"]["value"],
            {"type": "stream", "stream": "stream_exp_c01"})
        self.assertEqual(calls, [(path, "c01", "exp_c01", "STEP")])
        fl.close()

    def test_file_streams_and_skip(self):
        fl = self._step_file(streams={"c01": "scan:c01"})
        h5map = fl.h5map(skip=["FINAL"])
        det = h5map["children"]["entry"]["children"]["det"]["children"]
        self.assertEqual(sorted(det.keys()), ["counter"])
        self.assertEqual(det["counter"]["value"]["stream"], "scan:c01")
        h5map = fl.h5map()
        det = h5map["children"]["entry"]["children"]["det"]["children"]
        self.assertEqual(sorted(det.keys()), ["counter", "end_time"])
        fl.close()

    def test_close_reopen(self):
        fl = FileWriter.create_file(self._fname, writer=H5MapWriter)
        rt = fl.root()
        grp = rt.create_group("entry", "NXentry")
        fl.close()
        self.assertFalse(fl.is_valid)
        fl.close()
        fl.reopen()
        self.assertTrue(fl.is_valid)
        self.assertTrue(grp.is_valid)
        grp.create_group("added")
        fl.reopen(readonly=True)
        self.assertTrue(fl.readonly)
        h5map = fl.h5map()
        self.assertEqual(
            list(h5map["children"]["entry"]["children"].keys()), ["added"])
        fl.close()
        image = fl.tobytes()
        lfl = H5MapWriter.load_file(image, self._fname, readonly=True)
        self.assertEqual(lfl.h5map(), h5map)
        lfl.close()

    def test_virtual_dataset(self):
        if not H5MapWriter.is_vds_supported():
            return
        fl = FileWriter.create_file(self._fname, writer=H5MapWriter)
        rt = fl.root()
        layout = FileWriter.virtual_field_layout(
            [2, 10, 20], "uint16", parent=rt)
        for i in range(2):
            src = FileWriter.target_field_view(
                "frame_%s.h5" % i, "/entry/data/data", [1, 10, 20],
                "uint16", parent=rt)
            layout.add((slice(i, i + 1), slice(None), slice(None)), src)
        vfld = rt.create_virtual_field("vds", layout)
        vfld.attributes.create("units", "string")[...] = "counts"
        fl.close()

        h5map = fl.h5map()
        self.validate(h5map)
        vds = h5map["children"]["vds"]
        self.assertEqual(vds["type"], "virtual_dataset")
        self.assertEqual(vds["dtype"], "<u2")
        self.assertEqual(vds["shape"], [2, 10, 20])
        self.assertEqual(vds["attributes"], {"units": "counts"})
        self.assertEqual(len(vds["virtual_sources"]), 2)
        src = vds["virtual_sources"][1]
        self.assertEqual(src["src_file"], "frame_1.h5")
        self.assertEqual(src["src_dataset"], "/entry/data/data")
        self.assertEqual(
            src["vspace"], {"start": [1, 0, 0], "count": [1, 10, 20]})
        self.assertEqual(
            src["src_space"], {"start": [0, 0, 0], "count": [1, 10, 20]})

    @unittest.skipUnless(NXSWRITER, "nxswriter is not available")
    def test_tangodatawriter(self):
        TDW.WRITERS["h5map"] = H5MapWriter
        streams = {"c01": "scan:exp_c01"}
        tdw = TDW.TangoDataWriter()
        tdw.writer = "h5map"
        tdw.fileName = self._fname
        tdw.openFile()
        tdw.xmlsettings = XML
        tdw.jsonrecord = json.dumps({"data": {"ival": 7}})
        tdw.openEntry()
        start = tdw.getFile().h5map(streams, skip=["FINAL"])
        tdw.jsonrecord = json.dumps({"data": {
            "end_time": "2026-11-25T10:00:00",
            "farr": [1.5, float("nan"), 3]}})
        tdw.closeEntry()
        end = tdw.getFile().h5map(streams)
        tdw.closeFile()
        self.assertFalse(os.path.exists(self._fname))

        self.validate(start)
        self.validate(end)

        def det(h5map):
            return h5map["children"]["entry1"]["children"][
                "instrument"]["children"]["det"]["children"]

        sdet = det(start)
        edet = det(end)
        self.assertEqual(
            sorted(sdet.keys()), ["const", "counter", "init_val"])
        self.assertEqual(
            sorted(edet.keys()),
            ["const", "counter", "end_time", "final_arr", "init_val"])
        for dt in [sdet, edet]:
            self.assertEqual(
                dt["counter"]["value"],
                {"type": "stream", "stream": "scan:exp_c01"})
            self.assertEqual(dt["counter"]["attributes"]["units"], "m")
            self.assertEqual(
                dt["init_val"]["value"],
                {"type": "inline", "dtype": "int64", "value": [7]})
            self.assertEqual(dt["const"]["value"], "hello")
            self.assertEqual(dt["const"]["attributes"]["note"], "abc")
        self.assertEqual(edet["end_time"]["value"], "2026-11-25T10:00:00")
        self.assertEqual(
            edet["final_arr"]["value"],
            {"type": "inline", "dtype": "float64",
             "value": [1.5, "nan", 3.0]})
        self.assertEqual(
            end["children"]["entry1"]["children"]["data"]["children"][
                "counter"],
            {"type": "soft_link",
             "target_path": "/entry1/instrument/det/counter"})


if __name__ == '__main__':
    unittest.main()
