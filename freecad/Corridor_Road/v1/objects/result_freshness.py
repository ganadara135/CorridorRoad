"""Result freshness of a document: which stored results no longer match their inputs.

Reads the source and result objects of a document and fingerprints the inputs of each result
stage the way the stage records them when it is built (`stage_inputs.record_stage_inputs`).
Nothing here writes to the document: opening a panel or viewer that shows freshness changes no
fingerprint and no result.
"""

from __future__ import annotations

from ...objects.obj_project import find_project
from ..services.evaluation.result_freshness_service import (
    APPLIED_SECTIONS,
    BUILD_PARAMETRIC,
    CENTERLINE3D,
    STATIONING,
    StageFreshness,
    merge_stage_rows,
    stage_freshness,
)
from .obj_alignment import find_v1_alignment, list_v1_alignments, to_alignment_model
from .obj_applied_section import find_v1_applied_section_set
from .obj_centerline3d import centerline3d_result_fingerprint, find_v1_centerline3d_object
from .obj_corridor import find_v1_corridor_model
from .obj_drainage import find_v1_drainage_model, to_drainage_model
from .obj_intersection import find_v1_intersection_model, stored_intersection_spec, to_intersection_model
from .obj_profile import list_v1_profiles, to_profile_model
from .obj_region import list_v1_region_models, to_region_model
from .obj_stationing import list_v1_stationings
from .obj_structure import find_v1_structure_model, to_structure_model
from .obj_subassembly_assembly import list_v1_assembly_subassembly_models, to_assembly_subassembly_model
from .obj_subassembly_library import list_v1_subassembly_libraries, to_subassembly_library
from .obj_subassembly_preset_library import list_v1_subassembly_preset_libraries, to_subassembly_preset_library
from .obj_superelevation import list_v1_superelevation_sources, to_superelevation_model
from .obj_surface_transition import find_v1_surface_transition_model, to_surface_transition_model
from .persistence_payload_adapter import PAYLOAD_PROPERTIES
from .stage_inputs import input_fingerprint, read_stage_inputs, scoped_input_key


def stationing_inputs(alignment_obj) -> dict[str, str]:
    """A Stationing samples its Alignment."""

    model = to_alignment_model(alignment_obj) if alignment_obj is not None else None
    if model is None:
        return {}
    return {scoped_input_key("alignment", model.alignment_id): input_fingerprint(model)}


def centerline3d_inputs(document) -> dict[str, str]:
    """The 3D Centerline joins each road's Alignment, Profile and station values."""

    inputs: dict[str, str] = {}
    _road_inputs(inputs, document)
    return inputs


def _road_inputs(inputs: dict[str, str], document) -> None:
    for obj in list_v1_alignments(document):
        model = to_alignment_model(obj)
        if model is not None:
            inputs[scoped_input_key("alignment", model.alignment_id)] = input_fingerprint(model)
    for obj in list_v1_profiles(document):
        model = to_profile_model(obj)
        if model is not None:
            inputs[scoped_input_key("profile", str(getattr(obj, "AlignmentId", "") or ""))] = input_fingerprint(model)
    for obj in list_v1_stationings(document):
        # A Stationing is consumed only through its station values.
        stations = [float(value) for value in list(getattr(obj, "StationValues", []) or [])]
        inputs[scoped_input_key("stations", str(getattr(obj, "AlignmentId", "") or ""))] = input_fingerprint(stations)


def applied_sections_inputs(document) -> dict[str, str]:
    """Every source Applied Sections reads, per road where the source belongs to one road."""

    inputs: dict[str, str] = {}
    _road_inputs(inputs, document)
    for kind, objects, to_model in (
        ("regions", list_v1_region_models(document), to_region_model),
        ("superelevation", list_v1_superelevation_sources(document), to_superelevation_model),
    ):
        for obj in objects:
            model = to_model(obj)
            if model is not None:
                inputs[scoped_input_key(kind, str(getattr(obj, "AlignmentId", "") or ""))] = input_fingerprint(model)
    inputs["assembly"] = input_fingerprint(
        [
            [to_assembly_subassembly_model(obj) for obj in list_v1_assembly_subassembly_models(document)],
            [to_subassembly_library(obj) for obj in list_v1_subassembly_libraries(document)],
            [to_subassembly_preset_library(obj) for obj in list_v1_subassembly_preset_libraries(document)],
        ]
    )
    centerline_obj = find_v1_centerline3d_object(document)
    if centerline_obj is not None:
        # The stored 3D Centerline the station frames come from.
        inputs["centerline3d"] = centerline3d_result_fingerprint(centerline_obj)
    _optional_input(inputs, "structure", to_structure_model(find_v1_structure_model(document)))
    _optional_input(inputs, "drainage", to_drainage_model(find_v1_drainage_model(document)))
    intersection_obj = find_v1_intersection_model(document)
    if intersection_obj is not None:
        inputs["intersection"] = input_fingerprint(
            [to_intersection_model(intersection_obj), stored_intersection_spec(intersection_obj)]
        )
    _optional_input(inputs, "terrain", terrain_token(document))
    return inputs


