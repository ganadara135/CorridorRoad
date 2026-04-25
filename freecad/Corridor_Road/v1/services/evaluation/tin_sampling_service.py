"""TIN sampling service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.tin_surface import TINSurface, TINTriangle, TINVertex


@dataclass(frozen=True)
class TinSampleResult:
    """Minimal TIN sample result."""

    surface_ref: str
    x: float
    y: float
    z: float | None = None
    found: bool = False
    status: str = "no_hit"
    face_id: str = ""
    confidence: float = 0.0
    query_kind: str = "xy"
    notes: str = ""


class TinSamplingService:
    """Provide query-oriented TIN sampling."""

    def sample_xy(
        self,
        *,
        surface: TINSurface | None = None,
        surface_ref: str = "",
        x: float,
        y: float,
        tolerance: float = 1e-9,
    ) -> TinSampleResult:
        """Sample elevation from a TIN surface at XY."""

        resolved_ref = surface_ref or (surface.surface_id if surface is not None else "")
        if surface is None:
            return TinSampleResult(
                surface_ref=resolved_ref,
                x=x,
                y=y,
                status="error",
                notes="TIN surface object is required for XY sampling.",
            )

        vertices = surface.vertex_map()
        degenerate_count = 0
        for triangle in surface.triangle_rows:
            tri_vertices = self._triangle_vertices(vertices, triangle)
            if tri_vertices is None:
                continue
            sample = self._sample_triangle(
                triangle=triangle,
                vertices=tri_vertices,
                x=x,
                y=y,
                tolerance=tolerance,
            )
            if sample == "degenerate":
                degenerate_count += 1
                continue
            if sample is None:
                continue

            z, confidence = sample
            return TinSampleResult(
                surface_ref=resolved_ref,
                x=x,
                y=y,
                z=z,
                found=True,
                status="ok",
                face_id=triangle.triangle_id,
                confidence=confidence,
                notes="TIN XY sample resolved from triangle interpolation.",
            )

        return TinSampleResult(
            surface_ref=resolved_ref,
            x=x,
            y=y,
            status="no_hit",
            notes=self._no_hit_notes(degenerate_count),
        )

    def sample_station_offset(
        self,
        *,
        surface: TINSurface | None = None,
        surface_ref: str = "",
        station: float,
        offset: float,
        station_offset_to_xy=None,
    ) -> TinSampleResult:
        """Sample elevation using station/offset through an explicit adapter."""

        resolved_ref = surface_ref or (surface.surface_id if surface is not None else "")
        if station_offset_to_xy is None:
            return TinSampleResult(
                surface_ref=resolved_ref,
                x=station,
                y=offset,
                status="error",
                query_kind="station_offset",
                notes="Station/offset sampling requires an explicit station_offset_to_xy adapter.",
            )

        try:
            x, y = station_offset_to_xy(station, offset)
        except Exception as exc:
            return TinSampleResult(
                surface_ref=resolved_ref,
                x=station,
                y=offset,
                status="error",
                query_kind="station_offset",
                notes=f"Station/offset adapter failed: {exc}",
            )

        result = self.sample_xy(
            surface=surface,
            surface_ref=resolved_ref,
            x=float(x),
            y=float(y),
        )

        return TinSampleResult(
            surface_ref=result.surface_ref,
            x=result.x,
            y=result.y,
            z=result.z,
            found=result.found,
            status=result.status,
            face_id=result.face_id,
            confidence=result.confidence,
            query_kind="station_offset",
            notes=result.notes,
        )

    def station_offset_adapter_from_rows(self, station_rows):
        """Build a station/offset adapter from evaluated station XY rows."""

        rows = self._normalized_station_rows(station_rows)
        if not rows:
            raise ValueError("At least one evaluated station row is required.")

        def _adapter(station: float, offset: float) -> tuple[float, float]:
            return self._station_offset_to_xy_from_rows(rows, float(station), float(offset))

        return _adapter

    @staticmethod
    def _triangle_vertices(
        vertices: dict[str, TINVertex],
        triangle: TINTriangle,
    ) -> tuple[TINVertex, TINVertex, TINVertex] | None:
        try:
            return vertices[triangle.v1], vertices[triangle.v2], vertices[triangle.v3]
        except KeyError:
            return None

    @staticmethod
    def _sample_triangle(
        *,
        triangle: TINTriangle,
        vertices: tuple[TINVertex, TINVertex, TINVertex],
        x: float,
        y: float,
        tolerance: float,
    ) -> tuple[float, float] | str | None:
        del triangle
        a, b, c = vertices
        denominator = (
            (b.y - c.y) * (a.x - c.x)
            + (c.x - b.x) * (a.y - c.y)
        )
        if abs(denominator) <= tolerance:
            return "degenerate"

        w1 = ((b.y - c.y) * (x - c.x) + (c.x - b.x) * (y - c.y)) / denominator
        w2 = ((c.y - a.y) * (x - c.x) + (a.x - c.x) * (y - c.y)) / denominator
        w3 = 1.0 - w1 - w2
        if min(w1, w2, w3) < -tolerance:
            return None

        z = w1 * a.z + w2 * b.z + w3 * c.z
        edge_distance = min(max(w1, 0.0), max(w2, 0.0), max(w3, 0.0))
        confidence = max(0.5, min(1.0, 0.75 + edge_distance))
        return z, confidence

    @staticmethod
    def _no_hit_notes(degenerate_count: int) -> str:
        if degenerate_count:
            return f"No containing TIN triangle found; skipped {degenerate_count} degenerate triangle(s)."
        return "No containing TIN triangle found."

    @staticmethod
    def _normalized_station_rows(station_rows) -> list[dict[str, float]]:
        rows: list[dict[str, float]] = []
        for row in list(station_rows or []):
            try:
                if isinstance(row, dict):
                    station = row.get("station", None)
                    x = row.get("x", None)
                    y = row.get("y", None)
                else:
                    station = getattr(row, "station", None)
                    x = getattr(row, "x", None)
                    y = getattr(row, "y", None)
                if station is None or x is None or y is None:
                    continue
                rows.append({"station": float(station), "x": float(x), "y": float(y)})
            except Exception:
                continue
        return sorted(rows, key=lambda item: item["station"])

    def _station_offset_to_xy_from_rows(
        self,
        rows: list[dict[str, float]],
        station: float,
        offset: float,
    ) -> tuple[float, float]:
        if len(rows) == 1:
            if abs(float(offset)) > 1e-9:
                raise ValueError("At least two station rows are required when offset is non-zero.")
            return rows[0]["x"], rows[0]["y"]

        before, after = self._bracketing_station_rows(rows, station)
        station_delta = after["station"] - before["station"]
        if abs(station_delta) <= 1e-12:
            ratio = 0.0
        else:
            ratio = (float(station) - before["station"]) / station_delta

        base_x = before["x"] + (after["x"] - before["x"]) * ratio
        base_y = before["y"] + (after["y"] - before["y"]) * ratio
        tangent_x = after["x"] - before["x"]
        tangent_y = after["y"] - before["y"]
        tangent_length = (tangent_x * tangent_x + tangent_y * tangent_y) ** 0.5
        if tangent_length <= 1e-12:
            raise ValueError("Station rows do not define a usable tangent.")

        normal_x = -tangent_y / tangent_length
        normal_y = tangent_x / tangent_length
        return base_x + float(offset) * normal_x, base_y + float(offset) * normal_y

    @staticmethod
    def _bracketing_station_rows(
        rows: list[dict[str, float]],
        station: float,
    ) -> tuple[dict[str, float], dict[str, float]]:
        if station <= rows[0]["station"]:
            return rows[0], rows[1]
        if station >= rows[-1]["station"]:
            return rows[-2], rows[-1]
        for index in range(len(rows) - 1):
            before = rows[index]
            after = rows[index + 1]
            if before["station"] <= station <= after["station"]:
                return before, after
        return rows[-2], rows[-1]
