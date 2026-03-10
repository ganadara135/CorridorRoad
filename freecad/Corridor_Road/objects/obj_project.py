# CorridorRoad/objects/obj_project.py
import FreeCAD as App
import math
import re
from freecad.Corridor_Road.objects import design_standards as _ds


TREE_KEY_PROP = "CRTreeKey"
ALN_REF_PROP = "CRAlignmentRef"
ALN_REF_NAME_PROP = "CRAlignmentRefName"
ALN_NAME_PROP = "CRAlignmentName"

TREE_INPUTS = "root_inputs"
TREE_INPUTS_TERRAINS = "inputs_terrains"
TREE_INPUTS_SURVEY = "inputs_survey"
TREE_INPUTS_STRUCTURES = "inputs_structures"
TREE_ALIGNMENTS = "root_alignments"
TREE_SURFACES = "root_surfaces"
TREE_ANALYSIS = "root_analysis"
TREE_REFERENCES = "root_references"

ALIGNMENT_ROOT = "alignment_root"
ALIGNMENT_HORIZONTAL = "alignment_horizontal"
ALIGNMENT_STATIONING = "alignment_stationing"
ALIGNMENT_VERTICAL = "alignment_vertical_profiles"
ALIGNMENT_ASSEMBLY = "alignment_assembly"
ALIGNMENT_SECTIONS = "alignment_sections"
ALIGNMENT_CORRIDOR = "alignment_corridor"

BASE_TREE_DEFS = (
    (TREE_INPUTS, "01_Inputs", "CR_01_Inputs"),
    (TREE_ALIGNMENTS, "02_Alignments", "CR_02_Alignments"),
    (TREE_SURFACES, "03_Surfaces", "CR_03_Surfaces"),
    (TREE_ANALYSIS, "04_Analysis", "CR_04_Analysis"),
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
    (ALIGNMENT_ASSEMBLY, "Assembly", "CR_ALN_Assembly"),
    (ALIGNMENT_SECTIONS, "Sections", "CR_ALN_Sections"),
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


def get_length_scale(doc_or_project, default: float = 1.0) -> float:
    """
    Length scale = internal units per meter.
    1.0 means meter-native; 1000.0 means millimeter-like internal units.
    """
    if doc_or_project is None:
        return float(default)

    if hasattr(doc_or_project, "Document") and hasattr(doc_or_project, "LengthScale"):
        return _safe_scale(getattr(doc_or_project, "LengthScale", default), default=default)

    prj = find_project(doc_or_project) if hasattr(doc_or_project, "Objects") else None
    if prj is None:
        return float(default)
    return _safe_scale(getattr(prj, "LengthScale", default), default=default)


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


def meters_to_internal(doc_or_project, meters: float, default_scale: float = 1.0) -> float:
    return float(meters) * get_length_scale(doc_or_project, default=default_scale)


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
    }


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


def _ensure_child_folder(doc, owner, key: str, label: str, obj_name: str):
    if doc is None or owner is None:
        return None

    folder = _find_child_folder(owner, key)
    if folder is None:
        # Label fallback for compatibility with manually created folders.
        for ch in _group_get(owner):
            if _is_group_obj(ch) and _label(ch) == str(label):
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


def ensure_project_tree(obj_project, include_references: bool = False):
    if obj_project is None:
        return {}
    doc = getattr(obj_project, "Document", None)
    if doc is None:
        return {}

    ensure_project_properties(obj_project)

    out = {}
    for key, label, obj_name in BASE_TREE_DEFS:
        out[key] = _ensure_child_folder(doc, obj_project, key, label, obj_name)

    inputs = out.get(TREE_INPUTS, None)
    if inputs is not None:
        for key, label, obj_name in INPUT_SUBTREE_DEFS:
            out[key] = _ensure_child_folder(doc, inputs, key, label, obj_name)

    if include_references:
        out[TREE_REFERENCES] = _ensure_child_folder(doc, obj_project, TREE_REFERENCES, "05_References", "CR_05_References")
    _migrate_alignment_root_links(out.get(TREE_ALIGNMENTS, None))
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
    tree = ensure_project_tree(obj_project, include_references=False)
    root = tree.get(TREE_ALIGNMENTS, None)
    doc = getattr(obj_project, "Document", None)
    if root is None or doc is None:
        return {}

    aln_name = _alignment_name_from_obj(alignment_obj)
    aln_label_base = f"ALN_{aln_name}"
    aln_root = None

    for ch in _group_get(root):
        if not _is_group_obj(ch):
            continue
        if _tree_key(ch) != ALIGNMENT_ROOT:
            continue
        if _alignment_ref_matches(ch, alignment_obj):
            aln_root = ch
            break
        if alignment_obj is None and _label(ch) == aln_label_base:
            aln_root = ch
            break

    if aln_root is None:
        aln_root = doc.addObject("App::DocumentObjectGroup", f"CR_ALN_{aln_name}")
    aln_root.Label = _unique_alignment_label(root, aln_label_base, alignment_obj, exclude=aln_root)
    _ensure_alignment_folder_meta(aln_root, alignment_obj, aln_name)
    _group_add(root, aln_root)

    out = {"alignment_root": aln_root}
    for key, label, obj_name in ALIGNMENT_SUBTREE_DEFS:
        out[key] = _ensure_child_folder(doc, aln_root, key, label, f"{obj_name}_{aln_name}")
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

    if _is_type(child, proxy_types=("SectionSet",), name_prefixes=("SectionSet",)):
        aln = _alignment_from_section_set(child)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=("SectionSlice",), name_prefixes=("SectionSlice",)):
        sec = getattr(child, "ParentSectionSet", None)
        aln = _alignment_from_section_set(sec)
        if aln is not None:
            return aln

    if _is_type(child, proxy_types=("CorridorLoft",), name_prefixes=("CorridorLoft",)):
        sec = getattr(child, "SourceSectionSet", None)
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
            "Centerline3D",
            "AssemblyTemplate",
            "SectionSet",
            "SectionSlice",
            "CorridorLoft",
        ),
        name_prefixes=(
            "HorizontalAlignment",
            "Stationing",
            "VerticalAlignment",
            "ProfileBundle",
            "FinishedGradeFG",
            "Centerline3DDisplay",
            "Centerline3D",
            "AssemblyTemplate",
            "SectionSet",
            "SectionSlice",
            "CorridorLoft",
        ),
    )


