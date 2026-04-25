from freecad.Corridor_Road.v1.models.output.profile_output import (
    ProfileEarthworkRow,
    ProfileOutput,
)
from freecad.Corridor_Road.v1.services.evaluation import ProfileEarthworkAreaHintService


def _profile_output_with_depth_rows() -> ProfileOutput:
    return ProfileOutput(
        schema_version=1,
        project_id="test-project",
        profile_output_id="profile:test",
        alignment_id="alignment:test",
        profile_id="profile:test",
        earthwork_rows=[
            ProfileEarthworkRow(
                earthwork_row_id="profile:test:depth:1",
                kind="profile_cut_depth",
                station_start=0.0,
                station_end=0.0,
                value=1.5,
                unit="m",
            ),
            ProfileEarthworkRow(
                earthwork_row_id="profile:test:depth:2",
                kind="profile_fill_depth",
                station_start=10.0,
                station_end=10.0,
                value=2.0,
                unit="m",
            ),
            ProfileEarthworkRow(
                earthwork_row_id="profile:test:depth:3",
                kind="profile_balanced_depth",
                station_start=20.0,
                station_end=20.0,
                value=0.0,
                unit="m",
            ),
            ProfileEarthworkRow(
                earthwork_row_id="profile:test:balance:1",
                kind="usable_cut_minus_fill",
                station_start=0.0,
                station_end=20.0,
                value=5.0,
                unit="m3",
            ),
        ],
    )


def test_profile_earthwork_area_hint_service_builds_width_based_areas() -> None:
    result = ProfileEarthworkAreaHintService().build(
        _profile_output_with_depth_rows(),
        section_width=12.0,
    )

    assert result.status == "ok"
    assert [row.kind for row in result.rows] == [
        "profile_cut_area",
        "profile_fill_area",
        "profile_balanced_area",
    ]
    assert [row.station for row in result.rows] == [0.0, 10.0, 20.0]
    assert [row.area for row in result.rows] == [18.0, 24.0, 0.0]
    assert all(row.unit == "m2" for row in result.rows)


def test_profile_earthwork_area_hint_rows_convert_to_profile_earthwork_rows() -> None:
    service = ProfileEarthworkAreaHintService()
    result = service.build(_profile_output_with_depth_rows(), section_width=10.0)
    rows = service.to_profile_earthwork_rows(result, row_id_prefix="profile:test")

    assert len(rows) == 3
    assert rows[0].kind == "profile_cut_area"
    assert rows[0].station_start == 0.0
    assert rows[0].station_end == 0.0
    assert rows[0].value == 15.0
    assert rows[0].unit == "m2"


def test_profile_earthwork_area_hint_service_requires_positive_width() -> None:
    result = ProfileEarthworkAreaHintService().build(
        _profile_output_with_depth_rows(),
        section_width=None,
    )

    assert result.status == "missing_width"
    assert result.rows == []


def test_profile_earthwork_area_hint_service_ignores_unrelated_rows() -> None:
    result = ProfileEarthworkAreaHintService().build(
        ProfileOutput(
            schema_version=1,
            project_id="test-project",
            profile_output_id="profile:test",
            alignment_id="alignment:test",
            profile_id="profile:test",
            earthwork_rows=[
                ProfileEarthworkRow(
                    earthwork_row_id="profile:test:balance:1",
                    kind="usable_cut_minus_fill",
                    station_start=0.0,
                    station_end=20.0,
                    value=5.0,
                    unit="m3",
                ),
            ],
        ),
        section_width=12.0,
    )

    assert result.status == "missing_input"
    assert result.rows == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 profile earthwork area hint service contract tests completed.")
