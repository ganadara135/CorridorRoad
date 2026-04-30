# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/objects/obj_project.py
import FreeCAD as App
import math
import re
from freecad.Corridor_Road.objects import design_standards as _ds
from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.corridor_compat import (
    CORRIDOR_CHILD_LINK_PROPERTY,
    CORRIDOR_NAME_PREFIX,
    CORRIDOR_PROJECT_PROPERTY,
    CORRIDOR_PROXY_TYPE,
    CORRIDOR_SEGMENT_NAME,
    CORRIDOR_SKIP_MARKER_NAME,
)


TREE_KEY_PROP = "CRTreeKey"
ALN_REF_PROP = "CRAlignmentRef"
ALN_REF_NAME_PROP = "CRAlignmentRefName"
ALN_NAME_PROP = "CRAlignmentName"

TREE_INPUTS = "root_inputs"
TREE_INPUTS_TERRAINS = "inputs_terrains"
TREE_INPUTS_SURVEY = "inputs_survey"
TREE_INPUTS_STRUCTURES = "inputs_structures"
TREE_INPUTS_REGIONS = "inputs_regions"
TREE_ALIGNMENTS = "root_alignments"
TREE_SURFACES = "root_surfaces"
TREE_ANALYSIS = "root_analysis"
TREE_REFERENCES = "root_references"

V1_TREE_PROJECT_SETUP = "v1_project_setup"
V1_TREE_SOURCE_DATA = "v1_source_data"
V1_TREE_ALIGNMENT_PROFILE = "v1_alignment_profile"
V1_TREE_SURFACES = "v1_surfaces"
V1_TREE_CORRIDOR_MODEL = "v1_corridor_model"
V1_TREE_DRAINAGE = "v1_drainage"
V1_TREE_STRUCTURES = "v1_structures"
V1_TREE_QUANTITIES_EARTHWORK = "v1_quantities_earthwork"
V1_TREE_REVIEW = "v1_review"
V1_TREE_OUTPUTS_EXCHANGE = "v1_outputs_exchange"
V1_TREE_AI_ASSIST = "v1_ai_assist"

V1_TREE_PROJECT_SETTINGS = "v1_project_settings"
V1_TREE_COORDINATE_SYSTEM = "v1_coordinate_system"
V1_TREE_UNITS = "v1_units"
V1_TREE_STANDARDS = "v1_standards"
V1_TREE_SURVEY_POINTS = "v1_survey_points"
V1_TREE_SOURCE_FILES = "v1_source_files"
V1_TREE_EXISTING_REFERENCES = "v1_existing_references"
V1_TREE_ALIGNMENTS = "v1_alignments"
V1_TREE_PROFILES = "v1_profiles"
V1_TREE_STATIONS = "v1_stations"
V1_TREE_SUPERELEVATION = "v1_superelevation"
V1_TREE_EXISTING_GROUND_TIN = "v1_existing_ground_tin"
V1_TREE_EXISTING_GROUND_TIN_SOURCE = "v1_existing_ground_tin_source"
V1_TREE_EXISTING_GROUND_TIN_RESULT = "v1_existing_ground_tin_result"
V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW = "v1_existing_ground_tin_mesh_preview"
V1_TREE_EXISTING_GROUND_TIN_DIAGNOSTICS = "v1_existing_ground_tin_diagnostics"
V1_TREE_DESIGN_TIN = "v1_design_tin"
V1_TREE_COMPARISON_TIN = "v1_comparison_tin"
V1_TREE_ASSEMBLIES = "v1_assemblies"
V1_TREE_REGIONS = "v1_regions"
V1_TREE_APPLIED_SECTIONS = "v1_applied_sections"
V1_TREE_RAMPS = "v1_ramps"
V1_TREE_INTERSECTIONS = "v1_intersections"
V1_TREE_OVERRIDES = "v1_overrides"
V1_TREE_DITCHES = "v1_ditches"
V1_TREE_CULVERTS = "v1_culverts"
V1_TREE_INLETS = "v1_inlets"
V1_TREE_FLOW_PATHS = "v1_flow_paths"
V1_TREE_DRAINAGE_DIAGNOSTICS = "v1_drainage_diagnostics"
V1_TREE_RETAINING_WALLS = "v1_retaining_walls"
V1_TREE_BRIDGES = "v1_bridges"
V1_TREE_BARRIERS = "v1_barriers"
V1_TREE_STRUCTURE_INTERACTIONS = "v1_structure_interactions"
V1_TREE_QUANTITIES = "v1_quantities"
V1_TREE_CUT_FILL = "v1_cut_fill"
V1_TREE_MASS_HAUL = "v1_mass_haul"
V1_TREE_EARTHWORK_DIAGNOSTICS = "v1_earthwork_diagnostics"
V1_TREE_PLAN_PROFILE_REVIEW = "v1_plan_profile_review"
V1_TREE_SECTION_REVIEW = "v1_section_review"
V1_TREE_TIN_REVIEW = "v1_tin_review"
V1_TREE_ISSUES = "v1_issues"
V1_TREE_BOOKMARKS = "v1_bookmarks"
V1_TREE_SHEETS = "v1_sheets"
V1_TREE_REPORTS = "v1_reports"
V1_TREE_DXF = "v1_dxf"
V1_TREE_LANDXML = "v1_landxml"
V1_TREE_IFC = "v1_ifc"
V1_TREE_EXCHANGE_PACKAGES = "v1_exchange_packages"
V1_TREE_AI_SUGGESTIONS = "v1_ai_suggestions"
V1_TREE_AI_CHECKS = "v1_ai_checks"
V1_TREE_AI_GENERATED_ALTERNATIVES = "v1_ai_generated_alternatives"
V1_TREE_AI_USER_DECISIONS = "v1_ai_user_decisions"

ALIGNMENT_ROOT = "alignment_root"
ALIGNMENT_HORIZONTAL = "alignment_horizontal"
ALIGNMENT_STATIONING = "alignment_stationing"
ALIGNMENT_VERTICAL = "alignment_vertical_profiles"
ALIGNMENT_CENTERLINE = "alignment_centerline"
ALIGNMENT_ASSEMBLY = "alignment_assembly"
ALIGNMENT_REGIONS = "alignment_regions"
ALIGNMENT_SECTIONS = "alignment_sections"
ALIGNMENT_STRUCTURE_SECTIONS = "alignment_structure_sections"
ALIGNMENT_CORRIDOR = "alignment_corridor"

