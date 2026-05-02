from freecad.Corridor_Road.v1.services.evaluation.legacy_document_adapter import (
    LegacyDocumentAdapter,
)


class _FakeProxy:
    def __init__(self, proxy_type: str):
        self.Type = proxy_type


class _FakeObject:
    def __init__(self, name: str, label: str = "", proxy_type: str = ""):
        self.Name = name
        self.Label = label or name
        self.Proxy = _FakeProxy(proxy_type) if proxy_type else None


class _FakeDocument:
    def __init__(self, *objects):
        self.Name = "Doc"
        self.Label = "Doc"
        self.Objects = list(objects)


class _FakePoint:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


def test_parse_report_row_reads_station_bin_fields() -> None:
    adapter = LegacyDocumentAdapter()

    parsed = adapter._parse_report_row(
        "stationBin|fromStation=0.000|toStation=20.000|side=all|cut=12.500|fill=3.000"
    )

    assert parsed["kind"] == "stationBin"
    assert parsed["fromStation"] == "0.000"
    assert parsed["cut"] == "12.500"


def test_build_preview_bundle_returns_none_without_required_legacy_objects() -> None:
    adapter = LegacyDocumentAdapter()
    document = _FakeDocument(_FakeObject("HorizontalAlignment", proxy_type="HorizontalAlignment"))

    bundle = adapter.build_preview_bundle(document)

    assert bundle is None


def test_find_first_by_proxy_or_name_matches_proxy_type() -> None:
    adapter = LegacyDocumentAdapter()
    document = _FakeDocument(
        _FakeObject("SomethingElse"),
        _FakeObject("SectionSet001", proxy_type="SectionSet"),
    )

    found = adapter._find_first_by_proxy_or_name(document, "SectionSet", "SectionSet")

    assert found is not None
    assert found.Name == "SectionSet001"


def test_nearest_station_row_returns_closest_station() -> None:
    adapter = LegacyDocumentAdapter()

    class _FakeSectionSet:
        StationValues = [0.0, 20.0, 40.0]

    row = adapter.nearest_station_row(_FakeSectionSet(), preferred_station=17.0)

    assert row is not None
    assert row["station"] == 20.0


def test_build_alignment_model_from_ip_points() -> None:
    adapter = LegacyDocumentAdapter()
    project = _FakeObject("CorridorRoadProject", proxy_type="CorridorRoadProject")
    alignment = _FakeObject("HorizontalAlignment001", "Main Alignment", proxy_type="HorizontalAlignment")
    alignment.IPPoints = [_FakePoint(0.0, 0.0), _FakePoint(20.0, 0.0), _FakePoint(35.0, 10.0)]
    alignment.DesignSpeedKph = 60.0
    project.Alignment = alignment
    document = _FakeDocument(project, alignment)

    model = adapter.build_alignment_model(document)

    assert model is not None
    assert model.alignment_id == "HorizontalAlignment001"
    assert len(model.geometry_sequence) == 2
    assert model.constraint_rows[0].kind == "design_speed"


def test_build_profile_model_from_pvi_lists() -> None:
    adapter = LegacyDocumentAdapter()
    project = _FakeObject("CorridorRoadProject", proxy_type="CorridorRoadProject")
    alignment = _FakeObject("HorizontalAlignment001", proxy_type="HorizontalAlignment")
    profile = _FakeObject("VerticalAlignment001", "FG Profile", proxy_type="VerticalAlignment")
    profile.PVIStations = [0.0, 25.0, 50.0]
    profile.PVIElevations = [10.0, 11.5, 11.0]
    profile.CurveLengths = [0.0, 20.0, 0.0]
    profile.ClampOverlaps = True
    profile.MinTangent = 5.0
    project.Alignment = alignment
    project.VerticalAlignment = profile
    document = _FakeDocument(project, alignment, profile)

    model = adapter.build_profile_model(document)

    assert model is not None
    assert model.profile_id == "VerticalAlignment001"
    assert len(model.control_rows) == 3
    assert len(model.vertical_curve_rows) == 1
    assert model.constraint_rows[0].kind == "clamp_overlaps"
