from pathlib import Path

from freecad.Corridor_Road.v1.exchange.landxml_import import scan_landxml_file, scan_landxml_text


SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def test_scan_civil3d_landxml_reports_supported_source_and_candidates() -> None:
    result = scan_landxml_file(SAMPLES / "landxml_civil3d_alignment_profile_surface.xml")

    assert result.summary.supported_producer is True
    assert "Civil 3D" in result.summary.detected_producer
    assert result.summary.linear_unit == "meter"
    assert result.summary.alignment_count == 1
    assert result.summary.profile_count == 1
    assert result.summary.surface_count == 1
    assert result.summary.cgpoint_count == 2
    assert result.alignments[0].name == "Main Road CL"
    assert len(result.alignments[0].elements) == 2
    assert result.alignments[0].elements[0].kind == "line"
    assert result.alignments[0].elements[0].length == 50.0
    assert result.profiles[0].name == "FG Main"
    assert len(result.profiles[0].points) == 3
    assert result.surfaces[0].name == "Existing Ground"
    assert result.surfaces[0].faces == (("1", "2", "3"),)
    assert any(row.code == "landxml_civil3d_source_detected" for row in result.diagnostics)


def test_scan_unknown_producer_marks_import_as_unsupported() -> None:
    result = scan_landxml_file(SAMPLES / "landxml_unknown_producer.xml")

    assert result.summary.supported_producer is False
    assert result.summary.alignment_count == 1
    assert any(row.code == "landxml_unsupported_producer" for row in result.diagnostics)


def test_scan_invalid_landxml_text_returns_parse_diagnostic() -> None:
    result = scan_landxml_text("<LandXML>")

    assert result.summary.supported_producer is False
    assert result.alignments == ()
    assert result.diagnostics[0].severity == "error"
    assert result.diagnostics[0].code == "landxml_parse_failed"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] LandXML import parser tests completed.")
