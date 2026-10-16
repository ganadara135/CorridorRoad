# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/objects/obj_project.py
import FreeCAD as App
import math
import re
from freecad.Corridor_Road.objects import design_standards as _ds
from freecad.Corridor_Road.objects import unit_policy as _units


TREE_KEY_PROP = "CRTreeKey"

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
V1_TREE_CENTERLINE3D = "v1_centerline3d"
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
V1_TREE_BUILD_PARAMETRIC_OUTPUTS = "v1_build_parametric_outputs"
V1_TREE_INTERSECTIONS = "v1_intersections"
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
V1_TREE_WATERTIGHT_SOLIDS = "v1_watertight_solids"
V1_TREE_AI_SUGGESTIONS = "v1_ai_suggestions"
V1_TREE_AI_CHECKS = "v1_ai_checks"
V1_TREE_AI_GENERATED_ALTERNATIVES = "v1_ai_generated_alternatives"
V1_TREE_AI_USER_DECISIONS = "v1_ai_user_decisions"

V1_ROOT_TREE_DEFS = (
    (V1_TREE_PROJECT_SETUP, "00_Project Setup", "CRV1_00_Project_Setup"),
    (V1_TREE_SOURCE_DATA, "01_Source Data", "CRV1_01_Source_Data"),
    # the object names keep their original digits so saved documents keep their folders
    (V1_TREE_SURFACES, "02_Surfaces", "CRV1_03_Surfaces"),
    (V1_TREE_ALIGNMENT_PROFILE, "03_Alignment & Profile", "CRV1_02_Alignment_Profile"),
    (V1_TREE_CORRIDOR_MODEL, "04_Parametric Model", "CRV1_04_Corridor_Model"),
    (V1_TREE_DRAINAGE, "05_Drainage", "CRV1_05_Drainage"),
    (V1_TREE_STRUCTURES, "06_Structures", "CRV1_06_Structures"),
    (V1_TREE_QUANTITIES_EARTHWORK, "07_Quantities & Earthwork", "CRV1_07_Quantities_Earthwork"),
    (V1_TREE_REVIEW, "08_Review", "CRV1_08_Review"),
    (V1_TREE_OUTPUTS_EXCHANGE, "09_Outputs & Exchange", "CRV1_09_Outputs_Exchange"),
    (V1_TREE_AI_ASSIST, "10_AI Assist", "CRV1_10_AI_Assist"),
)
V1_LEGACY_TREE_LABELS = {
    V1_TREE_CORRIDOR_MODEL: {"04_Corridor Model"},
}
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
    (V1_TREE_ALIGNMENT_PROFILE, V1_TREE_CENTERLINE3D, "3D Centerline", "CRV1_3D_Centerline"),
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
    (V1_TREE_CORRIDOR_MODEL, V1_TREE_BUILD_PARAMETRIC_OUTPUTS, "Build Parametric Outputs", "CRV1_Build_Parametric_Outputs"),
    (V1_TREE_CORRIDOR_MODEL, V1_TREE_INTERSECTIONS, "Intersections", "CRV1_Intersections"),
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
    (V1_TREE_OUTPUTS_EXCHANGE, V1_TREE_WATERTIGHT_SOLIDS, "Watertight Solids", "CRV1_Watertight_Solids"),
    (V1_TREE_AI_ASSIST, V1_TREE_AI_SUGGESTIONS, "Suggestions", "CRV1_AI_Suggestions"),
    (V1_TREE_AI_ASSIST, V1_TREE_AI_CHECKS, "Checks", "CRV1_AI_Checks"),
    (V1_TREE_AI_ASSIST, V1_TREE_AI_GENERATED_ALTERNATIVES, "Generated Alternatives", "CRV1_AI_Generated_Alternatives"),
    (V1_TREE_AI_ASSIST, V1_TREE_AI_USER_DECISIONS, "User Decisions", "CRV1_AI_User_Decisions"),
)


def find_project(doc):
    if doc is None:
        return None
    for o in doc.Objects:
        if o.Name.startswith("CorridorRoadProject"):
            return o
        proxy = getattr(o, "Proxy", None)
        if proxy is not None and getattr(proxy, "Type", "") == "CorridorRoadProject":
            return o
        if str(getattr(o, "Label", "") or "") in {"CorridorRoad Project", "Parametric Road Project"}:
            return o
    return None


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


