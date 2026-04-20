# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Corridor proxy/type boundary smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_corridor_proxy_boundary.py
"""

import os


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _read_text(path):
    with open(path, "r", encoding="utf-8") as fp:
        return fp.read()


def run():
    repo_root = os.getcwd()
    freecad_root = os.path.join(repo_root, "freecad", "Corridor_Road")

    compat_path = os.path.normpath(os.path.join(freecad_root, "corridor_compat.py"))
    corridor_obj_path = os.path.normpath(os.path.join(freecad_root, "objects", "obj_corridor.py"))
    project_path = os.path.normpath(os.path.join(freecad_root, "objects", "obj_project.py"))
    region_plan_path = os.path.normpath(os.path.join(freecad_root, "objects", "obj_region_plan.py"))
    structure_set_path = os.path.normpath(os.path.join(freecad_root, "objects", "obj_structure_set.py"))
    task_path = os.path.normpath(os.path.join(freecad_root, "ui", "task_corridor.py"))

    allowed_proxy_token_refs = {
        compat_path,
        corridor_obj_path,
        project_path,
        region_plan_path,
        structure_set_path,
        task_path,
    }
    found_proxy_token_refs = set()

    for root, _dirs, files in os.walk(freecad_root):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.normpath(os.path.join(root, name))
            text = _read_text(path)
            if "CORRIDOR_PROXY_TYPE" in text or "CORRIDOR_NAME_PREFIX" in text:
                found_proxy_token_refs.add(path)

    unexpected = sorted(path for path in found_proxy_token_refs if path not in allowed_proxy_token_refs)
    _assert(
        not unexpected,
        f"Corridor proxy/type compatibility tokens should stay isolated to proxy-restore boundary files only: {unexpected}",
    )

    corridor_obj_text = _read_text(corridor_obj_path)
    _assert(
        "self.Type = CORRIDOR_PROXY_TYPE" in corridor_obj_text,
        "Corridor proxy object should own the compatibility proxy type assignment through the centralized constant",
    )

    project_text = _read_text(project_path)
    _assert(
        "if proxy_type == CORRIDOR_PROXY_TYPE or (" in project_text and "name.startswith(CORRIDOR_NAME_PREFIX)" in project_text,
        "Project helper should resolve corridor objects through centralized proxy/name-prefix compatibility constants",
    )

    region_text = _read_text(region_plan_path)
    _assert(
        "hide_user_stale_state = proxy_type == CORRIDOR_PROXY_TYPE" in region_text,
        "Region-plan recompute routing should use the centralized corridor proxy compatibility constant",
    )

    structure_text = _read_text(structure_set_path)
    _assert(
        "hide_user_stale_state = proxy_type == CORRIDOR_PROXY_TYPE" in structure_text,
        "Structure-set recompute routing should use the centralized corridor proxy compatibility constant",
    )

    virtual_paths_path = os.path.join(freecad_root, "virtual_paths.py")
    virtual_paths_text = _read_text(virtual_paths_path)
    _assert(
        '"obj_corridor_loft"' in virtual_paths_text,
        "Virtual-path mapping should retain the corridor proxy module in the explicit restore preload list until proxy retirement",
    )

    init_path = os.path.join(freecad_root, "__init__.py")
    init_text = _read_text(init_path)
    _assert(
        "CorridorLoft compatibility window" in init_text,
        "Package init should continue documenting the active proxy compatibility window until retirement",
    )

    print("[PASS] Corridor proxy/type boundary smoke test completed.")


if __name__ == "__main__":
    run()
