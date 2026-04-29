import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.objects import design_standards as _ds
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_alignment_editor import (
    CmdV1AlignmentEditor,
    V1AlignmentEditorTaskPanel,
    alignment_compiled_summary_rows,
    alignment_element_rows,
    alignment_ip_rows,
    alignment_preset_center,
    alignment_preset_placement_names,
    alignment_preset_rows_for_placement,
    alignment_pi_review_rows,
    apply_alignment_element_rows,
    apply_alignment_ip_rows,
    create_blank_v1_alignment,
    run_v1_alignment_editor_command,
)
from freecad.Corridor_Road.v1.commands.selection_context import selected_alignment_profile_target
from freecad.Corridor_Road.v1.objects.obj_alignment import (
    create_sample_v1_alignment,
    find_v1_alignment,
    to_alignment_model,
)


class _Selection:
    def __init__(self, objects):
        self._objects = list(objects or [])

    def getSelection(self):
        return list(self._objects)


class _Gui:
    def __init__(self, objects):
        self.Selection = _Selection(objects)


def _new_project_doc():
    doc = App.newDocument("CRV1AlignmentEditorContract")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    project.Label = "CorridorRoad Project"
    ensure_project_tree(project, include_references=False)
    return doc, project


def test_apply_alignment_element_rows_sorts_and_updates_source_object() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)

        rows = apply_alignment_element_rows(
            alignment,
            [
                {
                    "kind": "tangent",
                    "station_start": 50.0,
                    "station_end": 100.0,
                    "x_values": "50,100",
                    "y_values": "0,10",
                },
                {
                    "kind": "tangent",
                    "station_start": 0.0,
                    "station_end": 50.0,
                    "x_values": "0,50",
                    "y_values": "0,0",
                },
            ],
        )
        model = to_alignment_model(alignment)

        assert [row["station_start"] for row in rows] == [0.0, 50.0]
        assert list(alignment.StationStarts) == [0.0, 50.0]
        assert list(alignment.StationEnds) == [50.0, 100.0]
        assert list(alignment.ElementLengths) == [50.0, 50.0]
        assert model is not None
        assert [row.station_start for row in model.geometry_sequence] == [0.0, 50.0]
        assert model.geometry_sequence[1].geometry_payload["x_values"] == [50.0, 100.0]
    finally:
        App.closeDocument(doc.Name)


def test_apply_alignment_element_rows_rejects_mismatched_xy_counts() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)

        try:
            apply_alignment_element_rows(
                alignment,
                [
                    {
                        "kind": "tangent",
                        "station_start": 0.0,
                        "station_end": 50.0,
                        "x_values": "0,50",
                        "y_values": "0",
                    }
                ],
            )
            assert False, "mismatched XY rows should raise"
        except ValueError as exc:
            assert "X/Y value counts" in str(exc)
    finally:
        App.closeDocument(doc.Name)


def test_apply_alignment_ip_rows_stores_v0_style_inputs_and_compiles_v1_geometry() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)

        compiled = apply_alignment_ip_rows(
            alignment,
            [
                {"x": 0.0, "y": 0.0, "radius": 99.0, "transition_length": 99.0},
                {"x": 30.0, "y": 0.0, "radius": 120.0, "transition_length": 20.0},
                {"x": 30.0, "y": 40.0, "radius": 99.0, "transition_length": 99.0},
            ],
            use_transition_curves=True,
            design_standard="KDS",
            design_speed_kph=60.0,
            min_radius=100.0,
            min_tangent_length=10.0,
            min_transition_length=10.0,
        )
        model = to_alignment_model(alignment)

        assert len(alignment_ip_rows(alignment)) == 3
        assert list(alignment.CurveRadii) == [0.0, 120.0, 0.0]
        assert list(alignment.TransitionLengths) == [0.0, 20.0, 0.0]
        assert len(compiled) == 3
        assert list(alignment.ElementKinds) == ["tangent", "transition_curve", "tangent"]
        assert list(alignment.StationStarts)[0] == 0.0
        assert list(alignment.StationEnds)[-1] > 0.0
        assert model is not None
        assert len(model.geometry_sequence) == 3
        assert len(model.geometry_sequence[1].geometry_payload["y_values"]) > 3
    finally:
        App.closeDocument(doc.Name)


