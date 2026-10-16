"""Ditch Run prefill and checks of the Drainage editor (DR-1)."""

from freecad.Corridor_Road.v1.models.source.assembly_model import (
    AssemblySubassemblyModel,
    SubassemblySectionTemplate,
    TemplateSubassembly,
)
from freecad.Corridor_Road.v1.models.result.drainage_result import DitchRunFlowline, FlowlineStation
from freecad.Corridor_Road.v1.models.source.drainage_model import DitchRun, DrainageLink, DrainagePoint, DrainagePolicy
from freecad.Corridor_Road.v1.models.source.region_model import RegionModel, RegionRow
from freecad.Corridor_Road.v1.services.editing.drainage_editing_service import (
    RoadStationSpan,
    ditch_choices,
    ditch_run_diagnostics,
    downhill_links,
    link_diagnostics,
    next_point_id,
    point_diagnostics,
    policy_diagnostics,
    prefill_ditch_runs,
)


def _assembly(assembly_id: str, rows: list[TemplateSubassembly]) -> AssemblySubassemblyModel:
    template_id = f"template:{assembly_id}"
    return AssemblySubassemblyModel(
        schema_version=1,
        project_id="p",
        assembly_id=assembly_id,
        active_template_id=template_id,
        template_rows=[SubassemblySectionTemplate(template_id, "roadway", subassembly_rows=rows)],
    )


DITCHED = _assembly(
    "ditched",
    [
        TemplateSubassembly("lane:left", "lane", side="left", width=3.5),
        TemplateSubassembly("ditch:left", "ditch", side="left", width=1.8),
        TemplateSubassembly("ditch:right", "ditch", side="right", width=1.8),
    ],
)
BRIDGE = _assembly("bridge", [TemplateSubassembly("lane:left", "lane", side="left", width=3.5)])
BOTH_SIDES = _assembly("both", [TemplateSubassembly("ditch:both", "ditch", side="both", width=1.0)])


def _regions(*rows: tuple[str, float, float, str]) -> RegionModel:
    return RegionModel(
        schema_version=1,
        project_id="p",
        region_model_id="regions:main",
        alignment_id="alignment:main",
        region_rows=[RegionRow(region_id, start, end, assembly_ref=assembly) for region_id, start, end, assembly in rows],
    )


def _spans(runs: list[DitchRun]) -> list[tuple[str, str, float, float]]:
    return [(run.subassembly_ref, run.side, run.station_start, run.station_end) for run in runs]


def test_prefill_joins_a_ditch_across_regions_and_splits_it_where_a_region_has_none() -> None:
    regions = _regions(
        ("region:a", 0.0, 100.0, "ditched"),
        ("region:b", 100.0, 180.0, "ditched"),
        ("region:bridge", 180.0, 240.0, "bridge"),
        ("region:c", 240.0, 400.0, "ditched"),
    )

    runs = prefill_ditch_runs([RoadStationSpan("alignment:main", regions)], [DITCHED, BRIDGE])

    assert _spans(runs) == [
        ("ditch:left", "left", 0.0, 180.0),
        ("ditch:right", "right", 0.0, 180.0),
        ("ditch:left", "left", 240.0, 400.0),
        ("ditch:right", "right", 240.0, 400.0),
    ]
    assert [run.ditch_run_id for run in runs] == [
        "ditch-run:ditch:left",
        "ditch-run:ditch:right",
        "ditch-run:ditch:left:2",
        "ditch-run:ditch:right:2",
    ]
    assert {run.alignment_ref for run in runs} == {"alignment:main"}
    assert ditch_run_diagnostics(runs, ditch_choices([DITCHED, BRIDGE])) == []


def test_prefill_without_regions_covers_the_road_with_the_first_assembly() -> None:
    runs = prefill_ditch_runs([RoadStationSpan("alignment:main", None, 0.0, 250.0)], [BOTH_SIDES])

    # a "both" ditch drains each side of the road
    assert _spans(runs) == [("ditch:both", "left", 0.0, 250.0), ("ditch:both", "right", 0.0, 250.0)]


def test_prefill_names_the_road_only_when_there_are_several() -> None:
    roads = [RoadStationSpan("alignment:a", None, 0.0, 100.0), RoadStationSpan("alignment:b", None, 0.0, 80.0)]

    runs = prefill_ditch_runs(roads, [DITCHED])

    assert [(run.ditch_run_id, run.alignment_ref) for run in runs] == [
        ("ditch-run:alignment:a:ditch:left", "alignment:a"),
        ("ditch-run:alignment:a:ditch:right", "alignment:a"),
        ("ditch-run:alignment:b:ditch:left", "alignment:b"),
        ("ditch-run:alignment:b:ditch:right", "alignment:b"),
    ]
    assert prefill_ditch_runs([RoadStationSpan("alignment:main", None, 0.0, 250.0)], [BOTH_SIDES])[0].ditch_run_id == "ditch-run:ditch:both:left"


def test_prefill_is_empty_without_a_ditch() -> None:
    assert prefill_ditch_runs([RoadStationSpan("alignment:main", None, 0.0, 250.0)], [BRIDGE]) == []