BASE_TREE_DEFS = (
    (TREE_INPUTS, "01_Inputs", "CR_01_Inputs"),
    (TREE_ALIGNMENTS, "02_Alignments", "CR_02_Alignments"),
    (TREE_SURFACES, "03_Surfaces", "CR_03_Surfaces"),
    (TREE_ANALYSIS, "04_Analysis", "CR_04_Analysis"),
)
V1_ROOT_TREE_DEFS = (
    (V1_TREE_PROJECT_SETUP, "00_Project Setup", "CRV1_00_Project_Setup"),
    (V1_TREE_SOURCE_DATA, "01_Source Data", "CRV1_01_Source_Data"),
    (V1_TREE_ALIGNMENT_PROFILE, "02_Alignment & Profile", "CRV1_02_Alignment_Profile"),
    (V1_TREE_SURFACES, "03_Surfaces", "CRV1_03_Surfaces"),
    (V1_TREE_CORRIDOR_MODEL, "04_Corridor Model", "CRV1_04_Corridor_Model"),
    (V1_TREE_DRAINAGE, "05_Drainage", "CRV1_05_Drainage"),
    (V1_TREE_STRUCTURES, "06_Structures", "CRV1_06_Structures"),
    (V1_TREE_QUANTITIES_EARTHWORK, "07_Quantities & Earthwork", "CRV1_07_Quantities_Earthwork"),
    (V1_TREE_REVIEW, "08_Review", "CRV1_08_Review"),
    (V1_TREE_OUTPUTS_EXCHANGE, "09_Outputs & Exchange", "CRV1_09_Outputs_Exchange"),
    (V1_TREE_AI_ASSIST, "10_AI Assist", "CRV1_10_AI_Assist"),
)
V1_SUBTREE_DEFS = (
    (V1_TREE_PROJECT_SETUP, V1_TREE_PROJECT_SETTINGS, "Project Settings", "CRV1_Project_Settings"),
    (V1_TREE_PROJECT_SETUP, V1_TREE_COORDINATE_SYSTEM, "Coordinate System", "CRV1_Coordinate_System"),
    (V1_TREE_PROJECT_SETUP, V1_TREE_UNITS, "Units", "CRV1_Units"),
    (V1_TREE_PROJECT_SETUP, V1_TREE_STANDARDS, "Standards", "CRV1_Standards"),
    (V1_TREE_SOURCE_DATA, V1_TREE_SURVEY_POINTS, "Survey Points", "CRV1_Survey_Points"),
    (V1_TREE_SOURCE_DATA, V1_TREE_SOURCE_FILES, "Source Files", "CRV1_Source_Files"),
    (V1_TREE_SOURCE_DATA, V1_TREE_EXISTING_REFERENCES, "Existing References", "CRV1_Existing_References"),
    (V1_TREE_ALIGNMENT_PROFILE, V1_TREE_ALIGNMENTS, "Alignments", "CRV1_Alignments"),
    (V1_TREE_ALIGNMENT_PROFILE, V1_TREE_STATIONS, "Stations", "CRV1_Stations"),
    (V1_TREE_ALIGNMENT_PROFILE, V1_TREE_PROFILES, "Profiles", "CRV1_Profiles"),
    (V1_TREE_ALIGNMENT_PROFILE, V1_TREE_SUPERELEVATION, "Superelevation", "CRV1_Superelevation"),
    (V1_TREE_SURFACES, V1_TREE_EXISTING_GROUND_TIN, "Existing Ground TIN", "CRV1_Existing_Ground_TIN"),
    (V1_TREE_EXISTING_GROUND_TIN, V1_TREE_EXISTING_GROUND_TIN_SOURCE, "Source", "CRV1_EG_TIN_Source"),
    (V1_TREE_EXISTING_GROUND_TIN, V1_TREE_EXISTING_GROUND_TIN_RESULT, "TIN Result", "CRV1_EG_TIN_Result"),
    (V1_TREE_EXISTING_GROUND_TIN, V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW, "Mesh Preview", "CRV1_EG_TIN_Mesh_Preview"),
    (V1_TREE_EXISTING_GROUND_TIN, V1_TREE_EXISTING_GROUND_TIN_DIAGNOSTICS, "Diagnostics", "CRV1_EG_TIN_Diagnostics"),
    (V1_TREE_SURFACES, V1_TREE_DESIGN_TIN, "Design TIN", "CRV1_Design_TIN"),
    (V1_TREE_SURFACES, V1_TREE_COMPARISON_TIN, "Comparison TIN", "CRV1_Comparison_TIN"),
    (V1_TREE_CORRIDOR_MODEL, V1_TREE_ASSEMBLIES, "Assemblies", "CRV1_Assemblies"),
    (V1_TREE_CORRIDOR_MODEL, V1_TREE_REGIONS, "Regions", "CRV1_Regions"),
    (V1_TREE_CORRIDOR_MODEL, V1_TREE_APPLIED_SECTIONS, "Applied Sections", "CRV1_Applied_Sections"),
    (V1_TREE_CORRIDOR_MODEL, V1_TREE_RAMPS, "Ramps", "CRV1_Ramps"),
    (V1_TREE_CORRIDOR_MODEL, V1_TREE_INTERSECTIONS, "Intersections", "CRV1_Intersections"),
    (V1_TREE_CORRIDOR_MODEL, V1_TREE_OVERRIDES, "Overrides", "CRV1_Overrides"),
    (V1_TREE_DRAINAGE, V1_TREE_DITCHES, "Ditches", "CRV1_Ditches"),
    (V1_TREE_DRAINAGE, V1_TREE_CULVERTS, "Culverts", "CRV1_Culverts"),
    (V1_TREE_DRAINAGE, V1_TREE_INLETS, "Inlets", "CRV1_Inlets"),
    (V1_TREE_DRAINAGE, V1_TREE_FLOW_PATHS, "Flow Paths", "CRV1_Flow_Paths"),
    (V1_TREE_DRAINAGE, V1_TREE_DRAINAGE_DIAGNOSTICS, "Drainage Diagnostics", "CRV1_Drainage_Diagnostics"),
    (V1_TREE_STRUCTURES, V1_TREE_RETAINING_WALLS, "Retaining Walls", "CRV1_Retaining_Walls"),
    (V1_TREE_STRUCTURES, V1_TREE_BRIDGES, "Bridges", "CRV1_Bridges"),
    (V1_TREE_STRUCTURES, V1_TREE_BARRIERS, "Barriers", "CRV1_Barriers"),
    (V1_TREE_STRUCTURES, V1_TREE_STRUCTURE_INTERACTIONS, "Structure Interactions", "CRV1_Structure_Interactions"),
    (V1_TREE_QUANTITIES_EARTHWORK, V1_TREE_QUANTITIES, "Quantities", "CRV1_Quantities"),
    (V1_TREE_QUANTITIES_EARTHWORK, V1_TREE_CUT_FILL, "Cut Fill", "CRV1_Cut_Fill"),
    (V1_TREE_QUANTITIES_EARTHWORK, V1_TREE_MASS_HAUL, "Mass Haul", "CRV1_Mass_Haul"),
    (V1_TREE_QUANTITIES_EARTHWORK, V1_TREE_EARTHWORK_DIAGNOSTICS, "Earthwork Diagnostics", "CRV1_Earthwork_Diagnostics"),
    (V1_TREE_REVIEW, V1_TREE_PLAN_PROFILE_REVIEW, "Plan Profile Review", "CRV1_Plan_Profile_Review"),
    (V1_TREE_REVIEW, V1_TREE_SECTION_REVIEW, "Section Review", "CRV1_Section_Review"),
    (V1_TREE_REVIEW, V1_TREE_TIN_REVIEW, "TIN Review", "CRV1_TIN_Review"),
    (V1_TREE_REVIEW, V1_TREE_ISSUES, "Issues", "CRV1_Issues"),
    (V1_TREE_REVIEW, V1_TREE_BOOKMARKS, "Bookmarks", "CRV1_Bookmarks"),
    (V1_TREE_OUTPUTS_EXCHANGE, V1_TREE_SHEETS, "Sheets", "CRV1_Sheets"),
    (V1_TREE_OUTPUTS_EXCHANGE, V1_TREE_REPORTS, "Reports", "CRV1_Reports"),
    (V1_TREE_OUTPUTS_EXCHANGE, V1_TREE_DXF, "DXF", "CRV1_DXF"),
    (V1_TREE_OUTPUTS_EXCHANGE, V1_TREE_LANDXML, "LandXML", "CRV1_LandXML"),
    (V1_TREE_OUTPUTS_EXCHANGE, V1_TREE_IFC, "IFC", "CRV1_IFC"),
    (V1_TREE_OUTPUTS_EXCHANGE, V1_TREE_EXCHANGE_PACKAGES, "Exchange Packages", "CRV1_Exchange_Packages"),
    (V1_TREE_AI_ASSIST, V1_TREE_AI_SUGGESTIONS, "Suggestions", "CRV1_AI_Suggestions"),
    (V1_TREE_AI_ASSIST, V1_TREE_AI_CHECKS, "Checks", "CRV1_AI_Checks"),
    (V1_TREE_AI_ASSIST, V1_TREE_AI_GENERATED_ALTERNATIVES, "Generated Alternatives", "CRV1_AI_Generated_Alternatives"),
    (V1_TREE_AI_ASSIST, V1_TREE_AI_USER_DECISIONS, "User Decisions", "CRV1_AI_User_Decisions"),
)
INPUT_SUBTREE_DEFS = (
    (TREE_INPUTS_TERRAINS, "Terrains", "CR_01_Inputs_Terrains"),
    (TREE_INPUTS_SURVEY, "Survey", "CR_01_Inputs_Survey"),
    (TREE_INPUTS_STRUCTURES, "Structures", "CR_01_Inputs_Structures"),
)
ALIGNMENT_SUBTREE_DEFS = (
    (ALIGNMENT_HORIZONTAL, "Horizontal", "CR_ALN_Horizontal"),
    (ALIGNMENT_STATIONING, "Stationing", "CR_ALN_Stationing"),
    (ALIGNMENT_VERTICAL, "VerticalProfiles", "CR_ALN_VerticalProfiles"),
    (ALIGNMENT_CENTERLINE, "3D Centerline", "CR_ALN_Centerline3D"),
    (ALIGNMENT_ASSEMBLY, "Assembly", "CR_ALN_Assembly"),
    (ALIGNMENT_REGIONS, "Regions", "CR_ALN_Regions"),
    (ALIGNMENT_SECTIONS, "Sections", "CR_ALN_Sections"),
    (ALIGNMENT_STRUCTURE_SECTIONS, "Structure Sections", "CR_ALN_StructureSections"),
    (ALIGNMENT_CORRIDOR, "Corridor", "CR_ALN_Corridor"),
)


def _find_first(doc, name_prefix: str):
    for o in doc.Objects:
        if o.Name.startswith(name_prefix):
            return o

    return None


