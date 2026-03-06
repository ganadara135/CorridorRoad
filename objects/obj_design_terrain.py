# CorridorRoad/objects/obj_design_terrain.py
import math

import FreeCAD as App

from objects.obj_project import get_coordinate_setup, get_length_scale
from objects import surface_sampling_core as _ssc

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
    return _ssc.is_mesh_object(obj)


def _to_vec(p):
    return _ssc.to_vec(p)


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
    if not hasattr(obj, "ExistingTerrainCoords"):
        obj.addProperty(
            "App::PropertyEnumeration",
            "ExistingTerrainCoords",
            "DesignTerrain",
            "Coordinate system of ExistingTerrain mesh",
        )
        obj.ExistingTerrainCoords = ["Local", "World"]
        obj.ExistingTerrainCoords = "Local"

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
        return _ssc.triangle_bbox_xy(p0, p1, p2)

    @staticmethod
    def _triangles_from_mesh(mesh_obj):
        triangles = _ssc.mesh_triangles(mesh_obj)
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
        return _ssc.build_xy_buckets(
            triangles,
            bucket_size,
            max_cells_per_triangle=max_cells_per_triangle,
            max_wide_items=5000,
        )

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
        return _ssc.point_in_tri_z(x, y, p0, p1, p2)

    @staticmethod
    def _z_at_xy(x, y, triangles, buckets, bucket_size, wide_indices=None, max_candidates=None):
        return _ssc.z_at_xy(
            x,
            y,
            triangles,
            buckets,
            bucket_size,
            wide_indices=wide_indices,
            max_candidates=max_candidates,
        )

    @staticmethod
    def _decimate_triangles(triangles, max_count: int):
        return _ssc.decimate_triangles(triangles, max_count)

    @staticmethod
    def _iter_grid_centers(xmin, xmax, ymin, ymax, step):
        return _ssc.iter_grid_centers(xmin, xmax, ymin, ymax, step)

    @staticmethod
    def _source_bounds(src_obj):
        if not _is_mesh_object(src_obj):
            raise Exception("ExistingTerrain must be a valid mesh object.")
        return src_obj.Mesh.BoundBox

    @staticmethod
    def _world_to_local_params(doc_or_obj):
        c = get_coordinate_setup(doc_or_obj)
        th = math.radians(float(c.get("NorthRotationDeg", 0.0)))
        return {
            "cs": math.cos(th),
            "sn": math.sin(th),
            "e0": float(c.get("ProjectOriginE", 0.0)),
            "n0": float(c.get("ProjectOriginN", 0.0)),
            "z0": float(c.get("ProjectOriginZ", 0.0)),
            "lx": float(c.get("LocalOriginX", 0.0)),
            "ly": float(c.get("LocalOriginY", 0.0)),
            "lz": float(c.get("LocalOriginZ", 0.0)),
        }

    @staticmethod
    def _world_point_to_local(p, tr):
        de = float(p.x) - float(tr["e0"])
        dn = float(p.y) - float(tr["n0"])
        x = float(tr["lx"]) + float(tr["cs"]) * de + float(tr["sn"]) * dn
        y = float(tr["ly"]) - float(tr["sn"]) * de + float(tr["cs"]) * dn
        z = float(tr["lz"]) + (float(p.z) - float(tr["z0"]))
        return App.Vector(x, y, z)

    def _triangles_world_to_local_progress(self, doc_or_obj, triangles, pct0: float, pct1: float, label: str):
        if not triangles:
            return []
        tr = self._world_to_local_params(doc_or_obj)
        out = []
        n = max(1, int(len(triangles)))
        report_every = max(20, min(2000, n // 100))
        if self._report_progress(pct0, label):
            raise _CanceledError("Canceled by user.")
        for i, tri in enumerate(triangles, start=1):
            try:
                p0, p1, p2, _bb = tri
                q0 = self._world_point_to_local(p0, tr)
                q1 = self._world_point_to_local(p1, tr)
                q2 = self._world_point_to_local(p2, tr)
                bb = DesignTerrain._triangle_bbox_xy(q0, q1, q2)
                out.append((q0, q1, q2, bb))
            except Exception:
                pass
            if (i % report_every) == 0:
                pct = float(pct0) + (float(pct1) - float(pct0)) * (float(i) / float(n))
                if self._report_progress(pct, f"{label}: {i}/{n}"):
                    raise _CanceledError("Canceled by user.")
        return out

    @staticmethod
    def _triangles_bounds_xy(triangles):
        if not triangles:
            raise Exception("No triangles available for bounds.")
        x0 = None
        x1 = None
        y0 = None
        y1 = None
        for _p0, _p1, _p2, bb in triangles:
            bx0, bx1, by0, by1 = bb
            x0 = float(bx0) if x0 is None else min(float(x0), float(bx0))
            x1 = float(bx1) if x1 is None else max(float(x1), float(bx1))
            y0 = float(by0) if y0 is None else min(float(y0), float(by0))
            y1 = float(by1) if y1 is None else max(float(y1), float(by1))
        return float(x0), float(x1), float(y0), float(y1)

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
            eg_coords = str(getattr(obj, "ExistingTerrainCoords", "Local") or "Local")
            use_world_existing = eg_coords == "World"

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
            if self._report_progress(8.0, "Reading design grading mesh"):
                raise _CanceledError("Canceled by user.")
            tri_d = self._triangles_from_mesh_progress(dsg, 8.0, 12.0, "Reading design grading mesh")

            tri_e = self._triangles_from_mesh_progress(eg, 12.0, 20.0, "Reading existing terrain mesh")
            if use_world_existing:
                tri_e = self._triangles_world_to_local_progress(
                    obj,
                    tri_e,
                    20.0,
                    24.0,
                    "Transforming existing terrain to local",
                )

            bx0, bx1, by0, by1 = self._triangles_bounds_xy(tri_e)
            xmin = float(bx0 - margin)
            xmax = float(bx1 + margin)
            ymin = float(by0 - margin)
            ymax = float(by1 + margin)
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

            if len(tri_d) > max_tri:
                tri_d = DesignTerrain._decimate_triangles(tri_d, max_tri)
            if len(tri_e) > max_tri:
                tri_e = DesignTerrain._decimate_triangles(tri_e, max_tri)

            buck_d, wide_d = self._build_xy_buckets_progress(
                tri_d, cell, 24.0, 32.0, "Bucketing design terrain triangles"
            )
            buck_e, wide_e = self._build_xy_buckets_progress(
                tri_e, cell, 32.0, 40.0, "Bucketing existing terrain triangles"
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
            "ExistingTerrainCoords",
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
                if prop == "RebuildNow" and bool(getattr(obj, "RebuildNow", False)) and obj.Document is not None:
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
