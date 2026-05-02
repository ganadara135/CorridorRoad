"""Section-level cut/fill area evaluation for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.output.section_output import SectionOutput, SectionQuantityRow


_DEFAULT_DESIGN_KINDS = {
    "design_section",
    "finished_grade_section",
    "finished_grade",
    "section_polyline",
}

_DEFAULT_GROUND_KINDS = {
    "existing_ground_tin",
    "existing_ground",
    "terrain_intersection_polyline",
}


@dataclass(frozen=True)
class SectionEarthworkAreaRow:
    """One cut/fill area result for a section station."""

    quantity_kind: str
    value: float
    unit: str = "m2"


@dataclass(frozen=True)
class SectionEarthworkAreaResult:
    """Section cut/fill area result derived from design and ground polylines."""

    rows: list[SectionEarthworkAreaRow]
    status: str = "empty"
    notes: str = ""
    design_ref: str = ""
    ground_ref: str = ""

    @property
    def cut_area(self) -> float:
        return sum(row.value for row in self.rows if row.quantity_kind == "cut_area")

    @property
    def fill_area(self) -> float:
        return sum(row.value for row in self.rows if row.quantity_kind == "fill_area")


class SectionEarthworkAreaService:
    """Compute section cut/fill areas by comparing two section polylines."""

    def build(
        self,
        section_output: SectionOutput,
        *,
        design_kinds: set[str] | None = None,
        ground_kinds: set[str] | None = None,
        tolerance: float = 1e-9,
    ) -> SectionEarthworkAreaResult:
        """Build cut/fill area rows from one section output."""

        design_row = self._first_geometry_row(
            section_output,
            design_kinds or _DEFAULT_DESIGN_KINDS,
        )
        ground_row = self._first_geometry_row(
            section_output,
            ground_kinds or _DEFAULT_GROUND_KINDS,
        )
        if design_row is None or ground_row is None:
            return SectionEarthworkAreaResult(
                rows=[],
                status="missing_input",
                notes="Both design and existing-ground section polylines are required.",
            )

        design_points = self._geometry_points(design_row)
        ground_points = self._geometry_points(ground_row)
        if len(design_points) < 2 or len(ground_points) < 2:
            return SectionEarthworkAreaResult(
                rows=[],
                status="missing_input",
                notes="Both section polylines require at least two points.",
                design_ref=str(getattr(design_row, "row_id", "") or ""),
                ground_ref=str(getattr(ground_row, "row_id", "") or ""),
            )

        x_min = max(design_points[0][0], ground_points[0][0])
        x_max = min(design_points[-1][0], ground_points[-1][0])
        if x_max <= x_min + tolerance:
            return SectionEarthworkAreaResult(
                rows=[],
                status="no_overlap",
                notes="Design and existing-ground section polylines do not overlap in offset range.",
                design_ref=str(getattr(design_row, "row_id", "") or ""),
                ground_ref=str(getattr(ground_row, "row_id", "") or ""),
            )

        breakpoints = self._breakpoints_with_crossings(
            design_points,
            ground_points,
            x_min=x_min,
            x_max=x_max,
            tolerance=tolerance,
        )
        cut_area = 0.0
        fill_area = 0.0
        for x0, x1 in zip(breakpoints, breakpoints[1:]):
            if x1 <= x0 + tolerance:
                continue
            d0 = self._interpolate(design_points, x0) - self._interpolate(ground_points, x0)
            d1 = self._interpolate(design_points, x1) - self._interpolate(ground_points, x1)
            signed_area = (d0 + d1) * 0.5 * (x1 - x0)
            if signed_area > tolerance:
                fill_area += signed_area
            elif signed_area < -tolerance:
                cut_area += abs(signed_area)

        rows = []
        if cut_area > tolerance:
            rows.append(SectionEarthworkAreaRow(quantity_kind="cut_area", value=cut_area))
        if fill_area > tolerance:
            rows.append(SectionEarthworkAreaRow(quantity_kind="fill_area", value=fill_area))
        if not rows:
            rows.append(SectionEarthworkAreaRow(quantity_kind="balanced_area", value=0.0))

        return SectionEarthworkAreaResult(
            rows=rows,
            status="ok",
            notes=f"Computed section earthwork areas: cut={cut_area:.6f} m2, fill={fill_area:.6f} m2.",
            design_ref=str(getattr(design_row, "row_id", "") or ""),
            ground_ref=str(getattr(ground_row, "row_id", "") or ""),
        )

    def to_section_quantity_rows(
        self,
        result: SectionEarthworkAreaResult,
        *,
        row_id_prefix: str,
    ) -> list[SectionQuantityRow]:
        """Convert area result rows into section quantity rows."""

        return [
            SectionQuantityRow(
                quantity_row_id=f"{row_id_prefix}:section-earthwork-area:{index}",
                quantity_kind=row.quantity_kind,
                value=row.value,
                unit=row.unit,
                component_ref="section_earthwork_area",
            )
            for index, row in enumerate(result.rows, start=1)
        ]

    @staticmethod
    def quantity_kinds() -> set[str]:
        """Return section quantity kinds produced by this service."""

        return {"cut_area", "fill_area", "balanced_area"}

    @staticmethod
    def _first_geometry_row(section_output: SectionOutput, kinds: set[str]):
        for row in list(getattr(section_output, "geometry_rows", []) or []):
            kind = str(getattr(row, "kind", "") or "").strip()
            style_role = str(getattr(row, "style_role", "") or "").strip()
            if kind in kinds or style_role in kinds:
                return row
        return None

    @staticmethod
    def _geometry_points(row) -> list[tuple[float, float]]:
        x_values = [float(value) for value in list(getattr(row, "x_values", []) or [])]
        z_source = list(getattr(row, "z_values", []) or []) or list(getattr(row, "y_values", []) or [])
        z_values = [float(value) for value in z_source]
        count = min(len(x_values), len(z_values))
        points = sorted(zip(x_values[:count], z_values[:count]), key=lambda item: item[0])
        collapsed: list[tuple[float, float]] = []
        for x_value, z_value in points:
            if collapsed and abs(collapsed[-1][0] - x_value) <= 1e-12:
                collapsed[-1] = (x_value, z_value)
            else:
                collapsed.append((x_value, z_value))
        return collapsed

    def _breakpoints_with_crossings(
        self,
        design_points: list[tuple[float, float]],
        ground_points: list[tuple[float, float]],
        *,
        x_min: float,
        x_max: float,
        tolerance: float,
    ) -> list[float]:
        points = {x_min, x_max}
        points.update(x for x, _z in design_points if x_min - tolerance <= x <= x_max + tolerance)
        points.update(x for x, _z in ground_points if x_min - tolerance <= x <= x_max + tolerance)
        sorted_points = sorted(points)

        with_crossings = set(sorted_points)
        for x0, x1 in zip(sorted_points, sorted_points[1:]):
            if x1 <= x0 + tolerance:
                continue
            d0 = self._interpolate(design_points, x0) - self._interpolate(ground_points, x0)
            d1 = self._interpolate(design_points, x1) - self._interpolate(ground_points, x1)
            if d0 * d1 >= 0.0:
                continue
            crossing = x0 + (0.0 - d0) / (d1 - d0) * (x1 - x0)
            if x0 + tolerance < crossing < x1 - tolerance:
                with_crossings.add(crossing)
        return sorted(with_crossings)

    @staticmethod
    def _interpolate(points: list[tuple[float, float]], x_value: float) -> float:
        if x_value <= points[0][0]:
            return points[0][1]
        if x_value >= points[-1][0]:
            return points[-1][1]
        for index in range(len(points) - 1):
            x0, z0 = points[index]
            x1, z1 = points[index + 1]
            if abs(x1 - x0) <= 1e-12:
                continue
            if x0 - 1e-9 <= x_value <= x1 + 1e-9:
                ratio = (x_value - x0) / (x1 - x0)
                return z0 + (z1 - z0) * ratio
        return points[-1][1]
