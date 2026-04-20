# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Corridor hidden project-link boundary smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_corridor_project_link_boundary.py
"""

import os

from freecad.Corridor_Road.corridor_compat import CORRIDOR_PROJECT_PROPERTY


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _read_text(path):
    with open(path, "r", encoding="utf-8") as fp:
        return fp.read()


def run():
    repo_root = os.getcwd()
    freecad_root = os.path.join(repo_root, "freecad", "Corridor_Road")

    _assert(CORRIDOR_PROJECT_PROPERTY == "Corridor", "Project corridor link property should use the canonical 'Corridor' name")

    allowed_property_refs = {
        os.path.normpath(os.path.join(freecad_root, "corridor_compat.py")),
        os.path.normpath(os.path.join(freecad_root, "objects", "obj_project.py")),
    }
    found_property_token_refs = set()

    for root, _dirs, files in os.walk(freecad_root):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.normpath(os.path.join(root, name))
            text = _read_text(path)
            if "CORRIDOR_PROJECT_PROPERTY" in text:
                found_property_token_refs.add(path)

    unexpected = sorted(path for path in found_property_token_refs if path not in allowed_property_refs)
    _assert(
        not unexpected,
        f"Hidden corridor project-link compatibility token should stay isolated to project-link boundary files only: {unexpected}",
    )

    project_path = os.path.join(freecad_root, "objects", "obj_project.py")
    project_text = _read_text(project_path)
    _assert(
        "_ensure_hidden_link_property(obj, CORRIDOR_PROJECT_PROPERTY" in project_text,
        "Project helper should define the canonical hidden corridor link property",
    )
    _assert(
        "def assign_project_corridor(project_obj, corridor_obj):" in project_text
        and "setattr(prj, CORRIDOR_PROJECT_PROPERTY, corridor_obj)" in project_text,
        "Project helper should own canonical project-link assignment",
    )
    _assert(
        "def resolve_project_corridor(project_obj_or_doc):" in project_text
        and "assign_project_corridor(prj, corridor_obj)" in project_text,
        "Project helper should own canonical project-link resynchronization",
    )

    print("[PASS] Corridor hidden project-link boundary smoke test completed.")


if __name__ == "__main__":
    run()
