import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_APPLIED_SECTIONS,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.models.result.applied_section import AppliedSection, AppliedSectionFrame, AppliedSectionPoint, AppliedSectionSubassemblyRow
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from freecad.Corridor_Road.v1.common.diagnostics import DiagnosticMessage
from freecad.Corridor_Road.v1.objects.obj_applied_section import (
    build_v1_applied_section_set_review_shape,
    create_or_update_v1_applied_section_set_object,
    find_v1_applied_section_set,
    to_applied_section_set,
)


def _new_project_doc():
    doc = App.newDocument("V1AppliedSectionSetObjectTest")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    tree = ensure_project_tree(project, include_references=False)
    return doc, project, tree


def _sample_set() -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="proj-1",
        applied_section_set_id="sections:main",
        corridor_id="corridor:main",
        alignment_id="alignment:main",
        station_rows=[
            AppliedSectionStationRow("station:1", 0.0, "section:1"),
            AppliedSectionStationRow("station:2", 20.0, "section:2"),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:1",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                profile_id="profile:main",
                assembly_id="assembly:basic-road",
                station=0.0,
                frame=AppliedSectionFrame(
                    station=0.0,
                    x=100.0,
                    y=200.0,
                    z=10.0,
                    tangent_direction_deg=0.0,
                    source_mode="centerline3d_source_geometry",
                    source_status="source_geometry",
                ),
                surface_left_width=5.0,
                surface_right_width=4.5,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=2.5,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.4,
                active_superelevation_id="superelevation:main",
                superelevation_left_crossfall=-2.0,
                superelevation_right_crossfall=4.0,
                active_superelevation_transition_id="transition:runoff",
                superelevation_source_rows=[
                    "left:control:normal",
                    "right:control:right-full",
                    "transition:transition:runoff",
                ],
                active_intersection_id="intersection:t-01",
                active_intersection_control_area_id="area:main",
                active_intersection_leg_id="leg:main",
                active_intersection_leg_role="primary_before",
                active_intersection_control_region_refs=["region:main"],
                active_intersection_grading_policy_ref="grading:main",
                active_intersection_source_status="warning",
                active_intersection_source_diagnostic_rows=["source_leg_profile_ref_missing"],
                active_intersection_source_stage_rows=[
                    "Anchor|accepted|intersection-source-stage:anchor||intersection:t-01,area:main,leg:main",
                    "Control Areas|accepted|intersection-source-stage:control_areas||intersection:t-01,area:main,leg:main",
                    "Edge Families|warning|intersection-source-stage:edge_families|source_leg_edge_policy_refs_missing|intersection:t-01,area:main,leg:main",
                ],
                template_id="template:basic-road",
                region_id="region:main",
                subassembly_rows=[AppliedSectionSubassemblyRow("lane-1", "lane", drainage_refs=["drainage:side-ditch-right"])],
                active_structure_ids=["structure:bridge-01"],
                active_structure_rule_ids=["rule:bridge-section"],
                active_structure_influence_zone_ids=["zone:bridge-01"],
                structure_diagnostic_rows=["info|structure|section:1|Structure context active."],
                point_rows=[
                    AppliedSectionPoint(
                        "fg:right",
                        100.0,
                        195.5,
                        9.9,
                        "fg_surface",
                        -4.5,
                        subassembly_ref="lane-1",
                        side="right",
                        drainage_ref="drainage:side-ditch-right",
                    ),
                    AppliedSectionPoint("fg:center", 100.0, 200.0, 10.0, "fg_surface", 0.0),
                    AppliedSectionPoint("fg:left", 100.0, 205.0, 9.9, "fg_surface", 5.0),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="proj-1",
                applied_section_id="section:2",
                corridor_id="corridor:main",
                alignment_id="alignment:main",
                profile_id="profile:main",
                assembly_id="assembly:basic-road",
                station=20.0,
                frame=AppliedSectionFrame(
                    station=20.0,
                    x=120.0,
                    y=200.0,
                    z=11.0,
                    tangent_direction_deg=0.0,
                    source_mode="alignment_profile_fallback",
                    source_status="fallback",
                    source_diagnostic_rows=["centerline3d_result_missing"],
                ),
                surface_left_width=5.5,
                surface_right_width=4.0,
                subgrade_depth=0.20,
                daylight_left_width=3.5,
                daylight_right_width=2.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.4,
                template_id="template:basic-road",
                region_id="region:main",
                subassembly_rows=[AppliedSectionSubassemblyRow("lane-1", "lane")],
                point_rows=[
                    AppliedSectionPoint("fg:right", 120.0, 196.0, 10.9, "fg_surface", -4.0),
                    AppliedSectionPoint("fg:center", 120.0, 200.0, 11.0, "fg_surface", 0.0),
                    AppliedSectionPoint("fg:left", 120.0, 205.5, 10.9, "fg_surface", 5.5),
                ],
            ),
        ],
        source_refs=["alignment:main", "profile:main", "assembly:basic-road", "regions:main"],
    )