def test_alignment_editor_reads_design_standard_from_project_setup_without_editor_combo() -> None:
    doc, project = _new_project_doc()
    try:
        project.DesignStandard = "AASHTO"
        alignment = create_sample_v1_alignment(doc, project=project)
        alignment.CriteriaStandard = "KDS"
        panel = V1AlignmentEditorTaskPanel(alignment=alignment, document=doc)
        standard_combos = [
            combo
            for combo in panel.form.findChildren(QtWidgets.QComboBox)
            if [combo.itemText(index) for index in range(combo.count())] == list(_ds.SUPPORTED_STANDARDS)
        ]

        assert standard_combos == []
        assert panel._project_design_standard() == "AASHTO"
        assert "AASHTO (from Project Setup" in panel._design_standard_label.text()
    finally:
        App.closeDocument(doc.Name)


def test_alignment_editor_apply_snapshots_project_design_standard() -> None:
    doc, project = _new_project_doc()
    try:
        project.DesignStandard = "AASHTO"
        alignment = create_sample_v1_alignment(doc, project=project)
        alignment.CriteriaStandard = "KDS"
        panel = V1AlignmentEditorTaskPanel(alignment=alignment, document=doc)
        panel._show_apply_complete_message = lambda _count: None

        assert panel._apply(close_after=False) is True
        assert alignment.CriteriaStandard == "AASHTO"
        assert "last applied" not in panel._design_standard_label.text()
    finally:
        App.closeDocument(doc.Name)


def test_apply_alignment_ip_rows_compiles_radius_to_sampled_curve_geometry() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)

        compiled = apply_alignment_ip_rows(
            alignment,
            [
                {"x": 0.0, "y": 0.0, "radius": 0.0, "transition_length": 0.0},
                {"x": 100.0, "y": 0.0, "radius": 30.0, "transition_length": 10.0},
                {"x": 100.0, "y": 100.0, "radius": 0.0, "transition_length": 0.0},
            ],
            use_transition_curves=True,
            spiral_segments=12,
            min_radius=20.0,
            min_tangent_length=10.0,
            min_transition_length=5.0,
        )
        model = to_alignment_model(alignment)
        curve_rows = [row for row in compiled if row["kind"] == "transition_curve"]

        assert model is not None
        assert len(compiled) == 3
        assert len(curve_rows) == 1
        assert len(str(curve_rows[0]["x_values"]).split(",")) > 3
        assert list(alignment.ElementKinds) == ["tangent", "transition_curve", "tangent"]
        assert float(alignment.TotalLength) > 0.0
        assert model.geometry_sequence[1].kind == "transition_curve"
    finally:
        App.closeDocument(doc.Name)


def test_apply_alignment_ip_rows_uses_transition_length_for_scs_sampling() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)

        no_transition = apply_alignment_ip_rows(
            alignment,
            [
                {"x": 0.0, "y": 0.0, "radius": 0.0, "transition_length": 0.0},
                {"x": 100.0, "y": 0.0, "radius": 30.0, "transition_length": 0.0},
                {"x": 100.0, "y": 100.0, "radius": 0.0, "transition_length": 0.0},
            ],
            use_transition_curves=False,
            spiral_segments=8,
            min_radius=20.0,
            min_tangent_length=10.0,
            min_transition_length=5.0,
        )
        with_transition = apply_alignment_ip_rows(
            alignment,
            [
                {"x": 0.0, "y": 0.0, "radius": 0.0, "transition_length": 0.0},
                {"x": 100.0, "y": 0.0, "radius": 30.0, "transition_length": 20.0},
                {"x": 100.0, "y": 100.0, "radius": 0.0, "transition_length": 0.0},
            ],
            use_transition_curves=True,
            spiral_segments=8,
            min_radius=20.0,
            min_tangent_length=10.0,
            min_transition_length=5.0,
        )
        plain_curve = [row for row in no_transition if row["kind"] == "sampled_curve"][0]
        scs_curve = [row for row in with_transition if row["kind"] == "transition_curve"][0]

        assert len(str(scs_curve["x_values"]).split(",")) > len(str(plain_curve["x_values"]).split(","))
        assert list(alignment.TransitionLengths) == [0.0, 20.0, 0.0]
    finally:
        App.closeDocument(doc.Name)


