"""Side-slope bench row parsing for v1 Subassembly definitions."""

from __future__ import annotations

import ast
import json
import math
from dataclasses import dataclass, field

from ...common.diagnostics import DiagnosticMessage


@dataclass(frozen=True)
class ParsedBenchRow:
    """Typed side-slope bench row."""

    row_id: str
    drop: float
    width: float
    slope: float
    post_slope: float
    label: str = ""


@dataclass
class BenchRowParseResult:
    """Parsed bench rows plus validation diagnostics."""

    rows: list[ParsedBenchRow] = field(default_factory=list)
    diagnostic_rows: list[DiagnosticMessage] = field(default_factory=list)

    @property
    def status(self) -> str:
        if any(row.severity == "error" for row in self.diagnostic_rows):
            return "error"
        if any(row.severity == "warning" for row in self.diagnostic_rows):
            return "warning"
        return "ok"


def parse_bench_rows(value: object, *, source_id: str = "bench_rows") -> BenchRowParseResult:
    """Parse compact or structured side-slope bench rows."""

    diagnostics: list[DiagnosticMessage] = []
    raw_rows = _raw_rows(value, source_id=source_id, diagnostics=diagnostics)
    rows: list[ParsedBenchRow] = []
    for index, raw in enumerate(raw_rows, start=1):
        row = _row_dict(raw)
        if row is None:
            diagnostics.append(
                _diagnostic(
                    "error",
                    "invalid_bench_row",
                    "Bench row must be a dict or four values: drop,width,slope,post_slope.",
                    source_id,
                    index,
                )
            )
            continue
        parsed = _parsed_row(row, source_id=source_id, index=index, diagnostics=diagnostics)
        if parsed is not None:
            rows.append(parsed)
    return BenchRowParseResult(rows=rows, diagnostic_rows=diagnostics)


def bench_rows_to_dicts(rows: list[ParsedBenchRow]) -> list[dict[str, object]]:
    """Convert parsed bench rows to serializable dict rows."""

    output: list[dict[str, object]] = []
    for row in list(rows or []):
        data: dict[str, object] = {
            "row_id": row.row_id,
            "drop": row.drop,
            "width": row.width,
            "slope": row.slope,
            "post_slope": row.post_slope,
        }
        if row.label:
            data["label"] = row.label
        output.append(data)
    return output


def _raw_rows(value: object, *, source_id: str, diagnostics: list[DiagnosticMessage]) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    text = str(value or "").strip()
    if not text or text == "[]":
        return []
    parsed = _parse_literal(text)
    if parsed is not text:
        if isinstance(parsed, (list, tuple)):
            return list(parsed)
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="invalid_bench_rows_literal",
                message="bench_rows literal must evaluate to a list.",
                notes=f"source={source_id}; value={text}",
            )
        )
        return []
    return [part.strip() for part in text.split(";") if part.strip()]


def _parse_literal(text: str) -> object:
    stripped = str(text or "").strip()
    if not stripped:
        return text
    if not (stripped.startswith("[") or stripped.startswith("{")):
        return text
    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(stripped)
        except Exception:
            continue
    return text


def _row_dict(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, (list, tuple)):
        parts = list(value)
    else:
        parts = [part.strip() for part in str(value or "").split(",")]
    if len(parts) < 4:
        return None
    return {
        "drop": parts[0],
        "width": parts[1],
        "slope": parts[2],
        "post_slope": parts[3],
    }


def _parsed_row(
    row: dict[str, object],
    *,
    source_id: str,
    index: int,
    diagnostics: list[DiagnosticMessage],
) -> ParsedBenchRow | None:
    drop = _number(row.get("drop"))
    width = _number(row.get("width"))
    slope = _number(row.get("slope"))
    post_slope = _number(row.get("post_slope", row.get("post")))
    missing = [
        name
        for name, value in (
            ("drop", drop),
            ("width", width),
            ("slope", slope),
            ("post_slope", post_slope),
        )
        if value is None
    ]
    if missing:
        diagnostics.append(
            _diagnostic(
                "error",
                "invalid_bench_row_numeric_value",
                f"Bench row has non-numeric value(s): {', '.join(missing)}.",
                source_id,
                index,
            )
        )
        return None
    if drop < 0.0:
        diagnostics.append(
            _diagnostic("error", "invalid_bench_drop", "Bench row drop must be zero or positive.", source_id, index)
        )
    if width <= 0.0:
        diagnostics.append(_diagnostic("error", "invalid_bench_width", "Bench row width must be positive.", source_id, index))
    for name, value in (("slope", slope), ("post_slope", post_slope)):
        if not math.isfinite(value):
            diagnostics.append(
                _diagnostic("error", "invalid_bench_slope", f"Bench row {name} must be finite.", source_id, index)
            )
    if any(row.kind in {"invalid_bench_drop", "invalid_bench_width", "invalid_bench_slope"} for row in diagnostics):
        # Keep valid rows before this one; skip only the current row when it fails.
        if drop < 0.0 or width <= 0.0 or not math.isfinite(slope) or not math.isfinite(post_slope):
            return None
    row_id = str(row.get("row_id", "") or row.get("id", "") or "").strip() or f"bench:{index}"
    label = str(row.get("label", "") or "").strip()
    return ParsedBenchRow(
        row_id=row_id,
        drop=float(drop),
        width=float(width),
        slope=float(slope),
        post_slope=float(post_slope),
        label=label,
    )


def _number(value: object) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _diagnostic(severity: str, kind: str, message: str, source_id: str, index: int) -> DiagnosticMessage:
    return DiagnosticMessage(
        severity=severity,
        kind=kind,
        message=message,
        notes=f"source={source_id}; row={index}",
    )
