from freecad.Corridor_Road.v1.models.source.alignment_model import AlignmentElement, AlignmentModel
from freecad.Corridor_Road.v1.services.evaluation.intersection_alignment_detection_service import (
    AlignmentIntersectionDetectionService,
)


def _alignment(alignment_id: str, points: list[tuple[float, float]]) -> AlignmentModel:
    distances = [0.0]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        distances.append(distances[-1] + ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5)
    length = distances[-1]
    return AlignmentModel(
        schema_version=1,
        project_id="project:demo",
        alignment_id=alignment_id,
        geometry_sequence=[
            AlignmentElement(
                element_id=f"{alignment_id}:element-01",
                kind="sampled_curve",
                station_start=0.0,
                station_end=length,
                length=length,
                geometry_payload={
                    "x_values": [point[0] for point in points],
                    "y_values": [point[1] for point in points],
                },
            )
        ],
    )


def test_alignment_intersection_detection_maps_crossing_stations() -> None:
    primary = _alignment("alignment:main", [(0.0, 0.0), (100.0, 0.0)])
    secondary = _alignment("alignment:side", [(50.0, -25.0), (50.0, 25.0)])

    result = AlignmentIntersectionDetectionService().detect(primary, secondary)

    assert result.status == "intersection"
    assert round(result.x, 3) == 50.0
    assert round(result.y, 3) == 0.0
    assert round(result.primary_station, 3) == 50.0
    assert round(result.secondary_station, 3) == 25.0
    assert result.distance == 0.0


def test_alignment_intersection_detection_reports_nearest_approach() -> None:
    primary = _alignment("alignment:main", [(0.0, 0.0), (100.0, 0.0)])
    secondary = _alignment("alignment:side", [(50.0, 10.0), (50.0, 30.0)])

    result = AlignmentIntersectionDetectionService().detect(primary, secondary)

    assert result.status == "nearest"
    assert round(result.x, 3) == 50.0
    assert round(result.y, 3) == 5.0
    assert round(result.primary_station, 3) == 50.0
    assert round(result.secondary_station, 3) == 0.0
    assert round(result.distance, 3) == 10.0


def test_alignment_intersection_detection_reports_unusable_alignment_geometry() -> None:
    primary = _alignment("alignment:main", [(0.0, 0.0)])
    secondary = _alignment("alignment:side", [(50.0, -25.0), (50.0, 25.0)])

    result = AlignmentIntersectionDetectionService().detect(primary, secondary)

    assert result.status == "error"
    assert "usable sampled XY geometry" in result.notes
