# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import math

try:
    import Part
except Exception:
    Part = None


def _safe_text(value) -> str:
    return str(value or "").strip()


def _safe_float(value, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return float(default)
    if not math.isfinite(out):
        return float(default)
    return float(out)


def _safe_enabled(value, default: bool = True) -> bool:
    text = _safe_text(value).lower()
    if text in ("", "1", "true", "yes", "on", "enabled"):
        return bool(default) if text == "" else True
    if text in ("0", "false", "no", "off", "disabled"):
        return False
    return bool(default)


def _empty_shape():
    if Part is None:
        return None
    try:
        return Part.Shape()
    except Exception:
        return None


def edit_plan_row(kind: str = "cross_section_edit", **fields) -> str:
    parts = [str(kind or "cross_section_edit").strip()]
    for key, value in fields.items():
        parts.append(f"{str(key or '').strip()}={value}")
    return "|".join(parts)


def parse_edit_plan_row(text: str):
    raw = _safe_text(text)
    if not raw:
        return {}
    parts = [part.strip() for part in raw.split("|")]
    out = {"kind": parts[0] if parts else "cross_section_edit", "raw": raw}
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        out[_safe_text(key)] = _safe_text(value)
    return out


def _record_count(obj) -> int:
    lengths = []
    for prop in (
        "EditIds",
        "Scopes",
        "StartStations",
        "EndStations",
        "TargetIds",
        "Parameters",
        "Values",
    ):
        try:
            lengths.append(len(list(getattr(obj, prop, []) or [])))
        except Exception:
            pass
    return max(lengths) if lengths else 0


def ensure_cross_section_edit_plan_properties(obj):
    if not hasattr(obj, "EditIds"):
        obj.addProperty("App::PropertyStringList", "EditIds", "CrossSectionEditPlan", "Stable edit ids")
        obj.EditIds = []
    if not hasattr(obj, "EnabledFlags"):
        obj.addProperty("App::PropertyStringList", "EnabledFlags", "CrossSectionEditPlan", "Enabled flags stored as true/false text")
        obj.EnabledFlags = []
    if not hasattr(obj, "Scopes"):
        obj.addProperty("App::PropertyStringList", "Scopes", "CrossSectionEditPlan", "Edit scopes: station or range")
        obj.Scopes = []
    if not hasattr(obj, "StartStations"):
        obj.addProperty("App::PropertyFloatList", "StartStations", "CrossSectionEditPlan", "Override start stations")
        obj.StartStations = []
    if not hasattr(obj, "EndStations"):
        obj.addProperty("App::PropertyFloatList", "EndStations", "CrossSectionEditPlan", "Override end stations")
        obj.EndStations = []
    if not hasattr(obj, "TransitionIns"):
        obj.addProperty("App::PropertyFloatList", "TransitionIns", "CrossSectionEditPlan", "Transition-in distances")
        obj.TransitionIns = []
    if not hasattr(obj, "TransitionOuts"):
        obj.addProperty("App::PropertyFloatList", "TransitionOuts", "CrossSectionEditPlan", "Transition-out distances")
        obj.TransitionOuts = []
    if not hasattr(obj, "TargetIds"):
        obj.addProperty("App::PropertyStringList", "TargetIds", "CrossSectionEditPlan", "Target component ids")
        obj.TargetIds = []
    if not hasattr(obj, "TargetSides"):
        obj.addProperty("App::PropertyStringList", "TargetSides", "CrossSectionEditPlan", "Target component sides")
        obj.TargetSides = []
    if not hasattr(obj, "TargetTypes"):
        obj.addProperty("App::PropertyStringList", "TargetTypes", "CrossSectionEditPlan", "Target component types")
        obj.TargetTypes = []
    if not hasattr(obj, "Parameters"):
        obj.addProperty("App::PropertyStringList", "Parameters", "CrossSectionEditPlan", "Edited parameter names")
        obj.Parameters = []
    if not hasattr(obj, "Values"):
        obj.addProperty("App::PropertyFloatList", "Values", "CrossSectionEditPlan", "Edited numeric values")
        obj.Values = []
    if not hasattr(obj, "Units"):
        obj.addProperty("App::PropertyStringList", "Units", "CrossSectionEditPlan", "Edited value units")
        obj.Units = []
    if not hasattr(obj, "SourceScopes"):
        obj.addProperty("App::PropertyStringList", "SourceScopes", "CrossSectionEditPlan", "Original component scopes")
        obj.SourceScopes = []
    if not hasattr(obj, "Notes"):
        obj.addProperty("App::PropertyStringList", "Notes", "CrossSectionEditPlan", "Edit notes")
        obj.Notes = []
    if not hasattr(obj, "EditRows"):
        obj.addProperty("App::PropertyStringList", "EditRows", "Result", "Structured CrossSectionEditPlan rows")
        obj.EditRows = []
    if not hasattr(obj, "ValidationRows"):
        obj.addProperty("App::PropertyStringList", "ValidationRows", "Result", "Validation result rows")
        obj.ValidationRows = []
    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"


class CrossSectionEditPlan:
    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "CrossSectionEditPlan"
        self._suspend_recompute = False
        ensure_cross_section_edit_plan_properties(obj)

    @staticmethod
    def records(obj):
        ensure_cross_section_edit_plan_properties(obj)
        out = []
        count = _record_count(obj)
        for index in range(count):
            start = float((obj.StartStations or [])[index]) if index < len(list(getattr(obj, "StartStations", []) or [])) else 0.0
            end = float((obj.EndStations or [])[index]) if index < len(list(getattr(obj, "EndStations", []) or [])) else start
            if end < start:
                start, end = end, start
            out.append(
                {
                    "Index": index,
                    "Id": _safe_text((obj.EditIds or [])[index]) if index < len(list(getattr(obj, "EditIds", []) or [])) else f"EDIT_{index + 1:03d}",
                    "Enabled": _safe_enabled((obj.EnabledFlags or [])[index], default=True) if index < len(list(getattr(obj, "EnabledFlags", []) or [])) else True,
                    "Scope": _safe_text((obj.Scopes or [])[index]).lower() if index < len(list(getattr(obj, "Scopes", []) or [])) else "range",
                    "StartStation": start,
                    "EndStation": end,
                    "TransitionIn": max(0.0, _safe_float((obj.TransitionIns or [])[index], 0.0)) if index < len(list(getattr(obj, "TransitionIns", []) or [])) else 0.0,
                    "TransitionOut": max(0.0, _safe_float((obj.TransitionOuts or [])[index], 0.0)) if index < len(list(getattr(obj, "TransitionOuts", []) or [])) else 0.0,
                    "TargetId": _safe_text((obj.TargetIds or [])[index]) if index < len(list(getattr(obj, "TargetIds", []) or [])) else "",
                    "TargetSide": _safe_text((obj.TargetSides or [])[index]).lower() if index < len(list(getattr(obj, "TargetSides", []) or [])) else "",
                    "TargetType": _safe_text((obj.TargetTypes or [])[index]).lower() if index < len(list(getattr(obj, "TargetTypes", []) or [])) else "",
                    "Parameter": _safe_text((obj.Parameters or [])[index]).lower() if index < len(list(getattr(obj, "Parameters", []) or [])) else "",
                    "Value": _safe_float((obj.Values or [])[index], 0.0) if index < len(list(getattr(obj, "Values", []) or [])) else 0.0,
                    "Unit": _safe_text((obj.Units or [])[index]) if index < len(list(getattr(obj, "Units", []) or [])) else "",
                    "SourceScope": _safe_text((obj.SourceScopes or [])[index]).lower() if index < len(list(getattr(obj, "SourceScopes", []) or [])) else "",
                    "Notes": _safe_text((obj.Notes or [])[index]) if index < len(list(getattr(obj, "Notes", []) or [])) else "",
                }
            )
        return out

    @staticmethod
    def apply_records(obj, records):
        ensure_cross_section_edit_plan_properties(obj)
        rows = [dict(rec or {}) for rec in list(records or [])]
        obj.EditIds = [_safe_text(row.get("Id", "")) for row in rows]
        obj.EnabledFlags = ["true" if _safe_enabled(row.get("Enabled", True), default=True) else "false" for row in rows]
        obj.Scopes = [_safe_text(row.get("Scope", "range")).lower() for row in rows]
        obj.StartStations = [float(_safe_float(row.get("StartStation", 0.0), 0.0)) for row in rows]
        obj.EndStations = [float(_safe_float(row.get("EndStation", row.get("StartStation", 0.0)), 0.0)) for row in rows]
        obj.TransitionIns = [max(0.0, _safe_float(row.get("TransitionIn", 0.0), 0.0)) for row in rows]
        obj.TransitionOuts = [max(0.0, _safe_float(row.get("TransitionOut", 0.0), 0.0)) for row in rows]
        obj.TargetIds = [_safe_text(row.get("TargetId", "")) for row in rows]
        obj.TargetSides = [_safe_text(row.get("TargetSide", "")).lower() for row in rows]
        obj.TargetTypes = [_safe_text(row.get("TargetType", "")).lower() for row in rows]
        obj.Parameters = [_safe_text(row.get("Parameter", "")).lower() for row in rows]
        obj.Values = [float(_safe_float(row.get("Value", 0.0), 0.0)) for row in rows]
        obj.Units = [_safe_text(row.get("Unit", "")) for row in rows]
        obj.SourceScopes = [_safe_text(row.get("SourceScope", "")).lower() for row in rows]
        obj.Notes = [_safe_text(row.get("Notes", "")) for row in rows]
        obj.EditRows = [CrossSectionEditPlan.serialize_record(row) for row in CrossSectionEditPlan.records(obj)]
        return rows

    @staticmethod
    def serialize_record(record):
        row = dict(record or {})
        return edit_plan_row(
            "cross_section_edit",
            id=_safe_text(row.get("Id", "")),
            enabled=1 if _safe_enabled(row.get("Enabled", True), default=True) else 0,
            scope=_safe_text(row.get("Scope", "range")).lower(),
            start=f"{_safe_float(row.get('StartStation', 0.0), 0.0):.3f}",
            end=f"{_safe_float(row.get('EndStation', row.get('StartStation', 0.0)), 0.0):.3f}",
            transitionIn=f"{max(0.0, _safe_float(row.get('TransitionIn', 0.0), 0.0)):.3f}",
            transitionOut=f"{max(0.0, _safe_float(row.get('TransitionOut', 0.0), 0.0)):.3f}",
            targetId=_safe_text(row.get("TargetId", "")),
            targetSide=_safe_text(row.get("TargetSide", "")).lower(),
            targetType=_safe_text(row.get("TargetType", "")).lower(),
            parameter=_safe_text(row.get("Parameter", "")).lower(),
            value=f"{_safe_float(row.get('Value', 0.0), 0.0):.6f}",
            unit=_safe_text(row.get("Unit", "")),
            sourceScope=_safe_text(row.get("SourceScope", "")).lower(),
        )

    @staticmethod
    def validate_records(records):
        issues = []
        seen = set()
        for rec in list(records or []):
            rid = _safe_text(rec.get("Id", ""))
            label = rid or f"row_{int(rec.get('Index', 0) or 0) + 1}"
            if not rid:
                issues.append(f"{label}: missing edit id")
            if rid in seen:
                issues.append(f"{label}: duplicate edit id")
            seen.add(rid)
            scope = _safe_text(rec.get("Scope", "")).lower()
            if scope not in ("station", "range"):
                issues.append(f"{label}: scope must be station or range")
            if _safe_text(rec.get("Parameter", "")) == "":
                issues.append(f"{label}: missing parameter")
            if _safe_text(rec.get("TargetId", "")) == "":
                issues.append(f"{label}: missing target id")
            start = _safe_float(rec.get("StartStation", 0.0), 0.0)
            end = _safe_float(rec.get("EndStation", start), start)
            if end < start:
                issues.append(f"{label}: end station is before start station")
            if scope == "station" and abs(end - start) > 1e-6:
                issues.append(f"{label}: station scope must have matching start/end station")
        return issues

    @staticmethod
    def active_records_at_station(obj, station: float, tol: float = 1e-6):
        station = float(station)
        out = []
        for rec in CrossSectionEditPlan.records(obj):
            if not bool(rec.get("Enabled", True)):
                continue
            start = float(rec.get("StartStation", 0.0) or 0.0)
            end = float(rec.get("EndStation", start) or start)
            if (start - tol) <= station <= (end + tol):
                out.append(dict(rec))
        return out

    @staticmethod
    def boundary_station_values(obj):
        values = []
        for rec in CrossSectionEditPlan.records(obj):
            if not bool(rec.get("Enabled", True)):
                continue
            start = float(rec.get("StartStation", 0.0) or 0.0)
            end = float(rec.get("EndStation", start) or start)
            tin = max(0.0, float(rec.get("TransitionIn", 0.0) or 0.0))
            tout = max(0.0, float(rec.get("TransitionOut", 0.0) or 0.0))
            values.extend([start, end])
            if tin > 1e-9:
                values.append(start - tin)
            if tout > 1e-9:
                values.append(end + tout)
        out = []
        for value in sorted(values):
            if not any(abs(float(value) - float(existing)) <= 1e-6 for existing in out):
                out.append(float(value))
        return out

    def execute(self, obj):
        ensure_cross_section_edit_plan_properties(obj)
        records = CrossSectionEditPlan.records(obj)
        rows = [CrossSectionEditPlan.serialize_record(rec) for rec in records]
        obj.EditRows = list(rows)
        issues = CrossSectionEditPlan.validate_records(records)
        obj.ValidationRows = list(issues)
        enabled = sum(1 for rec in records if bool(rec.get("Enabled", True)))
        boundary_count = len(CrossSectionEditPlan.boundary_station_values(obj))
        obj.Status = f"{'WARN' if issues else 'OK'} | edits={enabled}/{len(records)} | boundaries={boundary_count} | issues={len(issues)}"
        try:
            shp = _empty_shape()
            if shp is not None:
                obj.Shape = shp
        except Exception:
            pass

    def onChanged(self, obj, prop):
        if bool(getattr(self, "_suspend_recompute", False)):
            return
        if prop in (
            "EditIds",
            "EnabledFlags",
            "Scopes",
            "StartStations",
            "EndStations",
            "TransitionIns",
            "TransitionOuts",
            "TargetIds",
            "TargetSides",
            "TargetTypes",
            "Parameters",
            "Values",
            "Units",
            "SourceScopes",
            "Notes",
        ):
            try:
                obj.touch()
            except Exception:
                pass


class ViewProviderCrossSectionEditPlan:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        return

    def updateData(self, obj, prop):
        return

    def getDisplayModes(self, vobj):
        return []

    def getDefaultDisplayMode(self):
        return "Flat Lines"

    def setDisplayMode(self, mode):
        return mode
