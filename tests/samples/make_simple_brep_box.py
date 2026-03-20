# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Generate a simple BREP box sample for CorridorRoad external-shape testing.

Usage examples:

1. With FreeCADCmd:
   FreeCADCmd.exe make_simple_brep_box.py

2. From FreeCAD Python console:
   exec(open(r"C:/.../tests/samples/make_simple_brep_box.py", "r", encoding="utf-8").read())

Output:
   tests/samples/simple_box_external_shape.brep
"""

from pathlib import Path

import Part


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "simple_box_external_shape.brep"


def main():
    # Simple rectangular solid:
    # length = 6.0, width = 2.5, height = 2.5
    #
    # Local axis convention for CorridorRoad external_shape placement:
    # X = along station/tangent
    # Y = lateral/normal
    # Z = up
    box = Part.makeBox(6.0, 2.5, 2.5)
    box.exportBrep(str(OUT))
    print(f"Wrote: {OUT}")


if __name__ == "__main__":
    main()
