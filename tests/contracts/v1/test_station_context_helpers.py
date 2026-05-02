from freecad.Corridor_Road.v1.ui.common.station_context import (
    context_station_label,
    context_station_value,
    nearest_span_index,
    nearest_value_index,
)


def test_context_station_label_uses_explicit_label() -> None:
    context = {"station_row": {"station": 12.5, "label": "STA 0+012.500"}}

    assert context_station_value(context) == 12.5
    assert context_station_label(context) == "STA 0+012.500"


def test_context_station_label_falls_back_to_numeric_value() -> None:
    context = {"station_row": {"station": 25.0}}

    assert context_station_label(context) == "STA 25.000"


def test_nearest_value_index_returns_closest_row() -> None:
    assert nearest_value_index([0.0, 20.0, 40.0], 18.0) == 1


def test_nearest_span_index_prefers_containing_row() -> None:
    spans = [(0.0, 10.0), (10.0, 30.0), (30.0, 50.0)]

    assert nearest_span_index(spans, 18.0) == 1


def test_nearest_span_index_falls_back_to_nearest_center() -> None:
    spans = [(0.0, 10.0), (20.0, 30.0), (40.0, 50.0)]

    assert nearest_span_index(spans, 34.0) == 1
