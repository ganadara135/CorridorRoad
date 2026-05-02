"""V1-native earthwork area analysis service."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable

from ...common.diagnostics import DiagnosticMessage
from ...models.output.section_output import SectionGeometryRow, SectionOutput
from ...models.result.applied_section import AppliedSection, AppliedSectionPoint
from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.quantity_model import QuantityFragment
from ...models.result.tin_surface import TINSurface
from ..evaluation import SectionEarthworkAreaService, TinSamplingService


_DEFAULT_DESIGN_ROLES = {
    "fg_surface",
    "ditch_surface",
    "side_slope_surface",
    "bench_surface",
    "daylight_marker",
    "section_point",
}

_ROLE_PRIORITY = {
    "section_point": 5,
    "fg_surface": 10,
    "ditch_surface": 20,
    "side_slope_surface": 30,
    "bench_surface": 40,
    "daylight_marker": 50,
}


@dataclass(frozen=True)
class EarthworkAnalysisBuildRequest:
    """Input contract for station-level v1 earthwork area analysis."""

    project_id: str
    applied_section_set: AppliedSectionSet | None
    existing_ground_surface: TINSurface | None
    analysis_id: str
    design_roles: set[str] = field(default_factory=lambda: set(_DEFAULT_DESIGN_ROLES))


@dataclass(frozen=True)
class EarthworkAnalysisResult:
    """Station-level earthwork area fragments and diagnostics."""

    analysis_id: str
    project_id: str
    applied_section_set_id: str = ""
    area_fragment_rows: list[QuantityFragment] = field(default_factory=list)
    section_outputs: list[SectionOutput] = field(default_factory=list)
    diagnostic_rows: list[DiagnosticMessage] = field(default_factory=list)
    status: str = "empty"
    notes: str = ""


@dataclass(frozen=True)
class _DesignPoint:
    offset: float
    x: float
    y: float
    z: float
    role: str
    point_id: str


class EarthworkAnalysisService:
    """Build station-level cut/fill area fragments from Applied Sections and EG TIN."""

    def __init__(
        self,
        *,
        area_service: SectionEarthworkAreaService | None = None,
        sampling_service: TinSamplingService | None = None,
    ) -> None:
        self.area_service = area_service or SectionEarthworkAreaService()
        self.sampling_service = sampling_service or TinSamplingService()

    def build(self, request: EarthworkAnalysisBuildRequest) -> EarthworkAnalysisResult:
        """Create station-level `cut_area` and `fill_area` quantity fragments."""

        diagnostics: list[DiagnosticMessage] = []
        applied_section_set = request.applied_section_set
        if applied_section_set is None:
            diagnostics.append(
                _diagnostic(
                    "error",
                    "missing_applied_section_set",
                    "Applied Sections result is required for earthwork analysis.",
                )
            )
            return self._result(request, diagnostics=diagnostics, status="missing_input")

        sections = self._ordered_sections(applied_section_set)
        if not sections:
            diagnostics.append(
                _diagnostic(
                    "error",
                    "missing_applied_sections",
                    "AppliedSectionSet has no section rows for earthwork analysis.",
                    notes=applied_section_set.applied_section_set_id,
                )
            )
            return self._result(request, diagnostics=diagnostics, status="missing_input")

        if request.existing_ground_surface is None:
            diagnostics.append(
                _diagnostic(
                    "error",
                    "missing_existing_ground_tin",
                    "Existing-ground TIN is required for v1 earthwork analysis.",
                    notes=applied_section_set.applied_section_set_id,
                )
            )
            return self._result(request, diagnostics=diagnostics, status="missing_input")

        fragments: list[QuantityFragment] = []
        section_outputs: list[SectionOutput] = []
        for section in sections:
            section_result = self._build_section_result(
                request=request,
                section=section,
                diagnostics=diagnostics,
            )
            if section_result is None:
                continue
            section_output, section_fragments = section_result
            section_outputs.append(section_output)
            fragments.extend(section_fragments)

        status = self._status(fragments, diagnostics)
        notes = self._notes(fragments, section_outputs, diagnostics)
        return self._result(
            request,
            area_fragment_rows=fragments,
            section_outputs=section_outputs,
            diagnostics=diagnostics,
            status=status,
            notes=notes,
        )

    def _build_section_result(
        self,
        *,
        request: EarthworkAnalysisBuildRequest,
        section: AppliedSection,
        diagnostics: list[DiagnosticMessage],
    ) -> tuple[SectionOutput, list[QuantityFragment]] | None:
        design_points = self._design_points(section, design_roles=request.design_roles)
        if len(design_points) < 2:
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "missing_design_section_polyline",
                    "Section has fewer than two design surface points for earthwork analysis.",
                    notes=self._section_notes(section),
                )
            )
            return None

        ground_points = self._ground_points(
            surface=request.existing_ground_surface,
            design_points=design_points,
            surface_ref=str(getattr(request.existing_ground_surface, "surface_id", "") or ""),
        )
        if len(ground_points) < 2:
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "missing_existing_ground_section_polyline",
                    "Section has fewer than two existing-ground TIN hits for earthwork analysis.",
                    notes=self._section_notes(section),
                )
            )
            return self._section_output(request, section, design_points, ground_points), []

        miss_count = len(design_points) - len(ground_points)
        if miss_count > 0:
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "partial_existing_ground_section_polyline",
                    "Some design offsets did not hit the existing-ground TIN.",
                    notes=f"{self._section_notes(section)}; missed_offsets={miss_count}",
                )
            )

        section_output = self._section_output(request, section, design_points, ground_points)
        area_result = self.area_service.build(section_output)
        if area_result.status != "ok":
            diagnostics.append(
                _diagnostic(
                    "warning",
                    f"section_earthwork_area_{area_result.status}",
                    area_result.notes or "Section earthwork area calculation did not produce usable rows.",
                    notes=self._section_notes(section),
                )
            )
            return section_output, []

        return section_output, self._area_fragments(request, section, area_result.rows)

    def _design_points(
        self,
        section: AppliedSection,
        *,
        design_roles: set[str],
    ) -> list[_DesignPoint]:
        points = [
            point
            for point in list(getattr(section, "point_rows", []) or [])
            if str(getattr(point, "point_role", "") or "").strip() in design_roles
        ]
        if not points:
            return self._fallback_flat_design_points(section)
        return _collapse_design_points(_to_design_points(points))

    def _fallback_flat_design_points(self, section: AppliedSection) -> list[_DesignPoint]:
        frame = getattr(section, "frame", None)
        left = max(float(getattr(section, "surface_left_width", 0.0) or 0.0), 0.0)
        right = max(float(getattr(section, "surface_right_width", 0.0) or 0.0), 0.0)
        if left <= 0.0 and right <= 0.0:
            return []
        z = float(getattr(frame, "z", 0.0) or 0.0)
        center_x = float(getattr(frame, "x", float(getattr(section, "station", 0.0) or 0.0)) or 0.0)
        center_y = float(getattr(frame, "y", 0.0) or 0.0)
        direction = math.radians(float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0))
        normal_x = -math.sin(direction)
        normal_y = math.cos(direction)
        offsets = [-right, left] if left > 0.0 and right > 0.0 else [0.0, left or -right]
        return [
            _DesignPoint(
                offset=float(offset),
                x=center_x + float(offset) * normal_x,
                y=center_y + float(offset) * normal_y,
                z=z,
                role="fallback_design_surface",
                point_id=f"{section.applied_section_id}:fallback:{index}",
            )
            for index, offset in enumerate(offsets, start=1)
        ]

    def _ground_points(
        self,
        *,
        surface: TINSurface,
        design_points: list[_DesignPoint],
        surface_ref: str,
    ) -> list[_DesignPoint]:
        ground: list[_DesignPoint] = []
        for point in design_points:
            sample = self.sampling_service.sample_xy(
                surface=surface,
                surface_ref=surface_ref,
                x=point.x,
                y=point.y,
            )
            if not bool(getattr(sample, "found", False)) or getattr(sample, "z", None) is None:
                continue
            ground.append(
                _DesignPoint(
                    offset=point.offset,
                    x=float(getattr(sample, "x", point.x) or point.x),
                    y=float(getattr(sample, "y", point.y) or point.y),
                    z=float(sample.z),
                    role="existing_ground_tin",
                    point_id=str(getattr(sample, "face_id", "") or ""),
                )
            )
        return ground

    def _section_output(
        self,
        request: EarthworkAnalysisBuildRequest,
        section: AppliedSection,
        design_points: list[_DesignPoint],
        ground_points: list[_DesignPoint],
    ) -> SectionOutput:
        section_id = str(getattr(section, "applied_section_id", "") or f"section:{section.station:g}")
        geometry_rows = [
            SectionGeometryRow(
                row_id=f"{request.analysis_id}:{section_id}:design",
                kind="design_section",
                x_values=[point.offset for point in design_points],
                y_values=[point.z for point in design_points],
                z_values=[point.z for point in design_points],
                style_role="finished_grade",
                source_ref=section_id,
            )
        ]
        if ground_points:
            geometry_rows.append(
                SectionGeometryRow(
                    row_id=f"{request.analysis_id}:{section_id}:existing-ground",
                    kind="existing_ground_tin",
                    x_values=[point.offset for point in ground_points],
                    y_values=[point.z for point in ground_points],
                    z_values=[point.z for point in ground_points],
                    style_role="existing_ground",
                    source_ref=str(getattr(request.existing_ground_surface, "surface_id", "") or ""),
                )
            )
        return SectionOutput(
            schema_version=1,
            project_id=request.project_id,
            section_output_id=f"{request.analysis_id}:{section_id}",
            alignment_id=str(getattr(section, "alignment_id", "") or ""),
            station=float(getattr(section, "station", 0.0) or 0.0),
            geometry_rows=geometry_rows,
        )

    def _area_fragments(
        self,
        request: EarthworkAnalysisBuildRequest,
        section: AppliedSection,
        area_rows: Iterable[object],
    ) -> list[QuantityFragment]:
        rows: list[QuantityFragment] = []
        section_id = str(getattr(section, "applied_section_id", "") or f"section:{section.station:g}")
        station = float(getattr(section, "station", 0.0) or 0.0)
        for index, row in enumerate(list(area_rows or []), start=1):
            quantity_kind = str(getattr(row, "quantity_kind", "") or "")
            rows.append(
                QuantityFragment(
                    fragment_id=f"{request.analysis_id}:area:{section_id}:{quantity_kind}:{index}",
                    quantity_kind=quantity_kind,
                    measurement_kind="section_earthwork_area",
                    value=float(getattr(row, "value", 0.0) or 0.0),
                    unit=str(getattr(row, "unit", "m2") or "m2"),
                    station_start=station,
                    station_end=station,
                    component_ref="section_earthwork_area",
                    assembly_ref=str(getattr(section, "assembly_id", "") or ""),
                    region_ref=str(getattr(section, "region_id", "") or ""),
                )
            )
        return rows

    def _ordered_sections(self, applied_section_set: AppliedSectionSet) -> list[AppliedSection]:
        sections = list(getattr(applied_section_set, "sections", []) or [])
        by_id = {str(getattr(section, "applied_section_id", "") or ""): section for section in sections}
        ordered: list[AppliedSection] = []
        seen: set[str] = set()
        for station_row in list(getattr(applied_section_set, "station_rows", []) or []):
            section_id = str(getattr(station_row, "applied_section_id", "") or "")
            section = by_id.get(section_id)
            if section is None or section_id in seen:
                continue
            ordered.append(section)
            seen.add(section_id)
        ordered.extend(
            section
            for section in sorted(sections, key=lambda item: float(getattr(item, "station", 0.0) or 0.0))
            if str(getattr(section, "applied_section_id", "") or "") not in seen
        )
        return ordered

    def _result(
        self,
        request: EarthworkAnalysisBuildRequest,
        *,
        area_fragment_rows: list[QuantityFragment] | None = None,
        section_outputs: list[SectionOutput] | None = None,
        diagnostics: list[DiagnosticMessage] | None = None,
        status: str,
        notes: str = "",
    ) -> EarthworkAnalysisResult:
        applied_section_set = request.applied_section_set
        return EarthworkAnalysisResult(
            analysis_id=request.analysis_id,
            project_id=request.project_id,
            applied_section_set_id=str(getattr(applied_section_set, "applied_section_set_id", "") or ""),
            area_fragment_rows=list(area_fragment_rows or []),
            section_outputs=list(section_outputs or []),
            diagnostic_rows=list(diagnostics or []),
            status=status,
            notes=notes,
        )

    @staticmethod
    def _section_notes(section: AppliedSection) -> str:
        return f"section={section.applied_section_id}; station={float(section.station):.3f}"

    @staticmethod
    def _status(fragments: list[QuantityFragment], diagnostics: list[DiagnosticMessage]) -> str:
        if not fragments:
            return "empty"
        if any(row.severity == "error" for row in diagnostics):
            return "partial"
        if diagnostics:
            return "partial"
        return "ok"

    @staticmethod
    def _notes(
        fragments: list[QuantityFragment],
        section_outputs: list[SectionOutput],
        diagnostics: list[DiagnosticMessage],
    ) -> str:
        return (
            f"Generated {len(fragments)} station earthwork area fragment(s) "
            f"from {len(section_outputs)} section output(s); diagnostics={len(diagnostics)}."
        )


def _to_design_points(points: list[AppliedSectionPoint]) -> list[_DesignPoint]:
    return [
        _DesignPoint(
            offset=float(getattr(point, "lateral_offset", 0.0) or 0.0),
            x=float(getattr(point, "x", 0.0) or 0.0),
            y=float(getattr(point, "y", 0.0) or 0.0),
            z=float(getattr(point, "z", 0.0) or 0.0),
            role=str(getattr(point, "point_role", "") or ""),
            point_id=str(getattr(point, "point_id", "") or ""),
        )
        for point in points
    ]


def _collapse_design_points(points: list[_DesignPoint]) -> list[_DesignPoint]:
    by_offset: dict[float, _DesignPoint] = {}
    for point in sorted(points, key=lambda item: (item.offset, _ROLE_PRIORITY.get(item.role, 0))):
        key = round(float(point.offset), 9)
        current = by_offset.get(key)
        if current is None or _ROLE_PRIORITY.get(point.role, 0) >= _ROLE_PRIORITY.get(current.role, 0):
            by_offset[key] = point
    return [by_offset[key] for key in sorted(by_offset)]


def _diagnostic(severity: str, kind: str, message: str, *, notes: str = "") -> DiagnosticMessage:
    return DiagnosticMessage(
        severity=severity,
        kind=kind,
        message=message,
        notes=notes,
    )
