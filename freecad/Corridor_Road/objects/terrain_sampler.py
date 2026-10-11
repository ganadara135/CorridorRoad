# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.


from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects import surface_sampling_core as _ssc


def is_mesh_object(obj) -> bool:
    return _ssc.is_mesh_object(obj)


def is_shape_object(obj) -> bool:
    return _ssc.is_shape_object(obj)


def _surface_triangles(src_obj):
    if is_mesh_object(src_obj):
        return _ssc.mesh_triangles(src_obj)
    if is_shape_object(src_obj):
        return _ssc.shape_triangles(src_obj, deflection=_units.model_length_from_meters(getattr(src_obj, "Document", None), 1.0))
    return []
