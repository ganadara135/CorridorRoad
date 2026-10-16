"""Document kind: a General Road document or an Intersection document.

The Project's `DocumentKind` decides which commands a document offers. A General Road document
holds exactly one Alignment and no Intersection; an Intersection document holds the roads of one
intersection. A project that stores no kind, made before the kind existed, is judged by its
content when read (`inferred_document_kind`); reading never writes the kind.
"""

from __future__ import annotations

from ...objects.obj_project import find_project
from ..services.editing.project_setup_service import (
    GENERAL_ROAD,
    INTERSECTION,
    inferred_document_kind,
    normalize_document_kind,
)
from .obj_alignment import list_v1_alignments


GENERAL_ROAD_ALIGNMENT_REFUSAL = (
    "A General Road document holds one Alignment, and this document already has one. "
    "Edit that Alignment, or start a new document for another road."
)
GENERAL_ROAD_INTERSECTION_REFUSAL = (
    "Intersection Presets are not available in a General Road document that already has its road. "
    "Start a new document for the intersection."
)


def document_kind(document) -> str:
    """The document's kind: the stored one, or the one its content gives."""

    project = find_project(document) if document is not None else None
    stored = normalize_document_kind(getattr(project, "DocumentKind", "")) if project is not None else ""
    if stored:
        return stored
    if document is None:
        return GENERAL_ROAD
    # Imported here: obj_intersection imports adapters that import this module.
    from .obj_intersection import find_v1_intersection_model

    return inferred_document_kind(
        has_intersection=find_v1_intersection_model(document) is not None,
        alignment_count=len(list_v1_alignments(document)),
    )


def is_general_road_document(document) -> bool:
    return document_kind(document) == GENERAL_ROAD


def is_intersection_document(document) -> bool:
    return document_kind(document) == INTERSECTION


def intersection_presets_available(document) -> bool:
    """Intersection Presets work in an Intersection document, and in a General Road document that
    has no road yet: its kind can still change."""

    return document is not None and (not is_general_road_document(document) or not list_v1_alignments(document))


def mark_intersection_document(document) -> None:
    """Make the document an Intersection document; refuse a General Road document with its road."""

    if not intersection_presets_available(document):
        raise RuntimeError(GENERAL_ROAD_INTERSECTION_REFUSAL)
    project = find_project(document)
    if project is None or normalize_document_kind(getattr(project, "DocumentKind", "")) == INTERSECTION:
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
    "intersection_presets_available",
    "is_general_road_document",
    "is_intersection_document",
    "mark_intersection_document",
    "require_alignment_slot",
]
