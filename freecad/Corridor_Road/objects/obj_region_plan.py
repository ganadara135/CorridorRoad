# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import json
import math

import FreeCAD as App

try:
    import Part
except Exception:
    Part = None

from freecad.Corridor_Road.corridor_compat import CORRIDOR_PROXY_TYPE
from freecad.Corridor_Road.objects.doc_query import find_first, find_project
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment


ALLOWED_REGION_LAYERS = ("base", "overlay")
ALLOWED_CORRIDOR_POLICIES = ("", "none", "split_only", "skip_zone", "notch", "boolean_cut")
COMMON_REGION_TYPES = (
    "",
    "roadway",
    "widening",
    "bridge_approach",
    "ditch_override",
    "retaining_wall_zone",
    "earthwork_zone",
    "other",
)
_RECOMP_LABEL_SUFFIX = " [Recompute]"


def _safe_float(v, default: float = 0.0) -> float:
    try:
        x = float(v)
    except Exception:
        return float(default)
    if not math.isfinite(x):
        return float(default)
    return float(x)


def _safe_int(v, default: int = 0) -> int:
    try:
        return int(round(float(v)))
    except Exception:
        return int(default)


def _safe_text(v) -> str:
    return str(v or "").strip()


def _safe_enabled_flag(v, default: bool = True) -> bool:
    txt = _safe_text(v).lower()
    if txt in ("", "1", "true", "yes", "on", "enabled"):
        return True if txt != "" else bool(default)
    if txt in ("0", "false", "no", "off", "disabled"):
        return False
    return bool(default)


def _empty_shape():
    if Part is None:
        return None
    try:
        return Part.Shape()
    except Exception:
        return None


def _mark_dependency_needs_recompute(obj_dep, status_text: str):
    proxy_type = str(getattr(getattr(obj_dep, "Proxy", None), "Type", "") or "")
    hide_user_stale_state = proxy_type == CORRIDOR_PROXY_TYPE
    try:
        if hasattr(obj_dep, "NeedsRecompute"):
            obj_dep.NeedsRecompute = True
    except Exception:
        pass
    if not hide_user_stale_state:
        try:
            st = str(getattr(obj_dep, "Status", "") or "")
            if "NEEDS_RECOMPUTE" not in st:
                obj_dep.Status = str(status_text or "NEEDS_RECOMPUTE")
        except Exception:
            pass
        try:
            label = str(getattr(obj_dep, "Label", "") or "")
            if _RECOMP_LABEL_SUFFIX not in label:
                obj_dep.Label = f"{label}{_RECOMP_LABEL_SUFFIX}"
        except Exception:
            pass
    try:
        obj_dep.touch()
    except Exception:
        pass


def _resolve_alignment(obj):
    doc = getattr(obj, "Document", None)
    prj = find_project(doc)
    if prj is not None:
        aln = getattr(prj, "Alignment", None)
        if aln is not None:
            return aln
        st = getattr(prj, "Stationing", None)
        if st is not None:
            aln = getattr(st, "Alignment", None)
            if aln is not None:
                return aln
    return find_first(doc, proxy_type="HorizontalAlignment", name_prefixes=("HorizontalAlignment",))


def _resolve_station_point(obj, station: float, aln=None):
    if aln is None:
        aln = _resolve_alignment(obj)
    if aln is not None:
        try:
            return HorizontalAlignment.point_at_station(aln, float(station))
        except Exception:
            pass
    return App.Vector(float(station), 0.0, 0.0)


def _record_count(obj) -> int:
    names = (
        "RegionIds",
        "RegionTypes",
        "Layers",
        "StartStations",
        "EndStations",
        "Priorities",
        "TransitionIns",
        "TransitionOuts",
        "TemplateNames",
        "AssemblyNames",
        "RuleSets",
        "SidePolicies",
        "DaylightPolicies",
        "CorridorPolicies",
        "EnabledFlags",
        "Notes",
        "HintSources",
        "HintStatuses",
        "HintReasons",
        "HintConfidences",
    )
    count = 0
    for name in names:
        try:
            count = max(count, len(list(getattr(obj, name, []) or [])))
        except Exception:
            pass
    return int(count)


def _normalize_layer(v) -> str:
    txt = _safe_text(v).lower()
    return txt if txt in ALLOWED_REGION_LAYERS else ("base" if txt == "" else txt)


def _title_case_token(v) -> str:
    token = _safe_text(v).replace("_", " ")
    return " ".join(part[:1].upper() + part[1:] for part in token.split() if part)


def _normalized_station_span(rec):
    s0 = _safe_float(rec.get("StartStation", 0.0), default=0.0)
    s1 = _safe_float(rec.get("EndStation", 0.0), default=0.0)
    if s1 < s0:
        s0, s1 = s1, s0
    return float(s0), float(s1)


def _scope_from_record(rec) -> str:
    scopes = []
    for token in (
        _safe_text(rec.get("SidePolicy", "")),
        _safe_text(rec.get("DaylightPolicy", "")),
    ):
        head, _, _tail = token.partition(":")
        head = head.strip().lower()
        if head in ("left", "right", "both") and head not in scopes:
            scopes.append(head)
    if not scopes:
        return "both"
    if len(scopes) == 1:
        return scopes[0]
    return "mixed"


def _override_kind_from_record(rec) -> str:
    corridor_policy = _safe_text(rec.get("CorridorPolicy", "")).lower()
    side_policy = _safe_text(rec.get("SidePolicy", "")).lower()
    daylight_policy = _safe_text(rec.get("DaylightPolicy", "")).lower()
    region_type = _safe_text(rec.get("RegionType", "")).lower()
    if side_policy.endswith(":berm") or region_type == "ditch_override":
        return "ditch_berm"
    if daylight_policy.endswith(":off") or region_type == "retaining_wall_zone":
        return "urban_edge"
    if corridor_policy in ("split_only", "skip_zone"):
        return "corridor_zone"
    return region_type or "other"


