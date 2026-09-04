# Parametric Road V1 Architecture Debt Execution Plan

Date: 2026-09-04
Branch: `v1-0503`
Status: M0 and M1 complete and validated; M8 added from the M0 measurement; M2 through M7 not started
Depends on:

- `AGENTS.md`
- `docsV1/V1_SUPPORTED_DOMAIN_STATUS.md`
- `docsV1/V1_PROJECT_ARCHITECTURE_IMPROVEMENT_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_MODULE_LAYOUT.md`

## 1. Purpose

`V1_PROJECT_ARCHITECTURE_IMPROVEMENT_IMPLEMENTATION_PLAN.md` records Phase 0 through Phase 5 as complete. A repository measurement taken on 2026-09-04 shows that several of its workstreams left measurable residue, and that the Phase 0 validation baseline has since been lost.

This document does not restate the architecture rules and does not reopen the completed phases. It sequences the specific remaining work into executable milestones with measured entry conditions, explicit acceptance criteria, and a validation level for each step.

This plan is behavior-preserving. No milestone in this document changes engineering results, command IDs, source schemas, or the user-facing workflow.

## 2. Relationship To The Architecture Improvement Plan

Every milestone here continues an existing workstream. Nothing new is introduced.

| Milestone | Continues | Residue this plan removes |
| --- | --- | --- |
| M0 | Workstream A | validation tiers are not executable on the current machine |
| M1 | Workstream B | project-tree routing still imported directly from legacy objects |
| M2 | Workstream F | build-path failures still resolve to silent `pass` |
| M3 | Workstream C | contract tests bind to command-module private functions |
| M4 | Workstream C | delegation shims remain in the command module |
| M5 | Workstream C | review row builders remain in the command module |
| M6 | Workstream C | preview functions retain evaluation logic |
| M7 | Workstream B | legacy v0 command surface has no recorded retirement boundary |

## 3. Measured Baseline

All figures were measured on 2026-09-04 at commit `12443f1` on branch `v1-0503`.

### 3.1 Repository size

| Area | Files | Lines |
| --- | --- | --- |
| `freecad/` total | 395 | 209,412 |
| `tests/` total | 255 | 78,362 |
| `v1/commands` | 30 | 60,194 |
| `v1/services` | 113 | 59,097 |
| `v1/ui` | 29 | 18,641 |
| `v1/objects` | 25 | 9,860 |
| `v1/models` | 92 | 7,619 |
| `v1/exchange` | 13 | 1,956 |
| `v1/common` | 6 | 120 |
| legacy `objects` | 31 | 25,945 |
| legacy `ui` | 21 | 24,255 |
| legacy `commands` | 25 | 1,168 |

`v1/commands` still holds slightly more code than `v1/services`. Workstream C acceptance is therefore not yet met in aggregate.

### 3.2 `cmd_build_corridor.py`

24,993 lines, 801 top-level functions, 1 class, 63 module-level import statements.

| Category | Functions | Lines |
| --- | --- | --- |
| single-return delegation shims | 125 | not measured separately |
| functions of 5 lines or fewer | 135 | 391 |
| functions of 100 lines or more | 34 | 6,622 |
| functions of 300 lines or more | 4 | not measured separately |

By responsibility:

| Group | Functions | Lines | Correct owner |
| --- | --- | --- | --- |
| general orchestration | 635 | 13,586 | commands, mostly correct |
| `create_*_preview` | 26 | 3,243 | commands, but oversized |
| `*_rows` | 35 | 2,647 | `services/mapping` or `ui/presentation` |
| document manipulation and selection | 54 | 1,918 | shared document adapter |
| `build_*` | 51 | 1,471 | `services/builders` |

Largest functions:

| Lines | Function |
| --- | --- |
| 721 | `create_corridor_intersection_surface_preview` |
| 499 | `shared_breakline_audit_display_rows` |
| 390 | `_create_corridor_intersection_slope_face_surface_preview` |
| 318 | `corridor_shared_breakline_audit_rows` |
| 269 | `_build_intersection_tie_slope_surface` |
| 268 | `corridor_intersection_contract_review_rows` |

