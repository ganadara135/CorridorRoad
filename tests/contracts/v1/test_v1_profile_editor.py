import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_profile_editor import (
    apply_profile_control_rows,
    build_profile_editor_handoff_context,
    profile_control_rows,
)
from freecad.Corridor_Road.v1.commands.selection_context import selected_alignment_profile_target
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile, to_profile_model


class _Selection:
    def __init__(self, objects):
        self._objects = list(objects or [])

    def getSelection(self):
        return list(self._objects)


class _Gui:
    def __init__(self, objects):
        self.Selection = _Selection(objects)


def _new_project_doc():
    doc = App.newDocument("CRV1ProfileEditorContract")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    project.Label = "CorridorRoad Project"
    ensure_project_tree(project, include_references=False)
    return doc, project


def test_apply_profile_control_rows_sorts_and_updates_source_object() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        rows = apply_profile_control_rows(
            profile,
            [
                {"station": 150.0, "elevation": 16.0, "kind": "grade_break"},
                {"station": 0.0, "elevation": 12.0, "kind": "grade_break"},
                {"station": 75.0, "elevation": 14.5, "kind": "pvi"},
            ],
        )
        model = to_profile_model(profile)

        assert [row["station"] for row in rows] == [0.0, 75.0, 150.0]
        assert list(profile.ControlStations) == [0.0, 75.0, 150.0]
        assert list(profile.ControlElevations) == [12.0, 14.5, 16.0]
        assert model is not None
        assert [row.station for row in model.control_rows] == [0.0, 75.0, 150.0]
    finally:
        App.closeDocument(doc.Name)


def test_apply_profile_control_rows_rejects_duplicate_stations() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        try:
            apply_profile_control_rows(
                profile,
                [
                    {"station": 0.0, "elevation": 12.0, "kind": "grade_break"},
                    {"station": 0.0, "elevation": 13.0, "kind": "pvi"},
                ],
            )
            assert False, "duplicate station should raise"
        except ValueError as exc:
            assert "Duplicate station" in str(exc)
    finally:
        App.closeDocument(doc.Name)


def test_profile_editor_handoff_context_targets_selected_station() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        context = build_profile_editor_handoff_context(
            profile,
            selected_row={"station": 75.0, "elevation": 14.5, "kind": "pvi"},
        )

        assert context["source"] == "v1_profile_editor"
        assert context["preferred_profile_name"] == profile.Name
        assert context["preferred_station"] == 75.0
        assert context["viewer_context"]["source_panel"] == "v1 Profile Editor"
        assert context["viewer_context"]["focus_station_label"] == "STA 75.000"
        assert "FG 14.500" in context["viewer_context"]["selected_row_label"]
    finally:
        App.closeDocument(doc.Name)


def test_selection_context_resolves_v1_profile_selection() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        profile = create_sample_v1_profile(doc, project=project, alignment=alignment)

        preferred_alignment, preferred_profile = selected_alignment_profile_target(
            _Gui([profile]),
            doc,
        )

        assert preferred_alignment is None
        assert preferred_profile == profile
        assert len(profile_control_rows(profile)) == 3
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 profile editor contract tests completed.")