def test_ditch_run_checks_name_the_problem() -> None:
    choices = ditch_choices([DITCHED])
    runs = [
        DitchRun("run:1", "left", "ditch:left", 0.0, 100.0),
        DitchRun("run:1", "left", "ditch:left", 50.0, 150.0),
        DitchRun("run:3", "right", "ditch:left", 0.0, 100.0),
        DitchRun("run:4", "left", "lane:left", 0.0, 100.0),
        DitchRun("run:5", "right", "ditch:right", 100.0, 100.0),
    ]

    messages = ditch_run_diagnostics(runs, choices)

    assert "run:1: the id is used twice." in messages
    assert "run:1 and run:1 overlap on the same ditch and side." in messages
    assert "run:3: ditch 'ditch:left' has no right side." in messages
    assert "run:4: 'lane:left' is not a ditch in any Assembly." in messages
    assert "run:5: End STA must be after Start STA." in messages


def test_a_switched_off_run_may_overlap() -> None:
    runs = [
        DitchRun("run:1", "left", "ditch:left", 0.0, 100.0),
        DitchRun("run:2", "left", "ditch:left", 50.0, 150.0, enabled=False),
    ]

    assert ditch_run_diagnostics(runs, ditch_choices([DITCHED])) == []


def test_policy_checks() -> None:
    assert policy_diagnostics(DrainagePolicy()) == []
    assert policy_diagnostics(DrainagePolicy(min_grade_percent=0.0, max_inlet_spacing_m=-1.0, low_point_rule="pump")) == [
        "Minimum grade must be above 0 %.",
        "Maximum inlet spacing must be above 0 m.",
        "Low point rule must be one of require_inlet, allow_ponding.",
    ]


def test_point_checks_name_the_problem() -> None:
    runs = [DitchRun("run:left", "left", "ditch:left", 0.0, 100.0)]
    points = [
        DrainagePoint("inlet:1", "inlet", 40.0, ditch_run_ref="run:left"),
        DrainagePoint("inlet:1", "inlet", 60.0, ditch_run_ref="run:left"),
        DrainagePoint("inlet:2", "inlet", 60.0),
        DrainagePoint("pump:1", "pump", 60.0, ditch_run_ref="run:left"),
        DrainagePoint("outfall:1", "outfall", 100.0, ditch_run_ref="run:gone"),
        # a culvert crosses the road and may name no run; one far off its run is the evaluation's to report
        DrainagePoint("culvert:1", "culvert", 500.0),
    ]

    assert point_diagnostics(points, runs) == [
        "inlet:1: the id is used twice.",
        "inlet:2: an inlet needs the Ditch Run it collects from.",
        "pump:1: kind must be one of inlet, outfall, culvert, not 'pump'.",
        "outfall:1: Ditch Run 'run:gone' does not exist.",
    ]
    assert next_point_id("inlet", {"inlet:1", "inlet:2"}) == "inlet:3"


def test_link_checks_name_the_problem() -> None:
    points = [DrainagePoint("inlet:1", "inlet", 40.0, ditch_run_ref="run:left"), DrainagePoint("outfall:1", "outfall", 100.0, ditch_run_ref="run:left")]
    links = [
        DrainageLink("link:1", "inlet:1", "outfall:1"),
        DrainageLink("link:1", "inlet:1", "outfall:9"),
        DrainageLink("link:3", "outfall:1", "outfall:1"),
        DrainageLink("link:4", "inlet:1", "outfall:1"),
    ]

    assert link_diagnostics(links, points) == [
        "link:1: the id is used twice.",
        "link:1: To point 'outfall:9' does not exist.",
        "link:3: links outfall:1 to itself.",
        "link:4: inlet:1 is already linked to outfall:1.",
    ]


def test_downhill_links_join_each_unlinked_inlet_to_the_nearest_lower_point() -> None:
    # a run falling 1 % from STA 0 to STA 200
    stations = [FlowlineStation(float(s), float(s), 0.0, 10.0 - s / 100.0) for s in range(0, 201, 20)]
    flowline = DitchRunFlowline("run:left", "left", "ditch:left", station_rows=stations)
    points = [
        DrainagePoint("inlet:1", "inlet", 40.0, ditch_run_ref="run:left"),
        DrainagePoint("inlet:2", "inlet", 100.0, ditch_run_ref="run:left"),
        DrainagePoint("inlet:3", "inlet", 160.0, ditch_run_ref="run:left"),
        DrainagePoint("outfall:1", "outfall", 200.0, ditch_run_ref="run:left"),
        # on another run: never a target
        DrainagePoint("outfall:other", "outfall", 120.0, ditch_run_ref="run:right"),
    ]
    existing = [DrainageLink("link:1", "inlet:3", "outfall:1")]

    added = downhill_links(points, existing, [flowline])

    assert [(link.link_id, link.from_ref, link.to_ref) for link in added] == [
        ("link:2", "inlet:1", "inlet:2"),
        ("link:3", "inlet:2", "inlet:3"),
    ]
