from freecad.Corridor_Road.v1.models.source.assembly_model import TemplateSubassembly
from freecad.Corridor_Road.v1.services.evaluation import SubassemblyBenchProfileService


def _row(*, width=5.0, slope=-0.5, parameters=None) -> TemplateSubassembly:
    return TemplateSubassembly(
        "side-slope:right",
        "side_slope",
        side="right",
        width=width,
        slope=slope,
        parameters=dict(parameters or {}),
    )


def _values(result) -> list[tuple[str, float, float]]:
    return [(row.kind, row.width, row.slope) for row in result.segment_rows]


def test_bench_profile_service_returns_plain_side_slope_without_bench_rows() -> None:
    result = SubassemblyBenchProfileService().evaluate(_row(width=4.0, slope=-0.4))

    assert result.status == "ok"
    assert _values(result) == [("side_slope", 4.0, -0.4)]
    assert result.to_dict_rows() == [{"kind": "side_slope", "width": 4.0, "slope": -0.4}]


def test_bench_profile_service_evaluates_breaks_and_total_width_override() -> None:
    result = SubassemblyBenchProfileService().evaluate(
        _row(
            parameters={
                "bench_rows": [
                    {"drop": 1.0, "width": 1.0, "slope": -0.02, "post_slope": -0.25}
                ]
            }
        ),
        total_width=6.0,
    )

    assert result.status == "ok"
    assert _values(result) == [
        ("side_slope", 2.0, -0.5),
        ("bench", 1.0, -0.02),
        ("side_slope", 3.0, -0.25),
    ]


def test_bench_profile_service_repeats_first_bench_to_requested_width() -> None:
    result = SubassemblyBenchProfileService().evaluate(
        _row(
            width=10.0,
            parameters={
                "bench_rows": [
                    {"drop": 2.0, "width": 1.0, "slope": -0.02, "post_slope": -0.5}
                ],
                "repeat_first_bench_to_daylight": True,
            },
        )
    )

    assert _values(result) == [
        ("side_slope", 4.0, -0.5),
        ("bench", 1.0, -0.02),
        ("side_slope", 4.0, -0.5),
        ("bench", 1.0, -0.02),
    ]
    assert sum(row.width for row in result.segment_rows) == 10.0


def test_bench_profile_service_preserves_parse_diagnostics() -> None:
    result = SubassemblyBenchProfileService().evaluate(
        _row(parameters={"bench_rows": [{"drop": 1.0, "width": -1.0, "slope": -0.02, "post_slope": -0.5}]})
    )

    assert result.status == "error"
    assert {row.kind for row in result.diagnostic_rows} == {"invalid_bench_width"}
    assert _values(result) == [("side_slope", 5.0, -0.5)]