def _find_document_tree_folder(doc, key: str, obj_name: str | None = None):
    if doc is None:
        return None
    if obj_name:
        obj = doc.getObject(str(obj_name))
        if _is_group_obj(obj):
            return obj
    for obj in list(getattr(doc, "Objects", []) or []):
        if not _is_group_obj(obj):
            continue
        if _tree_key(obj) == str(key):
            if obj_name and _name(obj) != str(obj_name):
                continue
            return obj
    return None


def _ensure_child_folder(doc, owner, key: str, label: str, obj_name: str):
    if doc is None or owner is None:
        return None

    folder = doc.getObject(str(obj_name))
    if folder is not None and not _is_group_obj(folder):
        folder = None
    if folder is None:
        folder = _find_child_folder(owner, key)
        if folder is not None and _name(folder) != str(obj_name):
            folder = None
    if folder is None:
        # Label fallback for compatibility with manually created folders.
        for ch in _group_get(owner):
            if _is_group_obj(ch) and not _tree_key(ch) and _label(ch) == str(label) and _name(ch) == str(obj_name):
                folder = ch
                break
    if folder is None:
        folder = _find_document_tree_folder(doc, key, obj_name)
    if folder is None:
        folder = doc.addObject("App::DocumentObjectGroup", str(obj_name))

    _ensure_folder_meta(folder, key)
    _update_folder_label(folder, key, label, force=True)
    _group_add(owner, folder)
    return folder


def _enforce_project_tree_folder_parents(obj_project, tree: dict) -> None:
    """Keep each fixed project-tree folder under its declared parent only."""

    if obj_project is None:
        return
    root_parent_by_key = {key: obj_project for key, _label, _obj_name in V1_ROOT_TREE_DEFS}
    subtree_parent_by_key = {key: parent_key for parent_key, key, _label, _obj_name in V1_SUBTREE_DEFS}
    all_owners = [obj_project] + _iter_tree_folders(obj_project)
    for key, folder in list(tree.items()):
        if folder is None:
            continue
        expected_parent = root_parent_by_key.get(key)
        if expected_parent is None:
            expected_parent_key = subtree_parent_by_key.get(key)
            expected_parent = tree.get(expected_parent_key, None)
        if expected_parent is None:
            continue
        for owner in list(all_owners):
            if owner is None or owner == folder or owner == expected_parent:
                continue
            _group_remove(owner, folder)
        _group_add(expected_parent, folder)


def _dedupe_project_tree_folders(obj_project, tree: dict) -> None:
    """Merge duplicate fixed tree folders left by older tree definitions."""

    if obj_project is None:
        return
    doc = getattr(obj_project, "Document", None)
    if doc is None:
        return
    known_keys = {
        key for key, _label, _obj_name in V1_ROOT_TREE_DEFS
    } | {
        key for _parent_key, key, _label, _obj_name in V1_SUBTREE_DEFS
    }
    subtree_parent_by_key = {key: parent_key for parent_key, key, _label, _obj_name in V1_SUBTREE_DEFS}
    owners = [obj_project] + _iter_tree_folders(obj_project)
    for folder in list(getattr(doc, "Objects", []) or []):
        key = _tree_key(folder)
        inferred_key = ""
        if not key and _looks_like_intersections_tree_folder(folder):
            inferred_key = V1_TREE_INTERSECTIONS
        if key == "v1_build_parametric_intersections":
            key = V1_TREE_INTERSECTIONS
        folder_key = key or inferred_key
        if not folder_key or folder_key not in known_keys:
            continue
        canonical = tree.get(folder_key, None)
        if canonical is None or folder == canonical:
            continue
        _merge_duplicate_tree_folder_payload(folder, canonical, tree, known_keys)
        for owner in owners:
            if owner is None or owner == folder:
                continue
            _group_remove(owner, folder)
        expected_parent_key = subtree_parent_by_key.get(folder_key, "")
        expected_parent = tree.get(expected_parent_key, obj_project)
        if expected_parent is not None and canonical is not None:
            _group_add(expected_parent, canonical)
        if not _group_get(folder):
            try:
                doc.removeObject(_name(folder))
            except Exception:
                pass


