"""TIN build service for CorridorRoad v1."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from ...models.result.tin_surface import (
    TINProvenanceRow,
    TINQualityRow,
    TINSurface,
    TINTriangle,
    TINVertex,
)


@dataclass(frozen=True)
class TINPointInput:
    """One raw point used to build a TIN surface."""

    point_id: str
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class TINBuildRequest:
    """Input bundle for building a TIN surface from point rows."""

    project_id: str
    surface_id: str
    point_rows: list[TINPointInput] = field(default_factory=list)
    surface_kind: str = "existing_ground_tin"
    label: str = ""
    source_ref: str = ""


class TINBuildService:
    """Build normalized TIN surfaces from point input."""

    def build_from_points(self, request: TINBuildRequest) -> TINSurface:
        """Build a first-slice TIN from a complete regular point lattice."""

        point_map = self._unique_point_map(request.point_rows)
        if not point_map:
            raise ValueError("At least three unique TIN points are required.")

        x_values = sorted({key[0] for key in point_map})
        y_values = sorted({key[1] for key in point_map})
        expected_count = len(x_values) * len(y_values)
        if expected_count != len(point_map):
            raise ValueError(
                "First-slice TIN build requires a complete regular point lattice; "
                f"expected {expected_count} grid points from unique X/Y values, got {len(point_map)}."
            )
        if len(x_values) < 2 or len(y_values) < 2:
            raise ValueError("At least two unique X and Y values are required to form TIN triangles.")

        vertices: list[TINVertex] = []
        vertex_ids: dict[tuple[float, float], str] = {}
        for y_index, y in enumerate(y_values):
            for x_index, x in enumerate(x_values):
                point = point_map[(x, y)]
                vertex_id = f"v{len(vertices)}"
                vertex_ids[(x, y)] = vertex_id
                vertices.append(
                    TINVertex(
                        vertex_id=vertex_id,
                        x=point.x,
                        y=point.y,
                        z=point.z,
                        source_point_ref=point.point_id,
                    )
                )

        triangles: list[TINTriangle] = []
        for y_index in range(len(y_values) - 1):
            y0 = y_values[y_index]
            y1 = y_values[y_index + 1]
            for x_index in range(len(x_values) - 1):
                x0 = x_values[x_index]
                x1 = x_values[x_index + 1]
                v00 = vertex_ids[(x0, y0)]
                v10 = vertex_ids[(x1, y0)]
                v01 = vertex_ids[(x0, y1)]
                v11 = vertex_ids[(x1, y1)]
                cell_id = f"cell:{x_index}:{y_index}"
                triangles.append(TINTriangle(f"{cell_id}:a", v00, v10, v11))
                triangles.append(TINTriangle(f"{cell_id}:b", v00, v11, v01))

        z_values = [point.z for point in point_map.values()]
        return TINSurface(
            schema_version=1,
            project_id=request.project_id,
            surface_id=request.surface_id,
            surface_kind=request.surface_kind,
            label=request.label or request.surface_id,
            source_refs=[request.source_ref] if request.source_ref else [],
            vertex_rows=vertices,
            triangle_rows=triangles,
            boundary_refs=[f"{request.surface_id}:grid-boundary"],
            quality_rows=self._quality_rows(
                request.surface_id,
                x_values=x_values,
                y_values=y_values,
                z_values=z_values,
                vertex_count=len(vertices),
                triangle_count=len(triangles),
            ),
            provenance_rows=[
                TINProvenanceRow(
                    provenance_id=f"{request.surface_id}:provenance:points",
                    source_kind="point_lattice",
                    source_ref=request.source_ref,
                    notes="Built from complete point lattice; each grid cell is split into two TIN triangles.",
                )
            ],
        )

    def build_from_csv(
        self,
        path: str | Path,
        *,
        project_id: str,
        surface_id: str,
        surface_kind: str = "existing_ground_tin",
        label: str = "",
        x_column: str = "easting",
        y_column: str = "northing",
        z_column: str = "elevation",
    ) -> TINSurface:
        """Build a TIN surface from a CSV point cloud file."""

        csv_path = Path(path)
        points: list[TINPointInput] = []
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for index, row in enumerate(reader):
                try:
                    points.append(
                        TINPointInput(
                            point_id=f"{csv_path.name}:row:{index + 2}",
                            x=float(row[x_column]),
                            y=float(row[y_column]),
                            z=float(row[z_column]),
                        )
                    )
                except KeyError as exc:
                    raise ValueError(f"Missing required CSV column: {exc}") from exc
                except Exception as exc:
                    raise ValueError(f"Invalid TIN point row at CSV line {index + 2}: {exc}") from exc

        return self.build_from_points(
            TINBuildRequest(
                project_id=project_id,
                surface_id=surface_id,
                surface_kind=surface_kind,
                label=label or csv_path.stem,
                point_rows=points,
                source_ref=str(csv_path),
            )
        )

    @staticmethod
    def _unique_point_map(point_rows: list[TINPointInput]) -> dict[tuple[float, float], TINPointInput]:
        point_map: dict[tuple[float, float], TINPointInput] = {}
        for point in list(point_rows or []):
            key = (round(float(point.x), 9), round(float(point.y), 9))
            if key in point_map:
                continue
            point_map[key] = TINPointInput(
                point_id=str(point.point_id),
                x=float(point.x),
                y=float(point.y),
                z=float(point.z),
            )
        return point_map

    @staticmethod
    def _quality_rows(
        surface_id: str,
        *,
        x_values: list[float],
        y_values: list[float],
        z_values: list[float],
        vertex_count: int,
        triangle_count: int,
    ) -> list[TINQualityRow]:
        x_spacing = TINBuildService._spacing_summary(x_values)
        y_spacing = TINBuildService._spacing_summary(y_values)
        return [
            TINQualityRow(f"{surface_id}:quality:vertex-count", "vertex_count", vertex_count, "count"),
            TINQualityRow(f"{surface_id}:quality:triangle-count", "triangle_count", triangle_count, "count"),
            TINQualityRow(f"{surface_id}:quality:unique-x-count", "unique_x_count", len(x_values), "count"),
            TINQualityRow(f"{surface_id}:quality:unique-y-count", "unique_y_count", len(y_values), "count"),
            TINQualityRow(f"{surface_id}:quality:x-min", "x_min", min(x_values), "model_length"),
            TINQualityRow(f"{surface_id}:quality:x-max", "x_max", max(x_values), "model_length"),
            TINQualityRow(f"{surface_id}:quality:y-min", "y_min", min(y_values), "model_length"),
            TINQualityRow(f"{surface_id}:quality:y-max", "y_max", max(y_values), "model_length"),
            TINQualityRow(f"{surface_id}:quality:z-min", "z_min", min(z_values), "model_length"),
            TINQualityRow(f"{surface_id}:quality:z-max", "z_max", max(z_values), "model_length"),
            TINQualityRow(f"{surface_id}:quality:x-spacing", "x_spacing", x_spacing, "model_length"),
            TINQualityRow(f"{surface_id}:quality:y-spacing", "y_spacing", y_spacing, "model_length"),
        ]

    @staticmethod
    def _spacing_summary(values: list[float]) -> float | str:
        deltas = [
            round(float(values[index + 1]) - float(values[index]), 9)
            for index in range(len(values) - 1)
        ]
        if not deltas:
            return ""
        unique = sorted(set(deltas))
        if len(unique) == 1:
            return unique[0]
        return "variable"
