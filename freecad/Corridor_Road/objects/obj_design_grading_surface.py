# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/objects/obj_design_grading_surface.py
from freecad.Corridor_Road.objects.obj_section_set import (
    SectionSet,
    _display_only_status_token,
    _earthwork_status_token,
    _external_shape_display_count,
    _status_join,
)
_RECOMP_LABEL_SUFFIX = " [Recompute]"


def _is_finite(x: float) -> bool:
    try:
        import math

        return math.isfinite(float(x))
    except Exception:
        return False


def _dedupe_consecutive_points(points, tol: float = 1e-9):
    out = []
    for p in points:
        if not out:
            out.append(p)
            continue
        if (p - out[-1]).Length > tol:
            out.append(p)
    return out


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


def _mark_design_terrain_needs_recompute(obj_dep):
    try:
        if hasattr(obj_dep, "NeedsRecompute"):
            obj_dep.NeedsRecompute = True
    except Exception:
        pass
    try:
        st = str(getattr(obj_dep, "Status", "") or "")
        if "NEEDS_RECOMPUTE" not in st:
            obj_dep.Status = "NEEDS_RECOMPUTE: Source DesignGradingSurface changed."
    except Exception:
        pass
    try:
        label = str(getattr(obj_dep, "Label", "") or "")
        if _RECOMP_LABEL_SUFFIX not in label:
            obj_dep.Label = f"{label}{_RECOMP_LABEL_SUFFIX}"
    except Exception:
        pass


def _empty_mesh():
    try:
        import Mesh

        return Mesh.Mesh()
    except Exception:
        return None


def ensure_design_grading_surface_properties(obj):
    if not hasattr(obj, "SourceSectionSet"):
        obj.addProperty("App::PropertyLink", "SourceSectionSet", "DesignSurface", "SectionSet source")

    if not hasattr(obj, "AutoUpdate"):
        obj.addProperty("App::PropertyBool", "AutoUpdate", "DesignSurface", "Auto update from source changes")
        obj.AutoUpdate = True

    if not hasattr(obj, "RebuildNow"):
        obj.addProperty("App::PropertyBool", "RebuildNow", "DesignSurface", "Set True to force rebuild now")
        obj.RebuildNow = False

    if not hasattr(obj, "NeedsRecompute"):
        obj.addProperty("App::PropertyBool", "NeedsRecompute", "Result", "Marked when source updates require recompute")
        obj.NeedsRecompute = False

    if not hasattr(obj, "SectionCount"):
        obj.addProperty("App::PropertyInteger", "SectionCount", "Result", "Used section count")
        obj.SectionCount = 0

    if not hasattr(obj, "PointCountPerSection"):
        obj.addProperty("App::PropertyInteger", "PointCountPerSection", "Result", "Point count per section")
        obj.PointCountPerSection = 0

    if not hasattr(obj, "FaceCount"):
        obj.addProperty("App::PropertyInteger", "FaceCount", "Result", "Generated face count")
        obj.FaceCount = 0

    if not hasattr(obj, "SchemaVersion"):
        obj.addProperty("App::PropertyInteger", "SchemaVersion", "Result", "Section schema version used")
        obj.SchemaVersion = 0
    if not hasattr(obj, "TopProfileSource"):
        obj.addProperty("App::PropertyString", "TopProfileSource", "Result", "Top-profile source summary")
        obj.TopProfileSource = "assembly_simple"
    if not hasattr(obj, "TopProfileEdgeSummary"):
        obj.addProperty("App::PropertyString", "TopProfileEdgeSummary", "Result", "Outermost top-profile edge component summary")
        obj.TopProfileEdgeSummary = "-"
    if not hasattr(obj, "PavementLayerCount"):
        obj.addProperty("App::PropertyInteger", "PavementLayerCount", "Result", "Typical-section pavement layer count")
        obj.PavementLayerCount = 0
    if not hasattr(obj, "EnabledPavementLayerCount"):
        obj.addProperty("App::PropertyInteger", "EnabledPavementLayerCount", "Result", "Enabled typical-section pavement layer count")
        obj.EnabledPavementLayerCount = 0
    if not hasattr(obj, "PavementTotalThickness"):
        obj.addProperty("App::PropertyFloat", "PavementTotalThickness", "Result", "Typical-section pavement total thickness")
        obj.PavementTotalThickness = 0.0

    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"
    if not hasattr(obj, "Mesh"):
        try:
            obj.addProperty("Mesh::PropertyMeshKernel", "Mesh", "Result", "Generated grading mesh")
            em = _empty_mesh()
            if em is not None:
                obj.Mesh = em
        except Exception:
            pass


