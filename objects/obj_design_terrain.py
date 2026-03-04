# CorridorRoad/objects/obj_design_terrain.py
import math

import FreeCAD as App
import Part

from objects.obj_project import get_length_scale

_RECOMP_LABEL_SUFFIX = " [Recompute]"


class _CanceledError(Exception):
    pass


def _is_mesh_object(obj) -> bool:
    try:
        return hasattr(obj, "Mesh") and obj.Mesh is not None and int(obj.Mesh.CountFacets) > 0
    except Exception:
        return False


def _is_shape_object(obj) -> bool:
    try:
        return hasattr(obj, "Shape") and obj.Shape is not None and (not obj.Shape.isNull())
    except Exception:
        return False


def _to_vec(p):
    try:
        return App.Vector(float(p.x), float(p.y), float(p.z))
    except Exception:
        pass
    try:
        return App.Vector(float(p[0]), float(p[1]), float(p[2]))
    except Exception:
        pass
    raise Exception("Invalid point format.")


def _mark_recompute_flag(obj, needed: bool):
    try:
        if hasattr(obj, "NeedsRecompute"):
            obj.NeedsRecompute = bool(needed)
    except Exception:
        pass

    try:
        label = str(getattr(obj, "Label", "") or "")
        if bool(needed):
            if _RECOMP_LABEL_SUFFIX not in label:
                obj.Label = f"{label}{_RECOMP_LABEL_SUFFIX}"
        else:
            if _RECOMP_LABEL_SUFFIX in label:
                obj.Label = label.replace(_RECOMP_LABEL_SUFFIX, "")
    except Exception:
        pass


def ensure_design_terrain_properties(obj):
    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)

    if not hasattr(obj, "SourceDesignSurface"):
        obj.addProperty("App::PropertyLink", "SourceDesignSurface", "DesignTerrain", "DesignGradingSurface source")
    if not hasattr(obj, "ExistingTerrain"):
        obj.addProperty("App::PropertyLink", "ExistingTerrain", "DesignTerrain", "Existing terrain source (Mesh/Shape)")

    if not hasattr(obj, "CellSize"):
        obj.addProperty("App::PropertyFloat", "CellSize", "DesignTerrain", "Sampling cell size (m)")
        obj.CellSize = 1.0 * scale
    if not hasattr(obj, "MaxSamples"):
        obj.addProperty("App::PropertyInteger", "MaxSamples", "DesignTerrain", "Maximum allowed sample cells")
        obj.MaxSamples = 250000
    if not hasattr(obj, "DomainMargin"):
        obj.addProperty("App::PropertyFloat", "DomainMargin", "DesignTerrain", "Margin from existing terrain bounds (m)")
        obj.DomainMargin = 0.0 * scale

    if not hasattr(obj, "AutoUpdate"):
        obj.addProperty("App::PropertyBool", "AutoUpdate", "DesignTerrain", "Auto update from source changes")
        obj.AutoUpdate = True
    if not hasattr(obj, "RebuildNow"):
        obj.addProperty("App::PropertyBool", "RebuildNow", "DesignTerrain", "Set True to force rebuild now")
        obj.RebuildNow = False

    if not hasattr(obj, "NeedsRecompute"):
        obj.addProperty("App::PropertyBool", "NeedsRecompute", "Result", "Marked when source updates require recompute")
        obj.NeedsRecompute = False

    if not hasattr(obj, "SampleCount"):
        obj.addProperty("App::PropertyInteger", "SampleCount", "Result", "Total sample cell count")
        obj.SampleCount = 0
    if not hasattr(obj, "ValidCount"):
        obj.addProperty("App::PropertyInteger", "ValidCount", "Result", "Valid merged sample count")
        obj.ValidCount = 0
    if not hasattr(obj, "NoDataArea"):
        obj.addProperty("App::PropertyFloat", "NoDataArea", "Result", "No-data area (m^2)")
        obj.NoDataArea = 0.0
    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"


