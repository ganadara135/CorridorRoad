# V1 Intersection Source/Result Audit Plan

Date: 2026-06-21
Status: In progress

Related process redesign:

- [V1_INTERSECTION_CREATION_PROCESS_REDESIGN_PLAN.md](./V1_INTERSECTION_CREATION_PROCESS_REDESIGN_PLAN.md)

Depends on:

- [V1_MASTER_PLAN.md](./V1_MASTER_PLAN.md)
- [V1_INTERSECTION_MODEL.md](./V1_INTERSECTION_MODEL.md)
- [V1_INTERSECTION_ENHANCEMENT_PLAN.md](./V1_INTERSECTION_ENHANCEMENT_PLAN.md)
- [V1_REGION_MODEL.md](./V1_REGION_MODEL.md)
- [V1_APPLIED_SECTION_SUPPLEMENTAL_SAMPLING_REDESIGN_PLAN.md](./V1_APPLIED_SECTION_SUPPLEMENTAL_SAMPLING_REDESIGN_PLAN.md)
- [V1_GENERAL_ROAD_PARAMETRIC_DESIGN_AUDIT_PLAN.md](./V1_GENERAL_ROAD_PARAMETRIC_DESIGN_AUDIT_PLAN.md)

## 1. Purpose

This document defines the source/result audit and improvement plan for v1 intersection design.

The goal is not to improve final solid geometry at this stage.

The goal is to make intersection design parametric enough that downstream geometry can be generated from durable source data and accepted result contracts.

## 2. Scope

Included:

- intersection source ownership
- control area source data
- participating road, Region, Alignment, Profile, Superelevation, Assembly, and Subassembly references
- curb return source data
- lane connection and edge mapping source data
- intersection grading policy source data
- drainage tie-in and low-point intent
- Applied Section supplemental rows generated for intersection control areas
- intersection result contracts consumed by Build Corridor and review surfaces
- diagnostics that explain missing or ambiguous source intent

Excluded for now:

- deep watertight solid geometry QA
- final boolean/fuse robustness
- detailed non-manifold or self-intersection repair
- automatic interchange synthesis without explicit source rules
- direct editing of generated surface or preview geometry

## 3. Core Rule

Intersection geometry must be generated from source intent and evaluated result contracts.

Generated preview wires, surfaces, patches, and solids are outputs.

They must not become the source of intersection design meaning.

## 4. Source/Result Boundary

Source owns:

- intersection id and type
- participating Alignment refs
- participating Region refs
- leg ids and approach/departure roles
- control area boundary intent
- curb return definitions
- lane connection rules
- edge-of-pavement, shoulder, sidewalk, ditch, and side-slope tie-in policies
- grading policy
- drainage low-point and flow-route context
- structure interaction refs where applicable

Evaluation owns:

- resolving station/offset/elevation frames on each participating Alignment
- detecting control boundary stations
- resolving curb return contact stations
- generating supplemental Applied Section station rows
- assigning source refs and diagnostic refs
- resolving precedence where Region, Intersection, Drainage, and Structure policies overlap

Result owns:

- intersection Applied Section rows
- junction surface patch contracts
- curb return result rows
- lane/edge connection result rows
- drainage tie-in result rows
- diagnostics and traceability rows

Output owns:

- review graphics
- surface meshes
- exported geometry
- optional future watertight solid targets

## 5. Status Dashboard

| Step | Status | Owner boundary | Output |
| --- | --- | --- | --- |
| 1. Baseline inventory | In progress | source/result/output | list current objects, commands, services, and tests |
| 2. Source contract audit | Pending | source | identify missing durable source fields |
| 3. Evaluation contract audit | Pending | evaluation | identify hidden geometry decisions and implicit sampling |
| 4. Result contract audit | Pending | result | define required result rows and diagnostics |
| 5. Consumer audit | Pending | result/output | check Applied Sections, Build Corridor, Drainage, Watertight handoff consumers |
| 6. UX and review audit | Pending | presentation | define user-visible status, source refs, and edit handoff |
| 7. Preset/sample data audit | Pending | source | ensure starter T/Cross/Y data is sufficient and parametric |
| 8. Implementation backlog | Pending | mixed | convert findings into ordered implementation tasks |
| 9. Validation plan | Pending | contracts/QA | define focused tests and manual QA checklist |

Status meanings:

- `Pending`: not started.
- `In progress`: actively being analyzed or implemented.
- `Blocked`: waiting on another subsystem or decision.
- `Done`: accepted for this audit stage.

## 6. Step 1 - Baseline Inventory

Status: In progress

Goal:

- identify current intersection source, result, output, command, service, preset, and test surfaces.

