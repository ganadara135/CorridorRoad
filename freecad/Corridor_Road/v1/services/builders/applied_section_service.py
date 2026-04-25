"""Applied section builder service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
)
from ...models.source.alignment_model import AlignmentModel
from ...models.source.assembly_model import AssemblyModel, SectionTemplate
from ...models.source.override_model import OverrideModel
from ...models.source.profile_model import ProfileModel
from ...models.source.region_model import RegionModel
from ...models.source.structure_model import StructureModel
from ...services.evaluation.alignment_evaluation_service import (
    AlignmentEvaluationService,
)
from ...services.evaluation.override_resolution_service import (
    OverrideResolutionService,
)
from ...services.evaluation.profile_evaluation_service import (
    ProfileEvaluationService,
)
from ...services.evaluation.region_resolution_service import (
    RegionResolutionService,
)
from ...services.evaluation.structure_interaction_service import (
    StructureInteractionService,
)


@dataclass(frozen=True)
class AppliedSectionBuildRequest:
    """Input bundle used to build one minimal applied section."""

    project_id: str
    corridor_id: str
    alignment: AlignmentModel
    profile: ProfileModel
    assembly: AssemblyModel
    region_model: RegionModel
    override_model: OverrideModel
    station: float
    applied_section_id: str
    structure_model: StructureModel | None = None


class AppliedSectionService:
    """Build minimal applied-section results from v1 source models."""

    def __init__(
        self,
        *,
        alignment_service: AlignmentEvaluationService | None = None,
        profile_service: ProfileEvaluationService | None = None,
        region_service: RegionResolutionService | None = None,
        override_service: OverrideResolutionService | None = None,
        structure_service: StructureInteractionService | None = None,
    ) -> None:
        self.alignment_service = alignment_service or AlignmentEvaluationService()
        self.profile_service = profile_service or ProfileEvaluationService()
        self.region_service = region_service or RegionResolutionService()
        self.override_service = override_service or OverrideResolutionService()
        self.structure_service = structure_service or StructureInteractionService()

    def build(self, request: AppliedSectionBuildRequest) -> AppliedSection:
        """Build a minimal applied section using source-layer references."""

        alignment_result = self.alignment_service.evaluate_station(
            request.alignment,
            request.station,
        )
        profile_result = self.profile_service.evaluate_station(
            request.profile,
            request.station,
        )
        region_result = self.region_service.resolve_station(
            request.region_model,
            request.station,
        )
        override_result = self.override_service.resolve_station(
            request.override_model,
            request.station,
            region_id=region_result.active_region_id,
        )
        structure_result = self.structure_service.resolve_station(
            request.structure_model,
            request.station,
        ) if request.structure_model is not None else None

        template = self._find_template(
            request.assembly,
            region_result.active_template_ref,
        )

        component_rows = self._build_component_rows(
            template,
            region_id=region_result.active_region_id,
            override_ids=override_result.active_override_ids,
            structure_ids=(
                structure_result.active_structure_ids
                if structure_result is not None
                else []
            ),
        )

        return AppliedSection(
            schema_version=1,
            project_id=request.project_id,
            applied_section_id=request.applied_section_id,
            corridor_id=request.corridor_id,
            alignment_id=request.alignment.alignment_id,
            profile_id=request.profile.profile_id,
            station=request.station,
            frame=self._build_frame(
                station=request.station,
                alignment_result=alignment_result,
                profile_result=profile_result,
            ),
            template_id=region_result.active_template_ref,
            region_id=region_result.active_region_id,
            component_rows=component_rows,
            label=f"STA {request.station:g}",
            source_refs=[
                ref
                for ref in [
                    request.alignment.alignment_id,
                    request.profile.profile_id,
                    request.region_model.region_model_id,
                    request.override_model.override_model_id,
                    request.structure_model.structure_model_id
                    if request.structure_model is not None
                    else "",
                ]
                if ref
            ],
            diagnostic_rows=[],
        )

    @staticmethod
    def _build_frame(
        *,
        station: float,
        alignment_result,
        profile_result,
    ) -> AppliedSectionFrame:
        notes = "; ".join(
            text
            for text in [
                str(getattr(alignment_result, "notes", "") or "").strip(),
                str(getattr(profile_result, "notes", "") or "").strip(),
            ]
            if text
        )
        return AppliedSectionFrame(
            station=float(station),
            x=float(getattr(alignment_result, "x", 0.0) or 0.0),
            y=float(getattr(alignment_result, "y", 0.0) or 0.0),
            z=float(getattr(profile_result, "elevation", 0.0) or 0.0),
            tangent_direction_deg=float(getattr(alignment_result, "tangent_direction_deg", 0.0) or 0.0),
            profile_grade=float(getattr(profile_result, "grade", 0.0) or 0.0),
            alignment_status=str(getattr(alignment_result, "status", "") or ""),
            profile_status=str(getattr(profile_result, "status", "") or ""),
            active_alignment_element_id=str(getattr(alignment_result, "active_element_id", "") or ""),
            active_profile_segment_start_id=str(getattr(profile_result, "active_segment_start_id", "") or ""),
            active_profile_segment_end_id=str(getattr(profile_result, "active_segment_end_id", "") or ""),
            active_vertical_curve_id=str(getattr(profile_result, "active_vertical_curve_id", "") or ""),
            notes=notes,
        )

    @staticmethod
    def _find_template(
        assembly: AssemblyModel,
        template_id: str,
    ) -> SectionTemplate | None:
        for template in assembly.template_rows:
            if template.template_id == template_id:
                return template
        return None

    @staticmethod
    def _build_component_rows(
        template: SectionTemplate | None,
        *,
        region_id: str,
        override_ids: list[str],
        structure_ids: list[str],
    ) -> list[AppliedSectionComponentRow]:
        if template is None:
            return []

        return [
            AppliedSectionComponentRow(
                component_id=component.component_id,
                kind=component.kind,
                source_template_id=template.template_id,
                region_id=region_id,
                override_ids=list(override_ids),
                structure_ids=list(structure_ids),
            )
            for component in template.component_rows
            if component.enabled
        ]
