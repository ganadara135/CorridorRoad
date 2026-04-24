# CorridorRoad V1 Main Review Command Manual Record

Date: 2026-04-23
Branch: `v1-dev`
Status: Manual record template
Depends on:

- `docsV1/V1_VIEWER_ROUNDTRIP_MANUAL_QA.md`
- `docsV1/V1_REAL_DOCUMENT_VIEWER_CHECKLIST.md`
- `docsV1/V1_CROSS_SECTION_VIEWER_EXECUTION_PLAN.md`
- `docsV1/V1_PLAN_PROFILE_REVIEW_EXECUTION_PLAN.md`
- `docsV1/V1_EARTHWORK_REVIEW_EXECUTION_PLAN.md`

## 1. Purpose

This document is the short record sheet for checking whether the main review commands now open the v1 viewers first.

Use it after running the actual GUI checks in FreeCAD.

## 2. Environment

- FreeCAD GUI executable:
  - `D:\Program Files\FreeCAD 1.0\bin\FreeCAD.exe`
- FreeCAD command-line validation executable:
  - `D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe`

## 3. Test Document

- Document:
- Date:
- Tester:
- Notes:

## 4. Cross Section Main Review Command

Command:

- `CorridorRoad_ViewCrossSection`

Expected behavior:

- opens the v1 `Cross Section Viewer` first
- falls back to the existing v0 viewer only if the v1 path fails

Interpretation rule:

- if the viewer opens first but shows `Built from demo section viewer payload.`, record that as:
  - `Opened v1 first = pass`
  - `real-document data verification = not yet passed`
- `Open Typical Section` opening the existing v0 `Edit Typical Section` task panel is a valid handoff result

Record:

- Opened v1 first: pass / fail
- Fallback to existing v0 viewer happened: yes / no
- If fallback happened, was it expected: yes / no
- Station context looked correct: pass / fail
- Demo payload was shown: yes / no
- `Open Typical Section` handoff worked: pass / fail / not checked
- Notes:

## 5. Plan/Profile Main Review Command

Command:

- `CorridorRoad_ReviewPlanProfile`

Expected behavior:

- opens the v1 `Plan/Profile Viewer` first
- falls back to the existing v0 profile editor or alignment editor only if the v1 path fails

Record:

- Opened v1 first: pass / fail
- Fallback path used: none / v0 profile editor / v0 alignment editor
- If fallback happened, was it expected: yes / no
- Focus station or selected-row context looked correct: pass / fail
- Notes:

## 6. Earthwork Main Review Command

Command:

- `CorridorRoad_GenerateCutFillCalc`

Expected behavior:

- opens the v1 `Earthwork Viewer` first
- falls back to the existing v0 cut/fill panel only if the v1 path fails

Record:

- Opened v1 first: pass / fail
- Fallback to existing v0 panel happened: yes / no
- If fallback happened, was it expected: yes / no
- Focus station or focused window looked correct: pass / fail
- Notes:

## 7. Overall Result

- All three main review commands opened v1 first: pass / fail
- Any unexpected fallback occurred: yes / no
- Any major context mismatch occurred: yes / no
- Recommended next action:
  - keep current routing
  - fix one or more commands before wider rollout
  - re-run manual verification

## 8. Final Rule

Do not mark the viewer-first transition as validated until this record and the real-document checklist are both completed on at least one real project document.