def find_project(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        if o.Name.startswith("CorridorRoadProject"):
            return o
    return None


def _safe_scale(v, default: float = 1.0) -> float:
    try:
        x = float(v)
    except Exception:
        return float(default)
    if x <= 1e-12:
        return float(default)
    return float(x)


def get_design_standard(doc_or_project, default: str = _ds.DEFAULT_STANDARD) -> str:
    prj = _resolve_project(doc_or_project)
    if prj is None:
        return _ds.normalize_standard(default, default=default)
    raw = str(getattr(prj, "DesignStandard", default) or default)
    std = _ds.normalize_standard(raw, default=default)
    try:
        if str(getattr(prj, "DesignStandard", "") or "") != std:
            prj.DesignStandard = std
    except Exception:
        pass
    return std


def _safe_float(v, default: float = 0.0) -> float:
    try:
        x = float(v)
    except Exception:
        return float(default)
    if not math.isfinite(x):
        return float(default)
    return float(x)


def _safe_angle_deg(v, default: float = 0.0) -> float:
    return _safe_float(v, default=default)


def _resolve_project(doc_or_project):
    if doc_or_project is None:
        return None

    # Direct project object
    try:
        if (
            str(getattr(doc_or_project, "Name", "") or "").startswith("CorridorRoadProject")
            or (getattr(doc_or_project, "Proxy", None) and getattr(doc_or_project.Proxy, "Type", "") == "CorridorRoadProject")
        ):
            return doc_or_project
    except Exception:
        pass

    # Document
    try:
        if hasattr(doc_or_project, "Objects"):
            return find_project(doc_or_project)
    except Exception:
        pass

    # Any object with Document link
    try:
        doc = getattr(doc_or_project, "Document", None)
        if doc is not None:
            return find_project(doc)
    except Exception:
        pass

    return None


def get_coordinate_setup(doc_or_project):
    """
    Coordinate setup dictionary.
    - CRS/EPSG metadata
    - world origin (E/N/Z)
    - local origin (X/Y/Z)
    - north rotation (deg)
    """
    prj = _resolve_project(doc_or_project)
    if prj is None:
        return {
            "CRSEPSG": "",
            "HorizontalDatum": "",
            "VerticalDatum": "",
            "ProjectOriginE": 0.0,
            "ProjectOriginN": 0.0,
            "ProjectOriginZ": 0.0,
            "LocalOriginX": 0.0,
            "LocalOriginY": 0.0,
            "LocalOriginZ": 0.0,
            "NorthRotationDeg": 0.0,
            "CoordSetupLocked": False,
            "CoordSetupStatus": "Uninitialized",
            "CoordinateWorkflow": "Local-first",
            "AutoApplyCoordinateRecommendations": True,
        }

    return {
        "CRSEPSG": str(getattr(prj, "CRSEPSG", "") or "").strip(),
        "HorizontalDatum": str(getattr(prj, "HorizontalDatum", "") or "").strip(),
        "VerticalDatum": str(getattr(prj, "VerticalDatum", "") or "").strip(),
        "ProjectOriginE": _safe_float(getattr(prj, "ProjectOriginE", 0.0), default=0.0),
        "ProjectOriginN": _safe_float(getattr(prj, "ProjectOriginN", 0.0), default=0.0),
        "ProjectOriginZ": _safe_float(getattr(prj, "ProjectOriginZ", 0.0), default=0.0),
        "LocalOriginX": _safe_float(getattr(prj, "LocalOriginX", 0.0), default=0.0),
        "LocalOriginY": _safe_float(getattr(prj, "LocalOriginY", 0.0), default=0.0),
        "LocalOriginZ": _safe_float(getattr(prj, "LocalOriginZ", 0.0), default=0.0),
        "NorthRotationDeg": _safe_angle_deg(getattr(prj, "NorthRotationDeg", 0.0), default=0.0),
        "CoordSetupLocked": bool(getattr(prj, "CoordSetupLocked", False)),
        "CoordSetupStatus": str(getattr(prj, "CoordSetupStatus", "Uninitialized") or "Uninitialized"),
        "CoordinateWorkflow": str(getattr(prj, "CoordinateWorkflow", "") or "").strip(),
        "AutoApplyCoordinateRecommendations": bool(getattr(prj, "AutoApplyCoordinateRecommendations", True)),
    }


def get_coordinate_workflow(doc_or_project, default: str = "") -> str:
    cst = get_coordinate_setup(doc_or_project)
    workflow = str(cst.get("CoordinateWorkflow", "") or "").strip()
    if workflow in ("World-first", "Local-first", "Custom"):
        return workflow
    epsg = str(cst.get("CRSEPSG", "") or "").strip()
    return "World-first" if epsg else ("Local-first" if not default else str(default))


def local_to_world(doc_or_project, x: float, y: float, z: float):
    """
    Convert local model XYZ to world ENZ using project coordinate setup.
    Rotation is around +Z, CCW positive (degrees).
    """
    c = get_coordinate_setup(doc_or_project)
    th = math.radians(float(c["NorthRotationDeg"]))
    cs = math.cos(th)
    sn = math.sin(th)

    dx = float(x) - float(c["LocalOriginX"])
    dy = float(y) - float(c["LocalOriginY"])

    de = cs * dx - sn * dy
    dn = sn * dx + cs * dy

    e = float(c["ProjectOriginE"]) + de
    n = float(c["ProjectOriginN"]) + dn
    zz = float(c["ProjectOriginZ"]) + (float(z) - float(c["LocalOriginZ"]))
    return float(e), float(n), float(zz)


def world_to_local(doc_or_project, e: float, n: float, z: float):
    """
    Convert world ENZ to local model XYZ using project coordinate setup.
    """
    c = get_coordinate_setup(doc_or_project)
    th = math.radians(float(c["NorthRotationDeg"]))
    cs = math.cos(th)
    sn = math.sin(th)

    de = float(e) - float(c["ProjectOriginE"])
    dn = float(n) - float(c["ProjectOriginN"])

    dx = cs * de + sn * dn
    dy = -sn * de + cs * dn

    x = float(c["LocalOriginX"]) + dx
    y = float(c["LocalOriginY"]) + dy
    zz = float(c["LocalOriginZ"]) + (float(z) - float(c["ProjectOriginZ"]))
    return float(x), float(y), float(zz)


def local_to_world_vec(doc_or_project, p_local):
    e, n, z = local_to_world(doc_or_project, float(p_local.x), float(p_local.y), float(p_local.z))
    return App.Vector(e, n, z)


def world_to_local_vec(doc_or_project, p_world):
    x, y, z = world_to_local(doc_or_project, float(p_world.x), float(p_world.y), float(p_world.z))
    return App.Vector(x, y, z)


def _uniq_links(values):
    out = []
    seen = set()
    for v in list(values or []):
        if v is None:
            continue
        k = getattr(v, "Name", None) or str(id(v))
        if k in seen:
            continue
        seen.add(k)
        out.append(v)
    return out


def _group_get(owner):
    return list(getattr(owner, "Group", []) or [])


def _group_set(owner, children):
    try:
        owner.Group = _uniq_links(children)
    except Exception:
        pass


def _group_contains(owner, child):
    if owner is None or child is None:
        return False
    try:
        return child in _group_get(owner)
    except Exception:
        return False


def _group_add(owner, child):
    if owner is None or child is None:
        return
    cur = _group_get(owner)
    if child in cur:
        return
    # Prefer native group APIs when available (App::DocumentObjectGroup).
    try:
        add_fn = getattr(owner, "addObject", None)
        if callable(add_fn):
            add_fn(child)
            if _group_contains(owner, child):
                return
    except Exception:
        pass
    cur.append(child)
    _group_set(owner, cur)


def _group_remove(owner, child):
    if owner is None or child is None:
        return
    cur = _group_get(owner)
    if child not in cur:
        return
    try:
        rem_fn = getattr(owner, "removeObject", None)
        if callable(rem_fn):
            rem_fn(child)
            if (not _group_contains(owner, child)):
                return
    except Exception:
        pass
    _group_set(owner, [o for o in cur if o != child])


def _reorder_children_by_tree_keys(owner, ordered_keys) -> None:
    if owner is None:
        return
    children = _group_get(owner)
    if not children:
        return
    key_order = {str(key): index for index, key in enumerate(list(ordered_keys or []))}
    keyed = []
    others = []
    for index, child in enumerate(children):
        key = _tree_key(child)
        if key in key_order:
            keyed.append((key_order[key], index, child))
        else:
            others.append(child)
    ordered = [child for _order, _index, child in sorted(keyed, key=lambda row: (row[0], row[1]))] + others
    if ordered != children:
        _group_set(owner, ordered)


def _prune_root_nonfolders(prj):
    if prj is None:
        return
    cur = _group_get(prj)
    keep = [ch for ch in cur if _is_tree_folder(ch)]
    if len(keep) != len(cur):
        _group_set(prj, keep)
    _prune_empty_unassigned_alignment_roots(prj)


def _proxy_type(obj) -> str:
    try:
        p = getattr(obj, "Proxy", None)
        return str(getattr(p, "Type", "") or "")
    except Exception:
        return ""


def _name(obj) -> str:
    try:
        return str(getattr(obj, "Name", "") or "")
    except Exception:
        return ""


def _label(obj) -> str:
    try:
        return str(getattr(obj, "Label", "") or "")
    except Exception:
        return ""


def _is_group_obj(obj) -> bool:
    try:
        return bool(hasattr(obj, "Group"))
    except Exception:
        return False


def _tree_key(obj) -> str:
    try:
        return str(getattr(obj, TREE_KEY_PROP, "") or "")
    except Exception:
        return ""


def _is_tree_folder(obj) -> bool:
    return _is_group_obj(obj) and bool(_tree_key(obj))


def _ensure_folder_meta(group_obj, key: str):
    if group_obj is None:
        return
    try:
        if not hasattr(group_obj, TREE_KEY_PROP):
            group_obj.addProperty("App::PropertyString", TREE_KEY_PROP, "CorridorRoad", "CorridorRoad tree folder key")
    except Exception:
        pass
    try:
        setattr(group_obj, TREE_KEY_PROP, str(key))
    except Exception:
        pass


def _find_child_folder(owner, key: str):
    if owner is None:
        return None
    for ch in _group_get(owner):
        if not _is_group_obj(ch):
            continue
        if _tree_key(ch) == str(key):
            return ch
    return None


def _ensure_child_folder(doc, owner, key: str, label: str, obj_name: str):
    if doc is None or owner is None:
        return None

    folder = _find_child_folder(owner, key)
    if folder is None:
        # Label fallback for compatibility with manually created folders.
        for ch in _group_get(owner):
            if _is_group_obj(ch) and not _tree_key(ch) and _label(ch) == str(label):
                folder = ch
                break
    if folder is None:
        folder = doc.addObject("App::DocumentObjectGroup", str(obj_name))
        folder.Label = str(label)

    _ensure_folder_meta(folder, key)
    _group_add(owner, folder)
    return folder


def _iter_tree_folders(root):
    out = []
    seen = set()

    def _walk(node):
        for ch in _group_get(node):
            nm = _name(ch)
            if nm in seen:
                continue
            seen.add(nm)
            if _is_tree_folder(ch):
                out.append(ch)
                _walk(ch)

    _walk(root)
    return out


def _sanitize_tag(text: str, default_text: str = "Default") -> str:
    raw = str(text or "").strip()
    if not raw:
        return str(default_text)
    raw = re.sub(r"\s+", "_", raw)
    raw = re.sub(r"[^A-Za-z0-9_]+", "_", raw)
    raw = re.sub(r"_+", "_", raw).strip("_")
    if not raw:
        return str(default_text)
    return raw


def _ensure_alignment_folder_meta(group_obj, alignment_obj, alignment_name: str):
    if group_obj is None:
        return
    _ensure_folder_meta(group_obj, ALIGNMENT_ROOT)
    try:
        if not hasattr(group_obj, ALN_NAME_PROP):
            group_obj.addProperty("App::PropertyString", ALN_NAME_PROP, "CorridorRoad", "Alignment tag")
        setattr(group_obj, ALN_NAME_PROP, str(alignment_name))
    except Exception:
        pass
    try:
        if not hasattr(group_obj, ALN_REF_NAME_PROP):
            group_obj.addProperty("App::PropertyString", ALN_REF_NAME_PROP, "CorridorRoad", "Alignment object name")
        setattr(group_obj, ALN_REF_NAME_PROP, _name(alignment_obj))
    except Exception:
        pass
    # Legacy cleanup: avoid direct object link on alignment root (causes wrong tree child display).
    try:
        if hasattr(group_obj, ALN_REF_PROP):
            setattr(group_obj, ALN_REF_PROP, None)
            try:
                group_obj.setEditorMode(ALN_REF_PROP, 2)
            except Exception:
                pass
            try:
                group_obj.setPropertyStatus(ALN_REF_PROP, ["Hidden"])
            except Exception:
                pass
    except Exception:
        pass


def _alignment_ref_matches(aln_root, alignment_obj) -> bool:
    if aln_root is None or alignment_obj is None:
        return False
    try:
        if str(getattr(aln_root, ALN_REF_NAME_PROP, "") or "") == _name(alignment_obj):
            return True
    except Exception:
        pass
    try:
        if getattr(aln_root, ALN_REF_PROP, None) == alignment_obj:
            return True
    except Exception:
        pass
    return False


def _migrate_alignment_root_links(root_alignments):
    if root_alignments is None:
        return
    for ch in _iter_alignment_roots(root_alignments):
        try:
            if not hasattr(ch, ALN_REF_NAME_PROP):
                ch.addProperty("App::PropertyString", ALN_REF_NAME_PROP, "CorridorRoad", "Alignment object name")
        except Exception:
            pass
        try:
            if not str(getattr(ch, ALN_REF_NAME_PROP, "") or ""):
                legacy = getattr(ch, ALN_REF_PROP, None)
                if legacy is not None:
                    setattr(ch, ALN_REF_NAME_PROP, _name(legacy))
        except Exception:
            pass
        # Clear old link to prevent root-level linked-child display in tree.
        try:
            if hasattr(ch, ALN_REF_PROP):
                setattr(ch, ALN_REF_PROP, None)
                try:
                    ch.setEditorMode(ALN_REF_PROP, 2)
                except Exception:
                    pass
                try:
                    ch.setPropertyStatus(ALN_REF_PROP, ["Hidden"])
                except Exception:
                    pass
        except Exception:
            pass


def _legacy_tree_keys() -> set[str]:
    return {
        TREE_INPUTS,
        TREE_INPUTS_TERRAINS,
        TREE_INPUTS_SURVEY,
        TREE_INPUTS_STRUCTURES,
        TREE_INPUTS_REGIONS,
        TREE_ALIGNMENTS,
        TREE_SURFACES,
        TREE_ANALYSIS,
        TREE_REFERENCES,
        ALIGNMENT_ROOT,
        ALIGNMENT_HORIZONTAL,
        ALIGNMENT_STATIONING,
        ALIGNMENT_VERTICAL,
        ALIGNMENT_CENTERLINE,
        ALIGNMENT_ASSEMBLY,
        ALIGNMENT_REGIONS,
        ALIGNMENT_SECTIONS,
        ALIGNMENT_STRUCTURE_SECTIONS,
        ALIGNMENT_CORRIDOR,
    }


def _remove_empty_legacy_tree_folders(obj_project) -> None:
    """Remove empty transition-era v0 tree folders from a v1 project tree."""

    if obj_project is None:
        return
    doc = getattr(obj_project, "Document", None)
    if doc is None:
        return
    legacy_keys = _legacy_tree_keys()
    for folder in reversed(_iter_tree_folders(obj_project)):
        if folder is None:
            continue
        if _tree_key(folder) not in legacy_keys:
            continue
        if _group_get(folder):
            continue
        owners = [obj_project] + _iter_tree_folders(obj_project)
        for owner in owners:
            if owner is None or owner == folder:
                continue
            _group_remove(owner, folder)
        try:
            doc.removeObject(_name(folder))
        except Exception:
            pass


def ensure_project_tree(obj_project, include_references: bool = False):
    if obj_project is None:
        return {}
    doc = getattr(obj_project, "Document", None)
    if doc is None:
        return {}

    ensure_project_properties(obj_project)

    out = {}
    for key, label, obj_name in V1_ROOT_TREE_DEFS:
        out[key] = _ensure_child_folder(doc, obj_project, key, label, obj_name)
    _reorder_children_by_tree_keys(obj_project, [key for key, _label, _obj_name in V1_ROOT_TREE_DEFS])
    for parent_key, key, label, obj_name in V1_SUBTREE_DEFS:
        parent = out.get(parent_key, None)
        if parent is not None:
            out[key] = _ensure_child_folder(doc, parent, key, label, obj_name)
    for parent_key in dict.fromkeys(parent_key for parent_key, _key, _label, _obj_name in V1_SUBTREE_DEFS):
        parent = out.get(parent_key, None)
        if parent is not None:
            ordered_keys = [key for pkey, key, _label, _obj_name in V1_SUBTREE_DEFS if pkey == parent_key]
            _reorder_children_by_tree_keys(parent, ordered_keys)

    if include_references:
        out[V1_TREE_EXISTING_REFERENCES] = out.get(V1_TREE_EXISTING_REFERENCES, None)
    _remove_empty_legacy_tree_folders(obj_project)
    return out


def _alignment_name_from_obj(alignment_obj):
    if alignment_obj is None:
        return "Unassigned"
    lbl = _label(alignment_obj)
    nm = _name(alignment_obj)
    src = lbl if lbl else nm
    if src.startswith("ALN_"):
        src = src[4:]
    return _sanitize_tag(src, default_text="Unassigned")


def _iter_alignment_roots(root_alignments):
    out = []
    for ch in _group_get(root_alignments):
        if not _is_group_obj(ch):
            continue
        if _tree_key(ch) != ALIGNMENT_ROOT:
            continue
        out.append(ch)
    return out


def _alignment_label_conflict(root_alignments, label: str, alignment_obj, exclude=None):
    for ch in _iter_alignment_roots(root_alignments):
        if exclude is not None and ch == exclude:
            continue
        if _label(ch) != str(label):
            continue
        if _alignment_ref_matches(ch, alignment_obj):
            continue
        return True
    return False


def _unique_alignment_label(root_alignments, base_label: str, alignment_obj, exclude=None):
    label = str(base_label)
    if not _alignment_label_conflict(root_alignments, label, alignment_obj, exclude=exclude):
        return label

    if alignment_obj is not None:
        name_tag = _sanitize_tag(_name(alignment_obj), default_text="Alignment")
        tagged = f"{base_label}_{name_tag}"
        if not _alignment_label_conflict(root_alignments, tagged, alignment_obj, exclude=exclude):
            return tagged

    idx = 2
    while idx < 1000:
        cand = f"{base_label}_{idx}"
        if not _alignment_label_conflict(root_alignments, cand, alignment_obj, exclude=exclude):
            return cand
        idx += 1
    return f"{base_label}_{_sanitize_tag(_name(alignment_obj), default_text='X')}"


def ensure_alignment_tree(obj_project, alignment_obj=None):
    """Return v1 alignment/profile folders without creating legacy ALN_* branches."""

    tree = ensure_project_tree(obj_project, include_references=False)
    alignments = tree.get(V1_TREE_ALIGNMENTS, None)
    profiles = tree.get(V1_TREE_PROFILES, None)
    stations = tree.get(V1_TREE_STATIONS, None)
    return {
        "alignment_root": tree.get(V1_TREE_ALIGNMENT_PROFILE, None),
        ALIGNMENT_HORIZONTAL: alignments,
        ALIGNMENT_STATIONING: stations,
        ALIGNMENT_VERTICAL: profiles,
        ALIGNMENT_CENTERLINE: alignments,
        ALIGNMENT_ASSEMBLY: tree.get(V1_TREE_ASSEMBLIES, None),
        ALIGNMENT_REGIONS: tree.get(V1_TREE_REGIONS, None),
        ALIGNMENT_SECTIONS: tree.get(V1_TREE_APPLIED_SECTIONS, None),
        ALIGNMENT_STRUCTURE_SECTIONS: tree.get(V1_TREE_STRUCTURE_INTERACTIONS, None),
        ALIGNMENT_CORRIDOR: tree.get(V1_TREE_CORRIDOR_MODEL, None),
    }


def _is_type(obj, proxy_types=(), name_prefixes=()):
    pt = _proxy_type(obj)
    if pt and pt in tuple(proxy_types or ()):
        return True
    nm = _name(obj)
    return any(nm.startswith(str(p)) for p in tuple(name_prefixes or ()))


def _looks_like_horizontal_alignment(obj):
    if obj is None:
        return False
    try:
        return bool(
            hasattr(obj, "IPPoints")
            and hasattr(obj, "CurveRadii")
            and hasattr(obj, "TransitionLengths")
        )
    except Exception:
        return False


def _first_alignment_from_doc(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        if _is_type(o, proxy_types=("HorizontalAlignment",), name_prefixes=("HorizontalAlignment",)):
            return o
    return None


def _first_stationing_from_doc(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        if _is_type(o, proxy_types=("Stationing",), name_prefixes=("Stationing",)):
            return o
    return None


def _alignment_from_centerline_display(obj):
    if obj is None:
        return None
    aln = getattr(obj, "Alignment", None)
    if aln is not None:
        return aln
    src = getattr(obj, "SourceCenterline", None)
    if src is not None:
        return getattr(src, "Alignment", None)
    return None


def _alignment_from_section_set(sec):
    if sec is None:
        return None
    src = getattr(sec, "SourceCenterlineDisplay", None)
    aln = _alignment_from_centerline_display(src)
    if aln is not None:
        return aln
    return getattr(sec, "Alignment", None)


def _alignment_from_profile_bundle(bundle):
    if bundle is None:
        return None
    st = getattr(bundle, "Stationing", None)
    if st is not None:
        aln = getattr(st, "Alignment", None)
        if aln is not None:
            return aln
    return None


def _alignment_from_project_links(prj):
    if prj is None:
        return None
    st = getattr(prj, "Stationing", None)
    if st is not None:
        aln = getattr(st, "Alignment", None)
        if aln is not None:
            return aln
    aln = getattr(prj, "Alignment", None)
    if aln is not None:
        return aln
    doc = getattr(prj, "Document", None)
    st0 = _first_stationing_from_doc(doc)
    if st0 is not None:
        aln = getattr(st0, "Alignment", None)
        if aln is not None:
            return aln
    aln0 = _first_alignment_from_doc(doc)
    if aln0 is not None:
        return aln0
    return None


def _alignment_from_vertical_alignment(prj, va):
    if va is None:
        return None
    doc = getattr(prj, "Document", None)
    if doc is None:
        return None
    for o in doc.Objects:
        if _is_type(o, proxy_types=("Centerline3DDisplay",), name_prefixes=("Centerline3DDisplay",)):
            if getattr(o, "VerticalAlignment", None) == va:
                aln = _alignment_from_centerline_display(o)
                if aln is not None:
                    return aln
    for o in doc.Objects:
        if _is_type(o, proxy_types=("ProfileBundle",), name_prefixes=("ProfileBundle",)):
            if getattr(o, "VerticalAlignment", None) == va:
                aln = _alignment_from_profile_bundle(o)
                if aln is not None:
                    return aln
    return None


def _resolve_alignment_for_object(prj, child):
    if prj is None or child is None:
        return None

    if _is_type(child, proxy_types=("HorizontalAlignment",), name_prefixes=("HorizontalAlignment",)) or _looks_like_horizontal_alignment(child):
        return child

    if hasattr(child, "Alignment"):
        aln = getattr(child, "Alignment", None)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=("Centerline3DDisplay",), name_prefixes=("Centerline3DDisplay",)):
        aln = _alignment_from_centerline_display(child)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=(), name_prefixes=("CenterlineBoundaryMarker",)):
        disp = getattr(child, "ParentCenterline3DDisplay", None)
        aln = _alignment_from_centerline_display(disp) if disp is not None else None
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=("SectionSet",), name_prefixes=("SectionSet",)):
        aln = _alignment_from_section_set(child)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=("SectionSlice",), name_prefixes=("SectionSlice",)):
        sec = getattr(child, "ParentSectionSet", None)
        aln = _alignment_from_section_set(sec)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=("SectionStructureOverlay",), name_prefixes=("SectionStructureOverlay",)):
        sec = getattr(child, "ParentSectionSet", None)
        if sec is None:
            slice_obj = getattr(child, "ParentSectionSlice", None)
            sec = getattr(slice_obj, "ParentSectionSet", None) if slice_obj is not None else None
        aln = _alignment_from_section_set(sec)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=(CORRIDOR_PROXY_TYPE,), name_prefixes=(CORRIDOR_NAME_PREFIX,)):
        sec = getattr(child, "SourceSectionSet", None)
        aln = _alignment_from_section_set(sec)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=(), name_prefixes=(CORRIDOR_SKIP_MARKER_NAME,)):
        cor = getattr(child, CORRIDOR_CHILD_LINK_PROPERTY, None)
        sec = getattr(cor, "SourceSectionSet", None) if cor is not None else None
        aln = _alignment_from_section_set(sec)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=(), name_prefixes=(CORRIDOR_SEGMENT_NAME,)):
        cor = getattr(child, CORRIDOR_CHILD_LINK_PROPERTY, None)
        sec = getattr(cor, "SourceSectionSet", None) if cor is not None else None
        aln = _alignment_from_section_set(sec)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=("AssemblyTemplate",), name_prefixes=("AssemblyTemplate",)):
        doc = getattr(prj, "Document", None)
        if doc is not None:
            for o in doc.Objects:
                if _is_type(o, proxy_types=("SectionSet",), name_prefixes=("SectionSet",)):
                    if getattr(o, "AssemblyTemplate", None) == child:
                        aln = _alignment_from_section_set(o)
                        if aln is not None:
                            return aln

    if _is_type(child, proxy_types=("TypicalSectionTemplate",), name_prefixes=("TypicalSectionTemplate",)):
        doc = getattr(prj, "Document", None)
        if doc is not None:
            for o in doc.Objects:
                if _is_type(o, proxy_types=("SectionSet",), name_prefixes=("SectionSet",)):
                    if getattr(o, "TypicalSectionTemplate", None) == child:
                        aln = _alignment_from_section_set(o)
                        if aln is not None:
                            return aln
        aln = _alignment_from_project_links(prj)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=("TypicalSectionPavementDisplay",), name_prefixes=("TypicalSectionPavementDisplay",)):
        src = getattr(child, "SourceTypicalSection", None)
        if src is not None:
            doc = getattr(prj, "Document", None)
            if doc is not None:
                for o in doc.Objects:
                    if _is_type(o, proxy_types=("SectionSet",), name_prefixes=("SectionSet",)):
                        if getattr(o, "TypicalSectionTemplate", None) == src:
                            aln = _alignment_from_section_set(o)
                            if aln is not None:
                                return aln
        aln = _alignment_from_project_links(prj)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=("RegionPlan",), name_prefixes=("RegionPlan",)):
        aln = _alignment_from_project_links(prj)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=("ProfileBundle",), name_prefixes=("ProfileBundle",)):
        aln = _alignment_from_profile_bundle(child)
        if aln is not None:
            return aln
        aln = _alignment_from_project_links(prj)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=("VerticalAlignment",), name_prefixes=("VerticalAlignment",)):
        aln = _alignment_from_vertical_alignment(prj, child)
        if aln is not None:
            return aln
        aln = _alignment_from_project_links(prj)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=("FGDisplay",), name_prefixes=("FinishedGradeFG",)):
        va = getattr(child, "SourceVA", None)
        aln = _alignment_from_vertical_alignment(prj, va)
        if aln is not None:
            return aln
        aln = _alignment_from_project_links(prj)
        if aln is not None:
            return aln

    # Unlinked objects are routed to ALN_Unassigned branch.
    return None