def _merge_duplicate_tree_folder_payload(folder, canonical, tree: dict, known_keys: set[str]) -> None:
    """Move duplicate tree-folder payload into canonical destinations."""

    if folder is None or canonical is None:
        return
    doc = getattr(folder, "Document", None)
    for child in list(_group_get(folder)):
        child_key = _tree_key(child)
        child_target = tree.get(child_key, None) if child_key in known_keys else None
        if child_target is None and _looks_like_intersections_tree_folder(child):
            child_target = tree.get(V1_TREE_INTERSECTIONS, None)
            if _is_group_obj(child):
                _merge_duplicate_tree_folder_payload(child, child_target, tree, known_keys)
        if child_target is None and _is_v1_intersection_build_parametric_output(child):
            child_target = tree.get(V1_TREE_INTERSECTIONS, None)
        if child_target is None or child_target == folder:
            child_target = canonical
        if child != child_target:
            _group_add(child_target, child)
        _group_remove(folder, child)
        if _is_group_obj(child) and child_target is not None and child != child_target and not _group_get(child):
            _group_remove(child_target, child)
            try:
                if doc is not None:
                    doc.removeObject(_name(child))
            except Exception:
                pass


def _looks_like_intersections_tree_folder(folder) -> bool:
    if not _is_group_obj(folder):
        return False
    return bool(
        re.match(r"^Intersections\d*$", _label(folder))
        or re.match(r"^Intersections\d*$", _name(folder))
        or _label(folder) == "Intersection Sources"
        or _name(folder) == "CRV1_Intersections"
        or _name(folder) == "CRV1_Build_Parametric_Intersections"
    )


def _update_folder_label(folder, key: str, label: str, *, force: bool = False) -> None:
    if folder is None:
        return
    desired = str(label)
    current = str(getattr(folder, "Label", "") or "")
    if current == desired:
        return
    legacy_labels = V1_LEGACY_TREE_LABELS.get(str(key), set())
    if (not force) and current and current not in legacy_labels:
        return
    try:
        folder.Label = desired
    except Exception:
        pass


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
    _enforce_project_tree_folder_parents(obj_project, out)
    _dedupe_project_tree_folders(obj_project, out)
    for parent_key in dict.fromkeys(parent_key for parent_key, _key, _label, _obj_name in V1_SUBTREE_DEFS):
        parent = out.get(parent_key, None)
        if parent is not None:
            ordered_keys = [key for pkey, key, _label, _obj_name in V1_SUBTREE_DEFS if pkey == parent_key]
            _reorder_children_by_tree_keys(parent, ordered_keys)

    if include_references:
        out[V1_TREE_EXISTING_REFERENCES] = out.get(V1_TREE_EXISTING_REFERENCES, None)
    return out


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


def _is_alignment_related(child):
    # v1 alignments carry IP rows; the v1 profile editor names its previews FinishedGradeFG_*
    return _looks_like_horizontal_alignment(child) or _is_type(child, name_prefixes=("FinishedGradeFG",))


def _is_surface(child):
    return _is_type(
        child,
        proxy_types=("V1SurfaceModel", "SurfaceModel"),
        name_prefixes=("V1SurfaceModel", "SurfaceModel"),
    )


def _is_v1_intersection(child):
    return _is_type(
        child,
        proxy_types=("IntersectionModel", "Intersection"),
        name_prefixes=("IntersectionModel", "Intersection"),
    )


