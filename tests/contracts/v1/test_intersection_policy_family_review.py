"""Item 5.10: the review reaches the five remaining Intersection row families.

`corner_rows`, `edge_policy_rows`, `lane_connection_rows`, `grading_policy_rows` and
`drainage_policy_rows` were the last row families a user could not review from the
panel. Accepting them clears their diagnostics. The edge families need one more step,
because the preset writes `source_method="subassembly_default"`, a value the
evaluation service does not accept, and adopting the Subassembly is a claim the user
makes in its own action rather than a side effect of accepting.
"""


import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import find_project
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
    build_document_corridor_model,
    build_document_corridor_surface_model,
    create_corridor_daylight_surface_preview,
    create_corridor_design_surface_preview,
    create_corridor_intersection_surface_preview,
)
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    apply_v1_applied_section_set,
    build_document_applied_section_set,
)
from freecad.Corridor_Road.v1.commands.cmd_intersection_editor import (
    resolve_intersection_review_leg_refs,
)
from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import (
    create_intersection_preset_sources,
)
from freecad.Corridor_Road.v1.models.source.intersection_model import (
    IntersectionEdgePolicyRow,
    IntersectionModel,
)
from freecad.Corridor_Road.v1.objects.obj_intersection import (
    find_v1_intersection_model,
    to_intersection_model,
    update_v1_intersection_model_object,
)
from freecad.Corridor_Road.v1.services.editing import (
    adopt_edge_families_from_subassembly,
    apply_intersection_review,
    intersection_preset_default_rows,
    intersection_review_rows,
)

FIVE_KINDS = {"corner", "edge_policy", "lane_connection", "grading_policy", "drainage_policy"}


def _preset_model(doc, label):
    create_intersection_preset_sources(doc, preset_label=label)
    return to_intersection_model(find_v1_intersection_model(doc))


def _reviewed_model(doc, label):
    model = _preset_model(doc, label)
    return apply_intersection_review(model, leg_refs=resolve_intersection_review_leg_refs(doc, model)).model


def _store(doc, model):
    obj = find_v1_intersection_model(doc)
    update_v1_intersection_model_object(obj, model, label=str(getattr(obj, "Label", "") or "Intersections"))


def _owner_status(doc):
    project = find_project(doc)
    from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (  # noqa: F401  (kept local, mirrors the smoke)
        corridor_build_review_rows,
    )

    applied = build_document_applied_section_set(doc, project=project)
    apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
    corridor_model = build_document_corridor_model(doc, project=project)
    surface_model = build_document_corridor_surface_model(doc, project=project, corridor_model=corridor_model)
    kwargs = dict(document=doc, project=project, corridor_model=corridor_model, surface_model=surface_model)
    create_corridor_intersection_surface_preview(**kwargs)
    create_corridor_design_surface_preview(**kwargs)
    create_corridor_daylight_surface_preview(**kwargs)
    preview = doc.getObject("V1CorridorIntersectionSlopeFaceSurfacePreview")
    assert preview is not None
    return (
        str(getattr(preview, "IntersectionBoundaryOwnerStatus", "") or ""),
        int(getattr(preview, "IntersectionBoundaryOwnerCount", 0) or 0),
    )


def test_the_review_lists_the_five_remaining_families_with_what_they_hold() -> None:
    doc = App.newDocument("CRV1PolicyFamilyList")
    try:
        model = _preset_model(doc, "T Intersection - Basic")

        rows = intersection_review_rows(model)

        by_kind = {}
        for row in rows:
            by_kind.setdefault(row.kind, []).append(row)
        assert FIVE_KINDS <= set(by_kind)
        # the counts measured on a T preset in plan item 5.10
        assert [len(by_kind[kind]) for kind in ("corner", "edge_policy", "lane_connection", "grading_policy", "drainage_policy")] == [2, 4, 2, 1, 1]
        for kind in FIVE_KINDS:
            for row in by_kind[kind]:
                assert row.approval_status == "draft", (kind, row.row_id)
                assert row.missing_fields == (), (kind, row.row_id)
                assert not row.reviewed
        # the review shows where each row came from, so the edge default is visible
        assert {row.notes for row in by_kind["edge_policy"]} == {"subassembly_default"}
    finally:
        App.closeDocument(doc.Name)


