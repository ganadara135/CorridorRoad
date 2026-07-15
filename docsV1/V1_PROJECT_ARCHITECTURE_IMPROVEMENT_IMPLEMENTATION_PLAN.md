# Parametric Road V1 Project Architecture Improvement Implementation Plan

Date: 2026-07-12
Status: Active implementation plan
Depends on:

- [V1_MASTER_PLAN.md](./V1_MASTER_PLAN.md)
- [V1_ARCHITECTURE.md](./V1_ARCHITECTURE.md)
- [V1_MODULE_LAYOUT.md](./V1_MODULE_LAYOUT.md)
- [V1_GENERAL_ROAD_PARAMETRIC_DESIGN_AUDIT_PLAN.md](./V1_GENERAL_ROAD_PARAMETRIC_DESIGN_AUDIT_PLAN.md)

## 1. Purpose

This plan converts the current repository-wide architecture review into an ordered implementation program.

The primary goals are:

- restore a reproducible development and validation baseline
- enforce the source -> evaluation -> result -> output -> presentation direction
- separate `commands`, `services`, `objects`, and `models` by responsibility
- reduce oversized command modules without changing accepted engineering behavior
- make build, review, diagnostics, and persistence independently testable
- stabilize the currently supported road, intersection, drainage, structure, quantity, earthwork, and exchange workflows

## 2. Active Scope Decisions

This plan records two explicit deviations from older v1 planning documents.

### 2.1 Ramp is removed from the active product scope

- Ramp authoring, evaluation, review, output, and UI development are not part of this plan.
- Do not add a Ramp command, toolbar stage, source editor, result builder, or new Ramp contract.
- Existing Ramp code and documents may remain for compatibility or historical reference.
- Existing Ramp code should receive only changes required to prevent regressions in supported workflows.
- Deleting or migrating existing Ramp data is a separate compatibility decision and is not authorized by this plan.
- Ordinary Region widening must not be relabeled as Ramp topology.

### 2.2 Watertight Solid development is paused

- New Watertight Solid capabilities, target families, simulation features, and package composition work are paused.
- Existing Watertight commands and persisted objects remain available for compatibility.
- Allowed work is limited to critical defect repair, data-loss prevention, compatibility, and keeping existing tests operational.
- Do not expand Watertight UI, topology algorithms, simulation QA, or export coverage during the pause.
- Watertight code may be moved mechanically when required by an architecture refactor, but behavior must remain unchanged.
- Resuming development requires an explicit scope decision and an update to this plan and `AGENTS.md`.

### 2.3 CI development is frozen

- Keep the current CI configuration and `release-guard` behavior unchanged.
- Do not add CI workflows, jobs, runners, matrices, quality gates, test stages, lint stages, or FreeCAD validation stages.
- Do not expand CI to run compile, architecture, contract, smoke, GUI, packaging, or platform compatibility tests.
- Do not change CI triggers, permissions, actions, runner versions, or release metadata validation unless a separate explicit request authorizes that exact change.
- Local validation scripts, VS Code tasks, and developer documentation may be improved without changing CI.
- CI expansion is not an acceptance criterion for any workstream in this plan.

## 3. Core Architecture Rule

All new and changed v1 code must use the following responsibility chain:

`commands -> services -> models`

FreeCAD document persistence uses:

`commands or services -> objects <-> models`

Presentation uses:

`commands -> ui -> result/output models`

The following reverse dependencies are prohibited:

- `models` importing `commands`, `objects`, UI, FreeCAD, Part, or Qt
- engineering `services` importing `commands` or UI
- UI importing a command module to reuse engineering behavior
- `objects` owning engineering evaluation rules
- commands reverse-reading preview geometry as source intent

Compatibility adapters must be named and isolated. They must not make a reverse dependency the normal v1 path.

## 4. Package Responsibilities

### 4.1 `models`

Purpose:

- define typed source, result, and output contracts
- preserve identity, schema version, source references, and diagnostics
- remain independent of FreeCAD and Qt

Rules:

- `models/source` owns durable user-authored design intent
- `models/result` owns rebuildable evaluated engineering state
- `models/output` owns normalized consumer and exchange contracts
- models must not read FreeCAD documents or create geometry presentation objects
- models may validate their own field-level invariants but must not orchestrate document workflows

### 4.2 `services`

Purpose:

- evaluate source models
- resolve domain context
- build result and output models
- provide deterministic geometry and mapping algorithms
- orchestrate reusable domain workflows without UI state

Rules:

- services consume and return typed models
- evaluation services must be deterministic where practical
- builder services may generate engineering geometry contracts but not FreeCAD preview objects
- mapping services translate between normalized contracts and external formats
- editing services apply explicit source changes and return validation diagnostics
- services must not own task panels, selections, visibility, or message boxes

### 4.3 `objects`

Purpose:

- adapt typed models to FreeCAD document objects
- create, update, restore, migrate, and locate persisted document records
- manage FreeCAD properties and stable tree placement through a shared document adapter

Rules:

- objects are persistence adapters, not source/evaluation engines
- object properties must round-trip to typed models
- schema migration must be explicit and versioned
- preview `Shape` data must not be read back as accepted source intent
- repeated project-tree routing logic must be centralized
- document transactions and recompute boundaries must be deliberate and testable

### 4.4 `commands`

Purpose:

- register FreeCAD commands
- validate active document and selection context
- assemble service requests
- invoke services and persistence adapters
- open UI and present actionable errors

Rules:

- commands must remain thin orchestration adapters
- commands must not contain domain geometry algorithms
- commands must not contain large reusable review or diagnostic calculations
- command task panels must move to `ui/editors` or `ui/viewers`
- FreeCAD preview creation must move to presentation adapters
- private service functions must not be imported

## 5. Current Baseline And Risks

The current repository has strong typed v1 models and mostly FreeCAD-independent service/model layers. The main imbalance is concentrated in command modules.

Current observations:

- v1 commands contain substantially more code than v1 services
- `cmd_build_corridor.py` contains command, UI, geometry, intersection, review, audit, and preview responsibilities
- several editor commands contain both task panels and source-editing rules
- some UI modules import command modules
- project-tree routing is imported repeatedly from legacy project objects
- broad `except Exception` handling can turn programming faults into silent fallbacks
- large result objects use many parallel FreeCAD `StringList` properties and custom row serialization
- local smoke tests can load the wrong workbench when duplicate Mod directories exist
- current CI validates release metadata only; this behavior is intentionally frozen and is not an improvement target

## 6. Implementation Workstreams

### Workstream A: Local development and validation baseline

Tasks:

1. Detect duplicate `CorridorRoad` or `Corridor-Road` Mod installations.
2. Print and verify the actual imported package path before tests.
3. Add a reproducible development dependency definition.
4. Add commands for compile, lint, pure contract tests, FreeCAD smoke tests, and full validation.
5. Keep all new validation paths local to developer scripts, VS Code tasks, and documentation.
6. Do not modify or expand CI while implementing this workstream.

Acceptance criteria:

- tests fail before execution when the imported workbench path is not the current repository
- a new contributor can identify and run the supported validation tiers
- the validation commands return non-zero on the first failed tier
- the existing CI configuration and release metadata validation remain unchanged

### Workstream B: Architecture boundary enforcement

Tasks:

1. Add architecture tests for package dependency rules.
2. Remove private service imports from command modules.
3. Remove UI-to-command imports by introducing presentation or editing services.
4. Introduce a shared `ProjectDocumentAdapter` for project lookup, persistence, tree routing, stale result cleanup, transaction, and recompute operations.
5. Record approved legacy compatibility adapters explicitly.

Acceptance criteria:

- `models` remain FreeCAD- and Qt-independent
- engineering services do not import commands or UI
- UI does not import command modules for reusable behavior
- new v1 object persistence does not call legacy tree routing directly from multiple feature modules

### Workstream C: Build Parametric decomposition

Tasks:

1. Freeze current public helper behavior with focused contract tests.
2. Move pure XY and polygon algorithms into `services/geometry`.
3. Extract general corridor surface orchestration.
4. Extract Intersection surface, slope-face, tie-slope, and shared-breakline services.
5. Extract shared-breakline audit into a typed result and review mapper.
6. Extract FreeCAD preview and diagnostic marker adapters.
7. Move `V1BuildCorridorTaskPanel` into `ui/viewers` with a view model.
8. Reduce `cmd_build_corridor.py` to request assembly, orchestration, persistence, and command registration.

Acceptance criteria:

- engineering geometry services do not create FreeCAD document objects
- Build Parametric consumes accepted Applied Sections and domain results
- no extracted service reads preview `Shape` geometry as source
- existing ordinary-road and Intersection contract tests retain equivalent results
- command code no longer owns polygon clipping or TIN triangulation algorithms

### Workstream D: Editor command decomposition

Target order:

1. Structure editor
2. Profile editor
3. SubAssembly Designer
4. Subassembly editor
5. Drainage editor and review
6. Alignment and TIN editors

Tasks for each editor:

- move the task panel to `ui/editors`
- move source validation and edit application to `services/editing`
- introduce a UI-independent view model where table state is complex
- keep command activation and registration in `commands`
- preserve source ownership and same-context return behavior

Acceptance criteria:

- source changes can be tested without constructing a Qt panel
- closing or refreshing a panel does not change source data
- Apply or Save is the explicit source-writing boundary
- preview generation remains temporary presentation behavior

### Workstream E: Persistence and schema hardening

Tasks:

1. Inventory parallel `StringList` row contracts.
2. Define versioned payload serializers for complex nested models.
3. Add explicit migration functions by schema version.
4. Validate row counts, required refs, and payload checksums during restore.
5. Preserve a readable subset of FreeCAD properties for tree/property review.
6. Add round-trip and old-document restoration tests.

Acceptance criteria:

- malformed or partial persisted rows produce diagnostics instead of silent truncation
- schema upgrades are explicit and testable
- source, result, and output refs survive save/reopen
- persistence adapters do not invent missing engineering intent

### Workstream F: Diagnostics and exception policy

Tasks:

1. Define specific exception families for source validation, evaluation, result contracts, persistence, preview, and exchange.
2. Replace broad exception handling in high-risk command paths incrementally.
3. Keep traceback and technical context for unexpected programming errors.
4. Convert expected domain failures into typed diagnostics.
5. Record every fallback with kind, owner, consumed refs, and user action.

Acceptance criteria:

- preview failure is distinguishable from engineering result failure
- unexpected errors are not converted into a successful empty result
- fallback output is visible and traceable
- error handling does not write repaired geometry back to source models

### Workstream G: Incremental build and performance

Tasks:

1. Add source fingerprints to major rebuildable result families.
2. Record consumed source/result refs and service versions.
3. Mark stale results with explicit reasons.
4. Rebuild only affected stages.
5. Batch FreeCAD object updates in a transaction.
6. Use one deliberate recompute per completed apply phase where feasible.
7. Separate presentation-only refresh from engineering rebuild.

Acceptance criteria:

- visibility and style changes do not rebuild engineering results
- unchanged source fingerprints reuse accepted results where safe
- interrupted builds preserve the previous accepted result
- build duration and changed stages are visible in diagnostics

### Workstream H: Supported-domain stabilization

Active supported domains for this plan:

- Project and TIN
- Alignment, Stations, Profile, and 3D Centerline
- Superelevation
- SubAssembly Designer, Assembly/Subassembly, and Region
- Applied Sections and Build Parametric
- Intersections
- Structures
- Drainage source, routing, review, and existing output handoff
- Cross Section, Plan/Profile, quantity, and earthwork review
- current exchange paths

Tasks:

- finish source/result ownership gaps before adding new geometry repair logic
- prioritize general Intersection contracts over preset-name branches
- keep Drainage hydraulic sizing and advanced analysis outside the current scope
- preserve existing Structure and Drainage handoff traceability
- keep Ramp removed and Watertight development paused as defined in Section 2

Acceptance criteria:

- supported output paths identify their source and result owners
- review tools do not become direct output editors
- missing source intent blocks or diagnoses output instead of silently repairing it

### Workstream I: Documentation and release alignment

Tasks:

1. Add a single domain status index.
2. Classify documents as contract, active plan, completed record, manual QA, or archived proposal.
3. Align minimum, recommended, and validated FreeCAD versions.
4. Update user documentation to remove Ramp from active scope.
5. Mark Watertight Solid development as paused while preserving current compatibility documentation.
6. Clean package metadata formatting and encoding artifacts.

Acceptance criteria:

- current product scope can be determined from one status document
- historical plans are not mistaken for active commitments
- release notes distinguish supported, paused, and removed scope

## 7. Delivery Phases

### Current implementation record

Phase 0 completed on 2026-07-12:

- duplicate Workbench detection added to the shared FreeCAD environment helper
- actual `freecad.Corridor_Road` import path verification added to the environment check
- maintained smoke runners now stop before execution when a conflicting Workbench installation is present
- local Compile, Lint, Contracts, Smokes, and Full validation tiers added without changing CI
- local development dependencies recorded in `requirements-dev.txt`
- VS Code tasks added for the local validation tiers
- v1-only project-tree smoke baseline restored
- stale bench face-count, boolean-cut status, Intersection audit, focus, and Roundabout boundary expectations aligned with current result contracts
- generated Intersection tie-in section augmentation now preserves existing Applied Section station-row kinds and source identity
- Compile, Short-term, Practical Scope, and Loft Retirement Gate validation passed
- `pytest 8.4.2` and `flake8 7.3.0` installed in the selected FreeCAD Python user environment
- contract collection passed with 1,228 tests discovered
- focused service, project-tree, Applied Sections, and Build Corridor contracts passed: 43 tests
- the complete 1,228-test contract run exceeded both 5-minute and 15-minute local execution limits without producing an early failure
- full-repository Lint executed and exposed the pre-existing baseline debt, including undefined names, duplicate definitions, unused imports/variables, indentation issues, and formatting issues

Known Phase 1 inputs:

- separate fast service contracts from long-running FreeCAD integration contracts
- remove or isolate tests that wait on GUI/event behavior during a full headless run
- fix `F821` undefined-name errors before lower-risk style cleanup
- establish architecture dependency checks independently from the full legacy lint backlog

CI remains unchanged and frozen.

Phase 1 boundary-guard slice 1 completed on 2026-07-12:

