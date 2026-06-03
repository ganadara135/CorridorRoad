"""Section output mapper for CorridorRoad v1."""

from __future__ import annotations

from ...models.output.section_output import (
    SectionComponentRow,
    SectionGeometryRow,
    SectionOutput,
    SectionQuantityRow,
    SectionSummaryRow,
)
from ...models.result.applied_section import AppliedSection


class SectionOutputMapper:
    """Map applied-section results into section output payloads."""

    def map_applied_section(self, applied_section: AppliedSection) -> SectionOutput:
        """Create a normalized section output from one applied section."""

        component_rows = [
            SectionComponentRow(
                component_row_id=f"{applied_section.applied_section_id}:{index}",
                component_id=row.component_id,
                kind=row.kind,
                template_ref=row.source_template_id,
                assembly_ref=applied_section.assembly_id,
                region_ref=row.region_id,
                notes=_component_notes(row),
            )
            for index, row in enumerate(applied_section.component_rows, start=1)
        ]

        quantity_rows = [
            SectionQuantityRow(
                quantity_row_id=fragment.fragment_id,
                quantity_kind=fragment.quantity_kind,
                value=fragment.value,
                unit=fragment.unit,
                component_ref=fragment.component_id,
            )
            for fragment in applied_section.quantity_rows
        ]

        geometry_rows = self._geometry_rows(applied_section)

        summary_rows = [
            SectionSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:component-count",
                kind="component_count",
                label="Component Count",
                value=len(component_rows),
            ),
            SectionSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:quantity-count",
                kind="quantity_count",
                label="Quantity Count",
                value=len(quantity_rows),
            ),
        ] + self._frame_summary_rows(applied_section) + self._superelevation_summary_rows(applied_section) + self._intersection_summary_rows(applied_section)

        return SectionOutput(
            schema_version=1,
            project_id=applied_section.project_id,
            section_output_id=applied_section.applied_section_id,
            alignment_id=applied_section.alignment_id,
            station=applied_section.station,
            label=applied_section.label,
            unit_context=applied_section.unit_context,
            coordinate_context=applied_section.coordinate_context,
            selection_scope={"scope_kind": "single_station", "station": applied_section.station},
            source_refs=list(applied_section.source_refs),
            result_refs=[applied_section.applied_section_id],
            geometry_rows=geometry_rows,
            component_rows=component_rows,
            quantity_rows=quantity_rows,
            summary_rows=summary_rows,
            diagnostic_rows=list(applied_section.diagnostic_rows),
        )

    @staticmethod
    def _geometry_rows(applied_section: AppliedSection) -> list[SectionGeometryRow]:
        points = list(getattr(applied_section, "point_rows", []) or [])
        if len(points) < 2:
            return []
        rows = [
            SectionGeometryRow(
                row_id=f"{applied_section.applied_section_id}:design-section",
                kind="design_section",
                x_values=[float(point.x) for point in points],
                y_values=[float(point.z) for point in points],
                z_values=[float(point.z) for point in points],
                closed=False,
                style_role="finished_grade",
                source_ref=applied_section.applied_section_id,
            )
        ]
        rows.extend(_side_slope_geometry_rows(applied_section, points))
        return rows

    @staticmethod
    def _frame_summary_rows(applied_section: AppliedSection) -> list[SectionSummaryRow]:
        frame = getattr(applied_section, "frame", None)
        if frame is None:
            return []
        return [
            SectionSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:frame-x",
                kind="frame_x",
                label="Frame X",
                value=float(getattr(frame, "x", 0.0) or 0.0),
                unit="m",
            ),
            SectionSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:frame-y",
                kind="frame_y",
                label="Frame Y",
                value=float(getattr(frame, "y", 0.0) or 0.0),
                unit="m",
            ),
            SectionSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:frame-z",
                kind="frame_z",
                label="Frame Z",
                value=float(getattr(frame, "z", 0.0) or 0.0),
                unit="m",
            ),
            SectionSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:frame-tangent",
                kind="frame_tangent_direction",
                label="Frame Tangent Direction",
                value=float(getattr(frame, "tangent_direction_deg", 0.0) or 0.0),
                unit="deg",
            ),
            SectionSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:profile-grade",
                kind="profile_grade",
                label="Profile Grade",
                value=float(getattr(frame, "profile_grade", 0.0) or 0.0),
            ),
            SectionSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:frame-status",
                kind="frame_status",
                label="Frame Status",
                value=(
                    f"alignment={getattr(frame, 'alignment_status', '')}; "
                    f"profile={getattr(frame, 'profile_status', '')}"
                ),
            ),
        ]

    @staticmethod
    def _superelevation_summary_rows(applied_section: AppliedSection) -> list[SectionSummaryRow]:
        superelevation_id = str(getattr(applied_section, "active_superelevation_id", "") or "").strip()
        if not superelevation_id:
            return []
        rows = [
            SectionSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:superelevation-id",
                kind="superelevation_id",
                label="Superelevation",
                value=superelevation_id,
            ),
            SectionSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:superelevation-left-crossfall",
                kind="superelevation_left_crossfall",
                label="Left Crossfall",
                value=float(getattr(applied_section, "superelevation_left_crossfall", 0.0) or 0.0),
                unit="percent",
            ),
            SectionSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:superelevation-right-crossfall",
                kind="superelevation_right_crossfall",
                label="Right Crossfall",
                value=float(getattr(applied_section, "superelevation_right_crossfall", 0.0) or 0.0),
                unit="percent",
            ),
        ]
        transition_id = str(getattr(applied_section, "active_superelevation_transition_id", "") or "").strip()
        if transition_id:
            rows.append(
                SectionSummaryRow(
                    summary_id=f"{applied_section.applied_section_id}:superelevation-transition",
                    kind="superelevation_transition",
                    label="Superelevation Transition",
                    value=transition_id,
                )
            )
        source_rows = list(getattr(applied_section, "superelevation_source_rows", []) or [])
        if source_rows:
            rows.append(
                SectionSummaryRow(
                    summary_id=f"{applied_section.applied_section_id}:superelevation-source-rows",
                    kind="superelevation_source_rows",
                    label="Superelevation Source Rows",
                    value=", ".join(str(row) for row in source_rows if str(row).strip()),
                )
            )
        return rows

    @staticmethod
    def _intersection_summary_rows(applied_section: AppliedSection) -> list[SectionSummaryRow]:
        intersection_id = str(getattr(applied_section, "active_intersection_id", "") or "").strip()
        if not intersection_id:
            return []
        rows = [
            SectionSummaryRow(
                summary_id=f"{applied_section.applied_section_id}:intersection-id",
                kind="intersection_id",
                label="Intersection",
                value=intersection_id,
            )
        ]
        control_area_id = str(getattr(applied_section, "active_intersection_control_area_id", "") or "").strip()
        if control_area_id:
            rows.append(
                SectionSummaryRow(
                    summary_id=f"{applied_section.applied_section_id}:intersection-control-area",
                    kind="intersection_control_area",
                    label="Intersection Control Area",
                    value=control_area_id,
                )
            )
        leg_id = str(getattr(applied_section, "active_intersection_leg_id", "") or "").strip()
        leg_role = str(getattr(applied_section, "active_intersection_leg_role", "") or "").strip()
        if leg_id or leg_role:
            rows.append(
                SectionSummaryRow(
                    summary_id=f"{applied_section.applied_section_id}:intersection-leg",
                    kind="intersection_leg",
                    label="Intersection Leg",
                    value=" | ".join(value for value in (leg_id, leg_role) if value),
                )
            )
        control_refs = list(getattr(applied_section, "active_intersection_control_region_refs", []) or [])
        if control_refs:
            rows.append(
                SectionSummaryRow(
                    summary_id=f"{applied_section.applied_section_id}:intersection-control-regions",
                    kind="intersection_control_regions",
                    label="Intersection Control Regions",
                    value=", ".join(str(value) for value in control_refs if str(value).strip()),
                )
            )
        return rows