def test_accepting_clears_the_diagnostics_of_the_five_families_and_keeps_source_method() -> None:
    doc = App.newDocument("CRV1PolicyFamilyAccept")
    try:
        model = _preset_model(doc, "T Intersection - Basic")
        assert all(row.diagnostic_rows for row in model.edge_policy_rows)

        prepared = apply_intersection_review(model, leg_refs=resolve_intersection_review_leg_refs(doc, model))

        for attribute in (
            "corner_rows",
            "edge_policy_rows",
            "lane_connection_rows",
            "grading_policy_rows",
            "drainage_policy_rows",
        ):
            rows = getattr(prepared.model, attribute)
            assert rows, attribute
            for row in rows:
                assert row.approval_status == "accepted", attribute
                assert row.diagnostic_rows == [], attribute
        # provenance lives in source_method, so clearing the markers loses nothing
        assert {row.source_method for row in prepared.model.edge_policy_rows} == {"subassembly_default"}
        # and drainage intent is Drainage's to decide, so the review leaves it alone
        assert {row.intent_status for row in prepared.model.drainage_policy_rows} == {"hint_only"}
        assert all(row.reviewed for row in intersection_review_rows(prepared.model))
        rows = {row.label: row for row in intersection_preset_default_rows(prepared.model)}
        assert rows["Grading policy"].review_state == "reviewed"
        assert rows["Drainage mode"].review_state == "reviewed"
    finally:
        App.closeDocument(doc.Name)


def test_adopting_the_edge_families_is_a_separate_action_that_only_changes_the_method() -> None:
    doc = App.newDocument("CRV1PolicyFamilyAdopt")
    try:
        reviewed = _reviewed_model(doc, "T Intersection - Basic")

        adopted = adopt_edge_families_from_subassembly(reviewed)

        assert len(adopted.accepted_row_ids) == len(reviewed.edge_policy_rows)
        assert {row.source_method for row in adopted.model.edge_policy_rows} == {"subassembly_derived"}
        for before, after in zip(reviewed.edge_policy_rows, adopted.model.edge_policy_rows):
            assert after.approval_status == before.approval_status
            assert after.diagnostic_rows == before.diagnostic_rows
            assert after.subassembly_kind == before.subassembly_kind
        # nothing else moved
        assert adopted.model.drainage_policy_rows == reviewed.drainage_policy_rows
        assert adopted.model.grading_policy_rows == reviewed.grading_policy_rows
    finally:
        App.closeDocument(doc.Name)


def test_a_row_missing_what_it_governs_is_not_accepted_and_not_adopted() -> None:
    model = IntersectionModel(
        schema_version=1,
        project_id="project:test",
        edge_policy_rows=[
            IntersectionEdgePolicyRow(
                policy_id="edge-policy:t:leg:01:pavement",
                intersection_id="intersection:t",
                leg_ref="intersection:t:leg:01",
                edge_family_intent="",
                source_method="subassembly_default",
                approval_status="draft",
                subassembly_kind="",
                diagnostic_rows=["edge_family_approval_pending"],
            )
        ],
    )

    rows = intersection_review_rows(model)
    prepared = apply_intersection_review(model)
    adopted = adopt_edge_families_from_subassembly(model)

    assert rows[0].missing_fields == ("edge_family_intent",)
    assert prepared.model.edge_policy_rows[0].approval_status == "draft"
    assert prepared.model.edge_policy_rows[0].diagnostic_rows == ["edge_family_approval_pending"]
    assert "edge-policy:t:leg:01:pavement" in prepared.incomplete_row_ids
    assert any(row.startswith("warning|edge_policy_review_incomplete:") for row in prepared.diagnostics)
    # without a subassembly_kind the evaluator would report an error, so the method stays
    assert adopted.model.edge_policy_rows[0].source_method == "subassembly_default"
    assert adopted.incomplete_row_ids == ("edge-policy:t:leg:01:pavement",)
    assert adopt_edge_families_from_subassembly(None).accepted is False


