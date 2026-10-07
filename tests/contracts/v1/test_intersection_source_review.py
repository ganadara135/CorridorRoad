"""Item 5.3: the Intersection source review a user must be able to do in the document.

An Intersection preset writes its rows as `draft` with each leg's `profile_ref`
and `centerline3d_ref` empty. Before this the only way to fill them was in code,
the way the T slope-face smoke does. These lock the review service, the document
resolver that feeds it real refs, and the panel surface that runs it.
"""

import json

import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_intersection_editor import (
    resolve_intersection_review_leg_refs,
)
from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import (
    V1IntersectionPresetsTaskPanel,
    create_intersection_preset_sources,
)
from freecad.Corridor_Road.v1.models.source.intersection_model import (
    IntersectionAnchorRow,
    IntersectionArmPolicyRow,
    IntersectionControlArea,
    IntersectionCurbReturnPolicyRow,
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
)
from freecad.Corridor_Road.v1.objects.obj_intersection import (
    find_v1_intersection_model,
    to_intersection_model,
)
from freecad.Corridor_Road.v1.services.editing import (
    apply_intersection_review,
    intersection_preset_default_rows,
    intersection_review_rows,
    intersection_review_summary,
)


def _model(*, profile_ref: str = "", centerline3d_ref: str = "", station_ranges=((10.0, 30.0),)) -> IntersectionModel:
    return IntersectionModel(
        schema_version=1,
        project_id="project:test",
        anchor_rows=[
            IntersectionAnchorRow(
                anchor_id="anchor:t:main",
                intersection_id="intersection:t",
                primary_alignment_ref="alignment:main",
            )
        ],
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:t",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                leg_rows=[
                    IntersectionLegRow(
                        leg_id="intersection:t:leg:01",
                        leg_role="primary_before",
                        alignment_ref="alignment:main",
                        intersection_id="intersection:t",
                        profile_ref=profile_ref,
                        centerline3d_ref=centerline3d_ref,
                        approval_status="draft",
                    )
                ],
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="intersection:t:control-area:01",
                intersection_id="intersection:t",
                alignment_ref="alignment:main",
                station_ranges=list(station_ranges),
                approval_status="draft",
            )
        ],
    )


def test_review_rows_report_what_each_row_still_needs() -> None:
    rows = intersection_review_rows(_model())

    by_kind = {row.kind: row for row in rows}
    assert set(by_kind) == {"leg", "anchor", "control_area"}
    assert by_kind["leg"].missing_fields == ("profile_ref", "centerline3d_ref")
    assert by_kind["anchor"].missing_fields == ("tolerance",)
    assert by_kind["control_area"].missing_fields == ()
    assert all(row.approval_status == "draft" for row in rows)
    assert not any(row.reviewed for row in rows)


def test_review_rows_flag_a_control_area_without_station_ranges() -> None:
    rows = intersection_review_rows(_model(station_ranges=()))

    area = next(row for row in rows if row.kind == "control_area")
    assert area.missing_fields == ("station_ranges",)


def test_apply_review_accepts_a_leg_once_the_caller_supplies_its_refs() -> None:
    prepared = apply_intersection_review(
        _model(),
        leg_refs={
            "intersection:t:leg:01": {
                "profile_ref": "profile:V1Profile",
                "centerline3d_ref": "centerline3d:multiple",
            }
        },
    )

    assert prepared.accepted
    assert prepared.incomplete_row_ids == ()
    assert prepared.diagnostics == ()
    leg = prepared.model.intersection_rows[0].leg_rows[0]
    assert leg.approval_status == "accepted"
    assert leg.span_source == "explicit"
    assert leg.profile_ref == "profile:V1Profile"
    assert leg.centerline3d_ref == "centerline3d:multiple"
    assert prepared.model.anchor_rows[0].approval_status == "accepted"
    assert prepared.model.anchor_rows[0].tolerance > 0.0
    assert prepared.model.control_area_rows[0].approval_status == "accepted"
    assert prepared.model.control_area_rows[0].intent_status == "intersection_owned"
    assert all(row.reviewed for row in intersection_review_rows(prepared.model))


