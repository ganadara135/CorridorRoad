"""3D Centerline result contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Centerline3DPointRow:
    """One evaluated station point on the 3D centerline baseline."""

    station: float
    x: float
    y: float
    z: float
    grade: float = 0.0
    source_alignment_ref: str = ""
    source_profile_ref: str = ""
    source_station_ref: str = ""
    status: str = "ok"
    diagnostic_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Centerline3DResult:
    """Read-only result for the shared station/offset/elevation baseline."""

    schema_version: int = 1
    project_id: str = "corridorroad-v1"
    centerline3d_result_id: str = "centerline3d:main"
    alignment_id: str = ""
    profile_id: str = ""
    stationing_id: str = ""
    point_rows: tuple[Centerline3DPointRow, ...] = ()
    diagnostic_rows: tuple[str, ...] = ()
    status: str = "empty"
    source_refs: tuple[str, ...] = field(default_factory=tuple)

    @property
    def point_count(self) -> int:
        return len(self.point_rows)

    @property
    def station_start(self) -> float:
        if not self.point_rows:
            return 0.0
        return min(float(row.station) for row in self.point_rows)

    @property
    def station_end(self) -> float:
        if not self.point_rows:
            return 0.0
        return max(float(row.station) for row in self.point_rows)

    @property
    def elevation_min(self) -> float:
        if not self.point_rows:
            return 0.0
        return min(float(row.z) for row in self.point_rows)

    @property
    def elevation_max(self) -> float:
        if not self.point_rows:
            return 0.0
        return max(float(row.z) for row in self.point_rows)