The extraction performed under Workstream C is confirmed working. Sampled `_xy_*` functions are pure single-line delegations to `services/geometry`. The remaining problem is that the alias layer was never removed after its callers migrated, which Workstream C explicitly allowed: preserve compatibility wrappers until callers migrate.

### 3.3 Test coupling

`tests/contracts/v1/test_build_corridor_command.py` is 11,833 lines and references 73 private functions of the command module directly. This is the binding constraint on M4 through M6.

### 3.4 Exception policy

2,715 `except Exception` handlers in `freecad/`, of which 1,278 are followed immediately by `pass`.

| Silent handlers | Module |
| --- | --- |
| 101 | `v1/commands/cmd_build_corridor.py` |
| 68 | `objects/obj_section_set.py` |
| 49 | `v1/commands/cmd_watertight_solids.py` |
| 49 | `objects/obj_project.py` |
| 47 | `v1/ui/viewers/build_corridor_view.py` |
| 34 | `ui/task_structure_editor.py` |
| 30 | `ui/task_profile_editor.py` |

### 3.5 Legacy boundary

`route_to_v1_tree` is defined at `objects/obj_project.py:1736` and imported from v1 code in 84 places, every one of them a function-local import. Function-local import at this scale indicates a circular-dependency workaround. Workstream B specified a shared `ProjectDocumentAdapter` for exactly this; the adapter exists but this call site family did not migrate.

`init_gui.py` still registers 12 legacy v0 command modules.

### 3.6 Other

- 91 `.recompute()` call sites. The highest counts in UI modules are `ui/task_section_generator.py` with 6 and `ui/task_cross_section_editor.py` with 5.
- 0 `TODO`, `FIXME`, `HACK`, or `XXX` markers.
- Intersection and roundabout code inside `v1/` is 66 files and 33,214 lines.

## 4. Root Cause Of The Lost Validation Baseline

The Phase 0 record dated 2026-07-12 states that `pytest 8.4.2` and `flake8 7.3.0` were installed in the selected FreeCAD Python user environment.

Current state:

- `C:\Program Files\FreeCAD 1.1\bin\python.exe` reports Python `3.11.14` and FreeCAD `1.1.3`, build date `2026/07/25`.
- Its user site directory `C:\Users\ganad\AppData\Roaming\Python\Python311\site-packages` does not exist.
- Neither `pytest` nor `flake8` is importable, and neither appears in the interpreter's site-packages.
- `python -m compileall freecad/Corridor_Road` still passes.

The cause is undetermined, and the initial hypothesis was disproved during M0 execution.

