"""Coordinate import policy for v1 CSV-based source data."""

from __future__ import annotations

from dataclasses import dataclass

from ....objects.obj_project import (
    get_coordinate_setup,
    get_coordinate_workflow,
    local_to_world,
    world_to_local,
)


@dataclass(frozen=True)
class CoordinateImportPolicy:
    """Resolved coordinate handling for external source rows."""

    input_coords: str = "Local"
    model_coords: str = "Local"
    workflow: str = "Local-first"
    epsg: str = ""
    project_origin_e: float = 0.0
    project_origin_n: float = 0.0
    project_origin_z: float = 0.0
    local_origin_x: float = 0.0
    local_origin_y: float = 0.0
    local_origin_z: float = 0.0
    north_rotation_deg: float = 0.0

    @property
    def transforms_to_local(self) -> bool:
        return self.input_coords == "World" and self.model_coords == "Local"

    def summary(self) -> str:
        if self.transforms_to_local:
            return "CSV coordinates: World E/N/Z -> Local X/Y/Z"
        return "CSV coordinates: Local X/Y/Z"


@dataclass(frozen=True)
class CoordinateExportPolicy:
    """Resolved coordinate handling for CSV export."""

    output_coords: str = "Local"
    model_coords: str = "Local"
    workflow: str = "Local-first"
    epsg: str = ""
    project_origin_e: float = 0.0
    project_origin_n: float = 0.0
    project_origin_z: float = 0.0
    local_origin_x: float = 0.0
    local_origin_y: float = 0.0
    local_origin_z: float = 0.0
    north_rotation_deg: float = 0.0

    @property
    def input_coords(self) -> str:
        """Compatibility alias: exported CSV rows become future input rows."""

        return self.output_coords

    @property
    def transforms_from_local(self) -> bool:
        return self.model_coords == "Local" and self.output_coords == "World"

    def summary(self) -> str:
        if self.transforms_from_local:
            return "Export coordinates: World E/N/Z"
        return "Export coordinates: Local X/Y/Z"

    def metadata(self) -> dict[str, object]:
        return {
            "input": self.output_coords,
            "model": self.model_coords,
            "workflow": self.workflow,
            "epsg": self.epsg,
            "project_origin_e": self.project_origin_e,
            "project_origin_n": self.project_origin_n,
            "project_origin_z": self.project_origin_z,
            "local_origin_x": self.local_origin_x,
            "local_origin_y": self.local_origin_y,
            "local_origin_z": self.local_origin_z,
            "north_rotation_deg": self.north_rotation_deg,
        }


def _setup_values(doc_or_project=None) -> tuple[dict[str, object], str]:
    setup = get_coordinate_setup(doc_or_project)
    workflow = get_coordinate_workflow(doc_or_project)
    return setup, workflow


def resolve_coordinate_import_policy(doc_or_project=None, input_coords: str = "auto") -> CoordinateImportPolicy:
    """Resolve whether incoming CSV coordinates are world or local."""

    setup, workflow = _setup_values(doc_or_project)
    requested = str(input_coords or "auto").strip().lower()
    if requested in ("world", "world-first", "e/n", "en", "easting/northing"):
        source_coords = "World"
    elif requested in ("local", "local-first", "x/y", "xy"):
        source_coords = "Local"
    else:
        source_coords = "World" if workflow == "World-first" else "Local"
    return CoordinateImportPolicy(
        input_coords=source_coords,
        model_coords="Local",
        workflow=str(workflow or "Local-first"),
        epsg=str(setup.get("CRSEPSG", "") or ""),
        project_origin_e=float(setup.get("ProjectOriginE", 0.0) or 0.0),
        project_origin_n=float(setup.get("ProjectOriginN", 0.0) or 0.0),
        project_origin_z=float(setup.get("ProjectOriginZ", 0.0) or 0.0),
        local_origin_x=float(setup.get("LocalOriginX", 0.0) or 0.0),
        local_origin_y=float(setup.get("LocalOriginY", 0.0) or 0.0),
        local_origin_z=float(setup.get("LocalOriginZ", 0.0) or 0.0),
        north_rotation_deg=float(setup.get("NorthRotationDeg", 0.0) or 0.0),
    )


