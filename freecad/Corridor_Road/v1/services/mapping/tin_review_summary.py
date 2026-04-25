"""TIN review summary helpers for CorridorRoad v1."""

from __future__ import annotations


def enrich_tin_review_preview(preview: dict[str, object]) -> dict[str, object]:
    """Attach derived TIN review fields to a preview payload."""

    result = dict(preview or {})
    surface = result.get("tin_surface")
    probe = dict(result.get("probe", {}) or {})
    extent = tin_extent(surface)
    source_label = tin_source_label(surface)
    extent_status = probe_extent_status(extent, probe)
    guidance = probe_guidance(extent, extent_status)

    result["tin_extent"] = extent
    result["tin_source"] = source_label
    result["probe_extent_status"] = extent_status
    result["probe_guidance"] = guidance
    result["summary_text"] = format_tin_review_summary(result)
    return result


def format_tin_review_summary(preview: dict[str, object]) -> str:
    """Format the common TIN review summary text."""

    surface = preview.get("tin_surface")
    result = preview.get("sample_result")
    probe = dict(preview.get("probe", {}) or {})
    extent = dict(preview.get("tin_extent", {}) or tin_extent(surface))
    source_label = str(preview.get("tin_source", "") or tin_source_label(surface))
    extent_status = str(
        preview.get("probe_extent_status", "")
        or probe_extent_status(extent, probe)
    )
    guidance = str(preview.get("probe_guidance", "") or probe_guidance(extent, extent_status))

    z_value = getattr(result, "z", None)
    z_text = "(none)" if z_value is None else f"{float(z_value):.3f}"
    found_text = "hit" if bool(getattr(result, "found", False)) else "no_hit"

    lines = [
        "CorridorRoad v1 TIN Review",
        f"Surface: {getattr(surface, 'label', '') or getattr(surface, 'surface_id', '') or '(missing)'}",
        f"Surface ID: {getattr(surface, 'surface_id', '') or '(missing)'}",
        f"Surface kind: {getattr(surface, 'surface_kind', '') or '(missing)'}",
        f"Source: {source_label or '(unknown)'}",
        f"Vertices: {len(list(getattr(surface, 'vertex_rows', []) or []))}",
        f"Triangles: {len(list(getattr(surface, 'triangle_rows', []) or []))}",
        f"Extents X: {_extent_text(extent, 'x_min')} -> {_extent_text(extent, 'x_max')}",
        f"Extents Y: {_extent_text(extent, 'y_min')} -> {_extent_text(extent, 'y_max')}",
        f"Extents Z: {_extent_text(extent, 'z_min')} -> {_extent_text(extent, 'z_max')}",
        f"Spacing X/Y: {_extent_text(extent, 'x_spacing')} / {_extent_text(extent, 'y_spacing')}",
        f"Boundaries: {len(list(getattr(surface, 'boundary_refs', []) or []))}",
        f"Voids: {len(list(getattr(surface, 'void_refs', []) or []))}",
        f"Quality rows: {len(list(getattr(surface, 'quality_rows', []) or []))}",
        f"Probe XY: {float(probe.get('x', 0.0) or 0.0):.3f}, {float(probe.get('y', 0.0) or 0.0):.3f}",
        f"Probe extent: {extent_status}",
        f"Probe result: {found_text}",
        f"Probe Z: {z_text}",
        f"Probe face: {getattr(result, 'face_id', '') or '(none)'}",
        f"Probe confidence: {float(getattr(result, 'confidence', 0.0) or 0.0):.3f}",
    ]
    mesh_preview = preview.get("mesh_preview")
    if mesh_preview is not None:
        lines.append(
            "Mesh preview: "
            f"{getattr(mesh_preview, 'status', '') or '(unknown)'}"
            f", object={getattr(mesh_preview, 'object_name', '') or '(none)'}"
            f", facets={int(getattr(mesh_preview, 'facet_count', 0) or 0)}"
        )
        mesh_notes = str(getattr(mesh_preview, "notes", "") or "").strip()
        if mesh_notes:
            lines.append(f"Mesh preview notes: {mesh_notes}")
    notes = str(getattr(result, "notes", "") or "").strip()
    if notes:
        lines.append(f"Probe notes: {notes}")
    if guidance:
        lines.append(f"Probe guidance: {guidance}")
    return "\n".join(lines)