def test_create_or_update_v1_applied_section_set_routes_to_tree() -> None:
    doc, project, tree = _new_project_doc()
    try:
        obj = create_or_update_v1_applied_section_set_object(
            document=doc,
            project=project,
            applied_section_set=_sample_set(),
        )

        assert obj.V1ObjectType == "V1AppliedSectionSet"
        assert obj.CRRecordKind == "v1_applied_section_set"
        assert obj.StationCount == 2
        assert list(obj.StationValues) == [0.0, 20.0]
        assert list(obj.FrameXValues) == [100.0, 120.0]
        assert list(obj.FrameZValues) == [10.0, 11.0]
        assert list(obj.SurfaceLeftWidths) == [5.0, 5.5]
        assert list(obj.SurfaceRightWidths) == [4.5, 4.0]
        assert list(obj.SubgradeDepths) == [0.25, 0.20]
        assert list(obj.DaylightLeftWidths) == [3.0, 3.5]
        assert list(obj.DaylightRightWidths) == [2.5, 2.0]
        assert list(obj.DaylightLeftSlopes) == [-0.5, -0.5]
        assert list(obj.DaylightRightSlopes) == [-0.4, -0.4]
        assert list(obj.SuperelevationIds) == ["superelevation:main", ""]
        assert list(obj.SuperelevationLeftCrossfalls) == [-2.0, 0.0]
        assert list(obj.SuperelevationRightCrossfalls) == [4.0, 0.0]
        assert list(obj.SuperelevationTransitionIds) == ["transition:runoff", ""]
        assert list(obj.SuperelevationSourceRows) == [
            "section:1|left:control:normal|right:control:right-full|transition:transition:runoff",
        ]
        assert list(obj.FrameSourceModes) == ["centerline3d_source_geometry", "alignment_profile_fallback"]
        assert list(obj.FrameSourceStatuses) == ["source_geometry", "fallback"]
        assert list(obj.FrameSourceDiagnosticRows) == ["section:2|centerline3d_result_missing"]
        assert list(obj.IntersectionSourceStatuses) == ["warning", ""]
        assert list(obj.IntersectionSourceDiagnosticRows) == ["section:1|source_leg_profile_ref_missing"]
        assert obj.IntersectionSourceSectionCount == 1
        assert obj.IntersectionSourceWarningCount == 1
        assert obj.IntersectionSourceDiagnosticCount == 2
        assert list(obj.IntersectionSourceStatusCounts) == ["warning=1"]
        assert obj.IntersectionSourceSummary == (
            "intersection_sections=1;intersection_warnings=1;intersection_source_diagnostics=2"
        )
        assert len(list(obj.PointRows)) == 6
        assert len(list(obj.SubassemblyRows)) == 2
        assert list(obj.RegionIds) == ["region:main", "region:main"]
        assert list(obj.AssemblyIds) == ["assembly:basic-road", "assembly:basic-road"]
        assert list(obj.ActiveStructureRows) == ["section:1|structure:bridge-01"]
        assert list(obj.ActiveStructureRuleRows) == ["section:1|rule:bridge-section"]
        assert list(obj.ActiveStructureInfluenceZoneRows) == ["section:1|zone:bridge-01"]
        assert list(obj.StructureDiagnosticRows) == ["section:1|info\\pstructure\\psection:1\\pStructure context active."]
        assert obj.ReviewShapeStatus == "not_built"
        assert obj.SourceSectionCount == 2
        assert obj.SupplementalSectionCount == 0
        assert obj.TotalSectionCount == 2
        assert list(obj.SectionKindCounts) == ["regular_sample=2"]
        assert list(obj.CenterlineSourceModeCounts) == [
            "alignment_profile_fallback=1",
            "centerline3d_source_geometry=1",
        ]
        assert list(obj.CenterlineSourceStatusCounts) == ["fallback=1", "source_geometry=1"]
        assert obj.AppliedSectionDiagnosticSummary == (
            "sections=2;source=2;supplemental=0;centerline_fallback=1;"
            "overlap_clip=0;ditch_shape=0;daylight_fallback=0;diagnostics=0"
        )
        assert int(obj.ReviewShapeStationCount) == 0
        assert obj.Shape.isNull()
        build_v1_applied_section_set_review_shape(obj)
        assert obj.ReviewShapeStatus == "built"
        assert int(obj.ReviewShapeStationCount) == 2
        assert obj.Shape.BoundBox.XLength > 0.0 or obj.Shape.BoundBox.YLength > 0.0
        assert obj.Name in _group_names(tree[V1_TREE_APPLIED_SECTIONS])
    finally:
        App.closeDocument(doc.Name)


