# Parametric Road Agent Guide

Last updated: 2026-06-20

This guide is the current development instruction set for the Parametric Road FreeCAD workbench.

The highest-priority product rule is that Parametric Road is a source-driven parametric road design system.

All road, corridor, intersection, drainage, ramp, structure, and output work must preserve the source -> evaluation -> result -> output -> presentation separation described below.

This file records repository-level operating rules for coding agents and automation helpers.

If any instruction here conflicts with a direct user request, the direct user request wins.
If any instruction here conflicts with higher-priority system or developer guidance, the higher-priority guidance wins.

## 0. Final Product Goal

Parametric Road's final product goal is Digital Twin road design.

The workbench should not stop at visual road modeling.

It should produce source-traceable road design data that can support:

- geometric design review
- corridor surface review
- drainage and structure coordination
- quantity and earthwork review
- watertight solid generation
- simulation handoff
- exchange/export workflows
- future Digital Twin operations and maintenance workflows

Watertight Solids are the first major gateway from design review into Digital Twin-ready output.

They convert accepted source-driven corridor results into closed, traceable, downstream-consumable solid bodies.

Watertight Solid work must preserve:

- source ownership
- Subassembly and surface-role traceability
- station and Region context
- material and quantity context
- diagnostic visibility
- repeatable rebuild behavior

Do not treat Watertight Solids as a decorative export feature.

They are a core Digital Twin entry point and must be designed as normalized output contracts that consume accepted result models.

## 1. Core Direction

- Treat CorridorRoad v1 as a product reset, not as a continuation of the legacy v0 architecture.
- Prefer the v1 source -> evaluation -> result -> output -> presentation layering.
- Do not reintroduce v0-style mixed ownership where UI, geometry, and source truth are blended together.
- Treat ramps, intersections, and drainage as first-class v1 domains, not as minor add-ons.
- Treat Watertight Solids as a first-class Digital Twin handoff domain, not as a final cosmetic mesh export.

## 2. Parametric Road Design Philosophy

Parametric Road must behave as a source-driven road design system.

The central rule is:

- user-authored source data defines design intent
- evaluation services resolve that intent into deterministic result contracts
- output builders consume result contracts
- preview and review surfaces display or diagnose results
- generated geometry must not become the source of design truth

Do not make road geometry by guessing from meshes, preview objects, tree objects, or previously generated output when a source contract should exist.

Do not silently repair missing source intent with visual cleanup geometry.

Fallbacks are allowed only when they are:

- explicit
- diagnostic
- traceable to the missing source condition
- not written back as accepted source intent

If a feature cannot be generated from available source data, prefer adding or correcting source data over adding downstream patch logic.

## 3. Source and Consumer Responsibility Rules

Each subsystem must clearly separate what it owns as source and what it may consume.

### Alignment

- Source: `AlignmentModel` owns horizontal geometry intent, curve definitions, station geometry, and alignment identity.
- Consumes: no generated corridor surface should be used to redefine Alignment.
- Outputs: evaluated alignment points, curve preview data, and source-geometry centerline paths are results or review aids.

### Profile

- Source: `ProfileModel` owns vertical geometry intent, PVI rows, vertical curve rows, grades, and elevation constraints.
- Consumes: Alignment station context only.
- Outputs: evaluated elevation rows and profile previews are results or review aids.

### 3D Centerline

- Source: Alignment and Profile are the source truth.
- Consumes: Alignment/Profile evaluation results.
- Outputs: `Centerline3DResult`, source-geometry preview, B-spline display, and polyline display are evaluated results or presentation modes.
- Rule: downstream geometry should prefer source-geometry centerline results. B-spline and polyline display modes must not become independent design intent.

### SubAssembly Designer

- Source: `SubassemblyLibrary` and `SubassemblyDefinition` own reusable point, link, shape, parameter, target, and surface-role behavior.
- Consumes: optional Assembly row context when editing a placed instance.
- Outputs: Designer preview is temporary review only.
- Rule: saving is required before a Designer edit becomes source data.

### Assembly / Subassembly

