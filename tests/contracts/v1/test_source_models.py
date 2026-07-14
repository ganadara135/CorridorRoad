from freecad.Corridor_Road.v1.models.source import (
    AlignmentModel,
    AssemblySubassemblyModel,
    OverrideModel,
    ProfileModel,
    ProjectModel,
    BridgeGeometrySpec,
    CulvertGeometrySpec,
    RetainingWallGeometrySpec,
    StructureGeometrySpec,
    RegionModel,
    StructureModel,
    SubassemblyDefinition,
    SubassemblyLibrary,
    SubassemblyLinkRow,
    SubassemblyParameterRow,
    SubassemblyPointRow,
    SubassemblyShapeRow,
    SubassemblyTargetRow,
    SuperelevationModel,
)
from freecad.Corridor_Road.v1.objects.obj_subassembly_library import (
    create_or_update_v1_subassembly_library_object,
    find_v1_subassembly_library,
    to_subassembly_library,
)
from freecad.Corridor_Road.v1.objects.obj_subassembly_assembly import (
    create_or_update_v1_assembly_subassembly_model_object,
    find_v1_assembly_subassembly_model,
    to_assembly_subassembly_model,
)
from freecad.Corridor_Road.v1.models.source.subassembly_definition_presets import (
    subassembly_definition_library_from_preset,
    subassembly_definition_preset_names,
)
from freecad.Corridor_Road.v1.models.source.alignment_model import (
    AlignmentConstraint,
    AlignmentElement,
)
from freecad.Corridor_Road.v1.models.source.assembly_model import (
    SubassemblySectionTemplate,
    TemplateSubassembly,
    normalize_bench_rows,
)
from freecad.Corridor_Road.v1.models.source.profile_model import (
    ProfileControlPoint,
)
from freecad.Corridor_Road.v1.models.source.region_model import RegionRow


def test_source_models_can_be_instantiated() -> None:
    project = ProjectModel(schema_version=1, project_id="proj-1", project_name="Demo")
    alignment = AlignmentModel(
        schema_version=1,
        project_id="proj-1",
        alignment_id="align-1",
        geometry_sequence=[
            AlignmentElement(
                element_id="el-1",
                kind="tangent",
                station_start=0.0,
                station_end=100.0,
                length=100.0,
            )
        ],
        constraint_rows=[
            AlignmentConstraint(
                constraint_id="c-1",
                kind="design_speed",
                value=60.0,
                unit="km/h",
            )
        ],
    )
    profile = ProfileModel(
        schema_version=1,
        project_id="proj-1",
        profile_id="prof-1",
        alignment_id="align-1",
        control_rows=[
            ProfileControlPoint(
                control_point_id="pvi-1",
                station=0.0,
                elevation=10.0,
            )
        ],
    )
    assembly = AssemblySubassemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="asm-1",
        template_rows=[
            SubassemblySectionTemplate(
                template_id="tmpl-1",
                template_kind="roadway",
                subassembly_rows=[
                    TemplateSubassembly(subassembly_id="lane-1", kind="lane"),
                ],
            )
        ],
    )
    region = RegionModel(
        schema_version=1,
        project_id="proj-1",
        region_model_id="reg-1",
        alignment_id="align-1",
        region_rows=[
            RegionRow(
                region_id="region-1",
                station_start=0.0,
                station_end=100.0,
                template_ref="tmpl-1",
            )
        ],
    )
    override_model = OverrideModel(
        schema_version=1,
        project_id="proj-1",
        override_model_id="ovr-1",
        alignment_id="align-1",
    )
    structure_model = StructureModel(
        schema_version=1,
        project_id="proj-1",
        structure_model_id="str-1",
        alignment_id="align-1",
        geometry_spec_rows=[
            StructureGeometrySpec(
                geometry_spec_id="geometry-spec-1",
                structure_ref="structure-1",
                shape_kind="deck_slab",
                width=10.0,
                height=1.2,
            )
        ],
        bridge_geometry_spec_rows=[
            BridgeGeometrySpec("geometry-spec-1", deck_width=10.0, deck_thickness=1.2)
        ],
        culvert_geometry_spec_rows=[
            CulvertGeometrySpec("geometry-spec-2", barrel_shape="box", span=3.0, rise=2.0)
        ],
        retaining_wall_geometry_spec_rows=[
            RetainingWallGeometrySpec("geometry-spec-3", wall_height=3.0, retained_side="right")
        ],
    )
    superelevation = SuperelevationModel(
        schema_version=1,
        project_id="proj-1",
        superelevation_id="sup-1",
        alignment_id="align-1",
    )

    assert project.project_name == "Demo"
    assert alignment.geometry_sequence[0].kind == "tangent"
    assert profile.control_rows[0].elevation == 10.0
    assert assembly.template_rows[0].subassembly_rows[0].kind == "lane"
    assert region.region_rows[0].template_ref == "tmpl-1"
    assert not hasattr(region.region_rows[0], "structure_ref")
    assert not hasattr(region.region_rows[0], "structure_refs")
    assert override_model.override_model_id == "ovr-1"
    assert structure_model.structure_model_id == "str-1"
    assert structure_model.geometry_spec_rows[0].shape_kind == "deck_slab"
    assert structure_model.bridge_geometry_spec_rows[0].deck_width == 10.0
    assert structure_model.culvert_geometry_spec_rows[0].barrel_shape == "box"
    assert structure_model.retaining_wall_geometry_spec_rows[0].retained_side == "right"
    assert superelevation.superelevation_id == "sup-1"


