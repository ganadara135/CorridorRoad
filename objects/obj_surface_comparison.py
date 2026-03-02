# CorridorRoad/objects/obj_surface_comparison.py
import math

import FreeCAD as App
import Part


class _CanceledError(Exception):
    pass


def _is_finite(x: float) -> bool:
    return math.isfinite(float(x))


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _lerp_rgb(c0, c1, t: float):
    tt = _clamp01(t)
    return (
        float(c0[0]) + (float(c1[0]) - float(c0[0])) * tt,
        float(c0[1]) + (float(c1[1]) - float(c0[1])) * tt,
        float(c0[2]) + (float(c1[2]) - float(c0[2])) * tt,
    )


def _vec(x, y, z):
    return App.Vector(float(x), float(y), float(z))


def _to_vec(p):
    try:
        return _vec(p.x, p.y, p.z)
    except Exception:
        pass
    try:
        return _vec(p[0], p[1], p[2])
    except Exception:
        pass
    raise Exception("Invalid point format.")


def _is_mesh_object(obj) -> bool:
    try:
        return hasattr(obj, "Mesh") and obj.Mesh is not None and int(obj.Mesh.CountFacets) > 0
    except Exception:
        return False


def ensure_surface_comparison_properties(obj):
    if not hasattr(obj, "SourceCorridor"):
        obj.addProperty("App::PropertyLink", "SourceCorridor", "Source", "CorridorLoft source (design)")
    if not hasattr(obj, "ExistingSurface"):
        obj.addProperty("App::PropertyLink", "ExistingSurface", "Source", "Existing surface mesh object")

    if not hasattr(obj, "CellSize"):
        obj.addProperty("App::PropertyFloat", "CellSize", "Comparison", "Sampling cell size (m)")
        obj.CellSize = 1.0
    if not hasattr(obj, "MaxSamples"):
        obj.addProperty("App::PropertyInteger", "MaxSamples", "Comparison", "Maximum allowed sample cells")
        obj.MaxSamples = 200000
    if not hasattr(obj, "MinMeshFacets"):
        obj.addProperty("App::PropertyInteger", "MinMeshFacets", "Comparison", "Minimum mesh facets required")
        obj.MinMeshFacets = 100
    if not hasattr(obj, "DomainMargin"):
        obj.addProperty("App::PropertyFloat", "DomainMargin", "Comparison", "Margin from corridor bounds (m)")
        obj.DomainMargin = 5.0
    if not hasattr(obj, "UseCorridorBounds"):
        obj.addProperty("App::PropertyBool", "UseCorridorBounds", "Comparison", "Use corridor top bounds for domain")
        obj.UseCorridorBounds = True
    if not hasattr(obj, "XMin"):
        obj.addProperty("App::PropertyFloat", "XMin", "Comparison", "Manual domain xmin")
        obj.XMin = 0.0
    if not hasattr(obj, "XMax"):
        obj.addProperty("App::PropertyFloat", "XMax", "Comparison", "Manual domain xmax")
        obj.XMax = 0.0
    if not hasattr(obj, "YMin"):
        obj.addProperty("App::PropertyFloat", "YMin", "Comparison", "Manual domain ymin")
        obj.YMin = 0.0
    if not hasattr(obj, "YMax"):
        obj.addProperty("App::PropertyFloat", "YMax", "Comparison", "Manual domain ymax")
        obj.YMax = 0.0

    if not hasattr(obj, "AutoUpdate"):
        obj.addProperty("App::PropertyBool", "AutoUpdate", "Comparison", "Auto update on source changes")
        obj.AutoUpdate = True
    if not hasattr(obj, "RebuildNow"):
        obj.addProperty("App::PropertyBool", "RebuildNow", "Comparison", "Set True to force rebuild now")
        obj.RebuildNow = False
    if not hasattr(obj, "NoDataWarnRatio"):
        obj.addProperty("App::PropertyFloat", "NoDataWarnRatio", "Comparison", "Warn threshold for no-data area ratio [0..1]")
        obj.NoDataWarnRatio = 0.05

    if not hasattr(obj, "ShowDeltaMap"):
        obj.addProperty("App::PropertyBool", "ShowDeltaMap", "Display", "Show cut/fill delta map in 3D")
        obj.ShowDeltaMap = True
    if not hasattr(obj, "DeltaDeadband"):
        obj.addProperty("App::PropertyFloat", "DeltaDeadband", "Display", "Neutral band threshold for |delta| (m)")
        obj.DeltaDeadband = 0.02
    if not hasattr(obj, "DeltaClamp"):
        obj.addProperty("App::PropertyFloat", "DeltaClamp", "Display", "Color clamp for |delta| (m)")
        obj.DeltaClamp = 2.0
    if not hasattr(obj, "VisualZOffset"):
        obj.addProperty("App::PropertyFloat", "VisualZOffset", "Display", "Z offset for delta map display (m)")
        obj.VisualZOffset = 0.05
    if not hasattr(obj, "MaxVisualCells"):
        obj.addProperty("App::PropertyInteger", "MaxVisualCells", "Display", "Maximum cells used for 3D delta map")
        obj.MaxVisualCells = 40000

    if not hasattr(obj, "SampleCount"):
        obj.addProperty("App::PropertyInteger", "SampleCount", "Result", "Total sample cell count")
        obj.SampleCount = 0
    if not hasattr(obj, "ValidCount"):
        obj.addProperty("App::PropertyInteger", "ValidCount", "Result", "Valid sample count")
        obj.ValidCount = 0
    if not hasattr(obj, "DeltaMin"):
        obj.addProperty("App::PropertyFloat", "DeltaMin", "Result", "Min(Design-Existing) elevation delta")
        obj.DeltaMin = 0.0
    if not hasattr(obj, "DeltaMax"):
        obj.addProperty("App::PropertyFloat", "DeltaMax", "Result", "Max(Design-Existing) elevation delta")
        obj.DeltaMax = 0.0
    if not hasattr(obj, "DeltaMean"):
        obj.addProperty("App::PropertyFloat", "DeltaMean", "Result", "Mean(Design-Existing) elevation delta")
        obj.DeltaMean = 0.0
    if not hasattr(obj, "CutVolume"):
        obj.addProperty("App::PropertyFloat", "CutVolume", "Result", "Cut volume (m^3)")
        obj.CutVolume = 0.0
    if not hasattr(obj, "FillVolume"):
        obj.addProperty("App::PropertyFloat", "FillVolume", "Result", "Fill volume (m^3)")
        obj.FillVolume = 0.0
    if not hasattr(obj, "NoDataArea"):
        obj.addProperty("App::PropertyFloat", "NoDataArea", "Result", "No-data area (m^2)")
        obj.NoDataArea = 0.0
    if not hasattr(obj, "DomainArea"):
        obj.addProperty("App::PropertyFloat", "DomainArea", "Result", "Evaluated domain area (m^2)")
        obj.DomainArea = 0.0
    if not hasattr(obj, "NoDataRatio"):
        obj.addProperty("App::PropertyFloat", "NoDataRatio", "Result", "No-data area ratio [0..1]")
        obj.NoDataRatio = 0.0
    if not hasattr(obj, "SignConvention"):
        obj.addProperty("App::PropertyString", "SignConvention", "Result", "Fixed cut/fill sign convention")
        obj.SignConvention = "delta = Design - Existing; delta>0 Fill; delta<0 Cut"
    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"


