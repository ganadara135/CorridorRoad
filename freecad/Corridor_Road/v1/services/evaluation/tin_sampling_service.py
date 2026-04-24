"""TIN sampling service for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TinSampleResult:
    """Minimal TIN sample result used until full TIN contracts are wired in."""

    surface_ref: str
    x: float
    y: float
    z: float | None = None
    found: bool = False
    notes: str = ""


class TinSamplingService:
    """Provide a minimal query-oriented interface for future TIN sampling."""

    def sample_xy(
        self,
        *,
        surface_ref: str,
        x: float,
        y: float,
    ) -> TinSampleResult:
        """Return a placeholder XY sampling result for a named surface."""

        return TinSampleResult(
            surface_ref=surface_ref,
            x=x,
            y=y,
            z=None,
            found=False,
            notes="TIN sampling not implemented yet in the v1 code skeleton.",
        )

    def sample_station_offset(
        self,
        *,
        surface_ref: str,
        station: float,
        offset: float,
    ) -> TinSampleResult:
        """Return a placeholder station/offset sampling result."""

        return TinSampleResult(
            surface_ref=surface_ref,
            x=station,
            y=offset,
            z=None,
            found=False,
            notes="Station/offset TIN sampling not implemented yet in the v1 code skeleton.",
        )