def tin_quality_map(surface) -> dict[str, object]:
    """Return quality rows keyed by kind."""

    values: dict[str, object] = {}
    for row in list(getattr(surface, "quality_rows", []) or []):
        kind = str(getattr(row, "kind", "") or "").strip()
        if kind:
            values[kind] = getattr(row, "value", "")
    return values


def tin_extent(surface) -> dict[str, object]:
    """Resolve review extents from quality rows with vertex fallback."""

    quality = tin_quality_map(surface)
    extent = {
        "x_min": _float_or_none(quality.get("x_min")),
        "x_max": _float_or_none(quality.get("x_max")),
        "y_min": _float_or_none(quality.get("y_min")),
        "y_max": _float_or_none(quality.get("y_max")),
        "z_min": _float_or_none(quality.get("z_min")),
        "z_max": _float_or_none(quality.get("z_max")),
        "x_spacing": quality.get("x_spacing", ""),
        "y_spacing": quality.get("y_spacing", ""),
    }
    vertices = list(getattr(surface, "vertex_rows", []) or [])
    if vertices:
        if extent["x_min"] is None:
            extent["x_min"] = min(float(row.x) for row in vertices)
        if extent["x_max"] is None:
            extent["x_max"] = max(float(row.x) for row in vertices)
        if extent["y_min"] is None:
            extent["y_min"] = min(float(row.y) for row in vertices)
        if extent["y_max"] is None:
            extent["y_max"] = max(float(row.y) for row in vertices)
        if extent["z_min"] is None:
            extent["z_min"] = min(float(row.z) for row in vertices)
        if extent["z_max"] is None:
            extent["z_max"] = max(float(row.z) for row in vertices)
    return extent


def tin_source_label(surface) -> str:
    """Resolve a human-readable source label for a TIN surface."""

    source_refs = list(getattr(surface, "source_refs", []) or [])
    if source_refs:
        return str(source_refs[0] or "")
    for row in list(getattr(surface, "provenance_rows", []) or []):
        source_ref = str(getattr(row, "source_ref", "") or "").strip()
        if source_ref:
            return source_ref
    return ""


def probe_extent_status(extent: dict[str, object], probe: dict[str, object]) -> str:
    """Return whether the probe XY is inside the known TIN extent."""

    x_min = _float_or_none(extent.get("x_min"))
    x_max = _float_or_none(extent.get("x_max"))
    y_min = _float_or_none(extent.get("y_min"))
    y_max = _float_or_none(extent.get("y_max"))
    if None in (x_min, x_max, y_min, y_max):
        return "extent_unknown"
    x = _float_or_none(probe.get("x"))
    y = _float_or_none(probe.get("y"))
    if x is None or y is None:
        return "probe_invalid"
    if x_min <= x <= x_max and y_min <= y <= y_max:
        return "inside_extent"
    return "outside_extent"


def probe_guidance(extent: dict[str, object], extent_status: str) -> str:
    """Return optional guidance for the current probe state."""

    if extent_status != "outside_extent":
        return ""
    return (
        "Probe XY is outside the TIN extents; use "
        f"X {_extent_text(extent, 'x_min')}..{_extent_text(extent, 'x_max')} and "
        f"Y {_extent_text(extent, 'y_min')}..{_extent_text(extent, 'y_max')}."
    )


def _float_or_none(value) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _extent_text(extent: dict[str, object], key: str) -> str:
    value = extent.get(key, "")
    numeric = _float_or_none(value)
    if numeric is not None:
        return f"{numeric:.3f}"
    text = str(value or "").strip()
    return text or "(unknown)"
