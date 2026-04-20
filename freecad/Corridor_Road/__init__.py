# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import os
import sys


def ensure_package_on_sys_path():
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    freecad_dir = os.path.dirname(pkg_dir)
    addon_root = os.path.dirname(freecad_dir)
    if addon_root not in sys.path:
        sys.path.insert(0, addon_root)
    return addon_root


ensure_package_on_sys_path()


def install_virtual_path_mappings(eager: bool = False):
    """Install legacy->canonical module aliases for FCStd proxy restore.

    These aliases are part of the current CorridorLoft compatibility window.
    Do not remove them until older FCStd files reopen cleanly after any proxy
    or module-path rename.
    """
    try:
        from .virtual_paths import install_virtual_path_mappings as _install

        _install(eager=eager)
    except Exception:
        # Keep startup resilient; mapping is best-effort compatibility glue.
        pass


install_virtual_path_mappings(eager=False)
