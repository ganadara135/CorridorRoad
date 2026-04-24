"""Corridor result model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ResultModelBase


@dataclass(frozen=True)
class CorridorSamplingPolicy:
    """Minimal station sampling policy for one corridor result."""

    sampling_policy_id: str
    station_interval: float
    key_station_policy: str = "include"
    region_boundary_policy: str = "include"
    event_station_policy: str = "include"
    transition_density_policy: str = "adaptive"


@dataclass(frozen=True)
class CorridorStationRow:
    """Minimal corridor station row."""

    station_row_id: str
    station: float
    kind: str = "regular_sample"
    source_reason: str = ""


@dataclass(frozen=True)
class CorridorGeometryPackage:
    """Minimal geometry package reference for corridor-derived geometry."""

    geometry_package_id: str
    centerline_row_ids: list[str] = field(default_factory=list)
    section_link_row_ids: list[str] = field(default_factory=list)
    skeleton_row_ids: list[str] = field(default_factory=list)


@dataclass
class CorridorModel(ResultModelBase):
    """Derived orchestration model for corridor evaluation."""

    corridor_id: str = ""
    alignment_id: str = ""
    profile_id: str = ""
    superelevation_id: str = ""
    region_model_ref: str = ""
    sampling_policy: CorridorSamplingPolicy | None = None
    station_rows: list[CorridorStationRow] = field(default_factory=list)
    applied_section_set_ref: str = ""
    geometry_package: CorridorGeometryPackage | None = None
    surface_build_refs: list[str] = field(default_factory=list)
    solid_build_refs: list[str] = field(default_factory=list)
