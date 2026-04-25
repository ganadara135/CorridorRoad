# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import FreeCAD as App
import FreeCADGui as Gui
from pathlib import Path

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtWidgets


def run_pointcloud_tin_command(
    *,
    app_module=App,
    gui_module=Gui,
    run_v1_review=None,
    select_csv_path=None,
):
    """Run the v1 TIN review path with optional CSV point-cloud selection."""

    if run_v1_review is None:
        from freecad.Corridor_Road.v1.commands.cmd_review_tin import (
            show_v1_tin_review,
        )

        def _run_v1_review(*, extra_context=None):
            return show_v1_tin_review(
                extra_context=extra_context,
                app_module=app_module,
                gui_module=gui_module,
            )

        run_v1_review = _run_v1_review

    if select_csv_path is None:
        select_csv_path = lambda: _select_tin_csv_path(gui_module)

    csv_path = select_csv_path()
    extra_context = {}
    if csv_path:
        csv_path = str(csv_path)
        extra_context = {
            "csv_path": csv_path,
            "surface_id": _surface_id_from_csv(csv_path),
        }

    try:
        run_v1_review(extra_context=extra_context or None)
        return "v1"
    except Exception as exc:
        app_module.Console.PrintWarning(
            "CorridorRoad v1 TIN review unavailable; "
            f"showing the placeholder PointCloud TIN message: {exc}\n"
        )
        if gui_module is not None:
            QtWidgets.QMessageBox.information(
                None,
                "PointCloud TIN",
                "TIN review is not available in this session.",
            )
        return "fallback"


class CmdImportPointCloudTIN:
    def GetResources(self):
        return {
            "Pixmap": icon_path("pointcloud_tin.svg"),
            "MenuText": "PointCloud TIN",
            "ToolTip": "Build and review a v1 TIN from a CSV point cloud",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        run_pointcloud_tin_command()


def _select_tin_csv_path(gui_module) -> str:
    if gui_module is None:
        return ""
    start_dir = Path(__file__).resolve().parents[3] / "tests" / "samples"
    if not start_dir.exists():
        start_dir = Path.home()
    try:
        selected, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select Point Cloud CSV for TIN",
            str(start_dir),
            "CSV Files (*.csv);;All Files (*.*)",
        )
        return str(selected or "")
    except Exception:
        return ""


def _surface_id_from_csv(csv_path: str) -> str:
    stem = Path(str(csv_path)).stem.strip() or "csv"
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in stem)
    return f"tin:{safe}"


if hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_ImportPointCloudTIN", CmdImportPointCloudTIN())