def test_apply_review_refuses_to_invent_a_missing_leg_ref() -> None:
    prepared = apply_intersection_review(_model(), leg_refs={})

    leg = prepared.model.intersection_rows[0].leg_rows[0]
    assert leg.approval_status == "draft"
    assert leg.profile_ref == ""
    assert leg.centerline3d_ref == ""
    assert prepared.incomplete_row_ids == ("intersection:t:leg:01",)
    assert prepared.diagnostics == (
        "warning|leg_review_incomplete:intersection:t:leg:01:profile_ref,centerline3d_ref",
    )
    # a warning does not block the rest of the review
    assert prepared.accepted
    assert prepared.model.anchor_rows[0].approval_status == "accepted"


def test_apply_review_keeps_a_ref_the_row_already_carries() -> None:
    prepared = apply_intersection_review(
        _model(profile_ref="profile:authored", centerline3d_ref="centerline3d:authored"),
        leg_refs={
            "intersection:t:leg:01": {
                "profile_ref": "profile:resolved",
                "centerline3d_ref": "centerline3d:resolved",
            }
        },
    )

    leg = prepared.model.intersection_rows[0].leg_rows[0]
    assert leg.profile_ref == "profile:authored"
    assert leg.centerline3d_ref == "centerline3d:authored"


def test_apply_review_resolves_review_state_markers_and_keeps_provenance() -> None:
    doc = App.newDocument("CRV1IntersectionReviewDiagnostics")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        model = to_intersection_model(find_v1_intersection_model(doc))
        before = list(model.intersection_rows[0].leg_rows[0].diagnostic_rows or [])
        assert "leg_approval_pending" in before
        assert "leg_source_region_derived" in before

        prepared = apply_intersection_review(
            model,
            leg_refs=resolve_intersection_review_leg_refs(doc, model),
        )

        leg = prepared.model.intersection_rows[0].leg_rows[0]
        # the marker that says nobody reviewed it is resolved by the review itself
        assert "leg_approval_pending" not in list(leg.diagnostic_rows or [])
        # where the row came from stays true and stays recorded
        assert "leg_source_region_derived" in list(leg.diagnostic_rows or [])
        anchor = prepared.model.anchor_rows[0]
        assert not any("review_required" in str(row) for row in list(anchor.diagnostic_rows or []))
        area = prepared.model.control_area_rows[0]
        assert "control_area_region_derived" in list(area.diagnostic_rows or [])
        assert not any("approval_pending" in str(row) for row in list(area.diagnostic_rows or []))
    finally:
        App.closeDocument(doc.Name)


def test_apply_review_reports_a_missing_model_as_an_error() -> None:
    prepared = apply_intersection_review(None)

    assert not prepared.accepted
    assert prepared.diagnostics == ("error|intersection_review_model_missing",)


def test_review_summary_counts_reviewed_and_blocked_rows() -> None:
    assert intersection_review_summary([]) == "No Intersection source rows to review."
    assert intersection_review_summary(intersection_review_rows(_model())) == (
        "0 of 3 row(s) reviewed; 2 still missing source fields."
    )


def test_resolver_finds_the_profile_and_centerline_refs_the_document_holds() -> None:
    doc = App.newDocument("CRV1IntersectionReviewResolver")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        model = to_intersection_model(find_v1_intersection_model(doc))

        refs = resolve_intersection_review_leg_refs(doc, model)

        legs = list(model.intersection_rows[0].leg_rows)
        assert len(refs) == len(legs)
        for leg in legs:
            resolved = refs[leg.leg_id]
            assert resolved["profile_ref"].startswith("profile:")
            assert resolved["centerline3d_ref"].startswith("centerline3d:")
        # the two roads resolve to different Profiles, not to one shared guess
        assert len({row["profile_ref"] for row in refs.values()}) == len(legs)
    finally:
        App.closeDocument(doc.Name)


def test_resolver_is_empty_without_a_document_or_a_model() -> None:
    assert resolve_intersection_review_leg_refs(None, _model()) == {}
    assert resolve_intersection_review_leg_refs(object(), None) == {}


def test_preset_default_rows_name_each_value_and_where_it_landed() -> None:
    doc = App.newDocument("CRV1PresetDefaultChecklist")
    try:
        create_intersection_preset_sources(
            doc,
            preset_label="T Intersection - Basic",
            design_vehicle="single_unit_truck",
            radius=11.0,
            control_length=30.0,
            grading_policy="keep_primary_crown",
            drainage_mode="curb_gutter_inlets",
        )
        model = to_intersection_model(find_v1_intersection_model(doc))

        rows = {row.label: row for row in intersection_preset_default_rows(model)}

        assert set(rows) == {
            "Design vehicle",
            "Curb return radius",
            "Control length",
            "Grading policy",
            "Drainage mode",
        }
        assert rows["Design vehicle"].value == "single_unit_truck"
        assert rows["Design vehicle"].carrier == "arm_policy_rows"
        assert rows["Curb return radius"].value == "11.000 m"
        assert rows["Curb return radius"].carrier == "curb_return_policy_rows"
        assert rows["Drainage mode"].value == "curb_gutter_inlets"
        assert "30.000 m" in rows["Control length"].value
    finally:
        App.closeDocument(doc.Name)


