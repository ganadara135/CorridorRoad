"""Item 5.3: the Intersection source review a user must be able to do in the document.

An Intersection preset writes its rows as `draft` with each leg's `profile_ref`
and `centerline3d_ref` empty. Before this the only way to fill them was in code,
the way the T slope-face smoke does. These lock the review service, the document
resolver that feeds it real refs, and the panel surface that runs it.
"""

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
    IntersectionControlArea,
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


def test_panel_review_surface_accepts_the_preset_rows_in_the_document() -> None:
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
