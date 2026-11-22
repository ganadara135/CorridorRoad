"""A compiled PI curve stays within the chord error of the curve, whatever its radius."""

import math

import pytest

from freecad.Corridor_Road.v1.commands.cmd_alignment_editor import (
    MAX_CURVE_CHORD_ERROR_M,
    MAX_CURVE_CHORDS_PER_PART,
    _chord_steps_for_curve,
    _sampled_alignment_chunks_from_ip_rows,
)


def _curve_points(radius: float, transition_length: float, deflection_deg: float) -> list[tuple[float, float]]:
    # Legs long enough that the layout never scales the requested radius down.
    leg = 2.0 * radius * math.tan(0.5 * math.radians(deflection_deg)) + 2.0 * transition_length + 100.0
    angle = math.radians(deflection_deg)
    rows = [
        {"x": 0.0, "y": 0.0, "radius": 0.0, "transition_length": 0.0},
        {"x": leg, "y": 0.0, "radius": radius, "transition_length": transition_length},
        {"x": leg + leg * math.cos(angle), "y": leg * math.sin(angle), "radius": 0.0, "transition_length": 0.0},
    ]
    chunks = _sampled_alignment_chunks_from_ip_rows(rows, use_transition_curves=True, spiral_segments=16)
    return next(chunk for chunk in chunks if chunk["kind"] != "tangent")["points"]


@pytest.mark.parametrize(
    ("radius", "transition_length", "deflection_deg"),
    [(180.0, 0.0, 19.1), (60.0, 0.0, 90.0), (500.0, 0.0, 10.0), (2000.0, 0.0, 30.0), (180.0, 60.0, 40.0), (180.0, 120.0, 60.0)],
)
def test_every_chord_stays_within_the_error_on_its_sharpest_radius(radius, transition_length, deflection_deg) -> None:
    points = _curve_points(radius, transition_length, deflection_deg)

    for start, end in zip(points, points[1:]):
        chord = math.hypot(end[0] - start[0], end[1] - start[1])
        assert radius - math.sqrt(radius * radius - chord * chord / 4.0) <= MAX_CURVE_CHORD_ERROR_M * 1.001


def test_arc_length_is_true_to_two_millimetres() -> None:
    points = _curve_points(180.0, 0.0, 19.1)

    length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))

    # A polyline inscribed in the arc is always a little shorter: here about 1.1 mm.
    assert 0.0 < 180.0 * math.radians(19.1) - length < 2.0e-3


def test_very_small_radius_keeps_its_deflection_based_point_count() -> None:
    assert len(_curve_points(5.0, 0.0, 90.0)) - 1 == 16


def test_chord_count_is_bounded() -> None:
    assert _chord_steps_for_curve(1.0e6, 1.0e5) == MAX_CURVE_CHORDS_PER_PART
    assert _chord_steps_for_curve(0.0, 180.0) == 0
    assert _chord_steps_for_curve(10.0, 0.0) == 0
