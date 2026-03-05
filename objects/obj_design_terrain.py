# CorridorRoad/objects/obj_design_terrain.py
import math

import FreeCAD as App

from objects.obj_project import get_length_scale

_RECOMP_LABEL_SUFFIX = " [Recompute]"


class _CanceledError(Exception):
    pass


def _empty_mesh():
    try:
        import Mesh

        return Mesh.Mesh()
    except Exception:
        return None


def _is_mesh_object(obj) -> bool:
    try:
        return hasattr(obj, "Mesh") and obj.Mesh is not None and int(obj.Mesh.CountFacets) > 0
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
        obj.addProperty("App::PropertyLink", "ExistingTerrain", "DesignTerrain", "Existing terrain source (Mesh)")

    if not hasattr(obj, "CellSize"):
        obj.addProperty("App::PropertyFloat", "CellSize", "DesignTerrain", "Sampling cell size (m)")
        obj.CellSize = 1.0 * scale
    if not hasattr(obj, "MaxSamples"):
        obj.addProperty("App::PropertyInteger", "MaxSamples", "DesignTerrain", "Maximum allowed sample cells")
        obj.MaxSamples = 250000
    if not hasattr(obj, "MaxCandidateTriangles"):
        obj.addProperty(
            "App::PropertyInteger",
            "MaxCandidateTriangles",
            "DesignTerrain",
            "Maximum candidate triangles checked per sample point",
        )
        obj.MaxCandidateTriangles = 2500
    if not hasattr(obj, "MaxTriangleChecks"):
        obj.addProperty(
            "App::PropertyInteger",
            "MaxTriangleChecks",
            "DesignTerrain",
            "Maximum estimated triangle checks before abort",
        )
        obj.MaxTriangleChecks = 250000000
    if not hasattr(obj, "MaxTrianglesPerSource"):
        obj.addProperty(
            "App::PropertyInteger",
            "MaxTrianglesPerSource",
            "DesignTerrain",
            "Maximum triangle count per source after decimation",
        )
        obj.MaxTrianglesPerSource = 150000
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
    if not hasattr(obj, "Mesh"):
        try:
            obj.addProperty("Mesh::PropertyMeshKernel", "Mesh", "Result", "Generated composite terrain mesh")
            em = _empty_mesh()
            if em is not None:
                obj.Mesh = em
        except Exception:
            pass


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
    def _z_at_xy(x, y, triangles, buckets, bucket_size, wide_indices=None, max_candidates=None):
        ix = int(math.floor(float(x) / bucket_size))
        iy = int(math.floor(float(y) / bucket_size))
        cand = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cand.extend(buckets.get((ix + dx, iy + dy), []))
        if wide_indices:
            cand.extend(wide_indices)
        if max_candidates is not None and int(max_candidates) > 0 and len(cand) > int(max_candidates):
            stride = int(max(2, math.ceil(float(len(cand)) / float(max_candidates))))
            cand = cand[::stride]
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
    def _decimate_triangles(triangles, max_count: int):
        n = int(len(triangles))
        if n <= 0:
            return triangles
        m = int(max_count)
        if m <= 0 or n <= m:
            return triangles
        stride = int(max(2, math.ceil(float(n) / float(m))))
        return triangles[::stride]

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
        if not _is_mesh_object(src_obj):
            raise Exception("ExistingTerrain must be a valid mesh object.")
        return src_obj.Mesh.BoundBox

    def execute(self, obj):
        ensure_design_terrain_properties(obj)
        try:
            scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
            if self._report_progress(1.0, "Preparing design terrain"):
                raise _CanceledError("Canceled by user.")

            dsg = getattr(obj, "SourceDesignSurface", None)
            if dsg is None or (not _is_mesh_object(dsg)):
                raise Exception("Missing SourceDesignSurface (DesignGradingSurface Mesh).")
            eg = getattr(obj, "ExistingTerrain", None)
            if eg is None or (not _is_mesh_object(eg)):
                raise Exception("Missing ExistingTerrain (Mesh).")

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
            max_candidates = int(getattr(obj, "MaxCandidateTriangles", 2500))
            if max_candidates <= 0:
                max_candidates = 2500
                obj.MaxCandidateTriangles = max_candidates
            max_checks = int(getattr(obj, "MaxTriangleChecks", 250000000))
            if max_checks <= 0:
                max_checks = 250000000
                obj.MaxTriangleChecks = max_checks
            max_tri = int(getattr(obj, "MaxTrianglesPerSource", 150000))
            if max_tri <= 0:
                max_tri = 150000
                obj.MaxTrianglesPerSource = max_tri
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

            if self._report_progress(8.0, "Reading design grading mesh"):
                raise _CanceledError("Canceled by user.")
            tri_d = self._triangles_from_mesh_progress(dsg, 8.0, 12.0, "Reading design grading mesh")

            tri_e = self._triangles_from_mesh_progress(eg, 12.0, 20.0, "Reading existing terrain mesh")

            if len(tri_d) > max_tri:
                tri_d = DesignTerrain._decimate_triangles(tri_d, max_tri)
            if len(tri_e) > max_tri:
                tri_e = DesignTerrain._decimate_triangles(tri_e, max_tri)

            buck_d, wide_d = self._build_xy_buckets_progress(
                tri_d, cell, 20.0, 30.0, "Bucketing design terrain triangles"
            )
            buck_e, wide_e = self._build_xy_buckets_progress(
                tri_e, cell, 30.0, 40.0, "Bucketing existing terrain triangles"
            )

            # Pre-run complexity guard for large terrains.
            def _avg_len(dct):
                if not dct:
                    return 0.0
                try:
                    return float(sum(len(v) for v in dct.values())) / float(max(1, len(dct)))
                except Exception:
                    return 0.0

            total_for_progress = max(1, est_samples)
            avg_local_d = _avg_len(buck_d)
            avg_local_e = _avg_len(buck_e)
            est_cand_d = min(float(max_candidates), 9.0 * avg_local_d + float(len(wide_d)))
            est_cand_e = min(float(max_candidates), 9.0 * avg_local_e + float(len(wide_e)))
            est_checks = int(float(total_for_progress) * float(max(1.0, est_cand_d + est_cand_e)))
            if est_checks > max_checks:
                raise Exception(
                    f"Estimated triangle checks {est_checks} exceed MaxTriangleChecks {max_checks}. "
                    "Increase CellSize, reduce domain, or lower mesh density."
                )

            mesh_out = _empty_mesh()
            if mesh_out is None:
                raise Exception("Mesh module is not available.")
            s_cnt = 0
            v_cnt = 0
            nodata = 0.0
            area = float(cell * cell)
            report_every = max(20, min(2000, total_for_progress // 200))

            for x, y in DesignTerrain._iter_grid_centers(xmin, xmax, ymin, ymax, cell):
                s_cnt += 1
                if (s_cnt % report_every) == 0:
                    pct = 40.0 + 58.0 * (float(s_cnt) / float(total_for_progress))
                    if self._report_progress(pct, f"Sampling merged terrain: {s_cnt}/{est_samples}"):
                        raise _CanceledError("Canceled by user.")

                zd = DesignTerrain._z_at_xy(x, y, tri_d, buck_d, cell, wide_d, max_candidates=max_candidates)
                ze = DesignTerrain._z_at_xy(x, y, tri_e, buck_e, cell, wide_e, max_candidates=max_candidates)
                z = zd if zd is not None else ze
                if z is None:
                    nodata += area
                    continue
                try:
                    h = 0.5 * float(cell)
                    zf = float(z)
                    p1 = App.Vector(float(x - h), float(y - h), zf)
                    p2 = App.Vector(float(x + h), float(y - h), zf)
                    p3 = App.Vector(float(x + h), float(y + h), zf)
                    p4 = App.Vector(float(x - h), float(y + h), zf)
                    # Two triangles per sampled cell.
                    mesh_out.addFacet(p1, p2, p3)
                    mesh_out.addFacet(p1, p3, p4)
                    v_cnt += 1
                except Exception:
                    nodata += area

            if int(v_cnt) <= 0:
                raise Exception("No valid merged terrain cells were generated.")

            if self._report_progress(98.5, "Applying output mesh"):
                raise _CanceledError("Canceled by user.")
            if hasattr(obj, "Mesh"):
                obj.Mesh = mesh_out
            obj.SampleCount = int(s_cnt)
            obj.ValidCount = int(v_cnt)
            obj.NoDataArea = float(nodata)
            try:
                fc = int(getattr(mesh_out, "CountFacets", 0))
            except Exception:
                fc = 0
            obj.Status = (
                f"OK: samples={s_cnt}, valid={v_cnt}, nodata={nodata:.3f} (scaled^2), "
                f"mode=DesignInsideElseExisting, facets={fc}"
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
            if hasattr(obj, "Mesh"):
                em = _empty_mesh()
                if em is not None:
                    obj.Mesh = em
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
            "MaxCandidateTriangles",
            "MaxTriangleChecks",
            "MaxTrianglesPerSource",
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