def _override_action_from_record(rec) -> str:
    corridor_policy = _safe_text(rec.get("CorridorPolicy", "")).lower()
    if corridor_policy == "split_only":
        return "split_corridor"
    if corridor_policy == "skip_zone":
        return "skip_corridor"
    side_policy = _safe_text(rec.get("SidePolicy", ""))
    if side_policy:
        _head, _, tail = side_policy.partition(":")
        if tail.strip():
            return tail.strip().lower().replace(" ", "_")
    daylight_policy = _safe_text(rec.get("DaylightPolicy", ""))
    if daylight_policy:
        _head, _, tail = daylight_policy.partition(":")
        if tail.strip():
            return f"daylight_{tail.strip().lower().replace(' ', '_')}"
    return "none"


def _hint_source_kind_from_record(rec) -> str:
    explicit = _safe_text(rec.get("HintSource", "")).lower()
    if explicit:
        return explicit
    rule_set = _safe_text(rec.get("RuleSet", ""))
    head, _, _tail = rule_set.partition(":")
    return head.strip().lower() or "manual"


def _hint_status_from_record(rec) -> str:
    explicit = _safe_text(rec.get("HintStatus", "")).lower()
    if explicit:
        return explicit
    return "accepted" if bool(rec.get("Enabled", True)) else "pending"


def _grouped_payload_from_records(records):
    groups = _split_records_by_group(records)
    base_rows = list(groups.get("base_rows", []) or [])
    override_rows = list(groups.get("override_rows", []) or [])
    hint_rows = list(groups.get("hint_rows", []) or [])

    return {
        "BaseIds": [_safe_text(rec.get("Id", "")) for rec in base_rows],
        "BasePurposes": [_safe_text(rec.get("RegionType", "")) for rec in base_rows],
        "BaseStartStations": [_normalized_station_span(rec)[0] for rec in base_rows],
        "BaseEndStations": [_normalized_station_span(rec)[1] for rec in base_rows],
        "BaseTemplateRefs": [_safe_text(rec.get("TemplateName", "")) for rec in base_rows],
        "BaseAssemblyRefs": [_safe_text(rec.get("AssemblyName", "")) for rec in base_rows],
        "BaseNotes": [_safe_text(rec.get("Notes", "")) for rec in base_rows],
        "OverrideIds": [_safe_text(rec.get("Id", "")) for rec in override_rows],
        "OverrideKinds": [_override_kind_from_record(rec) for rec in override_rows],
        "OverrideScopes": [_scope_from_record(rec) for rec in override_rows],
        "OverrideStartStations": [_normalized_station_span(rec)[0] for rec in override_rows],
        "OverrideEndStations": [_normalized_station_span(rec)[1] for rec in override_rows],
        "OverrideActions": [_override_action_from_record(rec) for rec in override_rows],
        "OverrideTransitionIns": [max(0.0, _safe_float(rec.get("TransitionIn", 0.0), default=0.0)) for rec in override_rows],
        "OverrideTransitionOuts": [max(0.0, _safe_float(rec.get("TransitionOut", 0.0), default=0.0)) for rec in override_rows],
        "OverrideNotes": [_safe_text(rec.get("Notes", "")) for rec in override_rows],
        "HintIds": [_safe_text(rec.get("Id", "")) for rec in hint_rows],
        "HintSourceKinds": [_hint_source_kind_from_record(rec) for rec in hint_rows],
        "HintKinds": [_safe_text(rec.get("RegionType", "")) or "other" for rec in hint_rows],
        "HintScopes": [_scope_from_record(rec) for rec in hint_rows],
        "HintStartStations": [_normalized_station_span(rec)[0] for rec in hint_rows],
        "HintEndStations": [_normalized_station_span(rec)[1] for rec in hint_rows],
        "HintReviewStates": [_hint_status_from_record(rec) for rec in hint_rows],
        "HintReasonTexts": [_safe_text(rec.get("HintReason", "")) or _safe_text(rec.get("Notes", "")) for rec in hint_rows],
        "HintConfidences": [
            max(0.0, min(1.0, _safe_float(rec.get("HintConfidence", 0.0), default=(1.0 if _hint_source_kind_from_record(rec) in ("typical", "structure") else 0.5))))
            for rec in hint_rows
        ],
    }


def _split_records_by_group(records):
    base_rows = []
    override_rows = []
    hint_rows = []
    for rec in list(records or []):
        layer = _normalize_layer(rec.get("Layer", "base"))
        enabled = bool(rec.get("Enabled", True))
        if not enabled:
            hint_rows.append(dict(rec))
        elif layer == "base":
            base_rows.append(dict(rec))
        else:
            override_rows.append(dict(rec))

    def _sorted(rows):
        return sorted(
            list(rows or []),
            key=lambda rec: (
                _safe_float(rec.get("StartStation", 0.0), default=0.0),
                _safe_float(rec.get("EndStation", 0.0), default=0.0),
                _safe_text(rec.get("Id", "")),
            ),
        )

    return {
        "base_rows": _sorted(base_rows),
        "override_rows": _sorted(override_rows),
        "hint_rows": _sorted(hint_rows),
    }


def _rows_from_grouped_json(text):
    raw = _safe_text(text)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    rows = []
    for item in data:
        if isinstance(item, dict):
            rows.append(dict(item))
    return rows