def test_alignment_review_rows_include_pi_curve_and_compiled_geometry_details() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)
        apply_alignment_ip_rows(
            alignment,
            [
                {"x": 0.0, "y": 0.0, "radius": 0.0, "transition_length": 0.0},
                {"x": 100.0, "y": 0.0, "radius": 30.0, "transition_length": 20.0},
                {"x": 100.0, "y": 100.0, "radius": 0.0, "transition_length": 0.0},
            ],
            use_transition_curves=True,
            spiral_segments=8,
            min_radius=20.0,
            min_tangent_length=10.0,
            min_transition_length=5.0,
        )

        pi_rows = alignment_pi_review_rows(alignment)
        compiled_rows = alignment_compiled_summary_rows(alignment)
        curve_pi = pi_rows[1]
        curve_row = compiled_rows[1]

        assert len(pi_rows) == 3
        assert curve_pi["kind"] == "transition_curve"
        assert curve_pi["ts_station"] is not None
        assert curve_pi["sc_station"] is not None
        assert curve_pi["cs_station"] is not None
        assert curve_pi["te_station"] is not None
        assert curve_pi["curve_point_count"] > 3
        assert len(compiled_rows) == 3
        assert curve_row["kind"] == "transition_curve"
        assert curve_row["point_count"] == curve_pi["curve_point_count"]
    finally:
        App.closeDocument(doc.Name)


def test_alignment_command_is_single_user_facing_entrypoint() -> None:
    resources = CmdV1AlignmentEditor().GetResources()

    assert resources["MenuText"] == "Alignment"
    assert "geometry" in resources["ToolTip"].lower()


def test_alignment_preset_placement_can_center_rows_on_terrain() -> None:
    rows = [
        (0.0, 0.0, 0.0, 0.0),
        (80.0, 0.0, 0.0, 0.0),
        (160.0, 0.0, 0.0, 0.0),
    ]

    placed = alignment_preset_rows_for_placement(
        rows,
        "Center on terrain",
        terrain_center=(1000.0, 2000.0),
    )

    assert "Center on terrain" in alignment_preset_placement_names()
    assert alignment_preset_center(placed["rows"]) == (1000.0, 2000.0)
    assert placed["placement"] == "Center on terrain"


def test_alignment_preset_placement_falls_back_to_project_origin_without_terrain() -> None:
    rows = [
        (0.0, 0.0, 0.0, 0.0),
        (80.0, 0.0, 0.0, 0.0),
        (160.0, 0.0, 0.0, 0.0),
    ]

    placed = alignment_preset_rows_for_placement(
        rows,
        "Center on terrain",
        project_origin=(25.0, -15.0),
    )

    assert alignment_preset_center(placed["rows"]) == (25.0, -15.0)
    assert placed["placement"] == "Center on project origin (fallback)"


def test_alignment_command_does_not_create_sample_alignment_on_open() -> None:
    doc, _project = _new_project_doc()
    try:
        result = run_v1_alignment_editor_command()

        assert result is None
        assert find_v1_alignment(doc) is None
    finally:
        App.closeDocument(doc.Name)


def test_blank_alignment_can_be_created_and_applied_from_rows() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_blank_v1_alignment(document=doc, project=project)
        compiled = apply_alignment_ip_rows(
            alignment,
            [
                {"x": 0.0, "y": 0.0, "radius": 0.0, "transition_length": 0.0},
                {"x": 50.0, "y": 0.0, "radius": 0.0, "transition_length": 0.0},
            ],
        )

        assert find_v1_alignment(doc) == alignment
        assert len(alignment_ip_rows(alignment)) == 2
        assert len(compiled) == 1
        assert list(alignment.ElementKinds) == ["tangent"]
    finally:
        App.closeDocument(doc.Name)


def test_selection_context_resolves_v1_alignment_selection() -> None:
    doc, project = _new_project_doc()
    try:
        alignment = create_sample_v1_alignment(doc, project=project)

        preferred_alignment, preferred_profile = selected_alignment_profile_target(
            _Gui([alignment]),
            doc,
        )

        assert preferred_alignment == alignment
        assert preferred_profile is None
        assert len(alignment_element_rows(alignment)) == 3
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 alignment editor contract tests completed.")
