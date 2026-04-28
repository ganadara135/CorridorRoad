"""Applied section builder service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
)
from ...models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from ...common.diagnostics import DiagnosticMessage
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


@dataclass(frozen=True)
class AppliedSectionSetBuildRequest:
    """Input bundle used to build station-ordered applied sections."""

    project_id: str
    corridor_id: str
    alignment: AlignmentModel
    profile: ProfileModel
    assembly: AssemblyModel
    region_model: RegionModel
    override_model: OverrideModel
    stations: list[float]
    applied_section_set_id: str
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
        region_context = self.region_service.resolve_handoff(
            request.region_model,
            request.station,
        )
        override_result = self.override_service.resolve_station(
            request.override_model,
            request.station,
            region_id=region_context.region_id,
        )
        structure_result = self.structure_service.resolve_station(
            request.structure_model,
            request.station,
        ) if request.structure_model is not None else None

        template_id = self._resolve_template_id(
            request.assembly,
            assembly_ref=region_context.assembly_ref,
            template_ref=region_context.template_ref,
        )
        template = self._find_template(
            request.assembly,
            template_id,
        )
        diagnostics = self._build_diagnostics(
            request.assembly,
            assembly_ref=region_context.assembly_ref,
            template_id=template_id,
            template=template,
        )

        component_rows = self._build_component_rows(
            template,
            region_id=region_context.region_id,
            override_ids=override_result.active_override_ids,
            structure_ids=_unique_refs(
                list(region_context.structure_refs or [])
                + (
                    structure_result.active_structure_ids
                    if structure_result is not None
                    else []
                )
            ),
        )
        left_width, right_width = self._surface_widths(template)
        subgrade_depth = self._subgrade_depth(template)

        return AppliedSection(
            schema_version=1,
            project_id=request.project_id,
            applied_section_id=request.applied_section_id,
            corridor_id=request.corridor_id,
            alignment_id=request.alignment.alignment_id,
            profile_id=request.profile.profile_id,
            assembly_id=request.assembly.assembly_id,
            station=request.station,
            frame=self._build_frame(
                station=request.station,
                alignment_result=alignment_result,
                profile_result=profile_result,
            ),
            template_id=template_id,
            region_id=region_context.region_id,
            component_rows=component_rows,
            surface_left_width=left_width,
            surface_right_width=right_width,
            subgrade_depth=subgrade_depth,
            label=f"STA {request.station:g}",
            source_refs=[
                ref
                for ref in [
                    request.alignment.alignment_id,
                    request.profile.profile_id,
                    request.assembly.assembly_id,
                    request.region_model.region_model_id,
                    request.override_model.override_model_id,
                    request.structure_model.structure_model_id
                    if request.structure_model is not None
                    else "",
                ]
                if ref
            ],
            diagnostic_rows=diagnostics,
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
    def _resolve_template_id(
        assembly: AssemblyModel,
        *,
        assembly_ref: str,
        template_ref: str,
    ) -> str:
        """Resolve the template id from Region handoff context and Assembly source."""

        requested_assembly = str(assembly_ref or "").strip()
        assembly_id = str(getattr(assembly, "assembly_id", "") or "").strip()
        if requested_assembly and requested_assembly != assembly_id:
            return ""
        requested_template = str(template_ref or "").strip()
        if requested_template:
            return requested_template
        return str(getattr(assembly, "active_template_id", "") or "").strip()

    @staticmethod
    def _build_diagnostics(
        assembly: AssemblyModel,
        *,
        assembly_ref: str,
        template_id: str,
        template: SectionTemplate | None,
    ) -> list[DiagnosticMessage]:
        diagnostics: list[DiagnosticMessage] = []
        requested_assembly = str(assembly_ref or "").strip()
        assembly_id = str(getattr(assembly, "assembly_id", "") or "").strip()
        if requested_assembly and requested_assembly != assembly_id:
            diagnostics.append(
                DiagnosticMessage(
                    severity="warning",
                    kind="assembly_ref_mismatch",
                    message=f"Region references {requested_assembly}, but build request provided {assembly_id}.",
                )
            )
        if not str(template_id or "").strip():
            diagnostics.append(
                DiagnosticMessage(
                    severity="warning",
                    kind="missing_template_ref",
                    message="No template id could be resolved from Region or Assembly active_template_id.",
                )
            )
        elif template is None:
            diagnostics.append(
                DiagnosticMessage(
                    severity="warning",
                    kind="missing_template",
                    message=f"Resolved template {template_id} was not found in Assembly {assembly_id}.",
                )
            )
        return diagnostics

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

    @staticmethod
    def _surface_widths(template: SectionTemplate | None) -> tuple[float, float]:
        """Resolve first-slice FG surface widths from enabled Assembly components."""

        if template is None:
            return 0.0, 0.0
        surface_kinds = {
            "lane",
            "shoulder",
            "median",
            "curb",
            "gutter",
            "sidewalk",
            "bike_lane",
            "green_strip",
        }
        left_width = 0.0
        right_width = 0.0
        for component in list(template.component_rows or []):
            if not bool(getattr(component, "enabled", True)):
                continue
            if str(getattr(component, "kind", "") or "") not in surface_kinds:
                continue
            width = max(float(getattr(component, "width", 0.0) or 0.0), 0.0)
            side = str(getattr(component, "side", "") or "center")
            if side == "left":
                left_width += width
            elif side == "right":
                right_width += width
            elif side == "both":
                left_width += width
                right_width += width
            else:
                left_width += width * 0.5
                right_width += width * 0.5
        return left_width, right_width

    @staticmethod
    def _subgrade_depth(template: SectionTemplate | None) -> float:
        """Resolve first-slice subgrade depth from enabled Assembly component thickness."""

        if template is None:
            return 0.0
        thickness_kinds = {
            "lane",
            "shoulder",
            "median",
            "curb",
            "gutter",
            "sidewalk",
            "bike_lane",
            "green_strip",
            "pavement_layer",
            "subbase",
        }
        depths = []
        for component in list(template.component_rows or []):
            if not bool(getattr(component, "enabled", True)):
                continue
            if str(getattr(component, "kind", "") or "") not in thickness_kinds:
                continue
            thickness = max(float(getattr(component, "thickness", 0.0) or 0.0), 0.0)
            if thickness > 0.0:
                depths.append(thickness)
        return max(depths) if depths else 0.0


class AppliedSectionSetService:
    """Build an ordered AppliedSectionSet from station rows and source models."""

    def __init__(self, *, section_service: AppliedSectionService | None = None) -> None:
        self.section_service = section_service or AppliedSectionService()

    def build(self, request: AppliedSectionSetBuildRequest) -> AppliedSectionSet:
        """Build one applied section result per unique station."""

        stations = _unique_stations(request.stations)
        sections: list[AppliedSection] = []
        station_rows: list[AppliedSectionStationRow] = []
        for index, station in enumerate(stations, start=1):
            section_id = f"{request.applied_section_set_id}:section:{index}"
            section = self.section_service.build(
                AppliedSectionBuildRequest(
                    project_id=request.project_id,
                    corridor_id=request.corridor_id,
                    alignment=request.alignment,
                    profile=request.profile,
                    assembly=request.assembly,
                    region_model=request.region_model,
                    override_model=request.override_model,
                    station=station,
                    applied_section_id=section_id,
                    structure_model=request.structure_model,
                )
            )
            sections.append(section)
            station_rows.append(
                AppliedSectionStationRow(
                    station_row_id=f"{request.applied_section_set_id}:station:{index}",
                    station=station,
                    applied_section_id=section_id,
                    kind="regular_sample",
                )
            )
        return AppliedSectionSet(
            schema_version=1,
            project_id=request.project_id,
            applied_section_set_id=request.applied_section_set_id,
            corridor_id=request.corridor_id,
            alignment_id=request.alignment.alignment_id,
            station_rows=station_rows,
            sections=sections,
            source_refs=[
                ref
                for ref in [
                    request.alignment.alignment_id,
                    request.profile.profile_id,
                    request.assembly.assembly_id,
                    request.region_model.region_model_id,
                    request.override_model.override_model_id,
                ]
                if ref
            ],
        )


def _unique_refs(values: list[str]) -> list[str]:
    output: list[str] = []
    seen = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _unique_stations(values: list[float]) -> list[float]:
    output: list[float] = []
    seen = set()
    for value in sorted(float(station) for station in list(values or [])):
        key = round(value, 9)
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output
