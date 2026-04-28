"""Assembly source model for CorridorRoad v1."""

from __future__ import annotations

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


@dataclass(frozen=True)
class TemplateComponent:
    """Minimal reusable section component definition."""

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
        object.__setattr__(self, "notes", str(self.notes or "").strip())


@dataclass(frozen=True)
class SectionTemplate:
    """Minimal section template definition."""

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
    """Durable assembly and section-template source contract."""

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


def _float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)
