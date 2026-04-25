"""Profile-level EG/FG earthwork hints for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.output.profile_output import ProfileEarthworkRow, ProfileLineRow, ProfileOutput


@dataclass(frozen=True)
class ProfileEarthworkHintRow:
    """One station-level profile earthwork hint."""

    station: float
    existing_ground_elevation: float
    finished_grade_elevation: float
    delta: float
    kind: str
    unit: str = "m"


@dataclass(frozen=True)
class ProfileEarthworkHintResult:
    """EG/FG comparison hints derived from profile line rows."""

    rows: list[ProfileEarthworkHintRow]
    status: str = "empty"
    notes: str = ""


class ProfileEarthworkHintService:
    """Build lightweight cut/fill depth hints from profile output lines."""

    def build(
        self,
        profile_output: ProfileOutput,
        *,
        tolerance: float = 1e-9,
    ) -> ProfileEarthworkHintResult:
        """Compare EG and FG profile lines at EG sampled stations."""

        fg_line = self._first_line(profile_output, {"finished_grade", "finished_grade_line"})
        eg_line = self._first_line(profile_output, {"existing_ground_line"})
        if fg_line is None or eg_line is None:
            return ProfileEarthworkHintResult(
                rows=[],
                status="missing_input",
                notes="Both finished grade and existing ground profile lines are required.",
            )

        fg_points = self._line_points(fg_line)
        eg_points = self._line_points(eg_line)
        if len(fg_points) < 2 or not eg_points:
            return ProfileEarthworkHintResult(
                rows=[],
                status="missing_input",
                notes="Profile earthwork hints require at least two FG points and one EG point.",
            )

        rows = []
        for station, eg_elevation in eg_points:
            fg_elevation = self._interpolate_line(fg_points, station)
            if fg_elevation is None:
                continue
            delta = fg_elevation - eg_elevation
            rows.append(
                ProfileEarthworkHintRow(
                    station=station,
                    existing_ground_elevation=eg_elevation,
                    finished_grade_elevation=fg_elevation,
                    delta=delta,
                    kind=self._depth_kind(delta, tolerance=tolerance),
                )
            )

        return ProfileEarthworkHintResult(
            rows=rows,
            status="ok" if rows else "empty",
            notes=self._overall_notes(rows),
        )

    def to_profile_earthwork_rows(
        self,
        result: ProfileEarthworkHintResult,
        *,
        row_id_prefix: str,
    ) -> list[ProfileEarthworkRow]:
        """Convert comparison hints into profile earthwork attachment rows."""

        return [
            ProfileEarthworkRow(
                earthwork_row_id=f"{row_id_prefix}:profile-earthwork-hint:{index}",
                kind=row.kind,
                station_start=row.station,
                station_end=row.station,
                value=abs(row.delta),
                unit=row.unit,
            )
            for index, row in enumerate(result.rows, start=1)
        ]

    @staticmethod
    def _first_line(profile_output: ProfileOutput, kinds: set[str]) -> ProfileLineRow | None:
        for row in list(getattr(profile_output, "line_rows", []) or []):
            kind = str(getattr(row, "kind", "") or "").strip()
            style_role = str(getattr(row, "style_role", "") or "").strip()
            if kind in kinds or style_role in kinds:
                return row
        return None

    @staticmethod
    def _line_points(line: ProfileLineRow) -> list[tuple[float, float]]:
        stations = [float(value) for value in list(getattr(line, "station_values", []) or [])]
        elevations = [float(value) for value in list(getattr(line, "elevation_values", []) or [])]
        count = min(len(stations), len(elevations))
        return sorted(zip(stations[:count], elevations[:count]), key=lambda row: row[0])

    @staticmethod
    def _interpolate_line(points: list[tuple[float, float]], station: float) -> float | None:
        if not points:
            return None
        if station < points[0][0] - 1e-9 or station > points[-1][0] + 1e-9:
            return None
        for index in range(len(points) - 1):
            station0, elevation0 = points[index]
            station1, elevation1 = points[index + 1]
            if abs(station1 - station0) <= 1e-12:
                continue
            if station0 - 1e-9 <= station <= station1 + 1e-9:
                ratio = (station - station0) / (station1 - station0)
                return elevation0 + (elevation1 - elevation0) * ratio
        if abs(station - points[-1][0]) <= 1e-9:
            return points[-1][1]
        return None

    @staticmethod
    def _depth_kind(delta: float, *, tolerance: float) -> str:
        if delta > tolerance:
            return "profile_fill_depth"
        if delta < -tolerance:
            return "profile_cut_depth"
        return "profile_balanced_depth"

    @staticmethod
    def _overall_notes(rows: list[ProfileEarthworkHintRow]) -> str:
        if not rows:
            return "No profile earthwork hint rows were generated."
        cut_count = sum(1 for row in rows if row.kind == "profile_cut_depth")
        fill_count = sum(1 for row in rows if row.kind == "profile_fill_depth")
        return f"Generated {len(rows)} profile earthwork hints: cut={cut_count}, fill={fill_count}."
