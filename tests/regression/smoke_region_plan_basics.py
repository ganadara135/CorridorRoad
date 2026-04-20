# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
RegionPlan basics smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_plan_basics.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_region_plan import RegionPlan


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    doc = App.newDocument("CRRegionPlanBasics")

    reg = doc.addObject("Part::FeaturePython", "RegionPlan")
    RegionPlan(reg)
    RegionPlan.apply_records(
        reg,
        [
            {"Id": "BASE_A", "RegionType": "roadway", "Layer": "base", "StartStation": 0.0, "EndStation": 40.0, "Priority": 0, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "", "SidePolicy": "", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "", "HintSource": "", "HintStatus": "", "HintReason": ""},
            {"Id": "BASE_B", "RegionType": "bridge_approach", "Layer": "base", "StartStation": 40.0, "EndStation": 80.0, "Priority": 0, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "", "SidePolicy": "", "DaylightPolicy": "", "CorridorPolicy": "", "Enabled": True, "Notes": "", "HintSource": "", "HintStatus": "", "HintReason": ""},
            {"Id": "OVR_1", "RegionType": "ditch_override", "Layer": "overlay", "StartStation": 30.0, "EndStation": 50.0, "Priority": 10, "TransitionIn": 5.0, "TransitionOut": 2.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "", "SidePolicy": "", "DaylightPolicy": "", "CorridorPolicy": "skip_zone", "Enabled": True, "Notes": "", "HintSource": "structure", "HintStatus": "accepted", "HintReason": "Linked structure span should skip loft generation.", "HintConfidence": 0.95},
            {"Id": "HINT_A", "RegionType": "retaining_wall_zone", "Layer": "overlay", "StartStation": 60.0, "EndStation": 70.0, "Priority": 20, "TransitionIn": 0.0, "TransitionOut": 0.0, "TemplateName": "", "AssemblyName": "", "RuleSet": "", "SidePolicy": "", "DaylightPolicy": "right:off", "CorridorPolicy": "", "Enabled": False, "Notes": "", "HintSource": "typical", "HintStatus": "pending", "HintReason": "Detected urban edge roadside pattern on the right side.", "HintConfidence": 0.9},
        ],
    )

    doc.recompute()

    issues = list(RegionPlan.validate(reg) or [])
    _assert(not issues, f"Unexpected validation issues: {issues}")

    items = list(RegionPlan.region_key_station_items(reg, include_boundaries=True, include_transitions=True) or [])
    key_stations = sorted({round(float(row.get("station", 0.0) or 0.0), 3) for row in items})
    _assert(key_stations == [0.0, 25.0, 30.0, 40.0, 50.0, 52.0, 80.0], f"Unexpected key stations: {key_stations}")

    ctx_35 = RegionPlan.resolve_station_context(reg, 35.0)
    _assert(str(ctx_35.get("BaseRegionId", "") or "") == "BASE_A", "35.0 base region mismatch")
    _assert(list(ctx_35.get("OverlayRegionIds", []) or []) == ["OVR_1"], "35.0 overlay region mismatch")

    ctx_40 = RegionPlan.resolve_station_context(reg, 40.0)
    _assert(str(ctx_40.get("BaseRegionId", "") or "") == "BASE_B", "40.0 boundary should resolve to the next base region")
    _assert({"start", "end"}.issubset(set(list(ctx_40.get("BoundaryRoles", []) or []))), "40.0 should report both start and end boundary roles")

    effective_35 = RegionPlan.resolve_effective_rules_at_station(reg, 35.0)
    _assert(str(effective_35.get("ResolvedCorridorPolicy", "") or "") == "skip_zone", "Overlay corridor policy should win at 35.0")
    records = list(RegionPlan.records(reg) or [])
    overlay_rec = next(rec for rec in records if str(rec.get("Id", "") or "") == "OVR_1")
    hint_rec = next(rec for rec in records if str(rec.get("Id", "") or "") == "HINT_A")
    _assert(str(overlay_rec.get("HintSource", "") or "") == "structure", "Hint source should round-trip from RegionPlan")
    _assert(str(overlay_rec.get("HintStatus", "") or "") == "accepted", "Hint status should round-trip from RegionPlan")
    _assert("skip loft" in str(overlay_rec.get("HintReason", "") or "").lower(), "Hint reason should round-trip from RegionPlan")
    _assert(abs(float(overlay_rec.get("HintConfidence", 0.0) or 0.0) - 0.95) < 1e-6, "Hint confidence should round-trip from RegionPlan")
    _assert(str(hint_rec.get("HintStatus", "") or "") == "pending", "Pending hint status should round-trip from RegionPlan")
    _assert(abs(float(hint_rec.get("HintConfidence", 0.0) or 0.0) - 0.9) < 1e-6, "Pending hint confidence should round-trip from RegionPlan")
    grouped = dict(RegionPlan.grouped_records(reg) or {})
    _assert(list(grouped.get("BaseIds", []) or []) == ["BASE_A", "BASE_B"], "Grouped base ids mismatch")
    _assert(list(grouped.get("OverrideIds", []) or []) == ["OVR_1"], "Grouped override ids mismatch")
    _assert(list(grouped.get("OverrideActions", []) or []) == ["skip_corridor"], "Grouped override actions mismatch")
    _assert(list(grouped.get("HintIds", []) or []) == ["HINT_A"], "Grouped hint ids mismatch")
    _assert(list(grouped.get("HintSourceKinds", []) or []) == ["typical"], "Grouped hint source kinds mismatch")
    _assert(list(grouped.get("HintReviewStates", []) or []) == ["pending"], "Grouped hint review states mismatch")
    _assert(abs(float((grouped.get("HintConfidences", [0.0]) or [0.0])[0]) - 0.9) < 1e-6, "Grouped hint confidence mismatch")
    _assert(list(reg.BaseIds or []) == ["BASE_A", "BASE_B"], "Synced BaseIds property mismatch")
    _assert(list(reg.OverrideIds or []) == ["OVR_1"], "Synced OverrideIds property mismatch")
    _assert(list(reg.HintIds or []) == ["HINT_A"], "Synced HintIds property mismatch")
    grouped_rows = dict(RegionPlan.grouped_raw_records(reg) or {})
    _assert([row.get("Id", "") for row in list(grouped_rows.get("base_rows", []) or [])] == ["BASE_A", "BASE_B"], "Grouped raw base rows mismatch")
    _assert([row.get("Id", "") for row in list(grouped_rows.get("override_rows", []) or [])] == ["OVR_1"], "Grouped raw override rows mismatch")
    _assert([row.get("Id", "") for row in list(grouped_rows.get("hint_rows", []) or [])] == ["HINT_A"], "Grouped raw hint rows mismatch")
    exported_rows = list(RegionPlan.export_records_from_grouped(reg) or [])
    _assert([row.get("Id", "") for row in exported_rows] == ["BASE_A", "OVR_1", "BASE_B", "HINT_A"], "Grouped raw export order mismatch")

    reg_bad = doc.addObject("Part::FeaturePython", "RegionPlanInvalid")
    RegionPlan(reg_bad)
    reg_bad.RegionIds = ["BAD_A", "BAD_B", "BAD_C"]
    reg_bad.Layers = ["base", "base", "overlay"]
    reg_bad.StartStations = [0.0, 30.0, 60.0]
    reg_bad.EndStations = [40.0, 70.0, 60.0]
    reg_bad.TransitionIns = [0.0, -1.0, 0.0]
    reg_bad.TransitionOuts = [0.0, 0.0, 0.0]
    reg_bad.EnabledFlags = ["true", "true", "true"]
    bad_issues = "\n".join(list(RegionPlan.validate(reg_bad) or []))
    _assert("BAD_B: overlaps base region BAD_A" in bad_issues, "Expected base overlap issue")
    _assert("BAD_B: TransitionIn is negative" in bad_issues, "Expected negative transition issue")
    _assert("BAD_C: zero-length region span is not supported in Phase 1" in bad_issues, "Expected zero-length region issue")

    App.closeDocument(doc.Name)
    print("[PASS] RegionPlan basics smoke test completed.")


if __name__ == "__main__":
    run()
