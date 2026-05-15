# Parametric Road V1 Centerline Ownership Consolidation Plan

Date: 2026-05-14
Status: Draft implementation plan
Scope: make the independent `3D Centerline` result the only baseline owner for downstream station/offset/elevation frame lookup

Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_3D_CENTERLINE_TOOLBAR_PLAN.md`
- `docsV1/V1_APPLIED_SECTIONS_PERFORMANCE_PLAN.md`
- `docsV1/V1_CORRIDOR_MODEL.md`
- `docsV1/V1_STRUCTURE_GEOMETRY_CONTRACT.md`
- `docsV1/V1_DRAINAGE_FLOW_ROUTE_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_WATERTIGHT_SOLID_IMPLEMENTATION_PLAN.md`

## 1. Purpose

The v1 workflow now has an independent `3D Centerline` toolbar stage.

That stage should own the evaluated station/offset/elevation baseline used by downstream tools.

Applied Sections should not act as a second centerline generator.

The goal is to reduce duplicate frame logic and make baseline review happen before section, structure, drainage, corridor, and solid outputs consume the frame.

## 2. Core Rule

`Centerline3DResult` is the authoritative generated baseline frame.

Applied Sections consume that baseline to place station-wise section results.

Applied Sections may persist each section's local placement frame, but that frame is a derived placement snapshot, not a separate 3D centerline source.

## 3. Terminology

| Term | Meaning |
|---|---|
| `Centerline3DResult` | Shared generated result from Alignment + Profile + Stationing. |
| `V1Centerline3DPreview` | Read-only review object for the shared 3D Centerline result. |
| `AppliedSection.frame` | Per-section placement snapshot derived from the shared baseline. |
| `applied_section_frame` | A fallback or diagnostic source name for existing section frames. |
| `centerline3d_result` | Preferred source name for shared baseline consumers. |

Avoid using `3d_centerline` as a vague source name in new code.

Use `centerline3d_result` when the shared result is used.

Use `applied_section_frame` only when a consumer intentionally falls back to persisted section frames.

## 4. Keep

Keep these parts:

- `Centerline3DResult`
- `V1Centerline3DPreview`
- `AppliedSection.frame`
- section point rows
- Applied Sections station-wise review and single-section preview
- Build Corridor result rows for centerline review

`AppliedSection.frame` is still required because each generated section needs a local origin, elevation, and orientation.

The ownership change is about where that frame comes from.

## 5. Remove Or Stop Treating As Source

Stop treating these as baseline owners:

- Applied Sections frames connected into a corridor centerline as the primary baseline
- Build Corridor centerline generation from Applied Sections as the default path
- Structures preview fallback to Applied Sections frames when the shared `Centerline3DResult` can be required
- vague `path_source=3d_centerline` values that do not identify the actual contract

Do not remove `AppliedSection.frame`.

Do not remove Applied Sections review geometry that shows section cross-section points.

## 6. Target Workflow

```text
Alignment
-> Stations
-> Profile
-> Review Plan/Profile
-> 3D Centerline
-> Assembly
-> Regions
-> Structures
-> Drainage
-> Applied Sections
-> Build Corridor
-> Watertight Solids
```

The important dependency is:

```text
Centerline3DResult
-> AppliedSection.frame
-> Corridor surfaces / Structure output / Watertight solids
```

## 7. Consumer Policy

| Consumer | Current behavior | Target behavior |
|---|---|---|
| Applied Sections | Builds section frames directly from Alignment + Profile + Stationing. | Build section frames from `Centerline3DResult` rows or a shared frame lookup service backed by that result. |
| Build Corridor | Prefers `Centerline3DResult`, falls back to Applied Sections frames. | Require or regenerate `Centerline3DResult`; keep Applied Sections fallback only during transition. |
| Structures preview | Prefers `Centerline3DResult`, falls back to Applied Sections frames and then Alignment. | Require or regenerate `Centerline3DResult`; retain Alignment fallback only for explicit minimal preview mode if needed. |
| Drainage pipeline preview | Prefers `Centerline3DResult`, falls back to Alignment station/offset. | Keep `Centerline3DResult` as preferred; later make missing baseline a visible validation warning before pipeline review. |
| Watertight Solids | Uses explicit `centerline3d_result` or `applied_section_frame` provenance where available. | Continue updating remaining solid families so path-source labels always identify the actual contract. |
| Cross Section Viewer | Reviews Applied Section result data. | Continue to review Applied Sections, but expose baseline provenance when useful. |

## 8. Required Shared Service

Introduce a shared frame lookup helper before removing fallbacks broadly.

Recommended service:

- `Centerline3DFrameService`

Responsibilities:

- build or receive a `Centerline3DResult`
- find exact station rows
- interpolate between centerline rows
- return `x`, `y`, `z`, tangent, normal, grade, and diagnostics
- report source mode as `centerline3d_result`

This prevents each command from keeping its own interpolation helper.

## 9. Validation Policy

Applied Sections validation should check:

- Alignment exists
- Profile exists
- Stationing exists
- `Centerline3DResult` can be evaluated
- every requested Applied Section station can be resolved against the centerline result
- Region boundary stations and transition stations are included or interpolatable

Missing `Centerline3DResult` should not silently create a second baseline.

During transition, tools may regenerate it on demand.

After transition, tools should show a clear message:

```text
Run 3D Centerline before Applied Sections.
```

## 10. Implementation Plan

| Step | Status | Work |
|---|---|---|
| 1 | Done | Record this consolidation plan and add it to `docsV1/README.md`. |
| 2 | Done | Add `Centerline3DFrameService` or equivalent shared lookup helper. |
| 3 | Done | Update Applied Sections build service to derive frames from the shared centerline lookup. |
| 4 | Done | Add Applied Sections validation for centerline coverage and diagnostics. |
| 5 | Done | Replace command-local interpolation helpers in Structures, Drainage, and Build Corridor with the shared service for shared `Centerline3DResult` paths. |
| 6 | Done | Rename ambiguous provenance values from `3d_centerline` to `centerline3d_result` or `applied_section_frame`. |
| 7 | Done | Remove Build Corridor Applied Sections centerline fallback after Applied Sections consumes the shared baseline. |
| 8 | Done | Update Watertight Solid path-source provenance and tests. |
| 9 | Done | Update Cross Section Viewer and output docs where they describe centerline ownership. |
| 10 | Partial | Run focused FreeCADCmd contract tests and manual 3D View QA. |

Step 8 result:

- `WatertightSolidOutputRow.path_source` is a persisted output field.
- FreeCAD watertight output objects store row-level `PathSources`.
- Road body and region solids from Applied Section profiles report `applied_section_frame`.
- Structure body solids pass through the Structure Solid `path_source`.
- Drainage pipeline and network solids report their resolved coordinate mode, including `centerline3d_result` when the shared 3D Centerline result is available.
- Watertight Solid build now reprojects Applied Section based closed solid profiles, including lined ditch bodies, onto the shared `centerline3d_result` frame before topology and Part shape creation.

Step 9 result:

- `V1_OUTPUT_STRATEGY.md` lists `Centerline3DResult` as a shared derived result source.
- `V1_SECTION_OUTPUT_SCHEMA.md` defines baseline provenance metadata for section outputs.
- `V1_CROSS_SECTION_VIEWER_EXECUTION_PLAN.md` states that the viewer reviews section payloads but does not own baseline generation.
- `V1_CROSS_SECTION_2D_VIEWER_DESIGN.md` routes stale or missing baseline context back to the `3D Centerline` stage.

Step 10 result:

- FreeCADCmd compile smoke passed for the 3D Centerline, Applied Sections, Build Corridor, Structures, Drainage, and Watertight Solids consolidation files.
- FreeCADCmd toolbar-order smoke confirmed `3D Centerline` is after `Review Plan/Profile` and before `Assembly`.
- FreeCADCmd Watertight Solid `PathSources` round-trip smoke passed for `centerline3d_result`.
- Focused pytest contract tests could not run in this environment because the installed FreeCADCmd Python does not have `pytest`.
- Manual 3D View QA remains to be performed inside the FreeCAD GUI.

## 11. Acceptance Criteria

- Applied Sections no longer own baseline centerline generation.
- Applied Sections still produce valid station-wise section frames.
- Build Corridor centerline review reports `source=centerline3d_result`.
- Structures and Drainage use the same frame lookup behavior.
- Watertight Solid provenance distinguishes `centerline3d_result` from `applied_section_frame`.
- Existing section review and single-section preview still work.

## 12. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Required section station is not in `Centerline3DResult` | Applied Sections fail or interpolate unexpectedly. | Add interpolation diagnostics and station coverage checks. |
| Removing fallbacks too early breaks existing tests or partial workflows. | Users cannot build corridor without manually running the new stage. | First regenerate shared result on demand, then tighten validation later. |
| `AppliedSection.frame` is mistaken for source ownership. | Future code may reintroduce duplicate baseline logic. | Document it as a derived placement snapshot. |
| Watertight Solid output path provenance changes. | Existing tests and UI text may fail. | Update tests and docs with explicit source names. |
| Command-local helper removal causes behavior drift. | Structures, Drainage, and Build Corridor may compute different offsets. | Centralize station/offset interpolation in one service. |

## 13. Decision

Proceed with consolidation.

Do not delete `AppliedSection.frame`.

Do remove the idea that Applied Sections generate or own the 3D baseline.

Use `Centerline3DResult` as the shared generated baseline result for downstream consumers.