- Source: Assembly templates and placed `TemplateSubassembly` rows own placement, side, order, row-local overrides, target refs, and definition refs.
- Consumes: reusable Subassembly definitions.
- Outputs: Section Preview is review only.
- Rule: Applied Sections should evaluate placed Assembly/Subassembly rows; Build Corridor should not re-evaluate Assembly intent directly.

### Region

- Source: `RegionModel` owns station spans, active Assembly assignment, and region-level source refs.
- Consumes: Alignment/Stationing context and optional domain refs.
- Outputs: region review tables and boundary highlights are presentation only.
- Rule: Regions may reference intersections, ramps, structures, and drainage, but do not own those domain meanings.

### Superelevation

- Source: `SuperelevationModel` owns crossfall control rows, transition rules, and lane/shoulder crossfall intent.
- Consumes: Alignment station context.
- Outputs: effective crossfall samples are evaluation results.
- Rule: Build Corridor consumes crossfall only after Applied Sections have stored the effective section result.

### Applied Sections

- Source: none. Applied Sections are generated results.
- Consumes: Alignment, Profile, 3D Centerline, Region, Assembly/Subassembly, Superelevation, Terrain, Structure, Drainage, Ramp, and Intersection source/evaluation context.
- Outputs: station-based evaluated point, link, shape, surface-role, quantity, and diagnostic rows.
- Rule: supplemental Applied Sections are result-only sampling rows. They must not become editable source stations.

### Build Corridor / Build Parametric

- Source: none for road design intent. Build Corridor may own output/display options and transition output settings where explicitly modeled.
- Consumes: Applied Sections and normalized result contracts.
- Outputs: corridor previews, surfaces, diagnostics, review objects, and output handoff objects.
- Rule: Build Corridor must not infer design meaning from generated meshes when an Applied Section or domain result contract should provide it.

### Terrain / Daylight

- Source: terrain/TIN source objects and side-slope/daylight policy own the available ground context and daylight intent.
- Consumes: Applied Section slope/daylight rows.
- Outputs: daylight intersection points, fallback diagnostics, and terrain-aware slope results.
- Rule: fixed-width or fallback daylight must be diagnostic and must not silently replace missing terrain intent.

### Drainage

- Source: `DrainageModel` owns drainage elements, flow routes, capture intent, low-point constraints, and discharge context.
- Consumes: Regions, Structures, Applied Section ditch/gutter context, and terrain where needed.
- Outputs: drainage review networks, hints, and downstream surface/solid handoff rows.
- Rule: ditch geometry from Applied Sections does not by itself create drainage source elements.

### Intersections

- Source: `IntersectionModel` owns at-grade junction topology, participating legs, control areas, curb-return policy, edge policy, grading policy, drainage policy, and design-vehicle intent.
- Consumes: Alignment, Profile, Region, Assembly/Subassembly, Superelevation, Drainage, Structure, and Terrain source context.
- Outputs: topology results, edge-network results, vertical-control results, surface-zone results, trim boundaries, diagnostics, and review geometry.
- Rule: intersection geometry must come from explicit source/evaluation contracts. Do not build intersections by repairing ordinary corridor surface fragments after the fact.

### Ramps

- Source: `RampModel` owns ramp topology, merge/diverge intent, gore/tie-in rules, and ramp-specific region relationships.
- Consumes: mainline Alignment/Profile/Region context and ramp source context.
- Outputs: ramp evaluation rows, transition/tie-in results, and review geometry.
- Rule: ramps must not be treated as minor lane widening in ordinary Regions when ramp topology is required.

### Structures

- Source: Structure source models own structure placement, type, connection points, and structural context.
- Consumes: Alignment/Profile/Region context and Drainage refs where relevant.
- Outputs: structure previews, connection point results, and output handoff rows.
- Rule: structure preview geometry must not become the source of pipe, inlet, culvert, bridge, or retaining-wall intent.

### Watertight Solids

