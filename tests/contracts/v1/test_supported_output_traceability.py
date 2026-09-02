import pytest

from freecad.Corridor_Road.v1.models.output.cross_section_drawing import CrossSectionDrawingPayload
from freecad.Corridor_Road.v1.models.output.drainage_output import DrainageOutput
from freecad.Corridor_Road.v1.models.output.earthwork_output import EarthworkBalanceOutput, MassHaulOutput
from freecad.Corridor_Road.v1.models.output.exchange_output import ExchangeOutput
from freecad.Corridor_Road.v1.models.output.plan_output import PlanOutput
from freecad.Corridor_Road.v1.models.output.profile_output import ProfileOutput
from freecad.Corridor_Road.v1.models.output.quantity_output import QuantityOutput
from freecad.Corridor_Road.v1.models.output.section_output import SectionOutput
from freecad.Corridor_Road.v1.models.output.structure_solid_output import StructureSolidOutput
from freecad.Corridor_Road.v1.models.output.surface_output import IntersectionSurfaceZoneOutput, SurfaceOutput
from freecad.Corridor_Road.v1.services.evaluation.output_traceability_service import OutputTraceabilityService


@pytest.mark.parametrize(
    "output_model",
    [
        PlanOutput(schema_version=1, project_id="project:1", plan_output_id="plan:1", source_refs=["alignment:1"]),
        ProfileOutput(schema_version=1, project_id="project:1", profile_output_id="profile-output:1", source_refs=["profile:1"]),
        CrossSectionDrawingPayload(schema_version=1, project_id="project:1", drawing_id="drawing:1", result_refs=["section:1"]),
        SectionOutput(schema_version=1, project_id="project:1", section_output_id="section-output:1", result_refs=["section:1"]),
        SurfaceOutput(schema_version=1, project_id="project:1", surface_output_id="surface-output:1", result_refs=["surface:1"]),
        QuantityOutput(schema_version=1, project_id="project:1", quantity_output_id="quantity-output:1", result_refs=["quantity:1"]),
        EarthworkBalanceOutput(schema_version=1, project_id="project:1", earthwork_output_id="earthwork-output:1", result_refs=["earthwork:1"]),
        MassHaulOutput(schema_version=1, project_id="project:1", mass_haul_output_id="mass-haul-output:1", result_refs=["mass-haul:1"]),
        DrainageOutput(
            schema_version=1,
            project_id="project:1",
            drainage_output_id="drainage-output:1",
            source_refs=["drainage:1"],
            result_refs=["drainage-pipeline:1"],
        ),
        ExchangeOutput(
            schema_version=1,
            project_id="project:1",
            exchange_output_id="exchange:1",
            source_refs=["alignment:1"],
            result_refs=["surface:1"],
        ),
        StructureSolidOutput(
            schema_version=1,
            project_id="project:1",
            structure_solid_output_id="structure-output:1",
            source_refs=["structures:1"],
            result_refs=["applied-sections:1"],
        ),
        IntersectionSurfaceZoneOutput(
            schema_version=1,
            project_id="project:1",
            surface_zone_output_id="intersection-zone-output:1",
            result_refs=["intersection-zone-result:1"],
        ),
    ],
)
def test_supported_outputs_expose_required_owner_refs(output_model) -> None:
    result = OutputTraceabilityService().validate_supported_output(output_model)

    assert result.status == "ready"
    assert result.output_ref
    assert result.diagnostic_rows == ()


def test_missing_result_owner_returns_actionable_diagnostic_without_mutating_output() -> None:
    output = SectionOutput(
        schema_version=1,
        project_id="project:1",
        section_output_id="section-output:missing-owner",
        source_refs=["alignment:1"],
    )

    result = OutputTraceabilityService().validate_supported_output(output)

    assert result.status == "error"
    assert result.diagnostic_rows[0].kind == "output_result_owner_missing"
    assert "do not repair" in result.diagnostic_rows[0].notes.lower()
    assert output.result_refs == []


def test_missing_project_and_identity_are_reported_separately() -> None:
    result = OutputTraceabilityService().validate_supported_output(
        PlanOutput(schema_version=1, project_id="", source_refs=["alignment:1"])
    )

    assert result.status == "error"
    assert [row.kind for row in result.diagnostic_rows] == [
        "output_project_owner_missing",
        "output_identity_missing",
    ]