- AST-based dependency tests now guard `models`, `services`, `objects`, UI, and command-to-service boundaries without importing FreeCAD
- the two existing UI-to-command reverse dependencies are fixed in an explicit compatibility list so new reverse dependencies fail locally
- existing command imports of private service symbols are fixed in an explicit compatibility list; this records 13 Centerline3D helpers, one Subassembly helper, and one Build Corridor helper for later removal
- all repository `F821` undefined-name errors are cleared
- the v1 earthwork report no longer builds station navigation twice
- the legacy earthwork compatibility report now creates the station-navigation rows it returns
- local `Architecture` and `Fast` validation tiers and matching VS Code tasks are available
- the Fast tier passed Compile, 5 architecture tests, and 47 focused v1 contracts
- CI remains unchanged and frozen

Next Phase 1 slice:

1. replace the Build Corridor import of `_supplemental_sampled_sections` with a public service API
2. preserve its sampling behavior with focused contracts
3. then remove the smaller Subassembly private-helper import before addressing the larger Centerline3D compatibility group

Phase 1 boundary-guard slice 2 completed on 2026-07-12:

- `supplemental_sampled_sections` is now a documented public service API exported by `services.builders`
- Build Corridor no longer imports `_supplemental_sampled_sections` from a service implementation module
- service-internal callers and supplemental-frame contracts use the same public API
- the temporary private-import compatibility list was reduced by one entry
- focused supplemental sampling and marker contracts passed: 8 tests
- the supplemental sampling contract suite is now part of the local Fast tier
- the updated Fast tier passed Compile, 5 architecture tests, and 55 focused v1 contracts
- CI remains unchanged and frozen

Next Phase 1 slice:

1. replace the Subassembly editor import of `_bench_profile_segments` with an explicit public evaluation API
2. preserve bench point, link, shape, material, and quantity behavior with focused contracts
3. then design the migration path for the 13 Centerline3D private geometry-helper imports

Phase 1 boundary-guard slice 3 completed on 2026-07-12:

- `BenchProfileSegment` and `SubassemblyBenchProfileResult` now define the typed Bench evaluation contract under `models/result`
- `SubassemblyBenchProfileService` now owns deterministic side-slope and Bench profile evaluation under `services/evaluation`
- Applied Sections consumes the public service through a compatibility conversion wrapper
- Subassembly Editor Preview consumes typed service result rows and no longer imports `_bench_profile_segments`
- the temporary command-to-private-service compatibility list now contains only the 13 Centerline3D helpers
- direct service, Applied Sections, terrain daylight, repeat, Preview, Viewer, quantity, material, and Exchange contracts passed: 21 tests
- the new service and Section Preview contracts are included in the local Fast tier
- the updated Fast tier passed Compile, 5 architecture tests, and 64 focused v1 contracts
- changed-file Lint and repository-wide `F821` validation passed
- CI remains unchanged and frozen

Next Phase 1 slice:

1. classify the 13 Centerline3D helpers into public source-geometry evaluation operations and command-local presentation-only operations
2. replace private imports with the smallest public typed service surface that preserves source-geometry behavior
3. remove the final command-to-private-service compatibility entries and run Centerline3D source-geometry contracts

Phase 1 boundary-guard slice 4 completed on 2026-07-12:

- the 13 Centerline3D private imports were classified into four required public operations and nine unused command compatibility wrappers
- `Centerline3DArcFitResult` now defines the typed plan arc-fit quality contract under `models/result`
- `Centerline3DSourceGeometryService` now publicly provides horizontal point evaluation, plan payload normalization, typed arc-fit evaluation, and tolerance normalization
- the nine unused command-local compatibility wrappers were removed
- Centerline3D Command no longer imports private service symbols
- the command-to-private-service compatibility list is empty and new private imports fail architecture validation
- accepted and rejected arc-fit, Part Arc, dense curve sampling, source-frame preference, and typed service contracts passed
- the updated Fast tier passed Compile, 5 architecture tests, and 73 focused v1 contracts
- changed-file Lint, repository-wide `F821`, and `git diff --check` passed
- CI remains unchanged and frozen

Remaining known Centerline3D baseline items:

- the complete Centerline3D command file has three pre-existing default-display expectation mismatches: empty display normalization, default preview curve kind, and default task-panel selection
- these display-default decisions are presentation behavior and were not changed as part of the source-geometry service boundary extraction

Next Phase 1 slice:

1. inventory repeated FreeCAD document discovery, lookup, property-write, tree-routing, transaction, and recompute behavior
2. define the minimal `ProjectDocumentAdapter` interface without moving engineering evaluation into objects
3. migrate one low-risk command path with contract tests before expanding adapter usage

Phase 1 document-adapter slice 1 completed on 2026-07-12:

- repeated v1 document operations were inventoried across Command, object, exchange, mapper, and viewer paths
- `ProjectDocumentAdapter` now provides project and object lookup, object and property persistence, value writes, canonical tree routing, explicit stale-result cleanup, nested transaction boundaries, and deliberate recompute
- the adapter remains a FreeCAD persistence boundary under `objects`; it does not evaluate engineering source intent
- Station Highlight was selected as the first low-risk migration because it is presentation-only and does not own source or result truth
- Station Highlight creation and update now use one transaction, one canonical tree-routing path, and one final recompute
- the previous Station Highlight command-local project lookup and legacy tree-routing helpers were removed
- 22 existing v1 object modules that still call legacy tree routing directly were recorded as an explicit compatibility baseline
- architecture validation now blocks any new direct legacy tree-routing module and requires the baseline to shrink deliberately as migrations proceed
- adapter unit contracts and the real FreeCAD Station Highlight reuse and tree-routing contract passed
- the updated Fast tier passed Compile, 6 architecture tests, and 79 focused v1 contracts
- changed-file Lint, repository-wide `F821`, JSON parsing, and `git diff --check` passed
- CI remains unchanged and frozen

Next Phase 1 slice:

1. migrate the v1 Stationing source-object persistence path to `ProjectDocumentAdapter` and remove `obj_stationing.py` from the direct-routing compatibility list
2. validate create, update, tree placement, and save/reopen behavior without changing station evaluation
3. then introduce a presentation service to remove the Profile Review UI import of `cmd_review_stations`

Phase 1 document-adapter slice 2 completed on 2026-07-12:

- `obj_stationing.py` now creates Stationing document objects and routes them through `ProjectDocumentAdapter`
- Station evaluation remains in `AlignmentStationSamplingService`; the adapter owns only persistence boundaries
- `generate_v1_stations` now batches project preparation, Stationing creation, project linking, and one final recompute in a shared transaction
- standalone Stationing creation preserves FreeCAD automatic object-name disambiguation through the adapter's explicit `create_object` operation
- `obj_stationing.py` was removed from the direct legacy tree-routing compatibility list, reducing the baseline from 22 modules to 21
- create, update, tick-shape, tree placement, and Station Highlight contracts passed
- a FreeCAD save/reopen contract now verifies Station values, source geometry signature, object identity, Stations tree membership, and persisted Shape
- the updated Fast tier passed Compile, 6 architecture tests, and 82 focused v1 contracts
- changed-file Lint, repository-wide `F821`, and `git diff --check` passed
- CI remains unchanged and frozen

Known unrelated Stationing suite item:

- the full Stationing source-object file still contains one Plan/Profile preview expectation for the removed `key_station_rows` response key; Stationing persistence and evaluation contracts pass independently

Next Phase 1 slice:

1. extract Station Highlight presentation behavior from `cmd_review_stations.py` into a presentation service
2. make Profile Review UI consume that service instead of importing a command module
3. remove the Profile Review UI-to-command compatibility entry and preserve same-context station focus behavior

Phase 1 presentation-boundary slice 1 completed on 2026-07-12:

- `StationHighlightPresentationService` now owns station marker Shape creation, presentation styling, and adapter-backed document application under `ui/presentation`
- `cmd_review_stations.py` retains compatibility exports for existing external callers but no longer owns Station Highlight implementation
- Profile Review Viewer consumes the presentation service directly and no longer imports `cmd_review_stations.py`
- the Profile Review UI-to-command compatibility entry was removed; only the Structure Editor compatibility entry remains
- same-context Profile Review station resolution and 3D marker application are covered without constructing a QWidget in headless validation
- the existing QWidget-based Plan/Profile highlight test terminates the Windows Qt process when run without a QApplication, confirming a separate headless-test isolation item rather than a presentation-service contract failure
- the updated Fast tier passed Compile, 6 architecture tests, and 84 focused v1 contracts
- changed-file Lint, repository-wide `F821`, and `git diff --check` passed
- CI remains unchanged and frozen

Next Phase 1 slice:

1. inspect the Structure Editor compatibility shim and separate its task-panel presentation class from command orchestration
2. make `ui/editors/structure_editor.py` own or import presentation code without importing a command module
3. remove the final UI-to-command compatibility entry and validate Structure create, edit, preview, and apply contracts

Phase 1 presentation-boundary slice 2 completed on 2026-07-12:

- `ui/editors/structure_editor.py` no longer imports or re-exports `cmd_structure_editor.py`
- `StructureEditorTaskPanelPresentation` now owns the Structure panel lifecycle, shared presentation state, status display, validation display, Apply acceptance, and dialog rejection behavior
- the concrete command-side controller inherits the UI presentation boundary and retains the existing editing callbacks during incremental migration
- the final UI-to-command compatibility entry was removed; architecture validation now requires zero UI imports from Command modules
- Structure station edits, applied-row reopen behavior, source-only Apply, and visible 3D Preview contracts passed
- two unused Structure source-model imports exposed by focused Lint were removed
- the updated Fast tier passed Compile, 6 architecture tests, and 89 focused v1 contracts
- changed-file Lint, repository-wide `F821`, and `git diff --check` passed
- CI remains unchanged and frozen

Remaining Structure Editor decomposition:

- concrete widget construction and editing callbacks still reside in `cmd_structure_editor.py`
- moving those responsibilities fully into `ui/editors` requires a typed editing/controller service and belongs to the Editor extraction phase rather than reintroducing a UI-to-command dependency

Next implementation slice:

1. run the complete Phase 1 architecture and focused regression record and confirm all temporary reverse-dependency lists are empty
2. inventory `cmd_build_corridor.py` pure geometry candidates and freeze their current public behavior with focused contracts
3. begin Phase 2 by extracting the first low-risk pure XY/polygon helper group into `services/geometry`

Phase 1 boundary guards completed on 2026-07-12:

- architecture validation enforces model, service, object, UI, private-service, and legacy tree-routing boundaries
- command-to-private-service and UI-to-command temporary compatibility lists are empty
- `ProjectDocumentAdapter` is established and used by Station Highlight and Stationing persistence
- existing direct legacy tree-routing object modules remain in an explicit shrinking compatibility baseline; new direct users are blocked
- the Phase 1 Fast record passed Compile, 6 architecture tests, and 89 focused v1 contracts before Phase 2 geometry tests were added
- the complete 1,228-test contract run remains separated from Fast because the headless full run exceeds the recorded execution limits
- CI remains unchanged and frozen

Phase 2 Build Parametric extraction slice 1 completed on 2026-07-12:

- `services/geometry` was introduced as a FreeCAD-independent pure geometry package
- XY point normalization, distance, triangle signed area, strict point-in-triangle, and polygon signed area were extracted from `cmd_build_corridor.py`
- existing Command `_xy_*` names remain behavior-preserving compatibility wrappers
- a duplicate `_xy_distance` definition in `cmd_build_corridor.py` was removed
- direct service contracts cover object and sequence inputs, orientation, strict boundary behavior, degeneracy, and polygon orientation
- Command wrapper contracts verify numeric equivalence with the new geometry service
- the updated Fast tier passed Compile, 6 architecture tests, and 94 focused v1 contracts
- changed-file Lint, repository-wide `F821`, and `git diff --check` passed
- CI remains unchanged and frozen

Known unrelated Build Corridor contract item:

- one older curb-return slope-band test calls `_augment_daylight_surface_with_curb_return_boundary_bands`, which is not present in the current Command module; the extracted primitive and compatibility-wrapper contracts pass independently

Next Phase 2 slice:

1. extract deterministic ear-clipping triangulation and triangle-quality calculations into `services/geometry`
2. keep Intersection-specific request assembly and diagnostics outside the pure geometry module
3. preserve winding, concave polygon, degenerate polygon, and skinny-triangle behavior with focused contracts

Phase 2 Build Parametric extraction slice 2 completed on 2026-07-12:

- deterministic ear-clipping triangulation moved to `services/geometry/polygon_triangulation.py`
- normalized triangle-quality calculation moved to the same FreeCAD-independent geometry module
- Intersection-specific TIN object assembly, quality-row mapping, diagnostics, and fallback selection remain outside the pure geometry service
- existing `_intersection_patch_ear_clip_indices` and `_xy_triangle_quality_ratio` names remain compatibility wrappers
- the Command-local `_intersection_patch_is_ear` implementation was removed
- contracts cover clockwise and counter-clockwise winding, deterministic indices, concave polygon area preservation, degenerate polygons, equilateral quality, skinny quality, zero-area quality, and Command wrapper equivalence
- the updated Fast tier passed Compile, 6 architecture tests, and 99 focused v1 contracts
- changed-file Lint, repository-wide `F821`, and `git diff --check` passed
- CI remains unchanged and frozen

Known triangulation limitation:

- when a concave notch lies exactly on a candidate ear diagonal, the preserved strict point-in-triangle rule can accept an overlapping ear and overstate triangulated area
- this is an existing algorithm behavior and was not silently changed during extraction; correcting it requires a separately tested boundary-inclusive ear predicate decision

Next Phase 2 slice:

1. extract convex polygon intersection and subtraction primitives from `cmd_build_corridor.py`
2. keep surface-role ownership, Intersection policy, and fallback diagnostics in the caller
3. cover full containment, partial overlap, disjoint polygons, winding reversal, and boundary-touch behavior

Phase 2 Build Parametric extraction slice 3 completed on 2026-07-12:

