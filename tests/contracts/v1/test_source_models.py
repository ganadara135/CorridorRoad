from freecad.Corridor_Road.v1.models.source import (
    AlignmentModel,
    AssemblyModel,
    OverrideModel,
    ProfileModel,
    ProjectModel,
    RegionModel,
    StructureModel,
    SuperelevationModel,
)
from freecad.Corridor_Road.v1.models.source.alignment_model import (
    AlignmentConstraint,
    AlignmentElement,
)
from freecad.Corridor_Road.v1.models.source.assembly_model import (
    SectionTemplate,
    TemplateComponent,
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
    assembly = AssemblyModel(
        schema_version=1,
        project_id="proj-1",
        assembly_id="asm-1",
        template_rows=[
            SectionTemplate(
                template_id="tmpl-1",
                template_kind="roadway",
                component_rows=[
                    TemplateComponent(component_id="lane-1", kind="lane"),
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
                region_kind="mainline_region",
                station_start=0.0,
                station_end=100.0,
                applied_layers="ditch, drainage",
                structure_refs=["structure:bridge-01"],
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
    assert assembly.template_rows[0].component_rows[0].kind == "lane"
    assert region.region_rows[0].template_ref == "tmpl-1"
    assert region.region_rows[0].primary_kind == "normal_road"
    assert region.region_rows[0].applied_layers == ["ditch", "drainage"]
    assert region.region_rows[0].structure_refs == ["structure:bridge-01"]
    assert override_model.override_model_id == "ovr-1"
    assert structure_model.structure_model_id == "str-1"
    assert superelevation.superelevation_id == "sup-1"