def test_side_slope_subassembly_normalizes_bench_rows_in_parameters() -> None:
    subassembly = TemplateSubassembly(
        subassembly_id="side-slope-left",
        kind="side_slope",
        side="left",
        width=12.0,
        slope=-0.5,
        parameters={
            "bench_rows": [{"drop": "3.0", "width": "1.5", "slope": "-0.02", "post": "-0.5"}],
            "repeat_first_bench_to_daylight": "true",
        },
    )

    assert subassembly.parameters["bench_mode"] == "rows"
    assert subassembly.parameters["bench_rows"] == [
        {"drop": 3.0, "width": 1.5, "slope": -0.02, "post_slope": -0.5, "row_id": "bench:1"}
    ]
    assert subassembly.parameters["repeat_first_bench_to_daylight"] is True


def test_template_subassembly_accepts_definition_ref_and_parameter_overrides() -> None:
    subassembly = TemplateSubassembly(
        subassembly_id="lane-left",
        definition_ref="subassembly-definition:lane-basic",
        kind="lane",
        parameter_overrides={"width": "3.75", "slope": "-2.5"},
    )

    assert subassembly.definition_ref == "subassembly-definition:lane-basic"
    assert subassembly.parameter_overrides == {"width": "3.75", "slope": "-2.5"}


def test_bench_rows_can_be_normalized_from_compact_text() -> None:
    rows = normalize_bench_rows("drop=2.5,width=1.2,slope=-0.02,post_slope=-0.5|3.0,1.5,-0.01,-0.4")

    assert rows == [
        {"drop": 2.5, "width": 1.2, "slope": -0.02, "post_slope": -0.5, "row_id": "bench:1"},
        {"drop": 3.0, "width": 1.5, "slope": -0.01, "post_slope": -0.4, "row_id": "bench:2"},
    ]


def test_subassembly_library_source_model_can_hold_reusable_definitions() -> None:
    library = SubassemblyLibrary(
        schema_version=1,
        project_id="proj-1",
        library_id="subassembly-library:main",
        preset_name="starter-road",
        definition_rows=[
            SubassemblyDefinition(
                definition_id="subassembly-definition:lane-basic",
                name="Basic Lane",
                kind="Lane",
                side_behavior="both",
                parameter_rows=(
                    SubassemblyParameterRow("width", label="Width", value=3.5, unit="m", required=True),
                    SubassemblyParameterRow("slope", label="Crossfall", value=-2.0, unit="%"),
                ),
                point_rows=(
                    SubassemblyPointRow("p0", x_expr="0", z_expr="0", code="CROWN", connectable=True),
                    SubassemblyPointRow("p1", x_expr="width", z_expr="width*slope/100", code="ETW", connectable=True),
                ),
                link_rows=(
                    SubassemblyLinkRow("l0", "p0", "p1", surface_role="finished-grade", quantity_role="lane_width"),
                ),
                shape_rows=(
                    SubassemblyShapeRow("shape:pavement", point_refs="p0,p1,p2,p3", solid_role="pavement_layer"),
                ),
                target_rows=(
                    SubassemblyTargetRow("target:daylight", target_kind="terrain daylight", required=False),
                ),
            )
        ],
    )

    definition = library.definition_by_id("subassembly-definition:lane-basic")

    assert definition is not None
    assert definition.kind == "lane"
    assert definition.side_behavior == "both"
    assert definition.parameter_rows[0].parameter_id == "width"
    assert definition.link_rows[0].surface_role == "design"
    assert definition.shape_rows[0].point_refs == ("p0", "p1", "p2", "p3")
    assert definition.target_rows[0].target_kind == "terrain_daylight"


