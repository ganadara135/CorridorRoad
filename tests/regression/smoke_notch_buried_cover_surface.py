# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Buried-notch surface preservation smoke test.

Run in FreeCAD Python environment:
    python tests/regression/smoke_notch_buried_cover_surface.py
"""

import FreeCAD as App
import Part

from freecad.Corridor_Road.objects.obj_corridor import Corridor


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
        App.Vector(-8.0, 0.0, 0.0),
        App.Vector(-5.0, 0.0, 0.0),
        App.Vector(5.0, 0.0, 0.0),
        App.Vector(8.0, 0.0, 0.0),
    ]
    open_wire = Part.makePolygon(pts)
    row = {
        "Mode": "notch",
        "Ramp": 1.0,
        "Record": {
            "Type": "culvert",
            "Width": 6.0,
            "Height": 2.5,
            "Cover": 1.0,
            "Offset": 0.0,
            "_notch_spec": {
                "Enabled": True,
                "TypeLabel": "culvert",
                "Width": 8.1,
                "Height": 3.5,
            },
        },
    }

    out_wire = Corridor._make_notch_profile_for_surface(open_wire, row, doc_or_obj=None)
    in_pts = Corridor._wire_points(open_wire)
    out_pts = Corridor._wire_points(out_wire)

    _assert(_points_equal(in_pts, out_pts), "Covered culvert notch should preserve the original surface wire")
    print("[PASS] Buried-notch surface preservation smoke test completed.")


if __name__ == "__main__":
    run()
