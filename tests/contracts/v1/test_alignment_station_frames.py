"""Station frames of a sampled Alignment element (found by the GR-8 workflow smoke).

A curve with transitions is stored as one sampled element whose chords are a few degrees apart.
Taking each chord's heading turned the station frame by that whole step at every vertex, so on the
inside of the curve neighbouring section lines crossed, overlap clipping cut them and the Daylight
surface folded. And the last station, stored rounded, lay a fraction of a nanometre past the last
element, so it fell back to a coarse 3D Centerline interpolation with a wrong heading.
"""

import math

from freecad.Corridor_Road.v1.models.source.alignment_model import AlignmentElement, AlignmentModel
from freecad.Corridor_Road.v1.services.evaluation.alignment_evaluation_service import AlignmentEvaluationService

# a quarter circle of radius 100 sampled every 10 degrees, then a straight to the north
ARC = [(100.0 * math.sin(math.radians(a)), 100.0 - 100.0 * math.cos(math.radians(a))) for a in range(0, 91, 10)]
ARC_LENGTH = 100.0 * math.pi / 2.0


def _alignment() -> AlignmentModel:
    return AlignmentModel(
        schema_version=1,
        project_id="p",
        alignment_id="alignment:main",
        geometry_sequence=[
            AlignmentElement(
                "curve",
                "sampled_curve",
                0.0,
                ARC_LENGTH,
                length=ARC_LENGTH,
                geometry_payload={"x_values": [x for x, _ in ARC], "y_values": [y for _, y in ARC]},
            ),
            AlignmentElement(
                "tangent",
                "tangent",
                ARC_LENGTH,
                ARC_LENGTH + 50.0,
                length=50.0,
                geometry_payload={"x_values": [100.0, 100.0], "y_values": [100.0, 150.0]},
            ),
        ],
    )


def _heading(station: float) -> float:
    return AlignmentEvaluationService().evaluate_station(_alignment(), station).tangent_direction_deg


def test_the_heading_turns_continuously_through_a_sampled_curve() -> None:
    stations = [ARC_LENGTH * i / 200.0 for i in range(201)]
    headings = [_heading(station) for station in stations]

    steps = [abs(b - a) for a, b in zip(headings, headings[1:])]
    # 90 degrees over 200 steps; a chord heading jumps 10 degrees at every vertex
    assert max(steps) < 1.5
    assert all(b >= a - 1.0e-9 for a, b in zip(headings, headings[1:]))


def test_a_sampled_element_ends_on_its_end_chord_heading() -> None:
    first_chord = math.degrees(math.atan2(ARC[1][1] - ARC[0][1], ARC[1][0] - ARC[0][0]))
    last_chord = math.degrees(math.atan2(ARC[-1][1] - ARC[-2][1], ARC[-1][0] - ARC[-2][0]))

    assert abs(_heading(0.0) - first_chord) < 1.0e-9
    assert abs(_heading(ARC_LENGTH - 1.0e-9) - last_chord) < 1.0e-6


def test_a_tangent_keeps_its_heading() -> None:
    assert abs(_heading(ARC_LENGTH + 25.0) - 90.0) < 1.0e-9


def test_the_rounded_last_station_is_on_the_alignment() -> None:
    end = ARC_LENGTH + 50.0
    result = AlignmentEvaluationService().evaluate_station(_alignment(), round(end, 9) + 5.0e-10)

    assert result.status == "ok"
    assert abs(result.tangent_direction_deg - 90.0) < 1.0e-9
    assert abs(result.y - 150.0) < 1.0e-6
    assert AlignmentEvaluationService().evaluate_station(_alignment(), end + 1.0e-3).status == "out_of_range"
