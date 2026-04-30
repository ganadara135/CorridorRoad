"""Applied section builder service for CorridorRoad v1."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ...models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
    AppliedSectionPoint,
)
from ...models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from ...models.result.tin_surface import TINSurface
from ...common.diagnostics import DiagnosticMessage
from ...models.source.alignment_model import AlignmentModel
from ...models.source.assembly_model import (
    AssemblyModel,
    SectionTemplate,
    assembly_bench_validation_messages,
    normalize_bench_rows,
)
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
from ...services.evaluation.tin_sampling_service import TinSamplingService


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
    assembly_models: list[AssemblyModel] = field(default_factory=list)
    structure_model: StructureModel | None = None
    existing_ground_surface: TINSurface | None = None


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
    assembly_models: list[AssemblyModel] = field(default_factory=list)
    structure_model: StructureModel | None = None
    existing_ground_surface: TINSurface | None = None


@dataclass(frozen=True)
class _BenchEvaluation:
    component: object
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
        tin_sampling_service: TinSamplingService | None = None,
    ) -> None:
        self.alignment_service = alignment_service or AlignmentEvaluationService()
        self.profile_service = profile_service or ProfileEvaluationService()
        self.region_service = region_service or RegionResolutionService()
        self.override_service = override_service or OverrideResolutionService()
        self.structure_service = structure_service or StructureInteractionService()
        self.tin_sampling_service = tin_sampling_service or TinSamplingService()

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
        structure_result = self.structure_service.resolve_station(
            request.structure_model,
            request.station,
            active_structure_ref=region_context.structure_ref,
        ) if request.structure_model is not None else None

        template_id = self._resolve_template_id(
            assembly,
            assembly_ref=region_context.assembly_ref,
            template_ref=region_context.template_ref,
        )
        template = self._find_template(
            assembly,
            template_id,
        )
        diagnostics = self._build_diagnostics(
            assembly,
            assembly_ref=region_context.assembly_ref,
            template_id=template_id,
            template=template,
        )

        frame = self._build_frame(
            station=request.station,
            alignment_result=alignment_result,
            profile_result=profile_result,
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
        left_width, right_width = self._surface_widths(template)
        subgrade_depth = self._subgrade_depth(template)
        daylight_left_width, daylight_right_width, daylight_left_slope, daylight_right_slope = self._daylight_policy(template)
        fg_points = _surface_section_offsets(template, frame=frame)
        bench_evaluations = _bench_evaluations(
            template,
            frame=frame,
            fg_points=fg_points,
            surface_left_width=left_width,
            surface_right_width=right_width,
            existing_ground_surface=request.existing_ground_surface,
            sampling_service=self.tin_sampling_service,
        )
        diagnostics.extend(_bench_evaluation_diagnostics(bench_evaluations))
        component_rows = self._build_component_rows(
            template,
            region_id=region_context.region_id,
            override_ids=override_result.active_override_ids,
            structure_ids=_unique_refs(
                _region_structure_refs(region_context)
                + (
                    structure_result.active_structure_ids
                    if structure_result is not None
                    else []
                )
            ),
            bench_evaluations=bench_evaluations,
        )
        point_rows = self._build_point_rows(
            template,
            frame=frame,
            fg_points=fg_points,
            surface_left_width=left_width,
            surface_right_width=right_width,
            subgrade_depth=subgrade_depth,
            bench_evaluations=bench_evaluations,
        )

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
            component_rows=component_rows,
            surface_left_width=left_width,
            surface_right_width=right_width,
            subgrade_depth=subgrade_depth,
            daylight_left_width=daylight_left_width,
            daylight_right_width=daylight_right_width,
            daylight_left_slope=daylight_left_slope,
            daylight_right_slope=daylight_right_slope,
            point_rows=point_rows,
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
    def _resolve_assembly_model(
        fallback: AssemblyModel,
        assembly_models: list[AssemblyModel],
        *,
        assembly_ref: str,
    ) -> AssemblyModel:
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
        if template is not None:
            diagnostics.extend(_ditch_shape_diagnostics(template))
            diagnostics.extend(_bench_diagnostics(template))
        return diagnostics

    @staticmethod
    def _build_component_rows(
        template: SectionTemplate | None,
        *,
        region_id: str,
        override_ids: list[str],
        structure_ids: list[str],
        bench_evaluations: list[_BenchEvaluation] | None = None,
    ) -> list[AppliedSectionComponentRow]:
        if template is None:
            return []

        rows = [
            AppliedSectionComponentRow(
                component_id=component.component_id,
                kind=component.kind,
                source_template_id=template.template_id,
                region_id=region_id,
                side=str(getattr(component, "side", "") or "center"),
                width=max(float(getattr(component, "width", 0.0) or 0.0), 0.0),
                slope=float(getattr(component, "slope", 0.0) or 0.0),
                thickness=max(float(getattr(component, "thickness", 0.0) or 0.0), 0.0),
                material=str(getattr(component, "material", "") or ""),
                override_ids=list(override_ids),
                structure_ids=list(structure_ids),
            )
            for component in template.component_rows
            if component.enabled
        ]
        rows.extend(
            _bench_component_rows(
                template,
                region_id=region_id,
                override_ids=override_ids,
                structure_ids=structure_ids,
                bench_evaluations=bench_evaluations,
            )
        )
        return rows

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

    @staticmethod
    def _daylight_policy(template: SectionTemplate | None) -> tuple[float, float, float, float]:
        """Resolve first-slice daylight widths and slopes from side-slope components."""

        if template is None:
            return 0.0, 0.0, 0.0, 0.0
        left_width = 0.0
        right_width = 0.0
        left_slopes: list[float] = []
        right_slopes: list[float] = []
        for component in list(template.component_rows or []):
            if not bool(getattr(component, "enabled", True)):
                continue
            if str(getattr(component, "kind", "") or "") != "side_slope":
                continue
            width = max(float(getattr(component, "width", 0.0) or 0.0), 0.0)
            slope = float(getattr(component, "slope", 0.0) or 0.0)
            side = str(getattr(component, "side", "") or "center")
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
        template: SectionTemplate | None,
        *,
        frame: AppliedSectionFrame,
        fg_points: list[tuple[float, float, float, float]] | None = None,
        surface_left_width: float,
        surface_right_width: float,
        subgrade_depth: float,
        bench_evaluations: list[_BenchEvaluation] | None = None,
    ) -> list[AppliedSectionPoint]:
        """Resolve first-slice FG, subgrade, and ditch section points from enabled components."""

        fg_points = list(fg_points if fg_points is not None else _surface_section_offsets(template, frame=frame))
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
            )
        )
        output.extend(
            _bench_section_points(
                template,
                frame=frame,
                fg_points=fg_points,
                surface_left_width=surface_left_width,
                surface_right_width=surface_right_width,
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
                    region_model=request.region_model,
                    override_model=request.override_model,
                    station=station,
                    applied_section_id=section_id,
                    structure_model=request.structure_model,
                    existing_ground_surface=request.existing_ground_surface,
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
                    *[
                        str(getattr(assembly, "assembly_id", "") or "")
                        for assembly in _unique_assembly_models([request.assembly] + list(request.assembly_models or []))
                    ],
                    request.region_model.region_model_id,
                    request.override_model.override_model_id,
                    request.structure_model.structure_model_id
                    if request.structure_model is not None
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


def _region_structure_refs(region_context) -> list[str]:
    structure_ref = str(getattr(region_context, "structure_ref", "") or "").strip()
    if structure_ref:
        return [structure_ref]
    return list(getattr(region_context, "structure_refs", []) or [])[:1]


def _bench_evaluations(
    template: SectionTemplate | None,
    *,
    frame: AppliedSectionFrame | None = None,
    fg_points: list[tuple[float, float, float, float]] | None = None,
    surface_left_width: float = 0.0,
    surface_right_width: float = 0.0,
    existing_ground_surface: TINSurface | None = None,
    sampling_service: TinSamplingService | None = None,
) -> list[_BenchEvaluation]:
    if template is None:
        return []
    frame_z = float(getattr(frame, "z", 0.0) or 0.0) if frame is not None else 0.0
    left_width = max(float(surface_left_width or 0.0), 0.0)
    right_width = max(float(surface_right_width or 0.0), 0.0)
    points = list(fg_points or [])
    output: list[_BenchEvaluation] = []
    for component in sorted(list(getattr(template, "component_rows", []) or []), key=lambda row: int(getattr(row, "component_index", 0) or 0)):
        if not bool(getattr(component, "enabled", True)):
            continue
        if str(getattr(component, "kind", "") or "") != "side_slope":
            continue
        base_segments = _bench_profile_segments(component)
        if not base_segments:
            continue
        side = str(getattr(component, "side", "") or "center")
        for side_label, edge_offset, direction in _bench_side_edges(side, left_width=left_width, right_width=right_width):
            edge_z = _edge_z_at_offset(points, edge_offset, default_z=frame_z)
            segments, diagnostics = _clip_bench_segments_to_terrain(
                component,
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
                    component=component,
                    side_label=side_label,
                    edge_offset=edge_offset,
                    edge_z=edge_z,
                    direction=direction,
                    segments=segments,
                    diagnostics=diagnostics,
                )
            )
    return output


def _bench_side_edges(side: str, *, left_width: float, right_width: float) -> list[tuple[str, float, float]]:
    key = str(side or "center")
    rows: list[tuple[str, float, float]] = []
    if key in {"left", "both", "center"}:
        rows.append(("left", max(float(left_width or 0.0), 0.0), 1.0))
    if key in {"right", "both", "center"}:
        rows.append(("right", -max(float(right_width or 0.0), 0.0), -1.0))
    return rows


def _bench_evaluation_diagnostics(evaluations: list[_BenchEvaluation]) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    for evaluation in list(evaluations or []):
        diagnostics.extend(list(getattr(evaluation, "diagnostics", []) or []))
    return diagnostics


def _bench_component_rows(
    template: SectionTemplate,
    *,
    region_id: str,
    override_ids: list[str],
    structure_ids: list[str],
    bench_evaluations: list[_BenchEvaluation] | None = None,
) -> list[AppliedSectionComponentRow]:
    rows: list[AppliedSectionComponentRow] = []
    evaluations = list(bench_evaluations or _bench_evaluations(template))
    for evaluation in evaluations:
        component = evaluation.component
        segments = list(evaluation.segments or [])
        if not segments:
            continue
        side = str(getattr(evaluation, "side_label", "") or getattr(component, "side", "") or "center")
        for index, segment in enumerate(segments, start=1):
            kind = str(segment.get("kind", "") or "side_slope")
            rows.append(
                AppliedSectionComponentRow(
                    component_id=f"{component.component_id}:{kind}:{index}",
                    kind=kind,
                    source_template_id=template.template_id,
                    region_id=region_id,
                    side=side,
                    width=max(float(segment.get("width", 0.0) or 0.0), 0.0),
                    slope=float(segment.get("slope", 0.0) or 0.0),
                    material=str(getattr(component, "material", "") or ""),
                    override_ids=list(override_ids),
                    structure_ids=list(structure_ids),
                )
            )
        rows.append(
            AppliedSectionComponentRow(
                component_id=f"{component.component_id}:daylight",
                kind="daylight",
                source_template_id=template.template_id,
                region_id=region_id,
                side=side,
                width=0.0,
                slope=0.0,
                material=str(getattr(component, "material", "") or ""),
                override_ids=list(override_ids),
                structure_ids=list(structure_ids),
            )
        )
    return rows


def _bench_section_points(
    template: SectionTemplate | None,
    *,
    frame: AppliedSectionFrame,
    fg_points: list[tuple[float, float, float, float]],
    surface_left_width: float,
    surface_right_width: float,
    bench_evaluations: list[_BenchEvaluation] | None = None,
) -> list[AppliedSectionPoint]:
    """Return evaluated side-slope and bench break points outside FG edges."""

    if template is None or not fg_points:
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
            frame=frame,
            fg_points=fg_points,
            surface_left_width=surface_left_width,
            surface_right_width=surface_right_width,
        )
    )
    for evaluation in evaluations:
        output.extend(
            _oriented_bench_points(
                evaluation.component,
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
    component,
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
    component_id = str(getattr(component, "component_id", "") or "side_slope")
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
                point_id=f"bench:{side_label}:{component_id}:{index}",
                x=base_x + normal_x * offset,
                y=base_y + normal_y * offset,
                z=z,
                point_role="bench_surface" if kind == "bench" else "side_slope_surface",
                lateral_offset=offset,
            )
        )
    if output:
        output.append(
            AppliedSectionPoint(
                point_id=f"bench:{side_label}:{component_id}:daylight",
                x=base_x + normal_x * offset,
                y=base_y + normal_y * offset,
                z=z,
                point_role="daylight_marker",
                lateral_offset=offset,
            )
        )
    return output


def _bench_profile_segments(component) -> list[dict[str, object]]:
    params = dict(getattr(component, "parameters", {}) or {})
    rows = normalize_bench_rows(params.get("bench_rows", []))
    if not rows:
        return []
    remaining = max(float(getattr(component, "width", 0.0) or 0.0), 0.0)
    current_slope = float(getattr(component, "slope", 0.0) or 0.0)
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
    component,
    segments: list[dict[str, object]],
    *,
    side_label: str,
    edge_offset: float,
    edge_z: float,
    direction: float,
    frame: AppliedSectionFrame | None,
    existing_ground_surface: TINSurface | None,
    sampling_service: TinSamplingService | None,
) -> tuple[list[dict[str, object]], list[DiagnosticMessage]]:
    params = dict(getattr(component, "parameters", {}) or {})
    if str(params.get("daylight_mode", "") or "").strip().lower() != "terrain":
        return segments, []
    component_id = str(getattr(component, "component_id", "") or "side_slope")
    notes = f"component_id={component_id}; side={side_label}"
    if existing_ground_surface is None or frame is None:
        return segments, [
            DiagnosticMessage(
                severity="warning",
                kind="bench_daylight_fallback",
                message=(
                    f"side-slope component {component_id} uses terrain daylight mode, "
                    "but no existing-ground TIN is available; Assembly side-slope width was used."
                ),
                notes=notes,
            )
        ]
    service = sampling_service or TinSamplingService()
    segments = _orient_bench_segments_to_terrain(
        segments,
        edge_offset=edge_offset,
        edge_z=edge_z,
        frame=frame,
        existing_ground_surface=existing_ground_surface,
        sampling_service=service,
    )
    terrain_context = _bench_terrain_context(
        component,
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
                    f"side-slope component {component_id} did not intersect terrain within "
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
            component,
            side_label=side_label,
            total_width=total_width,
            clip_distance=intersection,
            clip_info=clip_info,
        )
    )
    return clipped, diagnostics


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
    component,
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
    return DiagnosticMessage(
        severity="info",
        kind="bench_cut_fill_context",
        message=(
            f"side-slope component {getattr(component, 'component_id', '') or 'side_slope'} "
            f"evaluated {context} terrain context on {side_label} side."
        ),
        notes=f"design_edge_z={float(edge_z):g}; terrain_edge_z={terrain_z:g}; direction={float(direction):g}",
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
    component,
    *,
    side_label: str,
    total_width: float,
    clip_distance: float,
    clip_info: dict[str, object],
) -> list[DiagnosticMessage]:
    component_id = str(getattr(component, "component_id", "") or "side_slope")
    diagnostics = [
        DiagnosticMessage(
            severity="info",
            kind="bench_daylight_shortened",
            message=(
                f"side-slope component {component_id} was shortened at terrain daylight "
                f"from {float(total_width):g} to {float(clip_distance):g}."
            ),
            notes=f"component_id={component_id}; side={side_label}",
        )
    ]
    skipped_count = int(clip_info.get("skipped_count", 0) or 0)
    if skipped_count > 0:
        diagnostics.append(
            DiagnosticMessage(
                severity="info",
                kind="bench_daylight_skipped",
                message=(
                    f"side-slope component {component_id} skipped {skipped_count} downstream "
                    "bench/slope segment(s) after terrain daylight intersection."
                ),
                notes=f"component_id={component_id}; side={side_label}; shortened_kind={clip_info.get('shortened_kind', '')}",
            )
        )
    return diagnostics


def _segments_total_width(segments: list[dict[str, object]]) -> float:
    return sum(max(float(segment.get("width", 0.0) or 0.0), 0.0) for segment in list(segments or []))


def _bench_diagnostics(template: SectionTemplate) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    for component in list(getattr(template, "component_rows", []) or []):
        if not bool(getattr(component, "enabled", True)):
            continue
        if str(getattr(component, "kind", "") or "") != "side_slope":
            continue
        for message in assembly_bench_validation_messages(component):
            diagnostics.append(
                DiagnosticMessage(
                    severity="warning",
                    kind="side_slope_bench_parameter",
                    message=message,
                    notes=f"template_id={template.template_id}",
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


def _unique_assembly_models(values: list[AssemblyModel]) -> list[AssemblyModel]:
    output: list[AssemblyModel] = []
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
    template: SectionTemplate | None,
    *,
    frame: AppliedSectionFrame,
) -> list[tuple[float, float, float, float]]:
    """Return ordered FG points as lateral offset and world xyz tuples."""

    if template is None:
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
    for component in sorted(list(getattr(template, "component_rows", []) or []), key=lambda row: int(getattr(row, "component_index", 0) or 0)):
        if not bool(getattr(component, "enabled", True)):
            continue
        if str(getattr(component, "kind", "") or "") not in fg_kinds:
            continue
        width = max(float(getattr(component, "width", 0.0) or 0.0), 0.0)
        if width <= 0.0:
            continue
        side = str(getattr(component, "side", "") or "center")
        slope = float(getattr(component, "slope", 0.0) or 0.0)
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
    template: SectionTemplate | None,
    *,
    frame: AppliedSectionFrame,
    surface_left_width: float,
    surface_right_width: float,
) -> list[AppliedSectionPoint]:
    """Return first-slice ditch surface strip points outside FG edges."""

    if template is None:
        return []
    angle_rad = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
    normal_x = -math.sin(angle_rad)
    normal_y = math.cos(angle_rad)
    base_x = float(getattr(frame, "x", 0.0) or 0.0)
    base_y = float(getattr(frame, "y", 0.0) or 0.0)
    base_z = float(getattr(frame, "z", 0.0) or 0.0)
    left_width = max(float(surface_left_width or 0.0), 0.0)
    right_width = max(float(surface_right_width or 0.0), 0.0)
    rows: list[tuple[float, float, str]] = []
    for component in sorted(list(getattr(template, "component_rows", []) or []), key=lambda row: int(getattr(row, "component_index", 0) or 0)):
        if not bool(getattr(component, "enabled", True)):
            continue
        if str(getattr(component, "kind", "") or "") != "ditch":
            continue
        side = str(getattr(component, "side", "") or "center")
        local_profile = _ditch_local_profile(component)
        if not local_profile:
            continue
        if side in {"left", "both", "center"}:
            rows.extend(_oriented_ditch_rows(local_profile, edge_offset=left_width, direction=1.0, side_label="left"))
        if side in {"right", "both", "center"}:
            rows.extend(_oriented_ditch_rows(local_profile, edge_offset=-right_width, direction=-1.0, side_label="right"))
    output: list[AppliedSectionPoint] = []
    for index, (offset, z_delta, role) in enumerate(sorted(rows, key=lambda item: (item[0], item[2]))):
        output.append(
            AppliedSectionPoint(
                point_id=f"ditch:{role}:{index + 1}",
                x=base_x + normal_x * offset,
                y=base_y + normal_y * offset,
                z=base_z + z_delta,
                point_role="ditch_surface",
                lateral_offset=offset,
            )
        )
    return output


def _ditch_local_profile(component) -> list[tuple[float, float, str]]:
    """Return local outward distance, z delta, and semantic role for one ditch component."""

    params = dict(getattr(component, "parameters", {}) or {})
    shape = str(params.get("shape", "") or "").strip().lower().replace("-", "_")
    width = max(_parameter_float(params, "top_width", _component_width(component)), 0.0)
    if not shape:
        fallback_width = _component_width(component)
        if fallback_width <= 0.0:
            return []
        slope = float(getattr(component, "slope", 0.0) or 0.0)
        return [
            (0.0, 0.0, "inner_edge"),
            (fallback_width, slope * fallback_width, "outer_edge"),
        ]
    if shape == "trapezoid":
        return _trapezoid_ditch_profile(component, params, width)
    if shape == "v":
        return _v_ditch_profile(params, width)
    if shape in {"rectangular", "u"}:
        return _rectangular_ditch_profile(params, width, shape=shape)
    if shape == "l":
        return _l_ditch_profile(params, width)
    if shape == "custom_polyline":
        return _custom_ditch_profile(params)
    return []


def ditch_component_local_profile(component) -> list[tuple[float, float, str]]:
    """Return the local ditch profile used by viewers and section builders."""

    return _ditch_local_profile(component)


def ditch_component_validation_messages(component) -> list[str]:
    """Return user-facing validation messages for one ditch component."""

    if str(getattr(component, "kind", "") or "") != "ditch":
        return []
    params = dict(getattr(component, "parameters", {}) or {})
    shape = str(params.get("shape", "") or "").strip().lower().replace("-", "_")
    component_id = str(getattr(component, "component_id", "") or "ditch")
    material_policy = ditch_material_policy(getattr(component, "material", ""))
    messages: list[str] = []
    if not shape:
        return messages
    if shape not in {"trapezoid", "u", "l", "rectangular", "v", "custom_polyline"}:
        return [f"ditch component {component_id} uses unsupported shape '{shape}'."]

    def require_positive(key: str) -> None:
        if key not in params or str(params.get(key, "") or "").strip() == "":
            messages.append(f"ditch component {component_id} missing required parameter {key}.")
            return
        try:
            value = float(params.get(key))
        except Exception:
            messages.append(f"ditch component {component_id} parameter {key} must be numeric.")
            return
        if value <= 0.0:
            messages.append(f"ditch component {component_id} parameter {key} must be greater than zero.")

    def validate_positive_if_present(key: str) -> None:
        if key not in params or str(params.get(key, "") or "").strip() == "":
            return
        try:
            value = float(params.get(key))
        except Exception:
            messages.append(f"ditch component {component_id} parameter {key} must be numeric.")
            return
        if value < 0.0:
            messages.append(f"ditch component {component_id} parameter {key} must not be negative.")

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
                    f"ditch component {component_id} parameter wall_side must be inner or outer."
                )
    elif shape == "v":
        require_positive("depth")
        if _component_width(component) <= 0.0 and _parameter_float(params, "top_width", 0.0) <= 0.0:
            messages.append(
                f"ditch component {component_id} requires positive width or top_width for V shape."
            )
        validate_positive_if_present("top_width")
        validate_positive_if_present("invert_offset")
    elif shape == "custom_polyline":
        points = _custom_ditch_profile(params)
        if len(points) < 2:
            messages.append(
                f"ditch component {component_id} custom_polyline requires at least two section_points."
            )
    if material_policy == "structural" and shape in {"u", "l", "rectangular"}:
        if _parameter_float(params, "wall_thickness", 0.0) <= 0.0:
            messages.append(
                f"ditch component {component_id} uses structural material and requires wall_thickness."
            )
    if material_policy == "lined" and shape in {"trapezoid", "v", "rectangular"}:
        if _parameter_float(params, "lining_thickness", 0.0) <= 0.0:
            messages.append(
                f"ditch component {component_id} uses lined material and should define lining_thickness."
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


def _ditch_shape_diagnostics(template: SectionTemplate) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    for component in list(getattr(template, "component_rows", []) or []):
        if not bool(getattr(component, "enabled", True)):
            continue
        for message in ditch_component_validation_messages(component):
            diagnostics.append(
                DiagnosticMessage(
                    severity="warning",
                    kind="ditch_shape_parameter",
                    message=message,
                    notes=f"template_id={template.template_id}",
                )
            )
    return diagnostics


def _trapezoid_ditch_profile(component, params: dict[str, object], top_width: float) -> list[tuple[float, float, str]]:
    depth = max(_parameter_float(params, "depth", 0.0), 0.0)
    if depth <= 0.0:
        return _ditch_local_profile_without_shape(component)
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


def _ditch_local_profile_without_shape(component) -> list[tuple[float, float, str]]:
    width = _component_width(component)
    if width <= 0.0:
        return []
    slope = float(getattr(component, "slope", 0.0) or 0.0)
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
) -> list[tuple[float, float, str]]:
    rows = []
    for local_offset, z_delta, role in local_profile:
        rows.append((float(edge_offset) + float(direction) * float(local_offset), float(z_delta), f"{side_label}:{role}"))
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


def _component_width(component) -> float:
    return max(float(getattr(component, "width", 0.0) or 0.0), 0.0)


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