def _is_alignment_related(child):
    if _looks_like_horizontal_alignment(child):
        return True
    return _is_type(
        child,
        proxy_types=(
            "HorizontalAlignment",
            "Stationing",
            "VerticalAlignment",
            "ProfileBundle",
            "FGDisplay",
            "Centerline3DDisplay",
            "CenterlineBoundaryMarker",
            "Centerline3D",
            "AssemblyTemplate",
            "TypicalSectionTemplate",
            "TypicalSectionPavementDisplay",
            "RegionPlan",
            "SectionSet",
            "SectionSlice",
            "SectionStructureOverlay",
            CORRIDOR_PROXY_TYPE,
            CORRIDOR_SKIP_MARKER_NAME,
            CORRIDOR_SEGMENT_NAME,
        ),
        name_prefixes=(
            "HorizontalAlignment",
            "Stationing",
            "VerticalAlignment",
            "ProfileBundle",
            "FinishedGradeFG",
            "Centerline3DDisplay",
            "CenterlineBoundaryMarker",
            "Centerline3D",
            "AssemblyTemplate",
            "TypicalSectionTemplate",
            "TypicalSectionPavementDisplay",
            "RegionPlan",
            "SectionSet",
            "SectionSlice",
            "SectionStructureOverlay",
            CORRIDOR_NAME_PREFIX,
            CORRIDOR_SKIP_MARKER_NAME,
            CORRIDOR_SEGMENT_NAME,
        ),
    )