- convex polygon classification, payload-polygon intersection, and convex exclusion subtraction moved to `services/geometry/convex_polygon_clipping.py`
- half-plane splitting, boundary classification, segment intersection, Z interpolation, source-lineage composition, and XY payload deduplication are private geometry-service implementation details
- multi-exclusion ordering, hole-part composition, surface ownership, Intersection policy, and fallback diagnostics remain in the Command caller
- existing `_xy_polygon_is_convex`, `_xy_intersect_polygon_with_convex_polygon`, and `_xy_subtract_convex_polygon_from_polygon` names remain compatibility wrappers
- the duplicated Command-local half-plane and intersection implementations were removed
- contracts cover convex winding, concavity rejection, full containment, partial overlap, disjoint polygons, winding reversal, boundary touch, Z interpolation, source lineage, and Command wrapper equivalence
- the updated Fast tier passed Compile, 6 architecture tests, and 105 focused v1 contracts
- changed-file Lint, repository-wide `F821`, and `git diff --check` passed
- CI remains unchanged and frozen

Next Phase 2 slice:

1. consolidate `_xy_triangulate_simple_polygon_points` on the extracted ear-clipping service instead of maintaining a second Command-local implementation
2. extract reusable segment intersection, strict crossing, projection, and distance primitives into `services/geometry`
3. preserve collinear, endpoint-touch, parallel, zero-length, and nearest-distance behavior with focused contracts

Phase 2 Build Parametric extraction slice 4 completed on 2026-07-12:

- `_xy_triangulate_simple_polygon_points` now delegates to the extracted ear-clipping service instead of maintaining a second Command-local implementation
- the ear-clipping service accepts an explicit final-triangle area tolerance so the existing Intersection `1.0e-6` and simple-polygon `1.0e-9` behaviors remain distinct and traceable
- inclusive segment intersection, strict interior crossing, point-to-segment distance with raw projection ratio, segment projection ratio, and segment distance moved to `services/geometry/segment_geometry.py`
- existing Command helper names remain behavior-preserving compatibility wrappers
- the duplicated Command-local ear and triangle-area helpers were removed
- contracts cover crossing, endpoint touch, collinear overlap, disjoint and parallel segments, zero-length segments, unclamped projection ratios, nearest distance, deterministic simple-polygon triangulation, and Command wrapper equivalence
- the updated Fast tier passed Compile, 6 architecture tests, and 110 focused v1 contracts
- changed-file Lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. extract reusable point-in-polygon, closed-edge, and general polygon relation predicates into `services/geometry`
2. keep curb-return, surface-role ownership, Intersection policy, and fallback diagnostics in the Command caller
3. preserve inside, outside, boundary-touch, convex, concave, crossing, and degeneracy behavior with focused contracts

Phase 2 Build Parametric extraction slice 5 completed on 2026-07-12:

- closed polygon edge generation, point-on-segment, legacy ray-cast point inclusion, strict point inclusion, and triangle/polygon relation predicates moved to `services/geometry/polygon_relations.py`
- triangle/polygon relation classification preserves the existing `edge_crossing`, `centroid_inside`, `triangle_vertex_inside`, and `polygon_vertex_inside_triangle` result contract and evaluation priority
- the non-strict ray-cast boundary behavior remains unchanged, while the strict predicate consistently excludes every boundary edge with the existing `1.0e-6` tolerance
- `_xy_polygon_area` now delegates to the previously extracted signed-area primitive instead of maintaining another Command-local implementation
- existing Command helper names remain behavior-preserving compatibility wrappers
- curb-return protection, pavement-strip ownership, roundabout ownership, Intersection policy, and diagnostics remain in the Command caller
- contracts cover ordered edge closure, short inputs, inside and outside points, asymmetric legacy boundary results, strict boundary exclusion, concave polygons, boundary touch, disjoint and degenerate relations, zero-length segments, relation classification, and Command wrapper equivalence
- the updated Fast tier passed Compile, 6 architecture tests, and 116 focused v1 contracts
- changed-file Lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. extract reusable polygon self-intersection and ring-boundary intersection predicates into `services/geometry`
2. preserve adjacent-edge exclusion, closing-edge adjacency, endpoint touch, collinear overlap, concave-ring, and degenerate-ring behavior
3. keep Intersection ring ownership, ring-role diagnostics, and source-result mapping in the Command caller

Phase 2 Build Parametric extraction slice 6 completed on 2026-07-12:

- non-adjacent polygon-edge self-intersection and two-polygon boundary intersection predicates moved to `services/geometry/polygon_relations.py`
- both predicates reuse the extracted inclusive segment-intersection contract, so endpoint touch and collinear overlap remain intersections
- self-intersection preserves adjacent-edge exclusion and first-edge/last-edge adjacency exclusion
- `_xy_xyz_polygon_self_crossing`, `_intersection_patch_boundary_has_self_crossing`, and `_intersection_patch_boundary_rings_intersect` remain behavior-preserving Command compatibility wrappers
- Intersection point-row conversion, ring roles, ownership, diagnostic messages, and source-result mapping remain in the Command caller
- contracts cover simple and concave rings, bow-tie crossing, non-adjacent endpoint touch, collinear overlap, short and degenerate rings, explicit duplicate closing points, containment without boundary crossing, disjoint rings, endpoint touch, edge overlap, XYZ inputs, and Command wrapper equivalence
- the updated Fast tier passed Compile, 6 architecture tests, and 121 focused v1 contracts
- changed-file Lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Preserved topology input constraint:

- polygon self-intersection expects an open vertex sequence with implicit closure; explicitly repeating the first vertex at the end can create a non-adjacent endpoint-touch result and is preserved as existing behavior

Next Phase 2 slice:

1. extract reusable clamped segment parameters and XY segment-intersection point calculations needed by outer-boundary assembly
2. extract source-preserving XYZ intersection interpolation without moving Intersection ownership or union policy into geometry services
3. preserve parallel, endpoint, zero-length, clamping, and interpolated-Z averaging behavior with focused contracts

Phase 2 Build Parametric extraction slice 7 completed on 2026-07-12:

- finite-segment clamped projection parameters moved to `services/geometry/segment_geometry.py`
- finite XY segment-intersection point calculation with XYZ interpolation moved to the same FreeCAD-independent service
- point-on-segment moved from polygon relations to the segment service so segment intersection does not create a reverse geometry dependency
- intersection calculation preserves the existing `1.0e-9` parallel denominator tolerance and `1.0e-6` finite-boundary tolerance
- interpolated Z preserves the existing rule of averaging the independently interpolated elevations from both source segments
- `_xy_segment_parameter` and `_xy_segment_intersection_point` remain behavior-preserving Command compatibility wrappers
- outer-boundary candidate selection, segment-union policy, Intersection ownership, and diagnostics remain in the Command caller
- contracts cover inside and outside projection, start and end clamping, zero-length segments, interior crossing, endpoint crossing, non-intersecting infinite lines, parallel and collinear segments, averaged interpolated Z, and Command wrapper equivalence
- the updated Fast tier passed Compile, 6 architecture tests, and 125 focused v1 contracts
- changed-file Lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. extract deterministic source-preserving XYZ exterior convex-hull calculation into `services/geometry`
2. preserve six-decimal XY identity, collinear-point removal, `1.0e-9` turn tolerance, counter-clockwise winding, and source Z payload selection
3. keep tie-in candidate selection, Intersection union policy, fallback selection, and diagnostics in the Command caller

Phase 2 Build Parametric extraction slice 8 completed on 2026-07-12:

- deterministic source-preserving XYZ exterior convex-hull calculation moved to `services/geometry/polygon_boundary.py`
- coordinate-sequence-to-XYZ normalization moved to the same FreeCAD-independent geometry module
- hull identity preserves six-decimal rounded XY keys and retains the first source XYZ payload for duplicate keys
- the monotone-chain turn predicate preserves the existing `1.0e-9` tolerance, removes collinear edge points, rejects zero-area hulls at `1.0e-6`, and returns counter-clockwise output
- `_xy_polygon_exterior_hull_boundary`, `_xyz_tuple`, and `_xy_area_from_xyz_points` remain behavior-preserving Command compatibility wrappers; the area wrapper now uses the extracted signed-area primitive
- tie-in candidate selection, Intersection union policy, fallback selection, source ownership, and diagnostics remain in the Command caller
- contracts cover short XYZ normalization, missing Z, interior-point removal, collinear-point removal, first-Z selection for six-decimal XY duplicates, clockwise input, CCW output, short and collinear degeneracy, turn tolerance, and Command wrapper equivalence
- the updated Fast tier passed Compile, 6 architecture tests, and 130 focused v1 contracts
- changed-file Lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. extract source-preserving polygon-union outer-boundary and segment-graph ring-ordering algorithms into `services/geometry`
2. preserve intersection splitting, strict midpoint exclusion, six-decimal graph identity, duplicate-edge removal, ring winding, self-crossing rejection, and largest-ring selection
3. keep the selection of input tie-in and curb-return polygons, Intersection ownership, hull fallback policy, and diagnostics in the Command caller

Phase 2 Build Parametric extraction slice 9 completed on 2026-07-12:

- source-preserving XYZ polygon-union outer-boundary calculation moved to `services/geometry/polygon_boundary.py`
- unordered segment-graph ring construction and largest valid outer-ring selection moved to the same FreeCAD-independent service
- union processing reuses extracted finite-segment intersection, clamped projection, strict point-in-polygon, self-intersection, distance, and signed-area contracts
- intersection splitting preserves independently interpolated and averaged source Z values
- split-point deduplication preserves the actual runtime three-dimensional distance tolerance of `1.0e-6`; six-decimal XY identity remains limited to graph nodes and duplicate-edge identity
- graph traversal preserves duplicate undirected-edge removal, positive-angle continuation, self-crossing rejection, counter-clockwise winding, and largest-area ring selection
- `_xy_polygon_union_outer_boundary` and `_ordered_outer_boundary_from_segments` remain behavior-preserving Command compatibility wrappers; duplicated Command-local graph traversal was removed
- input tie-in and curb-return polygon selection, Intersection ownership, convex-hull fallback policy, and diagnostics remain in the Command caller
- contracts cover a single polygon, overlapping polygons, averaged intersection Z, strict-midpoint removal of contained boundaries, duplicate and near-zero edges, multiple rings, largest-ring selection, counter-clockwise winding, and Command wrapper equivalence
- the updated Fast tier passed Compile, 6 architecture tests, and 135 focused v1 contracts
- changed-file Lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Phase 2 pure-geometry first pass completed on 2026-07-12:

- reusable XY/XYZ primitives, triangulation, clipping, relations, topology, segment interpolation, convex hull, polygon union, and boundary ordering now live under `services/geometry`
- Command compatibility wrappers preserve existing private helper call sites while engineering algorithms no longer originate in the Command module
- the next Phase 2 work begins typed domain-builder extraction

Next Phase 2 slice:

1. freeze the ordinary-road corridor surface orchestration inputs, outputs, and diagnostic decisions currently assembled in `cmd_build_corridor.py`
2. introduce or extend typed request/result contracts under `services/builders` so general corridor surface orchestration consumes accepted Applied Sections and normalized results
3. keep FreeCAD document persistence, preview creation, task-panel state, and command registration in the Command and presentation layers

Phase 2 Build Parametric extraction slice 10 completed on 2026-07-12:

- `CorridorSurfaceGeometryBuildRequest` and `CorridorSurfaceGeometryBuildResult` were introduced under `services/builders`
- `CorridorSurfaceOrchestrationService` now owns ordinary-road surface-role normalization and explicit routing to design, subgrade, daylight, and drainage geometry builders
- existing surface-role aliases normalize into stable ordinary-road roles without dynamic Command-owned builder method names
- successful, unsupported-role, and geometry-build failure outcomes now return typed statuses and diagnostic rows
- Region surface preview request assembly now consumes the typed orchestration service; `_region_surface_role_specs` no longer stores geometry-service method names
- the service consumes the accepted `AppliedSectionSet` already carried by `CorridorDesignSurfaceGeometryRequest` and does not read FreeCAD documents or preview geometry
- Region surface preview object creation, styling, persistence, tree routing, ground-surface resolution, and supplemental-frame resolver assembly remain in the Command layer
- contracts cover all four ordinary-road roles, legacy role aliases, exact request forwarding, typed ready results, unsupported roles, build failures, diagnostic text, and Command Region role specifications
- focused existing Region preview regression checks passed 2 tests
- the updated Fast tier passed Compile, 6 architecture tests, and 148 focused v1 contracts
- changed-file Lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. migrate the top-level design, subgrade, daylight, and drainage preview geometry-build calls to `CorridorSurfaceOrchestrationService`
2. preserve each role's existing Applied Section selection, terrain input, supplemental sampling, transition input, post-build clipping, shared-breakline processing, and diagnostic wording
3. keep TIN preview mapping, FreeCAD object persistence, visibility, styling, tree routing, and review properties outside the builder service

Phase 2 Build Parametric extraction slice 11 completed on 2026-07-12:

- top-level design, subgrade, daylight, and drainage preview geometry builds now use `CorridorSurfaceOrchestrationService`
- `cmd_build_corridor.py` no longer imports or directly calls `CorridorSurfaceGeometryService`
- the typed build result now carries the original `error_message` separately from normalized diagnostic rows
- a Command result adapter restores failed typed results to the existing role-specific `try/except` flow, preserving user-facing diagnostic prefixes and original exception messages
- all existing `CorridorDesignSurfaceGeometryRequest` fields remain role-specific and unchanged, including accepted Applied Sections, terrain input for daylight, supplemental sampling, frame resolver, and surface-transition input
- design Intersection exclusion and shared-breakline processing, subgrade roundabout clipping, daylight suppression and shared-breakline processing, and drainage preview policy remain after the typed build boundary in the Command caller
- TIN preview mapping, FreeCAD persistence, visibility, styling, tree routing, and review properties remain outside the builder service
- contracts cover error-message preservation, ready-result unwrapping, failure rethrow behavior, and the absence of direct top-level geometry-service calls
- focused typed orchestration and architecture validation passed 23 tests
- focused design shared-breakline and drainage handoff regression validation passed 2 tests
- the updated Fast tier passed Compile, 6 architecture tests, and 150 focused v1 contracts
- changed-file Lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Known broader Build Corridor expectation mismatches observed during this slice:

