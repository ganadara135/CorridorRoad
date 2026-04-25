from freecad.Corridor_Road.v1.commands.cmd_review_plan_profile import (
    build_alignment_profile_bridge_diagnostics,
)
from freecad.Corridor_Road.v1.models.source.alignment_model import (
    AlignmentElement,
    AlignmentModel,
)
from freecad.Corridor_Road.v1.models.source.profile_model import (
    ProfileControlPoint,
    ProfileModel,
)


def _alignment_model() -> AlignmentModel:
    return AlignmentModel(
        schema_version=1,
        project_id="test-project",
        alignment_id="alignment:test",
        label="Test Alignment",
        geometry_sequence=[
            AlignmentElement(
                element_id="alignment:test:1",
                kind="tangent",
                station_start=0.0,
                station_end=100.0,
                length=100.0,
                geometry_payload={
                    "x_values": [0.0, 100.0],
                    "y_values": [0.0, 0.0],
                },
            )
        ],
    )


def _profile_model(*, alignment_id: str = "alignment:test", stations=None) -> ProfileModel:
    station_values = list(stations or [0.0, 100.0])
    return ProfileModel(
        schema_version=1,
        project_id="test-project",
        profile_id="profile:test",
        alignment_id=alignment_id,
        label="Test Profile",
        control_rows=[
            ProfileControlPoint(
                control_point_id=f"profile:test:pvi:{index}",
                station=float(station),
                elevation=10.0 + index,
            )
            for index, station in enumerate(station_values, start=1)
        ],
    )


def _row(rows: list[dict[str, str]], kind: str) -> dict[str, str]:
    return next(row for row in rows if row["kind"] == kind)


def test_alignment_profile_bridge_diagnostics_accept_valid_link_and_station_range() -> None:
    rows = build_alignment_profile_bridge_diagnostics(
        {
            "preview_source_kind": "document",
            "alignment_model": _alignment_model(),
            "profile_model": _profile_model(),
            "legacy_objects": {
                "alignment": object(),
                "profile": object(),
            },
        }
    )

    assert _row(rows, "preview_source")["status"] == "ok"
    assert _row(rows, "alignment_model")["status"] == "ok"
    assert _row(rows, "profile_model")["status"] == "ok"
    assert _row(rows, "alignment_profile_link")["status"] == "ok"
    assert _row(rows, "profile_station_range")["status"] == "ok"


def test_alignment_profile_bridge_diagnostics_warn_on_alignment_id_mismatch() -> None:
    rows = build_alignment_profile_bridge_diagnostics(
        {
            "preview_source_kind": "document",
            "alignment_model": _alignment_model(),
            "profile_model": _profile_model(alignment_id="alignment:other"),
            "legacy_objects": {
                "alignment": object(),
                "profile": object(),
            },
        }
    )

    assert _row(rows, "alignment_profile_link")["status"] == "warning"


def test_alignment_profile_bridge_diagnostics_warn_on_profile_station_outside_alignment() -> None:
    rows = build_alignment_profile_bridge_diagnostics(
        {
            "preview_source_kind": "document",
            "alignment_model": _alignment_model(),
            "profile_model": _profile_model(stations=[0.0, 140.0]),
            "legacy_objects": {
                "alignment": object(),
                "profile": object(),
            },
        }
    )

    assert _row(rows, "profile_station_range")["status"] == "warning"
