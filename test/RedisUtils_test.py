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
# \file RedisUtils_test.py
# unittests for the pure (REDIS-independent) helpers in nxstools.redisutils
#
import unittest

import nxstools.redisutils as redisutils


def scalar(device="mg_channels", unit=None):
    """ build a scalar (0D) channel description """
    cd = {"device": device, "dim": 0}
    if unit is not None:
        cd["unit"] = unit
    return cd


class RedisUtilsTest(unittest.TestCase):
    """ tests for build_plots and its motor parsing """

    def test_motors_from_title(self):
        self.assertEqual(
            redisutils.motors_from_title("ascan exp_mot01 0 1 10 0.1"),
            ["exp_mot01"])
        self.assertEqual(
            redisutils.motors_from_title(
                "a2scan mot1 0 1 mot2 0 1 10 0.1"),
            ["mot1", "mot2"])
        self.assertEqual(
            redisutils.motors_from_title(
                "mesh mx 0 1 4 my 0 2 5 0.1"),
            ["mx", "my"])
        # unrecognised / motorless
        self.assertEqual(redisutils.motors_from_title("ct 0.1"), [])
        self.assertEqual(redisutils.motors_from_title(""), [])
        # channel filtering drops a motor that is not a recorded channel
        self.assertEqual(
            redisutils.motors_from_title(
                "ascan exp_mot01 0 1 10 0.1", channels=["exp_c01"]),
            [])

    def test_curve_plot_step_scan(self):
        channels = {
            "exp_mot01": scalar(),
            "exp_c01": scalar(),
            "exp_c02": scalar(),
            "timestamp": scalar(device="time", unit="s"),
            "point_nb": scalar(),
        }
        result = redisutils.build_plots(
            title="ascan exp_mot01 0 1 10 0.1", channels=channels)
        self.assertEqual(result["channel_meta"], {})
        self.assertEqual(result["plots"], [
            {"kind": "curve-plot", "items": [
                {"kind": "curve", "y": "exp_c01", "x": "exp_mot01"},
                {"kind": "curve", "y": "exp_c02", "x": "exp_mot01"},
            ]},
        ])

    def test_curve_plot_two_motors_x_is_first(self):
        channels = {
            "mot1": scalar(),
            "mot2": scalar(),
            "exp_c01": scalar(),
        }
        result = redisutils.build_plots(
            title="a2scan mot1 0 1 mot2 0 1 10 0.1", channels=channels)
        self.assertEqual(result["plots"], [
            {"kind": "curve-plot", "items": [
                {"kind": "curve", "y": "exp_c01", "x": "mot1"},
            ]},
        ])

    def test_ct_uses_time_axis(self):
        channels = {
            "exp_c01": scalar(),
            "timestamp": scalar(device="time", unit="s"),
        }
        result = redisutils.build_plots(title="ct 0.1", channels=channels)
        self.assertEqual(result["plots"], [
            {"kind": "curve-plot", "items": [
                {"kind": "curve", "y": "exp_c01", "x": "timestamp"},
            ]},
        ])

    def test_scatter_plot_mesh(self):
        channels = {
            "mx": scalar(),
            "my": scalar(),
            "exp_c01": scalar(),
        }
        result = redisutils.build_plots(
            title="mesh mx 0 1 4 my 0 2 5 0.1", channels=channels)
        self.assertEqual(result["plots"], [
            {"kind": "scatter-plot", "items": [
                {"kind": "scatter", "x": "mx", "y": "my", "value": "exp_c01"},
            ]},
        ])
        self.assertEqual(result["channel_meta"], {
            "mx": {"axis_kind": "forth", "axis_id": 0,
                   "axis_points": 5, "start": 0.0, "stop": 1.0},
            "my": {"axis_kind": "forth", "axis_id": 1,
                   "axis_points": 6, "start": 0.0, "stop": 2.0},
        })

    def test_scatter_value_skips_time_unit(self):
        # a counter whose unit is seconds is a poor default value
        channels = {
            "mx": scalar(),
            "my": scalar(),
            "exp_t01": scalar(unit="s"),
            "exp_c01": scalar(),
        }
        result = redisutils.build_plots(
            title="dmesh mx 0 1 4 my 0 2 5 0.1", channels=channels)
        self.assertEqual(
            result["plots"][0]["items"][0]["value"], "exp_c01")

    def test_spectra_add_1d_plot(self):
        channels = {
            "exp_mot01": scalar(),
            "exp_c01": scalar(),
            "mca01": {"device": "mca", "dim": 1},
        }
        result = redisutils.build_plots(
            title="ascan exp_mot01 0 1 10 0.1", channels=channels)
        self.assertEqual(result["plots"], [
            {"kind": "curve-plot", "items": [
                {"kind": "curve", "y": "exp_c01", "x": "exp_mot01"},
            ]},
            {"kind": "1d-plot", "items": [
                {"kind": "curve", "y": "mca01"},
            ]},
        ])

    def test_ref_moveables_override_title(self):
        # ref_moveables wins over the title-parsed motor
        channels = {
            "realmot": scalar(),
            "exp_c01": scalar(),
        }
        result = redisutils.build_plots(
            title="ascan exp_mot01 0 1 10 0.1",
            channels=channels,
            ref_moveables=["realmot"])
        self.assertEqual(
            result["plots"][0]["items"][0]["x"], "realmot")

    def test_image_channels_ignored(self):
        channels = {
            "exp_mot01": scalar(),
            "exp_c01": scalar(),
            "det2d": {"device": "image", "dim": 2},
        }
        result = redisutils.build_plots(
            title="ascan exp_mot01 0 1 10 0.1", channels=channels)
        # only the curve-plot; image handled by the consumer
        self.assertEqual(len(result["plots"]), 1)
        self.assertEqual(result["plots"][0]["kind"], "curve-plot")


if __name__ == '__main__':
    unittest.main()
