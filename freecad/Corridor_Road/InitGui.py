# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import os
import sys


def _ensure_addon_root_on_sys_path():
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    addon_root = os.path.dirname(os.path.dirname(pkg_dir))
    if addon_root not in sys.path:
        sys.path.insert(0, addon_root)
    return addon_root


_ensure_addon_root_on_sys_path()

from freecad.Corridor_Road import ensure_package_on_sys_path, install_virtual_path_mappings  # noqa: E402
from freecad.Corridor_Road.init_gui import CorridorRoadWorkbench, register_workbench  # noqa: E402,F401


ensure_package_on_sys_path()
install_virtual_path_mappings(eager=True)
register_workbench()
