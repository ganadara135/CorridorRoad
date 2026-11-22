"""The sample Alignment is a road: tangent at its joints, and the road its own PI rows describe."""

import math

import FreeCAD as App
import pytest

from freecad.Corridor_Road.v1.commands.cmd_alignment_editor import apply_alignment_ip_rows
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment, to_alignment_model
from freecad.Corridor_Road.v1.services.evaluation.alignment_evaluation_service import AlignmentEvaluationService

END_STATION = 180.0
STATIONS = [END_STATION * i / 1800 for i in range(1801)]


@pytest.fixture
def sample():
    doc = App.newDocument("CRV1SampleAlignment")
    try:
        yield create_sample_v1_alignment(doc)
    finally:
        App.closeDocument(doc.Name)


def _frames(obj):
    model = to_alignment_model(obj)
    service = AlignmentEvaluationService()
    rows = [service.evaluate_station(model, station) for station in STATIONS]
    assert all(row.status == "ok" for row in rows)
    return rows


def test_the_stations_and_elements_stay_as_they_were(sample) -> None:
    assert list(sample.ElementKinds) == ["tangent", "sampled_curve", "tangent"]
    assert list(sample.StationStarts) == [0.0, 60.0, 120.0]
    assert list(sample.StationEnds) == [60.0, 120.0, 180.0]
    assert sample.TotalLength == 180.0


def test_each_element_is_as_long_as_its_stations(sample) -> None:
    for x_row, y_row, length in zip(sample.XValueRows, sample.YValueRows, sample.ElementLengths):
        points = list(zip(map(float, x_row.split(",")), map(float, y_row.split(","))))
        assert sum(math.dist(a, b) for a, b in zip(points, points[1:])) == pytest.approx(length, abs=0.01)


def test_the_heading_has_no_jump_along_the_road(sample) -> None:
    headings = [row.tangent_direction_deg for row in _frames(sample)]
    # the old sample turned 30.9 degrees between two neighbouring stations at STA 60
    assert max(abs(b - a) for a, b in zip(headings, headings[1:])) < 0.5
    assert headings[0] == pytest.approx(0.0, abs=1.0e-9)
    # 60 m of curve at R = 180 m turns the road by a third of a radian
    assert headings[-1] == pytest.approx(math.degrees(60.0 / 180.0), abs=1.0e-6)


def test_its_pi_rows_compile_to_the_same_road_with_no_criteria_warning(sample) -> None:
    before = _frames(sample)
    rows = [
        {"x": point.x, "y": point.y, "radius": radius, "transition_length": transition}
        for point, radius, transition in zip(sample.IPPoints, sample.CurveRadii, sample.TransitionLengths)
    ]
    compiled = apply_alignment_ip_rows(sample, rows)

    assert [row["kind"] for row in compiled] == ["tangent", "sampled_curve", "tangent"]
    # the panel samples the arc more coarsely, and its chords are a few centimetres shorter in all
    assert sample.TotalLength == pytest.approx(END_STATION, abs=0.03)
    assert not [text for text in sample.CriteriaMessages if not text.startswith("[INFO]")]
    assert sample.CriteriaStatus.startswith("WARN (1)")  # the one [INFO] line the compile always adds
    # the panel samples this arc with fewer, longer chords, so the road is compared at its vertices:
    # they lie on the sample's circle, whose centre is 180 m left of the end of the first straight
    curve = compiled[1]
    xs = [float(value) for value in str(curve["x_values"]).split(",")]
    ys = [float(value) for value in str(curve["y_values"]).split(",")]
    assert (xs[0], ys[0]) == pytest.approx((before[600].x, before[600].y), abs=1.0e-3)
    for x, y in zip(xs, ys):
        assert math.hypot(x - 60.0, y - 180.0) == pytest.approx(180.0, abs=1.0e-3)