- a drainage-missing review test assumes `rows[4]` is the drainage row, while the current row at that fixed index is daylight
- a drainage preview test expects 16 facets while the current geometry request produces 4 facets
- a slope-face contact-marker test expects a marker object that the current marker path does not create; this path is outside the surface geometry orchestration change
- these broader expectations are not included in Fast and were not silently changed during the routing extraction

Phase 2 ordinary-road surface routing first pass completed on 2026-07-12:

- Region and top-level ordinary-road surface geometry requests now cross one typed service boundary
- document-derived request inputs and all presentation/output mutations remain outside the engineering service

Next Phase 2 slice:

1. extract `shared_breakline_audit` from `cmd_build_corridor.py` into a typed result service under `services/evaluation` or `services/builders`
2. preserve consumer coverage, missing constraint-edge, ownership, source-lineage, and diagnostic status decisions with focused contracts
3. keep document row collection and UI display mapping in review or presentation layers rather than the engineering audit service

Phase 2 Build Parametric extraction slice 12 completed on 2026-07-12:

- `SharedBreaklineAuditResult` and `SharedBreaklineAdjacencyResult` were introduced under `models/result`
- `SharedBreaklineAuditService` was introduced under `services/evaluation` as the active engineering audit path
- the service owns consumer boundary-ref coverage, constraint-segment coverage, TIN edge and chain coverage, direction reversal, geometry and mesh mismatch, source error propagation, and final audit status decisions
- solid-readiness adjacency evaluation now returns a typed result covering open ends, duplicate edges, reversed duplicates, non-manifold nodes, and tolerance-normalized node identity
- typed audit results preserve source result identity and audited consumer refs in addition to the legacy output fields
- `shared_breakline_audit` and `shared_breakline_adjacency_graph` remain Command compatibility adapters that return the existing dict contract for current preview and UI consumers
- document preview-row collection, review summary construction, task-panel display rows, and FreeCAD property writes remain outside the evaluation service
- contracts cover missing inputs, open ends, duplicate and reversed edges, missing consumer refs, matching mesh edges, solid-readiness warnings, source/consumer traceability, and Command adapter equivalence
- 11 existing shared-breakline audit regression tests passed
- one existing constraint-contract test still expects `warning` while both the prior legacy implementation and the extracted service return `ready`; this baseline expectation was not changed silently
- the updated Fast tier passed Compile, 6 architecture tests, and 156 focused v1 contracts
- changed-file Lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. remove the now-inactive legacy shared-breakline audit implementations and audit-only helper copies from `cmd_build_corridor.py` after confirming no remaining callers
2. introduce a presentation mapper for typed audit summary and preview metadata fields so UI code does not depend on engineering-result dict access
3. retain the legacy dict compatibility adapter only for remaining external and contract callers, then migrate those callers incrementally

Phase 2 Build Parametric extraction slice 13 completed on 2026-07-12:

- inactive legacy shared-breakline adjacency and audit implementations were removed from `cmd_build_corridor.py`
- audit-only constraint matching, boundary-chain matching, minimum-distance, graph-path, and proximity helper copies were removed after AST caller analysis
- boundary coverage, station projection, interval merge, and segment projection helpers still used by non-audit TIN constraint processing remain in place
- `SharedBreaklineAuditPresentation` and `SharedBreaklineAuditPresentationMapper` were introduced under `ui/presentation`
- the mapper accepts typed audit results and legacy mappings and produces stable summary text, note rows, counts, solid-readiness fields, and display status
- preview metadata attachment and summary formatting no longer read engineering audit dictionaries directly
- Command retains only the public legacy dict compatibility adapters for current external and contract callers
- contracts cover typed/legacy presentation equivalence, exact summary formatting, note-row normalization, Command summary compatibility, and removal of inactive legacy audit symbols
- focused legacy-audit-removal and presentation validation passed 24 tests
- all 11 non-stale existing shared-breakline audit regression tests passed
- the updated Fast tier passed Compile, 6 architecture tests, and 158 focused v1 contracts
- changed-file Lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Phase 2 shared-breakline audit extraction completed on 2026-07-12:

- engineering audit decisions live in `services/evaluation`
- durable audit contracts live in `models/result`
- preview/display conversion lives in `ui/presentation`
- Command owns compatibility routing and FreeCAD property mutation only

Next Phase 2 slice:

1. freeze `_build_intersection_surface_patch_tin` inputs, output TIN contract, quality rows, fallback decisions, and diagnostics
2. introduce typed Intersection surface patch build request/result contracts under `services/builders` while consuming accepted Intersection and Applied Section results
3. keep document discovery, source-result selection, preview mapping, FreeCAD persistence, and review-object creation in Command and presentation layers

Phase 2 Build Parametric extraction slice 14 completed on 2026-07-12:

- `IntersectionSurfacePatchBuildRequest` was introduced under `services/builders`
- `IntersectionSurfacePatchBuildResult` was introduced under `models/result`
- `IntersectionSurfacePatchBuildService` now defines the typed orchestration boundary for Intersection patch build attempts
- the typed result carries surface and Intersection identity, the built TIN, vertex/triangle/quality counts, boundary source, triangulation mode, fallback status, normalized diagnostics, and original error text
- convex-hull fallback is exposed explicitly as `fallback_used` with a stable diagnostic row rather than requiring callers to parse TIN quality rows
- the primary Intersection preview and the daylight height-clip reference build now consume the typed service boundary
- Command failure adaptation preserves the existing preview diagnostic prefix and original builder exception text
- document discovery, accepted result selection, Intersection source loading, preview mapping, persistence, review objects, and downstream TIN post-processing remain outside the typed service
- the current 309-line `_build_intersection_surface_patch_tin` remains as an injected compatibility implementation for incremental domain extraction; the service does not import Command
- contracts cover exact request forwarding, ready result metadata, quality extraction, convex-hull fallback, missing-builder status, typed failures, and Command result adaptation
- focused typed builder and architecture validation passed 19 tests
- structured-strip triangulation and grading-plane elevation regression validation passed 2 tests
- one existing full preview test expects `structured_strip_curb_return_blend` while the current builder result is `ear_clip`; this baseline expectation was not changed during typed-boundary extraction
- the updated Fast tier passed Compile, 6 architecture tests, and 163 focused v1 contracts
- changed-file Lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. extract non-roundabout Intersection patch section selection, six-decimal FG vertex deduplication, source refs, and superelevation-context preparation from the compatibility builder
2. introduce a typed patch-input preparation result consumed by the existing triangulation and boundary-selection stages
3. preserve roundabout dispatch, grading policy, fallback behavior, quality rows, and Command compatibility while reducing the legacy builder incrementally

Phase 2 Build Parametric extraction slice 15 completed on 2026-07-12:

- `IntersectionPatchInputPreparationRequest` and `IntersectionPatchInputPreparationService` were introduced under `services/builders`
- `IntersectionPatchInputPreparationResult` and `IntersectionPatchSuperelevationContext` were introduced under `models/result`
- the service consumes accepted Applied Sections, the evaluated prerequisite result, and optional Intersection source context without FreeCAD document or preview access
- control-area and active-Intersection section selection, station ordering, per-Alignment center-nearest selection, primary/secondary target stations, and control-area range fallback now live in the preparation service
- FG vertex creation preserves point-row source indices, Alignment/station/Region notes, original XYZ values, sequential vertex IDs, and six-decimal XY first-source deduplication
- duplicate XY count is now explicit in the typed preparation result
- superelevation source and transition counts, left/right extrema, and summary text now use a typed context contract
- the compatibility TIN builder consumes prepared sections, vertices, control refs, and typed superelevation context instead of rebuilding those inputs locally
- the existing fewer-than-three unique FG point error text and diagnostic kind remain unchanged
- roundabout dispatch remains before the non-roundabout preparation service and is unaffected
- contracts cover target-station section selection, station ordering, source point indices, trace notes, six-decimal deduplication, first-source Z retention, typed superelevation context, and the insufficient-point error contract
- focused typed preparation and architecture validation passed 15 tests
- structured-strip, grading-plane elevation, and elevation-source-note regression validation passed 3 tests
- the updated Fast tier passed Compile, 6 architecture tests, and 167 focused v1 contracts
- changed-file Lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. extract non-roundabout Intersection grading policy selection, grading-plane calculation, vertex Z application, and maximum Z-delta diagnostics into a typed builder/evaluation service
2. preserve `use_normal_superelevation`, flattening, plane-fit, elevation-source notes, and existing policy defaults with focused contracts
3. keep boundary selection, triangulation, roundabout grading, quality-row assembly, and Command compatibility unchanged during this grading extraction

Phase 2 Build Parametric extraction slice 16 completed on 2026-07-12:

- `IntersectionPatchGradingRequest` and `IntersectionPatchGradingService` were introduced under `services/evaluation`
- `IntersectionPatchGradingResult` was introduced under `models/result`
- active grading policy selection now ignores disabled rows, matches Intersection identity, and returns the first accepted source policy
- grading mode normalization preserves `flatten_intersection`, `keep_primary_crown`, `blend_primary_side`, and `use_normal_superelevation`; unknown or missing modes resolve to normal superelevation
- flattening preserves the arithmetic-mean Z rule and grading note suffix
- primary-crown mode preserves vertex Z while adding the existing trace note
- primary/side blending preserves least-squares plane fitting, `1.0e-12` singularity handling, plane-based Z evaluation, and the primary-mean fallback when a plane cannot be fitted
- plane-unavailable and primary-missing fallback decisions are now explicit typed diagnostics
- the typed result carries the selected source policy, normalized mode, graded vertices, grading plane, maximum Z delta, and diagnostic rows
- the compatibility TIN builder now consumes the typed grading result and writes its maximum Z delta directly to the existing quality contract
- Command grading helper names remain compatibility wrappers over the evaluation service
- unused Command-local plane-fit, 3x3 solver, and maximum-delta implementations were removed after caller analysis
- contracts cover policy selection, disabled policies, unknown modes, normal preservation, flattening, plane fitting, grading notes, singular-plane fallback, primary preservation, side blending, and maximum Z delta
- focused typed grading and architecture validation passed 15 tests
- existing grading policy and grading-plane regression validation passed
- the updated Fast tier passed Compile, 6 architecture tests, and 172 focused v1 contracts
- changed-file Lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. extract non-roundabout Intersection boundary-source selection into a typed service that consumes evaluated patch-boundary and authoritative boundary-loop results
2. preserve authoritative-loop priority, ordered-patch fallback, convex-hull fallback, grading-plane boundary elevation, source notes, and boundary diagnostic counts
3. keep tie-in/boundary contract evaluation, triangulation, roundabout behavior, final TIN quality assembly, and Command compatibility unchanged during boundary selection extraction

Phase 2 Build Parametric extraction slice 17 completed on 2026-07-13:

- `IntersectionPatchBoundarySelectionRequest` and `IntersectionPatchBoundarySelectionService` were introduced under `services/builders`
- `IntersectionPatchBoundarySelectionResult` was introduced under `models/result`
- the service consumes evaluated patch-boundary rows, authoritative boundary-loop rows, graded source vertices, and optional grading-plane context without accessing FreeCAD documents or preview geometry
- boundary selection now has an explicit priority contract: the largest ready closed outer Intersection boundary loop, then a closed ordered patch boundary, then the source-vertex convex hull fallback
- authoritative-loop selection preserves area-descending and loop-ID tie-breaking, explicit closure removal, six-decimal XY deduplication, stable loop point refs, and loop point/segment trace counts
- ordered patch-boundary selection preserves source segment, source kind, nearest evaluated elevation source, source notes, and patch topology/diagnostic metrics
- grading-plane elevation remains authoritative for both loop and patch boundary vertices and retains the existing `intersection_grading` and `blend_basis` trace notes
- the legacy authoritative-loop zero-elevation fallback rule is preserved explicitly: a zero nearest-source Z falls back to the loop row Z, while ordered patch rows continue to accept an evaluated zero Z
- convex-hull use and insufficient unique boundary points are exposed as typed fallback and error diagnostics
- the non-roundabout compatibility TIN builder consumes the typed selection result and keeps final TIN quality-row names and values unchanged
- Command boundary helper names remain compatibility wrappers over the builder service; no document, UI, or output mutation moved into the service
- contracts cover authoritative-loop priority, loop closure and deduplication, ordered-boundary traceability and metrics, grading-plane elevation, zero-elevation compatibility, convex-hull fallback, source-object retention, and typed insufficient-point failure
- focused new and existing boundary/grading regression validation passed 23 tests
- the updated Fast tier passed Compile, 6 architecture tests, and 178 focused v1 contracts
- changed-file Lint, Command critical lint, and `git diff --check` passed
- CI remains unchanged and frozen

Next Phase 2 slice:

1. extract non-roundabout Intersection triangulation selection into a typed builder service consuming the selected boundary, evaluated tie-in/boundary contracts, center vertex, and triangulation policy
2. preserve authoritative-loop ordered-polygon priority, structured-strip preference for other boundaries, ordered-polygon fallback, quality metrics, degeneracy errors, and boundary-strategy diagnostics
3. keep tie-in/boundary contract evaluation, shared-breakline constraint application, roundabout behavior, final TIN quality assembly, preview persistence, and Command compatibility unchanged during triangulation extraction

Phase 2 Build Parametric extraction slice 18 completed on 2026-07-13:

