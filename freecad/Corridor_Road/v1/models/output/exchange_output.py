"""Exchange output contract for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import OutputModelBase


@dataclass(frozen=True)
class ExchangeOutputRef:
    """Minimal output reference row for exchange output."""

    ref_id: str
    output_kind: str
    output_id: str
    schema_version: int


@dataclass
class ExchangeOutput(OutputModelBase):
    """Normalized exchange package contract."""

    exchange_output_id: str = ""
    format: str = ""
    package_kind: str = ""
    output_refs: list[ExchangeOutputRef] = field(default_factory=list)
    payload_metadata: dict[str, object] = field(default_factory=dict)
    format_payload: dict[str, object] = field(default_factory=dict)