class SurfaceComparison:
    """
    Existing/Design surface comparison:
    - Design source: top faces extracted from CorridorLoft solid
    - Existing source: mesh object
    - Method: grid sampling and delta integration
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "SurfaceComparison"
        self._bulk_updating = False
        self._in_onchange = False
        self._progress_cb = None
        ensure_surface_comparison_properties(obj)

    def _report_progress(self, pct: float, message: str = "") -> bool:
        cb = getattr(self, "_progress_cb", None)
        if cb is None:
            return False
        try:
            p = max(0.0, min(100.0, float(pct)))
            return bool(cb(p, str(message or "")))
        except Exception:
            return False

    @staticmethod
    def _triangle_bbox_xy(p0, p1, p2):
        return (
            min(p0.x, p1.x, p2.x),
            max(p0.x, p1.x, p2.x),
            min(p0.y, p1.y, p2.y),
            max(p0.y, p1.y, p2.y),
        )

    @staticmethod
    def _top_shape_from_corridor(corridor_shape):
        if corridor_shape is None or corridor_shape.isNull():
            raise Exception("Corridor shape is missing.")

        top_faces = []
        for f in list(getattr(corridor_shape, "Faces", []) or []):
            try:
                u0, u1, v0, v1 = f.ParameterRange
                n = f.normalAt(0.5 * (u0 + u1), 0.5 * (v0 + v1))
                if float(n.z) > 0.05:
                    top_faces.append(f)
            except Exception:
                continue

        if not top_faces:
            raise Exception("No top faces found from corridor solid.")
        return top_faces[0] if len(top_faces) == 1 else Part.Compound(top_faces)

    @staticmethod
    def _triangles_from_shape(shape, deflection: float):
        try:
            pts, tri_idx = shape.tessellate(max(0.01, float(deflection)))
        except Exception as ex:
            raise Exception(f"Shape tessellation failed: {ex}")

        triangles = []
        for t in tri_idx:
            try:
                i0, i1, i2 = int(t[0]), int(t[1]), int(t[2])
                p0, p1, p2 = pts[i0], pts[i1], pts[i2]
                if (p1 - p0).Length <= 1e-12 or (p2 - p0).Length <= 1e-12:
                    continue
                bb = SurfaceComparison._triangle_bbox_xy(p0, p1, p2)
                triangles.append((p0, p1, p2, bb))
            except Exception:
                continue
        if not triangles:
            raise Exception("No valid triangles from design top surface.")
        return triangles

    @staticmethod
    def _triangles_from_mesh(mesh_obj):
        mesh = getattr(mesh_obj, "Mesh", None)
        if mesh is None:
            raise Exception("ExistingSurface has no mesh.")

        triangles = []
        topo = None
        try:
            topo = mesh.Topology
            if callable(topo):
                topo = topo()
        except Exception:
            topo = None

        if topo is not None and len(topo) == 2:
            pts, faces = topo
            for f in faces:
                try:
                    i0, i1, i2 = int(f[0]), int(f[1]), int(f[2])
                    p0, p1, p2 = pts[i0], pts[i1], pts[i2]
                    p0, p1, p2 = _to_vec(p0), _to_vec(p1), _to_vec(p2)
                    if (p1 - p0).Length <= 1e-12 or (p2 - p0).Length <= 1e-12:
                        continue
                    bb = SurfaceComparison._triangle_bbox_xy(p0, p1, p2)
                    triangles.append((p0, p1, p2, bb))
                except Exception:
                    continue
        else:
            for fc in list(getattr(mesh, "Facets", []) or []):
                try:
                    pts = list(getattr(fc, "Points", []) or [])
                    if len(pts) != 3:
                        continue
                    p0, p1, p2 = _to_vec(pts[0]), _to_vec(pts[1]), _to_vec(pts[2])
                    if (p1 - p0).Length <= 1e-12 or (p2 - p0).Length <= 1e-12:
                        continue
                    bb = SurfaceComparison._triangle_bbox_xy(p0, p1, p2)
                    triangles.append((p0, p1, p2, bb))
                except Exception:
                    continue

        if not triangles:
            raise Exception("No valid triangles from existing mesh.")
        return triangles

    def _triangles_from_mesh_progress(self, mesh_obj, pct0: float, pct1: float):
        mesh = getattr(mesh_obj, "Mesh", None)
        if mesh is None:
            raise Exception("ExistingSurface has no mesh.")

        triangles = []
        topo = None
        try:
            topo = mesh.Topology
            if callable(topo):
                topo = topo()
        except Exception:
            topo = None

        if topo is not None and len(topo) == 2:
            pts, faces = topo
            n = max(1, int(len(faces)))
            report_every = max(20, min(1000, n // 100))
            for i, f in enumerate(faces, start=1):
                try:
                    i0, i1, i2 = int(f[0]), int(f[1]), int(f[2])
                    p0, p1, p2 = pts[i0], pts[i1], pts[i2]
                    p0, p1, p2 = _to_vec(p0), _to_vec(p1), _to_vec(p2)
                    if (p1 - p0).Length <= 1e-12 or (p2 - p0).Length <= 1e-12:
                        pass
                    else:
                        bb = SurfaceComparison._triangle_bbox_xy(p0, p1, p2)
                        triangles.append((p0, p1, p2, bb))
                except Exception:
                    pass

                if (i % report_every) == 0:
                    pct = float(pct0) + (float(pct1) - float(pct0)) * (float(i) / float(n))
                    if self._report_progress(pct, f"Reading existing mesh: {i}/{n}"):
                        raise _CanceledError("Canceled by user.")
        else:
            facets = list(getattr(mesh, "Facets", []) or [])
            n = max(1, int(len(facets)))
            report_every = max(20, min(1000, n // 100))
            for i, fc in enumerate(facets, start=1):
                try:
                    pts = list(getattr(fc, "Points", []) or [])
                    if len(pts) == 3:
                        p0, p1, p2 = _to_vec(pts[0]), _to_vec(pts[1]), _to_vec(pts[2])
                        if (p1 - p0).Length > 1e-12 and (p2 - p0).Length > 1e-12:
                            bb = SurfaceComparison._triangle_bbox_xy(p0, p1, p2)
                            triangles.append((p0, p1, p2, bb))
                except Exception:
                    pass

                if (i % report_every) == 0:
                    pct = float(pct0) + (float(pct1) - float(pct0)) * (float(i) / float(n))
                    if self._report_progress(pct, f"Reading existing mesh: {i}/{n}"):
                        raise _CanceledError("Canceled by user.")

        if not triangles:
            raise Exception("No valid triangles from existing mesh.")
        return triangles

    @staticmethod
    def _build_xy_buckets(triangles, bucket_size: float):
        if bucket_size <= 1e-9:
            bucket_size = 1.0

        buckets = {}
        for idx, tri in enumerate(triangles):
            bb = tri[3]
            ix0 = int(math.floor(bb[0] / bucket_size))
            ix1 = int(math.floor(bb[1] / bucket_size))
            iy0 = int(math.floor(bb[2] / bucket_size))
            iy1 = int(math.floor(bb[3] / bucket_size))
            for ix in range(ix0, ix1 + 1):
                for iy in range(iy0, iy1 + 1):
                    buckets.setdefault((ix, iy), []).append(idx)
        return buckets

    def _build_xy_buckets_progress(
        self,
        triangles,
        bucket_size: float,
        pct0: float,
        pct1: float,
        label: str,
    ):
        if bucket_size <= 1e-9:
            bucket_size = 1.0

        buckets = {}
        wide = []
        # Guard against huge bbox-to-cell expansion.
        max_cells_per_triangle = 20000
        n = max(1, int(len(triangles)))
        report_every = max(20, min(1000, n // 100))

        if self._report_progress(pct0, label):
            raise _CanceledError("Canceled by user.")

        for idx, tri in enumerate(triangles, start=1):
            bb = tri[3]
            ix0 = int(math.floor(bb[0] / bucket_size))
            ix1 = int(math.floor(bb[1] / bucket_size))
            iy0 = int(math.floor(bb[2] / bucket_size))
            iy1 = int(math.floor(bb[3] / bucket_size))
            nx = int(max(0, ix1 - ix0 + 1))
            ny = int(max(0, iy1 - iy0 + 1))
            if int(nx * ny) > int(max_cells_per_triangle):
                wide.append(idx - 1)
            else:
                for ix in range(ix0, ix1 + 1):
                    for iy in range(iy0, iy1 + 1):
                        buckets.setdefault((ix, iy), []).append(idx - 1)

            if (idx % report_every) == 0:
                pct = float(pct0) + (float(pct1) - float(pct0)) * (float(idx) / float(n))
                if self._report_progress(pct, f"{label}: {idx}/{n}"):
                    raise _CanceledError("Canceled by user.")

        return buckets, wide

    @staticmethod
    def _point_in_tri_z(x, y, p0, p1, p2):
        x0, y0 = p0.x, p0.y
        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) <= 1e-14:
            return None
        w0 = ((y1 - y2) * (x - x2) + (x2 - x1) * (y - y2)) / den
        w1 = ((y2 - y0) * (x - x2) + (x0 - x2) * (y - y2)) / den
        w2 = 1.0 - w0 - w1
        tol = 1e-9
        if w0 < -tol or w1 < -tol or w2 < -tol:
            return None
        z = w0 * p0.z + w1 * p1.z + w2 * p2.z
        return float(z)

    @staticmethod
    def _z_at_xy(x, y, triangles, buckets, bucket_size, wide_indices=None):
        ix = int(math.floor(float(x) / bucket_size))
        iy = int(math.floor(float(y) / bucket_size))

        cand = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cand.extend(buckets.get((ix + dx, iy + dy), []))
        if wide_indices:
            cand.extend(wide_indices)
        if not cand:
            return None

        z_best = None
        seen = set()
        for idx in cand:
            if idx in seen:
                continue
            seen.add(idx)
            p0, p1, p2, bb = triangles[idx]
            if x < bb[0] - 1e-9 or x > bb[1] + 1e-9 or y < bb[2] - 1e-9 or y > bb[3] + 1e-9:
                continue
            z = SurfaceComparison._point_in_tri_z(x, y, p0, p1, p2)
            if z is None:
                continue
            if z_best is None or z > z_best:
                z_best = z
        return z_best

    @staticmethod
    def _make_cell_face(x: float, y: float, cell: float, z: float):
        h = 0.5 * float(cell)
        p1 = App.Vector(float(x - h), float(y - h), float(z))
        p2 = App.Vector(float(x + h), float(y - h), float(z))
        p3 = App.Vector(float(x + h), float(y + h), float(z))
        p4 = App.Vector(float(x - h), float(y + h), float(z))
        w = Part.makePolygon([p1, p2, p3, p4, p1])
        return Part.Face(w)

    def _delta_color(self, d: float, deadband: float, clamp_abs: float):
        # Fixed palette:
        # - Fill (delta>0): blue scale
        # - Cut  (delta<0): red scale
        # - Neutral: light gray
        neutral = (0.85, 0.85, 0.85)
        fill_hi = (0.15, 0.45, 0.95)
        cut_hi = (0.95, 0.25, 0.20)
        if abs(float(d)) <= max(0.0, float(deadband)):
            return neutral
        if clamp_abs <= 1e-9:
            clamp_abs = 1.0
        t = min(1.0, abs(float(d)) / float(clamp_abs))
        if d > 0.0:
            return _lerp_rgb(neutral, fill_hi, t)
        return _lerp_rgb(neutral, cut_hi, t)

    @staticmethod
    def _resolve_domain(obj, design_shape):
        use_corr = bool(getattr(obj, "UseCorridorBounds", True))
        if use_corr:
            bb = design_shape.BoundBox
            m = max(0.0, float(getattr(obj, "DomainMargin", 0.0)))
            return (
                float(bb.XMin - m),
                float(bb.XMax + m),
                float(bb.YMin - m),
                float(bb.YMax + m),
            )

        x0 = float(getattr(obj, "XMin", 0.0))
        x1 = float(getattr(obj, "XMax", 0.0))
        y0 = float(getattr(obj, "YMin", 0.0))
        y1 = float(getattr(obj, "YMax", 0.0))
        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0
        return x0, x1, y0, y1

    @staticmethod
    def _iter_grid_centers(xmin, xmax, ymin, ymax, step):
        if step <= 1e-9:
            step = 1.0
        x = xmin + 0.5 * step
        while x <= xmax - 0.5 * step + 1e-9:
            y = ymin + 0.5 * step
            while y <= ymax - 0.5 * step + 1e-9:
                yield x, y
                y += step
            x += step

    def execute(self, obj):
        ensure_surface_comparison_properties(obj)
        try:
            if self._report_progress(1.0, "Preparing comparison"):
                raise _CanceledError("Canceled by user.")

            force = bool(getattr(obj, "RebuildNow", False))
            auto = bool(getattr(obj, "AutoUpdate", True))
            if (not auto) and (not force):
                try:
                    obj.Status = "NEEDS_RECOMPUTE: AutoUpdate=False"
                except Exception:
                    pass
                return

            src = getattr(obj, "SourceCorridor", None)
            if src is None or getattr(src, "Shape", None) is None or src.Shape.isNull():
                raise Exception("Missing SourceCorridor.")

            eg = getattr(obj, "ExistingSurface", None)
            if eg is None or (not _is_mesh_object(eg)):
                raise Exception("ExistingSurface must be a valid mesh object.")
            mesh_facets = int(getattr(getattr(eg, "Mesh", None), "CountFacets", 0))
            min_facets = int(getattr(obj, "MinMeshFacets", 100))
            if mesh_facets < max(1, min_facets):
                raise Exception(f"Existing mesh facets {mesh_facets} < MinMeshFacets {min_facets}.")
            try:
                bbm = eg.Mesh.BoundBox
                if float(bbm.XLength) <= 1e-9 or float(bbm.YLength) <= 1e-9:
                    raise Exception("Existing mesh XY bounds are degenerate.")
            except Exception as ex:
                raise Exception(f"Existing mesh quality check failed: {ex}")

            if self._report_progress(5.0, "Extracting design top surface"):
                raise _CanceledError("Canceled by user.")
            design_top = SurfaceComparison._top_shape_from_corridor(src.Shape)

            cell = float(getattr(obj, "CellSize", 1.0))
            if not _is_finite(cell) or cell <= 1e-6:
                cell = 1.0
                obj.CellSize = 1.0

            xmin, xmax, ymin, ymax = SurfaceComparison._resolve_domain(obj, design_top)
            if xmax <= xmin + 1e-9 or ymax <= ymin + 1e-9:
                raise Exception("Invalid comparison domain.")

            max_samples = int(getattr(obj, "MaxSamples", 200000))
            if max_samples <= 0:
                max_samples = 200000
                obj.MaxSamples = max_samples

            nx = int(max(0.0, math.floor((xmax - xmin) / cell)))
            ny = int(max(0.0, math.floor((ymax - ymin) / cell)))
            est_samples = int(nx * ny)
            if est_samples > max_samples:
                raise Exception(
                    f"Estimated samples {est_samples} exceed MaxSamples {max_samples}. "
                    "Increase CellSize, reduce domain, or raise MaxSamples."
                )

            if self._report_progress(10.0, "Triangulating design surface"):
                raise _CanceledError("Canceled by user.")
            defl = max(0.05, min(2.0, 0.5 * cell))
            tri_design = SurfaceComparison._triangles_from_shape(design_top, defl)

            tri_exist = self._triangles_from_mesh_progress(eg, 15.0, 18.0)

            buck_d, wide_d = self._build_xy_buckets_progress(
                tri_design, cell, 18.0, 30.0, "Bucketing design triangles"
            )
            buck_e, wide_e = self._build_xy_buckets_progress(
                tri_exist, cell, 30.0, 40.0, "Bucketing existing triangles"
            )

            s_cnt = 0
            v_cnt = 0
            d_min = None
            d_max = None
            d_sum = 0.0
            cut = 0.0
            fill = 0.0
            nodata = 0.0
            area = cell * cell
            total_for_progress = max(1, est_samples)
            report_every = max(20, min(2000, total_for_progress // 200))
            show_map = bool(getattr(obj, "ShowDeltaMap", True))
            deadband = max(0.0, float(getattr(obj, "DeltaDeadband", 0.02)))
            clamp_abs = abs(float(getattr(obj, "DeltaClamp", 2.0)))
            zoff = float(getattr(obj, "VisualZOffset", 0.05))
            max_vis = int(getattr(obj, "MaxVisualCells", 40000))
            if max_vis <= 0:
                max_vis = 40000
            vis_stride = int(max(1, math.ceil(math.sqrt(float(total_for_progress) / float(max_vis))))) if total_for_progress > max_vis else 1
            vis_faces = []
            vis_colors = []
            nodata_color = (0.55, 0.55, 0.55)

            for x, y in SurfaceComparison._iter_grid_centers(xmin, xmax, ymin, ymax, cell):
                s_cnt += 1
                if (s_cnt % report_every) == 0:
                    pct = 40.0 + 57.0 * (float(s_cnt) / float(total_for_progress))
                    if self._report_progress(pct, f"Sampling grid: {s_cnt}/{est_samples}"):
                        raise _CanceledError("Canceled by user.")

                zd = SurfaceComparison._z_at_xy(x, y, tri_design, buck_d, cell, wide_d)
                ze = SurfaceComparison._z_at_xy(x, y, tri_exist, buck_e, cell, wide_e)

                vis_pick = show_map and ((s_cnt % vis_stride) == 0)
                if zd is None or ze is None:
                    nodata += area
                    if vis_pick and (zd is not None):
                        try:
                            vis_faces.append(SurfaceComparison._make_cell_face(x, y, cell, float(zd) + zoff))
                            vis_colors.append(nodata_color)
                        except Exception:
                            pass
                    continue

                d = float(zd - ze)
                v_cnt += 1
                d_sum += d
                d_min = d if d_min is None else min(d_min, d)
                d_max = d if d_max is None else max(d_max, d)
                if d >= 0.0:
                    fill += d * area
                else:
                    cut += (-d) * area

                if vis_pick:
                    try:
                        vis_faces.append(SurfaceComparison._make_cell_face(x, y, cell, float(zd) + zoff))
                        vis_colors.append(self._delta_color(d, deadband, clamp_abs))
                    except Exception:
                        pass

            if self._report_progress(97.0, "Finalizing result"):
                raise _CanceledError("Canceled by user.")

            if show_map and vis_faces:
                obj.Shape = Part.Compound(vis_faces)
                try:
                    if App.GuiUp:
                        obj.ViewObject.DiffuseColor = list(vis_colors)
                        obj.ViewObject.DisplayMode = "Shaded"
                        obj.ViewObject.Transparency = 0
                        obj.ViewObject.LineWidth = 1
                except Exception:
                    pass
            else:
                obj.Shape = design_top
                try:
                    if App.GuiUp:
                        obj.ViewObject.DisplayMode = "Flat Lines"
                        obj.ViewObject.Transparency = 70
                except Exception:
                    pass
            obj.SampleCount = int(s_cnt)
            obj.ValidCount = int(v_cnt)
            obj.DeltaMin = float(d_min if d_min is not None else 0.0)
            obj.DeltaMax = float(d_max if d_max is not None else 0.0)
            obj.DeltaMean = float((d_sum / float(v_cnt)) if v_cnt > 0 else 0.0)
            obj.CutVolume = float(cut)
            obj.FillVolume = float(fill)
            obj.NoDataArea = float(nodata)
            dom_area = float(area * float(s_cnt))
            nodata_ratio = float((nodata / dom_area) if dom_area > 1e-12 else 0.0)
            obj.DomainArea = dom_area
            obj.NoDataRatio = nodata_ratio
            obj.SignConvention = "delta = Design - Existing; delta>0 Fill; delta<0 Cut"

            warn_ratio = float(getattr(obj, "NoDataWarnRatio", 0.05))
            prefix = "OK"
            note = ""
            if nodata_ratio > max(0.0, warn_ratio):
                prefix = "WARN"
                note = f", nodata={100.0 * nodata_ratio:.2f}%"

            obj.Status = (
                f"{prefix}: samples={s_cnt}, valid={v_cnt}, "
                f"cut={cut:.3f} m^3, fill={fill:.3f} m^3{note}, vis_stride={vis_stride}"
            )

            if bool(getattr(obj, "RebuildNow", False)):
                obj.RebuildNow = False

            self._report_progress(100.0, "Completed")

        except _CanceledError:
            try:
                obj.Status = "CANCELED: user requested cancel"
            except Exception:
                pass
            try:
                if bool(getattr(obj, "RebuildNow", False)):
                    obj.RebuildNow = False
            except Exception:
                pass

        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.SampleCount = 0
            obj.ValidCount = 0
            obj.DeltaMin = 0.0
            obj.DeltaMax = 0.0
            obj.DeltaMean = 0.0
            obj.CutVolume = 0.0
            obj.FillVolume = 0.0
            obj.NoDataArea = 0.0
            obj.DomainArea = 0.0
            obj.NoDataRatio = 0.0
            obj.SignConvention = "delta = Design - Existing; delta>0 Fill; delta<0 Cut"
            obj.Status = f"ERROR: {ex}"

    def onChanged(self, obj, prop):
        if bool(getattr(self, "_bulk_updating", False)):
            return

        if prop in (
            "SourceCorridor",
            "ExistingSurface",
            "CellSize",
            "MaxSamples",
            "MinMeshFacets",
            "DomainMargin",
            "UseCorridorBounds",
            "XMin",
            "XMax",
            "YMin",
            "YMax",
            "NoDataWarnRatio",
            "ShowDeltaMap",
            "DeltaDeadband",
            "DeltaClamp",
            "VisualZOffset",
            "MaxVisualCells",
            "AutoUpdate",
            "RebuildNow",
        ):
            try:
                if prop == "RebuildNow":
                    # Force recompute only on explicit True toggle.
                    if not bool(getattr(obj, "RebuildNow", False)):
                        return
                elif prop == "AutoUpdate":
                    # Enabling AutoUpdate requests a recompute once.
                    if not bool(getattr(obj, "AutoUpdate", True)):
                        return
                else:
                    # Source/parameter changes recompute only when AutoUpdate is enabled.
                    if not bool(getattr(obj, "AutoUpdate", True)):
                        try:
                            obj.Status = "NEEDS_RECOMPUTE: parameters changed"
                        except Exception:
                            pass
                        return

                if bool(getattr(self, "_in_onchange", False)):
                    return
                self._in_onchange = True
                obj.touch()
                if obj.Document is not None:
                    obj.Document.recompute()
            except Exception:
                pass
            finally:
                self._in_onchange = False


class ViewProviderSurfaceComparison:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Flat Lines"
            vobj.LineWidth = 2
            vobj.Transparency = 70
        except Exception:
            pass

    def getIcon(self):
        return ""

    def updateData(self, obj, prop):
        return

    def onChanged(self, vobj, prop):
        return

    def getDisplayModes(self, vobj):
        return ["Wireframe", "Flat Lines", "Shaded"]

    def getDefaultDisplayMode(self):
        return "Flat Lines"

    def setDisplayMode(self, mode):
        return mode
