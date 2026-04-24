"""Station-context helpers shared by v1 preview and existing v0 editors."""

from __future__ import annotations


def context_station_row(context: dict[str, object] | None) -> dict[str, object]:
    """Return one normalized station-row payload from a shared UI context."""

    payload = dict(context or {})
    row = payload.get("station_row", {})
    return dict(row or {})


def context_station_value(context: dict[str, object] | None) -> float | None:
    """Return the current context station value in meters when available."""

    row = context_station_row(context)
    try:
        return float(row.get("station", 0.0))
    except Exception:
        return None


def context_station_label(context: dict[str, object] | None, *, digits: int = 3) -> str:
    """Return one human-readable station label from a shared UI context."""

    row = context_station_row(context)
    label = str(row.get("label", "") or "").strip()
    if label:
        return label
    value = context_station_value(context)
    if value is None:
        return ""
    return f"STA {value:.{int(digits)}f}"


def nearest_value_index(values: list[float], target: float | None) -> int:
    """Return the nearest numeric row index for one station target."""

    if target is None:
        return -1
    filtered = [(index, float(value)) for index, value in enumerate(list(values or []))]
    if not filtered:
        return -1
    index, _value = min(filtered, key=lambda item: abs(item[1] - float(target)))
    return int(index)


def nearest_span_index(spans: list[tuple[float, float]], target: float | None) -> int:
    """Return the best-matching span index for one station target."""

    if target is None:
        return -1
    norm_spans: list[tuple[int, float, float]] = []
    for index, span in enumerate(list(spans or [])):
        try:
            start = float(span[0])
            end = float(span[1])
        except Exception:
            continue
        if end < start:
            start, end = end, start
        norm_spans.append((index, start, end))
    if not norm_spans:
        return -1

    containing = [
        item for item in norm_spans
        if item[1] - 1e-9 <= float(target) <= item[2] + 1e-9
    ]
    if containing:
        index, _start, _end = min(containing, key=lambda item: (item[2] - item[1], abs((item[1] + item[2]) * 0.5 - float(target))))
        return int(index)

    index, _start, _end = min(
        norm_spans,
        key=lambda item: abs(((item[1] + item[2]) * 0.5) - float(target)),
    )
    return int(index)