def _is_surface(child):
    return _is_type(
        child,
        proxy_types=("DesignGradingSurface", "DesignTerrain", "V1SurfaceModel", "SurfaceModel"),
        name_prefixes=("DesignGradingSurface", "DesignTerrain", "V1SurfaceModel", "SurfaceModel"),
    )


def _is_analysis(child):
    return _is_type(child, proxy_types=("CutFillCalc",), name_prefixes=("CutFillCalc",))


def _is_structure_input(child):
    return _is_type(child, proxy_types=("StructureSet",), name_prefixes=("StructureSet",))


def _is_region_input(child):
    return _is_type(child, proxy_types=("RegionPlan",), name_prefixes=("RegionPlan",))


def _is_v1_ramp(child):
    return _is_type(child, proxy_types=("RampModel", "Ramp"), name_prefixes=("RampModel", "Ramp"))


def _is_v1_intersection(child):
    return _is_type(
        child,
        proxy_types=("IntersectionModel", "Intersection"),
        name_prefixes=("IntersectionModel", "Intersection"),
    )


def _is_v1_drainage(child):
    return _is_type(
        child,
        proxy_types=(
            "DrainageModel",
            "DitchModel",
            "CulvertModel",
            "InletModel",
            "FlowPathModel",
            "Ditch",
            "Culvert",
            "Inlet",
            "FlowPath",
        ),
        name_prefixes=(
            "DrainageModel",
            "DitchModel",
            "CulvertModel",
            "InletModel",
            "FlowPathModel",
            "Ditch",
            "Culvert",
            "Inlet",
            "FlowPath",
        ),
    )


def _is_v1_review(child):
    return _is_type(
        child,
        proxy_types=(
            "PlanProfileReview",
            "SectionReview",
            "TINReview",
            "ReviewIssue",
            "ReviewBookmark",
            "Issue",
            "Bookmark",
        ),
        name_prefixes=(
            "PlanProfileReview",
            "SectionReview",
            "TINReview",
            "ReviewIssue",
            "ReviewBookmark",
            "Issue",
            "Bookmark",
        ),
    )


def _is_v1_output_exchange(child):
    return _is_type(
        child,
        proxy_types=(
            "SheetOutput",
            "ReportOutput",
            "DXFExport",
            "LandXMLExport",
            "IFCExport",
            "ExchangePackage",
        ),
        name_prefixes=(
            "SheetOutput",
            "ReportOutput",
            "DXFExport",
            "LandXMLExport",
            "IFCExport",
            "ExchangePackage",
        ),
    )


def _is_v1_ai_assist(child):
    return _is_type(
        child,
        proxy_types=(
            "AISuggestion",
            "AICheck",
            "AIGeneratedAlternative",
            "AIUserDecision",
        ),
        name_prefixes=(
            "AISuggestion",
            "AICheck",
            "AIGeneratedAlternative",
            "AIUserDecision",
        ),
    )


def resolve_v1_target_container(prj, child):
    """Resolve the preferred v1 project-tree container for a child object."""

    if prj is None or child is None or child == prj:
        return None
    if _is_tree_folder(child):
        return prj

    tree = ensure_project_tree(prj, include_references=False)
    record_kind = str(getattr(child, "CRRecordKind", "") or "")
    if record_kind == "tin_source_csv":
        return tree.get(V1_TREE_SURVEY_POINTS, None)
    if record_kind == "tin_surface_source":
        return tree.get(V1_TREE_EXISTING_GROUND_TIN_SOURCE, None)
    if record_kind == "tin_surface_result":
        return tree.get(V1_TREE_EXISTING_GROUND_TIN_RESULT, None)
    if record_kind == "v1_corridor_surface_preview":
        return tree.get(V1_TREE_DESIGN_TIN, None)
    if record_kind == "v1_corridor_centerline_preview":
        return tree.get(V1_TREE_CORRIDOR_MODEL, None)
    if record_kind == "v1_assembly_show_preview":
        return tree.get(V1_TREE_ASSEMBLIES, None)
    if record_kind == "v1_structure_show_preview":
        return tree.get(V1_TREE_STRUCTURES, None)
    if record_kind == "v1_applied_section_show_preview":
        return tree.get(V1_TREE_APPLIED_SECTIONS, None)
    if record_kind == "tin_mesh_preview":
        return tree.get(V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW, None)
    if record_kind == "tin_diagnostics":
        return tree.get(V1_TREE_EXISTING_GROUND_TIN_DIAGNOSTICS, None)
    if _is_type(child, proxy_types=("V1Alignment", "HorizontalAlignment"), name_prefixes=("V1Alignment", "HorizontalAlignment")) or _looks_like_horizontal_alignment(child):
        return tree.get(V1_TREE_ALIGNMENTS, None)
    if _is_type(
        child,
        proxy_types=("V1Profile", "VerticalAlignment", "ProfileBundle", "FGDisplay"),
        name_prefixes=("V1Profile", "VerticalAlignment", "ProfileBundle", "FinishedGradeFG"),
    ):
        return tree.get(V1_TREE_PROFILES, None)
    if _is_type(
        child,
        proxy_types=("V1Stationing", "Stationing", "V1StationHighlight"),
        name_prefixes=("V1Stationing", "Stationing", "V1StationHighlight"),
    ):
        return tree.get(V1_TREE_STATIONS, None)
    if _is_type(child, proxy_types=("Superelevation", "SuperelevationModel"), name_prefixes=("Superelevation", "SuperelevationModel")):
        return tree.get(V1_TREE_SUPERELEVATION, None)
    if _is_v1_ramp(child):
        return tree.get(V1_TREE_RAMPS, None)
    if _is_v1_intersection(child):
        return tree.get(V1_TREE_INTERSECTIONS, None)
    if _is_v1_drainage(child):
        if _is_type(child, proxy_types=("DitchModel", "Ditch"), name_prefixes=("DitchModel", "Ditch")):
            return tree.get(V1_TREE_DITCHES, None)
        if _is_type(child, proxy_types=("CulvertModel", "Culvert"), name_prefixes=("CulvertModel", "Culvert")):
            return tree.get(V1_TREE_CULVERTS, None)
        if _is_type(child, proxy_types=("InletModel", "Inlet"), name_prefixes=("InletModel", "Inlet")):
            return tree.get(V1_TREE_INLETS, None)
        if _is_type(child, proxy_types=("FlowPathModel", "FlowPath"), name_prefixes=("FlowPathModel", "FlowPath")):
            return tree.get(V1_TREE_FLOW_PATHS, None)
        return tree.get(V1_TREE_DRAINAGE, None)
    if _is_type(
        child,
        proxy_types=("V1AssemblyModel", "AssemblyModel", "AssemblyTemplate", "TypicalSectionTemplate"),
        name_prefixes=("V1AssemblyModel", "AssemblyModel", "AssemblyTemplate", "TypicalSectionTemplate"),
    ):
        return tree.get(V1_TREE_ASSEMBLIES, None)
    if _is_type(child, proxy_types=("V1RegionModel", "RegionModel", "RegionPlan"), name_prefixes=("V1RegionModel", "RegionModel", "RegionPlan")):
        return tree.get(V1_TREE_REGIONS, None)
    if _is_type(
        child,
        proxy_types=("V1AppliedSectionSet", "AppliedSectionSet", "SectionSet", "SectionSlice"),
        name_prefixes=("V1AppliedSectionSet", "AppliedSectionSet", "SectionSet", "SectionSlice"),
    ):
        return tree.get(V1_TREE_APPLIED_SECTIONS, None)
    if _is_type(
        child,
        proxy_types=("V1CorridorModel", "CorridorModel", "V1CorridorCenterlinePreview"),
        name_prefixes=("V1CorridorModel", "CorridorModel", "V1CorridorCenterlinePreview"),
    ):
        return tree.get(V1_TREE_CORRIDOR_MODEL, None)
    if _is_type(child, proxy_types=("V1SurfaceModel", "SurfaceModel"), name_prefixes=("V1SurfaceModel", "SurfaceModel")):
        return tree.get(V1_TREE_DESIGN_TIN, None)
    if _is_type(child, proxy_types=(CORRIDOR_PROXY_TYPE,), name_prefixes=(CORRIDOR_NAME_PREFIX,)):
        return tree.get(V1_TREE_CORRIDOR_MODEL, None)
    if _is_type(child, proxy_types=("V1StructureModel", "StructureModel", "StructureSet"), name_prefixes=("V1StructureModel", "StructureModel", "StructureSet")):
        return tree.get(V1_TREE_STRUCTURES, None)
    if _is_v1_review(child):
        if _is_type(child, proxy_types=("PlanProfileReview",), name_prefixes=("PlanProfileReview",)):
            return tree.get(V1_TREE_PLAN_PROFILE_REVIEW, None)
        if _is_type(child, proxy_types=("SectionReview",), name_prefixes=("SectionReview",)):
            return tree.get(V1_TREE_SECTION_REVIEW, None)
        if _is_type(child, proxy_types=("TINReview",), name_prefixes=("TINReview",)):
            return tree.get(V1_TREE_TIN_REVIEW, None)
        if _is_type(child, proxy_types=("ReviewIssue", "Issue"), name_prefixes=("ReviewIssue", "Issue")):
            return tree.get(V1_TREE_ISSUES, None)
        if _is_type(child, proxy_types=("ReviewBookmark", "Bookmark"), name_prefixes=("ReviewBookmark", "Bookmark")):
            return tree.get(V1_TREE_BOOKMARKS, None)
        return tree.get(V1_TREE_REVIEW, None)
    if _is_v1_output_exchange(child):
        if _is_type(child, proxy_types=("SheetOutput",), name_prefixes=("SheetOutput",)):
            return tree.get(V1_TREE_SHEETS, None)
        if _is_type(child, proxy_types=("ReportOutput",), name_prefixes=("ReportOutput",)):
            return tree.get(V1_TREE_REPORTS, None)
        if _is_type(child, proxy_types=("DXFExport",), name_prefixes=("DXFExport",)):
            return tree.get(V1_TREE_DXF, None)
        if _is_type(child, proxy_types=("LandXMLExport",), name_prefixes=("LandXMLExport",)):
            return tree.get(V1_TREE_LANDXML, None)
        if _is_type(child, proxy_types=("IFCExport",), name_prefixes=("IFCExport",)):
            return tree.get(V1_TREE_IFC, None)
        if _is_type(child, proxy_types=("ExchangePackage",), name_prefixes=("ExchangePackage",)):
            return tree.get(V1_TREE_EXCHANGE_PACKAGES, None)
        return tree.get(V1_TREE_OUTPUTS_EXCHANGE, None)
    if _is_v1_ai_assist(child):
        if _is_type(child, proxy_types=("AISuggestion",), name_prefixes=("AISuggestion",)):
            return tree.get(V1_TREE_AI_SUGGESTIONS, None)
        if _is_type(child, proxy_types=("AICheck",), name_prefixes=("AICheck",)):
            return tree.get(V1_TREE_AI_CHECKS, None)
        if _is_type(child, proxy_types=("AIGeneratedAlternative",), name_prefixes=("AIGeneratedAlternative",)):
            return tree.get(V1_TREE_AI_GENERATED_ALTERNATIVES, None)
        if _is_type(child, proxy_types=("AIUserDecision",), name_prefixes=("AIUserDecision",)):
            return tree.get(V1_TREE_AI_USER_DECISIONS, None)
        return tree.get(V1_TREE_AI_ASSIST, None)
    return None


