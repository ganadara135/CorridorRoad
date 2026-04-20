# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Corridor child-link boundary smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_corridor_child_link_boundary.py
"""

import os

from freecad.Corridor_Road.corridor_compat import CORRIDOR_CHILD_LINK_PROPERTY


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _read_text(path):
    with open(path, "r", encoding="utf-8") as fp:
        return fp.read()


def run():
    repo_root = os.getcwd()
    freecad_root = os.path.join(repo_root, "freecad", "Corridor_Road")
    _assert(CORRIDOR_CHILD_LINK_PROPERTY == "ParentCorridor", "Corridor child-link property should use the canonical 'ParentCorridor' name")

    compat_path = os.path.normpath(os.path.join(freecad_root, "corridor_compat.py"))
    loft_path = os.path.normpath(os.path.join(freecad_root, "objects", "obj_corridor.py"))
    project_path = os.path.normpath(os.path.join(freecad_root, "objects", "obj_project.py"))
    task_path = os.path.normpath(os.path.join(freecad_root, "ui", "task_corridor.py"))

    allowed_child_link_refs = {
        compat_path,
        loft_path,
        project_path,
        task_path,
    }
    found_child_link_token_refs = set()

    for root, _dirs, files in os.walk(freecad_root):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.normpath(os.path.join(root, name))
            text = _read_text(path)
            if "CORRIDOR_CHILD_LINK_PROPERTY" in text:
                found_child_link_token_refs.add(path)

    unexpected = sorted(path for path in found_child_link_token_refs if path not in allowed_child_link_refs)
    _assert(
        not unexpected,
        f"Corridor child-link token should stay isolated to ownership boundary files only: {unexpected}",
    )

    loft_text = _read_text(loft_path)
    _assert(
        'mk.addProperty("App::PropertyLink", CORRIDOR_CHILD_LINK_PROPERTY' in loft_text
        and 'setattr(mk, CORRIDOR_CHILD_LINK_PROPERTY, obj)' in loft_text,
        "Corridor object should own skip-marker child-link creation and assignment",
    )
    _assert(
        'seg.addProperty("App::PropertyLink", CORRIDOR_CHILD_LINK_PROPERTY' in loft_text
        and 'setattr(seg, CORRIDOR_CHILD_LINK_PROPERTY, obj)' in loft_text,
        "Corridor object should own segment child-link creation and assignment",
    )

    project_text = _read_text(project_path)
    _assert(
        "getattr(child, CORRIDOR_CHILD_LINK_PROPERTY, None)" in project_text,
        "Project tree routing should resolve child ownership through the canonical child-link helper boundary",
    )

    task_text = _read_text(task_path)
    _assert(
        "getattr(o, CORRIDOR_CHILD_LINK_PROPERTY, None) == cor" in task_text,
        "Corridor task panel should recover generated child ownership through the canonical child-link boundary",
    )

    print("[PASS] Corridor child-link boundary smoke test completed.")


if __name__ == "__main__":
    run()
