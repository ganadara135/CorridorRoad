"""Applied section builder service for CorridorRoad v1."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from ...models.result.applied_section import (
    AppliedSection,
    AppliedSectionFrame,
    AppliedSectionPoint,
    AppliedSectionSubassemblyLink,
    AppliedSectionSubassemblyPoint,
    AppliedSectionSubassemblyRow,
    AppliedSectionSubassemblyShape,
)
from ...models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from ...models.result.tin_surface import TINSurface
from ...models.result.centerline3d import Centerline3DResult
from ...common.diagnostics import DiagnosticMessage
from ...models.source.alignment_model import AlignmentModel
from ...models.source.assembly_model import (
    AssemblySourceIdentity,
    AssemblySubassemblyModel,
    SubassemblySectionTemplate,
    normalize_bench_rows,
    subassembly_bench_validation_messages,
)
from ...models.source.drainage_model import DrainageModel
from ...models.source.intersection_model import IntersectionModel
from ...models.source.override_model import OverrideModel
from ...models.source.profile_model import ProfileModel
from ...models.source.region_model import RegionModel
from ...models.source.structure_model import StructureModel
from ...models.source.superelevation_model import SuperelevationModel
from ...services.evaluation.alignment_evaluation_service import (
    AlignmentEvaluationService,
)
from ...services.evaluation.centerline3d_frame_service import (
    Centerline3DFrame,
    Centerline3DFrameService,
)
from ...services.evaluation.override_resolution_service import (
    OverrideResolutionService,
)
from ...services.evaluation.intersection_evaluation_service import (
    IntersectionEvaluationResult,
    IntersectionEvaluationService,
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
from ...services.evaluation.superelevation_service import (
    SuperelevationService,
    SuperelevationStationResult,
)
from ...services.evaluation.station_context_resolver import StationContextResolver
from ...services.evaluation.tin_sampling_service import TinSamplingService


@dataclass(frozen=True)
class AppliedSectionBuildRequest:
    """Input bundle used to build one minimal applied section."""

    project_id: str
    corridor_id: str
    alignment: AlignmentModel
    profile: ProfileModel
    assembly: AssemblySourceIdentity
    region_model: RegionModel
    override_model: OverrideModel
    station: float
    applied_section_id: str
    assembly_models: list[AssemblySourceIdentity] = field(default_factory=list)
    assembly_subassembly_models: list[AssemblySubassemblyModel] = field(default_factory=list)
    structure_model: StructureModel | None = None
    drainage_model: DrainageModel | None = None
    superelevation_model: SuperelevationModel | None = None
    intersection_model: IntersectionModel | None = None
    existing_ground_surface: TINSurface | None = None
    centerline3d_result: Centerline3DResult | None = None


@dataclass(frozen=True)
class AppliedSectionSetBuildRequest:
    """Input bundle used to build station-ordered applied sections."""

    project_id: str
    corridor_id: str
    alignment: AlignmentModel
    profile: ProfileModel
    assembly: AssemblySourceIdentity
    region_model: RegionModel
    override_model: OverrideModel
    stations: list[float]
    applied_section_set_id: str
    station_kinds: dict[float, str] = field(default_factory=dict)
    assembly_models: list[AssemblySourceIdentity] = field(default_factory=list)
    assembly_subassembly_models: list[AssemblySubassemblyModel] = field(default_factory=list)
    structure_model: StructureModel | None = None
    drainage_model: DrainageModel | None = None
    superelevation_model: SuperelevationModel | None = None
    intersection_model: IntersectionModel | None = None
    existing_ground_surface: TINSurface | None = None
    centerline3d_result: Centerline3DResult | None = None


@dataclass(frozen=True)
class _BenchEvaluation:
    source_row: object
    side_label: str
    edge_offset: float
    edge_z: float
    direction: float
    segments: list[dict[str, object]]
    diagnostics: list[DiagnosticMessage] = field(default_factory=list)

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
        station_context_resolver: StationContextResolver | None = None,
        tin_sampling_service: TinSamplingService | None = None,
        centerline_frame_service: Centerline3DFrameService | None = None,
        superelevation_service: SuperelevationService | None = None,
        intersection_service: IntersectionEvaluationService | None = None,
    ) -> None:
        self.alignment_service = alignment_service or AlignmentEvaluationService()
        self.profile_service = profile_service or ProfileEvaluationService()
        self.region_service = region_service or RegionResolutionService()
        self.override_service = override_service or OverrideResolutionService()
        self.structure_service = structure_service or StructureInteractionService()
        self.station_context_resolver = station_context_resolver or StationContextResolver(
            region_service=self.region_service,
            structure_service=self.structure_service,
        )
        self.tin_sampling_service = tin_sampling_service or TinSamplingService()
        self.centerline_frame_service = centerline_frame_service or Centerline3DFrameService()
        self.superelevation_service = superelevation_service or SuperelevationService()
        self.intersection_service = intersection_service or IntersectionEvaluationService()

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
        station_context = self.station_context_resolver.resolve(
            region_model=request.region_model,
            station=request.station,
            structure_model=request.structure_model,
            drainage_model=request.drainage_model,
        )
        region_context = station_context.region_context
        assembly = self._resolve_assembly_model(
            request.assembly,
            request.assembly_models,
            assembly_ref=region_context.assembly_ref,
        )
        override_result = self.override_service.resolve_station(
            request.override_model,
            request.station,
            region_id=region_context.region_id,
        )
        structure_result = station_context.structure_result
        active_drainage_refs = list(station_context.active_drainage_refs or [])
        active_drainage_refs_by_side = dict(station_context.active_drainage_refs_by_side or {})

        template_id = self._resolve_template_id(
            assembly,
            assembly_ref=region_context.assembly_ref,
            template_ref=region_context.template_ref,
        )
        template = None
        subassembly_model = self._resolve_subassembly_model(
            request.assembly_subassembly_models,
            assembly_ref=region_context.assembly_ref or assembly.assembly_id,
        )
        subassembly_template_id = self._resolve_subassembly_template_id(
            subassembly_model,
            assembly_ref=region_context.assembly_ref or assembly.assembly_id,
            template_ref=region_context.template_ref or template_id,
        )
        subassembly_template = self._find_subassembly_template(subassembly_model, subassembly_template_id)
        diagnostics = self._build_diagnostics(
            assembly,
            assembly_ref=region_context.assembly_ref,
            template_id=template_id,
            template=template,
            subassembly_template=subassembly_template,
        )

        centerline_frame = self.centerline_frame_service.resolve_station(request.centerline3d_result, request.station)
        frame = self._build_frame(
            station=request.station,
            alignment_result=alignment_result,
            profile_result=profile_result,
            centerline_frame=centerline_frame,
        )
        active_structure_ids = list(getattr(structure_result, "active_structure_ids", []) or []) if structure_result is not None else []
        active_rule_ids = list(getattr(structure_result, "active_rule_ids", []) or []) if structure_result is not None else []
        active_influence_zone_ids = list(getattr(structure_result, "active_influence_zone_ids", []) or []) if structure_result is not None else []
        structure_diagnostics = _structure_context_diagnostics(
            station=request.station,
            active_structure_ids=active_structure_ids,
            active_rule_ids=active_rule_ids,
            active_influence_zone_ids=active_influence_zone_ids,
        )
        left_width, right_width = self._surface_widths(template, subassembly_template=subassembly_template)
        subgrade_depth = self._subgrade_depth(template, subassembly_template=subassembly_template)
        daylight_left_width, daylight_right_width, daylight_left_slope, daylight_right_slope = self._daylight_policy(
            template,
            subassembly_template=subassembly_template,
        )
        superelevation_result = self._evaluate_superelevation(
            request.superelevation_model,
            request.station,
            template=template,
            subassembly_template=subassembly_template,
        )
        intersection_result = self._evaluate_intersection(
            request.intersection_model,
            request.station,
            alignment_ref=request.alignment.alignment_id,
        )
        effective_template = template
        effective_subassembly_template = _subassembly_template_with_superelevation(subassembly_template, superelevation_result)
        diagnostics.extend(list(getattr(superelevation_result, "diagnostic_rows", []) or []))
        diagnostics.extend(_intersection_context_diagnostics(intersection_result))
        fg_points = _surface_section_offsets(
            effective_template,
            frame=frame,
            subassembly_template=effective_subassembly_template,
        )
        bench_evaluations = _bench_evaluations(
            effective_template,
            subassembly_template=effective_subassembly_template,
            frame=frame,
            fg_points=fg_points,
            surface_left_width=left_width,
            surface_right_width=right_width,
            existing_ground_surface=request.existing_ground_surface,
            sampling_service=self.tin_sampling_service,
        )
        diagnostics.extend(_bench_evaluation_diagnostics(bench_evaluations))
        subassembly_rows = self._build_subassembly_rows(
            effective_subassembly_template,
            region_id=region_context.region_id,
            override_ids=override_result.active_override_ids,
            structure_ids=_unique_refs(
                structure_result.active_structure_ids
                if structure_result is not None
                else []
            ),
            drainage_refs=active_drainage_refs,
            drainage_refs_by_side=active_drainage_refs_by_side,
        )
        point_rows = self._build_point_rows(
            effective_template,
            frame=frame,
            fg_points=fg_points,
            surface_left_width=left_width,
            surface_right_width=right_width,
            subgrade_depth=subgrade_depth,
            drainage_refs=active_drainage_refs,
            drainage_refs_by_side=active_drainage_refs_by_side,
            subassembly_template=effective_subassembly_template,
            bench_evaluations=bench_evaluations,
        )
        point_rows = _points_with_compatibility_subassembly_refs(point_rows, subassembly_rows)
        subassembly_point_rows = _subassembly_point_rows(point_rows, subassembly_rows)
        subassembly_point_rows.extend(
            _surface_subassembly_point_rows(
                fg_points,
                subassembly_rows,
                subgrade_depth=subgrade_depth,
            )
        )
        subassembly_point_rows.extend(
            _bench_subassembly_point_rows(
                bench_evaluations,
                subassembly_rows,
                frame=frame,
            )
        )
        subassembly_link_rows = _subassembly_link_rows(subassembly_point_rows, subassembly_rows)
        subassembly_shape_rows = _subassembly_shape_rows(subassembly_point_rows, subassembly_rows)

        return AppliedSection(
            schema_version=1,
            project_id=request.project_id,
            applied_section_id=request.applied_section_id,
            corridor_id=request.corridor_id,
            alignment_id=request.alignment.alignment_id,
            profile_id=request.profile.profile_id,
            assembly_id=assembly.assembly_id,
            station=request.station,
            frame=frame,
            template_id=template_id,
            region_id=region_context.region_id,
            subassembly_rows=subassembly_rows,
            surface_left_width=left_width,
            surface_right_width=right_width,
            subgrade_depth=subgrade_depth,
            daylight_left_width=daylight_left_width,
            daylight_right_width=daylight_right_width,
            daylight_left_slope=daylight_left_slope,
            daylight_right_slope=daylight_right_slope,
            active_superelevation_id=str(getattr(request.superelevation_model, "superelevation_id", "") or ""),
            superelevation_left_crossfall=float(getattr(superelevation_result, "left_crossfall", 0.0) or 0.0),
            superelevation_right_crossfall=float(getattr(superelevation_result, "right_crossfall", 0.0) or 0.0),
            active_superelevation_transition_id=str(getattr(superelevation_result, "active_transition_id", "") or ""),
            superelevation_source_rows=_superelevation_source_rows(superelevation_result),
            active_intersection_id=str(getattr(intersection_result, "active_intersection_id", "") or ""),
            active_intersection_control_area_id=str(getattr(intersection_result, "active_control_area_id", "") or ""),
            active_intersection_leg_id=str(getattr(intersection_result, "active_leg_id", "") or ""),
            active_intersection_leg_role=str(getattr(intersection_result, "leg_role", "") or ""),
            active_intersection_control_region_refs=list(getattr(intersection_result, "control_region_refs", ()) or ()),
            active_intersection_grading_policy_ref=str(getattr(intersection_result, "grading_policy_ref", "") or ""),
            intersection_diagnostic_rows=list(getattr(intersection_result, "diagnostic_rows", ()) or ()),
            point_rows=point_rows,
            subassembly_point_rows=subassembly_point_rows,
            subassembly_link_rows=subassembly_link_rows,
            subassembly_shape_rows=subassembly_shape_rows,
            active_structure_ids=active_structure_ids,
            active_structure_rule_ids=active_rule_ids,
            active_structure_influence_zone_ids=active_influence_zone_ids,
            structure_diagnostic_rows=structure_diagnostics,
            label=f"STA {request.station:g}",
            source_refs=[
                ref
                for ref in [
                    request.alignment.alignment_id,
                    request.profile.profile_id,
                    assembly.assembly_id,
                    str(getattr(subassembly_model, "assembly_id", "") or "") if subassembly_model is not None else "",
                    request.region_model.region_model_id,
                    request.override_model.override_model_id,
                    request.structure_model.structure_model_id
                    if request.structure_model is not None
                    else "",
                    request.drainage_model.drainage_model_id
                    if request.drainage_model is not None
                    else "",
                    request.superelevation_model.superelevation_id
                    if request.superelevation_model is not None
                    else "",
                    request.intersection_model.intersection_model_id
                    if request.intersection_model is not None
                    else "",
                    str(getattr(intersection_result, "active_intersection_id", "") or ""),
                    *active_drainage_refs,
                    *list(station_context.active_flow_route_refs or []),
                ]
                if ref
            ],
            diagnostic_rows=diagnostics,
        )

    @staticmethod
    def _resolve_assembly_model(
        fallback: AssemblySourceIdentity,
        assembly_models: list[AssemblySourceIdentity],
        *,
        assembly_ref: str,
    ) -> AssemblySourceIdentity:
        requested = str(assembly_ref or "").strip()
        candidates = [model for model in list(assembly_models or []) if model is not None]
        if fallback is not None:
            fallback_id = str(getattr(fallback, "assembly_id", "") or "").strip()
            if fallback_id and all(str(getattr(model, "assembly_id", "") or "").strip() != fallback_id for model in candidates):
                candidates.insert(0, fallback)
        if requested:
            for model in candidates:
                if str(getattr(model, "assembly_id", "") or "").strip() == requested:
                    return model
        return fallback

    @staticmethod
    def _resolve_subassembly_model(
        assembly_subassembly_models: list[AssemblySubassemblyModel],
        *,
        assembly_ref: str,
    ) -> AssemblySubassemblyModel | None:
        requested = str(assembly_ref or "").strip()
        candidates = [model for model in list(assembly_subassembly_models or []) if model is not None]
        if requested:
            for model in candidates:
                if str(getattr(model, "assembly_id", "") or "").strip() == requested:
                    return model
        return candidates[0] if candidates else None

    @staticmethod
    def _build_frame(
        *,
        station: float,
        alignment_result,
        profile_result,
        centerline_frame: Centerline3DFrame | None = None,
    ) -> AppliedSectionFrame:
        if centerline_frame is not None and str(getattr(centerline_frame, "status", "") or "") in {"ok", "warning"}:
            centerline_notes = "; ".join(
                text
                for text in [
                    "source=centerline3d_result",
                    *list(getattr(centerline_frame, "diagnostic_rows", []) or []),
                ]
                if text
            )
            return AppliedSectionFrame(
                station=float(station),
                x=float(getattr(centerline_frame, "x", 0.0) or 0.0),
                y=float(getattr(centerline_frame, "y", 0.0) or 0.0),
                z=float(getattr(centerline_frame, "z", 0.0) or 0.0),
                tangent_direction_deg=float(getattr(centerline_frame, "tangent_direction_deg", 0.0) or 0.0),
                profile_grade=float(getattr(centerline_frame, "grade", 0.0) or 0.0),
                alignment_status=str(getattr(alignment_result, "status", "") or ""),
                profile_status=str(getattr(profile_result, "status", "") or ""),
                active_alignment_element_id=str(getattr(alignment_result, "active_element_id", "") or ""),
                active_profile_segment_start_id=str(getattr(profile_result, "active_segment_start_id", "") or ""),
                active_profile_segment_end_id=str(getattr(profile_result, "active_segment_end_id", "") or ""),
                active_vertical_curve_id=str(getattr(profile_result, "active_vertical_curve_id", "") or ""),
                notes=centerline_notes,
            )
        notes = "; ".join(
            text
            for text in [
                str(getattr(alignment_result, "notes", "") or "").strip(),
                str(getattr(profile_result, "notes", "") or "").strip(),
                *(list(getattr(centerline_frame, "diagnostic_rows", []) or []) if centerline_frame is not None else []),
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

    def _evaluate_superelevation(
        self,
        superelevation_model: SuperelevationModel | None,
        station: float,
        *,
        template: object | None,
        subassembly_template: SubassemblySectionTemplate | None = None,
    ) -> SuperelevationStationResult | None:
        if superelevation_model is None:
            return None
        left_default, right_default = _default_crossfall_percent_by_side(
            template,
            subassembly_template=subassembly_template,
        )
        return self.superelevation_service.evaluate_station(
            superelevation_model,
            station,
            default_left_crossfall=left_default,
            default_right_crossfall=right_default,
        )

    def _evaluate_intersection(
        self,
        intersection_model: IntersectionModel | None,
        station: float,
        *,
        alignment_ref: str,
    ) -> IntersectionEvaluationResult | None:
        if intersection_model is None:
            return None
        return self.intersection_service.resolve_station(
            intersection_model,
            station,
            alignment_ref=alignment_ref,
        )

    @staticmethod
    def _find_subassembly_template(
        assembly: AssemblySubassemblyModel | None,
        template_id: str,
    ) -> SubassemblySectionTemplate | None:
        if assembly is None:
            return None
        for template in list(getattr(assembly, "template_rows", []) or []):
            if str(getattr(template, "template_id", "") or "") == str(template_id or ""):
                return template
        return None

    @staticmethod
    def _resolve_template_id(
        assembly: AssemblySourceIdentity,
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
    def _resolve_subassembly_template_id(
        assembly: AssemblySubassemblyModel | None,
        *,
        assembly_ref: str,
        template_ref: str,
    ) -> str:
        if assembly is None:
            return ""
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
        assembly: AssemblySourceIdentity,
        *,
        assembly_ref: str,
        template_id: str,
        template: object | None,
        subassembly_template: SubassemblySectionTemplate | None = None,
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
        elif template is None and subassembly_template is None:
            diagnostics.append(
                DiagnosticMessage(
                    severity="warning",
                    kind="missing_template",
                    message=f"Resolved template {template_id} was not found in Assembly/Subassembly source {assembly_id}.",
                )
            )
        if template is not None or subassembly_template is not None:
            diagnostics.extend(_ditch_shape_diagnostics(template, subassembly_template=subassembly_template))
            diagnostics.extend(_bench_diagnostics(template, subassembly_template=subassembly_template))
        return diagnostics

    @staticmethod
    def _build_subassembly_rows(
        template: SubassemblySectionTemplate | None,
        *,
        region_id: str,
        override_ids: list[str],
        structure_ids: list[str],
        drainage_refs: list[str],
        drainage_refs_by_side: dict[str, list[str]] | None = None,
    ) -> list[AppliedSectionSubassemblyRow]:
        if template is None:
            return []
        rows: list[AppliedSectionSubassemblyRow] = []
        for subassembly in list(getattr(template, "subassembly_rows", []) or []):
            if not bool(getattr(subassembly, "enabled", True)):
                continue
            rows.append(
                AppliedSectionSubassemblyRow(
                    subassembly_id=str(getattr(subassembly, "subassembly_id", "") or ""),
                    kind=str(getattr(subassembly, "kind", "") or ""),
                    source_template_id=str(getattr(template, "template_id", "") or ""),
                    region_id=str(region_id or ""),
                    side=str(getattr(subassembly, "side", "") or "center"),
                    width=max(float(getattr(subassembly, "width", 0.0) or 0.0), 0.0),
                    slope=float(getattr(subassembly, "slope", 0.0) or 0.0),
                    thickness=max(float(getattr(subassembly, "thickness", 0.0) or 0.0), 0.0),
                    material=str(getattr(subassembly, "material", "") or ""),
                    override_ids=list(override_ids or []),
                    structure_ids=list(structure_ids or []),
                    drainage_refs=_section_row_drainage_refs(subassembly, drainage_refs, drainage_refs_by_side),
                    parameters=dict(getattr(subassembly, "parameters", {}) or {}),
                    point_code_rules=tuple(getattr(subassembly, "point_code_rules", ()) or ()),
                    link_code_rules=tuple(getattr(subassembly, "link_code_rules", ()) or ()),
                    shape_code_rules=tuple(getattr(subassembly, "shape_code_rules", ()) or ()),
                )
            )
        return rows

    @staticmethod
    def _surface_widths(
        template: object | None,
        *,
        subassembly_template: SubassemblySectionTemplate | None = None,
    ) -> tuple[float, float]:
        """Resolve first-slice FG surface widths from enabled section rows."""

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
        rows = _active_section_source_rows(
            template,
            subassembly_template=subassembly_template,
        )
        if not rows:
            return 0.0, 0.0
        left_width = 0.0
        right_width = 0.0
        for source_row in rows:
            if str(getattr(source_row, "kind", "") or "") not in surface_kinds:
                continue
            width = max(float(getattr(source_row, "width", 0.0) or 0.0), 0.0)
            side = str(getattr(source_row, "side", "") or "center")
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
    def _subgrade_depth(
        template: object | None,
        *,
        subassembly_template: SubassemblySectionTemplate | None = None,
    ) -> float:
        """Resolve first-slice subgrade depth from enabled section row thickness."""

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
        rows = _active_section_source_rows(
            template,
            subassembly_template=subassembly_template,
        )
        depths = []
        for source_row in rows:
            if str(getattr(source_row, "kind", "") or "") not in thickness_kinds:
                continue
            thickness = max(float(getattr(source_row, "thickness", 0.0) or 0.0), 0.0)
            if thickness > 0.0:
                depths.append(thickness)
        return max(depths) if depths else 0.0

    @staticmethod
    def _daylight_policy(
        template: object | None,
        *,
        subassembly_template: SubassemblySectionTemplate | None = None,
    ) -> tuple[float, float, float, float]:
        """Resolve first-slice daylight widths and slopes from side-slope Subassembly rows."""

        rows = _active_section_source_rows(
            template,
            subassembly_template=subassembly_template,
        )
        if not rows:
            return 0.0, 0.0, 0.0, 0.0
        left_width = 0.0
        right_width = 0.0
        left_slopes: list[float] = []
        right_slopes: list[float] = []
        for source_row in rows:
            if str(getattr(source_row, "kind", "") or "") != "side_slope":
                continue
            width = max(float(getattr(source_row, "width", 0.0) or 0.0), 0.0)
            slope = float(getattr(source_row, "slope", 0.0) or 0.0)
            side = str(getattr(source_row, "side", "") or "center")
            if side == "left":
                left_width += width
                left_slopes.append(slope)
            elif side == "right":
                right_width += width
                right_slopes.append(slope)
            elif side == "both":
                left_width += width
                right_width += width
                left_slopes.append(slope)
                right_slopes.append(slope)
            else:
                left_width += width * 0.5
                right_width += width * 0.5
                left_slopes.append(slope)
                right_slopes.append(slope)
        return (
            left_width,
            right_width,
            _average(left_slopes),
            _average(right_slopes),
        )

    @staticmethod
    def _build_point_rows(
        template: object | None,
        *,
        frame: AppliedSectionFrame,
        fg_points: list[tuple[float, float, float, float]] | None = None,
        surface_left_width: float,
        surface_right_width: float,
        subgrade_depth: float,
        drainage_refs: list[str] | None = None,
        drainage_refs_by_side: dict[str, list[str]] | None = None,
        subassembly_template: SubassemblySectionTemplate | None = None,
        bench_evaluations: list[_BenchEvaluation] | None = None,
    ) -> list[AppliedSectionPoint]:
        """Resolve first-slice FG, subgrade, and ditch section points from enabled section rows."""

        fg_points = list(
            fg_points
            if fg_points is not None
            else _surface_section_offsets(template, frame=frame, subassembly_template=subassembly_template)
        )
        if not fg_points:
            return []
        output: list[AppliedSectionPoint] = []
        for index, (offset, x, y, z) in enumerate(fg_points):
            output.append(
                AppliedSectionPoint(
                    point_id=f"fg:{index + 1}",
                    x=x,
                    y=y,
                    z=z,
                    point_role="fg_surface",
                    lateral_offset=offset,
                )
            )
        depth = max(float(subgrade_depth or 0.0), 0.0)
        if depth > 0.0:
            for index, (offset, x, y, z) in enumerate(fg_points):
                output.append(
                    AppliedSectionPoint(
                        point_id=f"subgrade:{index + 1}",
                        x=x,
                        y=y,
                        z=z - depth,
                        point_role="subgrade_surface",
                        lateral_offset=offset,
                    )
                )
        output.extend(
            _ditch_section_points(
                template,
                frame=frame,
                surface_left_width=surface_left_width,
                surface_right_width=surface_right_width,
                drainage_refs=list(drainage_refs or []),
                drainage_refs_by_side=drainage_refs_by_side,
                subassembly_template=subassembly_template,
            )
        )
        output.extend(
            _bench_section_points(
                template,
                frame=frame,
                fg_points=fg_points,
                surface_left_width=surface_left_width,
                surface_right_width=surface_right_width,
                subassembly_template=subassembly_template,
                bench_evaluations=bench_evaluations,
            )
        )
        return output


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
                    assembly_models=list(request.assembly_models or []),
                    assembly_subassembly_models=list(request.assembly_subassembly_models or []),
                    region_model=request.region_model,
                    override_model=request.override_model,
                    station=station,
                    applied_section_id=section_id,
                    structure_model=request.structure_model,
                    drainage_model=request.drainage_model,
                    superelevation_model=request.superelevation_model,
                    intersection_model=request.intersection_model,
                    existing_ground_surface=request.existing_ground_surface,
                    centerline3d_result=request.centerline3d_result,
                )
            )
            station_kind = _station_kind_for(request.station_kinds, station)
            sections.append(section)
            station_rows.append(
                AppliedSectionStationRow(
                    station_row_id=f"{request.applied_section_set_id}:station:{index}",
                    station=station,
                    applied_section_id=section_id,
                    kind=station_kind,
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
                    *[
                        str(getattr(assembly, "assembly_id", "") or "")
                        for assembly in _unique_assembly_models([request.assembly] + list(request.assembly_models or []))
                    ],
                    *[
                        str(getattr(assembly, "assembly_id", "") or "")
                        for assembly in list(request.assembly_subassembly_models or [])
                    ],
                    request.region_model.region_model_id,
                    request.override_model.override_model_id,
                    request.structure_model.structure_model_id
                    if request.structure_model is not None
                    else "",
                    request.drainage_model.drainage_model_id
                    if request.drainage_model is not None
                    else "",
                    request.superelevation_model.superelevation_id
                    if request.superelevation_model is not None
                    else "",
                    request.intersection_model.intersection_model_id
                    if request.intersection_model is not None
                    else "",
                    request.centerline3d_result.centerline3d_result_id
                    if request.centerline3d_result is not None
                    else "",
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


def _station_kind_for(station_kinds: dict[float, str], station: float, *, tolerance: float = 1.0e-6) -> str:
    for key, value in dict(station_kinds or {}).items():
        try:
            if abs(float(key) - float(station)) <= tolerance:
                text = str(value or "").strip()
                return text or "regular_sample"
        except Exception:
            continue
    return "regular_sample"


def _subassembly_template_with_superelevation(
    template: SubassemblySectionTemplate | None,
    superelevation_result: SuperelevationStationResult | None,
) -> SubassemblySectionTemplate | None:
    if template is None or superelevation_result is None:
        return template
    rows = []
    for subassembly in list(getattr(template, "subassembly_rows", []) or []):
        rows.append(_subassembly_with_superelevation(subassembly, superelevation_result))
    return replace(template, subassembly_rows=rows)


def _active_section_source_rows(
    template: object | None,
    *,
    subassembly_template: SubassemblySectionTemplate | None = None,
) -> list[object]:
    """Return active Subassembly rows."""

    return [
        row
        for row in list(getattr(subassembly_template, "subassembly_rows", []) or [])
        if bool(getattr(row, "enabled", True))
    ]


def _section_source_sort_index(row: object) -> int:
    """Return the active Subassembly row order."""

    return int(getattr(row, "subassembly_index", 0) or 0)


def _subassembly_with_superelevation(subassembly, superelevation_result: SuperelevationStationResult):
    kind = str(getattr(subassembly, "kind", "") or "").strip().lower()
    if kind not in {"lane", "shoulder"}:
        return subassembly
    side = str(getattr(subassembly, "side", "") or "").strip().lower()
    if side == "left":
        effective_slope = float(getattr(superelevation_result, "left_crossfall", 0.0) or 0.0) / 100.0
        source = str(getattr(superelevation_result, "left_source", "") or "")
    elif side == "right":
        effective_slope = float(getattr(superelevation_result, "right_crossfall", 0.0) or 0.0) / 100.0
        source = str(getattr(superelevation_result, "right_source", "") or "")
    else:
        return subassembly
    if not source:
        return subassembly
    params = dict(getattr(subassembly, "parameters", {}) or {})
    params.update(
        {
            "assembly_default_slope": float(getattr(subassembly, "slope", 0.0) or 0.0),
            "effective_slope_source": "superelevation",
            "superelevation_source": source,
            "superelevation_transition": str(getattr(superelevation_result, "active_transition_id", "") or ""),
            "superelevation_crossfall_percent": effective_slope * 100.0,
        }
    )
    return replace(subassembly, slope=effective_slope, parameters=params)


def _points_with_compatibility_subassembly_refs(
    point_rows: list[AppliedSectionPoint],
    subassembly_rows: list[AppliedSectionSubassemblyRow],
) -> list[AppliedSectionPoint]:
    if not point_rows or not subassembly_rows:
        return point_rows
    subassembly_ids = {
        str(getattr(row, "subassembly_id", "") or "").strip()
        for row in list(subassembly_rows or [])
        if str(getattr(row, "subassembly_id", "") or "").strip()
    }
    if not subassembly_ids:
        return point_rows
    return point_rows


def _subassembly_point_rows(
    point_rows: list[AppliedSectionPoint],
    subassembly_rows: list[AppliedSectionSubassemblyRow],
) -> list[AppliedSectionSubassemblyPoint]:
    if not point_rows or not subassembly_rows:
        return []
    row_by_id = {
        str(getattr(row, "subassembly_id", "") or "").strip(): row
        for row in list(subassembly_rows or [])
        if str(getattr(row, "subassembly_id", "") or "").strip()
    }
    output: list[AppliedSectionSubassemblyPoint] = []
    for point in list(point_rows or []):
        if str(getattr(point, "point_role", "") or "") in {"side_slope_surface", "bench_surface", "daylight_marker"}:
            continue
        subassembly_ref = str(getattr(point, "subassembly_ref", "") or "").strip()
        if not subassembly_ref or subassembly_ref not in row_by_id:
            continue
        output.append(
            AppliedSectionSubassemblyPoint(
                point_id=str(getattr(point, "point_id", "") or ""),
                subassembly_ref=subassembly_ref,
                point_code=_subassembly_point_code(point, row_by_id.get(subassembly_ref)),
                x=float(getattr(point, "x", 0.0) or 0.0),
                y=float(getattr(point, "y", 0.0) or 0.0),
                z=float(getattr(point, "z", 0.0) or 0.0),
                lateral_offset=float(getattr(point, "lateral_offset", 0.0) or 0.0),
                side=str(getattr(point, "side", "") or getattr(row_by_id.get(subassembly_ref), "side", "") or ""),
                target_ref=str(getattr(point, "drainage_ref", "") or ""),
            )
        )
    return output


def _surface_subassembly_point_rows(
    fg_points: list[tuple[float, float, float, float]],
    subassembly_rows: list[AppliedSectionSubassemblyRow],
    *,
    subgrade_depth: float = 0.0,
) -> list[AppliedSectionSubassemblyPoint]:
    """Create Subassembly-owned FG/subgrade endpoint rows without changing legacy point rows."""

    if not fg_points or not subassembly_rows:
        return []
    fg_by_offset = {round(float(offset), 9): (float(x), float(y), float(z)) for offset, x, y, z in fg_points}
    output: list[AppliedSectionSubassemblyPoint] = []
    left_offset = 0.0
    right_offset = 0.0
    for row in sorted(list(subassembly_rows or []), key=lambda item: int(getattr(item, "parameters", {}).get("subassembly_index", 0) or 0)):
        kind = str(getattr(row, "kind", "") or "").strip().lower()
        if kind not in {"lane", "shoulder", "median", "curb", "gutter", "sidewalk", "bike_lane", "green_strip"}:
            continue
        subassembly_ref = str(getattr(row, "subassembly_id", "") or "").strip()
        if not subassembly_ref:
            continue
        width = max(float(getattr(row, "width", 0.0) or 0.0), 0.0)
        if width <= 1.0e-9:
            continue
        side = str(getattr(row, "side", "") or "center").strip().lower()
        intervals: list[tuple[str, float, float]] = []
        if side == "left":
            intervals.append(("left", left_offset, left_offset + width))
            left_offset += width
        elif side == "right":
            intervals.append(("right", -right_offset, -(right_offset + width)))
            right_offset += width
        elif side == "both":
            intervals.append(("left", left_offset, left_offset + width))
            intervals.append(("right", -right_offset, -(right_offset + width)))
            left_offset += width
            right_offset += width
        else:
            half_width = width * 0.5
            intervals.append(("center", -half_width, half_width))
        for side_label, start_offset, end_offset in intervals:
            output.extend(
                _surface_subassembly_endpoint_rows(
                    subassembly_ref,
                    side_label=side_label,
                    start_offset=start_offset,
                    end_offset=end_offset,
                    fg_by_offset=fg_by_offset,
                    subgrade_depth=subgrade_depth,
                )
            )
    return output


def _surface_subassembly_endpoint_rows(
    subassembly_ref: str,
    *,
    side_label: str,
    start_offset: float,
    end_offset: float,
    fg_by_offset: dict[float, tuple[float, float, float]],
    subgrade_depth: float,
) -> list[AppliedSectionSubassemblyPoint]:
    rows: list[AppliedSectionSubassemblyPoint] = []
    endpoints = [
        ("start", float(start_offset)),
        ("end", float(end_offset)),
    ]
    for endpoint_label, offset in endpoints:
        xyz = fg_by_offset.get(round(float(offset), 9))
        if xyz is None:
            continue
        x, y, z = xyz
        point_id = f"{subassembly_ref}:fg:{side_label}:{endpoint_label}"
        rows.append(
            AppliedSectionSubassemblyPoint(
                point_id=point_id,
                subassembly_ref=subassembly_ref,
                point_code="fg_surface",
                x=x,
                y=y,
                z=z,
                lateral_offset=offset,
                side=side_label,
            )
        )
        depth = max(float(subgrade_depth or 0.0), 0.0)
        if depth > 0.0:
            rows.append(
                AppliedSectionSubassemblyPoint(
                    point_id=f"{subassembly_ref}:subgrade:{side_label}:{endpoint_label}",
                    subassembly_ref=subassembly_ref,
                    point_code="subgrade_surface",
                    x=x,
                    y=y,
                    z=z - depth,
                    lateral_offset=offset,
                    side=side_label,
                )
            )
    return rows


def _bench_subassembly_point_rows(
    bench_evaluations: list[_BenchEvaluation],
    subassembly_rows: list[AppliedSectionSubassemblyRow],
    *,
    frame: AppliedSectionFrame,
) -> list[AppliedSectionSubassemblyPoint]:
    """Create Subassembly-owned side-slope/bench points from evaluated bench geometry."""

    if not bench_evaluations or not subassembly_rows:
        return []
    source_by_side = _side_slope_subassembly_rows_by_side(subassembly_rows)
    angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(angle_rad)
    normal_y = math.cos(angle_rad)
    base_x = float(getattr(frame, "x", 0.0) or 0.0)
    base_y = float(getattr(frame, "y", 0.0) or 0.0)
    output: list[AppliedSectionSubassemblyPoint] = []
    used_by_side: dict[str, int] = {}
    for evaluation in list(bench_evaluations or []):
        side_label = str(getattr(evaluation, "side_label", "") or "center").strip().lower()
        candidates = source_by_side.get(side_label, [])
        if not candidates:
            candidates = source_by_side.get("both", []) or source_by_side.get("center", [])
        if not candidates:
            continue
        index = used_by_side.get(side_label, 0)
        source_row = candidates[min(index, len(candidates) - 1)]
        used_by_side[side_label] = index + 1
        output.extend(
            _oriented_bench_subassembly_points(
                source_row,
                list(getattr(evaluation, "segments", []) or []),
                side_label=side_label,
                edge_offset=float(getattr(evaluation, "edge_offset", 0.0) or 0.0),
                edge_z=float(getattr(evaluation, "edge_z", 0.0) or 0.0),
                direction=float(getattr(evaluation, "direction", 1.0) or 1.0),
                base_x=base_x,
                base_y=base_y,
                normal_x=normal_x,
                normal_y=normal_y,
            )
        )
    return output


def _side_slope_subassembly_rows_by_side(
    subassembly_rows: list[AppliedSectionSubassemblyRow],
) -> dict[str, list[AppliedSectionSubassemblyRow]]:
    rows_by_side: dict[str, list[AppliedSectionSubassemblyRow]] = {}
    for row in list(subassembly_rows or []):
        if str(getattr(row, "kind", "") or "").strip().lower() != "side_slope":
            continue
        subassembly_ref = str(getattr(row, "subassembly_id", "") or "").strip()
        if not subassembly_ref:
            continue
        side = str(getattr(row, "side", "") or "center").strip().lower()
        rows_by_side.setdefault(side or "center", []).append(row)
    return rows_by_side


def _oriented_bench_subassembly_points(
    source_row: AppliedSectionSubassemblyRow,
    segments: list[dict[str, object]],
    *,
    side_label: str,
    edge_offset: float,
    edge_z: float,
    direction: float,
    base_x: float,
    base_y: float,
    normal_x: float,
    normal_y: float,
) -> list[AppliedSectionSubassemblyPoint]:
    output: list[AppliedSectionSubassemblyPoint] = []
    subassembly_ref = str(getattr(source_row, "subassembly_id", "") or "").strip()
    if not subassembly_ref:
        return []
    offset = float(edge_offset)
    z = float(edge_z)
    for index, segment in enumerate(list(segments or []), start=1):
        width = max(float(segment.get("width", 0.0) or 0.0), 0.0)
        if width <= 1.0e-9:
            continue
        slope = float(segment.get("slope", 0.0) or 0.0)
        kind = str(segment.get("kind", "") or "side_slope")
        offset += float(direction) * width
        z += slope * width
        point_code = "bench_surface" if kind == "bench" else "side_slope_surface"
        output.append(
            AppliedSectionSubassemblyPoint(
                point_id=f"{subassembly_ref}:{side_label}:{point_code}:{index}",
                subassembly_ref=subassembly_ref,
                point_code=point_code,
                x=base_x + normal_x * offset,
                y=base_y + normal_y * offset,
                z=z,
                lateral_offset=offset,
                side=side_label,
            )
        )
    if output:
        output.append(
            AppliedSectionSubassemblyPoint(
                point_id=f"{subassembly_ref}:{side_label}:daylight",
                subassembly_ref=subassembly_ref,
                point_code="daylight_marker",
                x=base_x + normal_x * offset,
                y=base_y + normal_y * offset,
                z=z,
                lateral_offset=offset,
                side=side_label,
            )
        )
    return output


def _subassembly_link_rows(
    subassembly_point_rows: list[AppliedSectionSubassemblyPoint],
    subassembly_rows: list[AppliedSectionSubassemblyRow],
) -> list[AppliedSectionSubassemblyLink]:
    if not subassembly_point_rows:
        return []
    row_by_id = {
        str(getattr(row, "subassembly_id", "") or "").strip(): row
        for row in list(subassembly_rows or [])
        if str(getattr(row, "subassembly_id", "") or "").strip()
    }
    groups: dict[tuple[str, str], list[AppliedSectionSubassemblyPoint]] = {}
    for point in list(subassembly_point_rows or []):
        subassembly_ref = str(getattr(point, "subassembly_ref", "") or "")
        link_code = _subassembly_link_code(getattr(point, "point_code", ""), row_by_id.get(subassembly_ref))
        groups.setdefault((subassembly_ref, link_code), []).append(point)
    output: list[AppliedSectionSubassemblyLink] = []
    for (subassembly_ref, link_code), points in groups.items():
        ordered = sorted(points, key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))
        if len(ordered) < 2:
            continue
        source_row = row_by_id.get(subassembly_ref)
        for index in range(len(ordered) - 1):
            start = ordered[index]
            end = ordered[index + 1]
            output.append(
                AppliedSectionSubassemblyLink(
                    link_id=f"{subassembly_ref}:link:{link_code}:{index + 1}",
                    subassembly_ref=subassembly_ref,
                    start_point_ref=str(getattr(start, "point_id", "") or ""),
                    end_point_ref=str(getattr(end, "point_id", "") or ""),
                    link_code=link_code,
                    surface_role=_surface_role_for_link_code(link_code),
                    material=str(getattr(source_row, "material", "") or "") if source_row is not None else "",
                )
            )
    return output


def _subassembly_shape_rows(
    subassembly_point_rows: list[AppliedSectionSubassemblyPoint],
    subassembly_rows: list[AppliedSectionSubassemblyRow],
) -> list[AppliedSectionSubassemblyShape]:
    if not subassembly_point_rows:
        return []
    row_by_id = {
        str(getattr(row, "subassembly_id", "") or "").strip(): row
        for row in list(subassembly_rows or [])
        if str(getattr(row, "subassembly_id", "") or "").strip()
    }
    groups: dict[tuple[str, str], list[AppliedSectionSubassemblyPoint]] = {}
    for point in list(subassembly_point_rows or []):
        subassembly_ref = str(getattr(point, "subassembly_ref", "") or "")
        shape_code = _subassembly_shape_code(getattr(point, "point_code", ""), row_by_id.get(subassembly_ref))
        groups.setdefault((subassembly_ref, shape_code), []).append(point)
    output: list[AppliedSectionSubassemblyShape] = []
    for (subassembly_ref, shape_code), points in groups.items():
        ordered = sorted(points, key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0))
        if len(ordered) < 3:
            continue
        source_row = row_by_id.get(subassembly_ref)
        output.append(
            AppliedSectionSubassemblyShape(
                shape_id=f"{subassembly_ref}:shape:{shape_code}",
                subassembly_ref=subassembly_ref,
                point_refs=[str(getattr(point, "point_id", "") or "") for point in ordered],
                shape_code=shape_code,
                material=str(getattr(source_row, "material", "") or "") if source_row is not None else "",
                thickness=float(getattr(source_row, "thickness", 0.0) or 0.0) if source_row is not None else 0.0,
                solid_family=_solid_family_for_shape_code(shape_code),
            )
        )
    return output


def _subassembly_point_code(point: AppliedSectionPoint, source_row: AppliedSectionSubassemblyRow | None) -> str:
    role = str(getattr(point, "point_role", "") or "").strip()
    if role:
        return role
    rules = tuple(getattr(source_row, "point_code_rules", ()) or ()) if source_row is not None else ()
    return str(rules[0]) if rules else "section_point"


def _subassembly_link_code(point_code: str, source_row: AppliedSectionSubassemblyRow | None) -> str:
    role = str(point_code or "").strip()
    if role:
        return _surface_role_for_link_code(role)
    rules = tuple(getattr(source_row, "link_code_rules", ()) or ()) if source_row is not None else ()
    return str(rules[0]) if rules else "section_link"


def _subassembly_shape_code(point_code: str, source_row: AppliedSectionSubassemblyRow | None) -> str:
    rules = tuple(getattr(source_row, "shape_code_rules", ()) or ()) if source_row is not None else ()
    if rules:
        return str(rules[0])
    return _surface_role_for_link_code(point_code)


def _surface_role_for_link_code(code: str) -> str:
    text = str(code or "").strip().lower()
    if text in {"fg_surface", "lane", "shoulder", "roadway"}:
        return "design_surface"
    if text in {"subgrade_surface", "subbase"}:
        return "subgrade_surface"
    if text in {"ditch_surface", "gutter_surface", "swale_surface", "channel_surface"}:
        return "drainage_surface"
    if text in {"side_slope_surface", "bench_surface", "daylight_marker", "daylight"}:
        return "slope_face_surface"
    return text or "section_link"


def _solid_family_for_shape_code(code: str) -> str:
    role = _surface_role_for_link_code(code)
    if role == "design_surface":
        return "road_body"
    if role == "subgrade_surface":
        return "subgrade"
    if role == "drainage_surface":
        return "drainage"
    if role == "slope_face_surface":
        return "grading"
    return "section_shape"


def _default_crossfall_percent_by_side(
    template: object | None,
    *,
    subassembly_template: SubassemblySectionTemplate | None = None,
) -> tuple[float, float]:
    left_values: list[float] = []
    right_values: list[float] = []
    for subassembly in list(getattr(subassembly_template, "subassembly_rows", []) or []):
        if not bool(getattr(subassembly, "enabled", True)):
            continue
        if str(getattr(subassembly, "kind", "") or "").strip().lower() not in {"lane", "shoulder"}:
            continue
        _append_crossfall_by_side(
            left_values,
            right_values,
            side=str(getattr(subassembly, "side", "") or "").strip().lower(),
            slope_percent=float(getattr(subassembly, "slope", 0.0) or 0.0) * 100.0,
        )
    if left_values or right_values:
        return _average(left_values), _average(right_values)
    return _average(left_values), _average(right_values)


def _append_crossfall_by_side(left_values: list[float], right_values: list[float], *, side: str, slope_percent: float) -> None:
    if side == "left":
        left_values.append(float(slope_percent))
    elif side == "right":
        right_values.append(float(slope_percent))
    elif side == "both":
        left_values.append(float(slope_percent))
        right_values.append(float(slope_percent))


def _superelevation_source_rows(result: SuperelevationStationResult | None) -> list[str]:
    if result is None:
        return []
    rows = []
    if str(getattr(result, "left_source", "") or ""):
        rows.append(f"left:{result.left_source}")
    if str(getattr(result, "right_source", "") or ""):
        rows.append(f"right:{result.right_source}")
    transition = str(getattr(result, "active_transition_id", "") or "")
    if transition:
        rows.append(f"transition:{transition}")
    return rows


def _section_row_drainage_refs(row, drainage_refs: list[str], drainage_refs_by_side: dict[str, list[str]] | None = None) -> list[str]:
    """Return Drainage refs for one active Subassembly row."""

    if str(getattr(row, "kind", "") or "").strip().lower() not in {"ditch", "gutter", "swale", "channel"}:
        return []
    side = str(getattr(row, "side", "") or "center").strip().lower()
    if side in {"left", "right"}:
        return _unique_refs(_drainage_refs_for_side(drainage_refs, side, drainage_refs_by_side))
    if side == "both":
        return _unique_refs(
            _drainage_refs_for_side(drainage_refs, "left", drainage_refs_by_side)
            + _drainage_refs_for_side(drainage_refs, "right", drainage_refs_by_side)
        )
    return _unique_refs(list(drainage_refs or []))


def _drainage_ref_for_side(
    drainage_refs: list[str] | None,
    side: str,
    drainage_refs_by_side: dict[str, list[str]] | None = None,
) -> str:
    refs = _drainage_refs_for_side(drainage_refs, side, drainage_refs_by_side)
    return refs[0] if refs else ""


def _drainage_refs_for_side(
    drainage_refs: list[str] | None,
    side: str,
    drainage_refs_by_side: dict[str, list[str]] | None = None,
) -> list[str]:
    side_text = str(side or "").strip().lower()
    if side_text and drainage_refs_by_side:
        direct = _unique_refs(list(drainage_refs_by_side.get(side_text, []) or []))
        if direct:
            return direct
    refs = _unique_refs(list(drainage_refs or []))
    if not refs:
        return []
    if side_text:
        for ref in refs:
            if side_text in str(ref or "").lower():
                return [ref]
    return refs if len(refs) == 1 else []


def _bench_evaluations(
    template: object | None,
    *,
    subassembly_template: SubassemblySectionTemplate | None = None,
    frame: AppliedSectionFrame | None = None,
    fg_points: list[tuple[float, float, float, float]] | None = None,
    surface_left_width: float = 0.0,
    surface_right_width: float = 0.0,
    existing_ground_surface: TINSurface | None = None,
    sampling_service: TinSamplingService | None = None,
) -> list[_BenchEvaluation]:
    if template is None and subassembly_template is None:
        return []
    frame_z = float(getattr(frame, "z", 0.0) or 0.0) if frame is not None else 0.0
    points = list(fg_points or [])
    side_edges = _bench_terminal_side_edges(
        template,
        subassembly_template=subassembly_template,
        frame=frame,
        fg_points=points,
        surface_left_width=surface_left_width,
        surface_right_width=surface_right_width,
    )
    output: list[_BenchEvaluation] = []
    for source_row in sorted(
        _active_section_source_rows(template, subassembly_template=subassembly_template),
        key=_section_source_sort_index,
    ):
        if not bool(getattr(source_row, "enabled", True)):
            continue
        if str(getattr(source_row, "kind", "") or "") != "side_slope":
            continue
        base_segments = _bench_profile_segments(source_row)
        if not base_segments:
            continue
        side = str(getattr(source_row, "side", "") or "center")
        for side_label, edge_offset, edge_z, direction in _bench_side_edges(side, side_edges=side_edges, default_z=frame_z):
            segments, diagnostics = _clip_bench_segments_to_terrain(
                source_row,
                list(base_segments),
                side_label=side_label,
                edge_offset=edge_offset,
                edge_z=edge_z,
                direction=direction,
                frame=frame,
                existing_ground_surface=existing_ground_surface,
                sampling_service=sampling_service,
            )
            output.append(
                _BenchEvaluation(
                    source_row=source_row,
                    side_label=side_label,
                    edge_offset=edge_offset,
                    edge_z=edge_z,
                    direction=direction,
                    segments=segments,
                    diagnostics=diagnostics,
                )
            )
    return output


def _bench_terminal_side_edges(
    template: object | None,
    *,
    subassembly_template: SubassemblySectionTemplate | None = None,
    frame: AppliedSectionFrame | None,
    fg_points: list[tuple[float, float, float, float]],
    surface_left_width: float,
    surface_right_width: float,
) -> dict[str, tuple[float, float, float]]:
    """Return slope/bench start edges after fixed-width section and ditch geometry."""

    frame_z = float(getattr(frame, "z", 0.0) or 0.0) if frame is not None else 0.0
    left_edge = (max(float(surface_left_width or 0.0), 0.0), frame_z)
    right_edge = (-max(float(surface_right_width or 0.0), 0.0), frame_z)
    for offset, _x, _y, z in list(fg_points or []):
        value = float(offset)
        elev = float(z)
        if value > left_edge[0] or (abs(value - left_edge[0]) <= 1.0e-9 and elev > left_edge[1]):
            left_edge = (value, elev)
        if value < right_edge[0] or (abs(value - right_edge[0]) <= 1.0e-9 and elev > right_edge[1]):
            right_edge = (value, elev)
    if frame is not None:
        for point in _ditch_section_points(
            template,
            frame=frame,
            surface_left_width=surface_left_width,
            surface_right_width=surface_right_width,
            subassembly_template=subassembly_template,
        ):
            offset = float(getattr(point, "lateral_offset", 0.0) or 0.0)
            z = float(getattr(point, "z", frame_z) or frame_z)
            if offset > left_edge[0] or (abs(offset - left_edge[0]) <= 1.0e-9 and z > left_edge[1]):
                left_edge = (offset, z)
            if offset < right_edge[0] or (abs(offset - right_edge[0]) <= 1.0e-9 and z > right_edge[1]):
                right_edge = (offset, z)
    return {
        "left": (left_edge[0], left_edge[1], 1.0),
        "right": (right_edge[0], right_edge[1], -1.0),
    }


def _bench_side_edges(
    side: str,
    *,
    side_edges: dict[str, tuple[float, float, float]],
    default_z: float,
) -> list[tuple[str, float, float, float]]:
    key = str(side or "center")
    rows: list[tuple[str, float, float, float]] = []
    if key in {"left", "both", "center"}:
        offset, z, direction = side_edges.get("left", (0.0, float(default_z), 1.0))
        rows.append(("left", float(offset), float(z), float(direction)))
    if key in {"right", "both", "center"}:
        offset, z, direction = side_edges.get("right", (0.0, float(default_z), -1.0))
        rows.append(("right", float(offset), float(z), float(direction)))
    return rows


def _bench_evaluation_diagnostics(evaluations: list[_BenchEvaluation]) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    for evaluation in list(evaluations or []):
        diagnostics.extend(list(getattr(evaluation, "diagnostics", []) or []))
    return diagnostics


def _bench_section_points(
    template: object | None,
    *,
    frame: AppliedSectionFrame,
    fg_points: list[tuple[float, float, float, float]],
    surface_left_width: float,
    surface_right_width: float,
    subassembly_template: SubassemblySectionTemplate | None = None,
    bench_evaluations: list[_BenchEvaluation] | None = None,
) -> list[AppliedSectionPoint]:
    """Return evaluated side-slope and bench break points outside FG edges."""

    if (template is None and subassembly_template is None) or not fg_points:
        return []
    angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(angle_rad)
    normal_y = math.cos(angle_rad)
    base_x = float(getattr(frame, "x", 0.0) or 0.0)
    base_y = float(getattr(frame, "y", 0.0) or 0.0)
    output: list[AppliedSectionPoint] = []
    evaluations = list(
        bench_evaluations
        or _bench_evaluations(
            template,
            subassembly_template=subassembly_template,
            frame=frame,
            fg_points=fg_points,
            surface_left_width=surface_left_width,
            surface_right_width=surface_right_width,
        )
    )
    for evaluation in evaluations:
        output.extend(
            _oriented_bench_points(
                evaluation.source_row,
                evaluation.segments,
                side_label=evaluation.side_label,
                edge_offset=evaluation.edge_offset,
                edge_z=evaluation.edge_z,
                direction=evaluation.direction,
                base_x=base_x,
                base_y=base_y,
                normal_x=normal_x,
                normal_y=normal_y,
            )
        )
    return output


def _oriented_bench_points(
    source_row,
    segments: list[dict[str, object]],
    *,
    side_label: str,
    edge_offset: float,
    edge_z: float,
    direction: float,
    base_x: float,
    base_y: float,
    normal_x: float,
    normal_y: float,
) -> list[AppliedSectionPoint]:
    output: list[AppliedSectionPoint] = []
    offset = float(edge_offset)
    z = float(edge_z)
    source_id = _subassembly_id(source_row, fallback="side_slope")
    subassembly_ref = str(getattr(source_row, "subassembly_id", "") or "").strip()
    for index, segment in enumerate(segments, start=1):
        width = max(float(segment.get("width", 0.0) or 0.0), 0.0)
        if width <= 1.0e-9:
            continue
        slope = float(segment.get("slope", 0.0) or 0.0)
        kind = str(segment.get("kind", "") or "side_slope")
        offset += float(direction) * width
        z += slope * width
        output.append(
            AppliedSectionPoint(
                point_id=f"bench:{side_label}:{source_id}:{index}",
                x=base_x + normal_x * offset,
                y=base_y + normal_y * offset,
                z=z,
                point_role="bench_surface" if kind == "bench" else "side_slope_surface",
                lateral_offset=offset,
                subassembly_ref=subassembly_ref,
                side=side_label,
            )
        )
    if output:
        output.append(
            AppliedSectionPoint(
                point_id=f"bench:{side_label}:{source_id}:daylight",
                x=base_x + normal_x * offset,
                y=base_y + normal_y * offset,
                z=z,
                point_role="daylight_marker",
                lateral_offset=offset,
                subassembly_ref=subassembly_ref,
                side=side_label,
            )
        )
    return output


def _bench_profile_segments(row, *, total_width: float | None = None) -> list[dict[str, object]]:
    params = dict(getattr(row, "parameters", {}) or {})
    rows = normalize_bench_rows(params.get("bench_rows", []))
    if not rows:
        return []
    remaining = max(
        float(total_width if total_width is not None else getattr(row, "width", 0.0) or 0.0),
        0.0,
    )
    current_slope = float(getattr(row, "slope", 0.0) or 0.0)
    repeat = _truthy(params.get("repeat_first_bench_to_daylight"))
    source_rows = [rows[0]] if repeat else rows
    segments: list[dict[str, object]] = []

    def append_row(row: dict[str, object]) -> bool:
        nonlocal remaining, current_slope
        if remaining <= 1.0e-9:
            return False
        before = remaining
        drop = max(float(row.get("drop", 0.0) or 0.0), 0.0)
        pre_width = 0.0
        if drop > 1.0e-9 and abs(current_slope) > 1.0e-9:
            pre_width = min(remaining, drop / abs(current_slope))
        if pre_width > 1.0e-9:
            segments.append({"kind": "side_slope", "width": pre_width, "slope": current_slope})
            remaining = max(remaining - pre_width, 0.0)
        bench_width = min(max(float(row.get("width", 0.0) or 0.0), 0.0), remaining)
        if bench_width > 1.0e-9:
            segments.append({"kind": "bench", "width": bench_width, "slope": float(row.get("slope", 0.0) or 0.0)})
            remaining = max(remaining - bench_width, 0.0)
        next_slope = float(row.get("post_slope", current_slope) or current_slope)
        current_slope = next_slope
        return abs(before - remaining) > 1.0e-9

    if repeat and source_rows:
        guard = 0
        while remaining > 1.0e-9 and guard < 512:
            guard += 1
            if not append_row(source_rows[0]):
                break
    else:
        for row in source_rows:
            if remaining <= 1.0e-9:
                break
            append_row(row)
    if remaining > 1.0e-9:
        segments.append({"kind": "side_slope", "width": remaining, "slope": current_slope})
    return segments


def _clip_bench_segments_to_terrain(
    subassembly,
    segments: list[dict[str, object]],
    *,
    side_label: str,
    edge_offset: float,
    edge_z: float,
    direction: float,
    frame: AppliedSectionFrame | None,
    existing_ground_surface: TINSurface | None,
    sampling_service: TinSamplingService | None = None,
) -> tuple[list[dict[str, object]], list[DiagnosticMessage]]:
    params = dict(getattr(subassembly, "parameters", {}) or {})
    if str(params.get("daylight_mode", "") or "").strip().lower() != "terrain":
        return segments, []
    subassembly_id = _subassembly_id(subassembly, fallback="side_slope")
    notes = f"{_subassembly_note(subassembly, fallback='side_slope')}; side={side_label}"
    if existing_ground_surface is None or frame is None:
        return segments, [
            DiagnosticMessage(
                severity="warning",
                kind="bench_daylight_fallback",
                message=(
                    f"side-slope subassembly {subassembly_id} uses terrain daylight mode, "
                    "but no existing-ground TIN is available; Assembly side-slope width was used."
                ),
                notes=notes,
            )
        ]
    service = sampling_service or TinSamplingService()
    segments = _terrain_daylight_search_segments(subassembly, segments)
    segments = _orient_bench_segments_to_terrain(
        segments,
        edge_offset=edge_offset,
        edge_z=edge_z,
        frame=frame,
        existing_ground_surface=existing_ground_surface,
        sampling_service=service,
    )
    terrain_context = _bench_terrain_context(
        subassembly,
        side_label=side_label,
        edge_offset=edge_offset,
        edge_z=edge_z,
        direction=direction,
        frame=frame,
        existing_ground_surface=existing_ground_surface,
        sampling_service=service,
    )
    diagnostics = []
    if terrain_context:
        diagnostics.append(terrain_context)
    intersection = _find_bench_tin_intersection(
        segments,
        side_label=side_label,
        edge_offset=edge_offset,
        edge_z=edge_z,
        direction=direction,
        frame=frame,
        surface=existing_ground_surface,
        sampling_service=service,
        search_step=_parameter_float(params, "daylight_search_step", 0.5),
    )
    if intersection is None:
        diagnostics.append(
            DiagnosticMessage(
                severity="warning",
                kind="bench_daylight_no_hit",
                message=(
                    f"side-slope subassembly {subassembly_id} did not intersect terrain within "
                    "the evaluated bench profile; full Assembly side-slope width was used."
                ),
                notes=notes,
            )
        )
        return segments, diagnostics
    total_width = _segments_total_width(segments)
    if intersection >= total_width - 1.0e-6:
        return segments, diagnostics
    clipped, clip_info = _clip_bench_segments(segments, intersection)
    diagnostics.extend(
        _bench_clip_diagnostics(
            subassembly,
            side_label=side_label,
            total_width=total_width,
            clip_distance=intersection,
            clip_info=clip_info,
        )
    )
    return clipped, diagnostics


def _terrain_daylight_search_segments(subassembly, segments: list[dict[str, object]]) -> list[dict[str, object]]:
    params = dict(getattr(subassembly, "parameters", {}) or {})
    if not _truthy(params.get("repeat_first_bench_to_daylight")):
        return segments
    max_width = _parameter_float(params, "daylight_max_width", _parameter_float(params, "daylight_max_search_width", 0.0))
    if max_width <= _segments_total_width(segments) + 1.0e-9:
        return segments
    extended = _bench_profile_segments(subassembly, total_width=max_width)
    return extended or segments


def _orient_bench_segments_to_terrain(
    segments: list[dict[str, object]],
    *,
    edge_offset: float,
    edge_z: float,
    frame: AppliedSectionFrame,
    existing_ground_surface: TINSurface,
    sampling_service: TinSamplingService,
) -> list[dict[str, object]]:
    direction = _bench_cut_fill_slope_direction(
        edge_offset=edge_offset,
        edge_z=edge_z,
        frame=frame,
        existing_ground_surface=existing_ground_surface,
        sampling_service=sampling_service,
    )
    if direction == 0:
        return segments
    output: list[dict[str, object]] = []
    for segment in list(segments or []):
        row = dict(segment)
        slope = float(row.get("slope", 0.0) or 0.0)
        if abs(slope) > 1.0e-12:
            row["slope"] = float(direction) * abs(slope)
        output.append(row)
    return output


def _bench_cut_fill_slope_direction(
    *,
    edge_offset: float,
    edge_z: float,
    frame: AppliedSectionFrame,
    existing_ground_surface: TINSurface,
    sampling_service: TinSamplingService,
    tolerance: float = 1.0e-6,
) -> int:
    x, y, _z = _station_offset_point(frame, edge_offset, edge_z)
    sample = sampling_service.sample_xy(surface=existing_ground_surface, x=x, y=y)
    if not bool(getattr(sample, "found", False)) or getattr(sample, "z", None) is None:
        return 0
    delta = float(sample.z) - float(edge_z)
    if delta > tolerance:
        return 1
    if delta < -tolerance:
        return -1
    return 0


def _bench_terrain_context(
    subassembly,
    *,
    side_label: str,
    edge_offset: float,
    edge_z: float,
    direction: float,
    frame: AppliedSectionFrame,
    existing_ground_surface: TINSurface,
    sampling_service: TinSamplingService,
) -> DiagnosticMessage | None:
    x, y, _z = _station_offset_point(frame, edge_offset, edge_z)
    sample = sampling_service.sample_xy(surface=existing_ground_surface, x=x, y=y)
    if not bool(getattr(sample, "found", False)) or getattr(sample, "z", None) is None:
        return None
    terrain_z = float(sample.z)
    context = "cut" if terrain_z > float(edge_z) else "fill" if terrain_z < float(edge_z) else "balanced"
    subassembly_id = _subassembly_id(subassembly, fallback="side_slope")
    return DiagnosticMessage(
        severity="info",
        kind="bench_cut_fill_context",
        message=(
            f"side-slope subassembly {subassembly_id} "
            f"evaluated {context} terrain context on {side_label} side."
        ),
        notes=(
            f"{_subassembly_note(subassembly, fallback='side_slope')}; "
            f"design_edge_z={float(edge_z):g}; terrain_edge_z={terrain_z:g}; direction={float(direction):g}"
        ),
    )


def _find_bench_tin_intersection(
    segments: list[dict[str, object]],
    *,
    side_label: str,
    edge_offset: float,
    edge_z: float,
    direction: float,
    frame: AppliedSectionFrame,
    surface: TINSurface,
    sampling_service: TinSamplingService,
    search_step: float,
    tolerance: float = 1.0e-6,
) -> float | None:
    del side_label
    total_width = _segments_total_width(segments)
    if total_width <= tolerance:
        return None
    step = max(float(search_step or 0.0), 0.25)
    sample_count = max(2, int(math.ceil(total_width / step)))
    previous_distance: float | None = None
    previous_delta: float | None = None
    for index in range(0, sample_count + 1):
        distance = total_width * float(index) / float(sample_count)
        delta = _bench_design_terrain_delta(
            segments,
            distance=distance,
            edge_offset=edge_offset,
            edge_z=edge_z,
            direction=direction,
            frame=frame,
            surface=surface,
            sampling_service=sampling_service,
        )
        if delta is None:
            continue
        if abs(delta) <= tolerance and distance > tolerance:
            return distance
        if previous_delta is not None and previous_distance is not None and previous_delta * delta < 0.0:
            return _bisect_bench_intersection(
                segments,
                low=previous_distance,
                high=distance,
                edge_offset=edge_offset,
                edge_z=edge_z,
                direction=direction,
                frame=frame,
                surface=surface,
                sampling_service=sampling_service,
                tolerance=tolerance,
            )
        previous_distance = distance
        previous_delta = delta
    return None


def _bisect_bench_intersection(
    segments: list[dict[str, object]],
    *,
    low: float,
    high: float,
    edge_offset: float,
    edge_z: float,
    direction: float,
    frame: AppliedSectionFrame,
    surface: TINSurface,
    sampling_service: TinSamplingService,
    tolerance: float,
    iterations: int = 32,
) -> float | None:
    low_delta = _bench_design_terrain_delta(
        segments,
        distance=low,
        edge_offset=edge_offset,
        edge_z=edge_z,
        direction=direction,
        frame=frame,
        surface=surface,
        sampling_service=sampling_service,
    )
    if low_delta is None:
        return None
    for _index in range(max(1, int(iterations))):
        mid = (float(low) + float(high)) * 0.5
        mid_delta = _bench_design_terrain_delta(
            segments,
            distance=mid,
            edge_offset=edge_offset,
            edge_z=edge_z,
            direction=direction,
            frame=frame,
            surface=surface,
            sampling_service=sampling_service,
        )
        if mid_delta is None:
            return None
        if abs(mid_delta) <= tolerance or abs(float(high) - float(low)) <= tolerance:
            return mid
        if low_delta * mid_delta <= 0.0:
            high = mid
        else:
            low = mid
            low_delta = mid_delta
    return (float(low) + float(high)) * 0.5


def _bench_design_terrain_delta(
    segments: list[dict[str, object]],
    *,
    distance: float,
    edge_offset: float,
    edge_z: float,
    direction: float,
    frame: AppliedSectionFrame,
    surface: TINSurface,
    sampling_service: TinSamplingService,
) -> float | None:
    offset, z = _bench_profile_point_at_distance(
        segments,
        distance=distance,
        edge_offset=edge_offset,
        edge_z=edge_z,
        direction=direction,
    )
    x, y, _z = _station_offset_point(frame, offset, z)
    sample = sampling_service.sample_xy(surface=surface, x=x, y=y)
    if not bool(getattr(sample, "found", False)) or getattr(sample, "z", None) is None:
        return None
    return z - float(sample.z)


def _bench_profile_point_at_distance(
    segments: list[dict[str, object]],
    *,
    distance: float,
    edge_offset: float,
    edge_z: float,
    direction: float,
) -> tuple[float, float]:
    remaining = max(float(distance or 0.0), 0.0)
    offset = float(edge_offset)
    z = float(edge_z)
    for segment in list(segments or []):
        width = max(float(segment.get("width", 0.0) or 0.0), 0.0)
        slope = float(segment.get("slope", 0.0) or 0.0)
        step = min(width, remaining)
        offset += float(direction) * step
        z += slope * step
        remaining -= step
        if remaining <= 1.0e-9:
            break
    return offset, z


def _station_offset_point(frame: AppliedSectionFrame, offset: float, z: float) -> tuple[float, float, float]:
    angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(angle_rad)
    normal_y = math.cos(angle_rad)
    base_x = float(getattr(frame, "x", 0.0) or 0.0)
    base_y = float(getattr(frame, "y", 0.0) or 0.0)
    return base_x + normal_x * float(offset), base_y + normal_y * float(offset), float(z)


def _clip_bench_segments(
    segments: list[dict[str, object]],
    clip_distance: float,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    remaining = max(float(clip_distance or 0.0), 0.0)
    output: list[dict[str, object]] = []
    skipped_count = 0
    shortened_kind = ""
    clipping_started = False
    for segment in list(segments or []):
        width = max(float(segment.get("width", 0.0) or 0.0), 0.0)
        if width <= 1.0e-9:
            continue
        if clipping_started:
            skipped_count += 1
            continue
        if remaining >= width - 1.0e-9:
            output.append(dict(segment))
            remaining -= width
            continue
        if remaining > 1.0e-9:
            clipped = dict(segment)
            clipped["width"] = remaining
            output.append(clipped)
            shortened_kind = str(segment.get("kind", "") or "side_slope")
        remaining = 0.0
        clipping_started = True
    return output, {"skipped_count": skipped_count, "shortened_kind": shortened_kind}


def _bench_clip_diagnostics(
    subassembly,
    *,
    side_label: str,
    total_width: float,
    clip_distance: float,
    clip_info: dict[str, object],
) -> list[DiagnosticMessage]:
    subassembly_id = _subassembly_id(subassembly, fallback="side_slope")
    notes = f"{_subassembly_note(subassembly, fallback='side_slope')}; side={side_label}"
    diagnostics = [
        DiagnosticMessage(
            severity="info",
            kind="bench_daylight_shortened",
            message=(
                f"side-slope subassembly {subassembly_id} was shortened at terrain daylight "
                f"from {float(total_width):g} to {float(clip_distance):g}."
            ),
            notes=notes,
        )
    ]
    skipped_count = int(clip_info.get("skipped_count", 0) or 0)
    if skipped_count > 0:
        diagnostics.append(
            DiagnosticMessage(
                severity="info",
                kind="bench_daylight_skipped",
                message=(
                    f"side-slope subassembly {subassembly_id} skipped {skipped_count} downstream "
                    "bench/slope segment(s) after terrain daylight intersection."
                ),
                notes=f"{notes}; shortened_kind={clip_info.get('shortened_kind', '')}",
            )
        )
    return diagnostics


def _segments_total_width(segments: list[dict[str, object]]) -> float:
    return sum(max(float(segment.get("width", 0.0) or 0.0), 0.0) for segment in list(segments or []))


def _bench_diagnostics(
    template: object | None,
    *,
    subassembly_template: SubassemblySectionTemplate | None = None,
) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    template_id = str(
        getattr(subassembly_template, "template_id", "")
        or getattr(template, "template_id", "")
        or ""
    )
    for source_row in _active_section_source_rows(template, subassembly_template=subassembly_template):
        if str(getattr(source_row, "kind", "") or "") != "side_slope":
            continue
        for message in subassembly_bench_validation_messages(source_row):
            diagnostics.append(
                DiagnosticMessage(
                    severity="warning",
                    kind="side_slope_bench_parameter",
                    message=message,
                    notes=f"template_id={template_id}",
                )
            )
    return diagnostics


def _structure_context_diagnostics(
    *,
    station: float,
    active_structure_ids: list[str],
    active_rule_ids: list[str],
    active_influence_zone_ids: list[str],
) -> list[str]:
    if not active_structure_ids:
        return []
    diagnostics: list[str] = []
    if not active_rule_ids:
        diagnostics.append(
            f"warning|structure_interaction_rule|STA {float(station):g}|Active structure context has no interaction rule ids."
        )
    if not active_influence_zone_ids:
        diagnostics.append(
            f"info|structure_influence_zone|STA {float(station):g}|Active structure context has no influence zone ids."
        )
    return diagnostics


def _intersection_context_diagnostics(result: IntersectionEvaluationResult | None) -> list[DiagnosticMessage]:
    if result is None:
        return []
    active_id = str(getattr(result, "active_intersection_id", "") or "")
    rows = []
    for kind in list(getattr(result, "diagnostic_rows", ()) or ()):
        text = str(kind or "")
        if text in {
            "intersection_context_not_found_for_alignment_station",
            "intersection_context_not_found_for_station",
        }:
            continue
        rows.append(
            DiagnosticMessage(
                severity="warning" if active_id else "info",
                kind=text,
                message="Intersection context diagnostic from Applied Sections handoff.",
                notes=f"intersection_id={active_id};station={float(getattr(result, 'station', 0.0) or 0.0):g}",
            )
        )
    return rows


def _unique_assembly_models(values: list[AssemblySourceIdentity]) -> list[AssemblySourceIdentity]:
    output: list[AssemblySourceIdentity] = []
    seen = set()
    for model in list(values or []):
        if model is None:
            continue
        assembly_id = str(getattr(model, "assembly_id", "") or "").strip()
        key = assembly_id or str(id(model))
        if key in seen:
            continue
        seen.add(key)
        output.append(model)
    return output


def _surface_section_offsets(
    template: object | None,
    *,
    frame: AppliedSectionFrame,
    subassembly_template: SubassemblySectionTemplate | None = None,
) -> list[tuple[float, float, float, float]]:
    """Return ordered FG points as lateral offset and world xyz tuples."""

    rows = _active_section_source_rows(template, subassembly_template=subassembly_template)
    if not rows:
        return []
    fg_kinds = {
        "lane",
        "shoulder",
        "median",
        "curb",
        "gutter",
        "sidewalk",
        "bike_lane",
        "green_strip",
    }
    left_points = [(0.0, float(getattr(frame, "z", 0.0) or 0.0))]
    right_points = [(0.0, float(getattr(frame, "z", 0.0) or 0.0))]
    center_half_width = 0.0
    center_z = float(getattr(frame, "z", 0.0) or 0.0)
    for source_row in sorted(rows, key=_section_source_sort_index):
        if str(getattr(source_row, "kind", "") or "") not in fg_kinds:
            continue
        width = max(float(getattr(source_row, "width", 0.0) or 0.0), 0.0)
        if width <= 0.0:
            continue
        side = str(getattr(source_row, "side", "") or "center")
        slope = float(getattr(source_row, "slope", 0.0) or 0.0)
        if side == "left":
            _append_offset_point(left_points, width, slope)
        elif side == "right":
            _append_offset_point(right_points, width, slope)
        elif side == "both":
            _append_offset_point(left_points, width, slope)
            _append_offset_point(right_points, width, slope)
        else:
            half_width = width * 0.5
            center_half_width = max(center_half_width, half_width)
            center_z = float(getattr(frame, "z", 0.0) or 0.0) + slope * half_width

    offset_rows: dict[float, float] = {0.0: float(getattr(frame, "z", 0.0) or 0.0)}
    if center_half_width > 0.0:
        offset_rows[-center_half_width] = center_z
        offset_rows[center_half_width] = center_z
    for offset, z in left_points[1:]:
        offset_rows[float(offset)] = float(z)
    for offset, z in right_points[1:]:
        offset_rows[-float(offset)] = float(z)
    if len(offset_rows) < 2:
        return []

    angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(angle_rad)
    normal_y = math.cos(angle_rad)
    base_x = float(getattr(frame, "x", 0.0) or 0.0)
    base_y = float(getattr(frame, "y", 0.0) or 0.0)
    return [
        (
            offset,
            base_x + normal_x * offset,
            base_y + normal_y * offset,
            z,
        )
        for offset, z in sorted(offset_rows.items(), key=lambda item: item[0])
    ]


def _append_offset_point(points: list[tuple[float, float]], width: float, slope: float) -> None:
    last_offset, last_z = points[-1]
    points.append((last_offset + float(width), last_z + float(slope) * float(width)))


def _ditch_section_points(
    template: object | None,
    *,
    frame: AppliedSectionFrame,
    surface_left_width: float,
    surface_right_width: float,
    drainage_refs: list[str] | None = None,
    drainage_refs_by_side: dict[str, list[str]] | None = None,
    subassembly_template: SubassemblySectionTemplate | None = None,
) -> list[AppliedSectionPoint]:
    """Return first-slice ditch surface strip points outside FG edges."""

    if template is None and subassembly_template is None:
        return []
    angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(angle_rad)
    normal_y = math.cos(angle_rad)
    base_x = float(getattr(frame, "x", 0.0) or 0.0)
    base_y = float(getattr(frame, "y", 0.0) or 0.0)
    base_z = float(getattr(frame, "z", 0.0) or 0.0)
    left_width = max(float(surface_left_width or 0.0), 0.0)
    right_width = max(float(surface_right_width or 0.0), 0.0)
    rows: list[tuple[float, float, str, str, str, str]] = []
    for source, source_ref in _ditch_source_rows(template, subassembly_template=subassembly_template):
        side = str(getattr(source, "side", "") or "center")
        local_profile = _ditch_local_profile(source)
        if not local_profile:
            continue
        if side in {"left", "both", "center"}:
            rows.extend(
                _oriented_ditch_rows(
                    local_profile,
                    edge_offset=left_width,
                    direction=1.0,
                    side_label="left",
                    subassembly_ref=source_ref,
                    drainage_ref=_drainage_ref_for_side(drainage_refs, "left", drainage_refs_by_side),
                )
            )
        if side in {"right", "both", "center"}:
            rows.extend(
                _oriented_ditch_rows(
                    local_profile,
                    edge_offset=-right_width,
                    direction=-1.0,
                    side_label="right",
                    subassembly_ref=source_ref,
                    drainage_ref=_drainage_ref_for_side(drainage_refs, "right", drainage_refs_by_side),
                )
            )
    output: list[AppliedSectionPoint] = []
    sorted_rows = sorted(rows, key=lambda item: (item[0], item[2]))
    for index, (offset, z_delta, role, subassembly_ref, side_label, drainage_ref) in enumerate(sorted_rows):
        output.append(
            AppliedSectionPoint(
                point_id=f"ditch:{role}:{index + 1}",
                x=base_x + normal_x * offset,
                y=base_y + normal_y * offset,
                z=base_z + z_delta,
                point_role="ditch_surface",
                lateral_offset=offset,
                subassembly_ref=subassembly_ref,
                side=side_label,
                drainage_ref=drainage_ref,
            )
        )
    for index, (offset, z_delta, subassembly_ref, side_label, drainage_ref) in enumerate(_ditch_flowline_rows(sorted_rows), start=1):
        output.append(
            AppliedSectionPoint(
                point_id=f"ditch:flowline:{side_label}:{index}",
                x=base_x + normal_x * offset,
                y=base_y + normal_y * offset,
                z=base_z + z_delta,
                point_role="ditch_flowline",
                lateral_offset=offset,
                subassembly_ref=subassembly_ref,
                side=side_label,
                drainage_ref=drainage_ref,
            )
        )
    return output


def _ditch_source_rows(
    template: object | None,
    *,
    subassembly_template: SubassemblySectionTemplate | None = None,
) -> list[tuple[object, str]]:
    subassemblies = [
        source
        for source in sorted(
            list(getattr(subassembly_template, "subassembly_rows", []) or []),
            key=_section_source_sort_index,
        )
        if bool(getattr(source, "enabled", True)) and str(getattr(source, "kind", "") or "") == "ditch"
    ]
    if subassemblies:
        return [(source, str(getattr(source, "subassembly_id", "") or "")) for source in subassemblies]
    return []


def _ditch_flowline_rows(rows: list[tuple[float, float, str, str, str, str]]) -> list[tuple[float, float, str, str, str]]:
    grouped: dict[tuple[str, str, str], list[tuple[float, float]]] = {}
    for offset, z_delta, _role, subassembly_ref, side_label, drainage_ref in list(rows or []):
        key = (str(subassembly_ref or ""), str(side_label or ""), str(drainage_ref or ""))
        grouped.setdefault(key, []).append((float(offset), float(z_delta)))
    output: list[tuple[float, float, str, str, str]] = []
    for subassembly_ref, side_label, drainage_ref in sorted(grouped):
        values = grouped[(subassembly_ref, side_label, drainage_ref)]
        if not values:
            continue
        min_z = min(z for _offset, z in values)
        low_offsets = [offset for offset, z in values if abs(z - min_z) <= 1.0e-9]
        if not low_offsets:
            continue
        flow_offset = sum(low_offsets) / len(low_offsets)
        output.append((flow_offset, min_z, subassembly_ref, side_label, drainage_ref))
    return output


def _ditch_local_profile(subassembly) -> list[tuple[float, float, str]]:
    """Return local outward distance, z delta, and semantic role for one ditch Subassembly row."""

    params = dict(getattr(subassembly, "parameters", {}) or {})
    shape = str(params.get("shape", "") or "").strip().lower().replace("-", "_")
    width = max(_parameter_float(params, "top_width", _section_row_width(subassembly)), 0.0)
    if not shape:
        fallback_width = _section_row_width(subassembly)
        if fallback_width <= 0.0:
            return []
        slope = float(getattr(subassembly, "slope", 0.0) or 0.0)
        return [
            (0.0, 0.0, "inner_edge"),
            (fallback_width, slope * fallback_width, "outer_edge"),
        ]
    if shape == "trapezoid":
        return _trapezoid_ditch_profile(subassembly, params, width)
    if shape == "v":
        return _v_ditch_profile(params, width)
    if shape in {"rectangular", "u"}:
        return _rectangular_ditch_profile(params, width, shape=shape)
    if shape == "l":
        return _l_ditch_profile(params, width)
    if shape == "custom_polyline":
        return _custom_ditch_profile(params)
    return []


def ditch_section_row_local_profile(row) -> list[tuple[float, float, str]]:
    """Return the local ditch profile used by viewers and section builders."""

    return _ditch_local_profile(row)


def ditch_section_row_validation_messages(row) -> list[str]:
    """Return user-facing validation messages for one ditch Subassembly row."""

    if str(getattr(row, "kind", "") or "") != "ditch":
        return []
    params = dict(getattr(row, "parameters", {}) or {})
    shape = str(params.get("shape", "") or "").strip().lower().replace("-", "_")
    subassembly_id = str(getattr(row, "subassembly_id", "") or "ditch")
    material_policy = ditch_material_policy(getattr(row, "material", ""))
    messages: list[str] = []
    if not shape:
        return messages
    if shape not in {"trapezoid", "u", "l", "rectangular", "v", "custom_polyline"}:
        return [f"ditch subassembly {subassembly_id} uses unsupported shape '{shape}'."]

    def require_positive(key: str) -> None:
        if key not in params or str(params.get(key, "") or "").strip() == "":
            messages.append(f"ditch subassembly {subassembly_id} missing required parameter {key}.")
            return
        try:
            value = float(params.get(key))
        except Exception:
            messages.append(f"ditch subassembly {subassembly_id} parameter {key} must be numeric.")
            return
        if value <= 0.0:
            messages.append(f"ditch subassembly {subassembly_id} parameter {key} must be greater than zero.")

    def validate_positive_if_present(key: str) -> None:
        if key not in params or str(params.get(key, "") or "").strip() == "":
            return
        try:
            value = float(params.get(key))
        except Exception:
            messages.append(f"ditch subassembly {subassembly_id} parameter {key} must be numeric.")
            return
        if value < 0.0:
            messages.append(f"ditch subassembly {subassembly_id} parameter {key} must not be negative.")

    if shape == "trapezoid":
        require_positive("depth")
        require_positive("bottom_width")
        validate_positive_if_present("top_width")
        validate_positive_if_present("inner_slope")
        validate_positive_if_present("outer_slope")
    elif shape in {"u", "l", "rectangular"}:
        require_positive("depth")
        require_positive("bottom_width")
        validate_positive_if_present("top_width")
        validate_positive_if_present("wall_thickness")
        validate_positive_if_present("lining_thickness")
        if shape == "l":
            wall_side = str(params.get("wall_side", "inner") or "inner").strip().lower()
            if wall_side not in {"inner", "outer", "left", "right"}:
                messages.append(
                    f"ditch subassembly {subassembly_id} parameter wall_side must be inner or outer."
                )
    elif shape == "v":
        require_positive("depth")
        if _section_row_width(row) <= 0.0 and _parameter_float(params, "top_width", 0.0) <= 0.0:
            messages.append(
                f"ditch subassembly {subassembly_id} requires positive width or top_width for V shape."
            )
        validate_positive_if_present("top_width")
        validate_positive_if_present("invert_offset")
    elif shape == "custom_polyline":
        points = _custom_ditch_profile(params)
        if len(points) < 2:
            messages.append(
                f"ditch subassembly {subassembly_id} custom_polyline requires at least two section_points."
            )
    if material_policy == "structural" and shape in {"u", "l", "rectangular"}:
        if _parameter_float(params, "wall_thickness", 0.0) <= 0.0:
            messages.append(
                f"ditch subassembly {subassembly_id} uses structural material and requires wall_thickness."
            )
    if material_policy == "lined" and shape in {"trapezoid", "v", "rectangular"}:
        if _parameter_float(params, "lining_thickness", 0.0) <= 0.0:
            messages.append(
                f"ditch subassembly {subassembly_id} uses lined material and should define lining_thickness."
            )
    return messages


def ditch_material_policy(material: object) -> str:
    """Classify ditch material for first-slice validation and editor hints."""

    text = str(material or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not text:
        return "unspecified"
    structural_tokens = ("concrete", "precast", "cast_in_place", "reinforced", "rc", "masonry", "stone")
    if any(token in text for token in structural_tokens):
        return "structural"
    lined_tokens = ("lined", "lining", "riprap", "gabion", "shotcrete")
    if any(token in text for token in lined_tokens):
        return "lined"
    earth_tokens = ("earth", "soil", "grass", "vegetated", "natural")
    if any(token in text for token in earth_tokens):
        return "earth"
    return "general"


def _ditch_shape_diagnostics(
    template: object | None,
    *,
    subassembly_template: SubassemblySectionTemplate | None = None,
) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    template_id = str(
        getattr(subassembly_template, "template_id", "")
        or getattr(template, "template_id", "")
        or ""
    )
    for source_row in _active_section_source_rows(template, subassembly_template=subassembly_template):
        for message in ditch_section_row_validation_messages(source_row):
            diagnostics.append(
                DiagnosticMessage(
                    severity="warning",
                    kind="ditch_shape_parameter",
                    message=message,
                    notes=f"template_id={template_id}",
                )
            )
    return diagnostics


def _trapezoid_ditch_profile(subassembly, params: dict[str, object], top_width: float) -> list[tuple[float, float, str]]:
    depth = max(_parameter_float(params, "depth", 0.0), 0.0)
    if depth <= 0.0:
        return _ditch_local_profile_without_shape(subassembly)
    bottom_width = max(_parameter_float(params, "bottom_width", max(top_width * 0.4, 0.0)), 0.0)
    inner_run = _run_from_slope(params, "inner_slope", depth)
    outer_run = _run_from_slope(params, "outer_slope", depth)
    if top_width <= 0.0:
        top_width = inner_run + bottom_width + outer_run
    if inner_run + bottom_width > top_width:
        inner_run = max(top_width - bottom_width, 0.0) * 0.5
    outer_pos = max(top_width, inner_run + bottom_width)
    return [
        (0.0, 0.0, "inner_edge"),
        (inner_run, -depth, "bottom_inner"),
        (inner_run + bottom_width, -depth, "bottom_outer"),
        (outer_pos, 0.0, "outer_edge"),
    ]


def _v_ditch_profile(params: dict[str, object], top_width: float) -> list[tuple[float, float, str]]:
    depth = max(_parameter_float(params, "depth", 0.0), 0.0)
    if depth <= 0.0 or top_width <= 0.0:
        return []
    invert_offset = _parameter_float(params, "invert_offset", top_width * 0.5)
    invert_offset = min(max(invert_offset, 0.0), top_width)
    return [
        (0.0, 0.0, "inner_edge"),
        (invert_offset, -depth, "invert"),
        (top_width, 0.0, "outer_edge"),
    ]


def _rectangular_ditch_profile(params: dict[str, object], top_width: float, *, shape: str) -> list[tuple[float, float, str]]:
    depth = max(_parameter_float(params, "depth", 0.0), 0.0)
    bottom_width = max(_parameter_float(params, "bottom_width", top_width), 0.0)
    if depth <= 0.0 or bottom_width <= 0.0:
        return []
    return [
        (0.0, 0.0, "inner_edge"),
        (0.0, -depth, "wall_bottom_inner" if shape == "u" else "bottom_inner"),
        (bottom_width, -depth, "wall_bottom_outer" if shape == "u" else "bottom_outer"),
        (bottom_width, 0.0, "outer_edge"),
    ]


def _l_ditch_profile(params: dict[str, object], top_width: float) -> list[tuple[float, float, str]]:
    depth = max(_parameter_float(params, "depth", 0.0), 0.0)
    bottom_width = max(_parameter_float(params, "bottom_width", top_width), 0.0)
    if depth <= 0.0 or bottom_width <= 0.0:
        return []
    wall_side = str(params.get("wall_side", "inner") or "inner").strip().lower()
    if wall_side in {"outer", "right"}:
        open_run = max(top_width - bottom_width, 0.0)
        return [
            (0.0, 0.0, "inner_edge"),
            (open_run, -depth, "bottom_inner"),
            (open_run + bottom_width, -depth, "wall_bottom"),
            (open_run + bottom_width, 0.0, "wall_top"),
        ]
    outer_pos = max(top_width, bottom_width)
    return [
        (0.0, 0.0, "wall_top"),
        (0.0, -depth, "wall_bottom"),
        (bottom_width, -depth, "bottom_outer"),
        (outer_pos, 0.0, "outer_edge"),
    ]


def _custom_ditch_profile(params: dict[str, object]) -> list[tuple[float, float, str]]:
    raw = str(params.get("section_points", "") or "")
    rows: list[tuple[float, float, str]] = []
    for index, token in enumerate(raw.replace(";", "|").split("|"), start=1):
        parts = [part.strip() for part in token.split(",")]
        if len(parts) < 2:
            continue
        try:
            rows.append((float(parts[0]), float(parts[1]), parts[2] if len(parts) > 2 and parts[2] else f"custom_{index}"))
        except Exception:
            continue
    return rows


def _ditch_local_profile_without_shape(subassembly) -> list[tuple[float, float, str]]:
    width = _section_row_width(subassembly)
    if width <= 0.0:
        return []
    slope = float(getattr(subassembly, "slope", 0.0) or 0.0)
    return [
        (0.0, 0.0, "inner_edge"),
        (width, slope * width, "outer_edge"),
    ]


def _oriented_ditch_rows(
    local_profile: list[tuple[float, float, str]],
    *,
    edge_offset: float,
    direction: float,
    side_label: str,
    subassembly_ref: str = "",
    drainage_ref: str = "",
) -> list[tuple[float, float, str, str, str, str]]:
    rows = []
    for local_offset, z_delta, role in local_profile:
        rows.append(
            (
                float(edge_offset) + float(direction) * float(local_offset),
                float(z_delta),
                f"{side_label}:{role}",
                subassembly_ref,
                str(side_label or ""),
                drainage_ref,
            )
        )
    return rows


def _edge_z_at_offset(
    fg_points: list[tuple[float, float, float, float]],
    offset: float,
    *,
    default_z: float,
) -> float:
    if not fg_points:
        return float(default_z)
    target = float(offset)
    nearest = min(fg_points, key=lambda row: abs(float(row[0]) - target))
    return float(nearest[3])


def _section_row_width(section_row) -> float:
    """Return the width carried by an active Subassembly row."""

    return max(float(getattr(section_row, "width", 0.0) or 0.0), 0.0)


def _subassembly_id(row, *, fallback: str = "") -> str:
    return str(getattr(row, "subassembly_id", "") or fallback)


def _subassembly_note(row, *, fallback: str = "") -> str:
    return f"subassembly_ref={_subassembly_id(row, fallback=fallback)}"


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _parameter_float(params: dict[str, object], key: str, default: float = 0.0) -> float:
    try:
        return float(params.get(key, default))
    except Exception:
        return float(default)


def _run_from_slope(params: dict[str, object], key: str, depth: float) -> float:
    slope = abs(_parameter_float(params, key, 0.0))
    if slope <= 1.0e-9:
        return 0.0
    return max(float(depth) / slope, 0.0)


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


def _average(values: list[float]) -> float:
    numbers = [float(value) for value in list(values or [])]
    return sum(numbers) / len(numbers) if numbers else 0.0
