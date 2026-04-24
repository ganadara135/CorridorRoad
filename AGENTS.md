# CorridorRoad Agent Guide

This file records repository-level operating rules for coding agents and automation helpers.

If any instruction here conflicts with a direct user request, the direct user request wins.
If any instruction here conflicts with higher-priority system or developer guidance, the higher-priority guidance wins.

## 1. Core Direction

- Treat CorridorRoad v1 as a product reset, not as a continuation of the legacy v0 architecture.
- Prefer the v1 source -> evaluation -> result -> output -> presentation layering.
- Do not reintroduce v0-style mixed ownership where UI, geometry, and source truth are blended together.
- Treat ramps, intersections, and drainage as first-class v1 domains, not as minor add-ons.

## 2. Authoritative Documents

- Use `docsV1/V1_MASTER_PLAN.md` as the baseline reference for v1 product direction.
- Treat `docsV1/` as the active redesign document set.
- Treat `docsV0/` as archived legacy reference only.
- When adding a new v1 design document, align it with the master plan or explicitly record a deviation.
- When adding a new document under `docsV1/`, update `docsV1/README.md` unless there is a strong reason not to.

## 3. V1 Architecture Rules

- Durable design intent belongs in source models, not in generated geometry.
- Generated section wires, viewer artifacts, and exported geometry are outputs, not edit sources.
- Keep corridor logic traceable back to source models.
- Use normalized output contracts for viewers, reports, and exchange flows.
- Do not hide engineering logic inside task panels, viewer widgets, or export commands.

## 4. Domain Expectations

- `AlignmentModel` owns horizontal geometry intent.
- `RampModel` owns ramp topology, merge/diverge, and tie-in intent.
- `IntersectionModel` owns at-grade junction control-area intent.
- `DrainageModel` owns drainage intent, low-point constraints, and collection/discharge context.
- `SectionModel` and `AppliedSection` must reflect ramp, intersection, drainage, terrain, and structure context when relevant.
- `CorridorModel` should be treated as a corridor-network orchestration layer, not a single-loft object.

## 5. Code Placement

- Prefer new v1 code under `freecad/Corridor_Road/v1/`.
- Use legacy `commands/`, `ui/`, and other v0 paths mainly for thin compatibility bridges unless the task clearly belongs to legacy behavior.
- Keep package boundaries visible:
  - `models/source`
  - `services/evaluation`
  - `models/result`
  - `models/output`
  - `ui/editors`
  - `ui/viewers`
  - `exchange`

## 6. Editing Rules

- Do not revert unrelated user changes.
- Do not use destructive git commands unless explicitly requested.
- Prefer minimal, architecture-consistent edits over quick hacks.
- When changing terminology or workflow structure, keep wording aligned with the active v1 stage model.
- If documentation and code both change, keep them in sync in the same task when practical.

## 7. Documentation Rules

- Use short, explicit statements.
- Prefer stable model names and subsystem names consistently across documents.
- For model documents, keep a consistent structure:
  - Purpose
  - Scope
  - Core Rule
  - Design Goals
  - Object Families
  - Root Fields
  - Relationships
  - Diagnostics
  - Non-goals
- For plan documents, keep implementation order and acceptance criteria explicit.

## 8. Viewer and Review Rules

- The Cross Section Viewer is a review and handoff surface, not a geometry editor.
- Review UI should expose source ownership, diagnostics, and context.
- Support same-context return after edit and rebuild when possible.
- Prefer read-only review surfaces over direct output editing.

## 9. Exchange and AI Rules

- Exchange logic should normalize into v1 contracts instead of inventing engineering meaning inside import/export code.
- AI outputs must stay explainable, reviewable, and approval-gated.
- Do not describe AI as silently rewriting accepted design state.

## 10. Testing Expectations

- The local FreeCAD command-line executable location is:
  - `D:\Program Files\FreeCAD 1.0\bin`
- When a task requires `FreeCADCmd.exe`, prefer this installed location first.
- For code changes, run focused validation when feasible.
- Prefer contract and service validation over UI-only manual checking.
- If tests cannot be run, say so clearly.
- For documentation-only changes, test execution is optional unless the change also affects executable examples or commands.

## 11. Preferred Change Workflow

Before making substantial changes:

- identify the active v1 source/result/output boundary involved
- check whether related docs need to be updated too
- avoid solving a v1 problem with a v0-shaped shortcut

When finishing work:

- summarize the actual architectural effect, not just the file list
- mention testing status
- call out any follow-up docs or code that should be aligned next