def test_preset_default_rows_report_a_real_review_state_for_every_value() -> None:
    doc = App.newDocument("CRV1PresetDefaultReviewState")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        model = to_intersection_model(find_v1_intersection_model(doc))

        rows = {row.label: row for row in intersection_preset_default_rows(model)}

        # item 5.11 gave the curb return radius and the design vehicle a review state;
        # before it they were the only two of the five with nowhere to record one
        for label in (
            "Design vehicle",
            "Curb return radius",
            "Control length",
            "Grading policy",
            "Drainage mode",
        ):
            assert rows[label].reviewable is True, label
            assert rows[label].review_state.startswith("review required"), label
    finally:
        App.closeDocument(doc.Name)


def test_preset_default_rows_follow_the_review_as_it_happens() -> None:
    doc = App.newDocument("CRV1PresetDefaultAfterReview")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        model = to_intersection_model(find_v1_intersection_model(doc))
        prepared = apply_intersection_review(
            model,
            leg_refs=resolve_intersection_review_leg_refs(doc, model),
        )

        rows = {row.label: row for row in intersection_preset_default_rows(prepared.model)}

        # control areas are one of the three families the review covers today
        assert rows["Control length"].review_state == "reviewed"
        # and so are the two families item 5.11 added
        assert rows["Curb return radius"].review_state == "reviewed"
        assert rows["Design vehicle"].review_state == "reviewed"
        # grading and drainage joined them with plan item 5.10
        assert rows["Grading policy"].review_state == "reviewed"
        assert rows["Drainage mode"].review_state == "reviewed"
    finally:
        App.closeDocument(doc.Name)


def test_preset_default_rows_are_empty_without_a_model() -> None:
    assert intersection_preset_default_rows(None) == []


def test_panel_review_surface_accepts_the_preset_rows_in_the_document(monkeypatch) -> None:
    from freecad.Corridor_Road.v1.commands import cmd_intersection_presets

    # a real QMessageBox is modal and waits for a click that never comes, which hung the gate
    monkeypatch.setattr(cmd_intersection_presets, "_show_message", lambda *args, **kwargs: None)
    # the application must outlive the widgets, so it is held for the test body
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    doc = App.newDocument("CRV1IntersectionReviewPanel")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic", control_length=24.0)
        panel = V1IntersectionPresetsTaskPanel(document=doc)

        panel._refresh_review_table()
        before = panel._review_table.rowCount()
        assert before > 0
        assert "0 of %d row(s) reviewed" % before in panel._review_summary.text()

        panel._accept_reviewed_rows()

        assert "%d of %d row(s) reviewed" % (before, before) in panel._review_summary.text()
        assert "0 still missing source fields" in panel._review_summary.text()
        reviewed = intersection_review_rows(to_intersection_model(find_v1_intersection_model(doc)))
        assert reviewed and all(row.reviewed for row in reviewed)
    finally:
        App.closeDocument(doc.Name)


def test_the_review_lists_the_curb_return_radius_and_the_design_vehicle() -> None:
    doc = App.newDocument("CRV1ReviewPolicyFamilies")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic", radius=11.0)
        model = to_intersection_model(find_v1_intersection_model(doc))

        rows = intersection_review_rows(model)

        by_kind = {}
        for row in rows:
            by_kind.setdefault(row.kind, []).append(row)
        assert {"leg", "anchor", "control_area", "curb_return_policy", "arm_policy"} <= set(by_kind)
        # one curb return policy for the junction, one arm policy for each leg
        assert len(by_kind["curb_return_policy"]) == 1
        assert len(by_kind["arm_policy"]) == len(model.intersection_rows[0].leg_rows)
        for row in by_kind["curb_return_policy"] + by_kind["arm_policy"]:
            assert row.approval_status == "draft"
            assert row.missing_fields == ()
            assert not row.reviewed
    finally:
        App.closeDocument(doc.Name)


