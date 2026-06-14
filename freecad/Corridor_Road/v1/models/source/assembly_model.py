"""Assembly source model for CorridorRoad v1."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field

from .base import SourceModelBase


ASSEMBLY_COMPONENT_KINDS = (
    "lane",
    "shoulder",
    "median",
    "curb",
    "gutter",
    "sidewalk",
    "bike_lane",
    "green_strip",
    "side_slope",
    "ditch",
    "barrier",
    "pavement_layer",
    "subbase",
    "structure_interface",
)

ASSEMBLY_COMPONENT_SIDES = ("left", "right", "center", "both")
ASSEMBLY_SUBASSEMBLY_KINDS = tuple(
    dict.fromkeys(
        ASSEMBLY_COMPONENT_KINDS
        + (
            "intersection_transition",
            "curb_return_transition",
        )
    )
)
ASSEMBLY_SUBASSEMBLY_SIDES = ASSEMBLY_COMPONENT_SIDES

ASSEMBLY_BENCH_MODES = ("none", "single", "rows")
ASSEMBLY_DAYLIGHT_MODES = ("off", "terrain", "fixed_width")
ASSEMBLY_BENCH_PARAMETER_KEYS = (
    "bench_mode",
    "bench_rows",
    "repeat_first_bench_to_daylight",
    "daylight_mode",
    "daylight_search_step",
    "daylight_max_width",
    "daylight_max_width_delta",
    "daylight_max_triangles",
    "cut_slope",
    "fill_slope",
)


@dataclass(frozen=True)
class TemplateComponent:
    """Deprecated legacy compatibility section component definition.

    New v1 authoring should use TemplateSubassembly. This row exists so old
    AssemblyModel data and transitional service fallbacks can still be read
    without treating component rows as active design state.
    """

    component_id: str
    kind: str
    component_index: int = 0
    side: str = "center"
    width: float = 0.0
    slope: float = 0.0
    thickness: float = 0.0
    material: str = ""
    target_ref: str = ""
    parameters: dict[str, object] = field(default_factory=dict)
    notes: str = ""
    enabled: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_id", str(self.component_id or "").strip())
        object.__setattr__(self, "kind", normalize_component_kind(self.kind))
        object.__setattr__(self, "side", normalize_component_side(self.side))
        object.__setattr__(self, "component_index", int(self.component_index or 0))
        object.__setattr__(self, "width", _float(self.width))
        object.__setattr__(self, "slope", _float(self.slope))
        object.__setattr__(self, "thickness", _float(self.thickness))
        object.__setattr__(self, "material", str(self.material or "").strip())
        object.__setattr__(self, "target_ref", str(self.target_ref or "").strip())
        object.__setattr__(self, "parameters", normalize_component_parameters(self.kind, self.parameters))
        object.__setattr__(self, "notes", str(self.notes or "").strip())


@dataclass(frozen=True)
class SectionTemplate:
    """Deprecated legacy compatibility section template definition.

    New v1 authoring should use SubassemblySectionTemplate. The component rows
    here are compatibility inputs only.
    """

    template_id: str
    template_kind: str
    template_index: int = 0
    label: str = ""
    component_rows: list[TemplateComponent] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "template_id", str(self.template_id or "").strip())
        object.__setattr__(self, "template_kind", str(self.template_kind or "roadway").strip() or "roadway")
        object.__setattr__(self, "template_index", int(self.template_index or 0))
        object.__setattr__(self, "label", str(self.label or self.template_id or "Assembly Template").strip())
        object.__setattr__(self, "component_rows", list(self.component_rows or []))
        object.__setattr__(self, "notes", str(self.notes or "").strip())


@dataclass
class AssemblyModel(SourceModelBase):
    """Deprecated component-based assembly source compatibility contract."""

    assembly_id: str = ""
    alignment_id: str = ""
    active_template_id: str = ""
    template_rows: list[SectionTemplate] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.assembly_id = str(self.assembly_id or "").strip()
        self.alignment_id = str(self.alignment_id or "").strip()
        self.template_rows = list(self.template_rows or [])
        if not str(self.active_template_id or "").strip() and self.template_rows:
            self.active_template_id = self.template_rows[0].template_id
        else:
            self.active_template_id = str(self.active_template_id or "").strip()


@dataclass(frozen=True)
class TemplateSubassembly:
    """Reusable v1 Subassembly definition.

    This is the durable source contract for assembly composition. Legacy
    TemplateComponent rows may be derived from it for compatibility, but the
    Subassembly row remains the active source of design intent.
    """

    subassembly_id: str
    kind: str
    subassembly_index: int = 0
    side: str = "center"
    width: float = 0.0
    slope: float = 0.0
    thickness: float = 0.0
    material: str = ""
    target_ref: str = ""
    parameters: dict[str, object] = field(default_factory=dict)
    point_code_rules: tuple[str, ...] = field(default_factory=tuple)
    link_code_rules: tuple[str, ...] = field(default_factory=tuple)
    shape_code_rules: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""
    enabled: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "subassembly_id", str(self.subassembly_id or "").strip())
        object.__setattr__(self, "kind", normalize_subassembly_kind(self.kind))
        object.__setattr__(self, "side", normalize_subassembly_side(self.side))
        object.__setattr__(self, "subassembly_index", int(self.subassembly_index or 0))
        object.__setattr__(self, "width", _float(self.width))
        object.__setattr__(self, "slope", _float(self.slope))
        object.__setattr__(self, "thickness", _float(self.thickness))
        object.__setattr__(self, "material", str(self.material or "").strip())
        object.__setattr__(self, "target_ref", str(self.target_ref or "").strip())
        object.__setattr__(self, "parameters", normalize_subassembly_parameters(self.kind, self.parameters))
        object.__setattr__(self, "point_code_rules", _string_tuple(self.point_code_rules))
        object.__setattr__(self, "link_code_rules", _string_tuple(self.link_code_rules))
        object.__setattr__(self, "shape_code_rules", _string_tuple(self.shape_code_rules))
        object.__setattr__(self, "notes", str(self.notes or "").strip())


@dataclass(frozen=True)
class SubassemblySectionTemplate:
    """Active v1 section template composed from TemplateSubassembly rows."""

    template_id: str
    template_kind: str
    template_index: int = 0
    label: str = ""
    subassembly_rows: list[TemplateSubassembly] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "template_id", str(self.template_id or "").strip())
        object.__setattr__(self, "template_kind", str(self.template_kind or "roadway").strip() or "roadway")
        object.__setattr__(self, "template_index", int(self.template_index or 0))
        object.__setattr__(self, "label", str(self.label or self.template_id or "Subassembly Template").strip())
        object.__setattr__(self, "subassembly_rows", list(self.subassembly_rows or []))
        object.__setattr__(self, "notes", str(self.notes or "").strip())


@dataclass
class AssemblySubassemblyModel(SourceModelBase):
    """Durable v1 assembly source model using explicit Subassembly rows."""

    assembly_id: str = ""
    alignment_id: str = ""
    active_template_id: str = ""
    template_rows: list[SubassemblySectionTemplate] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.assembly_id = str(self.assembly_id or "").strip()
        self.alignment_id = str(self.alignment_id or "").strip()
        self.template_rows = list(self.template_rows or [])
        if not str(self.active_template_id or "").strip() and self.template_rows:
            self.active_template_id = self.template_rows[0].template_id
        else:
            self.active_template_id = str(self.active_template_id or "").strip()


def normalize_component_kind(value: object) -> str:
    """Normalize component kind while preserving unknown future kinds as text."""

    text = str(value or "lane").strip().lower().replace(" ", "_").replace("-", "_")
    return text or "lane"


def normalize_component_side(value: object) -> str:
    """Normalize component side values used by Assembly editors and services."""

    text = str(value or "center").strip().lower().replace(" ", "_").replace("-", "_")
    if text in ("l", "lt"):
        return "left"
    if text in ("r", "rt"):
        return "right"
    if text in ASSEMBLY_COMPONENT_SIDES:
        return text
    return "center"


def normalize_subassembly_kind(value: object) -> str:
    """Normalize subassembly kind while preserving unknown future kinds."""

    text = normalize_component_kind(value)
    return text or "lane"


def normalize_subassembly_side(value: object) -> str:
    """Normalize subassembly side values."""

    return normalize_component_side(value)


def normalize_component_parameters(kind: object, parameters: dict[str, object] | None) -> dict[str, object]:
    """Normalize source component parameters while preserving future keys."""

    output = {str(key).strip(): value for key, value in dict(parameters or {}).items() if str(key).strip()}
    if normalize_component_kind(kind) != "side_slope":
        return output
    bench_mode = str(output.get("bench_mode", "") or "").strip().lower().replace("-", "_")
    bench_rows = normalize_bench_rows(output.get("bench_rows", []))
    if bench_rows:
        output["bench_rows"] = bench_rows
        output["bench_mode"] = bench_mode if bench_mode in ASSEMBLY_BENCH_MODES and bench_mode != "none" else "rows"
    elif bench_mode:
        output["bench_mode"] = bench_mode if bench_mode in ASSEMBLY_BENCH_MODES else bench_mode
    if "repeat_first_bench_to_daylight" in output:
        output["repeat_first_bench_to_daylight"] = _bool(output.get("repeat_first_bench_to_daylight"))
    return output


def normalize_subassembly_parameters(kind: object, parameters: dict[str, object] | None) -> dict[str, object]:
    """Normalize subassembly parameters while preserving future keys."""

    return normalize_component_parameters(kind, parameters)


def normalize_bench_rows(value: object) -> list[dict[str, object]]:
    """Return normalized side-slope bench rows from list or compact text."""

    raw_rows = _bench_raw_rows(value)
    rows: list[dict[str, object]] = []
    for index, raw in enumerate(raw_rows, start=1):
        row = _bench_row_dict(raw)
        if row is None:
            continue
        width = _float(row.get("width"), 0.0)
        if width <= 0.0:
            continue
        drop = max(_float(row.get("drop"), 0.0), 0.0)
        output = {
            "drop": drop,
            "width": width,
            "slope": _float(row.get("slope"), 0.0),
            "post_slope": _float(row.get("post_slope", row.get("post")), 0.0),
        }
        row_id = str(row.get("row_id", "") or row.get("id", "") or "").strip()
        label = str(row.get("label", "") or "").strip()
        output["row_id"] = row_id or f"bench:{index}"
        if label:
            output["label"] = label
        rows.append(output)
    return rows


def assembly_bench_validation_messages(component: TemplateComponent) -> list[str]:
    """Return warning strings for side-slope bench parameters."""

    if normalize_component_kind(getattr(component, "kind", "")) != "side_slope":
        return []
    params = dict(getattr(component, "parameters", {}) or {})
    messages: list[str] = []
    bench_mode = str(params.get("bench_mode", "") or "").strip().lower().replace("-", "_")
    if bench_mode and bench_mode not in ASSEMBLY_BENCH_MODES:
        messages.append(f"side_slope compatibility row {component.component_id} has unknown bench_mode {bench_mode}.")
    raw_rows_present = "bench_rows" in params and str(params.get("bench_rows", "") or "").strip() not in {"", "[]"}
    bench_rows = normalize_bench_rows(params.get("bench_rows", []))
    if raw_rows_present and not bench_rows:
        messages.append(f"side_slope compatibility row {component.component_id} has no valid bench_rows.")
    if bench_rows and float(getattr(component, "width", 0.0) or 0.0) <= 0.0:
        messages.append(f"side_slope compatibility row {component.component_id} has bench_rows but zero side-slope width.")
    if bench_rows and _bool(params.get("repeat_first_bench_to_daylight")):
        daylight_mode = str(params.get("daylight_mode", "") or "").strip().lower()
        max_width = _float(params.get("daylight_max_width", params.get("daylight_max_search_width")), 0.0)
        if daylight_mode and daylight_mode not in ASSEMBLY_DAYLIGHT_MODES:
            messages.append(f"side_slope compatibility row {component.component_id} has unknown daylight_mode {daylight_mode}.")
        if daylight_mode in {"", "none", "off"} or max_width <= 0.0:
            messages.append(
                f"side_slope compatibility row {component.component_id} repeats bench rows to daylight without daylight mode and max width."
            )
    return messages


def _compatibility_component_from_subassembly(subassembly: TemplateSubassembly) -> TemplateComponent:
    """Return a legacy validation proxy for shared side-slope bench checks."""

    return TemplateComponent(
        component_id=str(getattr(subassembly, "subassembly_id", "") or ""),
        kind=str(getattr(subassembly, "kind", "") or "side_slope"),
        component_index=int(getattr(subassembly, "subassembly_index", 0) or 0),
        side=str(getattr(subassembly, "side", "") or "center"),
        width=float(getattr(subassembly, "width", 0.0) or 0.0),
        slope=float(getattr(subassembly, "slope", 0.0) or 0.0),
        thickness=float(getattr(subassembly, "thickness", 0.0) or 0.0),
        material=str(getattr(subassembly, "material", "") or ""),
        target_ref=str(getattr(subassembly, "target_ref", "") or ""),
        parameters=dict(getattr(subassembly, "parameters", {}) or {}),
        notes=str(getattr(subassembly, "notes", "") or ""),
        enabled=bool(getattr(subassembly, "enabled", True)),
    )


def subassembly_bench_validation_messages(subassembly: TemplateSubassembly) -> list[str]:
    """Return warning strings for side-slope bench parameters on subassemblies."""

    if normalize_subassembly_kind(getattr(subassembly, "kind", "")) != "side_slope":
        return []
    proxy = _compatibility_component_from_subassembly(subassembly)
    return [
        message.replace("compatibility row", "subassembly")
        .replace("component", "subassembly")
        .replace(proxy.component_id, subassembly.subassembly_id)
        for message in assembly_bench_validation_messages(proxy)
    ]


def serialize_component_parameters(parameters: dict[str, object]) -> str:
    """Serialize component parameters for FreeCAD string-list storage."""

    tokens: list[str] = []
    for key, value in sorted(dict(parameters or {}).items()):
        key_text = str(key).strip()
        if not key_text:
            continue
        if isinstance(value, (dict, list, tuple, bool)):
            value_text = json.dumps(value, sort_keys=True, separators=(",", ":"))
        else:
            value_text = str(value)
        tokens.append(f"{key_text}={value_text}")
    return ";".join(tokens)


def parse_component_parameters(value: object) -> dict[str, object]:
    """Parse component parameters stored as key=value rows."""

    output: dict[str, object] = {}
    for token in str(value or "").split(";"):
        if "=" not in token:
            continue
        key, raw = token.split("=", 1)
        key = key.strip()
        if not key:
            continue
        output[key] = _parse_parameter_value(raw.strip())
    return output


def serialize_subassembly_parameters(parameters: dict[str, object]) -> str:
    """Serialize subassembly parameters for FreeCAD string-list storage."""

    return serialize_component_parameters(parameters)


def parse_subassembly_parameters(value: object) -> dict[str, object]:
    """Parse subassembly parameters stored as key=value rows."""

    return parse_component_parameters(value)


def serialize_code_rules(values: object) -> str:
    """Serialize point/link/shape code rules for compact FreeCAD storage."""

    return ";".join(_string_tuple(values))


def parse_code_rules(value: object) -> tuple[str, ...]:
    """Parse point/link/shape code rules from compact storage."""

    if isinstance(value, (list, tuple)):
        return _string_tuple(value)
    return tuple(part.strip() for part in str(value or "").split(";") if part.strip())


def _bench_raw_rows(value: object) -> list[object]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return [value]
    text = str(value or "").strip()
    if not text:
        return []
    parsed = _parse_parameter_value(text)
    if parsed is not text:
        return _bench_raw_rows(parsed)
    return [part.strip() for part in text.split("|") if part.strip()]


def _bench_row_dict(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return dict(value)
    text = str(value or "").strip()
    if not text:
        return None
    if "=" in text:
        output: dict[str, object] = {}
        for token in text.replace(",", ";").split(";"):
            if "=" not in token:
                continue
            key, raw = token.split("=", 1)
            key = key.strip()
            if key:
                output[key] = raw.strip()
        return output or None
    parts = [part.strip() for part in text.split(",")]
    if len(parts) < 2:
        return None
    return {
        "drop": parts[0],
        "width": parts[1],
        "slope": parts[2] if len(parts) > 2 else 0.0,
        "post_slope": parts[3] if len(parts) > 3 else 0.0,
    }


def _parse_parameter_value(value: str) -> object:
    text = str(value or "").strip()
    if not text:
        return ""
    if text[0] in "[{":
        for parser in (json.loads, ast.literal_eval):
            try:
                return parser(text)
            except Exception:
                pass
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    return text


def _float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def _string_tuple(values: object) -> tuple[str, ...]:
    if values is None:
        return tuple()
    if isinstance(values, str):
        raw_values = [part.strip() for part in values.split(";")]
    else:
        try:
            raw_values = list(values)
        except Exception:
            raw_values = [values]
    return tuple(str(value or "").strip() for value in raw_values if str(value or "").strip())