def _is_v1_intersection_build_parametric_output(child):
    """Return True for intersection review/preview objects generated by Build Parametric."""

    if child is None:
        return False
    record_kind = str(getattr(child, "CRRecordKind", "") or "")
    if record_kind in {
        "v1_intersection_review_overlay",
        "v1_corridor_intersection_tie_in_edge_preview",
        "v1_corridor_intersection_boundary_segment_preview",
        "v1_corridor_intersection_exclusion_zone_preview",
        "v1_corridor_intersection_slope_face_loop_preview",
        "v1_corridor_intersection_slope_face_surface_preview",
        "v1_corridor_intersection_slope_face_boundary_preview",
        "v1_corridor_intersection_tie_slope_surface_preview",
        "v1_corridor_roundabout_entry_exit_surface_preview",
        "v1_corridor_roundabout_apron_surface_preview",
        "v1_corridor_roundabout_subgrade_surface_preview",
        "v1_corridor_roundabout_slope_face_surface_preview",
        "v1_intersection_contract_review_highlight",
    }:
        return True
    if record_kind in {"v1_corridor_surface_preview", "v1_corridor_surface_preview_diagnostic"}:
        role = str(getattr(child, "SurfaceRole", "") or getattr(child, "Role", "") or "").lower()
        surface_kind = str(getattr(child, "SurfaceKind", "") or "").lower()
        if role == "intersection" or surface_kind == "intersection_surface":
            return True
    if _is_type(
        child,
        proxy_types=(
            "V1CorridorIntersectionSurfacePreview",
            "V1CorridorIntersectionTieInEdgePreview",
            "V1CorridorIntersectionBoundarySegmentPreview",
            "V1CorridorIntersectionExclusionZonePreview",
            "V1CorridorIntersectionSlopeFaceLoopPreview",
            "V1CorridorIntersectionSlopeFaceSurfacePreview",
            "V1CorridorIntersectionSlopeFaceBoundaryPreview",
            "V1CorridorIntersectionTieSlopeSurfacePreview",
            "V1CorridorRoundaboutEntryExitSurfacePreview",
            "V1CorridorRoundaboutApronSurfacePreview",
            "V1CorridorRoundaboutSubgradeSurfacePreview",
            "V1CorridorRoundaboutSlopeFaceSurfacePreview",
        ),
        name_prefixes=(
            "V1CorridorIntersectionSurfacePreview",
            "V1CorridorIntersectionTieInEdgePreview",
            "V1CorridorIntersectionBoundarySegmentPreview",
            "V1CorridorIntersectionExclusionZonePreview",
            "V1CorridorIntersectionSlopeFaceLoopPreview",
            "V1CorridorIntersectionSlopeFaceSurfacePreview",
            "V1CorridorIntersectionSlopeFaceBoundaryPreview",
            "V1CorridorIntersectionTieSlopeSurfacePreview",
            "V1CorridorRoundaboutEntryExitSurfacePreview",
            "V1CorridorRoundaboutApronSurfacePreview",
            "V1CorridorRoundaboutSubgradeSurfacePreview",
            "V1CorridorRoundaboutSlopeFaceSurfacePreview",
        ),
    ):
        return True
    label = _label(child)
    if label in {
        "Intersection Tie-in Edges",
        "Intersection Boundary Segments",
        "Intersection Exclusion Zone",
        "Intersection Slope Face Loops",
        "Intersection Slope Face Surface",
        "Intersection Slope Face Boundary",
        "Intersection Tie Slope",
    }:
        return True
    return False


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
            "V1Centerline3DReview",
            "Centerline3DReview",
            "ReviewIssue",
            "ReviewBookmark",
            "Issue",
            "Bookmark",
        ),
        name_prefixes=(
            "PlanProfileReview",
            "SectionReview",
            "TINReview",
            "V1Centerline3DPreview",
            "Centerline3DReview",
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
            "V1SimulationPackageOutput",
            "V1WatertightSolidOutput",
        ),
        name_prefixes=(
            "SheetOutput",
            "ReportOutput",
            "DXFExport",
            "LandXMLExport",
            "IFCExport",
            "ExchangePackage",
            "V1SimulationPackageOutput",
            "V1WatertightSolidOutput",
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
    if record_kind == "v1_intersection_contract_review_highlight":
        return tree.get(V1_TREE_ISSUES, None)
    if _is_v1_intersection_build_parametric_output(child):
        return tree.get(V1_TREE_INTERSECTIONS, None)
    if record_kind == "tin_source_csv":
        return tree.get(V1_TREE_SURVEY_POINTS, None)
    if record_kind == "tin_surface_source":
        return tree.get(V1_TREE_EXISTING_GROUND_TIN_SOURCE, None)
    if record_kind == "tin_surface_result":
        return tree.get(V1_TREE_EXISTING_GROUND_TIN_RESULT, None)
    if record_kind in {
        "v1_corridor_centerline_preview",
        "v1_corridor_surface_preview",
        "v1_corridor_region_surface_preview",
        "v1_corridor_surface_preview_diagnostic",
        "v1_surface_transition_span_marker",
    }:
        return tree.get(V1_TREE_BUILD_PARAMETRIC_OUTPUTS, None)
    if record_kind == "v1_surface_transition_model":
        return tree.get(V1_TREE_REGIONS, None)
    # the aggregate slope-face markers are review diagnostics and the per-issue ones
    # review issues; both belong beside the surfaces they annotate
    if record_kind in {"v1_review_issue", "v1_review_diagnostic"}:
        issue_kind = str(getattr(child, "IssueKind", "") or "")
        name = _name(child)
        if issue_kind in {
            "slope_face_tie_in",
            "slope_face_tie_in_diagnostic",
            "slope_face_fallback",
            "surface_transition_span",
            "drainage_flow",
            "drainage_station",
            "subassembly_kind",
        }:
            return tree.get(V1_TREE_BUILD_PARAMETRIC_OUTPUTS, None)
        if name.startswith(("ReviewIssueSlopeFace", "ReviewIssueDrainage", "ReviewDiagnosticSlopeFace")):
            return tree.get(V1_TREE_BUILD_PARAMETRIC_OUTPUTS, None)
    if record_kind in {
        "v1_centerline3d_review",
        "v1_centerline3d_station_markers",
    }:
        return tree.get(V1_TREE_CENTERLINE3D, None)
    if record_kind == "v1_intersection_model":
        return tree.get(V1_TREE_INTERSECTIONS, None)
    if record_kind == "v1_assembly_subassembly_model":
        return tree.get(V1_TREE_ASSEMBLIES, None)
    if record_kind == "v1_subassembly_library":
        return tree.get(V1_TREE_ASSEMBLIES, None)
    if record_kind == "v1_assembly_show_preview":
        return tree.get(V1_TREE_ASSEMBLIES, None)
    if record_kind == "v1_structure_show_preview":
        return tree.get(V1_TREE_STRUCTURES, None)
    if record_kind == "v1_structure_row_preview":
        return tree.get(V1_TREE_STRUCTURES, None)
    if record_kind == "v1_structure_connection_point_preview":
        return tree.get(V1_TREE_STRUCTURES, None)
    if record_kind in {
        "v1_applied_section_show_preview",
        "v1_applied_sections_show_all_preview",
        "v1_applied_section_station_marker",
    }:
        return tree.get(V1_TREE_APPLIED_SECTIONS, None)
    if record_kind in {
        "v1_watertight_solid_output",
        "v1_watertight_trim_preview",
        "v1_watertight_trim_application_preview",
        "v1_watertight_trim_application_output",
        "v1_watertight_trim_closure_surface_preview",
        "v1_watertight_trim_closure_surface_output",
        "v1_watertight_trim_closure_cell_output",
        "v1_watertight_trim_shell_candidate_output",
        "v1_watertight_trim_fuse_candidate_output",
        "v1_watertight_trim_shell_reconstruction_output",
        "v1_watertight_trim_solid_reconstruction_output",
        "v1_intersection_trim_boundary_result",
    }:
        return tree.get(V1_TREE_WATERTIGHT_SOLIDS, None)
    if record_kind == "v1_simulation_qa_output":
        return tree.get(V1_TREE_REPORTS, None)
    if record_kind == "v1_simulation_package_output":
        return tree.get(V1_TREE_EXCHANGE_PACKAGES, None)
    if record_kind == "v1_landxml_import":
        return tree.get(V1_TREE_EXCHANGE_PACKAGES, None)
    if record_kind == "v1_quantity_model":
        return tree.get(V1_TREE_QUANTITIES, None)
    if record_kind == "v1_drainage_model":
        return tree.get(V1_TREE_DRAINAGE, None)
    if record_kind == "v1_drainage_pipeline_candidate_preview":
        return tree.get(V1_TREE_DRAINAGE, None)
    if record_kind == "v1_drainage_pipeline_segment_preview":
        return tree.get(V1_TREE_DRAINAGE, None)
    if record_kind == "v1_drainage_pipeline_network_preview":
        return tree.get(V1_TREE_DRAINAGE, None)
    if record_kind == "v1_drainage_pipeline_networks_preview":
        return tree.get(V1_TREE_DRAINAGE, None)
    if record_kind == "v1_drainage_pipeline_segment_output_preview":
        return tree.get(V1_TREE_DRAINAGE, None)
    if record_kind == "v1_structure_pipe_connection_point_preview":
        return tree.get(V1_TREE_STRUCTURES, None)
    if record_kind == "tin_mesh_preview":
        return tree.get(V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW, None)
    if record_kind == "tin_diagnostics":
        return tree.get(V1_TREE_EXISTING_GROUND_TIN_DIAGNOSTICS, None)
    if _is_type(child, proxy_types=("V1Alignment",), name_prefixes=("V1Alignment",)) or _looks_like_horizontal_alignment(child):
        return tree.get(V1_TREE_ALIGNMENTS, None)
    if _is_type(
        child,
        proxy_types=("V1Profile",),
        name_prefixes=("V1Profile", "FinishedGradeFG"),
    ):
        return tree.get(V1_TREE_PROFILES, None)
    if _is_type(
        child,
        proxy_types=("V1Stationing", "V1StationHighlight"),
        name_prefixes=("V1Stationing", "V1StationHighlight"),
    ):
        return tree.get(V1_TREE_STATIONS, None)
    if record_kind in {"v1_superelevation_source", "v1_superelevation_review"}:
        return tree.get(V1_TREE_SUPERELEVATION, None)
    if record_kind == "v1_intersection_review_overlay":
        return tree.get(V1_TREE_INTERSECTIONS, None)
    if _is_type(
        child,
        proxy_types=("V1SuperelevationSource", "Superelevation", "SuperelevationModel"),
        name_prefixes=("V1SuperelevationSource", "Superelevation", "SuperelevationModel"),
    ):
        return tree.get(V1_TREE_SUPERELEVATION, None)
    if _is_v1_intersection(child):
        return tree.get(V1_TREE_INTERSECTIONS, None)
    if _is_v1_drainage(child):
        return tree.get(V1_TREE_DRAINAGE, None)
    if _is_type(
        child,
        proxy_types=(
            "V1AssemblySubassemblyModel",
            "V1AssemblyModel",
            "AssemblyModel",
        ),
        name_prefixes=(
            "V1AssemblySubassemblyModel",
            "V1AssemblyModel",
            "AssemblyModel",
        ),
    ):
        return tree.get(V1_TREE_ASSEMBLIES, None)
    if _is_type(
        child,
        proxy_types=("V1RegionModel", "RegionModel", "V1SurfaceTransitionModel"),
        name_prefixes=("V1RegionModel", "RegionModel", "V1SurfaceTransitionModel"),
    ):
        return tree.get(V1_TREE_REGIONS, None)
    if _is_type(
        child,
        proxy_types=("V1AppliedSectionSet", "AppliedSectionSet"),
        name_prefixes=("V1AppliedSectionSet", "AppliedSectionSet"),
    ):
        return tree.get(V1_TREE_APPLIED_SECTIONS, None)
    if _is_type(
        child,
        proxy_types=("V1CorridorCenterlinePreview",),
        name_prefixes=("V1CorridorCenterlinePreview",),
    ):
        return tree.get(V1_TREE_BUILD_PARAMETRIC_OUTPUTS, None)
    if _is_type(
        child,
        proxy_types=("V1CorridorModel", "CorridorModel"),
        name_prefixes=("V1CorridorModel", "CorridorModel"),
    ):
        return tree.get(V1_TREE_CORRIDOR_MODEL, None)
    if _is_type(child, proxy_types=("V1SurfaceModel", "SurfaceModel"), name_prefixes=("V1SurfaceModel", "SurfaceModel")):
        return tree.get(V1_TREE_DESIGN_TIN, None)
    if _is_type(child, proxy_types=("V1StructureModel", "StructureModel"), name_prefixes=("V1StructureModel", "StructureModel")):
        return tree.get(V1_TREE_STRUCTURES, None)
    if _is_type(child, proxy_types=("V1QuantityModel", "QuantityModel"), name_prefixes=("V1QuantityModel", "QuantityModel")):
        return tree.get(V1_TREE_QUANTITIES, None)
    if _is_v1_review(child):
        if _is_type(child, proxy_types=("PlanProfileReview",), name_prefixes=("PlanProfileReview",)):
            return tree.get(V1_TREE_PLAN_PROFILE_REVIEW, None)
        if _is_type(child, proxy_types=("SectionReview",), name_prefixes=("SectionReview",)):
            return tree.get(V1_TREE_SECTION_REVIEW, None)
        if _is_type(child, proxy_types=("TINReview",), name_prefixes=("TINReview",)):
            return tree.get(V1_TREE_TIN_REVIEW, None)
        if _is_type(child, proxy_types=("V1Centerline3DReview", "Centerline3DReview"), name_prefixes=("V1Centerline3DPreview", "Centerline3DReview")):
            return tree.get(V1_TREE_CENTERLINE3D, None)
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
        if _is_type(child, proxy_types=("V1SimulationPackageOutput",), name_prefixes=("V1SimulationPackageOutput",)):
            return tree.get(V1_TREE_EXCHANGE_PACKAGES, None)
        if _is_type(child, proxy_types=("V1WatertightSolidOutput",), name_prefixes=("V1WatertightSolidOutput",)):
            return tree.get(V1_TREE_WATERTIGHT_SOLIDS, None)
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
    try:
        _detach_from_other_tree_folders(prj, child, keep_owner=folder)
    except Exception:
        pass
    _group_add(folder, child)
    return folder


def _is_probable_terrain_input(prj, child):
    if child is None:
        return False
    if child == getattr(prj, "Terrain", None):
        return True
    if _is_surface(child) or _is_alignment_related(child):
        return False
    nm = _name(child).lower()
    lb = _label(child).lower()
    keywords = ("terrain", "existing", "eg", "survey", "topo", "dtm", "dem", "ground")
    return any(k in nm or k in lb for k in keywords)


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
    # the legacy object links stay as properties for saved documents but are no longer adopted
    link_props = ("Terrain", "Alignment", "Stationing")
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
        if _is_alignment_related(ch) or _is_surface(ch) or _is_probable_terrain_input(prj, ch):
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
        from freecad.Corridor_Road.v1.commands.cmd_project_setup import run_v1_project_setup_command

        document = getattr(preferred_project, "Document", None) or getattr(App, "ActiveDocument", None)
        run_v1_project_setup_command(document, preferred_project=preferred_project, prepare_project=False)
        return True
    except Exception as exc:
        App.Console.PrintError(f"Project Setup panel was not opened: {exc}\n")
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

    def __getstate__(self):
        # FreeCAD serializes view-provider proxies through PropertyPythonObject.
        # Keep transient FeaturePython references out of that state.
        return {"Type": "ViewProviderCorridorRoadProject"}

    def __setstate__(self, state):
        del state
        self.Type = "ViewProviderCorridorRoadProject"

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
        if (
            hasattr(proxy, "claimChildren")
            and hasattr(proxy, "setupContextMenu")
            and _has_custom_python_object_state(proxy)
        ):
            return
    try:
        ViewProviderCorridorRoadProject(vobj)
    except Exception:
        pass


def _has_custom_python_object_state(proxy) -> bool:
    try:
        state_method = getattr(type(proxy), "__getstate__", None)
        default_state_method = getattr(object, "__getstate__", None)
        return (
            state_method is not None
            and state_method is not default_state_method
            and callable(getattr(proxy, "__setstate__", None))
        )
    except Exception:
        return False


def _hide_project_link_properties(obj):
    if obj is None:
        return
    link_props = ("Terrain", "Alignment", "Stationing")
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
    if not hasattr(obj, "DocumentKind"):
        # general_road, intersection, or empty (not chosen); see v1 project_setup_service.
        obj.addProperty("App::PropertyString", "DocumentKind", "CorridorRoad", "General Road or Intersection document")
        obj.DocumentKind = ""
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
        obj.addProperty("App::PropertyString", "DesignStandard", "DesignCriteria", "Design standard (KDS/AASHTO)")
        obj.DesignStandard = _ds.DEFAULT_STANDARD
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
    _hide_project_link_properties(obj)


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
        ensure_project_properties(obj_project)
        target = _resolve_target_container(obj_project, child, allow_references=True)
        if target is None:
            return
        _detach_from_other_tree_folders(obj_project, child, keep_owner=target)
        _group_add(target, child)
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
        """Place the project's linked objects and the document's candidates into the tree."""
        if doc is None:
            return
        ensure_project_tree(obj_project, include_references=False)
        _adopt_project_linked_objects(obj_project)
        _adopt_document_candidates(obj_project)
        _rebalance_all_tree_objects(obj_project)
        _prune_root_nonfolders(obj_project)
