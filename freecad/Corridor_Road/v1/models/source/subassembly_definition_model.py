"""Subassembly definition source model for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .assembly_model import normalize_subassembly_kind
from .base import SourceModelBase


SUBASSEMBLY_SIDE_BEHAVIORS = ("left", "right", "center", "both", "agnostic")
SUBASSEMBLY_TARGET_KINDS = (
    "terrain_daylight",
    "ditch_flowline",
    "curb_return_tie_in",
    "structure_port",
    "drainage_element",
)


@dataclass(frozen=True)
class SubassemblyParameterRow:
    """User-editable Subassembly definition parameter."""

    parameter_id: str
    label: str = ""
    value: object = ""
    unit: str = ""
    min_value: object = ""
    max_value: object = ""
    required: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameter_id", _text(self.parameter_id))
        object.__setattr__(self, "label", _text(self.label or self.parameter_id))
        object.__setattr__(self, "unit", _text(self.unit))
        object.__setattr__(self, "required", _bool(self.required))
        object.__setattr__(self, "notes", _text(self.notes))


@dataclass(frozen=True)
class SubassemblyPointRow:
    """Named point expression row in a reusable Subassembly definition."""

    point_id: str
    x_expr: str = "0.0"
    z_expr: str = "0.0"
    code: str = ""
    role: str = ""
    connectable: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "point_id", _text(self.point_id))
        object.__setattr__(self, "x_expr", _text(self.x_expr or "0.0"))
        object.__setattr__(self, "z_expr", _text(self.z_expr or "0.0"))
        object.__setattr__(self, "code", _text(self.code))
        object.__setattr__(self, "role", _text(self.role))
        object.__setattr__(self, "connectable", _bool(self.connectable))
        object.__setattr__(self, "notes", _text(self.notes))


@dataclass(frozen=True)
class SubassemblyLinkRow:
    """Point-to-point link row with downstream surface and quantity roles."""

    link_id: str
    start_point_ref: str
    end_point_ref: str
    surface_role: str = ""
    code: str = ""
    material: str = ""
    quantity_role: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "link_id", _text(self.link_id))
        object.__setattr__(self, "start_point_ref", _text(self.start_point_ref))
        object.__setattr__(self, "end_point_ref", _text(self.end_point_ref))
        object.__setattr__(self, "surface_role", normalize_surface_role(self.surface_role))
        object.__setattr__(self, "code", _text(self.code))
        object.__setattr__(self, "material", _text(self.material))
        object.__setattr__(self, "quantity_role", _text(self.quantity_role))
        object.__setattr__(self, "notes", _text(self.notes))


@dataclass(frozen=True)
class SubassemblyShapeRow:
    """Closed profile row for material, quantity, and solid output."""

    shape_id: str
    point_refs: tuple[str, ...] = field(default_factory=tuple)
    shape_code: str = ""
    material: str = ""
    quantity_role: str = ""
    solid_role: str = ""
    closed: bool = True
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "shape_id", _text(self.shape_id))
        object.__setattr__(self, "point_refs", _string_tuple(self.point_refs))
        object.__setattr__(self, "shape_code", _text(self.shape_code))
        object.__setattr__(self, "material", _text(self.material))
        object.__setattr__(self, "quantity_role", _text(self.quantity_role))
        object.__setattr__(self, "solid_role", _text(self.solid_role))
        object.__setattr__(self, "closed", _bool(self.closed))
        object.__setattr__(self, "notes", _text(self.notes))


@dataclass(frozen=True)
class SubassemblyTargetRow:
    """Optional external control target for a Subassembly definition."""

    target_id: str
    target_kind: str
    required: bool = False
    fallback_policy: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_id", _text(self.target_id))
        object.__setattr__(self, "target_kind", normalize_target_kind(self.target_kind))
        object.__setattr__(self, "required", _bool(self.required))
        object.__setattr__(self, "fallback_policy", _text(self.fallback_policy))
        object.__setattr__(self, "notes", _text(self.notes))


@dataclass(frozen=True)
class SubassemblyDefinition:
    """Reusable source definition authored by the SubAssembly Designer."""

    definition_id: str
    name: str = ""
    kind: str = "lane"
    category: str = ""
    side_behavior: str = "agnostic"
    parameter_rows: tuple[SubassemblyParameterRow, ...] = field(default_factory=tuple)
    point_rows: tuple[SubassemblyPointRow, ...] = field(default_factory=tuple)
    link_rows: tuple[SubassemblyLinkRow, ...] = field(default_factory=tuple)
    shape_rows: tuple[SubassemblyShapeRow, ...] = field(default_factory=tuple)
    target_rows: tuple[SubassemblyTargetRow, ...] = field(default_factory=tuple)
    enabled: bool = True
    notes: str = ""

    def __post_init__(self) -> None:
        definition_id = _text(self.definition_id)
        object.__setattr__(self, "definition_id", definition_id)
        object.__setattr__(self, "name", _text(self.name or definition_id or "Subassembly Definition"))
        object.__setattr__(self, "kind", normalize_subassembly_kind(self.kind))
        object.__setattr__(self, "category", _text(self.category))
        object.__setattr__(self, "side_behavior", normalize_side_behavior(self.side_behavior))
        object.__setattr__(self, "parameter_rows", tuple(self.parameter_rows or ()))
        object.__setattr__(self, "point_rows", tuple(self.point_rows or ()))
        object.__setattr__(self, "link_rows", tuple(self.link_rows or ()))
        object.__setattr__(self, "shape_rows", tuple(self.shape_rows or ()))
        object.__setattr__(self, "target_rows", tuple(self.target_rows or ()))
        object.__setattr__(self, "enabled", _bool(self.enabled))
        object.__setattr__(self, "notes", _text(self.notes))


@dataclass
class SubassemblyLibrary(SourceModelBase):
    """Durable source library of reusable Subassembly definitions."""

    library_id: str = ""
    preset_name: str = ""
    definition_rows: list[SubassemblyDefinition] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.library_id = _text(self.library_id or "subassembly-library:main")
        self.preset_name = _text(self.preset_name)
        self.definition_rows = list(self.definition_rows or [])

    def definition_by_id(self, definition_id: str) -> SubassemblyDefinition | None:
        """Return one definition by id."""

        target = _text(definition_id)
        for definition in self.definition_rows:
            if definition.definition_id == target:
                return definition
        return None


def normalize_side_behavior(value: object) -> str:
    """Normalize reusable Subassembly side behavior."""

    text = _text(value or "agnostic").lower().replace("-", "_").replace(" ", "_")
    if text in ("l", "lt"):
        return "left"
    if text in ("r", "rt"):
        return "right"
    if text in SUBASSEMBLY_SIDE_BEHAVIORS:
        return text
    return "agnostic"


def normalize_surface_role(value: object) -> str:
    """Normalize link surface roles while preserving future role names."""

    text = _text(value).lower().replace("-", "_").replace(" ", "_")
    if text == "finished_grade":
        return "design"
    if text == "daylight":
        return "slope_face"
    return text


def normalize_target_kind(value: object) -> str:
    """Normalize target kind while preserving unknown future kinds."""

    text = _text(value).lower().replace("-", "_").replace(" ", "_")
    return text or "terrain_daylight"


def _text(value: object) -> str:
    return str(value or "").strip()


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _string_tuple(values: object) -> tuple[str, ...]:
    if isinstance(values, str):
        raw_values = values.replace(";", ",").split(",")
    else:
        raw_values = list(values or [])
    return tuple(str(value or "").strip() for value in raw_values if str(value or "").strip())

