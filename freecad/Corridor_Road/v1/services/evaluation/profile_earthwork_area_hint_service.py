"""Profile-level earthwork area hints for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.output.profile_output import ProfileEarthworkRow, ProfileOutput


_DEPTH_TO_AREA_KIND = {
    "profile_cut_depth": "profile_cut_area",
    "profile_fill_depth": "profile_fill_area",
    "profile_balanced_depth": "profile_balanced_area",
}

_AREA_KINDS = set(_DEPTH_TO_AREA_KIND.values())


@dataclass(frozen=True)
class ProfileEarthworkAreaHintRow:
    """One station-level profile earthwork area hint."""

    station: float
    depth: float
    width: float
    area: float
    kind: str
    unit: str = "m2"


@dataclass(frozen=True)
class ProfileEarthworkAreaHintResult:
    """Depth-to-area profile earthwork hints."""

    rows: list[ProfileEarthworkAreaHintRow]
    status: str = "empty"
    notes: str = ""


class ProfileEarthworkAreaHintService:
    """Build early rectangular-equivalent cut/fill area hints from depth rows."""

    def build(
        self,
        profile_output: ProfileOutput,
        *,
        section_width: float | None = None,
        section_width_by_station: dict[float, float] | None = None,
    ) -> ProfileEarthworkAreaHintResult:
        """Convert profile cut/fill depths into area hints using explicit widths."""

        depth_rows = [
            row
            for row in list(getattr(profile_output, "earthwork_rows", []) or [])
            if str(getattr(row, "kind", "") or "") in _DEPTH_TO_AREA_KIND
        ]
        if not depth_rows:
            return ProfileEarthworkAreaHintResult(
                rows=[],
                status="missing_input",
                notes="Profile cut/fill depth rows are required before area hints can be generated.",
            )

        rows = []
        missing_width_count = 0
        for depth_row in depth_rows:
            station = float(getattr(depth_row, "station_start", 0.0) or 0.0)
            width = self._resolve_width(
                station,
                section_width=section_width,
                section_width_by_station=section_width_by_station,
            )
            if width is None or width <= 0.0:
                missing_width_count += 1
                continue

            kind = _DEPTH_TO_AREA_KIND[str(getattr(depth_row, "kind", "") or "")]
            depth = abs(float(getattr(depth_row, "value", 0.0) or 0.0))
            area = 0.0 if kind == "profile_balanced_area" else depth * width
            rows.append(
                ProfileEarthworkAreaHintRow(
                    station=station,
                    depth=depth,
                    width=width,
                    area=area,
                    kind=kind,
                )
            )

        if rows:
            return ProfileEarthworkAreaHintResult(
                rows=rows,
                status="ok",
                notes=self._overall_notes(rows, missing_width_count=missing_width_count),
            )
        return ProfileEarthworkAreaHintResult(
            rows=[],
            status="missing_width",
            notes="A positive section width is required to generate profile area hints.",
        )

    def to_profile_earthwork_rows(
        self,
        result: ProfileEarthworkAreaHintResult,
        *,
        row_id_prefix: str,
    ) -> list[ProfileEarthworkRow]:
        """Convert area hints into profile earthwork attachment rows."""

        return [
            ProfileEarthworkRow(
                earthwork_row_id=f"{row_id_prefix}:profile-earthwork-area-hint:{index}",
                kind=row.kind,
                station_start=row.station,
                station_end=row.station,
                value=row.area,
                unit=row.unit,
            )
            for index, row in enumerate(result.rows, start=1)
        ]

    @staticmethod
    def area_kinds() -> set[str]:
        """Return earthwork row kinds produced by this service."""

        return set(_AREA_KINDS)

    @staticmethod
    def _resolve_width(
        station: float,
        *,
        section_width: float | None,
        section_width_by_station: dict[float, float] | None,
    ) -> float | None:
        if section_width_by_station:
            rounded_station = round(station, 9)
            for key, value in section_width_by_station.items():
                try:
                    station_key = round(float(key), 9)
                    width_value = float(value)
                except Exception:
                    continue
                if station_key == rounded_station:
                    return width_value
        if section_width is None:
            return None
        try:
            return float(section_width)
        except Exception:
            return None

    @staticmethod
    def _overall_notes(
        rows: list[ProfileEarthworkAreaHintRow],
        *,
        missing_width_count: int,
    ) -> str:
        cut_count = sum(1 for row in rows if row.kind == "profile_cut_area")
        fill_count = sum(1 for row in rows if row.kind == "profile_fill_area")
        notes = f"Generated {len(rows)} profile earthwork area hints: cut={cut_count}, fill={fill_count}."
        if missing_width_count:
            notes += f" Skipped {missing_width_count} rows without positive section width."
        return notes
