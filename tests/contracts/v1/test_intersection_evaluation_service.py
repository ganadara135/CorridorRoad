from freecad.Corridor_Road.v1.models.source.intersection_model import (
    IntersectionControlArea,
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
)
from freecad.Corridor_Road.v1.services.evaluation.intersection_evaluation_service import (
    IntersectionEvaluationService,
)


def _sample_intersection_model() -> IntersectionModel:
    return IntersectionModel(
        schema_version=1,
        project_id="project:demo",
        intersection_model_id="intersection-model:main",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:t-01",
                intersection_kind="t_intersection",
                primary_alignment_ref="alignment:main",
                secondary_alignment_refs=["alignment:side"],
                leg_rows=[
                    IntersectionLegRow(
                        "intersection:t-01:leg-main-before",
                        "primary_before",
                        "alignment:main",
                        intersection_id="intersection:t-01",
                        region_ref="region:main-intersection",
                        approach_station_start=480.0,
                        approach_station_end=520.0,
                        priority=1,
                    ),
                    IntersectionLegRow(
                        "intersection:t-01:leg-main-after",
                        "primary_after",
                        "alignment:main",
                        intersection_id="intersection:t-01",
                        region_ref="region:main-intersection",
                        approach_station_start=520.0,
                        approach_station_end=560.0,
                        priority=2,
                    ),
                    IntersectionLegRow(
                        "intersection:t-01:leg-side",
                        "side_approach",
                        "alignment:side",
                        intersection_id="intersection:t-01",
                        region_ref="region:side-intersection",
                        approach_station_start=0.0,
                        approach_station_end=120.0,
                        priority=1,
                    ),
                ],
            )
        ],
        control_area_rows=[
            IntersectionControlArea(
                control_area_id="intersection:t-01:control-main",
                intersection_id="intersection:t-01",
                alignment_ref="alignment:main",
                station_ranges=[(480.0, 560.0)],
                influence_ranges=[(460.0, 580.0)],
                control_region_refs=["region:main-intersection"],
                curb_return_policy_ref="policy:curb-return-main",
                turn_lane_policy_ref="policy:turn-lane-main",
                grading_policy_ref="policy:grading-main",
                drainage_policy_ref="policy:drainage-main",
            ),
            IntersectionControlArea(
                control_area_id="intersection:t-01:control-side",
                intersection_id="intersection:t-01",
                alignment_ref="alignment:side",
                station_ranges=[(0.0, 120.0)],
                influence_ranges=[(0.0, 140.0)],
                control_region_refs=["region:side-intersection"],
                curb_return_policy_ref="policy:curb-return-side",
                turn_lane_policy_ref="policy:turn-lane-side",
                grading_policy_ref="policy:grading-side",
                drainage_policy_ref="policy:drainage-side",
            ),
        ],
    )


def test_intersection_evaluation_resolves_by_alignment_and_station() -> None:
    result = IntersectionEvaluationService().resolve_station(
        _sample_intersection_model(),
        90.0,
        alignment_ref="alignment:side",
    )

    assert result.active_intersection_id == "intersection:t-01"
    assert result.active_control_area_id == "intersection:t-01:control-side"
    assert result.active_leg_id == "intersection:t-01:leg-side"
    assert result.leg_role == "side_approach"
    assert result.control_region_refs == ("region:side-intersection",)
    assert result.curb_return_policy_ref == "policy:curb-return-side"
    assert result.turn_lane_policy_ref == "policy:turn-lane-side"
    assert result.grading_policy_ref == "policy:grading-side"
    assert result.drainage_policy_ref == "policy:drainage-side"
    assert result.diagnostic_rows == ()


def test_intersection_evaluation_preserves_station_only_compatibility() -> None:
    result = IntersectionEvaluationService().resolve_station(_sample_intersection_model(), 500.0)

    assert result.active_intersection_id == "intersection:t-01"
    assert result.active_control_area_id == "intersection:t-01:control-main"
    assert result.active_leg_id == "intersection:t-01:leg-main-before"


def test_intersection_evaluation_does_not_cross_match_other_alignment() -> None:
    result = IntersectionEvaluationService().resolve_station(
        _sample_intersection_model(),
        90.0,
        alignment_ref="alignment:main",
    )

    assert result.active_intersection_id == ""
    assert result.diagnostic_rows == ("intersection_context_not_found_for_alignment_station",)


def test_intersection_evaluation_reports_missing_leg_when_control_area_matches() -> None:
    model = _sample_intersection_model()
    result = IntersectionEvaluationService().resolve_station(
        model,
        130.0,
        alignment_ref="alignment:side",
    )

    assert result.active_control_area_id == "intersection:t-01:control-side"
    assert result.active_leg_id == ""
    assert result.diagnostic_rows == ("intersection_leg_not_found_for_alignment_station",)
