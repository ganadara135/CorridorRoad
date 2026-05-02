import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_APPLIED_SECTIONS,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.models.result.applied_section import AppliedSection, AppliedSectionComponentRow, AppliedSectionFrame, AppliedSectionPoint
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
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
                frame=AppliedSectionFrame(station=0.0, x=100.0, y=200.0, z=10.0, tangent_direction_deg=0.0),
                surface_left_width=5.0,
                surface_right_width=4.5,
                subgrade_depth=0.25,
                daylight_left_width=3.0,
                daylight_right_width=2.5,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.4,
                template_id="template:basic-road",
                region_id="region:main",
                component_rows=[AppliedSectionComponentRow("lane-1", "lane")],
                active_structure_ids=["structure:bridge-01"],
                active_structure_rule_ids=["rule:bridge-section"],
                active_structure_influence_zone_ids=["zone:bridge-01"],
                structure_diagnostic_rows=["info|structure|section:1|Structure context active."],
                point_rows=[
                    AppliedSectionPoint("fg:right", 100.0, 195.5, 9.9, "fg_surface", -4.5),
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
                frame=AppliedSectionFrame(station=20.0, x=120.0, y=200.0, z=11.0, tangent_direction_deg=0.0),
                surface_left_width=5.5,
                surface_right_width=4.0,
                subgrade_depth=0.20,
                daylight_left_width=3.5,
                daylight_right_width=2.0,
                daylight_left_slope=-0.5,
                daylight_right_slope=-0.4,
                template_id="template:basic-road",
                region_id="region:main",
                component_rows=[AppliedSectionComponentRow("lane-1", "lane")],
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
        assert len(list(obj.PointRows)) == 6
        assert len(list(obj.ComponentRows)) == 2
        assert list(obj.RegionIds) == ["region:main", "region:main"]
        assert list(obj.AssemblyIds) == ["assembly:basic-road", "assembly:basic-road"]
        assert list(obj.ActiveStructureRows) == ["section:1|structure:bridge-01"]
        assert list(obj.ActiveStructureRuleRows) == ["section:1|rule:bridge-section"]
        assert list(obj.ActiveStructureInfluenceZoneRows) == ["section:1|zone:bridge-01"]
        assert list(obj.StructureDiagnosticRows) == ["section:1|info\\pstructure\\psection:1\\pStructure context active."]
        assert obj.ReviewShapeStatus == "not_built"
        assert int(obj.ReviewShapeStationCount) == 0
        assert obj.Shape.isNull()
        build_v1_applied_section_set_review_shape(obj)
        assert obj.ReviewShapeStatus == "built"
        assert int(obj.ReviewShapeStationCount) == 2
        assert obj.Shape.BoundBox.XLength > 0.0 or obj.Shape.BoundBox.YLength > 0.0
        assert obj.Name in _group_names(tree[V1_TREE_APPLIED_SECTIONS])
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
        assert [section.surface_left_width for section in model.sections] == [5.0, 5.5]
        assert [section.surface_right_width for section in model.sections] == [4.5, 4.0]
        assert [section.subgrade_depth for section in model.sections] == [0.25, 0.20]
        assert [section.daylight_left_width for section in model.sections] == [3.0, 3.5]
        assert [section.daylight_right_width for section in model.sections] == [2.5, 2.0]
        assert [section.component_rows[0].component_id for section in model.sections] == ["lane-1", "lane-1"]
        assert [section.component_rows[0].kind for section in model.sections] == ["lane", "lane"]
        assert [len(section.point_rows) for section in model.sections] == [3, 3]
        assert model.sections[0].active_structure_ids == ["structure:bridge-01"]
        assert model.sections[0].active_structure_rule_ids == ["rule:bridge-section"]
        assert model.sections[0].active_structure_influence_zone_ids == ["zone:bridge-01"]
        assert model.sections[0].structure_diagnostic_rows == ["info|structure|section:1|Structure context active."]
        assert model.sections[0].point_rows[0].point_role == "fg_surface"
        assert model.sections[0].point_rows[0].lateral_offset == -4.5
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