def resolve_coordinate_export_policy(doc_or_project=None, output_coords: str = "project") -> CoordinateExportPolicy:
    """Resolve whether exported CSV coordinates should be world or local."""

    setup, workflow = _setup_values(doc_or_project)
    requested = str(output_coords or "project").strip().lower()
    if requested in ("world", "world-first", "e/n", "en", "easting/northing"):
        target_coords = "World"
    elif requested in ("local", "local-first", "x/y", "xy"):
        target_coords = "Local"
    else:
        target_coords = "World" if workflow == "World-first" else "Local"
    return CoordinateExportPolicy(
        output_coords=target_coords,
        model_coords="Local",
        workflow=str(workflow or "Local-first"),
        epsg=str(setup.get("CRSEPSG", "") or ""),
        project_origin_e=float(setup.get("ProjectOriginE", 0.0) or 0.0),
        project_origin_n=float(setup.get("ProjectOriginN", 0.0) or 0.0),
        project_origin_z=float(setup.get("ProjectOriginZ", 0.0) or 0.0),
        local_origin_x=float(setup.get("LocalOriginX", 0.0) or 0.0),
        local_origin_y=float(setup.get("LocalOriginY", 0.0) or 0.0),
        local_origin_z=float(setup.get("LocalOriginZ", 0.0) or 0.0),
        north_rotation_deg=float(setup.get("NorthRotationDeg", 0.0) or 0.0),
    )


def import_point_to_local(doc_or_project, x: float, y: float, z: float = 0.0, *, input_coords: str = "auto"):
    """Return one incoming CSV point in v1 internal Local X/Y/Z coordinates."""

    policy = resolve_coordinate_import_policy(doc_or_project, input_coords=input_coords)
    if policy.transforms_to_local:
        return world_to_local(doc_or_project, float(x), float(y), float(z))
    return float(x), float(y), float(z)


def point_rows_to_local(doc_or_project, rows, *, input_coords: str = "auto"):
    """Convert point-like rows with x/y/z attributes into local coordinate triples."""

    policy = resolve_coordinate_import_policy(doc_or_project, input_coords=input_coords)
    converted = []
    for row in list(rows or []):
        x = float(getattr(row, "x"))
        y = float(getattr(row, "y"))
        z = float(getattr(row, "z"))
        if policy.transforms_to_local:
            x, y, z = world_to_local(doc_or_project, x, y, z)
        converted.append((row, float(x), float(y), float(z)))
    return converted, policy


def alignment_rows_to_local(doc_or_project, rows, *, input_coords: str = "auto"):
    """Convert alignment PI rows into internal Local X/Y rows."""

    policy = resolve_coordinate_import_policy(doc_or_project, input_coords=input_coords)
    converted = []
    for row in list(rows or []):
        x = float(row[0])
        y = float(row[1])
        if policy.transforms_to_local:
            x, y, _z = world_to_local(doc_or_project, x, y, 0.0)
        converted.append((float(x), float(y), float(row[2]), float(row[3])))
    return converted, policy


def alignment_rows_from_local(doc_or_project, rows, *, output_coords: str = "auto"):
    """Convert internal Local alignment rows for CSV export."""

    policy = resolve_coordinate_export_policy(doc_or_project, output_coords=output_coords)
    converted = []
    for row in list(rows or []):
        x = float(row[0])
        y = float(row[1])
        if policy.transforms_from_local:
            x, y, _z = local_to_world(doc_or_project, x, y, 0.0)
        converted.append((float(x), float(y), float(row[2]), float(row[3])))
    return converted, policy
