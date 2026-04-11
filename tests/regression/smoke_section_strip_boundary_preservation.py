# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Section-strip boundary preservation smoke test.

Run in FreeCAD Python environment:
    python tests/regression/smoke_section_strip_boundary_preservation.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.section_strip_builder import harmonize_pair_points


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _contains_point(points, target, tol=1e-9):
    for point in list(points or []):
        if (point - target).Length <= tol:
            return True
    return False


def run():
    a = [
        App.Vector(-8.0, 0.0, 0.0),
        App.Vector(-5.0, 0.0, -0.5),
        App.Vector(5.0, 0.0, -0.5),
        App.Vector(8.0, 0.0, 0.0),
    ]
    b = [
        App.Vector(-8.0, 10.0, 0.0),
        App.Vector(-6.0, 10.0, -0.2),
        App.Vector(-3.5, 10.0, -1.0),
        App.Vector(3.5, 10.0, -1.0),
        App.Vector(6.0, 10.0, -0.2),
        App.Vector(8.0, 10.0, 0.0),
    ]

    aa, bb = harmonize_pair_points(None, None, a, b, point_count_hint=0)

    _assert(len(aa) == len(bb), "Harmonized pair should have equal point counts")
    _assert(len(aa) > max(len(a), len(b)), "Merged-parameter harmonization should add preserved break points")
    _assert(_contains_point(aa, a[1]), "Section A interior break point should be preserved")
    _assert(_contains_point(aa, a[2]), "Section A second interior break point should be preserved")
    _assert(_contains_point(bb, b[2]), "Section B interior break point should be preserved")
    _assert(_contains_point(bb, b[3]), "Section B second interior break point should be preserved")
    print("[PASS] Section-strip boundary preservation smoke test completed.")


if __name__ == "__main__":
    run()