def _region_source_matches(section_obj, region_obj) -> bool:
    try:
        from freecad.Corridor_Road.objects.obj_section_set import region_plan_usage_enabled

        if not bool(region_plan_usage_enabled(section_obj)):
            return False
    except Exception:
        return False
    try:
        from freecad.Corridor_Road.objects.obj_section_set import resolve_region_plan_source

        return resolve_region_plan_source(section_obj) == region_obj
    except Exception:
        pass
    try:
        if getattr(section_obj, "RegionPlan", None) == region_obj:
            return True
    except Exception:
        pass
    try:
        from freecad.Corridor_Road.objects.obj_project import resolve_project_region_plan

        prj_region = resolve_project_region_plan(getattr(section_obj, "Document", None))
        if prj_region == region_obj:
            return True
    except Exception:
        pass
    return False


def _mark_dependents_from_region_plan(region_obj):
    doc = getattr(region_obj, "Document", None)
    if doc is None:
        return

    dependent_sections = []
    for o in list(getattr(doc, "Objects", []) or []):
        try:
            proxy_type = str(getattr(getattr(o, "Proxy", None), "Type", "") or "")
            if proxy_type != "SectionSet":
                continue
            if not _region_source_matches(o, region_obj):
                continue
            _mark_dependency_needs_recompute(o, "NEEDS_RECOMPUTE: Source Region Plan changed.")
            dependent_sections.append(o)
        except Exception:
            continue

    for sec in dependent_sections:
        for o in list(getattr(doc, "Objects", []) or []):
            try:
                proxy_type = str(getattr(getattr(o, "Proxy", None), "Type", "") or "")
                if getattr(o, "SourceSectionSet", None) == sec:
                    if proxy_type == CORRIDOR_PROXY_TYPE:
                        _mark_dependency_needs_recompute(o, "NEEDS_RECOMPUTE: Source SectionSet changed.")
                    elif proxy_type == "DesignGradingSurface":
                        _mark_dependency_needs_recompute(o, "NEEDS_RECOMPUTE: Source SectionSet changed.")
            except Exception:
                continue


