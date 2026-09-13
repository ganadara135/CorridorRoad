"""Presentation rows for the Build Corridor Results tab review."""

from __future__ import annotations

from .review_text import join_review_notes as _join_review_notes


def roundabout_build_review_rows(
    intersection_obj,
    *,
    apron_obj,
    subgrade_obj,
    slope_face_obj,
) -> list[dict[str, object]]:
    """Return roundabout-specific Results tab rows from generated output contracts."""

    rows: list[dict[str, object]] = []

    rows.append(
        _corridor_roundabout_review_row(
            role="roundabout_circulatory",
            title="Roundabout Circulatory Surface",
            object_name="V1CorridorIntersectionSurfacePreview",
            obj=intersection_obj,
            notes=_join_review_notes(
                "roundabout annular circulatory surface",
                f"boundary={getattr(intersection_obj, 'PatchSurfaceBoundaryStrategy', '')}",
                f"triangulation={getattr(intersection_obj, 'PatchTriangulationMode', '')}",
            ),
        )
    )
    connector_obj = None
    if apron_obj is not None:
        rows.append(
            _corridor_roundabout_review_row(
                role="roundabout_apron",
                title="Roundabout Apron Surface",
                object_name="V1CorridorRoundaboutApronSurfacePreview",
                obj=apron_obj,
                notes=_join_review_notes(
                    "roundabout annular apron surface",
                    f"boundary={getattr(apron_obj, 'PatchSurfaceBoundaryStrategy', '')}",
                    f"triangulation={getattr(apron_obj, 'PatchTriangulationMode', '')}",
                ),
            )
        )
    if subgrade_obj is not None:
        rows.append(
            _corridor_roundabout_review_row(
                role="roundabout_subgrade",
                title="Roundabout Subgrade Surface",
                object_name="V1CorridorRoundaboutSubgradeSurfacePreview",
                obj=subgrade_obj,
                notes=_join_review_notes(
                    "roundabout dedicated subgrade surface",
                    f"boundary={getattr(subgrade_obj, 'PatchSurfaceBoundaryStrategy', '')}",
                    f"triangulation={getattr(subgrade_obj, 'PatchTriangulationMode', '')}",
                ),
            )
        )
    breakline_status = "ready"
    if any(
        int(getattr(candidate, "SharedBreaklineGeometryMismatchCount", 0) or 0)
        or int(getattr(candidate, "SharedBreaklineMeshMismatchCount", 0) or 0)
        or int(getattr(candidate, "SharedBreaklineMissingConsumerCount", 0) or 0)
        for candidate in (connector_obj, apron_obj, subgrade_obj, slope_face_obj)
        if candidate is not None
    ):
        breakline_status = "warning"
    if apron_obj is None or subgrade_obj is None or slope_face_obj is None:
        breakline_status = "missing"
    rows.append(
        {
            "role": "roundabout_breakline_readiness",
            "result": "Roundabout Breakline Readiness",
            "object_name": str(getattr(slope_face_obj, "Name", "") or ""),
            "object_label": str(getattr(slope_face_obj, "Label", "") or ""),
            "status": breakline_status,
            "vertex_count": "",
            "triangle_or_point_count": "",
            "output_path": "roundabout_shared_breakline_contract",
            "notes": _join_review_notes(
                f"apron={getattr(apron_obj, 'SharedBreaklineAuditStatus', '')}" if apron_obj is not None else "apron=missing",
                f"subgrade={getattr(subgrade_obj, 'SharedBreaklineAuditStatus', '')}" if subgrade_obj is not None else "subgrade=missing",
                f"slope_face={getattr(slope_face_obj, 'SharedBreaklineAuditStatus', '')}" if slope_face_obj is not None else "slope_face=missing",
                "entry/exit connector, splitter-island, transitional entry/exit, and generic tie-slope outputs are disabled for roundabout generalization",
                "Recommended Action: Review roundabout source policy and rebuild if any roundabout output is missing.",
            ),
        }
    )
    return rows


def _corridor_roundabout_review_row(
    *,
    role: str,
    title: str,
    object_name: str,
    obj,
    notes: str,
) -> dict[str, object]:
    vertex_count = int(getattr(obj, "VertexCount", 0) or 0) if obj is not None else 0
    triangle_count = int(getattr(obj, "TriangleCount", 0) or 0) if obj is not None else 0
    status = "ready" if vertex_count > 0 and triangle_count > 0 else "missing"
    return {
        "role": role,
        "result": title,
        "object_name": str(getattr(obj, "Name", "") or object_name),
        "object_label": str(getattr(obj, "Label", "") or ""),
        "status": status,
        "vertex_count": vertex_count if obj is not None else "",
        "triangle_or_point_count": triangle_count if obj is not None else "",
        "output_path": "roundabout_output_contract" if obj is not None else "",
        "notes": notes or ("Roundabout output has not been built yet." if obj is None else ""),
    }