- `IntersectionPatchTriangulationRequest` and `IntersectionPatchTriangulationService` were introduced under `services/builders`
- `IntersectionPatchTriangulationResult` was introduced under `models/result`
- the request carries the accepted boundary source and vertices, center vertex, evaluated tie-in and boundary-segment contracts, Intersection source context, Intersection identity, and resolved triangulation policy
- authoritative boundary loops route directly to ordered-polygon triangulation without attempting structured strips
- other non-roundabout boundaries attempt structured-strip triangulation first and use ordered-polygon triangulation only when the structured result contains no usable triangles
- the selected path is explicit as `ordered_polygon_authoritative`, `structured_strip`, or `ordered_polygon_fallback`; ordered fallback is also exposed as a typed diagnostic and `fallback_used` flag
- the typed result normalizes output vertices and triangles, degeneracy counts, long-edge policy and measurements, boundary strategy, structured-strip count, curb-return sampling and blend counts, and boundary-role counts
- the existing insufficient-triangle error wording remains unchanged and is now returned through a typed error result before the Command compatibility builder restores the existing exception flow
- injected structured-strip and ordered-polygon implementations preserve the current geometry algorithms during this selection-only extraction; the builder service does not import Command
- the compatibility TIN builder now consumes typed triangulation fields directly when assembling existing TIN quality rows
- shared-breakline constraint application, shape-quality evaluation, final TIN assembly, roundabout dispatch, preview persistence, and UI review properties remain outside this service
- contracts cover authoritative routing, exact request forwarding, structured-strip priority, full metric normalization, ordered fallback, typed degeneracy failure, missing-builder status, and exception-message preservation
- 4 existing structured-strip, curb-return, and ordered long-edge-policy geometry regressions passed unchanged
- the updated Fast tier passed Compile, 6 architecture tests, and 184 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. move the ordered-polygon triangulation implementation and its long-edge policy metrics from Command into `IntersectionPatchTriangulationService`
2. preserve ear-clipping priority, centroid fan fallback, triangle IDs and trace notes, degeneracy tolerance, boundary edge metrics, and existing quality values with direct service contracts
3. keep structured-strip construction as an injected compatibility implementation, and keep shared-breakline processing, final TIN assembly, roundabout behavior, preview persistence, and UI review outside the service

Phase 2 Build Parametric extraction slice 19 completed on 2026-07-13:

- ordered-polygon triangulation now lives in `IntersectionPatchTriangulationService` and consumes the previously extracted pure geometry primitives for ear clipping, XY distance, and signed triangle area
- the service uses the internal ordered implementation by default; an optional injected implementation remains available only as a narrow compatibility and test seam
- the non-roundabout compatibility TIN builder no longer injects a Command-owned ordered-polygon implementation
- the Command `_intersection_patch_ordered_polygon_triangulation` name remains as a thin compatibility wrapper over the builder service
- counter-clockwise and clockwise ear-clipping output continues to use deterministic geometry-service indices
- triangle IDs, vertex refs, `intersection_surface_patch` kind, `ordered_polygon` quality refs, six-decimal area notes, and the `1.0e-6` degeneracy tolerance remain unchanged
- when ear clipping cannot produce indices, centroid fan fallback preserves `ordered_fan_fallback`, center vertex ownership, triangle ordering, trace notes, and per-edge degeneracy counts
- boundary edge maximum length, average-derived limit, explicit maximum-length policy override, minimum long-edge factor of `1.0`, and strict greater-than long-edge counting remain unchanged
- direct contracts cover stable ear-clip trace rows, centroid fan fallback, fully degenerate fan counting, default internal-builder routing, and the typed selection result
- the existing Command long-edge policy regression and 3 structured-strip/curb-return regressions passed unchanged
- the updated Fast tier passed Compile, 6 architecture tests, and 188 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. move structured-strip triangulation and its cohesive tie-in strip, overlap-cut, curb-return surface-part, vertex-source, and boundary-role helper cluster from Command into `IntersectionPatchTriangulationService`
2. preserve primary/secondary Alignment selection, source-elevation transfer, polygon cleanup, ear-clipping and quadrilateral fallback, triangle trace rows, curb-return sampling metrics, and boundary-strategy values
3. retain Command compatibility wrappers as needed, and keep boundary-contract evaluation, shared-breakline processing, final TIN assembly, roundabout behavior, preview persistence, and UI review outside the service

Phase 2 Build Parametric extraction slice 20 completed on 2026-07-13:

- structured-strip triangulation and its active helper cluster now live in `IntersectionPatchTriangulationService`
- the non-roundabout compatibility TIN builder now uses the service's internal structured-strip implementation and no longer injects a Command-owned implementation
- tie-in edges are normalized into boundary-segment rows and grouped by Alignment inside the service
- explicit primary Alignment selection remains source-driven through the matching Intersection row; missing or unavailable primary refs preserve first-participating-Alignment fallback
- tie-in strip candidate ordering, duplicate removal, counter-clockwise normalization, six-decimal XY vertex identity, `1.0e-6` polygon validity tolerance, secondary overlap-cut construction, and self-crossing rejection remain unchanged
- nearest accepted source-vertex Z transfer remains active for generated structured-strip vertices, including the existing zero-Z fallback behavior and stable structured-strip source refs and notes
- curb-return chord sampling, `0.58` inner blend interpolation, blend quadrilateral and core construction, sample and segment counts, and edge-blend face counts now reside in the service
- structured surface parts preserve ear-clipping priority, quadrilateral index fallback, triangle IDs, quality roles, surface-part trace notes, and degeneracy counts
- pavement tie-in, stem tie-in, overlap cut, and curb-return role counts and summary ordering are normalized by the service
- `structured_strip_union`, `structured_strip_curb_return`, and `structured_strip_curb_return_blend` boundary-strategy values remain unchanged
- empty structured results preserve source vertices plus center, ordered-polygon strategy, normalized long-edge policy defaults, and ordered fallback behavior
- Command retains thin compatibility wrappers for structured triangulation and shared tie-in, curb-return, overlap-cut, interpolation, and role helpers used by existing exclusion and contract callers
- direct contracts cover internal structured routing, source elevation, source refs, role metrics, explicit long-edge policy, and policy-aware empty results
- 7 existing structured-strip, skew/wide-radius curb-return, exclusion-footprint, exterior-hull, and tie-in normalization regressions passed unchanged
- the updated Fast tier passed Compile, 6 architecture tests, and 190 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. extract post-constraint Intersection patch shape-quality evaluation into a typed result service consuming final TIN vertices and triangles
2. preserve triangulation-mode classification, bounding-box dimensions and aspect ratio, minimum normalized triangle quality, the `0.08` skinny threshold, and missing-vertex handling
3. keep shared-breakline constraint mutation, drainage hints, final TIN quality-row assembly, roundabout behavior, preview persistence, and UI review outside the quality service

Phase 2 Build Parametric extraction slice 21 completed on 2026-07-13:

- `IntersectionPatchShapeQualityRequest` and `IntersectionPatchShapeQualityService` were introduced under `services/evaluation`
- `IntersectionPatchShapeQualityResult` was introduced under `models/result`
- the service consumes final TIN vertices and triangles only and has no FreeCAD document, preview, Command, or UI dependency
- the non-roundabout compatibility builder now invokes the typed service after shared-breakline constraint application and consumes typed quality fields directly during final TIN quality-row assembly
- triangulation-mode precedence remains `structured_strip_curb_return_blend`, `structured_strip_curb_return`, `structured_strip`, `fan_fallback`, then `ear_clip`
- quality-ref mode detection remains independent of vertex resolution so missing triangle vertices do not erase the selected triangulation mode
- bounding-box X/Y spans include all supplied final vertices; aspect ratio preserves the `1.0e-9` minimum-axis guard and zero result for a collapsed axis
- normalized triangle quality reuses the extracted pure geometry service and preserves minimum-value selection
- skinny triangle counting preserves the strict less-than comparison and the default `0.08` threshold; the threshold is explicit in the typed request and result
- triangles with missing vertex refs remain excluded from numeric quality calculation and are now also exposed through typed missing-vertex counts and diagnostics
- empty inputs preserve the existing `ear_clip` mode and zero-valued legacy quality contract
- the Command `_intersection_patch_shape_quality` function remains a thin dict compatibility adapter for roundabout and existing external callers
- contracts cover all five existing mode classifications, bbox and aspect ratio, normalized quality, threshold behavior, missing-vertex handling, empty input, typed result identity, and Command mapping equivalence
- 5 existing structured-strip and slope-face quality regressions passed unchanged
- the updated Fast tier passed Compile, 6 architecture tests, and 199 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. extract the non-roundabout patch low-point and boundary-to-low flow review calculation into a typed evaluation result service
2. preserve the `0.001` low-point tolerance, first-candidate selection, source ref, elevated boundary filtering, average XY flow vector, and existing summary wording
3. keep accepted Drainage source ownership separate: the extracted calculation remains a result-only review hint and must not create or rewrite `DrainageModel` elements

Phase 2 Build Parametric extraction slice 22 completed on 2026-07-13:

- `IntersectionPatchDrainageReviewRequest` and `IntersectionPatchDrainageReviewService` were introduced under `services/evaluation`
- `IntersectionPatchDrainageReviewResult` was introduced under `models/result`
- the typed result explicitly declares `result_only_review_hint` source scope and does not create, modify, or imply accepted `DrainageModel` elements
- the service consumes evaluated patch boundary vertices and the current patch vertex set only; it has no document, preview, UI, Command, or Drainage source-writing dependency
- empty inputs preserve zero-valued low-point and flow fields and the exact `no intersection patch vertices` summary while adding a typed empty diagnostic
- low-point elevation selection preserves the minimum evaluated Z, the default `0.001` tolerance, and first-candidate ordering
- the selected low point preserves XYZ coordinates and source point ref
- boundary flow sources preserve the strict `z > low_z + tolerance` filter so rows exactly at the tolerance boundary remain excluded
- average boundary-to-low X/Y vectors preserve the existing arithmetic mean and three-decimal summary formatting
- flat or near-flat boundaries preserve the exact `boundary_to_low count=0; patch appears flat at low-point tolerance` summary
- the low-point tolerance is explicit in the typed request/result and is clamped to a nonnegative value
- the non-roundabout compatibility builder consumes typed drainage review fields directly when assembling the existing TIN quality rows
- `_intersection_patch_drainage_hint` remains a thin dict compatibility adapter for existing external callers
- contracts cover empty input, result-only scope, first-candidate selection, tolerance candidate grouping, strict elevated-boundary filtering, average vectors, flat summaries, `None` filtering, custom tolerance behavior, and Command mapping equivalence
- the updated Fast tier passed Compile, 6 architecture tests, and 205 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. extract non-roundabout Intersection patch boundary-context orchestration into a typed builder/evaluation service covering tie-in edges, boundary segments, ordered patch boundary, authoritative boundary loops, and shared-breakline results
2. preserve evaluation order, accepted Applied Section and Intersection inputs, partial-result visibility, boundary diagnostic counts, failure text, and compatibility evaluator behavior
3. keep the current evaluator implementations behind injected compatibility seams initially, and keep boundary selection, triangulation, constraint mutation, final TIN assembly, document access, preview persistence, and UI review outside the context service

Phase 2 Build Parametric extraction slice 23 completed on 2026-07-13:

- `IntersectionPatchBoundaryContextRequest` and `IntersectionPatchBoundaryContextService` were introduced under `services/builders`
- `IntersectionPatchBoundaryContextResult` was introduced under `models/result`
- the service owns the ordered non-roundabout evaluation chain: tie-in edges, boundary segments, ordered patch boundary, authoritative boundary loops, then shared breaklines
- accepted Applied Sections, prerequisite result, and optional Intersection source model are forwarded unchanged to the compatibility evaluators
- evaluator dependencies are injected; the service does not import Command or UI and reports a typed `unsupported` result when any required evaluator is missing
- successful results preserve every evaluated contract, completed-stage order, Intersection identity, boundary-loop diagnostics, and shared-breakline result
- failures no longer discard the original exception: the typed result records the failed stage, completed stages, all available partial results, loop diagnostics, exception type, and original message
- programming failures return typed `error` results and are not converted into successful empty contexts
- the compatibility TIN builder consumes the typed partial context and preserves the existing downstream boundary selection and convex-hull fallback behavior when no patch boundary is available
- triangulation now receives the typed tie-in and boundary-segment partial results directly rather than relying on `locals()` inspection
- boundary selection, structured/ordered triangulation, shared-breakline constraint mutation, shape quality, final TIN assembly, document access, preview persistence, and UI review remain outside the context service
- contracts cover exact stage order and request forwarding, all five stage failures, partial-result visibility, failed-stage diagnostics, loop diagnostic retention, successful identity propagation, and missing-evaluator reporting
- focused boundary-context, boundary-selection, triangulation, and architecture validation passed 31 tests
- 3 existing ordered-boundary and shared-breakline result regressions passed
- one broader direct shared-breakline regression currently expects `curb_return_to_slope_face` consumer refs `("intersection_surface", "slope_face_surface")`, while the current evaluator returns a different consumer-ref contract; this baseline mismatch does not exercise the new context orchestration and was not changed silently
- the updated Fast tier passed Compile, 6 architecture tests, and 212 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. introduce a typed shared-breakline constraint build request/result service around post-triangulation Intersection TIN constraint application
2. preserve input vertex/triangle identity, constraint segment and edge counts, inserted vertex counts, boundary-loop refs and role summaries, snap counts and distances, diagnostics, and no-constraint pass-through behavior
3. keep the current constraint implementation behind an injected compatibility seam initially, and keep boundary-context evaluation, final shape-quality evaluation, TIN quality-row assembly, document access, preview persistence, and UI review outside the constraint service

Phase 2 Build Parametric extraction slice 24 completed on 2026-07-13:

- `IntersectionPatchConstraintBuildRequest` and `IntersectionPatchConstraintBuildService` were introduced under `services/builders`
- `IntersectionPatchConstraintBuildResult` was introduced under `models/result`
- the typed request carries the post-triangulation vertex and triangle rows, evaluated shared-breakline result, and target surface identity
- the compatibility constraint implementation is injected; the service does not import Command, UI, FreeCAD, or preview objects
- successful output normalizes constrained vertices and triangles, mode, constraint segment and edge counts, inserted vertex count, boundary-loop segment and edge counts, loop refs, role counts and summary, snap count, maximum snap distance, and snap diagnostics
- boundary-loop role counts are normalized as a stable sorted tuple and preserve the existing comma-separated positive-count summary
- no-constraint and partial-stat results preserve input rows and the existing `none`, zero, and empty defaults
- missing builders return typed `unsupported` results without losing input vertices or triangles
- implementation exceptions return typed `error` results with original input rows, exception type, and original message rather than a successful empty mesh
- the non-roundabout compatibility TIN builder consumes typed constraint rows and statistics directly before typed shape-quality evaluation
- existing final TIN quality-row names, units, loop-ref deduplication, role summary wording, and snap diagnostic joining remain unchanged
- contracts cover exact request forwarding, complete statistic normalization, stable role ordering, no-constraint pass-through, empty implementation rows, missing builder, and implementation failure
- focused constraint, boundary-context, and architecture validation passed 18 tests
- 3 existing endpoint insertion, snap, and boundary-loop role-summary regressions passed
- one broader regression completes constraint application but then calls the no-longer-present `_surface_boundary_edge_matches_shared_breakline` helper; this pre-existing test/helper mismatch is outside the typed constraint boundary and was not changed silently
- the updated Fast tier passed Compile, 6 architecture tests, and 217 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. move the active TIN shared-breakline constraint implementation and its cohesive edge identity, endpoint insertion, snap, existing-chain coverage, and support-triangle helper cluster from Command into the builder service layer
2. preserve six-decimal XYZ identity, snap tolerance and source-point protection, existing edge and edge-chain reuse, support vertex offset rules, triangle IDs and trace refs, and every typed statistic
3. retain thin Command compatibility wrappers for ordinary-road and existing direct callers, and keep boundary-context evaluation, final quality-row assembly, document access, preview persistence, and UI review outside the constraint implementation