`pip install` places these packages in the user site directory `C:\Users\ganad\AppData\Roaming\Python\Python311\site-packages`, which lives in the user profile and not inside the FreeCAD installation. A FreeCAD upgrade that replaces `C:\Program Files\FreeCAD 1.1\` therefore cannot by itself remove them. A change of the bundled Python minor version would orphan the old directory rather than delete it, and no orphaned `Python3xx` directory exists. The entire `C:\Users\ganad\AppData\Roaming\Python` tree was absent, so the packages were removed by something acting on the user profile, not by the FreeCAD upgrade.

The exact trigger is not recoverable from the current machine state, and identifying it is not worth further effort. What matters operationally is unchanged and, if anything, stronger: the loss happened outside the repository, left no trace in the repository, and produced no symptom other than every validation tier except Compile failing at startup.

The consequence is that six of the seven validation tiers in `scripts/run_local_validation.ps1` failed before running any test, and that 148 contract test modules plus the architecture boundary guards were inactive for an unknown period. Reinstalling the packages is necessary but not sufficient, because the loss is silent. The environment check must detect the condition and name the remedy, which is M0 task 2.

## 5. Milestones

Milestones are ordered by dependency, not by size. M0 blocks everything. M1 and M2 are independent of each other and of the M3 through M6 chain.

### 5.1 M0: Validation baseline recovery and upgrade durability

Entry condition: `pytest` and `flake8` are not importable from the FreeCAD interpreter.

Tasks:

1. Reinstall development dependencies through the required interpreter:
   `& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pip install -r requirements-dev.txt`
2. Extend `scripts/check_freecad_environment.ps1` to verify that `pytest` and `flake8` import from the resolved interpreter, and to fail with a remediation message naming the exact `pip install` command when they do not.
3. Record the resolved interpreter path, its Python version, and the FreeCAD API version in the environment check output so an upgrade is visible in test logs.
4. Run `scripts/run_local_validation.ps1 -Tier Fast` and record the result.
5. Split the contract suite into a fast tier and a long-running tier. The Phase 0 record states that the full 1,228-test run exceeded both the 5-minute and 15-minute local limits without producing an early failure. That figure no longer holds: the complete suite is now 1,462 tests in 390s. The tier split is still worth doing, because 73 percent of that time sits in four modules, and because the full run turned out to be red rather than merely slow.
6. Withdrawn. This task assumed that test imports depended on the working directory. They do not. The FreeCAD-bundled `site-packages/freecad/__init__.py` extends the `freecad` namespace package `__path__` with the `freecad` subdirectory of every Mod directory, so `freecad.Corridor_Road` resolves from any working directory and without the repository root on `sys.path`. A root `conftest.py` would add nothing and would misdescribe how imports resolve. The real risk in this mechanism is importing a different installed copy, which `Assert-CorridorRoadWorkbenchLayout` and the import-path check in `scripts/check_freecad_environment.ps1` already cover.

Acceptance criteria:

- `-Tier Fast` completes and returns zero.
- `-Tier Architecture` completes and returns zero.
- The environment check fails with an actionable message when development dependencies are missing.
- A fast contract tier exists with a documented target duration.
- No CI file is modified.

Validation level: 1, 2, 3.

Risk: none. No product code changes.

### 5.2 M1: Project-tree routing consolidation

Entry condition: 84 function-local imports of `route_to_v1_tree` from `objects/obj_project.py`.

Tasks:

1. Confirm whether the existing shared document adapter introduced in Workstream B already exposes an equivalent routing entry point. If it does, this milestone is a call-site migration only.
2. If it does not, add a v1-owned routing operation to the document adapter, implemented once.
3. Keep `objects/obj_project.route_to_v1_tree` as a thin delegating alias. Do not remove it; existing FCStd documents and legacy commands depend on the legacy module surface.
4. Replace the 84 function-local imports with a single module-level import per module.
5. If any module still requires a function-local import after the change, record the circular-dependency reason in a comment rather than leaving it unexplained.

Acceptance criteria:

- v1 feature modules do not import legacy project objects for tree routing.
- The legacy alias still resolves for compatibility.
- Save, close, reopen, and recompute behavior is unchanged for an existing document.
- The architecture boundary test suite passes unchanged.

Validation level: 1, 2, 3, 5, 6.

Risk: low. Mechanical, behavior-preserving, and independently revertible.

### 5.3 M2: Build-path diagnostics

Entry condition: 101 silent handlers in `cmd_build_corridor.py`, 47 in `build_corridor_view.py`.

This milestone deliberately does not attempt a repository-wide cleanup. A substantial share of the 1,278 silent handlers are intentional startup-resilience guards, for example the virtual path mapping in `freecad/Corridor_Road/__init__.py` and the project touch loop in `init_gui.Activated`. Those must remain.

Tasks:

1. Classify the 101 handlers in `cmd_build_corridor.py` into three sets: geometry or kernel failure, expected domain failure, and startup or compatibility resilience.
2. For geometry and kernel failures, emit a typed diagnostic carrying what failed, the owning object or source ID or station, the input to inspect, and whether the result is blocked, partial, stale, or a fallback.
3. Carry those diagnostics through the existing result contract. Do not emit console text as the only record.
4. Leave resilience guards in place and add a one-line comment stating the compatibility reason for each.
5. Add focused contract tests asserting that an induced geometry failure produces a diagnostic rather than an empty successful result.
6. Repeat for `build_corridor_view.py` only where a viewer failure currently hides a result failure.

Acceptance criteria:

- Preview failure is distinguishable from engineering result failure in the result contract.
- No induced geometry failure produces a successful empty result.
- Startup resilience behavior is unchanged.
- Every remaining silent handler in the touched files carries a stated reason.

Validation level: 1, 2, 3, 5.

Risk: low to medium. Newly surfaced diagnostics may expose pre-existing failures that were previously invisible. That is the intended outcome, but it can look like a regression in manual QA and should be recorded as such.

### 5.4 M3: Test decoupling from command-module privates

Entry condition: 73 private functions of `cmd_build_corridor.py` referenced directly by an 11,833-line contract test module.

This milestone produces no production code change. It exists solely to unblock M4 through M6.

Tasks:

1. Classify the 73 referenced privates by the layer that now owns their behavior: geometry service, builder service, evaluation service, mapping, or genuine command orchestration.
2. For each private that delegates to a service, move the assertion to the service's public API in the appropriate service contract test.
3. Leave assertions that genuinely test command orchestration, such as document object creation, tree routing, and diagnostic surfacing, in the command test.
4. Track the count of referenced privates as the milestone's progress metric. Target zero for shim-backed privates.
5. Do not restructure the test file wholesale. Move assertions in groups matching the shim families in M4.

Acceptance criteria:

- Every shim-backed private has an equivalent assertion against a service public API.
- The command contract test asserts orchestration only.
- Total assertion coverage does not decrease.

Validation level: 1, 2, 3.

Risk: medium. The main hazard is silently dropping coverage while moving assertions. Move, do not rewrite, and compare test counts before and after each group.

### 5.5 M4: Delegation shim removal

Entry condition: 125 single-return delegation shims; M3 complete for the family being removed.

Tasks:

1. Process one shim family at a time. Suggested order: `_xy_*`, then `_xyz_*`, then `_intersection_patch_*`, then the remainder.
2. For each family, migrate call sites to the service function, then delete the shim.
3. Run `-Tier Fast` after each family. Do not batch families.
4. Update the architecture test's wrapper line-count limits when a listed wrapper is deleted, so the guard continues to describe reality.

Acceptance criteria:

- No single-return delegation shim to a service remains in `cmd_build_corridor.py`.
- Build Parametric results are unchanged for an ordinary road and for a cross intersection.
- The architecture wrapper limits match the surviving wrappers.

Validation level: 1, 2, 3, 5, 7.

Risk: low per family, medium in aggregate. Mitigated by family-at-a-time sequencing.

### 5.6 M5: Review row builders to mapping or presentation

Entry condition: 35 `*_rows` functions totalling 2,647 lines in the command module, including a 499-line and a 318-line function.

Tasks:

1. Confirm the correct owner for each row family. Row builders that produce a normalized contract belong in `services/mapping`, next to the existing 15 mappers. Row builders that produce table state for a specific panel belong in `ui/presentation`.
2. Extract the shared-breakline audit rows first. They are the largest, and a typed audit result plus a review mapper was already specified in Workstream C task 5.
3. Extract the intersection contract review rows second.
4. Move the corresponding assertions with each extraction.
5. Keep row ordering, column identity, and diagnostic text stable. These are user-visible review surfaces.

Acceptance criteria:

- `cmd_build_corridor.py` contains no review row calculation.
- Review tables render identically before and after for the same document.
- Extracted mappers do not import FreeCAD, Part, or Qt where the layer forbids it.

Validation level: 1, 2, 3, 5, 7.

Risk: medium. Row output is user-visible. Manual GUI QA is required, not optional.

### 5.7 M6: Preview function decomposition

Entry condition: 26 `create_*_preview` functions totalling 3,243 lines, the largest being 721 lines.

Creating FreeCAD document objects is legitimate command territory. The defect is that these functions also evaluate.

Tasks:

1. For `create_corridor_intersection_surface_preview` at 721 lines, separate evaluation from document object creation. Evaluation moves to a builder service returning a typed result; the command consumes the result and creates objects.
2. Repeat for `_create_corridor_intersection_slope_face_surface_preview` at 390 lines and the remaining functions above 150 lines.
3. Do not combine this milestone with any geometry algorithm change. Extraction only.
4. Preserve object naming, tree placement, visibility defaults, and view provider behavior exactly.

Acceptance criteria:

- No preview function exceeds roughly 150 lines.
- Extracted builders create no FreeCAD document objects.
- Preview object names, tree placement, and appearance are unchanged.
- Save and reopen behavior is unchanged.

Validation level: 1, 2, 3, 5, 6, 7.

Risk: medium to high. This is the milestone most likely to change what the user sees. Sequence it last and run full manual QA.

### 5.8 M7: Legacy v0 retirement boundary, documentation only

Entry condition: 51,368 lines across legacy `objects`, `ui`, and `commands`; 12 legacy command modules registered in `init_gui.py`.

This milestone deletes nothing. Its output is a decision record.

Tasks:

1. Produce a table of every registered legacy command with its v1 replacement, or the explicit statement that none exists.
2. For each legacy command with a complete v1 replacement, record whether removing it from the toolbar and menu would break document restoration.
3. Declare the large legacy persistence modules, `objects/obj_section_set.py`, `objects/obj_corridor.py`, and `objects/obj_project.py`, as frozen read-and-restore compatibility surfaces.
4. Record the decision in `docsV1/V1_SUPPORTED_DOMAIN_STATUS.md`.

Acceptance criteria:

- Every registered legacy command has a recorded status.
- No code is removed under this milestone.

Validation level: none. Documentation only.

Risk: none as scoped. Any subsequent removal is a separate authorized task, because existing FCStd documents reference legacy proxies through the virtual path mapping.

### 5.9 M8: Contract failure triage

Entry condition: 131 of 1,462 contract tests fail. This milestone did not exist when the plan was written; it was created from the M0 task 4 measurement.

The failures are reproducible, not an artefact of ordering or of the full-suite run. `test_applied_sections_command.py` produces the same four failures when executed alone as it does inside the complete suite.

Measured classification of all 131:

| Count | Share | Class |
| --- | --- | --- |
| 73 | 55% | value mismatch, `assert x == y` |
| 31 | 23% | `AttributeError`, contract drift |
| 21 | 16% | predicate false, missing row or flag |
| 3 | 2% | `KeyError` or `IndexError` |
| 2 | 1% | GUI or `ViewObject`, headless incompatible |
| 1 | 1% | `TypeError`, signature drift |

Only 2 of 131 are headless-environment problems. The remaining 129 are behavioral or contract mismatches between the tests and the code.

Representative examples:

- `test_build_document_applied_section_set_uses_v1_sources` expects 5 station rows and gets 40, the extra rows carrying `kind='vertical_curve_supplemental'`.
- `test_assembly_preset_apply_syncs_region_refs_for_benched_build` finds no `bench` row in the benched-slope preset result.
- `AttributeError` cases name `IntersectionModel.control_areas`, `TINQualityRow.metric`, and `FeaturePython.ElementAssemblyComponentRefs`.

Failures by module: `test_build_corridor_command.py` 39, `test_watertight_solids_command.py` 17, `test_result_builders.py` 17, `test_intersection_command.py` 16, `test_intersection_shared_boundary_graph_builder.py` 9, and 20 further modules with 5 or fewer each.

Tasks:

1. Decide, per failure family, whether the test encodes a stale expectation or the code has regressed. This requires product judgement and cannot be inferred from the code alone. The supplemental-sampling and benched-slope families are the two largest and should be decided first.
2. Record the decision per family before changing anything.
3. For stale expectations, update the test to the accepted behavior and cite the document or release that established it.
4. For regressions, fix the code and keep the test unchanged.
5. Move the 2 headless-incompatible tests to the FreeCAD GUI smoke path, or mark them so a headless run reports them as skipped rather than failed.
6. Watertight Solid failures are inside a paused area. Repair only what data-loss prevention or compatibility requires, and record the rest as accepted-red with a reason.

Acceptance criteria:

- Every one of the 131 failures is classified as stale expectation, regression, environment, or accepted-red with a recorded reason.
- No test is changed to match current behavior without a recorded decision that the current behavior is correct.
- The `ContractsFull` tier is green, or its remaining failures are an explicitly recorded accepted-red list.

Validation level: 1, 2, 3, 5, 6, 7 depending on the family.

Risk: high if rushed. Changing a test to match current behavior is the fastest way to make the suite green and the fastest way to cement a regression in a released product. This milestone is judgement work, not mechanical work.

## 6. Sequencing

```text
M0  (blocking, must complete first)
 |
 +-- M1  (independent, low risk)
 |
 +-- M2  (independent, low risk)
 |
 +-- M8  (judgement work; should precede M4-M6)
 |    |
 +-- M3 -> M4 -> M5 -> M6   (strictly ordered chain)
 |
 +-- M7  (independent, documentation only)
