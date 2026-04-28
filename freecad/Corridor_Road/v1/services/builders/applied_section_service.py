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
    assembly_models: list[AssemblyModel] = field(default_factory=list)
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
    assembly_models: list[AssemblyModel] = field(default_factory=list)
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
        daylight_left_width, daylight_right_width, daylight_left_slope, daylight_right_slope = self._daylight_policy(template)
        point_rows = self._build_point_rows(
            template,
            frame=frame,
            surface_left_width=left_width,
            surface_right_width=right_width,
            subgrade_depth=subgrade_depth,
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
        surface_left_width: float,
        surface_right_width: float,
        subgrade_depth: float,
    ) -> list[AppliedSectionPoint]:
        """Resolve first-slice FG, subgrade, and ditch section points from enabled components."""

        fg_points = _surface_section_offsets(template, frame=frame)
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


def _component_width(component) -> float:
    return max(float(getattr(component, "width", 0.0) or 0.0), 0.0)


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
