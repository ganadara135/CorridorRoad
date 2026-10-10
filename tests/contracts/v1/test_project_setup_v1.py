import tempfile
from dataclasses import replace
from pathlib import Path

import FreeCAD as App

from freecad.Corridor_Road.commands.cmd_new_project import create_corridorroad_project
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_project_setup import (
    V1ProjectSetupTaskPanel,
    apply_v1_project_setup,
    run_v1_project_setup_command,
)
from freecad.Corridor_Road.v1.objects.project_setup_adapter import (
    project_setup_draft_from_project,
    write_project_setup,
)
from freecad.Corridor_Road.v1.services.editing.project_setup_service import ProjectSetupDraft

_QAPP = None


def _ensure_qapp():
    global _QAPP
    _QAPP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _QAPP


def _new_project_doc(name: str):
    doc = App.newDocument(name)
    return doc, create_corridorroad_project(doc)


def _silence_message_boxes(monkeypatch) -> None:
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", staticmethod(lambda *args, **kwargs: 0))
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", staticmethod(lambda *args, **kwargs: 0))


_WORLD_SETUP = ProjectSetupDraft(
    design_standard="AASHTO",
    linear_unit_display="mm",
    linear_unit_import="custom",
    linear_unit_export="mm",
    custom_linear_unit_scale=0.3048,
    tin_max_triangles=500000,
    crs_epsg="EPSG:5186",
    coordinate_workflow="World-first",
    auto_apply_coordinate_recommendations=False,
    horizontal_datum="KGD2002",
    vertical_datum="Incheon MSL",
    project_origin_e=200000.0,
    project_origin_n=500000.0,
    project_origin_z=10.0,
    local_origin_x=5.0,
    local_origin_y=6.0,
    local_origin_z=7.0,
    north_rotation_deg=12.5,
    coord_setup_locked=False,
    coord_setup_status="Validated",
)


def test_project_setup_survives_save_and_reopen() -> None:
    doc, project = _new_project_doc("CRV1ProjectSetupRoundTrip")
    project_name = project.Name
    with tempfile.TemporaryDirectory() as folder:
        path = str(Path(folder) / "project_setup.FCStd")
        try:
            write_project_setup(project, _WORLD_SETUP)
            doc.saveAs(path)
        finally:
            App.closeDocument(doc.Name)
        reopened = App.openDocument(path)
        try:
            assert project_setup_draft_from_project(reopened.getObject(project_name)) == _WORLD_SETUP
        finally:
            App.closeDocument(reopened.Name)


def test_apply_stores_the_normalized_setup_without_a_recompute() -> None:
    doc, project = _new_project_doc("CRV1ProjectSetupApply")
    try:
        doc.recompute()
        result = apply_v1_project_setup(project, replace(_WORLD_SETUP, coordinate_workflow="", coord_setup_status=""))

        assert result.applied
        assert result.draft.coordinate_workflow == "World-first"
        assert result.draft.coord_setup_status == "Initialized"
        assert project_setup_draft_from_project(project) == result.draft
        assert "EPSG='EPSG:5186'" in result.summary
        # Touched, not recomputed: nothing computes geometry from these properties.
        assert "Touched" in project.State
    finally:
        App.closeDocument(doc.Name)


def test_apply_refuses_coordinate_changes_to_a_locked_setup_and_writes_nothing() -> None:
    doc, project = _new_project_doc("CRV1ProjectSetupLocked")
    try:
        locked = replace(_WORLD_SETUP, coord_setup_locked=True)
        write_project_setup(project, locked)

        result = apply_v1_project_setup(project, replace(locked, project_origin_e=1.0, linear_unit_display="m"))

        assert not result.applied
        assert result.blocked_fields == ("project_origin_e",)
        assert project_setup_draft_from_project(project) == locked
        assert apply_v1_project_setup(project, replace(locked, linear_unit_display="m")).applied
    finally:
        App.closeDocument(doc.Name)


def test_panel_shows_the_stored_workflow_and_apply_keeps_it(monkeypatch) -> None:
    # The v0 panel replaced a stored Local-first with the CRS recommendation on load, so a locked
    # project with a CRS could not apply any change.
    _ensure_qapp()
    _silence_message_boxes(monkeypatch)
    doc, project = _new_project_doc("CRV1ProjectSetupWorkflow")
    try:
        stored = replace(_WORLD_SETUP, coordinate_workflow="Local-first", coord_setup_locked=True)
        write_project_setup(project, stored)
        panel = V1ProjectSetupTaskPanel(document=doc, preferred_project=project)

        assert panel.cmb_coord_workflow.currentText() == "Local-first"

        panel.cmb_linear_display.setCurrentText("m")
        panel._apply()

        assert project.CoordinateWorkflow == "Local-first"
        assert project.LinearUnitDisplay == "m"
    finally:
        App.closeDocument(doc.Name)


def test_editing_the_crs_follows_the_recommended_workflow_until_custom() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("CRV1ProjectSetupCrsEdit")
    try:
        panel = V1ProjectSetupTaskPanel(document=doc, preferred_project=project)

        panel.cmb_epsg.setEditText("EPSG:5186")
        assert panel.cmb_coord_workflow.currentText() == "World-first"
        assert panel.lbl_epsg_info.text().startswith("Preset selected")

        panel.cmb_coord_workflow.setCurrentText("Custom")
        panel.cmb_epsg.setEditText("")
        assert panel.cmb_coord_workflow.currentText() == "Custom"
    finally:
        App.closeDocument(doc.Name)


def test_opening_and_closing_the_panel_writes_nothing() -> None:
    _ensure_qapp()
    doc, project = _new_project_doc("CRV1ProjectSetupNoWrite")
    try:
        write_project_setup(project, _WORLD_SETUP)
        doc.recompute()

        panel = run_v1_project_setup_command(doc, preferred_project=project, prepare_project=False)
        panel.sp_e.setValue(1.0)
        panel.cmb_linear_display.setCurrentText("m")
        panel.reject()

        assert project_setup_draft_from_project(project) == _WORLD_SETUP
        assert "Touched" not in project.State
    finally:
        App.closeDocument(doc.Name)
