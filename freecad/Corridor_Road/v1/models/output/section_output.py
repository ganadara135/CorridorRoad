"""Section output contract for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class SectionGeometryRow:
    """Minimal geometry row for section output."""

    row_id: str
    kind: str
    x_values: list[float] = field(default_factory=list)
    y_values: list[float] = field(default_factory=list)
    z_values: list[float] = field(default_factory=list)
    closed: bool = False
    style_role: str = ""
    source_ref: str = ""


@dataclass(frozen=True)
class SectionSubassemblyRow:
    """Minimal subassembly row for section output."""

    subassembly_row_id: str
    subassembly_id: str
    kind: str
    template_ref: str = ""
    definition_ref: str = ""
    assembly_ref: str = ""
    region_ref: str = ""
    side: str = ""
    parameters: dict[str, object] = field(default_factory=dict)
    notes: str = ""


@dataclass(frozen=True)
class SectionSubassemblyPointRow:
    """Output point row produced by a Subassembly."""

    point_row_id: str
    point_id: str
    subassembly_ref: str
    point_code: str
    lateral_offset: float = 0.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    side: str = ""
    target_ref: str = ""


@dataclass(frozen=True)
class SectionSubassemblyLinkRow:
    """Output link row produced by a Subassembly."""

    link_row_id: str
    link_id: str
    subassembly_ref: str
    start_point_ref: str
    end_point_ref: str
    link_code: str
    surface_role: str = ""
    material: str = ""


@dataclass(frozen=True)
class SectionSubassemblyShapeRow:
    """Output shape row produced by a Subassembly."""

    shape_row_id: str
    shape_id: str
    subassembly_ref: str
    point_refs: list[str] = field(default_factory=list)
    shape_code: str = ""
    material: str = ""
    thickness: float = 0.0
    solid_family: str = ""


@dataclass(frozen=True)
class SectionQuantityRow:
    """Minimal quantity row attached to section output."""

    quantity_row_id: str
    quantity_kind: str
    value: float
    unit: str
    subassembly_ref: str = ""


@dataclass(frozen=True)
class SectionSummaryRow:
    """Minimal summary row for section output."""

    summary_id: str
    kind: str
    label: str
    value: float | str
    unit: str = ""


@dataclass
class SectionOutput(OutputModelBase):
    """Normalized section output payload.

    subassembly_rows are the active section owner rows.
    """

    section_output_id: str = ""
    alignment_id: str = ""
    station: float = 0.0
    geometry_rows: list[SectionGeometryRow] = field(default_factory=list)
    subassembly_rows: list[SectionSubassemblyRow] = field(default_factory=list)
    subassembly_point_rows: list[SectionSubassemblyPointRow] = field(default_factory=list)
    subassembly_link_rows: list[SectionSubassemblyLinkRow] = field(default_factory=list)
    subassembly_shape_rows: list[SectionSubassemblyShapeRow] = field(default_factory=list)
    quantity_rows: list[SectionQuantityRow] = field(default_factory=list)
    summary_rows: list[SectionSummaryRow] = field(default_factory=list)