def test_subassembly_library_object_round_trips_definition_rows() -> None:
    document = _FakeDocument()
    library = SubassemblyLibrary(
        schema_version=1,
        project_id="proj-1",
        library_id="subassembly-library:main",
        preset_name="starter-road",
        definition_rows=[
            SubassemblyDefinition(
                definition_id="subassembly-definition:lane-basic",
                name="Basic Lane",
                kind="lane",
                side_behavior="both",
                parameter_rows=[SubassemblyParameterRow("width", value=3.5, unit="m")],
                point_rows=[
                    SubassemblyPointRow("p0", x_expr="0", z_expr="0"),
                    SubassemblyPointRow("p1", x_expr="width", z_expr="0"),
                ],
                link_rows=[SubassemblyLinkRow("l0", "p0", "p1", surface_role="finished-grade")],
                shape_rows=[SubassemblyShapeRow("shape:pavement", point_refs=("p0", "p1"))],
                target_rows=[SubassemblyTargetRow("target:daylight", target_kind="terrain daylight")],
            )
        ],
    )

    obj = create_or_update_v1_subassembly_library_object(document, library_model=library)
    restored = to_subassembly_library(find_v1_subassembly_library(document))

    assert obj.V1ObjectType == "V1SubassemblyLibrary"
    assert obj.CRRecordKind == "v1_subassembly_library"
    assert obj.DefinitionCount == 1
    assert restored is not None
    assert restored.library_id == "subassembly-library:main"
    assert restored.definition_rows[0].definition_id == "subassembly-definition:lane-basic"
    assert restored.definition_rows[0].parameter_rows[0].parameter_id == "width"
    assert restored.definition_rows[0].link_rows[0].surface_role == "design"


def test_assembly_subassembly_object_round_trips_definition_refs_and_overrides() -> None:
    document = _FakeDocument()
    assembly = AssemblySubassemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="assembly:subassembly-main",
        active_template_id="template:main",
        template_rows=[
            SubassemblySectionTemplate(
                template_id="template:main",
                template_kind="roadway",
                subassembly_rows=[
                    TemplateSubassembly(
                        subassembly_id="lane-left",
                        definition_ref="subassembly-definition:lane-basic",
                        kind="lane",
                        parameter_overrides={"width": 3.75, "slope": -2.5},
                    )
                ],
            )
        ],
    )

    obj = create_or_update_v1_assembly_subassembly_model_object(document, assembly_model=assembly)
    restored = to_assembly_subassembly_model(find_v1_assembly_subassembly_model(document))
    restored_subassembly = restored.template_rows[0].subassembly_rows[0]

    assert obj.V1ObjectType == "V1AssemblySubassemblyModel"
    assert obj.SubassemblyDefinitionRefs == ["subassembly-definition:lane-basic"]
    assert restored_subassembly.definition_ref == "subassembly-definition:lane-basic"
    assert restored_subassembly.parameter_overrides["width"] == 3.75
    assert restored_subassembly.parameter_overrides["slope"] == -2.5


def test_subassembly_definition_preset_creates_reusable_road_primitives() -> None:
    names = subassembly_definition_preset_names()
    library = subassembly_definition_library_from_preset("Starter Road Primitives", project_id="proj-1")
    definition_ids = {row.definition_id for row in library.definition_rows}
    lane = library.definition_by_id("subassembly-definition:lane-basic")
    ditch = library.definition_by_id("subassembly-definition:ditch-trapezoid")

    assert "Starter Road Primitives" in names
    assert library.project_id == "proj-1"
    assert {
        "subassembly-definition:lane-basic",
        "subassembly-definition:shoulder-basic",
        "subassembly-definition:side-slope-daylight",
        "subassembly-definition:ditch-trapezoid",
        "subassembly-definition:gutter-pan",
        "subassembly-definition:curb-basic",
        "subassembly-definition:sidewalk-basic",
    }.issubset(definition_ids)
    assert lane is not None
    assert lane.kind == "lane"
    assert lane.link_rows[0].surface_role == "design"
    assert lane.shape_rows[0].solid_role == "pavement_layer"
    assert ditch is not None
    assert ditch.kind == "ditch"
    assert any(row.surface_role == "drainage_surface" for row in ditch.link_rows)
    assert ditch.target_rows[0].target_kind == "ditch_flowline"
    sidewalk = library.definition_by_id("subassembly-definition:sidewalk-basic")
    assert sidewalk is not None
    assert sidewalk.kind == "sidewalk"
    assert sidewalk.shape_rows[0].solid_role == "sidewalk_body"


class _FakeDocument:
    def __init__(self) -> None:
        self.Objects = []

    def getObject(self, name: str):
        for obj in self.Objects:
            if obj.Name == name:
                return obj
        return None

    def addObject(self, _object_type: str, name: str):
        obj = _FakeObject(name)
        self.Objects.append(obj)
        return obj


class _FakeObject:
    def __init__(self, name: str) -> None:
        self.Name = name
        self.Label = name
        self.ViewObject = _FakeViewObject()

    def addProperty(self, _property_type: str, name: str, _group: str, _doc: str = "") -> None:
        setattr(self, name, None)

    def touch(self) -> None:
        return


class _FakeViewObject:
    pass
