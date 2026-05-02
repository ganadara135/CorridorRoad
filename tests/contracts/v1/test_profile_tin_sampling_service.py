from freecad.Corridor_Road.v1.models.result import TINSurface
from freecad.Corridor_Road.v1.models.result.tin_surface import TINTriangle, TINVertex
from freecad.Corridor_Road.v1.models.source.alignment_model import (
    AlignmentElement,
    AlignmentModel,
)
from freecad.Corridor_Road.v1.services.evaluation import ProfileTinSamplingService


def _alignment() -> AlignmentModel:
    return AlignmentModel(
        schema_version=1,
        project_id="test-project",
        alignment_id="alignment:profile-eg",
        geometry_sequence=[
            AlignmentElement(
                element_id="alignment:profile-eg:tangent:1",
                kind="tangent",
                station_start=0.0,
                station_end=10.0,
                length=10.0,
                geometry_payload={
                    "x_values": [0.0, 10.0],
                    "y_values": [0.0, 0.0],
                },
            )
        ],
    )


def _long_alignment() -> AlignmentModel:
    return AlignmentModel(
        schema_version=1,
        project_id="test-project",
        alignment_id="alignment:profile-eg-long",
        geometry_sequence=[
            AlignmentElement(
                element_id="alignment:profile-eg-long:tangent:1",
                kind="tangent",
                station_start=0.0,
                station_end=20.0,
                length=20.0,
                geometry_payload={
                    "x_values": [0.0, 20.0],
                    "y_values": [0.0, 0.0],
                },
            )
        ],
    )


def _surface() -> TINSurface:
    return TINSurface(
        schema_version=1,
        project_id="test-project",
        surface_id="tin:profile-eg",
        vertex_rows=[
            TINVertex("v0", 0.0, 0.0, 100.0),
            TINVertex("v1", 10.0, 0.0, 110.0),
            TINVertex("v2", 10.0, 10.0, 120.0),
            TINVertex("v3", 0.0, 10.0, 110.0),
        ],
        triangle_rows=[
            TINTriangle("t0", "v0", "v1", "v2"),
            TINTriangle("t1", "v0", "v2", "v3"),
        ],
    )


def test_profile_tin_sampling_builds_existing_ground_rows() -> None:
    result = ProfileTinSamplingService().sample_alignment(
        alignment=_alignment(),
        surface=_surface(),
        interval=5.0,
    )

    assert result.status == "ok"
    assert result.hit_count == 3
    assert [row.station for row in result.rows] == [0.0, 5.0, 10.0]
    assert [round(float(row.elevation or 0.0), 6) for row in result.rows] == [100.0, 105.0, 110.0]
    assert all(row.face_id for row in result.rows)


def test_profile_tin_sampling_preserves_no_hit_as_none() -> None:
    result = ProfileTinSamplingService().sample_alignment(
        alignment=_long_alignment(),
        surface=_surface(),
        interval=10.0,
    )

    assert result.status == "partial"
    assert [row.status for row in result.rows] == ["ok", "ok", "no_hit"]
    assert result.rows[-1].elevation is None
    assert result.rows[-1].elevation != 0.0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 profile TIN sampling service contract tests completed.")