def _component_notes(row) -> str:
    kind = str(getattr(row, "kind", "") or "").strip().lower()
    notes = []
    if kind in {"side_slope", "bench", "daylight"}:
        notes.append("scope=side_slope")
    side = str(getattr(row, "side", "") or "").strip()
    if side:
        notes.append(f"side={side}")
    parameters = dict(getattr(row, "parameters", {}) or {})
    if str(parameters.get("effective_slope_source", "") or "") == "superelevation":
        notes.append("slope_source=superelevation")
        source = str(parameters.get("superelevation_source", "") or "").strip()
        if source:
            notes.append(f"superelevation_source={source}")
        transition = str(parameters.get("superelevation_transition", "") or "").strip()
        if transition:
            notes.append(f"superelevation_transition={transition}")
        crossfall = parameters.get("superelevation_crossfall_percent", None)
        if crossfall not in (None, ""):
            notes.append(f"crossfall={float(crossfall):.3f}%")
    structure_ids = list(getattr(row, "structure_ids", []) or [])
    if structure_ids:
        notes.append(f"structure_refs={','.join(str(value) for value in structure_ids if str(value).strip())}")
    return "; ".join(notes)


def _side_slope_geometry_rows(applied_section: AppliedSection, points: list[object]) -> list[SectionGeometryRow]:
    side_points = [
        point
        for point in list(points or [])
        if str(getattr(point, "point_role", "") or "") in {"side_slope_surface", "bench_surface", "daylight_marker"}
    ]
    if len(side_points) < 2:
        return []
    rows: list[SectionGeometryRow] = []
    for role, kind, style_role in (
        ("side_slope_surface", "side_slope_section", "side_slope"),
        ("bench_surface", "bench_section", "side_slope_bench"),
        ("daylight_marker", "daylight_marker", "side_slope"),
    ):
        role_points = sorted(
            [point for point in side_points if str(getattr(point, "point_role", "") or "") == role],
            key=lambda point: float(getattr(point, "lateral_offset", 0.0) or 0.0),
        )
        if len(role_points) < 1:
            continue
        rows.append(
            SectionGeometryRow(
                row_id=f"{applied_section.applied_section_id}:{kind}",
                kind=kind,
                x_values=[float(getattr(point, "lateral_offset", 0.0) or 0.0) for point in role_points],
                y_values=[float(getattr(point, "z", 0.0) or 0.0) for point in role_points],
                z_values=[float(getattr(point, "z", 0.0) or 0.0) for point in role_points],
                closed=False,
                style_role=style_role,
                source_ref=applied_section.applied_section_id,
            )
        )
    return rows
