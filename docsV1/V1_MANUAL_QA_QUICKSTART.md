# CorridorRoad V1 Manual QA Quickstart

Date: 2026-04-23
Branch: `v1-dev`
Status: Quick execution note
Depends on:

- `docsV1/V1_MAIN_REVIEW_COMMAND_MANUAL_RECORD.md`
- `docsV1/V1_REAL_DOCUMENT_VIEWER_CHECKLIST.md`
- `docsV1/V1_CROSS_SECTION_2D_MANUAL_QA.md`
- `docsV1/V1_VIEWER_ROUNDTRIP_MANUAL_QA.md`
- `scripts/launch_v1_manual_review.ps1`

## 1. Purpose

This is the fastest path to verify that the three main review commands now open the v1 viewers first.

Use it when you want a 5-minute manual check rather than the full roundtrip note.

## 2. Fast Launch

Recommended launcher:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\launch_v1_manual_review.ps1
```

If you already know the document to open:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\launch_v1_manual_review.ps1 -DocumentPath "C:\path\to\your\project.FCStd"
```

Dry-run check:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\launch_v1_manual_review.ps1 -DryRun
```

## 3. Five-Minute Flow

1. Open FreeCAD and load one real CorridorRoad project document.
2. Run `CorridorRoad_ViewCrossSection`.
3. Confirm the v1 `Cross Section Viewer` opens first.
   - if it says `Built from demo section viewer payload.`, count that as command routing success only, not as a real-document review pass
   - if checking section drawing quality, follow `V1_CROSS_SECTION_2D_MANUAL_QA.md`
4. Run `CorridorRoad_ReviewPlanProfile`.
5. Confirm the v1 `Plan/Profile Viewer` opens first.
6. Run `CorridorRoad_GenerateCutFillCalc`.
7. Confirm the v1 `Earthwork Viewer` opens first.
8. If any command falls back to an existing v0 screen, record that immediately.

## 4. Minimum Pass Conditions

- all three commands open successfully
- all three commands open a v1 viewer first
- no unexpected fallback happens
- focus station or row context still looks understandable
- at least the cross-section check is not limited to demo payload only if you are claiming a real-document pass

## 5. Where to Record

Write the result into:

- `docsV1/V1_MAIN_REVIEW_COMMAND_MANUAL_RECORD.md`
- `docsV1/V1_REAL_DOCUMENT_VIEWER_CHECKLIST.md`

Use the longer roundtrip note only if something looks wrong:

- `docsV1/V1_VIEWER_ROUNDTRIP_MANUAL_QA.md`

## 6. Final Rule

If any of the three main review commands does not open a v1 viewer first, do not mark the viewer-first transition as validated.
