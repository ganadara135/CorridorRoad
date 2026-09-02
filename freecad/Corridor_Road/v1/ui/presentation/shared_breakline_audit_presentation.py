"""Presentation mapping for typed shared-breakline audit results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class SharedBreaklineAuditPresentation:
    status: str
    missing_consumer_count: int
    mismatch_count: int
    geometry_match_count: int
    geometry_mismatch_count: int
    mesh_match_count: int
    mesh_mismatch_count: int
    reversed_edge_count: int
    solid_readiness_status: str
    solid_open_end_count: int
    solid_duplicate_edge_count: int
    solid_reversed_edge_count: int
    solid_non_manifold_node_count: int
    solid_readiness_notes: str
    notes: str
    summary: str
    note_rows: tuple[str, ...]


class SharedBreaklineAuditPresentationMapper:
    """Map typed or compatibility audit results into stable display fields."""

    def map(self, audit: object) -> SharedBreaklineAuditPresentation:
        status = str(_value(audit, "status", "") or "")
        geometry_match = int(_value(audit, "geometry_match_count", 0) or 0)
        geometry_mismatch = int(
            _value(audit, "geometry_mismatch_count", 0) or 0
        )
        mesh_match = int(_value(audit, "mesh_match_count", 0) or 0)
        mesh_mismatch = int(_value(audit, "mesh_mismatch_count", 0) or 0)
        missing = int(_value(audit, "missing_consumer_count", 0) or 0)
        mismatch = int(_value(audit, "mismatch_count", 0) or 0)
        reversed_count = int(_value(audit, "reversed_edge_count", 0) or 0)
        notes = str(_value(audit, "notes", "") or "")
        summary = (
            f"audit={status or 'unknown'} "
            f"geometry={geometry_match}/{geometry_match + geometry_mismatch} "
            f"mesh={mesh_match}/{mesh_match + mesh_mismatch} "
            f"missing={missing} mismatch={mismatch} reversed={reversed_count}"
        )
        return SharedBreaklineAuditPresentation(
            status=status,
            missing_consumer_count=missing,
            mismatch_count=mismatch,
            geometry_match_count=geometry_match,
            geometry_mismatch_count=geometry_mismatch,
            mesh_match_count=mesh_match,
            mesh_mismatch_count=mesh_mismatch,
            reversed_edge_count=reversed_count,
            solid_readiness_status=str(
                _value(audit, "solid_readiness_status", "") or ""
            ),
            solid_open_end_count=int(
                _value(audit, "solid_open_end_count", 0) or 0
            ),
            solid_duplicate_edge_count=int(
                _value(audit, "solid_duplicate_edge_count", 0) or 0
            ),
            solid_reversed_edge_count=int(
                _value(audit, "solid_reversed_edge_count", 0) or 0
            ),
            solid_non_manifold_node_count=int(
                _value(audit, "solid_non_manifold_node_count", 0) or 0
            ),
            solid_readiness_notes=str(
                _value(audit, "solid_readiness_notes", "") or ""
            ),
            notes=notes,
            summary=summary,
            note_rows=tuple(
                value.strip() for value in notes.split(";") if value.strip()
            ),
        )


def _value(source: object, name: str, default: object) -> object:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)