def route_to_v1_tree(prj, child):
    """Add a child object to its preferred v1 project-tree container."""

    folder = resolve_v1_target_container(prj, child)
    if folder is None:
        return None
    _group_add(folder, child)
    return folder


def _is_probable_terrain_input(prj, child):
    if child is None:
        return False
    if child == getattr(prj, "Terrain", None):
        return True
    if _is_surface(child) or _is_analysis(child) or _is_alignment_related(child):
        return False
    doc = getattr(prj, "Document", None)
    if doc is not None:
        for o in list(getattr(doc, "Objects", []) or []):
            if o is None or o == child:
                continue
            for prop in ("ExistingSurface", "ExistingTerrain", "TerrainMesh"):
                try:
                    if getattr(o, prop, None) == child:
                        return True
                except Exception:
                    pass

    nm = _name(child).lower()
    lb = _label(child).lower()
    keywords = ("terrain", "existing", "eg", "survey", "topo", "dtm", "dem", "ground")
    return any(k in nm or k in lb for k in keywords)


def _target_folder_for_alignment_child(prj, child):
    aln = _resolve_alignment_for_object(prj, child)
    aln_tree = ensure_alignment_tree(prj, alignment_obj=aln)
    if not aln_tree:
        return None

    if _is_type(child, proxy_types=("Centerline3DDisplay",), name_prefixes=("Centerline3DDisplay",)):
        return aln_tree.get(ALIGNMENT_CENTERLINE, None)
    if _is_type(child, proxy_types=("HorizontalAlignment",), name_prefixes=("HorizontalAlignment",)) or _looks_like_horizontal_alignment(child):
        return aln_tree.get(ALIGNMENT_HORIZONTAL, None)
    if _is_type(child, proxy_types=("Stationing",), name_prefixes=("Stationing",)):
        return aln_tree.get(ALIGNMENT_STATIONING, None)
    if _is_type(child, proxy_types=("AssemblyTemplate",), name_prefixes=("AssemblyTemplate",)):
        return aln_tree.get(ALIGNMENT_ASSEMBLY, None)
    if _is_type(child, proxy_types=("TypicalSectionTemplate",), name_prefixes=("TypicalSectionTemplate",)):
        return aln_tree.get(ALIGNMENT_ASSEMBLY, None)
    if _is_type(child, proxy_types=("TypicalSectionPavementDisplay",), name_prefixes=("TypicalSectionPavementDisplay",)):
        return aln_tree.get(ALIGNMENT_ASSEMBLY, None)
    if _is_type(child, proxy_types=("RegionPlan",), name_prefixes=("RegionPlan",)):
        return aln_tree.get(ALIGNMENT_REGIONS, None)
    if _is_type(child, proxy_types=("SectionSet", "SectionSlice"), name_prefixes=("SectionSet", "SectionSlice")):
        return aln_tree.get(ALIGNMENT_SECTIONS, None)
    if _is_type(child, proxy_types=("SectionStructureOverlay",), name_prefixes=("SectionStructureOverlay",)):
        return aln_tree.get(ALIGNMENT_STRUCTURE_SECTIONS, None)
    if _is_type(child, proxy_types=(), name_prefixes=(CORRIDOR_SKIP_MARKER_NAME,)):
        return aln_tree.get(ALIGNMENT_CORRIDOR, None)
    if _is_type(child, proxy_types=(), name_prefixes=(CORRIDOR_SEGMENT_NAME,)):
        return aln_tree.get(ALIGNMENT_CORRIDOR, None)
    if _is_type(child, proxy_types=(CORRIDOR_PROXY_TYPE,), name_prefixes=(CORRIDOR_NAME_PREFIX,)):
        return aln_tree.get(ALIGNMENT_CORRIDOR, None)
    if _is_type(child, proxy_types=(), name_prefixes=("CenterlineBoundaryMarker",)):
        return None
    return aln_tree.get(ALIGNMENT_VERTICAL, None)


def _resolve_target_container(prj, child, allow_references: bool = True):
    if prj is None or child is None:
        return None
    if child == prj:
        return None
    if _is_tree_folder(child):
        return prj

    tree = ensure_project_tree(prj, include_references=False)

    v1_target = resolve_v1_target_container(prj, child)
    if v1_target is not None:
        return v1_target

    if _is_alignment_related(child):
        return tree.get(V1_TREE_ALIGNMENT_PROFILE, None)

    if _is_surface(child):
        return tree.get(V1_TREE_SURFACES, None)

    if _is_analysis(child):
        return tree.get(V1_TREE_QUANTITIES_EARTHWORK, None)

    if _is_structure_input(child):
        return tree.get(V1_TREE_STRUCTURES, None)

    if _is_region_input(child):
        return tree.get(V1_TREE_REGIONS, None)

    if _is_probable_terrain_input(prj, child):
        return tree.get(V1_TREE_SURVEY_POINTS, None)

    if allow_references:
        return tree.get(V1_TREE_EXISTING_REFERENCES, None)
    return prj


def _detach_from_other_tree_folders(prj, child, keep_owner):
    if prj is None or child is None:
        return
    owners = [prj] + _iter_tree_folders(prj)
    for owner in owners:
        if owner is None or owner == keep_owner or owner == child:
            continue
        _group_remove(owner, child)


def _adopt_project_linked_objects(prj):
    if prj is None:
        return
    link_props = (
        "Terrain",
        "Alignment",
        "Stationing",
        "Centerline3D",
        "Centerline3DDisplay",
        "AssemblyTemplate",
        "TypicalSectionTemplate",
        "StructureSet",
        "SectionSet",
        CORRIDOR_PROJECT_PROPERTY,
        "DesignGradingSurface",
        "DesignTerrain",
        "CutFillCalc",
    )
    for pn in link_props:
        try:
            ch = getattr(prj, pn, None)
        except Exception:
            ch = None
        if ch is None:
            continue
        CorridorRoadProject.adopt(prj, ch)


def _adopt_document_candidates(prj):
    if prj is None:
        return
    doc = getattr(prj, "Document", None)
    if doc is None:
        return
    for ch in list(getattr(doc, "Objects", []) or []):
        if ch is None or ch == prj or _is_tree_folder(ch):
            continue
        if _is_alignment_related(ch) or _is_surface(ch) or _is_analysis(ch) or _is_probable_terrain_input(prj, ch) or _is_region_input(ch) or _is_structure_input(ch):
            CorridorRoadProject.adopt(prj, ch)


def _rebalance_all_tree_objects(prj):
    if prj is None:
        return
    owners = [prj] + _iter_tree_folders(prj)
    objs = []
    seen = set()
    for owner in owners:
        for ch in _group_get(owner):
            if ch is None or _is_tree_folder(ch) or ch == prj:
                continue
            k = _name(ch) or str(id(ch))
            if k in seen:
                continue
            seen.add(k)
            objs.append(ch)
    for ch in objs:
        CorridorRoadProject.adopt(prj, ch)


def _gui_up() -> bool:
    try:
        return bool(getattr(App, "GuiUp", False))
    except Exception:
        return False


def show_project_setup_dialog(preferred_project=None) -> bool:
    if not _gui_up():
        return False
    try:
        import FreeCADGui as Gui
        from freecad.Corridor_Road.ui.task_project_setup import ProjectSetupTaskPanel
    except Exception:
        return False
    try:
        Gui.Control.showDialog(ProjectSetupTaskPanel(preferred_project=preferred_project))
        return True
    except Exception:
        return False


class ViewProviderCorridorRoadProject:
    def __init__(self, vobj):
        vobj.Proxy = self
        self.Type = "ViewProviderCorridorRoadProject"

    def attach(self, vobj):
        self.Object = getattr(vobj, "Object", None)
        try:
            vobj.Visibility = True
        except Exception:
            pass

    def getIcon(self):
        return ""

    def setEdit(self, vobj, mode=0):
        # Do not auto-open task panel on selection/edit start.
        return False

    def unsetEdit(self, vobj, mode=0):
        return True

    def doubleClicked(self, vobj):
        # Keep default behavior; opening project setup is menu-driven.
        return False

    def setupContextMenu(self, vobj, menu):
        # Context menu entry for selected CorridorRoadProject.
        try:
            act = menu.addAction("Project Setup")
            act.triggered.connect(lambda: show_project_setup_dialog(getattr(vobj, "Object", None)))
        except Exception:
            pass

    def claimChildren(self):
        # Tree should be driven by the fixed folder schema only.
        try:
            obj = getattr(self, "Object", None)
            return list(getattr(obj, "Group", []) or [])
        except Exception:
            return []


def ensure_project_viewprovider(obj):
    if obj is None or (not _gui_up()):
        return
    vobj = getattr(obj, "ViewObject", None)
    if vobj is None:
        return
    proxy = getattr(vobj, "Proxy", None)
    if proxy is not None and getattr(proxy, "Type", "") == "ViewProviderCorridorRoadProject":
        # Older proxy instances may not have latest methods (e.g., claimChildren).
        if hasattr(proxy, "claimChildren") and hasattr(proxy, "setupContextMenu"):
            return
    try:
        ViewProviderCorridorRoadProject(vobj)
    except Exception:
        pass


def _hide_project_link_properties(obj):
    if obj is None:
        return
    link_props = (
        "Terrain",
        "Alignment",
        "Stationing",
        "Centerline3D",
        "Centerline3DDisplay",
        "AssemblyTemplate",
        "TypicalSectionTemplate",
        "SectionSet",
        CORRIDOR_PROJECT_PROPERTY,
        "DesignGradingSurface",
        "DesignTerrain",
        "CutFillCalc",
    )
    for pn in link_props:
        try:
            obj.setEditorMode(pn, 2)  # hidden in property editor
        except Exception:
            pass
        try:
            obj.setPropertyStatus(pn, ["Hidden"])
        except Exception:
            pass


def _prop_type_id(obj, prop_name: str) -> str:
    try:
        return str(obj.getTypeIdOfProperty(str(prop_name)) or "")
    except Exception:
        return ""


def _add_link_property_prefer_hidden(obj, prop_name: str, group_name: str, doc_text: str):
    for tp in ("App::PropertyLinkHidden", "App::PropertyLink"):
        try:
            obj.addProperty(tp, prop_name, group_name, doc_text)
            return True
        except Exception:
            pass
    return False


def _ensure_hidden_link_property(obj, prop_name: str, group_name: str, doc_text: str):
    if obj is None:
        return
    if not hasattr(obj, prop_name):
        _add_link_property_prefer_hidden(obj, prop_name, group_name, doc_text)
        return
    pt = _prop_type_id(obj, prop_name)
    if "PropertyLinkHidden" in pt:
        return
    # Migrate visible App::PropertyLink -> App::PropertyLinkHidden (same name/value).
    try:
        cur = getattr(obj, prop_name, None)
    except Exception:
        cur = None
    try:
        obj.removeProperty(prop_name)
    except Exception:
        # Migration failed; keep current property and hide via UI/status as fallback.
        if str(prop_name) == "Alignment":
            try:
                setattr(obj, prop_name, None)
            except Exception:
                pass
        return
    if not _add_link_property_prefer_hidden(obj, prop_name, group_name, doc_text):
        return
    try:
        if "PropertyLinkHidden" in _prop_type_id(obj, prop_name):
            setattr(obj, prop_name, cur)
        elif str(prop_name) == "Alignment":
            # If hidden type is unavailable, keep Alignment empty to prevent tree duplication.
            setattr(obj, prop_name, None)
        else:
            setattr(obj, prop_name, cur)
    except Exception:
        pass


