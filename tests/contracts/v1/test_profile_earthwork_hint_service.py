from freecad.Corridor_Road.v1.models.output.profile_output import (
    ProfileLineRow,
    ProfileOutput,
)
from freecad.Corridor_Road.v1.services.evaluation import ProfileEarthworkHintService


def _profile_output() -> ProfileOutput:
    return ProfileOutput(
        schema_version=1,
        project_id="test-project",
        profile_output_id="profile:test",
        alignment_id="alignment:test",
        profile_id="profile:test",
        line_rows=[
            ProfileLineRow(
                line_row_id="profile:test:fg",
                kind="finished_grade",
                station_values=[0.0, 10.0, 20.0],
                elevation_values=[100.0, 102.0, 101.0],
                style_role="finished_grade",
            ),
            ProfileLineRow(
                line_row_id="profile:test:eg",
                kind="existing_ground_line",
                station_values=[0.0, 5.0, 10.0, 20.0],
                elevation_values=[101.0, 101.0, 101.0, 101.0],
                style_role="existing_ground",
            ),
        ],
    )


def test_profile_earthwork_hint_service_compares_fg_and_eg() -> None:
    result = ProfileEarthworkHintService().build(_profile_output())

    assert result.status == "ok"
    assert [row.station for row in result.rows] == [0.0, 5.0, 10.0, 20.0]
    assert [row.kind for row in result.rows] == [
        "profile_cut_depth",
        "profile_balanced_depth",
        "profile_fill_depth",
        "profile_balanced_depth",
    ]
    assert [round(row.delta, 6) for row in result.rows] == [-1.0, 0.0, 1.0, 0.0]


def test_profile_earthwork_hint_rows_convert_to_profile_earthwork_rows() -> None:
    service = ProfileEarthworkHintService()
    result = service.build(_profile_output())
    rows = service.to_profile_earthwork_rows(result, row_id_prefix="profile:test")

    assert len(rows) == 4
    assert rows[0].kind == "profile_cut_depth"
    assert rows[0].station_start == 0.0
    assert rows[0].station_end == 0.0
    assert rows[0].value == 1.0
    assert rows[0].unit == "m"


def test_profile_earthwork_hint_service_requires_fg_and_eg() -> None:
    result = ProfileEarthworkHintService().build(
        ProfileOutput(
            schema_version=1,
            project_id="test-project",
            profile_output_id="profile:test",
            alignment_id="alignment:test",
            profile_id="profile:test",
        )
    )

    assert result.status == "missing_input"
    assert result.rows == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 profile earthwork hint service contract tests completed.")