Tasks:

- inventory `IntersectionModel` source fields.
- inventory intersection command/task panel behavior.
- inventory intersection result/service builders.
- inventory Applied Sections intersection consumption.
- inventory Build Corridor intersection consumption.
- inventory drainage and structure references into or from intersections.
- inventory current tests and manual QA docs.

Acceptance:

- the audit has a named list of existing source/result/output artifacts.
- each artifact is classified as source, evaluation, result, output, or presentation.

## 7. Step 2 - Source Contract Audit

Status: Pending

Goal:

- determine whether current source data is enough to regenerate intersection geometry without reading generated output geometry as source intent.

Questions:

- Are control area boundaries represented as durable source intent?
- Are curb return definitions explicit enough to regenerate contact points and station ranges?
- Are lane connection rules explicit?
- Are edge roles clear for lane, shoulder, curb, sidewalk, ditch, side slope, and median?
- Are grading rules explicit enough for crown, sag, low point, and tie-in decisions?
- Are drainage low-point and flow-route references source-owned?
- Are Region refs explicit and stable?

Acceptance:

- missing source fields are listed.
- fields that already exist are marked as sufficient or insufficient.
- no output geometry is accepted as a substitute for missing source intent.

## 8. Step 3 - Evaluation Contract Audit

Status: Pending

Goal:

- identify where hidden runtime geometry decisions are made during intersection evaluation.

Questions:

- Where are supplemental intersection stations generated?
- Are station rows derived from Centerline3DResult or from profile/alignment fallback geometry?
- Are control boundary frames generated consistently for all participating Alignments?
- Are curb return contact stations carried as result rows?
- Are diagnostics emitted when sampling is missing, sparse, or ambiguous?

Acceptance:

- implicit evaluation decisions are listed.
- required diagnostics are identified.
- fallback behavior is visible to the user.

## 9. Step 4 - Result Contract Audit

Status: Pending

Goal:

- define the normalized intersection result contracts needed by downstream builders.

Required result families:

- intersection applied-section rows
- control boundary rows
- curb return rows
- lane connection rows
- edge tie-in rows
- junction grading rows
- drainage tie-in rows
- source lineage rows
- diagnostics

Acceptance:

- result rows can be consumed without re-reading generated preview geometry.
- each result row has source refs and diagnostic refs where relevant.

## 10. Step 5 - Consumer Audit

Status: Pending

Goal:

- verify that consumers use accepted result contracts instead of inferred output geometry.

Consumers:

- Applied Sections
- Build Corridor
- SurfaceModel generation
- Drainage review
- Structure interaction
- Watertight Solids readiness handoff
- exchange/export packages

Acceptance:

- consumer gaps are listed.
- any reverse-read or hidden fallback behavior is identified.
- deferred solid geometry work remains out of scope unless explicitly requested.

## 11. Step 6 - UX and Review Audit

Status: Pending

Goal:

- ensure users can understand intersection source ownership and result status.

Review surfaces should show:

- intersection id
- participating Alignment refs
- Region refs
- control area status
- curb return status
- lane connection status
- grading status
- drainage tie-in status
- missing source fields
- fallback usage
- edit handoff target

Acceptance:

- review UI requirements are listed.
- the user can identify what source needs editing when a result is wrong.

## 12. Step 7 - Preset and Sample Data Audit

Status: Pending

Goal:

- ensure starter intersection examples are not just visual samples, but complete parametric source examples.

Preset examples to review:

- T intersection
- Cross intersection
- Y intersection
- skewed intersection
- urban curb return intersection
- drainage-sensitive sag intersection

Acceptance:

- each sample has sufficient source fields to regenerate intended result contracts.
- missing sample data is listed as implementation backlog.

## 13. Step 8 - Implementation Backlog

Status: Pending

Goal:

- convert audit findings into implementation tasks.

Backlog format:

- task id
- status
- affected boundary
- source files
- expected behavior
- validation path
- manual QA path

Acceptance:

- implementation tasks are ordered so source contracts are stabilized before result/output consumers.

## 14. Step 9 - Validation Plan

Status: Pending

Goal:

- define focused automated tests and manual QA checks.

Validation should cover:

- source object roundtrip
- starter source completeness
- intersection supplemental Applied Section rows
- result source refs
- fallback diagnostics
- Build Corridor consumer traceability
- review status visibility

Acceptance:

- validation can run without depending on final watertight solid geometry quality.

## 15. Current Next Action

Next action:

- complete Step 1 baseline inventory and Phase 1 of the creation-process redesign.

Expected output:

- a table of current intersection source/result/output artifacts with boundary classification and notes.
