"""FreeCAD-independent XY geometry primitives for CorridorRoad v1."""

from __future__ import annotations


def xy_point(value: object) -> tuple[float, float]:
    """Normalize an object with x/y fields or a coordinate sequence to one XY pair."""

    if hasattr(value, "x") or hasattr(value, "y"):
        return (
            float(getattr(value, "x", 0.0) or 0.0),
            float(getattr(value, "y", 0.0) or 0.0),
        )
    try:
        sequence = tuple(value or ())
    except Exception:
        sequence = ()
    return (
        float(sequence[0]) if len(sequence) > 0 else 0.0,
        float(sequence[1]) if len(sequence) > 1 else 0.0,
    )
