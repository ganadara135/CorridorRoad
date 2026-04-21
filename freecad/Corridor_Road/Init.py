# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import os
import sys


_init_path = globals().get("__file__", "")
if not _init_path:
    for _root in [os.getcwd()] + list(sys.path):
        _candidate = os.path.join(str(_root or ""), "freecad", "Corridor_Road", "Init.py")
        if os.path.isfile(_candidate):
            _init_path = _candidate
            break
if not _init_path:
    _init_path = os.path.abspath("Init.py")

_pkg_dir = os.path.dirname(os.path.abspath(_init_path))
_addon_root = os.path.dirname(os.path.dirname(_pkg_dir))
if _addon_root not in sys.path:
    sys.path.insert(0, _addon_root)

from freecad.Corridor_Road import ensure_package_on_sys_path, install_virtual_path_mappings  # noqa: E402


ensure_package_on_sys_path()
install_virtual_path_mappings(eager=False)