def test_boundary_owner_reaches_ready_from_the_preset_plus_review_and_adoption() -> None:
    doc = App.newDocument("CRV1PolicyFamilyOwner")
    try:
        reviewed = _reviewed_model(doc, "T Intersection - Basic")

        # accepting alone is not enough: the edge rows still evaluate as method_unknown
        _store(doc, reviewed)
        accepted_only = _owner_status(doc)
        assert accepted_only[0] != "ready", accepted_only

        _store(doc, adopt_edge_families_from_subassembly(reviewed).model)
        adopted = _owner_status(doc)
        assert adopted[0] == "ready", adopted
        assert adopted[1] > 0
    finally:
        App.closeDocument(doc.Name)


def test_panel_adoption_needs_the_users_confirmation_and_then_changes_only_the_method(monkeypatch) -> None:
    from freecad.Corridor_Road.qt_compat import QtWidgets
    from freecad.Corridor_Road.v1.commands import cmd_intersection_presets
    from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import V1IntersectionPresetsTaskPanel

    # a real QMessageBox is modal and would wait for a click that never comes
    monkeypatch.setattr(cmd_intersection_presets, "_show_message", lambda *args, **kwargs: None)

    # the application must outlive the widgets, so it is held for the test body
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    doc = App.newDocument("CRV1PolicyFamilyPanel")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        panel = V1IntersectionPresetsTaskPanel(document=doc)
        panel._accept_reviewed_rows()

        def methods():
            return {row.source_method for row in to_intersection_model(find_v1_intersection_model(doc)).edge_policy_rows}

        panel._confirm_edge_family_adoption = lambda: False
        panel._adopt_edge_families()
        assert methods() == {"subassembly_default"}

        panel._confirm_edge_family_adoption = lambda: True
        panel._adopt_edge_families()
        assert methods() == {"subassembly_derived"}
        reviewed = intersection_review_rows(to_intersection_model(find_v1_intersection_model(doc)))
        assert all(row.reviewed for row in reviewed)
    finally:
        App.closeDocument(doc.Name)


def test_cross_boundary_owner_is_one_curb_return_arc_per_corner() -> None:
    # A Cross takes the curb return envelope path: its boundary is built from the corner
    # arcs, not from the edge rows, so the owner is the corner arc and it does not wait for
    # the edge families to be adopted. A curved span has no rectangle side to own it. The
    # fillets leave the arm mouths open, and the connector across each is owned by the corner
    # it follows: 4 arc owners and 3 connector owners (the first corner has none before it
    # and the closing connector belongs to the last).
    doc = App.newDocument("CRV1PolicyFamilyCrossOwner")
    try:
        _store(doc, _reviewed_model(doc, "Cross Intersection - Basic"))
        status, count = _owner_status(doc)
        preview = doc.getObject("V1CorridorIntersectionSlopeFaceSurfacePreview")
        owner_refs = list(getattr(preview, "IntersectionBoundaryOwnerRefs", []) or [])
        assert (status, count) == ("ready", 7)
        assert len(owner_refs) == 7
        assert sum(ref.endswith(":arc") for ref in owner_refs) == 4, owner_refs
        assert sum(ref.endswith(":connector") for ref in owner_refs) == 3, owner_refs
        # the surface itself is unchanged: no face fills these arcs yet, so the loop
        # coverage keeps saying so rather than borrowing the owner status
        assert int(getattr(preview, "IntersectionBoundaryLoopGraphFilledEdgeCount", -1)) == 0
        assert str(getattr(preview, "IntersectionBoundaryLoopGraphCoverageStatus", "")) == "warning"
    finally:
        App.closeDocument(doc.Name)
