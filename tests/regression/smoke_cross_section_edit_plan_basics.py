# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
CrossSectionEditPlan persistence/link smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd -c "exec(open(r'tests\\regression\\smoke_cross_section_edit_plan_basics.py', encoding='utf-8').read())"
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_cross_section_edit_plan import CrossSectionEditPlan, parse_edit_plan_row
from freecad.Corridor_Road.objects.obj_section_set import SectionSet


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    doc = App.newDocument("CRCrossSectionEditPlanBasics")

    plan = doc.addObject("Part::FeaturePython", "CrossSectionEditPlan")
    CrossSectionEditPlan(plan)
    CrossSectionEditPlan.apply_records(
        plan,
        [
            {
                "Id": "EDIT_WIDTH_001",
                "Enabled": True,
                "Scope": "range",
                "StartStation": 10.0,
                "EndStation": 30.0,
                "TransitionIn": 2.5,
                "TransitionOut": 5.0,
                "TargetId": "L10",
                "TargetSide": "left",
                "TargetType": "side_slope",
                "Parameter": "width",
                "Value": 7.25,
                "Unit": "m",
                "SourceScope": "side_slope",
            }
        ],
    )
    doc.recompute()

    _assert(str(getattr(plan.Proxy, "Type", "") or "") == "CrossSectionEditPlan", "Proxy type mismatch")
    _assert(int(len(list(getattr(plan, "EditRows", []) or []))) == 1, "EditRows should contain one serialized row")
    parsed = parse_edit_plan_row(list(plan.EditRows)[0])
    _assert(str(parsed.get("id", "") or "") == "EDIT_WIDTH_001", "Serialized row id mismatch")
    _assert(str(parsed.get("parameter", "") or "") == "width", "Serialized row parameter mismatch")
    _assert(abs(float(parsed.get("value", 0.0) or 0.0) - 7.25) < 1e-9, "Serialized row value mismatch")

    active = CrossSectionEditPlan.active_records_at_station(plan, 20.0)
    _assert(len(active) == 1, "Active record lookup should find the range edit")
    inactive = CrossSectionEditPlan.active_records_at_station(plan, 40.0)
    _assert(len(inactive) == 0, "Active record lookup should skip stations outside the range")
    boundaries = CrossSectionEditPlan.boundary_station_values(plan)
    _assert([round(v, 3) for v in boundaries] == [7.5, 10.0, 30.0, 35.0], f"Boundary stations mismatch: {boundaries}")
    _assert(str(getattr(plan, "Status", "") or "").startswith("OK"), "Plan status should be OK")

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.CrossSectionEditPlan = plan
    sec.UseCrossSectionEditPlan = True
    doc.recompute()

    _assert(getattr(sec, "CrossSectionEditPlan", None) == plan, "SectionSet CrossSectionEditPlan link mismatch")
    _assert(bool(getattr(sec, "UseCrossSectionEditPlan", False)), "SectionSet UseCrossSectionEditPlan should be enabled")
    _assert(int(getattr(sec, "ResolvedCrossSectionEditCount", 0) or 0) == 1, "SectionSet edit count summary mismatch")
    summary = list(getattr(sec, "ResolvedCrossSectionEditSummaryRows", []) or [])
    _assert(any("edits=1" in row for row in summary), f"SectionSet edit summary mismatch: {summary}")

    App.closeDocument(doc.Name)
    print("[PASS] CrossSectionEditPlan persistence/link smoke test completed.")


if __name__ == "__main__":
    run()