```

M1, M2, M7, and M8 may proceed in any order once M0 is green. The M3 chain is strictly ordered: removing a shim before its assertion has moved deletes coverage.

M8 should be resolved before M4, M5, and M6 even though it does not block them mechanically. Those milestones move code that the failing tests cover, and a suite with 131 pre-existing failures cannot distinguish a new regression from the existing red. Running them against a red baseline is possible only by diffing the exact failure set before and after each slice, which is what M1 did, but that is a workaround rather than a gate.

## 7. Validation Matrix

Levels follow section 9 of `V1_PROJECT_ARCHITECTURE_IMPROVEMENT_IMPLEMENTATION_PLAN.md`.

| Milestone | 1 compile | 2 architecture | 3 contracts | 4 persistence | 5 smoke | 6 save/reopen | 7 manual GUI |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | yes | yes | yes | no | no | no | no |
| M1 | yes | yes | yes | no | yes | yes | no |
| M2 | yes | yes | yes | no | yes | no | no |
| M3 | yes | yes | yes | no | no | no | no |
| M4 | yes | yes | yes | no | yes | no | yes |
| M5 | yes | yes | yes | no | yes | no | yes |
| M6 | yes | yes | yes | no | yes | yes | yes |
| M7 | no | no | no | no | no | no | no |
| M8 | yes | yes | yes | yes | yes | yes | yes |

Report tests actually run and tests not run for every slice. Do not claim GUI validation when only headless tests ran.

## 8. Non-Goals

- No CI change of any kind. CI development remains frozen.
- No Ramp work.
- No Watertight Solid work beyond keeping existing tests passing.
- No repository-wide exception cleanup.
- No legacy code deletion.
- No geometry algorithm change.
- No user-facing workflow, command ID, object name, or property name change.
- No new external dependency.

## 9. Completion Criteria

This plan is complete when:

- the validation tiers run on the current machine, and an interpreter upgrade that removes development dependencies fails the environment check with an actionable message
- v1 feature modules no longer import legacy project objects for tree routing
- Build Parametric geometry and kernel failures produce typed diagnostics rather than silent fallbacks
- `cmd_build_corridor.py` contains no delegation shims and no review row calculation
- no preview function in the command module exceeds roughly 150 lines
- the command contract test asserts orchestration rather than extracted service internals
- every registered legacy v0 command has a recorded replacement status
- the `ContractsFull` tier is green, or every remaining failure is on a recorded accepted-red list with a reason

An aggregate size target for `cmd_build_corridor.py` is deliberately omitted. Line count is a symptom; the acceptance criteria above describe the actual defect.

## 10. Execution Record

### M0 completed on 2026-09-04

- `pytest 8.4.2` and `flake8 7.3.0` reinstalled through `C:\Program Files\FreeCAD 1.1\bin\python.exe`. They install into the user site directory, which pip recreated.
- `scripts/check_freecad_environment.ps1` now reports the resolved interpreter path, Python version, FreeCAD API version, and FreeCAD build date, then verifies that `pytest` and `flake8` import from that interpreter.
- The failure path was verified by simulating a missing user site with `PYTHONNOUSERSITE=1`. The check fails with the exact `pip install` command for the resolved interpreter and names the tiers that cannot run.
- `-Tier Architecture` passes: 8 tests.
- `-Tier Fast` passes: compile, 8 architecture tests, 312 contract tests, 33s at first green run.
- Task 6 withdrawn. See section 5.1.
- `ContractsFull` tier added. `Contracts` now skips the four heavy modules and runs 1,133 tests in 72s; the complete suite is 1,462 tests in 390s. `Full` uses the complete suite.
- No CI file was modified.

The M0 measurement produced the M8 finding: the complete contract suite has 131 failures. It was not previously known to be red, because the Phase 0 record shows the full run was never carried to completion.

### M1 completed on 2026-09-04

- `route_object_to_project_tree` added to `v1/objects/project_document_adapter.py` as a module-level pass-through to the legacy function, next to the existing `ProjectDocumentAdapter.route_to_project_tree` method.
- 78 function-local imports across 31 v1 modules replaced by one module-level import per module, and the 78 call sites renamed.
- Four further modules used a combined import (`cmd_centerline3d.py`, `cmd_edit_tin.py`, `cmd_intersection_editor.py`, `cmd_superelevation_editor.py`). `route_to_v1_tree` was removed from each import list and the remaining symbols kept.
- `cmd_intersection_presets.py` and `cmd_watertight_solids.py` wrapped the local import in `try: ... except Exception: return` as an import-availability guard. With the import hoisted to module level the guard is unreachable by construction, so it was removed. This is the one behavioral difference in M1: a failure to import the legacy routing symbol now fails module import instead of returning early. The adapter already imported the same symbol at module level, so the dependency was already hard for v1.
- The Watertight command module was included. `V1_PROJECT_ARCHITECTURE_IMPROVEMENT_IMPLEMENTATION_PLAN.md` section 2.2 permits mechanical moves of Watertight code during an architecture refactor when behavior is unchanged.
- `route_to_v1_tree` is now referenced only by `v1/objects/project_document_adapter.py`.
- `tests/architecture/test_v1_package_boundaries.py` carried a ratchet recording 21 `objects/obj_*.py` files as accepted legacy-routing paths. The migration emptied that set, so the guard was tightened deliberately: the adapter is the only allowed path, and the check now covers every v1 package rather than `objects` alone.
- A first pass normalized line endings in six mixed-ending files, producing about 3,000 lines of cosmetic churn. Those files were restored and the edit reapplied with per-line ending preservation. Every changed file now matches the expected edit size exactly.

M1 validation actually run:

- level 1 compile: `compileall freecad tests` passes.
- level 2 architecture: 8 tests pass, including the tightened routing guard.
- level 3 contracts: `-Tier Fast` passes with 312 tests. The complete suite was run before and after the migration and the failing set is identical: 131 failed and 1,331 passed both times, with the same test identifiers. M1 introduced no contract regression.

- level 5 smoke: `tests/regression/run_short_term_smokes.ps1` ran 26 smoke scripts under FreeCADCmd and returned exit code 0 with no failure or traceback output. The set includes `smoke_tree_schema.py`, which exercises the project-tree schema directly.
- levels 6 and 7 manual: executed by the maintainer in the FreeCAD GUI on 2026-09-04 against FreeCAD 1.1.3 and reported as passing for every part, including the 24-step tree routing walkthrough, the two behavioral change points, save and reopen, legacy document compatibility, and preview visibility. Recorded in `docsV1/V1_ARCHITECTURE_DEBT_M1_MANUAL_QA.md`.

M1 is complete. All seven validation levels applicable to it have run.

## 11. Open Decisions

These require a decision before the affected milestone starts. None blocks M0.

1. Resolved on 2026-09-04. `ProjectDocumentAdapter.route_to_project_tree` already existed, and the adapter module already imported the legacy function at module level, which proved there was no circular-dependency reason for the 78 function-local imports. M1 was a call-site migration.
2. M5: for each row family, is the correct owner `services/mapping` or `ui/presentation`? This depends on whether the rows feed a normalized output contract or only a panel table.
3. M0 task 5: what is the target duration for the fast contract tier, and which modules belong to the long-running tier?
4. M7: is a legacy command with a complete v1 replacement removed from the toolbar in a later task, or retained indefinitely for user familiarity?