def ensure_region_plan_properties(obj):
    if not hasattr(obj, "RegionIds"):
        obj.addProperty("App::PropertyStringList", "RegionIds", "Regions", "Region identifiers")
        obj.RegionIds = []
    if not hasattr(obj, "RegionTypes"):
        obj.addProperty("App::PropertyStringList", "RegionTypes", "Regions", "Region type names")
        obj.RegionTypes = []
    if not hasattr(obj, "Layers"):
        obj.addProperty("App::PropertyStringList", "Layers", "Regions", "Region layer values")
        obj.Layers = []
    if not hasattr(obj, "StartStations"):
        obj.addProperty("App::PropertyFloatList", "StartStations", "Regions", "Region start stations")
        obj.StartStations = []
    if not hasattr(obj, "EndStations"):
        obj.addProperty("App::PropertyFloatList", "EndStations", "Regions", "Region end stations")
        obj.EndStations = []
    if not hasattr(obj, "Priorities"):
        obj.addProperty("App::PropertyIntegerList", "Priorities", "Regions", "Region priorities")
        obj.Priorities = []
    if not hasattr(obj, "TransitionIns"):
        obj.addProperty("App::PropertyFloatList", "TransitionIns", "Regions", "Transition-in distance before start")
        obj.TransitionIns = []
    if not hasattr(obj, "TransitionOuts"):
        obj.addProperty("App::PropertyFloatList", "TransitionOuts", "Regions", "Transition-out distance after end")
        obj.TransitionOuts = []
    if not hasattr(obj, "TemplateNames"):
        obj.addProperty("App::PropertyStringList", "TemplateNames", "Regions", "Template names owned by regions")
        obj.TemplateNames = []
    if not hasattr(obj, "AssemblyNames"):
        obj.addProperty("App::PropertyStringList", "AssemblyNames", "Regions", "Assembly names owned by regions")
        obj.AssemblyNames = []
    if not hasattr(obj, "RuleSets"):
        obj.addProperty("App::PropertyStringList", "RuleSets", "Regions", "Logical region rule-set names")
        obj.RuleSets = []
    if not hasattr(obj, "SidePolicies"):
        obj.addProperty("App::PropertyStringList", "SidePolicies", "Regions", "Side policy tokens")
        obj.SidePolicies = []
    if not hasattr(obj, "DaylightPolicies"):
        obj.addProperty("App::PropertyStringList", "DaylightPolicies", "Regions", "Daylight policy tokens")
        obj.DaylightPolicies = []
    if not hasattr(obj, "CorridorPolicies"):
        obj.addProperty("App::PropertyStringList", "CorridorPolicies", "Regions", "Corridor policy tokens")
        obj.CorridorPolicies = []
    if not hasattr(obj, "EnabledFlags"):
        obj.addProperty("App::PropertyStringList", "EnabledFlags", "Regions", "Enabled flags stored as true/false text")
        obj.EnabledFlags = []
    if not hasattr(obj, "Notes"):
        obj.addProperty("App::PropertyStringList", "Notes", "Regions", "Region notes")
        obj.Notes = []
    if not hasattr(obj, "HintSources"):
        obj.addProperty("App::PropertyStringList", "HintSources", "Regions", "Hint source labels")
        obj.HintSources = []
    if not hasattr(obj, "HintStatuses"):
        obj.addProperty("App::PropertyStringList", "HintStatuses", "Regions", "Hint status values")
        obj.HintStatuses = []
    if not hasattr(obj, "HintReasons"):
        obj.addProperty("App::PropertyStringList", "HintReasons", "Regions", "Hint reason text")
        obj.HintReasons = []
    if not hasattr(obj, "BaseIds"):
        obj.addProperty("App::PropertyStringList", "BaseIds", "PlanGroups", "Base region ids")
        obj.BaseIds = []
    if not hasattr(obj, "BasePurposes"):
        obj.addProperty("App::PropertyStringList", "BasePurposes", "PlanGroups", "Base region purposes")
        obj.BasePurposes = []
    if not hasattr(obj, "BaseStartStations"):
        obj.addProperty("App::PropertyFloatList", "BaseStartStations", "PlanGroups", "Base region start stations")
        obj.BaseStartStations = []
    if not hasattr(obj, "BaseEndStations"):
        obj.addProperty("App::PropertyFloatList", "BaseEndStations", "PlanGroups", "Base region end stations")
        obj.BaseEndStations = []
    if not hasattr(obj, "BaseTemplateRefs"):
        obj.addProperty("App::PropertyStringList", "BaseTemplateRefs", "PlanGroups", "Base template references")
        obj.BaseTemplateRefs = []
    if not hasattr(obj, "BaseAssemblyRefs"):
        obj.addProperty("App::PropertyStringList", "BaseAssemblyRefs", "PlanGroups", "Base assembly references")
        obj.BaseAssemblyRefs = []
    if not hasattr(obj, "BaseNotes"):
        obj.addProperty("App::PropertyStringList", "BaseNotes", "PlanGroups", "Base region notes")
        obj.BaseNotes = []
    if not hasattr(obj, "OverrideIds"):
        obj.addProperty("App::PropertyStringList", "OverrideIds", "PlanGroups", "Override ids")
        obj.OverrideIds = []
    if not hasattr(obj, "OverrideKinds"):
        obj.addProperty("App::PropertyStringList", "OverrideKinds", "PlanGroups", "Override kinds")
        obj.OverrideKinds = []
    if not hasattr(obj, "OverrideScopes"):
        obj.addProperty("App::PropertyStringList", "OverrideScopes", "PlanGroups", "Override scopes")
        obj.OverrideScopes = []
    if not hasattr(obj, "OverrideStartStations"):
        obj.addProperty("App::PropertyFloatList", "OverrideStartStations", "PlanGroups", "Override start stations")
        obj.OverrideStartStations = []
    if not hasattr(obj, "OverrideEndStations"):
        obj.addProperty("App::PropertyFloatList", "OverrideEndStations", "PlanGroups", "Override end stations")
        obj.OverrideEndStations = []
    if not hasattr(obj, "OverrideActions"):
        obj.addProperty("App::PropertyStringList", "OverrideActions", "PlanGroups", "Override actions")
        obj.OverrideActions = []
    if not hasattr(obj, "OverrideTransitionIns"):
        obj.addProperty("App::PropertyFloatList", "OverrideTransitionIns", "PlanGroups", "Override transition-in distances")
        obj.OverrideTransitionIns = []
    if not hasattr(obj, "OverrideTransitionOuts"):
        obj.addProperty("App::PropertyFloatList", "OverrideTransitionOuts", "PlanGroups", "Override transition-out distances")
        obj.OverrideTransitionOuts = []
    if not hasattr(obj, "OverrideNotes"):
        obj.addProperty("App::PropertyStringList", "OverrideNotes", "PlanGroups", "Override notes")
        obj.OverrideNotes = []
    if not hasattr(obj, "HintIds"):
        obj.addProperty("App::PropertyStringList", "HintIds", "PlanGroups", "Hint ids")
        obj.HintIds = []
    if not hasattr(obj, "HintSourceKinds"):
        obj.addProperty("App::PropertyStringList", "HintSourceKinds", "PlanGroups", "Hint source kinds")
        obj.HintSourceKinds = []
    if not hasattr(obj, "HintKinds"):
        obj.addProperty("App::PropertyStringList", "HintKinds", "PlanGroups", "Hint kinds")
        obj.HintKinds = []
    if not hasattr(obj, "HintScopes"):
        obj.addProperty("App::PropertyStringList", "HintScopes", "PlanGroups", "Hint scopes")
        obj.HintScopes = []
    if not hasattr(obj, "HintStartStations"):
        obj.addProperty("App::PropertyFloatList", "HintStartStations", "PlanGroups", "Hint start stations")
        obj.HintStartStations = []
    if not hasattr(obj, "HintEndStations"):
        obj.addProperty("App::PropertyFloatList", "HintEndStations", "PlanGroups", "Hint end stations")
        obj.HintEndStations = []
    if not hasattr(obj, "HintReviewStates"):
        obj.addProperty("App::PropertyStringList", "HintReviewStates", "PlanGroups", "Hint review states")
        obj.HintReviewStates = []
    if not hasattr(obj, "HintReasonTexts"):
        obj.addProperty("App::PropertyStringList", "HintReasonTexts", "PlanGroups", "Hint reason text mirrors")
        obj.HintReasonTexts = []
    if not hasattr(obj, "HintConfidences"):
        obj.addProperty("App::PropertyFloatList", "HintConfidences", "PlanGroups", "Hint confidence values")
        obj.HintConfidences = []
    if not hasattr(obj, "BaseRowsJson"):
        obj.addProperty("App::PropertyString", "BaseRowsJson", "PlanGroups", "Base group raw rows as JSON")
        obj.BaseRowsJson = "[]"
    if not hasattr(obj, "OverrideRowsJson"):
        obj.addProperty("App::PropertyString", "OverrideRowsJson", "PlanGroups", "Override group raw rows as JSON")
        obj.OverrideRowsJson = "[]"
    if not hasattr(obj, "HintRowsJson"):
        obj.addProperty("App::PropertyString", "HintRowsJson", "PlanGroups", "Hint group raw rows as JSON")
        obj.HintRowsJson = "[]"
    if not hasattr(obj, "ValidationRows"):
        obj.addProperty("App::PropertyStringList", "ValidationRows", "Result", "Region validation rows")
        obj.ValidationRows = []
    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Region Plan status")
        obj.Status = "Idle"


