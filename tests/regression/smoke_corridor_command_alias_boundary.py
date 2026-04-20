# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Corridor command-alias boundary smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_corridor_command_alias_boundary.py
"""

import os

from freecad.Corridor_Road.corridor_compat import LEGACY_COMMAND_ID, PREFERRED_COMMAND_ID


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _read_text(path):
    with open(path, "r", encoding="utf-8") as fp:
        return fp.read()


def run():
    repo_root = os.getcwd()
    freecad_root = os.path.join(repo_root, "freecad", "Corridor_Road")

    allowed_legacy_id_files = {
        os.path.normpath(os.path.join(freecad_root, "corridor_compat.py")),
        os.path.normpath(os.path.join(freecad_root, "commands", "cmd_generate_corridor.py")),
    }
    found_legacy_id_files = set()

    for root, _dirs, files in os.walk(freecad_root):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.normpath(os.path.join(root, name))
            text = _read_text(path)
            if LEGACY_COMMAND_ID in text:
                found_legacy_id_files.add(path)

    unexpected = sorted(path for path in found_legacy_id_files if path not in allowed_legacy_id_files)
    _assert(not unexpected, f"Legacy command id should stay isolated to compatibility boundary files only: {unexpected}")

    init_gui_path = os.path.join(freecad_root, "init_gui.py")
    init_gui_text = _read_text(init_gui_path)
    _assert(PREFERRED_COMMAND_ID in init_gui_text, "Workbench UI should reference the preferred corridor command id")
    _assert(LEGACY_COMMAND_ID not in init_gui_text, "Workbench UI should not reference the legacy corridor command id directly")

    cmd_path = os.path.join(freecad_root, "commands", "cmd_generate_corridor.py")
    cmd_text = _read_text(cmd_path)
    _assert("Gui.addCommand(PREFERRED_COMMAND_ID, _CMD)" in cmd_text, "Canonical command module should register the preferred command id through the preferred constant")
    _assert("Gui.addCommand(LEGACY_COMMAND_ID, _CMD)" in cmd_text, "Canonical command module should retain the legacy command alias through the compatibility constant until retirement")

    print("[PASS] Corridor command-alias boundary smoke test completed.")


if __name__ == "__main__":
    run()