def ensure_project_properties(obj):
    if not hasattr(obj, "Group"):
        obj.addProperty("App::PropertyLinkList", "Group", "CorridorRoad", "Contained objects")

    if not hasattr(obj, "Version"):
        obj.addProperty("App::PropertyString", "Version", "CorridorRoad", "Project schema version")
        obj.Version = "0.5"
    if not hasattr(obj, "LinearUnitDisplay"):
        obj.addProperty("App::PropertyString", "LinearUnitDisplay", "Units", "Preferred display unit for linear values")
        obj.LinearUnitDisplay = "m"
    if not hasattr(obj, "LinearUnitImportDefault"):
        obj.addProperty("App::PropertyString", "LinearUnitImportDefault", "Units", "Default import/input unit for linear values")
        obj.LinearUnitImportDefault = "m"
    if not hasattr(obj, "LinearUnitExportDefault"):
        obj.addProperty("App::PropertyString", "LinearUnitExportDefault", "Units", "Default export/report unit for linear values")
        obj.LinearUnitExportDefault = "m"
    if not hasattr(obj, "CustomLinearUnitScale"):
        obj.addProperty("App::PropertyFloat", "CustomLinearUnitScale", "Units", "Meters per user-unit when import/export unit is custom")
        obj.CustomLinearUnitScale = 1.0
    resolved_unit_settings = _units.resolve_project_unit_settings(obj)
    try:
        obj.LinearUnitDisplay = str(resolved_unit_settings.get("display", "m"))
    except Exception:
        pass
    try:
        obj.LinearUnitImportDefault = str(resolved_unit_settings.get("import", "m"))
    except Exception:
        pass
    try:
        obj.LinearUnitExportDefault = str(resolved_unit_settings.get("export", "m"))
    except Exception:
        pass
    try:
        obj.CustomLinearUnitScale = float(resolved_unit_settings.get("custom_scale", 1.0))
    except Exception:
        pass
    if not hasattr(obj, "DesignStandard"):
        legacy = ""
        try:
            legacy = str(getattr(obj, "DesignCriteria", "") or "")
        except Exception:
            legacy = ""
        obj.addProperty("App::PropertyString", "DesignStandard", "DesignCriteria", "Design standard (KDS/AASHTO)")
        obj.DesignStandard = _ds.normalize_standard(legacy or _ds.DEFAULT_STANDARD)
    try:
        obj.DesignStandard = _ds.normalize_standard(getattr(obj, "DesignStandard", _ds.DEFAULT_STANDARD))
    except Exception:
        pass

    if not hasattr(obj, "CRSEPSG"):
        obj.addProperty("App::PropertyString", "CRSEPSG", "CoordinateSystem", "CRS code (e.g., EPSG:5186)")
        obj.CRSEPSG = ""
    if not hasattr(obj, "HorizontalDatum"):
        obj.addProperty("App::PropertyString", "HorizontalDatum", "CoordinateSystem", "Horizontal datum metadata")
        obj.HorizontalDatum = ""
    if not hasattr(obj, "VerticalDatum"):
        obj.addProperty("App::PropertyString", "VerticalDatum", "CoordinateSystem", "Vertical datum metadata")
        obj.VerticalDatum = ""
    if not hasattr(obj, "ProjectOriginE"):
        obj.addProperty("App::PropertyFloat", "ProjectOriginE", "CoordinateSystem", "World origin Easting")
        obj.ProjectOriginE = 0.0
    if not hasattr(obj, "ProjectOriginN"):
        obj.addProperty("App::PropertyFloat", "ProjectOriginN", "CoordinateSystem", "World origin Northing")
        obj.ProjectOriginN = 0.0
    if not hasattr(obj, "ProjectOriginZ"):
        obj.addProperty("App::PropertyFloat", "ProjectOriginZ", "CoordinateSystem", "World origin elevation")
        obj.ProjectOriginZ = 0.0
    if not hasattr(obj, "LocalOriginX"):
        obj.addProperty("App::PropertyFloat", "LocalOriginX", "CoordinateSystem", "Local model origin X")
        obj.LocalOriginX = 0.0
    if not hasattr(obj, "LocalOriginY"):
        obj.addProperty("App::PropertyFloat", "LocalOriginY", "CoordinateSystem", "Local model origin Y")
        obj.LocalOriginY = 0.0
    if not hasattr(obj, "LocalOriginZ"):
        obj.addProperty("App::PropertyFloat", "LocalOriginZ", "CoordinateSystem", "Local model origin Z")
        obj.LocalOriginZ = 0.0
    if not hasattr(obj, "NorthRotationDeg"):
        obj.addProperty("App::PropertyFloat", "NorthRotationDeg", "CoordinateSystem", "North rotation (deg, CCW)")
        obj.NorthRotationDeg = 0.0
    if not hasattr(obj, "CoordSetupLocked"):
        obj.addProperty("App::PropertyBool", "CoordSetupLocked", "CoordinateSystem", "Lock coordinate setup edits")
        obj.CoordSetupLocked = False
    if not hasattr(obj, "CoordSetupStatus"):
        obj.addProperty("App::PropertyString", "CoordSetupStatus", "CoordinateSystem", "Coordinate setup status")
        obj.CoordSetupStatus = "Uninitialized"
    if not hasattr(obj, "CoordinateWorkflow"):
        obj.addProperty("App::PropertyString", "CoordinateWorkflow", "CoordinateSystem", "Coordinate workflow recommendation")
        obj.CoordinateWorkflow = "Local-first"
    try:
        workflow = str(getattr(obj, "CoordinateWorkflow", "") or "").strip()
        if workflow not in ("World-first", "Local-first", "Custom"):
            workflow = "World-first" if str(getattr(obj, "CRSEPSG", "") or "").strip() else "Local-first"
            obj.CoordinateWorkflow = workflow
    except Exception:
        pass
    if not hasattr(obj, "AutoApplyCoordinateRecommendations"):
        obj.addProperty("App::PropertyBool", "AutoApplyCoordinateRecommendations", "CoordinateSystem", "Use coordinate workflow as task-panel default")
        obj.AutoApplyCoordinateRecommendations = True
    if not hasattr(obj, "TINConversionMaxTriangles"):
        obj.addProperty(
            "App::PropertyInteger",
            "TINConversionMaxTriangles",
            "TIN",
            "Maximum triangles converted from a document mesh/shape for v1 TIN review and EG sampling",
        )
        obj.TINConversionMaxTriangles = 250000
    try:
        obj.TINConversionMaxTriangles = max(1000, int(getattr(obj, "TINConversionMaxTriangles", 250000) or 250000))
    except Exception:
        obj.TINConversionMaxTriangles = 250000

    _ensure_hidden_link_property(obj, "Terrain", "CorridorRoad", "Link to EG terrain object")
    _ensure_hidden_link_property(obj, "Alignment", "CorridorRoad", "Link to horizontal alignment object")
    _ensure_hidden_link_property(obj, "Stationing", "CorridorRoad", "Link to stationing object")
    _ensure_hidden_link_property(obj, "Centerline3D", "CorridorRoad", "Link to 3D centerline object")
    _ensure_hidden_link_property(obj, "Centerline3DDisplay", "CorridorRoad", "Link to 3D centerline display object")
    _ensure_hidden_link_property(obj, "AssemblyTemplate", "CorridorRoad", "Link to assembly template object")
    _ensure_hidden_link_property(obj, "TypicalSectionTemplate", "CorridorRoad", "Link to typical section template object")
    _ensure_hidden_link_property(obj, "StructureSet", "CorridorRoad", "Link to structure set object")
    _ensure_hidden_link_property(obj, "RegionPlan", "CorridorRoad", "Link to region plan object")
    _ensure_hidden_link_property(obj, "SectionSet", "CorridorRoad", "Link to section set object")
    _ensure_hidden_link_property(obj, CORRIDOR_PROJECT_PROPERTY, "CorridorRoad", "Link to corridor object")
    _ensure_hidden_link_property(obj, "DesignGradingSurface", "CorridorRoad", "Link to design grading surface object")
    _ensure_hidden_link_property(obj, "DesignTerrain", "CorridorRoad", "Link to design terrain object")
    _ensure_hidden_link_property(obj, "CutFillCalc", "CorridorRoad", "Link to cut/fill calc object")
    _hide_project_link_properties(obj)


def ensure_region_plan_object(region_obj):
    """Return the RegionPlan object or None when the input is not a RegionPlan."""
    if region_obj is None:
        return None
    try:
        proxy_type = str(getattr(getattr(region_obj, "Proxy", None), "Type", "") or "")
    except Exception:
        proxy_type = ""
    try:
        name = str(getattr(region_obj, "Name", "") or "")
    except Exception:
        name = ""
    if proxy_type == "RegionPlan" or name.startswith("RegionPlan"):
        return region_obj
    return None


def assign_project_region_plan(project_obj, region_obj):
    prj = project_obj
    if prj is None:
        return None
    region_obj = ensure_region_plan_object(region_obj)
    try:
        if hasattr(prj, "RegionPlan"):
            prj.RegionPlan = region_obj
    except Exception:
        pass
    return region_obj


def ensure_corridor_object(corridor_obj):
    """Return the corridor object or None when the input is not a corridor compatibility result.

    This helper is the preferred boundary for compatibility-name handling.
    New code should call this helper instead of matching the raw compatibility
    proxy/type/property names directly.
    """
    if corridor_obj is None:
        return None
    try:
        proxy_type = str(getattr(getattr(corridor_obj, "Proxy", None), "Type", "") or "")
    except Exception:
        proxy_type = ""
    try:
        name = str(getattr(corridor_obj, "Name", "") or "")
    except Exception:
        name = ""
    if proxy_type == CORRIDOR_PROXY_TYPE or (
        name.startswith(CORRIDOR_NAME_PREFIX)
        and not name.startswith("CorridorRoadProject")
        and not name.startswith("CorridorSegment")
    ):
        return corridor_obj
    return None


def find_corridor_objects(doc):
    out = []
    seen = set()
    if doc is None:
        return out
    for o in list(getattr(doc, "Objects", []) or []):
        cor = ensure_corridor_object(o)
        if cor is None:
            continue
        key = str(getattr(cor, "Name", "") or "") or str(id(cor))
        if key in seen:
            continue
        seen.add(key)
        out.append(cor)
    return out


def assign_project_corridor(project_obj, corridor_obj):
    prj = project_obj
    if prj is None:
        return None
    corridor_obj = ensure_corridor_object(corridor_obj)
    try:
        if hasattr(prj, CORRIDOR_PROJECT_PROPERTY):
            setattr(prj, CORRIDOR_PROJECT_PROPERTY, corridor_obj)
    except Exception:
        pass
    return corridor_obj


def _project_corridor_candidate(project_obj):
    try:
        corridor_obj = getattr(project_obj, CORRIDOR_PROJECT_PROPERTY, None) if hasattr(project_obj, CORRIDOR_PROJECT_PROPERTY) else None
    except Exception:
        corridor_obj = None
    return ensure_corridor_object(corridor_obj)


def resolve_project_corridor(project_obj_or_doc):
    """
    Resolve the preferred corridor object for a project/document and keep the
    project corridor link synchronized when possible.
    """
    prj = _resolve_project(project_obj_or_doc)
    if prj is None:
        return None
    corridor_obj = _project_corridor_candidate(prj)
    if corridor_obj is None:
        doc = getattr(prj, "Document", None)
        found = find_corridor_objects(doc)
        corridor_obj = found[0] if found else None
    if corridor_obj is not None:
        assign_project_corridor(prj, corridor_obj)
    return corridor_obj


def _project_region_plan_candidate(project_obj):
    try:
        region_obj = getattr(project_obj, "RegionPlan", None) if hasattr(project_obj, "RegionPlan") else None
    except Exception:
        region_obj = None
    return ensure_region_plan_object(region_obj)


