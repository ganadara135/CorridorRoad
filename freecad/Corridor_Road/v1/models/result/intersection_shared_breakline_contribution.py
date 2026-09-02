"""Typed Intersection shared-breakline contribution result."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntersectionSharedBreaklineContributionResult:
    status: str
    intersection_id: str
    breakline_rows: tuple[object, ...] = ()
    point_rows: tuple[object, ...] = ()
    diagnostic_rows: tuple[str, ...] = ()
    completed_contributors: tuple[str, ...] = ()
