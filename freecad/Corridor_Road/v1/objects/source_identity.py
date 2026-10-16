"""One source object per concern.

Readers pair Profile, Region, Stationing and Superelevation with their Alignment by
`AlignmentId`, and read Drainage as the project's single object. Two objects with the same
identity would leave one of them unread while an editor may write into it, so the build
refuses them instead of choosing one.
"""

from __future__ import annotations

from .obj_drainage import list_v1_drainage_models
from .obj_profile import list_v1_profiles
from .obj_region import list_v1_region_models
from .obj_stationing import list_v1_stationings
from .obj_superelevation import list_v1_superelevation_sources


ALIGNMENT_SCOPED_SOURCES = (
    ("Profile", list_v1_profiles),
    ("Regions", list_v1_region_models),
    ("Stations", list_v1_stationings),
    ("Superelevation", list_v1_superelevation_sources),
)
PROJECT_SCOPED_SOURCES = (("Drainage", list_v1_drainage_models),)


def duplicate_source_rows(document) -> list[dict[str, object]]:
    """Return one row for each source identity held by more than one object."""

    rows: list[dict[str, object]] = []
    for source_kind, list_objects in ALIGNMENT_SCOPED_SOURCES:
        by_alignment: dict[str, list[object]] = {}
        for obj in list_objects(document):
            alignment_id = str(getattr(obj, "AlignmentId", "") or "").strip()
            by_alignment.setdefault(alignment_id, []).append(obj)
        for alignment_id, objects in by_alignment.items():
            if len(objects) > 1:
                rows.append(_duplicate_row(source_kind, alignment_id, objects))
    for source_kind, list_objects in PROJECT_SCOPED_SOURCES:
        objects = list_objects(document)
        if len(objects) > 1:
            rows.append(_duplicate_row(source_kind, "", objects))
    return rows


def duplicate_source_text(row: dict[str, object]) -> str:
    """Describe one duplicate row for a status line or an error message."""

    scope = f" for {row['alignment_id']}" if row["alignment_id"] else ""
    return f"{row['source_kind']}{scope}: {', '.join(row['object_labels'])}"


def _duplicate_row(source_kind: str, alignment_id: str, objects: list[object]) -> dict[str, object]:
    return {
        "source_kind": source_kind,
        "alignment_id": alignment_id,
        "object_names": [str(getattr(obj, "Name", "") or "") for obj in objects],
        "object_labels": [str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "") for obj in objects],
    }