class RegionPlan:
    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "RegionPlan"
        self._suspend_recompute = False
        ensure_region_plan_properties(obj)

    @staticmethod
    def records(obj):
        ensure_region_plan_properties(obj)
        count = _record_count(obj)
        out = []
        for i in range(count):
            rid = ""
            if i < len(list(getattr(obj, "RegionIds", []) or [])):
                rid = _safe_text((obj.RegionIds or [])[i])
            layer = "base"
            if i < len(list(getattr(obj, "Layers", []) or [])):
                layer = _normalize_layer((obj.Layers or [])[i])
            rec = {
                "Index": i,
                "Id": rid or f"REG_{i + 1:03d}",
                "RegionType": _safe_text((obj.RegionTypes or [])[i]) if i < len(list(getattr(obj, "RegionTypes", []) or [])) else "",
                "Layer": layer,
                "StartStation": float((obj.StartStations or [])[i]) if i < len(list(getattr(obj, "StartStations", []) or [])) else 0.0,
                "EndStation": float((obj.EndStations or [])[i]) if i < len(list(getattr(obj, "EndStations", []) or [])) else 0.0,
                "Priority": _safe_int((obj.Priorities or [])[i], default=0) if i < len(list(getattr(obj, "Priorities", []) or [])) else 0,
                "TransitionIn": float((obj.TransitionIns or [])[i]) if i < len(list(getattr(obj, "TransitionIns", []) or [])) else 0.0,
                "TransitionOut": float((obj.TransitionOuts or [])[i]) if i < len(list(getattr(obj, "TransitionOuts", []) or [])) else 0.0,
                "TemplateName": _safe_text((obj.TemplateNames or [])[i]) if i < len(list(getattr(obj, "TemplateNames", []) or [])) else "",
                "AssemblyName": _safe_text((obj.AssemblyNames or [])[i]) if i < len(list(getattr(obj, "AssemblyNames", []) or [])) else "",
                "RuleSet": _safe_text((obj.RuleSets or [])[i]) if i < len(list(getattr(obj, "RuleSets", []) or [])) else "",
                "SidePolicy": _safe_text((obj.SidePolicies or [])[i]) if i < len(list(getattr(obj, "SidePolicies", []) or [])) else "",
                "DaylightPolicy": _safe_text((obj.DaylightPolicies or [])[i]) if i < len(list(getattr(obj, "DaylightPolicies", []) or [])) else "",
                "CorridorPolicy": _safe_text((obj.CorridorPolicies or [])[i]) if i < len(list(getattr(obj, "CorridorPolicies", []) or [])) else "",
                "Enabled": _safe_enabled_flag((obj.EnabledFlags or [])[i], default=True) if i < len(list(getattr(obj, "EnabledFlags", []) or [])) else True,
                "Notes": _safe_text((obj.Notes or [])[i]) if i < len(list(getattr(obj, "Notes", []) or [])) else "",
                "HintSource": _safe_text((obj.HintSources or [])[i]) if i < len(list(getattr(obj, "HintSources", []) or [])) else "",
                "HintStatus": _safe_text((obj.HintStatuses or [])[i]) if i < len(list(getattr(obj, "HintStatuses", []) or [])) else "",
                "HintReason": _safe_text((obj.HintReasons or [])[i]) if i < len(list(getattr(obj, "HintReasons", []) or [])) else "",
                "HintConfidence": float((obj.HintConfidences or [])[i]) if i < len(list(getattr(obj, "HintConfidences", []) or [])) else 0.0,
            }
            out.append(rec)
        return out

    @staticmethod
    def grouped_records(obj):
        ensure_region_plan_properties(obj)
        return _grouped_payload_from_records(RegionPlan.records(obj))

    @staticmethod
    def grouped_raw_records(obj):
        ensure_region_plan_properties(obj)
        return {
            "base_rows": _rows_from_grouped_json(getattr(obj, "BaseRowsJson", "[]")),
            "override_rows": _rows_from_grouped_json(getattr(obj, "OverrideRowsJson", "[]")),
            "hint_rows": _rows_from_grouped_json(getattr(obj, "HintRowsJson", "[]")),
        }

    @staticmethod
    def export_records_from_grouped(obj):
        ensure_region_plan_properties(obj)
        groups = RegionPlan.grouped_raw_records(obj)
        rows = list(groups.get("base_rows", []) or []) + list(groups.get("override_rows", []) or []) + list(groups.get("hint_rows", []) or [])
        if rows:
            rows.sort(
                key=lambda rec: (
                    _safe_float(rec.get("StartStation", 0.0), default=0.0),
                    _safe_float(rec.get("EndStation", 0.0), default=0.0),
                    _safe_text(rec.get("Id", "")),
                )
            )
        return rows

    @staticmethod
    def apply_records(obj, records):
        ensure_region_plan_properties(obj)
        rows = [dict(rec) for rec in list(records or [])]
        obj.RegionIds = [_safe_text(row.get("Id", "")) for row in rows]
        obj.RegionTypes = [_safe_text(row.get("RegionType", "")) for row in rows]
        obj.Layers = [_normalize_layer(row.get("Layer", "base")) for row in rows]
        obj.StartStations = [_normalized_station_span(row)[0] for row in rows]
        obj.EndStations = [_normalized_station_span(row)[1] for row in rows]
        obj.Priorities = [_safe_int(row.get("Priority", 0), default=0) for row in rows]
        obj.TransitionIns = [max(0.0, _safe_float(row.get("TransitionIn", 0.0), default=0.0)) for row in rows]
        obj.TransitionOuts = [max(0.0, _safe_float(row.get("TransitionOut", 0.0), default=0.0)) for row in rows]
        obj.TemplateNames = [_safe_text(row.get("TemplateName", "")) for row in rows]
        obj.AssemblyNames = [_safe_text(row.get("AssemblyName", "")) for row in rows]
        obj.RuleSets = [_safe_text(row.get("RuleSet", "")) for row in rows]
        obj.SidePolicies = [_safe_text(row.get("SidePolicy", "")) for row in rows]
        obj.DaylightPolicies = [_safe_text(row.get("DaylightPolicy", "")) for row in rows]
        obj.CorridorPolicies = [_safe_text(row.get("CorridorPolicy", "")) for row in rows]
        obj.EnabledFlags = ["true" if _safe_enabled_flag(row.get("Enabled", True), default=True) else "false" for row in rows]
        obj.Notes = [_safe_text(row.get("Notes", "")) for row in rows]
        obj.HintSources = [_safe_text(row.get("HintSource", "")) for row in rows]
        obj.HintStatuses = [_safe_text(row.get("HintStatus", "")) for row in rows]
        obj.HintReasons = [_safe_text(row.get("HintReason", "")) for row in rows]
        obj.HintConfidences = [
            max(0.0, min(1.0, _safe_float(row.get("HintConfidence", 0.0), default=(1.0 if _hint_source_kind_from_record(row) in ("typical", "structure") else 0.5))))
            for row in rows
        ]
        RegionPlan.sync_grouped_properties(obj, records=rows)
        return rows

    @staticmethod
    def sync_grouped_properties(obj, records=None):
        ensure_region_plan_properties(obj)
        rows = [dict(rec) for rec in list(records if records is not None else RegionPlan.records(obj))]
        payload = _grouped_payload_from_records(rows)
        groups = _split_records_by_group(rows)
        for prop, values in payload.items():
            try:
                setattr(obj, prop, list(values or []))
            except Exception:
                continue
        try:
            obj.BaseRowsJson = json.dumps(list(groups.get("base_rows", []) or []), ensure_ascii=True)
            obj.OverrideRowsJson = json.dumps(list(groups.get("override_rows", []) or []), ensure_ascii=True)
            obj.HintRowsJson = json.dumps(list(groups.get("hint_rows", []) or []), ensure_ascii=True)
        except Exception:
            pass
        return payload

    @staticmethod
    def validate_records(records):
        issues = []
        seen_ids = set()
        base_rows = []
        for rec in list(records or []):
            rid = _safe_text(rec.get("Id", "") or f"REG_{int(rec.get('Index', 0)) + 1:03d}")
            layer = _normalize_layer(rec.get("Layer", "base"))
            region_type = _safe_text(rec.get("RegionType", ""))
            s0, s1 = _normalized_station_span(rec)
            tin = max(0.0, _safe_float(rec.get("TransitionIn", 0.0), default=0.0))
            tout = max(0.0, _safe_float(rec.get("TransitionOut", 0.0), default=0.0))
            priority = _safe_int(rec.get("Priority", 0), default=0)
            if rid in seen_ids:
                issues.append(f"{rid}: duplicate region id")
            seen_ids.add(rid)
            if layer not in ALLOWED_REGION_LAYERS:
                issues.append(f"{rid}: unknown layer '{layer}'")
            if _safe_float(rec.get("TransitionIn", 0.0), default=0.0) < -1e-9:
                issues.append(f"{rid}: TransitionIn is negative")
            if _safe_float(rec.get("TransitionOut", 0.0), default=0.0) < -1e-9:
                issues.append(f"{rid}: TransitionOut is negative")
            if abs(s1 - s0) <= 1e-9:
                issues.append(f"{rid}: zero-length region span is not supported in Phase 1")
            if _safe_text(rec.get("CorridorPolicy", "")).lower() not in ALLOWED_CORRIDOR_POLICIES:
                issues.append(f"{rid}: unknown corridor policy '{_safe_text(rec.get('CorridorPolicy', ''))}'")
            if layer == "base" and _safe_enabled_flag(rec.get("Enabled", True), default=True):
                base_rows.append((s0, s1, priority, rid, region_type, tin, tout))

        base_rows.sort(key=lambda row: (float(row[0]), float(row[1]), -int(row[2]), str(row[3])))
        prev = None
        for row in base_rows:
            if prev is None:
                prev = row
                continue
            if float(row[0]) < float(prev[1]) - 1e-9:
                issues.append(f"{row[3]}: overlaps base region {prev[3]}")
            if abs(float(row[0]) - float(prev[1])) > 1e-9 and float(row[0]) > float(prev[1]) + 1e-9:
                issues.append(f"{prev[3]} -> {row[3]}: uncovered base-region gap {float(prev[1]):.3f} to {float(row[0]):.3f}")
            if float(row[1]) > float(prev[1]):
                prev = row
        return issues

    @staticmethod
    def validate(obj):
        return RegionPlan.validate_records(RegionPlan.records(obj))

    @staticmethod
    def _membership_value(rec, station: float, tol: float = 1e-6) -> int:
        s0, s1 = _normalized_station_span(rec)
        ss = float(station)
        tt = max(1e-9, float(tol))
        if abs(s1 - s0) <= tt:
            return 1 if abs(ss - s0) <= tt else 0
        if ss >= s0 - tt and ss < s1 - tt:
            return 2
        if abs(ss - s0) <= tt:
            return 3
        if abs(ss - s1) <= tt:
            return 1
        return 0

    @staticmethod
    def active_records_at_station(obj, s: float, tol: float = 1e-6):
        active = []
        ending = []
        ss = float(s)
        for rec in RegionPlan.records(obj):
            if not bool(rec.get("Enabled", True)):
                continue
            membership = RegionPlan._membership_value(rec, ss, tol=tol)
            if membership >= 2:
                active.append(dict(rec))
            elif membership == 1:
                ending.append(dict(rec))
        return active if active else ending

    @staticmethod
    def _region_sort_key(rec):
        s0, s1 = _normalized_station_span(rec)
        span = max(0.0, float(s1 - s0))
        return (
            -_safe_int(rec.get("Priority", 0), default=0),
            -float(s0),
            float(span),
            _safe_text(rec.get("Id", "")),
        )

    @staticmethod
    def resolve_station_context(obj, station: float, tol: float = 1e-6):
        active = RegionPlan.active_records_at_station(obj, station, tol=tol)
        base = []
        overlays = []
        boundary_roles = []
        boundary_ids = []
        boundary_types = []
        for rec in RegionPlan.records(obj):
            if not bool(rec.get("Enabled", True)):
                continue
            rid = _safe_text(rec.get("Id", ""))
            region_type = _safe_text(rec.get("RegionType", ""))
            s0, s1 = _normalized_station_span(rec)
            tin = max(0.0, _safe_float(rec.get("TransitionIn", 0.0), default=0.0))
            tout = max(0.0, _safe_float(rec.get("TransitionOut", 0.0), default=0.0))
            ss = float(station)
            tt = max(1e-9, float(tol))
            if abs(ss - s0) <= tt:
                if "start" not in boundary_roles:
                    boundary_roles.append("start")
                if rid and rid not in boundary_ids:
                    boundary_ids.append(rid)
                if region_type and region_type not in boundary_types:
                    boundary_types.append(region_type)
            if abs(ss - s1) <= tt:
                if "end" not in boundary_roles:
                    boundary_roles.append("end")
                if rid and rid not in boundary_ids:
                    boundary_ids.append(rid)
                if region_type and region_type not in boundary_types:
                    boundary_types.append(region_type)
            if tin > tt and abs(ss - (s0 - tin)) <= tt:
                if "transition_in" not in boundary_roles:
                    boundary_roles.append("transition_in")
                if rid and rid not in boundary_ids:
                    boundary_ids.append(rid)
                if region_type and region_type not in boundary_types:
                    boundary_types.append(region_type)
            if tout > tt and abs(ss - (s1 + tout)) <= tt:
                if "transition_out" not in boundary_roles:
                    boundary_roles.append("transition_out")
                if rid and rid not in boundary_ids:
                    boundary_ids.append(rid)
                if region_type and region_type not in boundary_types:
                    boundary_types.append(region_type)

        for rec in list(active or []):
            if _normalize_layer(rec.get("Layer", "base")) == "overlay":
                overlays.append(dict(rec))
            else:
                base.append(dict(rec))
        base.sort(key=RegionPlan._region_sort_key)
        overlays.sort(key=RegionPlan._region_sort_key)
        base_rec = dict(base[0]) if base else None
        overlay_ids = [_safe_text(rec.get("Id", "")) for rec in overlays if _safe_text(rec.get("Id", ""))]
        overlay_types = [_safe_text(rec.get("RegionType", "")) for rec in overlays if _safe_text(rec.get("RegionType", ""))]
        return {
            "HasRegion": bool(base_rec is not None or overlays or boundary_roles),
            "BaseRegion": base_rec,
            "BaseRegionId": _safe_text(base_rec.get("Id", "")) if base_rec else "",
            "BaseRegionType": _safe_text(base_rec.get("RegionType", "")) if base_rec else "",
            "OverlayRegions": overlays,
            "OverlayRegionIds": overlay_ids,
            "OverlayRegionTypes": overlay_types,
            "BoundaryRoles": boundary_roles,
            "BoundaryRegionIds": boundary_ids,
            "BoundaryRegionTypes": boundary_types,
            "ActiveRecords": list(base) + list(overlays),
        }

    @staticmethod
    def resolve_effective_rules_at_station(obj, station: float, tol: float = 1e-6):
        ctx = RegionPlan.resolve_station_context(obj, station, tol=tol)
        base = dict(ctx.get("BaseRegion") or {})
        overlays = list(ctx.get("OverlayRegions", []) or [])
        resolved = {
            "BaseRegionId": str(ctx.get("BaseRegionId", "") or ""),
            "OverlayRegionIds": list(ctx.get("OverlayRegionIds", []) or []),
            "ResolvedTemplate": _safe_text(base.get("TemplateName", "")),
            "ResolvedAssembly": _safe_text(base.get("AssemblyName", "")),
            "ResolvedRuleSet": _safe_text(base.get("RuleSet", "")),
            "ResolvedSidePolicy": _safe_text(base.get("SidePolicy", "")),
            "ResolvedDaylightPolicy": _safe_text(base.get("DaylightPolicy", "")),
            "ResolvedCorridorPolicy": _safe_text(base.get("CorridorPolicy", "")),
            "ResolvedWarnings": [],
        }
        owners = {
            "ResolvedTemplate": str(ctx.get("BaseRegionId", "") or ""),
            "ResolvedAssembly": str(ctx.get("BaseRegionId", "") or ""),
            "ResolvedRuleSet": str(ctx.get("BaseRegionId", "") or ""),
            "ResolvedSidePolicy": str(ctx.get("BaseRegionId", "") or ""),
            "ResolvedDaylightPolicy": str(ctx.get("BaseRegionId", "") or ""),
            "ResolvedCorridorPolicy": str(ctx.get("BaseRegionId", "") or ""),
        }
        field_map = {
            "TemplateName": "ResolvedTemplate",
            "AssemblyName": "ResolvedAssembly",
            "RuleSet": "ResolvedRuleSet",
            "SidePolicy": "ResolvedSidePolicy",
            "DaylightPolicy": "ResolvedDaylightPolicy",
            "CorridorPolicy": "ResolvedCorridorPolicy",
        }
        for rec in overlays:
            rid = _safe_text(rec.get("Id", ""))
            for src_field, out_field in field_map.items():
                value = _safe_text(rec.get(src_field, ""))
                if not value:
                    continue
                prev_owner = str(owners.get(out_field, "") or "")
                if resolved.get(out_field) and prev_owner and prev_owner != rid:
                    resolved["ResolvedWarnings"].append(f"{rid}: overrides {out_field} owned by {prev_owner}")
                resolved[out_field] = value
                owners[out_field] = rid
        return resolved

    @staticmethod
    def region_key_station_items(obj, include_boundaries: bool = True, include_transitions: bool = True):
        items = []
        for rec in RegionPlan.records(obj):
            if not bool(rec.get("Enabled", True)):
                continue
            rid = _safe_text(rec.get("Id", "") or f"REG_{int(rec.get('Index', 0)) + 1:03d}")
            region_type = _safe_text(rec.get("RegionType", ""))
            layer = _normalize_layer(rec.get("Layer", "base"))
            s0, s1 = _normalized_station_span(rec)
            tin = max(0.0, _safe_float(rec.get("TransitionIn", 0.0), default=0.0))
            tout = max(0.0, _safe_float(rec.get("TransitionOut", 0.0), default=0.0))

            def _add(station, tag="", role=""):
                items.append(
                    {
                        "station": float(station),
                        "tag": str(tag or ""),
                        "role": str(role or ""),
                        "ids": [rid],
                        "types": [region_type] if region_type else [],
                        "layers": [layer] if layer else [],
                    }
                )

            if include_boundaries:
                _add(s0, "REG_START", "start")
                if abs(s1 - s0) > 1e-9:
                    _add(s1, "REG_END", "end")
            if include_transitions:
                if tin > 1e-9:
                    _add(s0 - tin, "REG_TRANSITION", "transition_in")
                if tout > 1e-9:
                    _add(s1 + tout, "REG_TRANSITION", "transition_out")
        return items

    @staticmethod
    def build_display_shape(obj):
        if Part is None:
            return _empty_shape()
        recs = [rec for rec in RegionPlan.records(obj) if bool(rec.get("Enabled", True))]
        if not recs:
            return _empty_shape()
        aln = _resolve_alignment(obj)
        lines = []
        for rec in recs:
            s0, s1 = _normalized_station_span(rec)
            p0 = _resolve_station_point(obj, s0, aln=aln)
            p1 = _resolve_station_point(obj, s1, aln=aln)
            if _normalize_layer(rec.get("Layer", "base")) == "overlay":
                p0 = App.Vector(p0.x, p0.y, p0.z + 0.15)
                p1 = App.Vector(p1.x, p1.y, p1.z + 0.15)
            try:
                if abs((p1.sub(p0)).Length) <= 1e-9:
                    p1 = App.Vector(p0.x + 0.1, p0.y, p0.z)
                lines.append(Part.makeLine(p0, p1))
            except Exception:
                continue
        if not lines:
            return _empty_shape()
        try:
            return Part.Compound(lines)
        except Exception:
            return _empty_shape()

    def execute(self, obj):
        ensure_region_plan_properties(obj)
        recs_all = list(RegionPlan.records(obj) or [])
        self._suspend_recompute = True
        try:
            RegionPlan.sync_grouped_properties(obj, records=recs_all)
        finally:
            self._suspend_recompute = False
        issues = list(RegionPlan.validate_records(recs_all) or [])
        obj.ValidationRows = list(issues)
        recs = [rec for rec in recs_all if bool(rec.get("Enabled", True))]
        base_count = sum(1 for rec in recs if _normalize_layer(rec.get("Layer", "base")) == "base")
        overlay_count = max(0, len(recs) - base_count)
        try:
            shp = RegionPlan.build_display_shape(obj)
            if shp is not None:
                obj.Shape = shp
        except Exception:
            try:
                obj.Shape = _empty_shape()
            except Exception:
                pass
        if issues:
            obj.Status = f"WARN | regions={len(recs)} | base={base_count} | overlay={overlay_count} | issues={len(issues)}"
        else:
            obj.Status = f"OK | regions={len(recs)} | base={base_count} | overlay={overlay_count}"

    def onChanged(self, obj, prop):
        ensure_region_plan_properties(obj)
        if bool(getattr(self, "_suspend_recompute", False)):
            return
        if prop in (
            "RegionIds",
            "RegionTypes",
            "Layers",
            "StartStations",
            "EndStations",
            "Priorities",
            "TransitionIns",
            "TransitionOuts",
            "TemplateNames",
            "AssemblyNames",
            "RuleSets",
            "SidePolicies",
            "DaylightPolicies",
            "CorridorPolicies",
            "EnabledFlags",
            "Notes",
            "HintSources",
            "HintStatuses",
            "HintReasons",
        ):
            self._suspend_recompute = True
            try:
                RegionPlan.sync_grouped_properties(obj)
            finally:
                self._suspend_recompute = False
            try:
                obj.touch()
            except Exception:
                pass
            _mark_dependents_from_region_plan(obj)


class ViewProviderRegionPlan:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Flat Lines"
            vobj.ShapeColor = (0.18, 0.58, 0.85)
            vobj.LineColor = (0.12, 0.40, 0.72)
            vobj.Transparency = 20
            vobj.LineWidth = 3
        except Exception:
            pass

    def getIcon(self):
        return ""

    def getDisplayModes(self, vobj):
        return ["Flat Lines", "Wireframe", "Shaded"]

    def getDefaultDisplayMode(self):
        return "Flat Lines"

    def setDisplayMode(self, mode):
        return str(mode)

    def updateData(self, obj, prop):
        return

    def onChanged(self, vobj, prop):
        return
