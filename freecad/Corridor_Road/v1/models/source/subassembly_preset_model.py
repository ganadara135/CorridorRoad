"""Subassembly preset integration source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .assembly_model import (
    TemplateSubassembly,
    normalize_parameter_overrides,
    normalize_subassembly_kind,
    normalize_subassembly_parameters,
    normalize_subassembly_side,
)
from .base import SourceModelBase
from .subassembly_definition_model import SubassemblyDefinition


SUBASSEMBLY_PRESET_STATUSES = (
    "linked",
    "modified",
    "snapshot",
    "preset_outdated",
    "missing_preset",
)

SUBASSEMBLY_SURFACE_ROLE_CONTRACT = {
    "lane": {
        "fg_surface": "design_surface",
        "subgrade_surface": "subgrade_surface",
    },
    "shoulder": {
        "fg_surface": "design_surface",
        "subgrade_surface": "subgrade_surface",
    },
    "ditch": {
        "ditch_surface": "drainage_surface",
    },
    "side_slope": {
        "side_slope_surface": "slope_face_surface",
        "bench_surface": "slope_face_surface",
        "daylight_marker": "slope_face_surface",
    },
}


@dataclass(frozen=True)
class SubassemblyPreset:
    """Reusable source preset for one Subassembly definition."""

    preset_id: str
    name: str = ""
    kind: str = "lane"
    version: str = "1"
    definition_ref: str = ""
    parameter_defaults: dict[str, object] = field(default_factory=dict)
    point_roles: dict[str, str] = field(default_factory=dict)
    link_roles: dict[str, str] = field(default_factory=dict)
    shape_roles: dict[str, str] = field(default_factory=dict)
    surface_roles: dict[str, str] = field(default_factory=dict)
    quantity_roles: dict[str, str] = field(default_factory=dict)
    target_specs: dict[str, str] = field(default_factory=dict)
    diagnostic_rules: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""

    def __post_init__(self) -> None:
        preset_id = _text(self.preset_id)
        kind = normalize_subassembly_kind(self.kind)
        object.__setattr__(self, "preset_id", preset_id)
        object.__setattr__(self, "name", _text(self.name or preset_id or "Subassembly Preset"))
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "version", _text(self.version or "1"))
        object.__setattr__(self, "definition_ref", _text(self.definition_ref))
        object.__setattr__(self, "parameter_defaults", normalize_subassembly_parameters(kind, self.parameter_defaults))
        object.__setattr__(self, "point_roles", _text_dict(self.point_roles))
        object.__setattr__(self, "link_roles", _text_dict(self.link_roles))
        object.__setattr__(self, "shape_roles", _text_dict(self.shape_roles))
        object.__setattr__(self, "surface_roles", _surface_role_dict(kind, self.surface_roles))
        object.__setattr__(self, "quantity_roles", _text_dict(self.quantity_roles))
        object.__setattr__(self, "target_specs", _text_dict(self.target_specs))
        object.__setattr__(self, "diagnostic_rules", _string_tuple(self.diagnostic_rules))
        object.__setattr__(self, "notes", _text(self.notes))

    @classmethod
    def from_definition(
        cls,
        definition: SubassemblyDefinition,
        *,
        preset_id: str = "",
        version: str = "1",
    ) -> "SubassemblyPreset":
        """Create a preset contract from a reusable Designer definition."""

        definition_id = _text(getattr(definition, "definition_id", ""))
        kind = normalize_subassembly_kind(getattr(definition, "kind", "lane"))
        return cls(
            preset_id=_text(preset_id or definition_id),
            name=_text(getattr(definition, "name", "") or definition_id),
            kind=kind,
            version=version,
            definition_ref=definition_id,
            parameter_defaults={
                row.parameter_id: row.value
                for row in tuple(getattr(definition, "parameter_rows", ()) or ())
                if _text(getattr(row, "parameter_id", ""))
            },
            point_roles={
                row.point_id: row.role
                for row in tuple(getattr(definition, "point_rows", ()) or ())
                if _text(getattr(row, "point_id", "")) and _text(getattr(row, "role", ""))
            },
            link_roles={
                row.link_id: row.surface_role
                for row in tuple(getattr(definition, "link_rows", ()) or ())
                if _text(getattr(row, "link_id", "")) and _text(getattr(row, "surface_role", ""))
            },
            shape_roles={
                row.shape_id: row.solid_role
                for row in tuple(getattr(definition, "shape_rows", ()) or ())
                if _text(getattr(row, "shape_id", "")) and _text(getattr(row, "solid_role", ""))
            },
            surface_roles=_surface_roles_from_definition(definition, kind=kind),
            quantity_roles={
                row.link_id: row.quantity_role
                for row in tuple(getattr(definition, "link_rows", ()) or ())
                if _text(getattr(row, "link_id", "")) and _text(getattr(row, "quantity_role", ""))
            },
            target_specs={
                row.target_id: _target_spec_text(row)
                for row in tuple(getattr(definition, "target_rows", ()) or ())
                if _text(getattr(row, "target_id", ""))
            },
            notes=_text(getattr(definition, "notes", "")),
        )


@dataclass(frozen=True)
class AssemblySubassemblyInstance:
    """Assembly placement of a preset-backed or custom Subassembly."""

    instance_id: str
    preset_ref: str = ""
    preset_version: str = ""
    kind: str = "lane"
    side: str = "center"
    station_range_ref: str = ""
    placement_order: int = 0
    width: float = 0.0
    slope: float = 0.0
    thickness: float = 0.0
    material: str = ""
    target_ref: str = ""
    definition_ref: str = ""
    overrides: dict[str, object] = field(default_factory=dict)
    parameters: dict[str, object] = field(default_factory=dict)
    status: str = "linked"
    locked: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        kind = normalize_subassembly_kind(self.kind)
        object.__setattr__(self, "instance_id", _text(self.instance_id))
        object.__setattr__(self, "preset_ref", _text(self.preset_ref))
        object.__setattr__(self, "preset_version", _text(self.preset_version))
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "side", normalize_subassembly_side(self.side))
        object.__setattr__(self, "station_range_ref", _text(self.station_range_ref))
        object.__setattr__(self, "placement_order", int(self.placement_order or 0))
        object.__setattr__(self, "width", _float(self.width))
        object.__setattr__(self, "slope", _float(self.slope))
        object.__setattr__(self, "thickness", _float(self.thickness))
        object.__setattr__(self, "material", _text(self.material))
        object.__setattr__(self, "target_ref", _text(self.target_ref))
        object.__setattr__(self, "definition_ref", _text(self.definition_ref))
        object.__setattr__(self, "overrides", normalize_parameter_overrides(self.overrides))
        object.__setattr__(self, "parameters", normalize_subassembly_parameters(kind, self.parameters))
        object.__setattr__(self, "status", normalize_subassembly_preset_status(self.status, has_preset=bool(_text(self.preset_ref))))
        object.__setattr__(self, "locked", _bool(self.locked))
        object.__setattr__(self, "notes", _text(self.notes))


@dataclass(frozen=True)
class AssemblyPreset:
    """Reusable Assembly preset composed from Subassembly instances."""

    preset_id: str
    name: str = ""
    version: str = "1"
    instance_rows: tuple[AssemblySubassemblyInstance, ...] = field(default_factory=tuple)
    layout_rules: dict[str, object] = field(default_factory=dict)
    notes: str = ""

    def __post_init__(self) -> None:
        preset_id = _text(self.preset_id)
        object.__setattr__(self, "preset_id", preset_id)
        object.__setattr__(self, "name", _text(self.name or preset_id or "Assembly Preset"))
        object.__setattr__(self, "version", _text(self.version or "1"))
        object.__setattr__(self, "instance_rows", tuple(self.instance_rows or ()))
        object.__setattr__(self, "layout_rules", dict(self.layout_rules or {}))
        object.__setattr__(self, "notes", _text(self.notes))


@dataclass
class SubassemblyPresetLibrary(SourceModelBase):
    """Project-level source library for Subassembly and Assembly presets."""

    library_id: str = ""
    subassembly_preset_rows: list[SubassemblyPreset] = field(default_factory=list)
    assembly_preset_rows: list[AssemblyPreset] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.library_id = _text(self.library_id or "subassembly-preset-library:main")
        self.subassembly_preset_rows = list(self.subassembly_preset_rows or [])
        self.assembly_preset_rows = list(self.assembly_preset_rows or [])

    def subassembly_preset_by_id(self, preset_id: str) -> SubassemblyPreset | None:
        """Return one Subassembly preset by id."""

        target = _text(preset_id)
        for preset in self.subassembly_preset_rows:
            if preset.preset_id == target:
                return preset
        return None

    def assembly_preset_by_id(self, preset_id: str) -> AssemblyPreset | None:
        """Return one Assembly preset by id."""

        target = _text(preset_id)
        for preset in self.assembly_preset_rows:
            if preset.preset_id == target:
                return preset
        return None


def normalize_subassembly_preset_status(value: object, *, has_preset: bool = True) -> str:
    """Normalize preset linkage status for Designer and Assembly display."""

    text = _text(value or "linked").lower().replace("-", "_").replace(" ", "_")
    if text in SUBASSEMBLY_PRESET_STATUSES:
        if text == "linked" and not has_preset:
            return "snapshot"
        return text
    return "linked" if has_preset else "snapshot"


def resolved_template_subassembly_from_instance(
    instance: AssemblySubassemblyInstance,
    preset: SubassemblyPreset | None = None,
    *,
    subassembly_id: str = "",
) -> TemplateSubassembly:
    """Resolve an Assembly instance into the existing TemplateSubassembly contract."""

    preset_parameters = dict(getattr(preset, "parameter_defaults", {}) or {}) if preset is not None else {}
    parameters = dict(preset_parameters)
    parameters.update(dict(getattr(instance, "parameters", {}) or {}))
    overrides = dict(getattr(instance, "overrides", {}) or {})
    parameters.update(overrides)
    preset_ref = _text(getattr(instance, "preset_ref", ""))
    preset_version = _text(getattr(instance, "preset_version", ""))
    preset_status = normalize_subassembly_preset_status(getattr(instance, "status", ""), has_preset=bool(preset_ref))
    if preset_ref and preset is None:
        preset_status = "missing_preset"
    elif preset is not None and preset_version and preset.version != preset_version:
        preset_status = "preset_outdated"
    elif preset_ref and overrides and preset_status == "linked":
        preset_status = "modified"
    return TemplateSubassembly(
        subassembly_id=_text(subassembly_id or instance.instance_id),
        kind=instance.kind,
        subassembly_index=instance.placement_order,
        side=instance.side,
        width=_value_from_override(instance, parameters, "width"),
        slope=_value_from_override(instance, parameters, "slope"),
        thickness=_value_from_override(instance, parameters, "thickness"),
        material=_text(parameters.get("material", instance.material or "")),
        target_ref=instance.target_ref,
        definition_ref=_text(instance.definition_ref or getattr(preset, "definition_ref", "")),
        preset_ref=preset_ref,
        preset_version=preset_version or _text(getattr(preset, "version", "")),
        preset_status=preset_status,
        source_instance_ref=instance.instance_id,
        parameter_overrides=overrides,
        parameters=parameters,
        notes=instance.notes,
        enabled=True,
    )


def subassembly_preset_library_from_definition_library(
    definition_library,
    *,
    library_id: str = "",
) -> SubassemblyPresetLibrary:
    """Create preset integration contracts from an existing Designer definition library."""

    return SubassemblyPresetLibrary(
        schema_version=getattr(definition_library, "schema_version", 1),
        project_id=getattr(definition_library, "project_id", "corridorroad-v1"),
        label=getattr(definition_library, "label", ""),
        library_id=library_id or "subassembly-preset-library:from-definitions",
        subassembly_preset_rows=[
            SubassemblyPreset.from_definition(definition)
            for definition in list(getattr(definition_library, "definition_rows", []) or [])
        ],
    )


def _surface_roles_from_definition(definition: SubassemblyDefinition, *, kind: str) -> dict[str, str]:
    roles = dict(SUBASSEMBLY_SURFACE_ROLE_CONTRACT.get(normalize_subassembly_kind(kind), {}))
    for link in tuple(getattr(definition, "link_rows", ()) or ()):
        surface_role = _text(getattr(link, "surface_role", ""))
        code = _text(getattr(link, "code", ""))
        if code and surface_role:
            roles[code] = surface_role
    return roles


def _target_spec_text(row) -> str:
    target_kind = _text(getattr(row, "target_kind", ""))
    required = "required" if _bool(getattr(row, "required", False)) else "optional"
    fallback_policy = _text(getattr(row, "fallback_policy", ""))
    return "|".join((target_kind, required, fallback_policy))


def _surface_role_dict(kind: str, values: object) -> dict[str, str]:
    roles = dict(SUBASSEMBLY_SURFACE_ROLE_CONTRACT.get(normalize_subassembly_kind(kind), {}))
    roles.update(_text_dict(values))
    return roles


def _value_from_override(instance: AssemblySubassemblyInstance, parameters: dict[str, object], key: str) -> float:
    value = parameters.get(key, getattr(instance, key, 0.0))
    return _float(value)


def _text(value: object) -> str:
    return str(value or "").strip()


def _text_dict(values: object) -> dict[str, str]:
    return {
        _text(key): _text(value)
        for key, value in dict(values or {}).items()
        if _text(key) and _text(value)
    }


def _string_tuple(values: object) -> tuple[str, ...]:
    if isinstance(values, str):
        raw_values = values.replace(";", ",").split(",")
    else:
        raw_values = list(values or [])
    return tuple(_text(value) for value in raw_values if _text(value))


def _float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return _text(value).lower() in {"1", "true", "yes", "y", "on"}
