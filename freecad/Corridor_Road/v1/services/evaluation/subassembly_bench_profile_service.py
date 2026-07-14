"""Deterministic side-slope bench profile evaluation for CorridorRoad v1."""

from __future__ import annotations

from ...models.result.subassembly_bench_profile import (
    BenchProfileSegment,
    SubassemblyBenchProfileResult,
)
from .subassembly_bench_row_parser import bench_rows_to_dicts, parse_bench_rows


class SubassemblyBenchProfileService:
    """Evaluate source bench rows into deterministic result-only profile segments."""

    def evaluate(self, row, *, total_width: float | None = None) -> SubassemblyBenchProfileResult:
        params = dict(getattr(row, "parameters", {}) or {})
        subassembly_id = str(getattr(row, "subassembly_id", "") or "side_slope")
        parse_result = parse_bench_rows(
            params.get("bench_rows", []),
            source_id=f"{subassembly_id}:bench_rows",
        )
        remaining = max(
            float(total_width if total_width is not None else getattr(row, "width", 0.0) or 0.0),
            0.0,
        )
        current_slope = float(getattr(row, "slope", 0.0) or 0.0)
        rows = bench_rows_to_dicts(parse_result.rows)
        diagnostics = tuple(parse_result.diagnostic_rows)
        if not rows:
            segments = ()
            if remaining > 1.0e-9:
                segments = (BenchProfileSegment("side_slope", remaining, current_slope),)
            return SubassemblyBenchProfileResult(segments, diagnostics)

        repeat = _truthy(params.get("repeat_first_bench_to_daylight"))
        source_rows = [rows[0]] if repeat else rows
        segments: list[BenchProfileSegment] = []

        def append_row(source_row: dict[str, object]) -> bool:
            nonlocal remaining, current_slope
            if remaining <= 1.0e-9:
                return False
            before = remaining
            drop = max(float(source_row.get("drop", 0.0) or 0.0), 0.0)
            pre_width = 0.0
            if drop > 1.0e-9 and abs(current_slope) > 1.0e-9:
                pre_width = min(remaining, drop / abs(current_slope))
            if pre_width > 1.0e-9:
                segments.append(BenchProfileSegment("side_slope", pre_width, current_slope))
                remaining = max(remaining - pre_width, 0.0)
            bench_width = min(max(float(source_row.get("width", 0.0) or 0.0), 0.0), remaining)
            if bench_width > 1.0e-9:
                segments.append(
                    BenchProfileSegment(
                        "bench",
                        bench_width,
                        float(source_row.get("slope", 0.0) or 0.0),
                    )
                )
                remaining = max(remaining - bench_width, 0.0)
            current_slope = float(source_row.get("post_slope", current_slope) or current_slope)
            return abs(before - remaining) > 1.0e-9

        if repeat and source_rows:
            guard = 0
            while remaining > 1.0e-9 and guard < 512:
                guard += 1
                if not append_row(source_rows[0]):
                    break
        else:
            for source_row in source_rows:
                if remaining <= 1.0e-9:
                    break
                append_row(source_row)
        if remaining > 1.0e-9:
            segments.append(BenchProfileSegment("side_slope", remaining, current_slope))
        return SubassemblyBenchProfileResult(tuple(segments), diagnostics)


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}