def test_v1_applied_section_set_summarizes_result_diagnostics() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        section_set = _sample_set()
        section_set.station_rows[1] = AppliedSectionStationRow("station:2", 20.0, "section:2", kind="supplemental_curve")
        section_set.sections[0].frame = AppliedSectionFrame(
            station=0.0,
            x=100.0,
            y=200.0,
            z=10.0,
            tangent_direction_deg=0.0,
            notes="source=centerline3d_source_geometry",
        )
        section_set.sections[0].diagnostic_rows = [
            DiagnosticMessage("info", "applied_section_overlap_clip", "left side clipped"),
            DiagnosticMessage("warning", "ditch_shape_parameter", "ditch shape inferred from parameters"),
        ]
        section_set.sections[1].frame = AppliedSectionFrame(
            station=20.0,
            x=120.0,
            y=200.0,
            z=11.0,
            tangent_direction_deg=0.0,
            notes="source=alignment_profile_fallback",
        )
        section_set.sections[1].diagnostic_rows = [
            DiagnosticMessage("warning", "bench_daylight_fallback", "fixed-width daylight fallback"),
        ]

        obj = create_or_update_v1_applied_section_set_object(
            document=doc,
            project=project,
            applied_section_set=section_set,
        )

        assert obj.SourceSectionCount == 1
        assert obj.SupplementalSectionCount == 1
        assert obj.TotalSectionCount == 2
        assert list(obj.SectionKindCounts) == ["regular_sample=1", "supplemental_curve=1"]
        assert list(obj.CenterlineSourceModeCounts) == [
            "alignment_profile_fallback=1",
            "centerline3d_source_geometry=1",
        ]
        assert list(obj.CenterlineSourceStatusCounts) == ["fallback=1", "source_geometry=1"]
        assert obj.CenterlineFallbackCount == 1
        assert obj.OverlapClipDiagnosticCount == 1
        assert obj.DitchShapeInferenceDiagnosticCount == 1
        assert obj.DaylightFallbackDiagnosticCount == 1
        assert obj.IntersectionSourceSectionCount == 1
        assert obj.IntersectionSourceWarningCount == 1
        assert obj.IntersectionSourceDiagnosticCount == 2
        assert list(obj.IntersectionSourceStatusCounts) == ["warning=1"]
        assert obj.IntersectionSourceSummary == (
            "intersection_sections=1;intersection_warnings=1;intersection_source_diagnostics=2"
        )
        assert obj.AppliedSectionDiagnosticCount == 3
        assert list(obj.AppliedSectionDiagnosticKinds) == [
            "applied_section_overlap_clip=1",
            "bench_daylight_fallback=1",
            "ditch_shape_parameter=1",
        ]
        assert obj.AppliedSectionDiagnosticSummary == (
            "sections=2;source=1;supplemental=1;centerline_fallback=1;"
            "overlap_clip=1;ditch_shape=1;daylight_fallback=1;diagnostics=3"
        )
        model = to_applied_section_set(obj)
        assert model is not None
        assert [row.kind for row in model.sections[0].diagnostic_rows] == [
            "applied_section_overlap_clip",
            "ditch_shape_parameter",
        ]
        assert [row.kind for row in model.sections[1].diagnostic_rows] == ["bench_daylight_fallback"]
    finally:
        App.closeDocument(doc.Name)


