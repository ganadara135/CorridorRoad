# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Default (non-notch) surface preservation smoke test.

Run in FreeCAD Python environment:
    python tests/regression/smoke_notch_default_surface_preservation.py
"""

import FreeCAD as App
import Part

from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _points_equal(a, b, tol=1e-9):
    aa = list(a or [])
    bb = list(b or [])
    if len(aa) != len(bb):
        return False
    for pa, pb in zip(aa, bb):
        if (pa - pb).Length > tol:
            return False
    return True


def run():
    pts = [
        App.Vector(-12.0, -4.0, 0.0),
        App.Vector(-10.0, -2.0, 0.0),
        App.Vector(-6.0, -1.0, 0.0),
        App.Vector(0.0, 0.0, 0.0),
        App.Vector(6.0, -1.5, 0.0),
        App.Vector(11.0, -3.0, 0.0),
        App.Vector(14.0, -5.0, 0.0),
    ]
    open_wire = Part.makePolygon(pts)
    row = {
        "Mode": "default",
        "Ramp": 0.0,
        "Record": {
            "Type": "culvert",
            "Width": 6.0,
            "Height": 2.5,
            "Cover": 0.0,
            "Offset": 0.0,
            "_notch_spec": {
                "Enabled": True,
                "TypeLabel": "culvert",
                "Width": 8.1,
                "Height": 3.5,
            },
        },
    }

    out_wire = CorridorLoft._make_notch_profile_for_surface(open_wire, row, doc_or_obj=None)
    in_pts = CorridorLoft._wire_points(open_wire)
    out_pts = CorridorLoft._wire_points(out_wire)

    _assert(_points_equal(in_pts, out_pts), "Non-notch stations should preserve the original section wire")
    print("[PASS] Default-notch surface preservation smoke test completed.")


if __name__ == "__main__":
    run()
