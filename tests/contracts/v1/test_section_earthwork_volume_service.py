from freecad.Corridor_Road.v1.models.result.quantity_model import QuantityFragment
from freecad.Corridor_Road.v1.services.evaluation import SectionEarthworkVolumeService


def _area_fragment(
    fragment_id: str,
    quantity_kind: str,
    station: float,
    value: float,
) -> QuantityFragment:
    return QuantityFragment(
        fragment_id=fragment_id,
        quantity_kind=quantity_kind,
        measurement_kind="station_fragment",
        value=value,
        unit="m2",
        station_start=station,
        station_end=station,
        component_ref="section_earthwork_area",
    )


def test_section_earthwork_volume_service_builds_average_end_area_fragments() -> None:
    result = SectionEarthworkVolumeService().build(
        [
            _area_fragment("cut-area:0", "cut_area", 0.0, 2.0),
            _area_fragment("cut-area:10", "cut_area", 10.0, 4.0),
            _area_fragment("fill-area:0", "fill_area", 0.0, 1.0),
            _area_fragment("fill-area:10", "fill_area", 10.0, 3.0),
        ],
        station_values=[0.0, 10.0],
        fragment_id_prefix="quantity:test:volume",
    )

    assert result.status == "ok"
    assert [row.quantity_kind for row in result.rows] == ["cut", "fill"]
    assert [row.measurement_kind for row in result.rows] == [
        "average_end_area_volume",
        "average_end_area_volume",
    ]
    assert [row.value for row in result.rows] == [30.0, 20.0]
    assert all(row.unit == "m3" for row in result.rows)


def test_section_earthwork_volume_service_requires_complete_station_pairs() -> None:
    result = SectionEarthworkVolumeService().build(
        [
            _area_fragment("cut-area:0", "cut_area", 0.0, 2.0),
            _area_fragment("cut-area:20", "cut_area", 20.0, 4.0),
        ],
        station_values=[0.0, 10.0, 20.0],
        fragment_id_prefix="quantity:test:volume",
    )

    assert result.status == "empty"
    assert result.rows == []


def test_section_earthwork_volume_service_requires_area_fragments() -> None:
    result = SectionEarthworkVolumeService().build(
        [],
        station_values=[0.0, 10.0],
        fragment_id_prefix="quantity:test:volume",
    )

    assert result.status == "missing_input"
    assert result.rows == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 section earthwork volume service contract tests completed.")
