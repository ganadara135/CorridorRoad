from freecad.Corridor_Road.v1.models.source.intersection_model import (
    INTERSECTION_KIND_PRESETS,
    IntersectionControlArea,
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
    intersection_kind_from_label,
    intersection_preset_labels,
    intersection_row_from_kind,
)


def test_intersection_type_presets_are_user_selectable() -> None:
    labels = intersection_preset_labels()

    assert labels == ["T Intersection", "Cross Intersection", "Y Intersection"]
    assert intersection_kind_from_label("T Intersection") == "t_intersection"
    assert intersection_kind_from_label("Cross Intersection") == "cross_intersection"
    assert intersection_kind_from_label("Y Intersection") == "y_intersection"
    assert set(INTERSECTION_KIND_PRESETS) == {"t_intersection", "cross_intersection", "y_intersection"}


def test_intersection_row_preserves_alignment_refs_control_regions_and_legs() -> None:
    row = intersection_row_from_kind(
        intersection_id="intersection:t-01",
        intersection_kind="t_intersection",
        primary_alignment_ref="alignment:main-road",
        secondary_alignment_refs=["alignment:side-road-01"],
        control_region_refs=["region:main-intersection-01", "region:side-intersection-01"],
    )

    assert row.is_supported_kind is True
    assert row.primary_alignment_ref == "alignment:main-road"
    assert row.secondary_alignment_refs == ["alignment:side-road-01"]
    assert row.control_region_refs == ["region:main-intersection-01", "region:side-intersection-01"]
    assert row.control_area_ref == "intersection:t-01:control-area"
    assert [leg.leg_role for leg in row.leg_rows] == ["primary_before", "primary_after", "side_approach"]
    assert row.leg_rows[0].alignment_ref == "alignment:main-road"
    assert row.leg_rows[-1].alignment_ref == "alignment:side-road-01"


def test_intersection_model_round_trips_control_area_and_leg_context() -> None:
    leg = IntersectionLegRow(
        leg_id="intersection:x-01:leg-primary",
        intersection_id="intersection:x-01",
        leg_role="primary_before",
        alignment_ref="alignment:main",
        profile_ref="profile:main",
        centerline3d_ref="centerline3d:main",
        region_ref="region:main-intersection",
        approach_station_start=480.0,
        approach_station_end=520.0,
    )
    row = IntersectionRow(
        intersection_id="intersection:x-01",
        intersection_kind="cross_intersection",
        primary_alignment_ref="alignment:main",
        secondary_alignment_refs=["alignment:cross"],
        intersection_point_x=100.0,
        intersection_point_y=50.0,
        primary_station=500.0,
        secondary_station_refs={"alignment:cross": 80.0},
        control_region_refs=["region:main-intersection", "region:cross-intersection"],
        leg_rows=[leg],
        policy_refs=["policy:curb-return-basic"],
    )
    control = IntersectionControlArea(
        control_area_id="intersection:x-01:control-main",
        intersection_id="intersection:x-01",
        alignment_ref="alignment:main",
        station_ranges=[(480.0, 560.0)],
        influence_ranges=[(460.0, 580.0)],
        control_region_refs=["region:main-intersection"],
        curb_return_policy_ref="policy:curb-return-basic",
        grading_policy_ref="policy:intersection-grading-basic",
        drainage_policy_ref="policy:intersection-drainage-basic",
    )
    model = IntersectionModel(
        schema_version=1,
        project_id="project:demo",
        intersection_model_id="intersection-model:main",
        intersection_rows=[row],
        control_area_rows=[control],
    )

    assert model.intersection_rows[0].intersection_kind == "cross_intersection"
    assert model.intersection_rows[0].secondary_station_refs["alignment:cross"] == 80.0
    assert model.intersection_rows[0].leg_rows[0].centerline3d_ref == "centerline3d:main"
    assert model.control_area_rows[0].control_region_refs == ["region:main-intersection"]


def test_intersection_kind_helper_rejects_unsupported_kind() -> None:
    try:
        intersection_row_from_kind(intersection_id="intersection:bad", intersection_kind="roundabout")
    except ValueError as exc:
        assert "Unsupported intersection kind" in str(exc)
    else:
        raise AssertionError("Unsupported intersection kind should be rejected.")