class DesignTerrain:
    """
    Composite design terrain:
    - inside design grading surface footprint: use design grading elevation
    - elsewhere: keep existing terrain elevation
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "DesignTerrain"
        self._bulk_updating = False
        self._progress_cb = None
        ensure_design_terrain_properties(obj)

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
    def _triangles_from_shape(shape_obj, deflection: float):
        shp = getattr(shape_obj, "Shape", None)
        if shp is None or shp.isNull():
            raise Exception("Shape source is empty.")
        try:
            pts, tri_idx = shp.tessellate(max(0.01, float(deflection)))
        except Exception as ex:
            raise Exception(f"Shape tessellation failed: {ex}")

        triangles = []
        for t in tri_idx:
            try:
                i0, i1, i2 = int(t[0]), int(t[1]), int(t[2])
                p0, p1, p2 = _to_vec(pts[i0]), _to_vec(pts[i1]), _to_vec(pts[i2])
                if (p1 - p0).Length <= 1e-12 or (p2 - p0).Length <= 1e-12:
                    continue
                bb = DesignTerrain._triangle_bbox_xy(p0, p1, p2)
                triangles.append((p0, p1, p2, bb))
            except Exception:
                continue
        if not triangles:
            raise Exception("No valid triangles from shape.")
        return triangles

    @staticmethod
    def _triangles_from_mesh(mesh_obj):
        mesh = getattr(mesh_obj, "Mesh", None)
        if mesh is None:
            raise Exception("Mesh source is empty.")

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
                    p0, p1, p2 = _to_vec(pts[i0]), _to_vec(pts[i1]), _to_vec(pts[i2])
                    if (p1 - p0).Length <= 1e-12 or (p2 - p0).Length <= 1e-12:
                        continue
                    bb = DesignTerrain._triangle_bbox_xy(p0, p1, p2)
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
                    bb = DesignTerrain._triangle_bbox_xy(p0, p1, p2)
                    triangles.append((p0, p1, p2, bb))
                except Exception:
                    continue

        if not triangles:
            raise Exception("No valid triangles from mesh.")
        return triangles

    def _triangles_from_mesh_progress(self, mesh_obj, pct0: float, pct1: float, label: str):
        mesh = getattr(mesh_obj, "Mesh", None)
        if mesh is None:
            raise Exception("Mesh source is empty.")

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
                    p0, p1, p2 = _to_vec(pts[i0]), _to_vec(pts[i1]), _to_vec(pts[i2])
                    if (p1 - p0).Length <= 1e-12 or (p2 - p0).Length <= 1e-12:
                        pass
                    else:
                        bb = DesignTerrain._triangle_bbox_xy(p0, p1, p2)
                        triangles.append((p0, p1, p2, bb))
                except Exception:
                    pass

                if (i % report_every) == 0:
                    pct = float(pct0) + (float(pct1) - float(pct0)) * (float(i) / float(n))
                    if self._report_progress(pct, f"{label}: {i}/{n}"):
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
                            bb = DesignTerrain._triangle_bbox_xy(p0, p1, p2)
                            triangles.append((p0, p1, p2, bb))
                except Exception:
                    pass

                if (i % report_every) == 0:
                    pct = float(pct0) + (float(pct1) - float(pct0)) * (float(i) / float(n))
                    if self._report_progress(pct, f"{label}: {i}/{n}"):
                        raise _CanceledError("Canceled by user.")

        if not triangles:
            raise Exception("No valid triangles from mesh.")
        return triangles

    @staticmethod
    def _triangles_from_source(obj, deflection: float):
        if _is_mesh_object(obj):
            return DesignTerrain._triangles_from_mesh(obj)
        if _is_shape_object(obj):
            return DesignTerrain._triangles_from_shape(obj, deflection)
        raise Exception("Source must be mesh or shape.")

    @staticmethod
    def _build_xy_buckets(triangles, bucket_size: float, max_cells_per_triangle: int = 20000):
        if bucket_size <= 1e-9:
            bucket_size = 1.0
        buckets = {}
        wide = []
        for idx, tri in enumerate(triangles):
            bb = tri[3]
            ix0 = int(math.floor(bb[0] / bucket_size))
            ix1 = int(math.floor(bb[1] / bucket_size))
            iy0 = int(math.floor(bb[2] / bucket_size))
            iy1 = int(math.floor(bb[3] / bucket_size))
            nx = int(max(0, ix1 - ix0 + 1))
            ny = int(max(0, iy1 - iy0 + 1))
            if int(nx * ny) > int(max(1, max_cells_per_triangle)):
                wide.append(idx)
                continue
            for ix in range(ix0, ix1 + 1):
                for iy in range(iy0, iy1 + 1):
                    buckets.setdefault((ix, iy), []).append(idx)
        if len(wide) > 5000:
            stride = int(math.ceil(float(len(wide)) / 5000.0))
            wide = wide[::max(1, stride)]
        return buckets, wide

    def _build_xy_buckets_progress(
        self,
        triangles,
        bucket_size: float,
        pct0: float,
        pct1: float,
        label: str,
        max_cells_per_triangle: int = 20000,
    ):
        if bucket_size <= 1e-9:
            bucket_size = 1.0
        buckets = {}
        wide = []
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
            if int(nx * ny) > int(max(1, max_cells_per_triangle)):
                wide.append(idx - 1)
            else:
                for ix in range(ix0, ix1 + 1):
                    for iy in range(iy0, iy1 + 1):
                        buckets.setdefault((ix, iy), []).append(idx - 1)

            if (idx % report_every) == 0:
                pct = float(pct0) + (float(pct1) - float(pct0)) * (float(idx) / float(n))
                if self._report_progress(pct, f"{label}: {idx}/{n}"):
                    raise _CanceledError("Canceled by user.")

        if len(wide) > 5000:
            stride = int(math.ceil(float(len(wide)) / 5000.0))
            wide = wide[::max(1, stride)]
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
        return float(w0 * p0.z + w1 * p1.z + w2 * p2.z)

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
            z = DesignTerrain._point_in_tri_z(x, y, p0, p1, p2)
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

    @staticmethod
    def _source_bounds(src_obj):
        if _is_mesh_object(src_obj):
            return src_obj.Mesh.BoundBox
        if _is_shape_object(src_obj):
            return src_obj.Shape.BoundBox
        raise Exception("Invalid terrain source bounds.")

    def execute(self, obj):
        ensure_design_terrain_properties(obj)
        try:
            scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
            if self._report_progress(1.0, "Preparing design terrain"):
                raise _CanceledError("Canceled by user.")

            dsg = getattr(obj, "SourceDesignSurface", None)
            if dsg is None or (not _is_shape_object(dsg)):
                raise Exception("Missing SourceDesignSurface (DesignGradingSurface).")
            eg = getattr(obj, "ExistingTerrain", None)
            if eg is None or (not (_is_mesh_object(eg) or _is_shape_object(eg))):
                raise Exception("Missing ExistingTerrain (Mesh/Shape).")

            cell = float(getattr(obj, "CellSize", 1.0 * scale))
            if (not math.isfinite(cell)) or cell <= 1e-6:
                cell = 1.0 * scale
                obj.CellSize = 1.0 * scale

            min_cell = 0.2 * scale
            if cell < min_cell:
                cell = min_cell
                obj.CellSize = min_cell

            max_samples = int(getattr(obj, "MaxSamples", 250000))
            if max_samples <= 0:
                max_samples = 250000
                obj.MaxSamples = max_samples

            margin = max(0.0, float(getattr(obj, "DomainMargin", 0.0)))
            bb = DesignTerrain._source_bounds(eg)
            xmin = float(bb.XMin - margin)
            xmax = float(bb.XMax + margin)
            ymin = float(bb.YMin - margin)
            ymax = float(bb.YMax + margin)
            if xmax <= xmin + 1e-9 or ymax <= ymin + 1e-9:
                raise Exception("ExistingTerrain XY bounds are degenerate.")

            nx = int(max(0.0, math.floor((xmax - xmin) / cell)))
            ny = int(max(0.0, math.floor((ymax - ymin) / cell)))
            est_samples = int(nx * ny)
            if est_samples > max_samples:
                raise Exception(
                    f"Estimated samples {est_samples} exceed MaxSamples {max_samples}. "
                    "Increase CellSize, reduce domain, or raise MaxSamples."
                )

            if self._report_progress(8.0, "Triangulating design grading surface"):
                raise _CanceledError("Canceled by user.")
            defl = max(0.05 * scale, min(2.0 * scale, 0.5 * cell))
            tri_d = DesignTerrain._triangles_from_shape(dsg, defl)

            if _is_mesh_object(eg):
                tri_e = self._triangles_from_mesh_progress(eg, 12.0, 20.0, "Reading existing terrain mesh")
            else:
                if self._report_progress(12.0, "Triangulating existing terrain shape"):
                    raise _CanceledError("Canceled by user.")
                tri_e = DesignTerrain._triangles_from_source(eg, defl)

            buck_d, wide_d = self._build_xy_buckets_progress(
                tri_d, cell, 20.0, 30.0, "Bucketing design terrain triangles"
            )
            buck_e, wide_e = self._build_xy_buckets_progress(
                tri_e, cell, 30.0, 40.0, "Bucketing existing terrain triangles"
            )

            faces = []
            s_cnt = 0
            v_cnt = 0
            nodata = 0.0
            area = float(cell * cell)
            total_for_progress = max(1, est_samples)
            report_every = max(20, min(2000, total_for_progress // 200))

            for x, y in DesignTerrain._iter_grid_centers(xmin, xmax, ymin, ymax, cell):
                s_cnt += 1
                if (s_cnt % report_every) == 0:
                    pct = 40.0 + 58.0 * (float(s_cnt) / float(total_for_progress))
                    if self._report_progress(pct, f"Sampling merged terrain: {s_cnt}/{est_samples}"):
                        raise _CanceledError("Canceled by user.")

                zd = DesignTerrain._z_at_xy(x, y, tri_d, buck_d, cell, wide_d)
                ze = DesignTerrain._z_at_xy(x, y, tri_e, buck_e, cell, wide_e)
                z = zd if zd is not None else ze
                if z is None:
                    nodata += area
                    continue
                try:
                    faces.append(DesignTerrain._make_cell_face(x, y, cell, float(z)))
                    v_cnt += 1
                except Exception:
                    nodata += area

            if not faces:
                raise Exception("No valid merged terrain cells were generated.")

            obj.Shape = Part.Compound(faces)
            obj.SampleCount = int(s_cnt)
            obj.ValidCount = int(v_cnt)
            obj.NoDataArea = float(nodata)
            obj.Status = (
                f"OK: samples={s_cnt}, valid={v_cnt}, nodata={nodata:.3f} (scaled^2), "
                f"mode=DesignInsideElseExisting"
            )
            _mark_recompute_flag(obj, False)

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
            obj.NoDataArea = 0.0
            obj.Status = f"ERROR: {ex}"
            _mark_recompute_flag(obj, False)

    def onChanged(self, obj, prop):
        if bool(getattr(self, "_bulk_updating", False)):
            return

        if prop in (
            "SourceDesignSurface",
            "ExistingTerrain",
            "CellSize",
            "MaxSamples",
            "DomainMargin",
            "AutoUpdate",
            "RebuildNow",
        ):
            try:
                if prop == "RebuildNow":
                    if not bool(getattr(obj, "RebuildNow", False)):
                        return
                elif prop == "AutoUpdate":
                    if not bool(getattr(obj, "AutoUpdate", True)):
                        return
                else:
                    if not bool(getattr(obj, "AutoUpdate", True)):
                        obj.Status = "NEEDS_RECOMPUTE: source/parameters changed"
                        _mark_recompute_flag(obj, True)
                        return

                obj.touch()
                if obj.Document is not None:
                    obj.Document.recompute()
            except Exception:
                pass


class ViewProviderDesignTerrain:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Shaded"
            vobj.LineWidth = 1
            vobj.Transparency = 30
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
        return "Shaded"

    def setDisplayMode(self, mode):
        return mode