def _is_surface(child):
    return _is_type(
        child,
        proxy_types=("DesignGradingSurface", "DesignTerrain"),
        name_prefixes=("DesignGradingSurface", "DesignTerrain"),
    )


def _is_analysis(child):
    return _is_type(child, proxy_types=("CutFillCalc",), name_prefixes=("CutFillCalc",))


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

    if _is_type(child, proxy_types=("HorizontalAlignment",), name_prefixes=("HorizontalAlignment",)) or _looks_like_horizontal_alignment(child):
        return aln_tree.get(ALIGNMENT_HORIZONTAL, None)
    if _is_type(child, proxy_types=("Stationing",), name_prefixes=("Stationing",)):
        return aln_tree.get(ALIGNMENT_STATIONING, None)
    if _is_type(child, proxy_types=("AssemblyTemplate",), name_prefixes=("AssemblyTemplate",)):
        return aln_tree.get(ALIGNMENT_ASSEMBLY, None)
    if _is_type(child, proxy_types=("SectionSet", "SectionSlice"), name_prefixes=("SectionSet", "SectionSlice")):
        return aln_tree.get(ALIGNMENT_SECTIONS, None)
    if _is_type(child, proxy_types=("CorridorLoft",), name_prefixes=("CorridorLoft",)):
        return aln_tree.get(ALIGNMENT_CORRIDOR, None)
    return aln_tree.get(ALIGNMENT_VERTICAL, None)


def _resolve_target_container(prj, child, allow_references: bool = True):
    if prj is None or child is None:
        return None
    if child == prj:
        return None
    if _is_tree_folder(child):
        return prj

    tree = ensure_project_tree(prj, include_references=False)

    if _is_alignment_related(child):
        return _target_folder_for_alignment_child(prj, child)

    if _is_surface(child):
        return tree.get(TREE_SURFACES, None)

    if _is_analysis(child):
        return tree.get(TREE_ANALYSIS, None)

    if _is_probable_terrain_input(prj, child):
        return tree.get(TREE_INPUTS_TERRAINS, None)

    if allow_references:
        tree = ensure_project_tree(prj, include_references=True)
        return tree.get(TREE_REFERENCES, None)
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
        "SectionSet",
        "CorridorLoft",
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
        if _is_alignment_related(ch) or _is_surface(ch) or _is_analysis(ch) or _is_probable_terrain_input(prj, ch):
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
        "SectionSet",
        "CorridorLoft",
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
    if not hasattr(obj, "LengthScale"):
        obj.addProperty("App::PropertyFloat", "LengthScale", "CorridorRoad", "Length scale (internal units per meter)")
        obj.LengthScale = 1.0
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

    _ensure_hidden_link_property(obj, "Terrain", "CorridorRoad", "Link to EG terrain object")
    _ensure_hidden_link_property(obj, "Alignment", "CorridorRoad", "Link to horizontal alignment object")
    _ensure_hidden_link_property(obj, "Stationing", "CorridorRoad", "Link to stationing object")
    _ensure_hidden_link_property(obj, "Centerline3D", "CorridorRoad", "Link to 3D centerline object")
    _ensure_hidden_link_property(obj, "Centerline3DDisplay", "CorridorRoad", "Link to 3D centerline display object")
    _ensure_hidden_link_property(obj, "AssemblyTemplate", "CorridorRoad", "Link to assembly template object")
    _ensure_hidden_link_property(obj, "SectionSet", "CorridorRoad", "Link to section set object")
    _ensure_hidden_link_property(obj, "CorridorLoft", "CorridorRoad", "Link to corridor loft object")
    _ensure_hidden_link_property(obj, "DesignGradingSurface", "CorridorRoad", "Link to design grading surface object")
    _ensure_hidden_link_property(obj, "DesignTerrain", "CorridorRoad", "Link to design terrain object")
    _ensure_hidden_link_property(obj, "CutFillCalc", "CorridorRoad", "Link to cut/fill calc object")
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
    def auto_link(doc, obj_project):
        """Try to auto-detect first alignment/stationing/profile and link them."""
        if doc is None:
            return

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

        if hasattr(obj_project, "CorridorLoft") and obj_project.CorridorLoft is None:
            c = None
            for o in doc.Objects:
                if getattr(o, "Proxy", None) and getattr(o.Proxy, "Type", "") == "CorridorLoft":
                    c = o
                    break
                if o.Name.startswith("CorridorLoft"):
                    c = o
                    break
            if c is not None:
                obj_project.CorridorLoft = c

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
