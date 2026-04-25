from freecad.Corridor_Road.v1.commands.cmd_earthwork_balance import (
    build_demo_earthwork_report,
    format_earthwork_report,
)


def test_build_demo_earthwork_report_returns_connected_outputs() -> None:
    report = build_demo_earthwork_report(document_label="Demo Doc")

    assert report["corridor"].label == "Demo Doc"
    assert report["quantity_output"].quantity_output_id == "quantity:v1-demo"
    assert report["earthwork_output"].earthwork_output_id == "earthwork:v1-demo"
    assert report["mass_haul_output"].mass_haul_output_id == "masshaul:v1-demo"
    assert len(report["earthwork_output"].balance_rows) == 2
    assert report["focused_balance_row"] is not None
    assert len(report["key_station_rows"]) == 3
    assert report["key_station_rows"][0]["is_current"] is True


def test_format_earthwork_report_contains_key_summary_lines() -> None:
    summary = format_earthwork_report(build_demo_earthwork_report())

    assert "CorridorRoad v1 Earthwork Balance Viewer" in summary
    assert "Total cut: 120.0 m3" in summary
    assert "Total fill: 110.0 m3" in summary
    assert "Final cumulative mass: -8.0 m3" in summary
    assert "Max surplus/deficit: 45.0 / -8.0 m3" in summary
    assert "Key stations: 3" in summary
    assert "Focus Station: STA 0.000" in summary
