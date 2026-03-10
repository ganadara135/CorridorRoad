# CorridorRoad/Init.py
# Root entrypoint that forwards to the namespaced package.
import os
import sys

import FreeCAD as App


def _ensure_wb_root_on_sys_path():
    user_wb = os.path.join(App.getUserAppDataDir(), "Mod", "CorridorRoad")
    sys_wb = os.path.join(App.getHomePath(), "Mod", "CorridorRoad")
    wb_root = user_wb if os.path.isdir(user_wb) else sys_wb
    if os.path.isdir(wb_root) and wb_root not in sys.path:
        sys.path.insert(0, wb_root)


_ensure_wb_root_on_sys_path()

try:
    import freecad.Corridor_Road  # noqa: F401
except Exception:
    # Keep startup resilient in case optional imports fail.
    pass