def resolve_project_region_plan(project_obj_or_doc):
    """
    Resolve the preferred RegionPlan for a project/document and keep project
    compatibility links synchronized when possible.
    """
    prj = _resolve_project(project_obj_or_doc)
    if prj is None:
        return None
    region_obj = _project_region_plan_candidate(prj)
    if region_obj is None:
        doc = getattr(prj, "Document", None)
        candidates = find_region_plan_objects(doc)
        region_obj = candidates[0] if candidates else None
    if region_obj is not None:
        assign_project_region_plan(prj, region_obj)
    return region_obj


def find_region_plan_objects(doc):
    """Return unique RegionPlan objects visible in the document."""
    out = []
    seen = set()
    if doc is None:
        return out
    for o in list(getattr(doc, "Objects", []) or []):
        try:
            proxy_type = str(getattr(getattr(o, "Proxy", None), "Type", "") or "")
        except Exception:
            proxy_type = ""
        try:
            name = str(getattr(o, "Name", "") or "")
        except Exception:
            name = ""
        if proxy_type != "RegionPlan" and not name.startswith("RegionPlan"):
            continue
        upgraded = ensure_region_plan_object(o)
        if upgraded is None:
            continue
        key = str(getattr(upgraded, "Name", "") or "")
        if key in seen:
            continue
        seen.add(key)
        out.append(upgraded)
    return out


def _is_unassigned_alignment_root(aln_root) -> bool:
    if aln_root is None:
        return False
    try:
        if str(getattr(aln_root, ALN_NAME_PROP, "") or "").strip() == "Unassigned":
            return True
    except Exception:
        pass
    try:
        if str(getattr(aln_root, "Label", "") or "").strip().startswith("ALN_Unassigned"):
            return True
    except Exception:
        pass
    return False


def _folder_tree_has_payload(folder) -> bool:
    if folder is None:
        return False
    for ch in _group_get(folder):
        if _is_tree_folder(ch):
            if _folder_tree_has_payload(ch):
                return True
            continue
        return True
    return False


def _delete_folder_tree(doc, folder):
    if doc is None or folder is None:
        return
    children = [ch for ch in _group_get(folder) if _is_tree_folder(ch)]
    for ch in children:
        _delete_folder_tree(doc, ch)
    try:
        doc.removeObject(_name(folder))
    except Exception:
        pass


def _prune_empty_unassigned_alignment_roots(prj):
    if prj is None:
        return
    tree = ensure_project_tree(prj, include_references=False)
    root_alignments = tree.get(TREE_ALIGNMENTS, None)
    doc = getattr(prj, "Document", None)
    if root_alignments is None or doc is None:
        return
    for aln_root in list(_iter_alignment_roots(root_alignments)):
        if not _is_unassigned_alignment_root(aln_root):
            continue
        if _folder_tree_has_payload(aln_root):
            continue
        try:
            _group_remove(root_alignments, aln_root)
        except Exception:
            pass
        _delete_folder_tree(doc, aln_root)


def _migrate_region_plan_links(obj_project):
    if obj_project is None:
        return
    doc = getattr(obj_project, "Document", None)
    if doc is None:
        return
    try:
        from freecad.Corridor_Road.objects.obj_section_set import (
            region_plan_usage_enabled as _section_region_plan_usage_enabled,
            resolve_region_plan_source as _section_resolve_region_plan_source,
            synchronize_region_plan_state as _section_synchronize_region_plan_state,
        )
    except Exception:
        _section_region_plan_usage_enabled = None
        _section_resolve_region_plan_source = None
        _section_synchronize_region_plan_state = None

    def _section_candidate(section_obj):
        try:
            target = _section_resolve_region_plan_source(section_obj) if _section_resolve_region_plan_source is not None else None
        except Exception:
            target = None
        if target is not None:
            return ensure_region_plan_object(target)
        try:
            sec_region_plan = getattr(section_obj, "RegionPlan", None) if hasattr(section_obj, "RegionPlan") else None
        except Exception:
            sec_region_plan = None
        target = ensure_region_plan_object(sec_region_plan)
        if target is not None:
            return target
        return ensure_region_plan_object(project_region_plan)

    def _section_enabled(section_obj):
        try:
            if _section_region_plan_usage_enabled is not None:
                return bool(_section_region_plan_usage_enabled(section_obj))
        except Exception:
            pass
        try:
            return bool(getattr(section_obj, "UseRegionPlan", False))
        except Exception:
            return False

    preferred = None
    for o in list(getattr(doc, "Objects", []) or []):
        try:
            proxy_type = str(getattr(getattr(o, "Proxy", None), "Type", "") or "")
        except Exception:
            proxy_type = ""
        if proxy_type != "RegionPlan":
            continue
        upgraded = ensure_region_plan_object(o)
        if preferred is None and upgraded is not None:
            preferred = upgraded

    project_region_plan = _project_region_plan_candidate(obj_project)
    if project_region_plan is None:
        project_region_plan = preferred

    assign_project_region_plan(obj_project, project_region_plan)

    for o in list(getattr(doc, "Objects", []) or []):
        try:
            proxy_type = str(getattr(getattr(o, "Proxy", None), "Type", "") or "")
        except Exception:
            proxy_type = ""
        if proxy_type != "SectionSet":
            continue
        target = _section_candidate(o)
        enabled = _section_enabled(o)
        try:
            if _section_synchronize_region_plan_state is not None:
                _section_synchronize_region_plan_state(o, preferred_region=target, enabled=enabled)
            else:
                if hasattr(o, "RegionPlan") and target is not None:
                    o.RegionPlan = target
                if hasattr(o, "UseRegionPlan"):
                    o.UseRegionPlan = enabled
        except Exception:
            pass


class CorridorRoadProject:
    """
    Project container:
    - stores Links to key objects
    - optionally groups child objects via Group property (DocumentObjectGroup)
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "CorridorRoadProject"
        ensure_project_properties(obj)
        ensure_project_viewprovider(obj)

    def execute(self, obj):
        ensure_project_properties(obj)
        ensure_project_viewprovider(obj)
        _migrate_region_plan_links(obj)
        ensure_project_tree(obj, include_references=False)
        _adopt_project_linked_objects(obj)
        _adopt_document_candidates(obj)
        _rebalance_all_tree_objects(obj)
        _prune_root_nonfolders(obj)
        # Container does not generate shape.
        return

    @staticmethod
    def adopt(obj_project, child):
        """Place child into fixed schema folders under project."""
        if obj_project is None or child is None:
            return
        if _is_type(child, proxy_types=(), name_prefixes=("CenterlineBoundaryMarker",)):
            CorridorRoadProject.unadopt(obj_project, child)
            return
        ensure_project_properties(obj_project)
        target = _resolve_target_container(obj_project, child, allow_references=True)
        if target is None:
            return
        _detach_from_other_tree_folders(obj_project, child, keep_owner=target)
        _group_add(target, child)
        _remove_empty_legacy_tree_folders(obj_project)
        # Ensure non-folder objects do not remain directly under project root.
        if target != obj_project and (not _is_tree_folder(child)):
            _group_remove(obj_project, child)
            # Hard cleanup fallback in case removeObject/path failed.
            roots = _group_get(obj_project)
            if child in roots:
                _group_set(obj_project, [ch for ch in roots if ch != child])
            _prune_root_nonfolders(obj_project)

    @staticmethod
    def unadopt(obj_project, child):
        """Remove child from project tree folders so it can be shown only via claimChildren."""
        if obj_project is None or child is None:
            return
        owners = [obj_project] + _iter_tree_folders(obj_project)
        for owner in owners:
            if owner is None or owner == child:
                continue
            _group_remove(owner, child)
        _prune_root_nonfolders(obj_project)

    @staticmethod
    def auto_link(doc, obj_project):
        """Try to auto-detect first alignment/stationing/profile and link them."""
        if doc is None:
            return
        _migrate_region_plan_links(obj_project)

        if obj_project.Alignment is None:
            # Keep Alignment link empty when property is visible (avoid tree duplication).
            try:
                pt = str(obj_project.getTypeIdOfProperty("Alignment") or "")
            except Exception:
                pt = ""
            if "Hidden" in pt:
                a = _find_first(doc, "HorizontalAlignment")
                if a is not None:
                    obj_project.Alignment = a

        if obj_project.Stationing is None:
            s = _find_first(doc, "Stationing")
            if s is not None:
                obj_project.Stationing = s

        if hasattr(obj_project, "Centerline3D") and obj_project.Centerline3D is None:
            c = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "Centerline3D":
                    c = o
                    break
                if o.Name.startswith("Centerline3D") and (not o.Name.startswith("Centerline3DDisplay")):
                    c = o
                    break
            if c is not None:
                obj_project.Centerline3D = c

        if hasattr(obj_project, "Centerline3DDisplay") and obj_project.Centerline3DDisplay is None:
            d = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "Centerline3DDisplay":
                    d = o
                    break
                if o.Name.startswith("Centerline3DDisplay"):
                    d = o
                    break
            if d is not None:
                obj_project.Centerline3DDisplay = d

        if hasattr(obj_project, "AssemblyTemplate") and obj_project.AssemblyTemplate is None:
            a = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "AssemblyTemplate":
                    a = o
                    break
                if o.Name.startswith("AssemblyTemplate"):
                    a = o
                    break
            if a is not None:
                obj_project.AssemblyTemplate = a

        if hasattr(obj_project, "TypicalSectionTemplate") and obj_project.TypicalSectionTemplate is None:
            t = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "TypicalSectionTemplate":
                    t = o
                    break
                if o.Name.startswith("TypicalSectionTemplate"):
                    t = o
                    break
            if t is not None:
                obj_project.TypicalSectionTemplate = t

        if hasattr(obj_project, "StructureSet") and obj_project.StructureSet is None:
            s = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "StructureSet":
                    s = o
                    break
                if o.Name.startswith("StructureSet"):
                    s = o
                    break
            if s is not None:
                obj_project.StructureSet = s

        if hasattr(obj_project, "RegionPlan") and obj_project.RegionPlan is None:
            resolve_project_region_plan(obj_project)

        if hasattr(obj_project, "SectionSet") and obj_project.SectionSet is None:
            s = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "SectionSet":
                    s = o
                    break
                if o.Name.startswith("SectionSet"):
                    s = o
                    break
            if s is not None:
                obj_project.SectionSet = s

        if hasattr(obj_project, CORRIDOR_PROJECT_PROPERTY) and getattr(obj_project, CORRIDOR_PROJECT_PROPERTY, None) is None:
            resolve_project_corridor(obj_project)

        if hasattr(obj_project, "DesignGradingSurface") and obj_project.DesignGradingSurface is None:
            g = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "DesignGradingSurface":
                    g = o
                    break
                if o.Name.startswith("DesignGradingSurface"):
                    g = o
                    break
            if g is not None:
                obj_project.DesignGradingSurface = g

        if hasattr(obj_project, "DesignTerrain") and obj_project.DesignTerrain is None:
            d = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "DesignTerrain":
                    d = o
                    break
                if o.Name.startswith("DesignTerrain"):
                    d = o
                    break
            if d is not None:
                obj_project.DesignTerrain = d

        if hasattr(obj_project, "CutFillCalc") and obj_project.CutFillCalc is None:
            s = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "CutFillCalc":
                    s = o
                    break
                if o.Name.startswith("CutFillCalc"):
                    s = o
                    break
            if s is not None:
                obj_project.CutFillCalc = s

        ensure_project_tree(obj_project, include_references=False)
        _adopt_project_linked_objects(obj_project)
        _adopt_document_candidates(obj_project)
        _rebalance_all_tree_objects(obj_project)
        _prune_root_nonfolders(obj_project)
