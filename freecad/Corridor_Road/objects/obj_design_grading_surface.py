# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/objects/obj_design_grading_surface.py
from freecad.Corridor_Road.objects.obj_section_set import (
    SectionSet,
    _display_only_status_token,
    _earthwork_status_token,
    _external_shape_display_count,
    _external_shape_proxy_count,
    _status_join,
)
from freecad.Corridor_Road.objects.section_strip_builder import build_mesh_from_point_lists
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


def _report_row(kind: str, **fields) -> str:
    parts = [str(kind or "").strip() or "row"]
    for key, value in fields.items():
        parts.append(f"{str(key)}={value}")
    return "|".join(parts)


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
    if not hasattr(obj, "SubassemblySchemaVersion"):
        obj.addProperty("App::PropertyInteger", "SubassemblySchemaVersion", "Result", "Practical subassembly schema version")
        obj.SubassemblySchemaVersion = 0
    if not hasattr(obj, "PracticalSectionMode"):
        obj.addProperty("App::PropertyString", "PracticalSectionMode", "Result", "Practical section mode summary")
        obj.PracticalSectionMode = "simple"
    if not hasattr(obj, "TypicalSectionAdvancedComponentCount"):
        obj.addProperty("App::PropertyInteger", "TypicalSectionAdvancedComponentCount", "Result", "Advanced typical-section component count")
        obj.TypicalSectionAdvancedComponentCount = 0
    if not hasattr(obj, "PavementLayerCount"):
        obj.addProperty("App::PropertyInteger", "PavementLayerCount", "Result", "Typical-section pavement layer count")
        obj.PavementLayerCount = 0
    if not hasattr(obj, "EnabledPavementLayerCount"):
        obj.addProperty("App::PropertyInteger", "EnabledPavementLayerCount", "Result", "Enabled typical-section pavement layer count")
        obj.EnabledPavementLayerCount = 0
    if not hasattr(obj, "PavementTotalThickness"):
        obj.addProperty("App::PropertyFloat", "PavementTotalThickness", "Result", "Typical-section pavement total thickness")
        obj.PavementTotalThickness = 0.0
    if not hasattr(obj, "PavementLayerSummaryRows"):
        obj.addProperty("App::PropertyStringList", "PavementLayerSummaryRows", "Result", "Enabled pavement layer report rows")
        obj.PavementLayerSummaryRows = []
    if not hasattr(obj, "SubassemblyContractRows"):
        obj.addProperty("App::PropertyStringList", "SubassemblyContractRows", "Result", "Resolved subassembly contract rows")
        obj.SubassemblyContractRows = []
    if not hasattr(obj, "SubassemblyValidationRows"):
        obj.addProperty("App::PropertyStringList", "SubassemblyValidationRows", "Result", "Resolved subassembly validation rows")
        obj.SubassemblyValidationRows = []
    if not hasattr(obj, "RoadsideLibraryRows"):
        obj.addProperty("App::PropertyStringList", "RoadsideLibraryRows", "Result", "Detected reusable roadside-library rows")
        obj.RoadsideLibraryRows = []
    if not hasattr(obj, "RoadsideLibrarySummary"):
        obj.addProperty("App::PropertyString", "RoadsideLibrarySummary", "Result", "Detected reusable roadside-library summary")
        obj.RoadsideLibrarySummary = "-"
    if not hasattr(obj, "ReportSchemaVersion"):
        obj.addProperty("App::PropertyInteger", "ReportSchemaVersion", "Result", "Structured report schema version")
        obj.ReportSchemaVersion = 1
    if not hasattr(obj, "SectionComponentSummaryRows"):
        obj.addProperty("App::PropertyStringList", "SectionComponentSummaryRows", "Result", "Structured section-component summary rows")
        obj.SectionComponentSummaryRows = []
    if not hasattr(obj, "PavementScheduleRows"):
        obj.addProperty("App::PropertyStringList", "PavementScheduleRows", "Result", "Structured pavement schedule rows")
        obj.PavementScheduleRows = []
    if not hasattr(obj, "StructureInteractionSummaryRows"):
        obj.addProperty("App::PropertyStringList", "StructureInteractionSummaryRows", "Result", "Structured structure-interaction summary rows")
        obj.StructureInteractionSummaryRows = []
    if not hasattr(obj, "ExportSummaryRows"):
        obj.addProperty("App::PropertyStringList", "ExportSummaryRows", "Result", "Structured export-ready summary rows")
        obj.ExportSummaryRows = []

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
    def _validate_profiles(profiles):
        if len(list(profiles or [])) < 2:
            raise Exception("Need at least 2 section profiles to build design surface.")

        stations = []
        point_lists = []
        ref_n = None
        for idx, profile in enumerate(list(profiles or [])):
            station = float(profile.get("station", 0.0) or 0.0)
            if not _is_finite(station):
                raise Exception(f"SectionProfile[{idx}] station is not finite.")
            if stations and station <= stations[-1] + 1e-9:
                raise Exception("SectionProfile stations must be strictly increasing.")

            points = list(profile.get("points", []) or [])
            if len(points) < 2:
                raise Exception(f"SectionProfile[{idx}] has insufficient points.")
            if ref_n is None:
                ref_n = len(points)
            elif len(points) != ref_n:
                raise Exception(
                    f"SectionProfile point count mismatch at index {idx}: {len(points)} != {ref_n}. "
                    "Design surface stopped by section contract."
                )
            axis = points[0] - points[-1]
            if axis.Length <= 1e-12:
                raise Exception(f"SectionProfile[{idx}] left/right axis is degenerate.")
            stations.append(float(station))
            point_lists.append(list(points))

        return stations, point_lists, int(ref_n or 0)

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
                obj.SubassemblySchemaVersion = 0
                obj.PracticalSectionMode = "simple"
                obj.TypicalSectionAdvancedComponentCount = 0
                obj.PavementLayerCount = 0
                obj.EnabledPavementLayerCount = 0
                obj.PavementTotalThickness = 0.0
                obj.PavementLayerSummaryRows = []
                obj.SubassemblyContractRows = []
                obj.SubassemblyValidationRows = []
                obj.RoadsideLibraryRows = []
                obj.RoadsideLibrarySummary = "-"
                obj.ReportSchemaVersion = 1
                obj.SectionComponentSummaryRows = []
                obj.PavementScheduleRows = []
                obj.StructureInteractionSummaryRows = []
                obj.ExportSummaryRows = []
                obj.Status = "Missing SourceSectionSet"
                _mark_recompute_flag(obj, False)
                return

            profiles, _profile_rows, pt_count = SectionSet.resolve_section_profiles(src)
            stations, pts, pt_count = DesignGradingSurface._validate_profiles(profiles)
            mesh_out, quad_count, tri_count = build_mesh_from_point_lists(pts)
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
            obj.SubassemblySchemaVersion = int(getattr(src, "SubassemblySchemaVersion", 0) or 0)
            obj.PracticalSectionMode = str(getattr(src, "PracticalSectionMode", "simple") or "simple")
            obj.TypicalSectionAdvancedComponentCount = int(getattr(src, "TypicalSectionAdvancedComponentCount", 0) or 0)
            obj.PavementLayerCount = int(getattr(src, "PavementLayerCount", 0) or 0)
            obj.EnabledPavementLayerCount = int(getattr(src, "EnabledPavementLayerCount", 0) or 0)
            obj.PavementTotalThickness = float(getattr(src, "PavementTotalThickness", 0.0) or 0.0)
            obj.PavementLayerSummaryRows = list(getattr(src, "PavementLayerSummaryRows", []) or [])
            obj.SubassemblyContractRows = list(getattr(src, "SubassemblyContractRows", []) or [])
            obj.SubassemblyValidationRows = list(getattr(src, "SubassemblyValidationRows", []) or [])
            obj.RoadsideLibraryRows = list(getattr(src, "RoadsideLibraryRows", []) or [])
            obj.RoadsideLibrarySummary = str(getattr(src, "RoadsideLibrarySummary", "-") or "-")
            obj.ReportSchemaVersion = int(getattr(src, "ReportSchemaVersion", 1) or 1)
            obj.SectionComponentSummaryRows = list(getattr(src, "SectionComponentSummaryRows", []) or [])
            obj.PavementScheduleRows = list(getattr(src, "PavementScheduleRows", []) or [])
            obj.StructureInteractionSummaryRows = list(getattr(src, "StructureInteractionSummaryRows", []) or [])
            try:
                fc = int(getattr(getattr(obj, "Mesh", None), "CountFacets", 0))
            except Exception:
                fc = 0
            try:
                ss = getattr(src, "StructureSet", None) if bool(getattr(src, "UseStructureSet", False)) else None
            except Exception:
                ss = None
            ext_count = _external_shape_display_count(ss)
            ext_proxy_count = _external_shape_proxy_count(ss)
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
                    proxy_count=ext_proxy_count,
                    overrides_enabled=bool(getattr(src, "ApplyStructureOverrides", False)),
                ),
            ]
            if int(getattr(obj, "SubassemblySchemaVersion", 0) or 0) > 0:
                status_tokens.append(f"subSchema={int(getattr(obj, 'SubassemblySchemaVersion', 0) or 0)}")
                status_tokens.append(f"practical={str(getattr(obj, 'PracticalSectionMode', 'simple') or 'simple')}")
            if str(getattr(obj, "RoadsideLibrarySummary", "-") or "-") != "-":
                status_tokens.append(f"roadside={str(getattr(obj, 'RoadsideLibrarySummary', '-') or '-')}")
            if int(getattr(src, "BenchAppliedSectionCount", 0) or 0) > 0:
                bench_summary = str(getattr(src, "BenchSummary", "-") or "-")
                if bench_summary.startswith("mode="):
                    bench_mode = bench_summary.split(",", 1)[0].split("=", 1)[-1].strip() or "both"
                else:
                    bench_mode = "both"
                status_tokens.append(f"bench={bench_mode}")
                status_tokens.append(f"benchSections={int(getattr(src, 'BenchAppliedSectionCount', 0) or 0)}")
                if int(getattr(src, "BenchDaylightAdjustedSectionCount", 0) or 0) > 0:
                    status_tokens.append(f"benchDayAdj={int(getattr(src, 'BenchDaylightAdjustedSectionCount', 0) or 0)}")
                if int(getattr(src, "BenchDaylightSkippedSectionCount", 0) or 0) > 0:
                    status_tokens.append(f"benchDaySkip={int(getattr(src, 'BenchDaylightSkippedSectionCount', 0) or 0)}")
            if len(list(getattr(obj, "SubassemblyValidationRows", []) or [])) > 0:
                status_tokens.append(f"subWarn={len(list(getattr(obj, 'SubassemblyValidationRows', []) or []))}")
            if int(getattr(obj, "TypicalSectionAdvancedComponentCount", 0) or 0) > 0:
                status_tokens.append(f"typicalAdvanced={int(getattr(obj, 'TypicalSectionAdvancedComponentCount', 0) or 0)}")
            if int(getattr(obj, "PavementLayerCount", 0) or 0) > 0:
                status_tokens.append(
                    f"pavLayers={int(getattr(obj, 'EnabledPavementLayerCount', 0) or 0)}/{int(getattr(obj, 'PavementLayerCount', 0) or 0)}"
                )
            try:
                st_count = int(getattr(src, "ResolvedStructureCount", 0) or 0)
            except Exception:
                st_count = 0
            if st_count > 0:
                status_tokens.append(f"structures={st_count}")
            if ext_count > 0:
                status_tokens.append(_display_only_status_token(ext_count))
                status_tokens.append(f"externalShapeDisplayOnly={int(ext_count)}")
            if ext_proxy_count > 0:
                status_tokens.append(f"externalShapeProxy={int(ext_proxy_count)}")
            obj.Status = _status_join("OK (Mesh)", *status_tokens)
            obj.ExportSummaryRows = [
                _report_row(
                    "export",
                    target="design_grading_surface",
                    reportSchema=int(getattr(obj, "ReportSchemaVersion", 1) or 1),
                    sectionSchema=int(getattr(obj, "SchemaVersion", 0) or 0),
                    practical=str(getattr(obj, "PracticalSectionMode", "simple") or "simple"),
                    sections=int(len(stations)),
                    faces=int(quad_count),
                    pointCount=int(pt_count),
                    benchSections=int(getattr(src, "BenchAppliedSectionCount", 0) or 0),
                    benchAdjusted=int(getattr(src, "BenchDaylightAdjustedSectionCount", 0) or 0),
                    benchSkipped=int(getattr(src, "BenchDaylightSkippedSectionCount", 0) or 0),
                    roadside=str(getattr(obj, "RoadsideLibrarySummary", "-") or "-"),
                )
            ]
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
            obj.SubassemblySchemaVersion = 0
            obj.PracticalSectionMode = "fallback"
            obj.TypicalSectionAdvancedComponentCount = 0
            obj.PavementLayerCount = 0
            obj.EnabledPavementLayerCount = 0
            obj.PavementTotalThickness = 0.0
            obj.PavementLayerSummaryRows = []
            obj.SubassemblyContractRows = []
            obj.SubassemblyValidationRows = []
            obj.RoadsideLibraryRows = []
            obj.RoadsideLibrarySummary = "-"
            obj.ReportSchemaVersion = 1
            obj.SectionComponentSummaryRows = []
            obj.PavementScheduleRows = []
            obj.StructureInteractionSummaryRows = []
            obj.ExportSummaryRows = []
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