Phase 2 Build Parametric extraction slice 25 completed on 2026-07-13:

- the active shared-breakline TIN constraint algorithm now lives in `IntersectionPatchConstraintBuildService`
- the service uses its internal implementation by default; an optional injected implementation remains only as a narrow compatibility and failure-test seam
- the non-roundabout Intersection builder no longer injects a Command-owned constraint implementation
- `_tin_rows_with_shared_breakline_constraint_edges` is now a thin Command compatibility wrapper used by ordinary-road surface and existing direct callers
- shared-breakline consumer filtering, ordered point lookup, segment counting, and boundary-loop source detection now execute in the builder service
- six-decimal XYZ vertex identity, existing vertex-ID edge identity, coordinate-edge reuse, and existing collinear edge-chain coverage remain unchanged
- edge-chain coverage preserves 3D station projection, `0.05` distance tolerance, `0.95` coverage threshold, endpoint coverage checks, one-percent interval gap tolerance, and diagonal-edge rejection
- missing endpoints preserve stable point vertex IDs, accepted source point refs, and shared-breakline trace notes
- near endpoint snap preserves the `0.05` tolerance, nearest-last tie behavior, one-snap-per-result-vertex rule, original source point ownership when present, snap distance notes, count, maximum distance, and diagnostics
- missing constraint edges preserve support-triangle generation, the `0.02` to `0.10` support offset clamp, sequential vertex and triangle IDs, constraint quality ref, and breakline source ref
- boundary-loop segment, edge, ref, and role statistics remain available through the typed result
- 11 inactive Command-local constraint helper copies were removed after AST caller analysis; general surface coverage helpers with other active consumers remain in Command
- direct contracts cover default internal routing, support vertex and triangle traceability, accepted source refs, boundary-loop statistics, and six-decimal coordinate-edge reuse
- 4 existing Intersection and ordinary-road endpoint insertion, snap, boundary-loop summary, and design-surface constraint regressions passed unchanged
- two broader existing tests expect reused coordinate and edge-chain constraints to report `edge_count=0`, while both the prior Command implementation and the migrated service count the preserved accepted edge as `1`; these baseline expectation mismatches were not changed silently
- the updated Fast tier passed Compile, 6 architecture tests, and 219 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. introduce a typed final non-roundabout Intersection TIN assembly request/result builder consuming prepared identity, selected boundary metrics, triangulation, constraint, grading, superelevation, drainage review, and shape-quality results
2. preserve every existing TIN source ref, boundary ref, quality-row name/value/unit, provenance row, fallback visibility, and result identity without reading documents or preview objects
3. keep roundabout builders separate, and keep document access, preview mapping, persistence, visibility, tree routing, and UI review outside the final TIN assembly service

Phase 2 Build Parametric extraction slice 26 completed on 2026-07-13:

- `IntersectionPatchTinAssemblyRequest` and `IntersectionPatchTinAssemblyService` were introduced under `services/builders`
- `IntersectionPatchTinAssemblyResult` was introduced under `models/result`
- the assembly request consumes explicit project, surface, Intersection, Corridor, Applied Section, and Region identity plus typed boundary selection, triangulation, constraint, grading, superelevation, drainage review, and shape-quality results
- the assembly service has no document, preview, FreeCAD, Command, or UI dependency
- the non-roundabout compatibility builder no longer constructs `TINSurface`, `TINQualityRow`, or `TINProvenanceRow` directly
- final surface kind, label fallback, source refs, constrained vertex and triangle rows, boundary ref, and result identity remain unchanged
- all 69 existing non-roundabout quality rows preserve their exact order, stable `surface_id:kind` IDs, kind names, values, and units
- boundary-loop constraint refs preserve first-seen deduplication and comma joining; snap diagnostics preserve semicolon joining
- boolean boundary metrics remain integer `0` or `1` with the existing `boolean` unit
- Applied Sections provenance preserves ID, source kind, source ref, sorted control-Region refs, and exact note wording
- invalid typed inputs return an assembly `error` result with exception type and original message rather than a partial successful TIN
- the Command compatibility builder converts a failed assembly result back into the existing exception path and returns the assembled TIN on success
- contracts exhaustively assert all 69 quality kind positions, quality IDs, representative values and units, source and boundary refs, provenance, typed failure behavior, and absence of direct final `TINSurface` assembly in the non-roundabout Command function
- the updated Fast tier passed Compile, 6 architecture tests, and 222 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. introduce a typed non-roundabout Intersection patch pipeline service that orchestrates boundary selection, centroid creation, drainage review, triangulation, shared-breakline constraints, shape quality, and final TIN assembly from prepared/grading/boundary-context results
2. preserve service call order, fallback diagnostics, stable centroid identity, all intermediate typed results, failure propagation, and final TIN contract
3. keep roundabout dispatch separate and retain current boundary evaluators behind compatibility seams until their engineering logic is migrated out of Command

Phase 2 Build Parametric extraction slice 27 completed on 2026-07-13:

- `IntersectionPatchPipelineRequest` and `IntersectionPatchPipelineService` were introduced under `services/builders`
- `IntersectionPatchPipelineResult` was introduced under `models/result`
- the service owns the post-context non-roundabout order: boundary selection, centroid, drainage review, triangulation, shared-breakline constraints, shape quality, then final TIN assembly
- the pipeline consumes graded vertices, grading plane/result, superelevation context, typed boundary context, explicit identity/counts, Intersection model context, and triangulation policy without reading documents or preview objects
- boundary selection preserves authoritative-loop, ordered-patch, and convex-hull priority and exposes its fallback diagnostic through the pipeline result
- centroid construction preserves `v:center`, arithmetic-mean XYZ, `surface_id:centroid` source ref, and exact note wording
- drainage review still executes from the selected boundary and boundary-plus-centroid rows before triangulation
- triangulation receives typed tie-in and boundary-segment partial results from boundary context and preserves ordered fallback diagnostics
- constraint, post-constraint quality, and final 69-row TIN assembly consume the exact typed outputs from the preceding stage
- the pipeline result retains every intermediate typed result, completed-stage order, failed stage, accumulated diagnostics, original error text, and final TIN
- boundary-selection and triangulation failures return typed partial pipeline results without attempting later stages
- the non-roundabout compatibility Command builder is reduced to 99 lines covering roundabout dispatch, input preparation, grading, boundary-context evaluator wiring, pipeline request assembly, and result adaptation
- contracts exercise the real default services through the complete seven-stage happy path, stable centroid identity, dual fallback diagnostics, final 69-row contract, insufficient boundary failure, degenerate triangulation failure, and partial-result visibility
- the updated Fast tier passed Compile, 6 architecture tests, and 225 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` are included in the completion check
- CI remains unchanged and frozen

Next Phase 2 slice:

1. introduce a typed non-roundabout preparation pipeline that orchestrates Applied Section input preparation, grading evaluation, boundary-context evaluation, and the existing post-context patch pipeline
2. preserve insufficient-FG diagnostics, grading policy and plane behavior, evaluator injection order, prepared control refs and superelevation context, partial results, and final TIN output
3. keep roundabout dispatch in Command and retain current tie-in/boundary/shared-breakline evaluator implementations behind explicit compatibility seams until migrated

Phase 2 Build Parametric extraction slice 28 completed on 2026-07-13:

- `IntersectionPatchPreparationPipelineRequest` and `IntersectionPatchPreparationPipelineService` were introduced under `services/builders`
- `IntersectionPatchPreparationPipelineResult` was introduced under `models/result`
- the service owns the non-roundabout preparation order: Applied Section input preparation, grading evaluation, boundary-context evaluation, then the existing post-context patch pipeline
- the request consumes explicit project, surface, corridor, Applied Section set, prerequisite, Intersection model, and triangulation-policy inputs without reading documents or generated preview geometry
- insufficient unique `fg_surface` input stops at `input_preparation` with the existing exact diagnostic and no later evaluation
- grading preserves the selected source policy, normalized mode, fitted plane, graded vertices, and missing-policy diagnostic before boundary evaluation
- the configured boundary evaluators retain the existing tie-in, boundary-segment, ordered-patch, authoritative-loop, and shared-breakline call order
- boundary-context errors remain typed partial results and still permit the existing convex-hull fallback path to produce a final TIN when sufficient accepted Applied Section vertices exist
- prepared control-region refs, source control refs, superelevation context, prerequisite counts, grading result, boundary-context partials, and triangulation policy are forwarded unchanged into the post-context pipeline
- the preparation result retains every stage result, completed-stage order, failed stage, accumulated diagnostics, original error text, and final TIN
- the non-roundabout compatibility Command builder is reduced from 99 lines to 50 lines and now covers only roundabout dispatch, compatibility evaluator injection, typed request assembly, and result adaptation
- contracts cover the real four-stage happy path, evaluator injection order, control-ref normalization, superelevation propagation, exact insufficient-FG failure, boundary-context failure with successful fallback, post-context failure, partial-result visibility, and final 69-row TIN contract
- the updated Fast tier passed Compile, 6 architecture tests, and 229 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` passed
- CI remains unchanged and frozen

Next Phase 2 slice:

1. introduce a typed tie-in edge evaluation service under `services/evaluation` and move the current non-roundabout `corridor_intersection_tie_in_edge_result` engineering implementation out of Command
2. preserve Applied Section selection, primary/secondary alignment handling, side-edge selection, projected tie-in geometry, source refs, deterministic row identity, status, counts, and diagnostics
3. keep a thin public Command compatibility wrapper and inject the service evaluator into the boundary-context preparation pipeline; leave boundary-segment, ordered-patch, authoritative-loop, and shared-breakline evaluators as the next explicit seams

Phase 2 Build Parametric extraction slice 29 completed on 2026-07-13:

- `IntersectionTieInEdgeEvaluationRequest` and `IntersectionTieInEdgeEvaluationService` were introduced under `services/evaluation`
- the service consumes accepted Applied Section results, typed prerequisite context, and optional Intersection source model context without reading documents, selections, UI state, or generated preview geometry
- the service now owns control-region and active-Intersection section filtering, deterministic station ordering, primary/secondary target-station resolution, exact-target bracketing, left/right FG point selection, and result-row construction
- target stations preserve Intersection primary and secondary station refs first, control-area range centers second, and the mean accepted Applied Section station as the final fallback
- deterministic tie-in identity, alignment and Region source refs, section refs, station spans, XYZ edge endpoints, `candidate` and `single_section_candidate` statuses, and target-station notes are preserved
- single-section candidates preserve tangent-directed synthetic edge generation, the 1.5-width or 8.0 minimum span policy, warning diagnostics, and non-blocking ready status
- missing alignment and missing FG edge diagnostics still produce the existing incomplete-count diagnostic and `warning` or `missing` aggregate status according to available rows
- `corridor_intersection_tie_in_edge_result` is reduced to a 15-line compatibility wrapper that only creates a typed request and invokes the service
- the non-roundabout preparation pipeline injects `IntersectionTieInEdgeEvaluationService.evaluate_context` directly into its ordered boundary-context chain
- the former tie-in section-pair, side-point, point-coordinate, lateral-offset, and single-section geometry implementations were removed from Command
- contracts cover primary and secondary side edges, deterministic row order and identity, exact-target bracketing, source geometry, single-section synthetic edges, warning behavior, missing alignment behavior, incomplete counts, the public wrapper, and direct preparation-pipeline service injection
- the updated Fast tier passed Compile, 6 architecture tests, and 234 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` passed
- CI remains unchanged and frozen

Next Phase 2 slice:

1. introduce a typed Intersection boundary-segment evaluation service under `services/evaluation` and move `corridor_intersection_boundary_segment_result` engineering logic out of Command
2. preserve tie-in segment mapping, Intersection-kind radius defaults, curb-return policy validation, arc/chord construction, source refs, row ordering, readiness status, counts, and diagnostics
3. keep a thin public Command compatibility wrapper and inject the new service evaluator into the boundary-context preparation pipeline; leave ordered-patch, authoritative-loop, and shared-breakline evaluators as the remaining explicit seams

Phase 2 Build Parametric extraction slice 30 completed on 2026-07-13:

- `IntersectionBoundarySegmentEvaluationRequest` and `IntersectionBoundarySegmentEvaluationService` were introduced under `services/evaluation`
- the service consumes an accepted tie-in edge result and optional Intersection source model context without reading documents, selection, UI state, or generated preview geometry
- the service now owns deterministic tie-in-to-boundary row mapping, Intersection source-row lookup, active curb-return policy selection, radius validation, Intersection-kind defaults, direction resolution, and boundary result assembly
- tie-in source refs, alignment refs, sides, endpoint XYZ rows, source status, notes, row order, and `boundary:<tie-in-id>` identity are preserved
- default curb-return radii remain 12.0 m for T intersections, 10.0 m for cross intersections, and 15.0 m for Y intersections
- disabled policy exclusion, non-positive and small-radius diagnostics, large-radius versus tie-in-span diagnostics, and non-blocking warning semantics are preserved
- primary and secondary tie-in direction resolution still normalizes accepted edge vectors and emits explicit axis-fallback diagnostics when a direction is unavailable
- T, cross, Y, and unknown-kind quadrant policies, 90-degree chord construction, policy-controlled sample count and spacing, 5-to-49 explicit sample clamping, endpoint-gap diagnostics, and deterministic arc identity are preserved
- arc rows retain policy source refs, source or derived center XYZ, radius, full chord-point rows, candidate status, kind/quadrant notes, and exact sample/segment counts
- incomplete tie-in coverage remains an engineering diagnostic that changes a non-empty result to `warning`; warning-prefixed radius and direction observations do not block `ready`
- `corridor_intersection_boundary_segment_result` is reduced to a 13-line compatibility wrapper that only creates a typed request and invokes the service
- the non-roundabout preparation pipeline injects `IntersectionBoundarySegmentEvaluationService.evaluate_context` directly after typed tie-in evaluation
- obsolete Command implementations for arc sample calculation, boundary-center averaging, tie-in direction resolution, chord generation, tie-in span, endpoint gap, and vector normalization were removed
- contracts cover traceable tie-in mapping, deterministic row and arc identity, T/cross/Y defaults and arc counts, policy source refs, source center, chord samples, invalid radius fallback, explicit sample clamping, incomplete coverage, direction fallback, large-radius warnings, the public wrapper, and direct preparation-pipeline service injection
- the updated Fast tier passed Compile, 6 architecture tests, and 242 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` passed
- CI remains unchanged and frozen