def test_v1_applied_section_set_object_roundtrips_summary_rows() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        obj = create_or_update_v1_applied_section_set_object(
            document=doc,
            project=project,
            applied_section_set=_sample_set(),
        )

        model = to_applied_section_set(obj)

        assert model is not None
        assert model.applied_section_set_id == "sections:main"
        assert [row.station for row in model.station_rows] == [0.0, 20.0]
        assert [section.frame.x for section in model.sections] == [100.0, 120.0]
        assert [section.frame.z for section in model.sections] == [10.0, 11.0]
        assert [section.frame.source_mode for section in model.sections] == [
            "centerline3d_source_geometry",
            "alignment_profile_fallback",
        ]
        assert [section.frame.source_status for section in model.sections] == ["source_geometry", "fallback"]
        assert model.sections[1].frame.source_diagnostic_rows == ["centerline3d_result_missing"]
        assert [section.surface_left_width for section in model.sections] == [5.0, 5.5]
        assert [section.surface_right_width for section in model.sections] == [4.5, 4.0]
        assert [section.subgrade_depth for section in model.sections] == [0.25, 0.20]
        assert [section.daylight_left_width for section in model.sections] == [3.0, 3.5]
        assert [section.daylight_right_width for section in model.sections] == [2.5, 2.0]
        assert [section.active_superelevation_id for section in model.sections] == ["superelevation:main", ""]
        assert [section.superelevation_left_crossfall for section in model.sections] == [-2.0, 0.0]
        assert [section.superelevation_right_crossfall for section in model.sections] == [4.0, 0.0]
        assert [section.active_superelevation_transition_id for section in model.sections] == ["transition:runoff", ""]
        assert model.sections[0].superelevation_source_rows == [
            "left:control:normal",
            "right:control:right-full",
            "transition:transition:runoff",
        ]
        assert model.sections[0].active_intersection_id == "intersection:t-01"
        assert model.sections[0].active_intersection_source_status == "warning"
        assert model.sections[0].active_intersection_source_diagnostic_rows == ["source_leg_profile_ref_missing"]
        assert model.sections[0].active_intersection_source_stage_rows[2].startswith("Edge Families|warning|intersection-source-stage:edge_families")
        assert [section.subassembly_rows[0].subassembly_id for section in model.sections] == ["lane-1", "lane-1"]
        assert [section.subassembly_rows[0].kind for section in model.sections] == ["lane", "lane"]
        assert model.sections[0].subassembly_rows[0].drainage_refs == ["drainage:side-ditch-right"]
        assert [len(section.point_rows) for section in model.sections] == [3, 3]
        assert model.sections[0].active_structure_ids == ["structure:bridge-01"]
        assert model.sections[0].active_structure_rule_ids == ["rule:bridge-section"]
        assert model.sections[0].active_structure_influence_zone_ids == ["zone:bridge-01"]
        assert model.sections[0].structure_diagnostic_rows == ["info|structure|section:1|Structure context active."]
        assert model.sections[0].point_rows[0].point_role == "fg_surface"
        assert model.sections[0].point_rows[0].lateral_offset == -4.5
        assert model.sections[0].point_rows[0].subassembly_ref == "lane-1"
        assert model.sections[0].point_rows[0].side == "right"
        assert model.sections[0].point_rows[0].drainage_ref == "drainage:side-ditch-right"
        assert find_v1_applied_section_set(doc) == obj
    finally:
        App.closeDocument(doc.Name)


def test_v1_applied_section_set_builds_review_shape_when_unhidden() -> None:
    doc, project, _tree = _new_project_doc()
    try:
        obj = create_or_update_v1_applied_section_set_object(
            document=doc,
            project=project,
            applied_section_set=_sample_set(),
        )
        if getattr(obj, "ViewObject", None) is None:
            return

        assert obj.ReviewShapeStatus == "not_built"
        obj.ViewObject.Visibility = True

        assert obj.ViewObject.Visibility is True
        assert obj.ReviewShapeStatus == "built"
        assert obj.Shape.BoundBox.XLength > 0.0 or obj.Shape.BoundBox.YLength > 0.0
    finally:
        App.closeDocument(doc.Name)


def _group_names(folder) -> set[str]:
    return {str(getattr(child, "Name", "") or "") for child in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 applied section set object contract tests completed.")
