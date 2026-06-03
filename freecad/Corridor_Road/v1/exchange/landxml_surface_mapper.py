"""Map Civil 3D LandXML TIN surface candidates into v1 surface outputs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..models.result.surface_model import SurfaceBuildRelation, SurfaceModel, SurfaceRow
from ..models.result.tin_surface import TINProvenanceRow, TINQualityRow, TINSurface, TINTriangle, TINVertex
from ..objects.obj_surface import create_or_update_v1_surface_model_object
from ..services.mapping.tin_mesh_preview_mapper import TINMeshPreviewMapper, TINMeshPreviewResult
from .landxml_import_contracts import LandXMLSurfaceCandidate


@dataclass(frozen=True)
class LandXMLSurfaceImportObjects:
    """Objects created or updated for one imported LandXML surface."""

    surface_model_object: object
    preview_result: TINMeshPreviewResult
    tin_surface: TINSurface


def tin_surface_from_landxml_candidate(
    candidate: LandXMLSurfaceCandidate,
    *,
    project_id: str = "corridorroad-v1",
) -> TINSurface:
    """Normalize one LandXML surface candidate into a TINSurface."""

    surface_id = _surface_id(candidate)
    vertices = [
        TINVertex(
            vertex_id=str(point.point_id),
            x=float(point.x),
            y=float(point.y),
            z=float(point.z),
            source_point_ref=f"landxml:{point.point_id}",
            notes=str(point.description or ""),
        )
        for point in candidate.points
    ]
    vertex_ids = {row.vertex_id for row in vertices}
    triangles: list[TINTriangle] = []
    skipped_faces = 0
    for index, face in enumerate(candidate.faces, start=1):
        if len(face) != 3 or any(str(vertex_id) not in vertex_ids for vertex_id in face):
            skipped_faces += 1
            continue
        triangles.append(
            TINTriangle(
                triangle_id=f"{surface_id}:tri:{index:06d}",
                v1=str(face[0]),
                v2=str(face[1]),
                v3=str(face[2]),
            )
        )
    return TINSurface(
        schema_version=1,
        project_id=str(project_id or "corridorroad-v1"),
        surface_id=surface_id,
        surface_kind="existing_ground_tin",
        label=str(candidate.name or candidate.surface_id or "LandXML Surface"),
        source_refs=[f"landxml:{candidate.surface_id or candidate.name}"],
        vertex_rows=vertices,
        triangle_rows=triangles,
        quality_rows=[
            TINQualityRow("quality:vertex-count", "vertex_count", len(vertices), "count"),
            TINQualityRow("quality:triangle-count", "triangle_count", len(triangles), "count"),
            TINQualityRow("quality:skipped-face-count", "skipped_face_count", skipped_faces, "count"),
        ],
        provenance_rows=[
            TINProvenanceRow(
                "provenance:landxml-civil3d",
                "landxml_civil3d_surface",
                str(candidate.surface_id or candidate.name or ""),
                "Imported from Autodesk Civil 3D LandXML surface points and faces.",
            )
        ],
    )


def surface_model_from_landxml_tin(
    surface: TINSurface,
    *,
    project_id: str = "corridorroad-v1",
) -> SurfaceModel:
    """Build a SurfaceModel summary for one imported TIN surface."""

    surface_ref = str(surface.surface_id or "tin:landxml-surface")
    return SurfaceModel(
        schema_version=1,
        project_id=str(project_id or surface.project_id or "corridorroad-v1"),
        surface_model_id=f"surface-model:{_slug(surface_ref)}",
        corridor_id="",
        label=str(surface.label or "LandXML Surface"),
        source_refs=list(surface.source_refs or []),
        surface_rows=[
            SurfaceRow(
                surface_id=surface_ref,
                surface_kind="existing_ground_tin",
                tin_ref=surface_ref,
                status="ready" if surface.triangle_rows else "empty",
            )
        ],
        build_relation_rows=[
            SurfaceBuildRelation(
                build_relation_id=f"{surface_ref}:landxml-import",
                surface_ref=surface_ref,
                relation_kind="landxml_import",
                input_refs=list(surface.source_refs or []),
                operation_summary="Imported Civil 3D LandXML TIN points and faces.",
            )
        ],
        span_rows=[],
    )


def create_or_update_surface_from_landxml_candidate(
    document,
    candidate: LandXMLSurfaceCandidate,
    *,
    project=None,
    create_preview: bool = True,
) -> LandXMLSurfaceImportObjects:
    """Create/update v1 surface summary and optional mesh preview from LandXML."""

    if document is None:
        raise RuntimeError("No active document is available for LandXML surface import.")
    project_id = _project_id(project)
    tin_surface = tin_surface_from_landxml_candidate(candidate, project_id=project_id)
    surface_model = surface_model_from_landxml_tin(tin_surface, project_id=project_id)
    object_name = _object_name(surface_model.surface_model_id)
    summary_obj = create_or_update_v1_surface_model_object(
        document=document,
        project=None,
        surface_model=surface_model,
        object_name=object_name,
        label=f"LandXML Surface - {tin_surface.label or tin_surface.surface_id}",
    )
    try:
        summary_obj.CRRecordKind = "tin_surface_result"
    except Exception:
        pass
    _route(project, summary_obj)

    preview_result = TINMeshPreviewResult(status="skipped", notes="Preview creation disabled.")
    if create_preview:
        preview_result = TINMeshPreviewMapper().create_or_update_preview_object(
            document,
            tin_surface,
            object_name=_object_name(f"TINPreview:{tin_surface.surface_id}"),
            label_prefix="LandXML TIN Preview",
            surface_role="base",
        )
        preview_obj = document.getObject(preview_result.object_name)
        _route(project, preview_obj)

    return LandXMLSurfaceImportObjects(
        surface_model_object=summary_obj,
        preview_result=preview_result,
        tin_surface=tin_surface,
    )


def _surface_id(candidate: LandXMLSurfaceCandidate) -> str:
    raw = candidate.surface_id or candidate.name or "landxml-surface"
    return f"tin:{_slug(raw)}"


def _slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.:-]+", "-", str(text or "").strip()).strip("-")
    return slug or "landxml-surface"


def _object_name(text: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", str(text or "").strip()).strip("_")
    return (safe or "LandXMLSurface")[:80]


def _project_id(project) -> str:
    if project is None:
        return "corridorroad-v1"
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _route(project, obj) -> None:
    if project is None or obj is None:
        return
    try:
        from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree

        route_to_v1_tree(project, obj)
    except Exception:
        pass
