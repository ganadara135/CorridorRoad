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
                region_ref=row.region_id,
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
        ] + self._frame_summary_rows(applied_section)

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
        return [
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
