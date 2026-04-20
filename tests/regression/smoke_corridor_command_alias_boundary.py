# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Corridor command-alias boundary smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_corridor_command_alias_boundary.py
"""

import os

from freecad.Corridor_Road.corridor_compat import PREFERRED_COMMAND_ID


LEGACY_COMMAND_ID = "CorridorRoad_GenerateCorridorLoft"


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _read_text(path):
    with open(path, "r", encoding="utf-8") as fp:
        return fp.read()


def run():
    repo_root = os.getcwd()
    freecad_root = os.path.join(repo_root, "freecad", "Corridor_Road")
    found_legacy_id_files = []

    for root, _dirs, files in os.walk(freecad_root):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.normpath(os.path.join(root, name))
            text = _read_text(path)
            if LEGACY_COMMAND_ID in text:
                found_legacy_id_files.append(path)

    _assert(not found_legacy_id_files, f"Legacy command id should be fully removed from runtime code: {sorted(found_legacy_id_files)}")

    init_gui_path = os.path.join(freecad_root, "init_gui.py")
    init_gui_text = _read_text(init_gui_path)
    _assert(PREFERRED_COMMAND_ID in init_gui_text, "Workbench UI should reference the preferred corridor command id")
    _assert(LEGACY_COMMAND_ID not in init_gui_text, "Workbench UI should not reference the legacy corridor command id directly")

    cmd_path = os.path.join(freecad_root, "commands", "cmd_generate_corridor.py")
    cmd_text = _read_text(cmd_path)
    _assert("Gui.addCommand(PREFERRED_COMMAND_ID, _CMD)" in cmd_text, "Canonical command module should register the preferred command id through the preferred constant")

    legacy_wrapper_path = os.path.join(freecad_root, "commands", "cmd_generate_corridor_loft.py")
    _assert(not os.path.exists(legacy_wrapper_path), "Legacy corridor command wrapper should be removed")

    print("[PASS] Corridor command-alias boundary smoke test completed.")


if __name__ == "__main__":
    run()