class DesignGradingSurface:
    """
    Design grading surface (road + side slopes) generated from SectionSet wires.
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "DesignGradingSurface"
        ensure_design_grading_surface_properties(obj)

    @staticmethod
    def _wire_points(wire):
        edges = list(getattr(wire, "Edges", []) or [])
        if not edges:
            return []
        pts = [edges[0].valueAt(edges[0].FirstParameter)]
        for e in edges:
            pts.append(e.valueAt(e.LastParameter))
        return _dedupe_consecutive_points(pts)

    @staticmethod
    def _validate_and_points(stations, wires):
        if len(stations) < 2 or len(wires) < 2:
            raise Exception("Need at least 2 sections to build design surface.")
        if len(stations) != len(wires):
            raise Exception("Stations/wires size mismatch.")

        st = [float(s) for s in stations]
        for i, s in enumerate(st):
            if not _is_finite(s):
                raise Exception(f"Station[{i}] is not finite.")
            if i >= 1 and s <= st[i - 1] + 1e-9:
                raise Exception("Station values must be strictly increasing.")

        pt_lists = []
        ref_n = None
        for i, w in enumerate(wires):
            pts = DesignGradingSurface._wire_points(w)
            if len(pts) < 2:
                raise Exception(f"Section[{i}] has insufficient points.")
            if ref_n is None:
                ref_n = len(pts)
            elif len(pts) != ref_n:
                raise Exception(
                    f"Section point count mismatch at index {i}: {len(pts)} != {ref_n}. "
                    "Design surface stopped by section contract."
                )
            pt_lists.append(pts)

        # SectionSet.build_section_wires already stabilizes N-direction with prev_n.
        # Keep source point order as-is; additional auto-flip can mis-detect
        # heading rotation as a true left/right inversion.
        out = []
        for i, pts in enumerate(pt_lists):
            axis = pts[0] - pts[-1]
            if axis.Length <= 1e-12:
                raise Exception(f"Section[{i}] left/right axis is degenerate.")
            out.append(pts)

        return out, int(ref_n or 0)

    @staticmethod
    def _add_triangle(mesh_out, p0, p1, p2, area_tol: float = 1e-12):
        try:
            if (p1 - p0).Length <= area_tol or (p2 - p0).Length <= area_tol:
                return 0
            n = (p1 - p0).cross(p2 - p0)
            if n.Length <= area_tol:
                return 0
            mesh_out.addFacet(p0, p1, p2)
            return 1
        except Exception:
            return 0

    @staticmethod
    def _build_mesh_from_sections(pt_lists):
        import Mesh

        m = Mesh.Mesh()
        quad_count = 0
        tri_count = 0
        for i in range(len(pt_lists) - 1):
            a = pt_lists[i]
            b = pt_lists[i + 1]
            for j in range(len(a) - 1):
                p00 = a[j]
                p01 = a[j + 1]
                p10 = b[j]
                p11 = b[j + 1]
                tri_count += DesignGradingSurface._add_triangle(m, p00, p01, p11)
                tri_count += DesignGradingSurface._add_triangle(m, p00, p11, p10)
                quad_count += 1
        return m, int(quad_count), int(tri_count)

    def execute(self, obj):
        ensure_design_grading_surface_properties(obj)
        try:
            src = getattr(obj, "SourceSectionSet", None)
            if src is None:
                if hasattr(obj, "Mesh"):
                    em = _empty_mesh()
                    if em is not None:
                        obj.Mesh = em
                obj.SectionCount = 0
                obj.PointCountPerSection = 0
                obj.FaceCount = 0
                obj.SchemaVersion = 0
                obj.TopProfileSource = "assembly_simple"
                obj.TopProfileEdgeSummary = "-"
                obj.PavementLayerCount = 0
                obj.EnabledPavementLayerCount = 0
                obj.PavementTotalThickness = 0.0
                obj.Status = "Missing SourceSectionSet"
                _mark_recompute_flag(obj, False)
                return

            stations, wires, _tf, _so = SectionSet.build_section_wires(src)
            pts, pt_count = DesignGradingSurface._validate_and_points(stations, wires)
            mesh_out, quad_count, tri_count = DesignGradingSurface._build_mesh_from_sections(pts)
            if tri_count <= 0:
                raise Exception("No valid grading mesh triangles were generated.")

            if hasattr(obj, "Mesh"):
                obj.Mesh = mesh_out
            obj.SectionCount = int(len(stations))
            obj.PointCountPerSection = int(pt_count)
            obj.FaceCount = int(quad_count)
            obj.SchemaVersion = int(getattr(src, "SectionSchemaVersion", 0))
            obj.TopProfileSource = str(getattr(src, "TopProfileSource", "assembly_simple") or "assembly_simple")
            obj.TopProfileEdgeSummary = str(getattr(src, "TopProfileEdgeSummary", "-") or "-")
            obj.PavementLayerCount = int(getattr(src, "PavementLayerCount", 0) or 0)
            obj.EnabledPavementLayerCount = int(getattr(src, "EnabledPavementLayerCount", 0) or 0)
            obj.PavementTotalThickness = float(getattr(src, "PavementTotalThickness", 0.0) or 0.0)
            try:
                fc = int(getattr(getattr(obj, "Mesh", None), "CountFacets", 0))
            except Exception:
                fc = 0
            try:
                ss = getattr(src, "StructureSet", None) if bool(getattr(src, "UseStructureSet", False)) else None
            except Exception:
                ss = None
            ext_count = _external_shape_display_count(ss)
            status_tokens = [
                f"quads={quad_count}",
                f"facets={fc}",
                f"schema={int(obj.SchemaVersion)}",
                f"topProfile={obj.TopProfileSource}",
                f"topEdges={obj.TopProfileEdgeSummary}",
                f"pavement={obj.PavementTotalThickness:.3f}m",
                _earthwork_status_token(
                    struct_src=ss,
                    resolved_count=int(getattr(src, "ResolvedStructureCount", 0) or 0),
                    ext_count=ext_count,
                    overrides_enabled=bool(getattr(src, "ApplyStructureOverrides", False)),
                ),
            ]
            try:
                st_count = int(getattr(src, "ResolvedStructureCount", 0) or 0)
            except Exception:
                st_count = 0
            if st_count > 0:
                status_tokens.append(f"structures={st_count}")
            if ext_count > 0:
                status_tokens.append(_display_only_status_token(ext_count))
                status_tokens.append(f"externalShapeDisplayOnly={int(ext_count)}")
            obj.Status = _status_join("OK (Mesh)", *status_tokens)
            _mark_recompute_flag(obj, False)

            # Push updates to linked DesignTerrain objects as pending recompute.
            if obj.Document is not None:
                for o in list(obj.Document.Objects):
                    try:
                        if getattr(o, "SourceDesignSurface", None) == obj and bool(getattr(o, "AutoUpdate", True)):
                            _mark_design_terrain_needs_recompute(o)
                    except Exception:
                        pass

            if bool(getattr(obj, "RebuildNow", False)):
                obj.RebuildNow = False

        except Exception as ex:
            if hasattr(obj, "Mesh"):
                em = _empty_mesh()
                if em is not None:
                    obj.Mesh = em
            obj.SectionCount = 0
            obj.PointCountPerSection = 0
            obj.FaceCount = 0
            obj.SchemaVersion = 0
            obj.TopProfileSource = "assembly_simple"
            obj.TopProfileEdgeSummary = "-"
            obj.PavementLayerCount = 0
            obj.EnabledPavementLayerCount = 0
            obj.PavementTotalThickness = 0.0
            obj.Status = f"ERROR: {ex}"
            _mark_recompute_flag(obj, False)

    def onChanged(self, obj, prop):
        if prop in (
            "SourceSectionSet",
            "AutoUpdate",
            "RebuildNow",
        ):
            try:
                if prop == "RebuildNow":
                    if not bool(getattr(obj, "RebuildNow", False)):
                        return
                elif not bool(getattr(obj, "AutoUpdate", True)):
                    try:
                        obj.Status = "NEEDS_RECOMPUTE: source/parameters changed"
                    except Exception:
                        pass
                    return

                obj.touch()
                if prop == "RebuildNow" and bool(getattr(obj, "RebuildNow", False)) and obj.Document is not None:
                    obj.Document.recompute()
            except Exception:
                pass


class ViewProviderDesignGradingSurface:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Shaded"
            vobj.Transparency = 20
            vobj.LineWidth = 1
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
