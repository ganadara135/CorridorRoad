"""FreeCAD document objects for CorridorRoad v1 source models."""

from .obj_alignment import (
    V1AlignmentObject,
    create_sample_v1_alignment,
    find_v1_alignment,
    to_alignment_model,
)
from .obj_applied_section import (
    V1AppliedSectionSetObject,
    create_or_update_v1_applied_section_set_object,
    find_v1_applied_section_set,
    to_applied_section_set,
)
from .obj_assembly import (
    V1AssemblyModelObject,
    assembly_model_ids,
    create_or_update_v1_assembly_model_object,
    find_v1_assembly_model,
    list_v1_assembly_models,
    to_assembly_model,
)
from .obj_corridor import (
    V1CorridorModelObject,
    create_or_update_v1_corridor_model_object,
    find_v1_corridor_model,
    to_corridor_model,
)
from .obj_surface import (
    V1SurfaceModelObject,
    create_or_update_v1_surface_model_object,
    find_v1_surface_model,
    to_surface_model,
)
from .obj_profile import (
    V1ProfileObject,
    create_sample_v1_profile,
    find_v1_profile,
    to_profile_model,
)
from .obj_region import (
    V1RegionModelObject,
    create_or_update_v1_region_model_object,
    find_v1_region_model,
    to_region_model,
)
from .obj_structure import (
    V1StructureModelObject,
    create_or_update_v1_structure_model_object,
    find_v1_structure_model,
    to_structure_model,
)
from .obj_stationing import (
    V1StationingObject,
    create_v1_stationing,
    find_v1_stationing,
    station_value_rows,
    update_v1_stationing_from_alignment,
)

__all__ = [
    "V1AlignmentObject",
    "V1AppliedSectionSetObject",
    "V1AssemblyModelObject",
    "V1CorridorModelObject",
    "V1ProfileObject",
    "V1RegionModelObject",
    "V1StationingObject",
    "V1StructureModelObject",
    "V1SurfaceModelObject",
    "assembly_model_ids",
    "create_or_update_v1_assembly_model_object",
    "create_or_update_v1_applied_section_set_object",
    "create_or_update_v1_region_model_object",
    "create_or_update_v1_structure_model_object",
    "create_or_update_v1_corridor_model_object",
    "create_or_update_v1_surface_model_object",
    "create_sample_v1_alignment",
    "create_sample_v1_profile",
    "create_v1_stationing",
    "find_v1_alignment",
    "find_v1_applied_section_set",
    "find_v1_assembly_model",
    "find_v1_corridor_model",
    "find_v1_surface_model",
    "find_v1_profile",
    "find_v1_region_model",
    "find_v1_stationing",
    "find_v1_structure_model",
    "list_v1_assembly_models",
    "station_value_rows",
    "to_alignment_model",
    "to_applied_section_set",
    "to_assembly_model",
    "to_corridor_model",
    "to_surface_model",
    "to_profile_model",
    "to_region_model",
    "to_structure_model",
    "update_v1_stationing_from_alignment",
]