- Source: none for design intent. Watertight Solid targets may own output configuration only.
- Consumes: accepted Applied Sections, Corridor/Surface results, Subassembly shape rows, Structure/Drainage output contracts, material context, quantity context, Region context, and diagnostic rows.
- Outputs: closed solid bodies, solid target rows, simulation/export packages, and Digital Twin handoff artifacts.
- Rule: Watertight Solids must not invent missing engineering meaning. If a closed body cannot be generated from accepted result contracts, report diagnostics and return to the owning source or evaluation stage.
- Rule: every generated solid should remain traceable to source ownership such as Subassembly ref, Region ref, station span, material role, surface role, Structure ref, or Drainage ref where available.

### Review, Viewer, Exchange, and AI

- Source: none unless an explicit approved source-writing command is being executed.
- Consumes: source models and result/output contracts.
- Outputs: review displays, reports, exchange packages, suggestions, and diagnostics.
- Rule: review tools and AI may explain or propose changes, but must not silently rewrite accepted design state.

## 4. Authoritative Documents

- Use `docsV1/V1_MASTER_PLAN.md` as the baseline reference for v1 product direction.
- Treat `docsV1/` as the active redesign document set.
- Treat `docsV0/` as archived legacy reference only.
- When adding a new v1 design document, align it with the master plan or explicitly record a deviation.
- When adding a new document under `docsV1/`, update `docsV1/README.md` unless there is a strong reason not to.

## 5. V1 Architecture Rules

- Durable design intent belongs in source models, not in generated geometry.
- Generated section wires, viewer artifacts, and exported geometry are outputs, not edit sources.
- Keep corridor logic traceable back to source models.
- Use normalized output contracts for viewers, reports, and exchange flows.
- Do not hide engineering logic inside task panels, viewer widgets, or export commands.

## 6. Domain Expectations

- `AlignmentModel` owns horizontal geometry intent.
- `RampModel` owns ramp topology, merge/diverge, and tie-in intent.
- `IntersectionModel` owns at-grade junction control-area intent.
- `DrainageModel` owns drainage intent, low-point constraints, and collection/discharge context.
- `SectionModel` and `AppliedSection` must reflect ramp, intersection, drainage, terrain, and structure context when relevant.
- `CorridorModel` should be treated as a corridor-network orchestration layer, not a single-loft object.

## 7. Code Placement

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

## 8. Editing Rules

- Do not revert unrelated user changes.
- Do not use destructive git commands unless explicitly requested.
- Prefer minimal, architecture-consistent edits over quick hacks.
- When changing terminology or workflow structure, keep wording aligned with the active v1 stage model.
- If documentation and code both change, keep them in sync in the same task when practical.

## 9. Documentation Rules

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

## 10. Viewer and Review Rules

- The Cross Section Viewer is a review and handoff surface, not a geometry editor.
- Review UI should expose source ownership, diagnostics, and context.
- Support same-context return after edit and rebuild when possible.
- Prefer read-only review surfaces over direct output editing.

## 11. Exchange and AI Rules

- Exchange logic should normalize into v1 contracts instead of inventing engineering meaning inside import/export code.
- AI outputs must stay explainable, reviewable, and approval-gated.
- Do not describe AI as silently rewriting accepted design state.

## 12. Testing Expectations

- The local FreeCAD command-line executable location is:
  - `D:\Program Files\FreeCAD 1.0\bin`
- When a task requires `FreeCADCmd.exe`, prefer this installed location first.
- For code changes, run focused validation when feasible.
- Prefer contract and service validation over UI-only manual checking.
- If tests cannot be run, say so clearly.
- For documentation-only changes, test execution is optional unless the change also affects executable examples or commands.

## 13. Preferred Change Workflow

Before making substantial changes:

- identify the active v1 source/result/output boundary involved
- check whether related docs need to be updated too
- avoid solving a v1 problem with a v0-shaped shortcut
- verify that any new geometry is produced from source/evaluation contracts, not preview objects or mesh repair
- record diagnostics when fallback geometry is unavoidable

When finishing work:

- summarize the actual architectural effect, not just the file list
- mention testing status
- call out any follow-up docs or code that should be aligned next
