import math

from freecad.Corridor_Road.objects.obj_project import get_length_scale
from freecad.Corridor_Road.objects import surface_sampling_core as _ssc


def is_mesh_object(obj) -> bool:
    return _ssc.is_mesh_object(obj)


def is_shape_object(obj) -> bool:
    return _ssc.is_shape_object(obj)


def _surface_triangles(src_obj):
    if is_mesh_object(src_obj):
        return _ssc.mesh_triangles(src_obj)
    if is_shape_object(src_obj):
        scale = get_length_scale(getattr(src_obj, "Document", None), default=1.0)
        return _ssc.shape_triangles(src_obj, deflection=1.0 * scale)
    return []


class TerrainSampler:
    def __init__(self, triangles, bucket_size: float, buckets, wide_indices):
        self.triangles = list(triangles or [])
        self.bucket_size = float(bucket_size)
        self.buckets = dict(buckets or {})
        self.wide_indices = list(wide_indices or [])

    @staticmethod
    def from_object(src_obj, max_triangles: int = 300000):
        tris = _surface_triangles(src_obj)
        if not tris:
            return None

        mt = int(max(1000, int(max_triangles)))
        tris = _ssc.decimate_triangles(tris, mt)

        scale = get_length_scale(getattr(src_obj, "Document", None), default=1.0)
        bucket = 2.0 * scale
        try:
            if is_mesh_object(src_obj):
                bb = src_obj.Mesh.BoundBox
            else:
                bb = src_obj.Shape.BoundBox
            n = max(1, len(tris))
            area = max((1.0 * scale) ** 2, float(bb.XLength) * float(bb.YLength))
            bucket = max(0.5 * scale, min(20.0 * scale, math.sqrt(area / float(n)) * 2.0))
        except Exception:
            pass

        buckets, wide = _ssc.build_xy_buckets(tris, bucket)
        return TerrainSampler(tris, bucket, buckets, wide)

    def z_at(self, x: float, y: float):
        if not self.triangles:
            return None
        return _ssc.z_at_xy(
            float(x),
            float(y),
            self.triangles,
            self.buckets,
            float(self.bucket_size),
            wide_indices=self.wide_indices,
            max_candidates=None,
        )
