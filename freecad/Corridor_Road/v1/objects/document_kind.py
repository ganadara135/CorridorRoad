"""Document kind: a General Road document or an Intersection document.

The Project's `DocumentKind` decides which commands a document offers. A General Road document
holds exactly one Alignment and no Intersection; an Intersection document holds the roads of one
intersection. An empty kind restricts nothing, and the kind is never inferred from the content.
"""

from __future__ import annotations

from ...objects.obj_project import find_project
from ..services.editing.project_setup_service import (
    GENERAL_ROAD,
    INTERSECTION,
    normalize_document_kind,
)
from .obj_alignment import list_v1_alignments


GENERAL_ROAD_ALIGNMENT_REFUSAL = (
    "A General Road document holds one Alignment, and this document already has one. "
    "Edit that Alignment, or start a new document for another road."
)
GENERAL_ROAD_INTERSECTION_REFUSAL = (
    "Intersection Presets are not available in a General Road document. "
    "Start a new document and set its Document Kind to Intersection in Project Setup."
)


def document_kind(document) -> str:
    """The stored kind of the document's project: general_road, intersection, or ""."""

    project = find_project(document) if document is not None else None
    return normalize_document_kind(getattr(project, "DocumentKind", "")) if project is not None else ""


def is_general_road_document(document) -> bool:
    return document_kind(document) == GENERAL_ROAD


def is_intersection_document(document) -> bool:
    return document_kind(document) == INTERSECTION


def mark_intersection_document(document) -> None:
    """Make an unset document an Intersection document; refuse a General Road document."""

    if is_general_road_document(document):
        raise RuntimeError(GENERAL_ROAD_INTERSECTION_REFUSAL)
    project = find_project(document)
    if project is None or normalize_document_kind(getattr(project, "DocumentKind", "")):
        return
    if not hasattr(project, "DocumentKind"):
        project.addProperty("App::PropertyString", "DocumentKind", "CorridorRoad", "General Road or Intersection document")
    project.DocumentKind = INTERSECTION


def require_alignment_slot(document, alignment_ids=()) -> None:
    """Refuse an Alignment write that would leave a General Road document with two Alignments.

    `alignment_ids` are the ids about to be written; an id that already exists is an update. With
    no ids, the caller is about to create one new Alignment.
    """

    if not is_general_road_document(document):
        return
    existing = {str(getattr(obj, "AlignmentId", "") or "") for obj in list_v1_alignments(document)}
    incoming = {str(value or "") for value in alignment_ids} if alignment_ids else {None}
    if len(existing | incoming) > 1:
        raise RuntimeError(GENERAL_ROAD_ALIGNMENT_REFUSAL)


__all__ = [
    "GENERAL_ROAD_ALIGNMENT_REFUSAL",
    "GENERAL_ROAD_INTERSECTION_REFUSAL",
    "document_kind",
    "is_general_road_document",
    "is_intersection_document",
    "mark_intersection_document",
    "require_alignment_slot",
]