def build_parametric_inputs(document) -> dict[str, str]:
    """Build Parametric reads the Applied Sections result, Surface Transitions and the terrain."""

    inputs: dict[str, str] = {}
    applied_obj = find_v1_applied_section_set(document)
    if applied_obj is not None:
        # The result's own content fingerprint, written with its payload.
        inputs["applied_sections"] = str(getattr(applied_obj, PAYLOAD_PROPERTIES.fingerprint, "") or "")
    _optional_input(inputs, "surface_transitions", to_surface_transition_model(find_v1_surface_transition_model(document)))
    _optional_input(inputs, "terrain", terrain_token(document))
    return inputs


def stationing_freshness_rows(document) -> list[StageFreshness]:
    """One row per Stationing object: each road's stations are rebuilt on their own."""

    rows = []
    for obj in list_v1_stationings(document):
        alignment_obj = find_v1_alignment(document, alignment_id=str(getattr(obj, "AlignmentId", "") or ""))
        rows.append(
            stage_freshness(
                STATIONING,
                object_names=(str(obj.Name),),
                recorded=read_stage_inputs(obj),
                current=stationing_inputs(alignment_obj),
            )
        )
    return rows


def document_result_freshness(document) -> list[StageFreshness]:
    """Freshness of every result stage, in workflow order."""

    stationing = merge_stage_rows(STATIONING, stationing_freshness_rows(document))
    centerline_obj = find_v1_centerline3d_object(document)
    centerline = stage_freshness(
        CENTERLINE3D,
        object_names=_names(centerline_obj),
        recorded=read_stage_inputs(centerline_obj),
        current=centerline3d_inputs(document) if centerline_obj is not None else {},
        upstream=stationing,
    )
    applied_obj = find_v1_applied_section_set(document)
    applied = stage_freshness(
        APPLIED_SECTIONS,
        object_names=_names(applied_obj),
        recorded=read_stage_inputs(applied_obj),
        current=applied_sections_inputs(document) if applied_obj is not None else {},
        upstream=stationing,
    )
    corridor_obj = find_v1_corridor_model(document)
    build = stage_freshness(
        BUILD_PARAMETRIC,
        object_names=_names(corridor_obj),
        recorded=read_stage_inputs(corridor_obj),
        current=build_parametric_inputs(document) if corridor_obj is not None else {},
        upstream=applied,
    )
    return [stationing, centerline, applied, build]


def terrain_token(document) -> list[object] | None:
    """A cheap identity of the existing-ground terrain the builds sample.

    The builds convert the terrain to a TIN, which is too slow to repeat for a freshness check, so
    this fingerprints the terrain objects instead: their names, point and facet counts, bounding
    box and placement. The candidates follow the builds' preference: an edited TIN preview, then a
    TIN mesh preview, then the project's Terrain link. A terrain the user selects in the tree at
    build time is not followed.
    """

    # Corridor result previews reuse the "edited" display role but are never terrain.
    objects = [
        obj
        for obj in list(getattr(document, "Objects", []) or [])
        if not str(getattr(obj, "CRRecordKind", "") or "").startswith("v1_corridor")
    ]
    edited = [obj for obj in objects if str(getattr(obj, "SurfaceRole", "") or "").lower() == "edited"]
    previews = [obj for obj in objects if str(getattr(obj, "CRRecordKind", "") or "") == "tin_mesh_preview"]
    project = find_project(document)
    terrain = getattr(project, "Terrain", None) if project is not None else None
    candidates = edited or previews or ([terrain] if terrain is not None else [])
    tokens = [_geometry_token(obj) for obj in candidates]
    return tokens or None


def _geometry_token(obj) -> list[object]:
    mesh = getattr(obj, "Mesh", None)
    shape = getattr(obj, "Shape", None)
    counts: list[int] = []
    box = None
    try:
        if mesh is not None:
            counts = [int(mesh.CountPoints), int(mesh.CountFacets)]
            box = mesh.BoundBox
        elif shape is not None and not shape.isNull():
            counts = [len(shape.Faces), len(shape.Edges)]
            box = shape.BoundBox
    except (AttributeError, RuntimeError):
        # A shape that cannot report its topology fingerprints by name and placement only.
        counts, box = [], None
    bounds = [] if box is None else [round(float(value), 6) for value in (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax)]
    placement = getattr(obj, "Placement", None)
    placement_text = str(placement) if placement is not None else ""
    return [str(getattr(obj, "Name", "") or ""), counts, bounds, placement_text]


def _optional_input(inputs: dict[str, str], key: str, value: object) -> None:
    if value is not None:
        inputs[key] = input_fingerprint(value)


def _names(obj) -> tuple[str, ...]:
    return (str(obj.Name),) if obj is not None else ()


__all__ = [
    "applied_sections_inputs",
    "build_parametric_inputs",
    "centerline3d_inputs",
    "document_result_freshness",
    "stationing_freshness_rows",
    "stationing_inputs",
    "terrain_token",
]