def test_accepting_the_review_accepts_both_policy_families_and_keeps_provenance() -> None:
    doc = App.newDocument("CRV1ReviewPolicyAccept")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        model = to_intersection_model(find_v1_intersection_model(doc))
        curb_before = model.curb_return_policy_rows[0]
        assert "preset_curb_return_policy_review_required" in curb_before.diagnostic_rows
        assert "curb_return_source_defaulted" in curb_before.diagnostic_rows

        prepared = apply_intersection_review(
            model,
            leg_refs=resolve_intersection_review_leg_refs(doc, model),
        )

        curb = prepared.model.curb_return_policy_rows[0]
        assert curb.approval_status == "accepted"
        # the markers that said nobody had reviewed it are resolved by the review
        assert not any("review_required" in str(row) for row in curb.diagnostic_rows)
        assert not any("approval_pending" in str(row) for row in curb.diagnostic_rows)
        # where the row came from stays true, and these two have no source_method
        assert "curb_return_source_defaulted" in curb.diagnostic_rows
        arm = prepared.model.arm_policy_rows[0]
        assert arm.approval_status == "accepted"
        assert "arm_policy_source_defaulted" in arm.diagnostic_rows
        assert curb.policy_id in prepared.accepted_row_ids
        assert arm.policy_id in prepared.accepted_row_ids
        # the radius itself is untouched by being reviewed
        assert curb.radius == curb_before.radius
    finally:
        App.closeDocument(doc.Name)


def test_a_policy_row_missing_what_it_governs_is_not_accepted() -> None:
    model = _model(profile_ref="profile:main", centerline3d_ref="centerline3d:main")
    model.curb_return_policy_rows = [
        IntersectionCurbReturnPolicyRow(
            policy_id="curb-return:intersection:t:default",
            intersection_id="intersection:t",
            radius=0.0,
            approval_status="draft",
        )
    ]
    model.arm_policy_rows = [
        IntersectionArmPolicyRow(
            policy_id="arm-policy:intersection:t:leg:01",
            intersection_id="intersection:t",
            leg_ref="intersection:t:leg:01",
            approval_status="draft",
        )
    ]

    rows = {row.kind: row for row in intersection_review_rows(model)}
    prepared = apply_intersection_review(model)

    # a radius of zero governs no arc, so the row is not reviewed by accepting it
    assert rows["curb_return_policy"].missing_fields == ("radius",)
    assert rows["arm_policy"].missing_fields == ("design_vehicle_ref",)
    assert prepared.model.curb_return_policy_rows[0].approval_status == "draft"
    assert prepared.model.arm_policy_rows[0].approval_status == "draft"
    assert "curb-return:intersection:t:default" in prepared.incomplete_row_ids
    assert "arm-policy:intersection:t:leg:01" in prepared.incomplete_row_ids
    assert any(
        row.startswith("warning|curb_return_review_incomplete:") for row in prepared.diagnostics
    )
    assert any(
        row.startswith("warning|arm_policy_review_incomplete:") for row in prepared.diagnostics
    )


def test_a_document_written_before_the_review_state_existed_still_restores() -> None:
    # item 5.11 added approval_status and diagnostic_rows to these two families. A
    # document saved before it has neither key, so the reader falls back the way the
    # other nine do: accepted, with no diagnostics, and nothing refuses to restore.
    doc = App.newDocument("CRV1PolicyRowLegacyRestore")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        obj = find_v1_intersection_model(doc)
        for property_name in ("CurbReturnPolicyRowsJson", "ArmPolicyRowsJson"):
            legacy = [
                {
                    key: value
                    for key, value in row.items()
                    if key not in {"approval_status", "diagnostic_rows"}
                }
                for row in json.loads(getattr(obj, property_name))
            ]
            assert legacy
            setattr(obj, property_name, json.dumps(legacy))
        doc.recompute()

        restored = to_intersection_model(obj)

        for row in list(restored.curb_return_policy_rows) + list(restored.arm_policy_rows):
            assert row.approval_status == "accepted"
            assert row.diagnostic_rows == []
        # the values the old document did carry are unchanged
        assert restored.curb_return_policy_rows[0].radius > 0.0
        assert restored.arm_policy_rows[0].design_vehicle_ref.startswith("design-vehicle:")
        # and the checklist reports the state it can actually see
        rows = {row.label: row for row in intersection_preset_default_rows(restored)}
        assert rows["Curb return radius"].review_state == "reviewed"
    finally:
        App.closeDocument(doc.Name)
