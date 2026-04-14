# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Typical-section ditch-shape smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_typical_section_ditch_shapes.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_typical_section_template import (
    TypicalSectionTemplate,
    build_top_profile,
    component_rows,
)


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _almost_equal(a, b, tol=1e-6):
    return abs(float(a) - float(b)) <= float(tol)


def _make_typical(doc, name, shape_mode, extra_width):
    typ = doc.addObject("Part::FeaturePython", name)
    TypicalSectionTemplate(typ)
    typ.ComponentIds = ["DITCH-L"]
    typ.ComponentTypes = ["ditch"]
    typ.ComponentShapes = [shape_mode]
    typ.ComponentSides = ["left"]
    typ.ComponentWidths = [3.000]
    typ.ComponentCrossSlopes = [2.0]
    typ.ComponentHeights = [1.000]
    typ.ComponentExtraWidths = [extra_width]
    typ.ComponentBackSlopes = [-10.0]
    typ.ComponentOffsets = [0.0]
    typ.ComponentOrders = [10]
    typ.ComponentEnabled = [1]
    return typ


def run():
    doc = App.newDocument("CRTypicalSectionDitchShapes")
    try:
        typ_v = _make_typical(doc, "TypicalSectionDitchV", "v", 0.0)
        typ_trap = _make_typical(doc, "TypicalSectionDitchTrap", "trapezoid", 1.000)
        typ_u = _make_typical(doc, "TypicalSectionDitchU", "u", 0.500)

        doc.recompute()

        rows_v = component_rows(typ_v)
        rows_trap = component_rows(typ_trap)
        rows_u = component_rows(typ_u)
        _assert(rows_v[0]["Shape"] == "v", "V ditch shape not preserved")
        _assert(rows_trap[0]["Shape"] == "trapezoid", "Trapezoid ditch shape not preserved")
        _assert(rows_u[0]["Shape"] == "u", "U ditch shape not preserved")

        pts_v = build_top_profile(typ_v)
        pts_trap = build_top_profile(typ_trap)
        pts_u = build_top_profile(typ_u)

        _assert(len(pts_v) == 3, f"V ditch should produce 3 top-profile points, got {len(pts_v)}")
        _assert(len(pts_trap) == 4, f"Trapezoid ditch should produce 4 top-profile points, got {len(pts_trap)}")
        _assert(len(pts_u) == 5, f"U ditch should produce 5 top-profile points, got {len(pts_u)}")
        _assert(float(pts_trap[1].y) < float(pts_trap[0].y), "Trapezoid ditch should drop below the starting elevation")
        _assert(_almost_equal(float(pts_trap[1].y), float(pts_trap[2].y)), "Trapezoid ditch bottom should stay flat")
        _assert(_almost_equal(float(pts_trap[3].y), float(pts_trap[0].y)), "Trapezoid ditch should return to the starting elevation at the outer edge")
        _assert(float(pts_trap[0].x) > float(pts_trap[1].x) > float(pts_trap[2].x) > float(pts_trap[3].x), "Left-side trapezoid ditch points should progress from the outer edge back toward the centerline")

        shape_rows_u = [str(row or "") for row in list(getattr(typ_u, "SectionComponentSummaryRows", []) or [])]
        _assert(any("type=ditch" in row and "shape=u" in row for row in shape_rows_u), "U ditch report row missing shape=u")

        print("[PASS] Typical-section ditch-shapes smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