Next Phase 2 slice:

1. introduce a typed ordered Intersection patch-boundary evaluation service under `services/evaluation` and move `corridor_intersection_patch_boundary_result` engineering logic out of Command
2. preserve tie-in union priority, multi-ring role and identity handling, chord expansion, deterministic point ordering, polygon area, self-crossing checks, closed/readiness state, source refs, counts, and diagnostics
3. keep a thin public Command compatibility wrapper and inject the new service evaluator into the boundary-context preparation pipeline; leave authoritative boundary-loop and shared-breakline evaluators as the remaining explicit seams

Phase 2 Build Parametric extraction slice 31 completed on 2026-07-13:

- `IntersectionPatchBoundaryEvaluationRequest` and `IntersectionPatchBoundaryEvaluationService` were introduced under `services/evaluation`
- the service consumes the accepted boundary-segment result contract without reading documents, selections, UI state, or generated preview geometry
- the service now owns tie-in pavement-strip construction, two-or-more alignment strip-union priority, union failure fallback, ordered multi-ring expansion, result-row construction, area and topology diagnostics, and readiness assembly
- tie-in strip normalization preserves duplicate removal, CCW orientation, non-zero-area selection, self-crossing rejection preference, and deterministic largest-valid candidate selection
- a successful tie-in union preserves `tie_in_strip_union` boundary mode, union-specific point identity and source kind, outer-ring ownership, source tie-in count, source Z values, deterministic order, polygon area, and closed state
- union warnings remain visible and fall back to ordinary ordered segment rings when a valid union outer boundary cannot be produced
- segment role parsing still recognizes hole, void, opening, and island meanings; explicit role-based ring identity, source-ref fallback identity, and deterministic outer/hole/island ordering are preserved
- chord-point rows expand before ordinary segment endpoints, XY duplicates are removed at six-decimal identity, and each ring is ordered by angle around its arithmetic centroid
- point rows retain source segment refs, source segment kinds, ring refs, ring roles, global deterministic order, candidate status, and `patch-boundary:<intersection>:<ring>:<order>` identity
- multi-ring area preserves outer and island addition with hole subtraction and non-negative final clamping
- diagnostics preserve too-few points, zero-area rings, self-crossing rings, inner rings outside or intersecting the primary outer ring, intersecting inner rings, source diagnostics, and aggregate zero-area/self-crossing state
- the largest-area outer ring remains the containment reference when multiple outer rings are present
- `corridor_intersection_patch_boundary_result` is reduced to a 10-line compatibility wrapper that only creates a typed request and invokes the service
- the non-roundabout preparation pipeline injects `IntersectionPatchBoundaryEvaluationService.evaluate_context` directly after typed boundary-segment evaluation
- former Command implementations for tie-in union assembly, ring role and identity, angular ordering, signed and multi-ring area, containment diagnostics, primary outer selection, and ring centroid calculation were removed
- pure Command polygon-topology compatibility wrappers remain for existing callers, but the new engineering service consumes the geometry services directly
- contracts cover tie-in union priority and identity, deterministic ordering, source Z and refs, hole preservation and subtraction, outside-hole diagnostics, source-diagnostic propagation, zero-area rejection, the public wrapper, and direct preparation-pipeline service injection
- the updated Fast tier passed Compile, 6 architecture tests, and 247 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` passed
- CI remains unchanged and frozen

Next Phase 2 slice:

1. introduce a typed authoritative Intersection boundary-loop evaluation service under `services/evaluation` and move `_intersection_boundary_loop_result_for_shared_breaklines` orchestration out of Command
2. preserve topology, edge-network, surface-zone, slope-face-loop, and final boundary-loop evaluation order; Intersection filtering; Applied Section context; diagnostics; and explicit missing-model behavior
3. inject the new service evaluator into the boundary-context preparation pipeline and keep only a thin compatibility wrapper if required; leave shared-breakline evaluation as the final explicit Command seam in this chain

Phase 2 Build Parametric extraction slice 32 completed on 2026-07-13:

- `IntersectionBoundaryLoopEvaluationRequest` and `IntersectionBoundaryLoopEvaluationService` were introduced under `services/evaluation`
- `IntersectionBoundaryLoopEvaluationChainResult` was introduced under `models/result`
- the service consumes accepted Applied Section results, typed prerequisite context, and optional Intersection source model context without reading documents, selections, UI state, or generated preview geometry
- the service now owns the authoritative chain order: topology, edge network, surface zones, slope-face loops, then boundary loops
- each stage receives the exact preceding typed result contracts and the final boundary-loop call preserves accepted Applied Section context and explicit Intersection ID filtering
- the chain result retains every intermediate typed result, completed-stage order, failed stage, diagnostics, original error text, and final boundary-loop result
- missing Intersection model context returns typed `missing` at `input_validation`, preserves the exact `intersection_boundary_loop_model_missing` diagnostic, and does not execute downstream evaluation
- evaluation exceptions return typed `error`, preserve already completed intermediate results, identify the exact failed stage, and retain the existing `intersection_boundary_loop_evaluation_failed:<message>` compatibility diagnostic
- the boundary-context adapter appends typed diagnostics to the caller-provided loop diagnostic list and returns only the accepted boundary-loop result expected by the existing chain
- the non-roundabout preparation pipeline injects `IntersectionBoundaryLoopEvaluationService.evaluate_context` directly after ordered patch-boundary evaluation
- `_intersection_boundary_loop_result_for_shared_breaklines` remains as a 15-line compatibility wrapper because existing shared-breakline and exclusion-boundary callers still use it; it contains no engineering evaluation logic
- contracts cover exact evaluation order and arguments, every intermediate result, Intersection filtering, missing-model short-circuit, partial-result preservation on failure, exact diagnostics, adapter behavior, direct preparation-pipeline injection, and the thin compatibility wrapper
- the updated Fast tier passed Compile, 6 architecture tests, and 252 focused v1 contracts
- changed-file Lint and Command critical lint passed; repository-wide `F821` and `git diff --check` passed
- CI remains unchanged and frozen

Next Phase 2 slice:

1. introduce typed shared-breakline evaluation request and result-assembly boundaries under `services/evaluation` as the first migration slice for `corridor_intersection_shared_breakline_result`
2. move authoritative boundary-loop and ordered patch-boundary breakline contribution, deterministic point/breakline identity, source refs, consumer refs, duplicate handling, counts, and diagnostics out of Command first
3. keep tie-slope, slope-face, curb-return bridge, drainage, and other remaining contributors behind explicit injected compatibility seams; retain a thin public Command wrapper until those contributors are migrated in subsequent slices

Phase 2 Build Parametric extraction slice 33 completed on 2026-07-13:

- `IntersectionSharedBreaklineContributionRequest`, `IntersectionSharedBreaklineAssemblyRequest`, and `IntersectionSharedBreaklineService` were introduced under `services/evaluation`
- `IntersectionSharedBreaklineContributionResult` was introduced under `models/result`
- authoritative boundary-loop, patch-to-design contact, and roundabout ordinary-surface clip contributors now build typed point, breakline, source-ref, consumer-ref, handoff, status, and diagnostic rows outside Command
- boundary-loop contribution preserves accepted-loop filtering, segment refs, reversed-edge deduplication, stable shared IDs, canonical roles, expected consumers, and missing/degenerate diagnostics
- patch contribution preserves primary pavement versus secondary stem roles, per-contact identity, broad fallback and boundary-loop suppression, and source contract lineage
- roundabout clip contribution preserves approach, subgrade, and slope handoff roles, closed-loop filtering, edge deduplication, collision-safe IDs, exact diagnostics, and ordinary-surface-only consumers
- final Intersection shared-breakline status and ready/warning/error counts are assembled by the typed service
- Command retains only a thin boundary-loop compatibility wrapper for direct legacy contract callers; inactive patch and roundabout contributor implementations were removed
- focused contributor, graph compatibility, and FreeCAD roundabout guardrail tests passed; the updated Fast tier passed Compile, 6 architecture tests, and 256 focused v1 contracts
- CI remains unchanged and frozen

Next Phase 2 slice:

1. migrate curb-return bridge and tie-slope shared-breakline contributors into the typed shared-breakline service
2. preserve window ordering, canonical roles, source and consumer refs, contact-cap identity, diagnostics, and result row order
3. then migrate slope-face, control-area, drainage, and upper-panel contributors before reducing the public Command evaluator to request assembly and compatibility adaptation

Phase 2 Build Parametric extraction slice 34 completed on 2026-07-13:

- diagnostic curb-return bridge, source-owned tie-slope, and Applied Section tie-slope window contributors moved into `IntersectionSharedBreaklineService`
- curb bridge parsing preserves diagnostic group identity, XY sample parsing, reversed-segment deduplication, stable point refs, diagnostic status, consumers, and count diagnostics
- source-owned tie-slope rows preserve inner, outer, start-cap, and end-cap roles, supplied or deterministic fallback IDs, source lineage, consumers, and ready-row filtering
- window rows preserve ownership suppression, blocking-diagnostic filtering, default, curb-return approach, supplemental, and endpoint role selection, station spans, accepted source refs, and exact accepted/suppressed counts
- Command tie-slope and curb bridge helpers are now compatibility wrappers; their engineering implementations and window edge-spec tables were removed from Command
- focused contributor and compatibility tests passed; the updated Fast tier passed Compile, 6 architecture tests, and 258 focused v1 contracts
- CI remains unchanged and frozen

Next Phase 2 slice:

1. migrate slope-face boundary, local clip-cap, curb-return contact, and main/side slope-face seam contributors into typed services
2. migrate control-area, drainage-handoff, upper-panel, and profile-ref enrichment contributors
3. reduce `corridor_intersection_shared_breakline_result` to typed request assembly and contributor orchestration, then begin preview/presentation extraction

Phase 2 Build Parametric extraction slice 35 completed on 2026-07-13:

- all remaining Intersection shared-breakline contributors moved into `IntersectionSharedBreaklineService`
- slope-face local clip caps, curb-return contacts, main/side seams, control-area rows, drainage handoff rows, upper-panel rows, and profile-ref enrichment now assemble from typed result contracts outside Command
- `IntersectionSharedBreaklineEvaluationRequest` owns the complete contributor order and final assembly
- `corridor_intersection_shared_breakline_result` is a 97-line request/context adapter; compatibility helpers delegate to public typed service APIs
- the updated Fast tier passed Compile, 6 architecture tests, and 258 focused v1 contracts
- CI remains unchanged and frozen

Phase 2 Build Parametric extraction slice 36 completed on 2026-07-13:

- `IntersectionSlopeFaceBoundaryEvaluationService`, `IntersectionTieSlopeEvaluationService`, `IntersectionSlopeFaceCellEvaluationService`, and `IntersectionSharedBoundaryGraphEvaluationService` were introduced under `services/evaluation`
- the services consume Applied Sections and accepted Intersection/shared-breakline result contracts without reading documents, selections, UI state, or preview `Shape` geometry
- source-owned boundary candidates, station-separated tie-slope contracts, slope-face cells, canonical nodes, edges, cells, diagnostics, and graph audit are now evaluated outside Command
- public Command evaluators are reduced to typed compatibility wrappers of 15, 19, 13, and 13 lines respectively
- inactive engineering helper implementations were removed from Command while presentation helpers that still serve review/output behavior were preserved
- focused contracts cover missing context, roundabout generic-path suppression, source lineage, upper-cell subdivision, graph assembly, and boundary compatibility
- CI remains unchanged and frozen

Phase 2 Build Parametric extraction slice 37 completed on 2026-07-13:

- `BuildCorridorPreviewAdapter` was introduced under `ui/presentation` and now owns typed FreeCAD preview properties, stale preview cleanup, and diagnostic marker compound creation
- `BuildCorridorViewModel` now owns progress, summary, guided review, result, slope issue, Intersection contract, and shared-breakline presentation state
- `V1BuildCorridorTaskPanel` moved from `commands/cmd_build_corridor.py` to `ui/viewers/build_corridor_view.py`
- the UI module has no Command import; an explicit command/controller callback map preserves the existing workflow while keeping the dependency direction visible
- `cmd_build_corridor.py` no longer defines the task-panel class and retains command activation, request assembly, service calls, persistence routing, compatibility wrappers, and runtime callback registration
- architecture coverage now freezes UI ownership of the task panel and the required Phase 2 engineering service set
- presentation contracts cover ViewModel state, typed preview properties, result-coordinate markers, stale marker cleanup, and the UI-owned panel identity
- the completed Phase 2 Fast tier passed Compile, 7 architecture tests, and 268 focused v1 contracts
- targeted FreeCAD panel construction and progress-bar compatibility passed
- CI remains unchanged and frozen

Phase 2 Build Parametric extraction slice 38 closure audit completed on 2026-07-13:

- Roundabout surface generation, Roundabout ownership clipping, Intersection exclusion clipping, Intersection daylight TIN suppression, Intersection slope-face TIN generation, exclusion-boundary geometry, and shared-breakline TIN constraint assembly are owned by typed builder services
- `cmd_build_corridor.py` retains source/document context resolution, service request assembly, persistence routing, presentation mapping, and behavior-preserving compatibility wrappers; copied polygon clipping and TIN triangulation implementations were removed
- pure anchor-window and anchor-box segment clipping moved to `services/geometry`, with direct geometry contracts and Command-wrapper equivalence coverage
- architecture coverage freezes the new builder ownership, rejects FreeCAD/Part/Qt imports in the extracted engineering builders, limits named Command compatibility wrappers by size, and rejects reintroduction of removed implementation helpers
- direct builder contracts cover daylight height suppression, practical Intersection exclusion, shared-breakline edge reuse, Roundabout ownership clipping, and ready-loop slope-face TIN generation
- the final Phase 2 Fast tier passed Compile, 7 architecture tests, and 275 focused v1 contracts
- changed-file lint and `git diff --check` passed
- the non-gating legacy aggregate `test_build_corridor_command.py` run recorded 169 passed and 39 failed; the remaining failures include superseded preview facet/status expectations, UI panel expectations that predate the `ui/viewers` move, and retired Command-local helper expectations, and are not treated as a successful full-suite result
- CI remains unchanged and frozen; no CI workflow or additional CI development was added

Phase 2 Build Parametric extraction completed after closure audit on 2026-07-13:

- pure XY, polygon, and TIN algorithms are owned by `services/geometry` and typed builders
- general corridor surface orchestration and Intersection surface preparation are service-owned
- Intersection slope-face, tie-slope, shared-breakline, cell, and shared-boundary graph evaluation are service-owned
- shared-breakline audit is represented by typed result and presentation contracts
- FreeCAD preview property and diagnostic marker writes are presentation-adapter owned
- the Build Parametric task panel and its UI-independent ViewModel are owned by `ui/viewers`
- Command no longer owns polygon clipping, TIN triangulation, the Build Parametric task-panel class, or the extracted engineering evaluators
- the automatic Phase 2 completion gate is Compile plus the architecture and focused contract tiers recorded above; the legacy aggregate file remains recorded technical debt rather than a hidden pass
- Ramp remains removed, Watertight Solid development remains paused, and CI remains unchanged with additional CI development prohibited

Phase 2 user validation accepted on 2026-07-13:

- the user completed the focused FreeCAD 1.1.1 Build Parametric panel and Apply workflow validation
- Phase 2 is accepted as complete; remaining non-gating legacy aggregate-test, preview-detail, and UI-detail gaps may be handled as explicit follow-up maintenance
- deferred detail work must preserve the Phase 2 service, model, object, command, and presentation boundaries and must not restore retired Command-local engineering implementations

Phase 3 Editor extraction completed and accepted on 2026-07-13:

- Structure, Profile, SubAssembly Designer, Assembly/Subassembly, Drainage, Alignment, and TIN task-panel classes moved from `commands` to `ui/editors`
- Drainage Review task-panel ownership moved from `commands` to `ui/viewers/drainage_review_view.py`
- command modules retain activation, command registration, document-context assembly, persistence routing, and explicit runtime callback registration
- UI modules do not import Command modules; explicit runtime collaborator placeholders keep the dependency direction visible and lintable
- `editor_source_service.py` now provides UI-independent typed edit preparation, identity diagnostics, and view-model summaries for Structure, Profile, Alignment, Drainage, Assembly/Subassembly, and SubAssembly Library source models
- Profile and Alignment row-write compatibility functions now pass normalized rows through editing-service validation before persistence
- Structure, Drainage, Assembly/Subassembly, and SubAssembly Library Apply paths now pass typed source models through editing-service preparation before object-adapter persistence
- existing `TINEditService` remains the TIN source-edit owner
- architecture coverage rejects reintroduction of all Phase 3 task panels into Command and verifies their UI owners and editing-service package ownership
- direct UI-independent editor-source contracts, command-to-UI identity contracts, no-write-on-close Designer coverage, and the architecture/presentation gate passed: 13 tests
- changed Phase 3 files passed Compile, flake8, and `git diff --check`
- the existing Profile aggregate recorded 45 passed and 4 pre-existing expectation failures involving the retired `Starter Road` preset and a legacy vertical-curve length expectation
- the existing Subassembly aggregate recorded 10 passed and 1 pre-existing preview-text formatting expectation failure (`material=...` versus the current `material: ...`)
- the initial focused GUI and Fast-tier runs did not return because FreeCAD Python started QWidget tests without a `QApplication`; `scripts/run_pytest_with_qt.py` now provides a deterministic local Qt harness without changing CI
- the final reproducible local Fast tier passed Compile, 8 architecture tests, and 287 focused v1 contracts, including all Phase 3 editor-source and selected QWidget boundaries
- representative Phase 3 QWidget contracts passed 9 of 10 cases under the explicit Qt harness; the remaining non-gating failure is the existing Drainage header expectation (`Assembly`) versus the current UI label (`Subassembly`)
- no Ramp, Watertight Solid, or CI development was added; CI remains unchanged and additional CI development remains prohibited
- the user completed the focused FreeCAD 1.1.1 editor validation and accepted Phase 3
- remaining non-gating legacy expectation and UI-label details may be handled as explicit follow-up maintenance without reopening the completed editor boundaries

Phase 4 Persistence and incremental rebuild completed on 2026-07-13:

- `V1_PERSISTENCE_SCHEMA_INVENTORY.md` records the active complex-property inventory, typed payload authority, compatibility fallback rule, migration policy, incremental metadata, and excluded scope
- payload envelope schema 2 stores canonical typed data, model type and schema, counted row families, required refs, checksum, and source/result fingerprint
- schema 1 to 2 migration is explicit and registered; newer unsupported payload schemas and missing migration steps are rejected
- embedded checksum, separate FreeCAD checksum, fingerprint, model type, row counts, and required refs are validated during restore
- a present malformed payload produces typed persistence diagnostics and is not silently replaced by compatibility-property data
- old documents with no typed payload continue through the existing readable FreeCAD property adapters
- Structure, Drainage, SubAssembly Library, Assembly/Subassembly, and Region source objects write typed payloads
- Applied Sections, Corridor, and Surface result objects write typed payloads and incremental result metadata
- nested numeric Subassembly parameters and overrides now preserve their typed numeric values through the typed payload instead of being converted to compatibility strings
- incremental records expose stage, service version, input/result fingerprints, consumed source/result refs, accepted state, duration, changed stages, and stale reasons
- presentation-only visibility and style fields are excluded from engineering fingerprints; unchanged accepted result persistence is reused without resetting presentation state
- Build Parametric batches Corridor and Surface persistence plus preview application in one document transaction with one final recompute
- an interrupted stage builder does not replace the previous accepted record, and a failed document transaction aborts without recompute
- FreeCAD 1.1.1 save/reopen coverage verifies Structure and Assembly source refs, Corridor result refs, station rows, fingerprints, and accepted incremental metadata
- existing exchange-package chunked-payload save/reopen coverage verifies output refs and large normalized output payload survival without expanding exchange behavior
- serializer, corruption, migration, incremental, transaction, save/reopen, and output persistence focus passed 16 tests
- the six migrated source/result object contract files passed 27 tests
- the final Phase 4 Fast tier passed Compile, 8 architecture tests, and 297 focused v1 contracts
- changed Phase 4 Python files passed flake8 and `git diff --check`
- the non-gating legacy aggregate `test_build_corridor_command.py` remains at 169 passed and 39 failed, matching the recorded Phase 2 technical-debt result rather than being represented as a successful full-suite run
- Ramp remains removed, Watertight Solid development remains paused, and CI remains unchanged with additional CI development prohibited

Phase 5 automated supported-domain stabilization completed on 2026-07-13; user manual acceptance is pending:

- `V1_SUPPORTED_DOMAIN_STATUS.md` is the single current-scope index for supported, review-only, removed, and paused domains
- the status index records source owners, evaluated/result owners, output/review boundaries, exclusions, runtime policy, document classification, and precedence
- package compatibility remains FreeCAD 1.0.3, while recommended, development, and validated runtime is FreeCAD 1.1.1 with Python 3.10+
- `V1_PHASE5_SUPPORTED_DOMAIN_MANUAL_QA.md` provides the final source-chain, SubAssembly/Assembly/Region, Intersection/Structure/Drainage, Applied Sections/Build Parametric, review/output, and save/reopen acceptance flow
- `OutputTraceabilityService` validates project identity and required source/result owners for supported normalized outputs without mutating output or source models
- Cross Section empty-result mapping now identifies `AppliedSectionSet` as its result owner and returns a typed missing-Applied-Section diagnostic instead of a source-ref misclassification
- direct output traceability and Cross Section ownership contracts passed 20 tests; the focused normalized output mapper/traceability set passed 37 tests
- primary README, Addon overview, v1 README, Wiki Home/Quick Start/Troubleshooting, current release status, and Master Plan scope override now remove Ramp from active scope and mark Watertight as paused compatibility
- `package.xml` section comments were normalized to ASCII, its XML parses successfully, and primary UTF-8 documentation contains no replacement-character or known mojibake markers
- one Practical Scope T-Intersection smoke expectation was corrected to distinguish consumed constraint segments and preserved boundary-loop edges from newly added support-triangle count; the underlying typed edge-preservation result remained ready
- the final automated Fast tier passed Compile, 8 architecture tests, and 311 focused v1 contracts
- Short-term FreeCAD smoke, the 14-test Practical Scope regression set, and the 8-test Loft Retirement/FCStd restore gate passed under FreeCAD 1.1.1
- changed Phase 5 Python files passed flake8 and `git diff --check`
- the broader non-gating `test_result_builders.py` aggregate recorded 89 passed and 17 existing expectation failures involving older template constructors, bench/daylight orientation and supplemental sampling, and quantity rounding/formula expectations; current focused service and FreeCAD smoke gates remain the accepted Phase 5 automatic baseline
- Ramp remains removed, Watertight Solid development remains paused, and CI remains unchanged with additional CI development prohibited

Phase 5 completion gate:

1. the user runs `V1_PHASE5_SUPPORTED_DOMAIN_MANUAL_QA.md` in FreeCAD 1.1.1
2. A through F pass with no unexplained source mutation or unexpected traceback
3. record the user's acceptance here and close the repository-wide architecture improvement plan

Phase 5 user validation accepted on 2026-07-13:

- the user completed the supported-domain FreeCAD 1.1.1 inspection and accepted the functional result
- the user reported that operation has become slower and elected to investigate performance later
- the slowdown is recorded as explicit follow-up maintenance and does not reopen completed Phase 1 through Phase 5 architecture boundaries
- future performance work must measure stage duration and changed-stage metadata before optimization, distinguish engineering rebuild from presentation refresh and persistence cost, and preserve accepted result reuse and source traceability
- no Ramp, Watertight expansion, or CI development is authorized by the deferred performance item

Repository-wide architecture improvement plan status: completed and user accepted on 2026-07-13.

Post-plan follow-up:

1. investigate the reported slowdown only when explicitly requested
2. collect reproducible timings by stage and document size before changing algorithms or persistence behavior
3. keep legacy aggregate-test and UI-detail gaps as separate maintenance items

Build Parametric panel performance maintenance completed on 2026-07-14:

- profiling identified repeated `AppliedSectionSet` payload restoration during initial review-panel loading as the primary delay
- accepted payload-backed `AppliedSectionSet` restoration now reuses a bounded checksum/fingerprint-keyed object-adapter cache and invalidates on result persistence update
- only Guided Review loads at panel open; Results, Side Slope Diagnostics, Intersections, Breakline Audit, Regions, Drainage, and Visibility load when their tab is first opened
- a 90-section reproducible local fixture reduced initial panel construction from about 12.5 seconds to about 0.38 seconds; this measurement does not change source, result, output, or presentation ownership
- focused payload-cache invalidation and inactive-tab deferral contracts passed under FreeCAD 1.1.1; no Ramp, Watertight, or CI scope changed

Build Parametric panel performance user validation accepted on 2026-07-14:

- the user confirmed that the reported initial panel-opening slowdown is resolved
- initial Guided Review loading, deferred review-tab loading, Refresh behavior, and Apply workflow remain accepted
- this closes the explicitly deferred performance follow-up without reopening the completed Phase 1 through Phase 5 architecture boundaries

### Phase 0: Baseline recovery

- complete Workstream A
- capture the initial test record
- do not begin broad refactoring until the import path and test tiers are reliable
- keep baseline recovery tooling local and do not add CI work

### Phase 1: Boundary guards

- add architecture tests
- introduce the document adapter boundary
- remove private imports and UI-to-command reverse dependencies

### Phase 2: Build Parametric extraction

- extract pure geometry first
- extract typed domain builders second
- extract preview adapters and UI last
- preserve compatibility wrappers until callers migrate

### Phase 3: Editor extraction

- process one editor at a time
- move tests with each responsibility
- avoid simultaneous user-facing workflow redesign

### Phase 4: Persistence and incremental rebuild

- introduce schema migration and result fingerprints
- batch document writes and recomputes
- validate save/reopen behavior in FreeCAD 1.1.1

### Phase 5: Supported-domain stabilization

- close remaining source/result ownership gaps
- complete manual QA for supported domains
- update release and status documentation

## 8. Change Rules

- Keep refactors behavior-preserving unless a separately approved task changes product behavior.
- Add or move tests before deleting compatibility entry points.
- Do not combine a large file move with a geometry algorithm rewrite.
- Do not migrate Ramp or resume Watertight development implicitly during cleanup.
- Do not use preview meshes or shapes to reconstruct accepted design intent.
- Keep diagnostics and source traceability intact through every extraction.

## 9. Validation Matrix

Every implementation slice should run the narrowest relevant levels and record unavailable levels.

1. import and compile validation
2. architecture boundary tests
3. model/service contract tests
4. persistence round-trip tests
5. focused FreeCADCmd smoke tests
6. save/reopen validation when document objects change
7. manual GUI QA when task panels or presentation adapters change

## 10. Completion Criteria

This plan is complete when:

- supported tests run from a verified repository import path
- current CI remains unchanged and no additional CI development has been introduced
- package dependency rules are automated
- major command modules act as thin adapters
- reusable engineering logic resides in services
- FreeCAD persistence logic resides in objects or the shared document adapter
- source, result, and output contracts reside in models
- task panels and viewers do not own engineering truth
- persisted models have tested schema migration and round-trip behavior
- Build Parametric supports incremental, diagnosable rebuilds
- Ramp remains outside active scope
- Watertight Solid development remains paused unless explicitly resumed
