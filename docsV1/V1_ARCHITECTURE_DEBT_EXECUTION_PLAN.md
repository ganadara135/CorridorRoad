# Parametric Road V1 Architecture Debt Execution Plan

Date: 2026-09-04
Branch: `ganada_0902`
Status: M0, M1, M2, M3, M4, M5 (presentation scope), M6, and M7 complete; M8 in progress, contract baseline 52 to 32
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

`init_gui.py` still registers 13 legacy v0 command modules. The initial count of 12 in this section was wrong; M7 measured it directly and the corrected figure and its breakdown are in `docsV1/V1_LEGACY_COMMAND_RETIREMENT_BOUNDARY.md`.

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

### M2 completed on 2026-09-04

The milestone premise in section 5.3 was largely wrong and is corrected here.

Classification of the 101 silent handlers in `cmd_build_corridor.py`:

| Count | What the guarded block does |
| --- | --- |
| 41 | progress callbacks, tree routing, and other orchestration |
| 30 | `ViewObject` and display property access |
| 14 | document writes such as `recompute` and `addObject` |
| 8 | geometry construction |
| 7 | payload parsing and service calls |
| 1 | import availability |

Only 8 of 101 touch geometry at all. The wider measurement explains why: the services layer, where geometry now lives after Workstream C, has 11 silent handlers in total and **none** of them are geometry-bearing. Across all of v1, only 27 silent handlers guard geometry, and they sit in commands and objects rather than in services. The extraction performed under Workstream C did its job, and the aggregate count of 1,278 silent handlers was a poor proxy for hidden engineering failure.

Of the 8 geometry-bearing handlers in the command module, 4 are the deliberate marker fallback chain in `_point_sphere_marker_shapes` and `_point_cross_shapes`, which degrades a marker from sphere to cross to vertex. Silence there is the mechanism, not a defect, and each is now commented with that reason.

The real defect was a different pattern that the milestone text did not anticipate:

```python
try:
    obj.Shape = Part.makeCompound(shapes)
    obj.Label = "..."
except Exception:
    return obj
```

Fifteen preview-creation functions used it. On failure the caller receives a document object with no `Shape` that also never reached its `_set_preview_property(obj, "CRRecordKind", ...)` tagging, which is indistinguishable from a successful empty preview. This is exactly the acceptance criterion "no induced geometry failure produces a successful empty result".

Changes made:

- Added `_mark_preview_shape_failure(obj, *, preview_kind, error)`. It sets `PreviewShapeStatus` to `shape_build_failed` and `PreviewShapeDiagnostic` to a bounded `kind: ExceptionType: message` string, then returns the object. A preview failure still does not abort a build.
- Converted all 15 sites to return through it, naming the owning preview function as `preview_kind`.
- `_create_drainage_flow_review_highlight` and `_create_subassembly_kind_review_highlight` silently dropped individual highlight segments. They now count them and publish `SkippedSegmentCount` and `SkippedLinkCount` next to the existing `PipeSegmentCount`, `StationSpanCount`, and `SurfacePatchCount` properties, so partial output is visible.
- Added `tests/contracts/v1/test_build_corridor_preview_diagnostics.py` with 4 tests, including one asserting that a failure to write properties does not turn a preview failure into a louder failure.
- Added `test_build_corridor_preview_shape_failures_are_marked` to the architecture suite as a ratchet, so a new handler that returns a bare `obj` after a shape assignment fails the build.

Validation run:

- level 1 compile: passes.
- level 2 architecture: 9 tests pass, up from 8.
- level 3 contracts: `-Tier Fast` passes with 312 tests. The complete suite was run before and after the change and the failing set is identical: 131 failed both times with the same test identifiers, while passing tests rose from 1,331 to 1,335 as the new contract module was added. M2 introduced no contract regression.
- level 5 smoke: `tests/regression/run_short_term_smokes.ps1` rerun after the change. 26 smoke scripts, exit code 0, no failure or traceback output.
- level 7 manual GUI: executed by the maintainer on 2026-09-04 and reported as passing. Build Parametric completed normally, the new `SkippedSegmentCount` and `SkippedLinkCount` counters reported no dropped highlight items, and no preview object carried `PreviewShapeStatus` or `PreviewShapeDiagnostic`. The absence of those two properties is the substantive result: it confirms that no preview shape assignment was failing silently in this document before the change.

Known limitation, deliberately not addressed:

- In the failure path the object still does not receive `CRRecordKind`, so it is not routed into the project tree and remains at the document root. Fixing that would change tree placement behavior, which would invalidate the M1 tree-routing manual QA completed the same day. It belongs in a separate slice.

### M7 completed on 2026-09-05

Output is `docsV1/V1_LEGACY_COMMAND_RETIREMENT_BOUNDARY.md`. No code was removed, and no command, id, toolbar entry, or menu changed.

The inventory changed the shape of the question. `init_gui.Initialize` imports 13 legacy command modules, but they are not one population:

- 4 of them are stable-command-id bridges that call a v1 entry point and hold no behavior of their own: `cmd_generate_corridor` calls `run_v1_build_corridor_command`, and `cmd_view_cross_section`, `cmd_review_plan_profile`, and `cmd_generate_cut_fill_calc` do the same for their v1 engines. Together they are 260 lines. They are the compatibility mechanism, not the debt, and retiring them would change user-visible command ids that `AGENTS.md` requires to stay stable.
- 3 are surfaced and have no v1 successor at all: `cmd_project_setup`, `cmd_outputs_exchange`, `cmd_ai_assist`. `cmd_project_setup` is the notable one, because Project Setup is stage 1 of the v1 workflow and is still driven by the v0 task panel `ui/task_project_setup`.
- 6 are registered but not surfaced in the toolbar or menus, and each already has a surfaced v1 successor. These 316 lines are the only real retirement candidates.

The decisive compatibility finding is that retirement carries no document risk. No module in `commands` or `v1/commands` assigns `.Proxy`, and all 15 modules in `virtual_paths._PROXY_OBJECT_MODULES` are `obj_*` modules in the legacy `objects` package. Removing a legacy command from the toolbar, a menu, or `init_gui.Initialize` cannot break FCStd restoration. The only cost is to macros, custom toolbars, and user familiarity, which moves open decision 4 from a compatibility question to a user-experience one.

`objects/obj_section_set.py` (5,569 lines), `objects/obj_corridor.py` (2,974 lines), and `objects/obj_project.py` (2,747 lines) are declared frozen read-and-restore compatibility surfaces. `obj_project.py` is frozen but not dormant: 23 v1 modules import it, and the v1 routing entry point added in M1 delegates into it.

The record is indexed in `docsV1/README.md` and referenced from the special classifications list in `docsV1/V1_SUPPORTED_DOMAIN_STATUS.md`. It is registered there as an inventory record, not as a scope decision, because the retirement decision itself is still open.

Validation level: none. Documentation only, as specified.

### M8 first pass on 2026-09-05

Two failure families were decided by the maintainer and applied. A third group was deleted as obsolete.

**Family 1: supplemental sampling.** Investigation showed the five failures were not one change but two.

The panel checkbox was deliberately removed when supplemental density moved to the Applied Sections stage, which the Build Parametric panel now states in its own visible text and which `_use_supplemental_sampling` encodes by returning False unconditionally. The maintainer confirmed the removal is correct. `test_build_corridor_panel_has_supplemental_sampling_checked_by_default` was rewritten as `test_build_corridor_panel_delegates_supplemental_sampling_to_applied_sections`, a guard for the new contract rather than a deletion.

Separately, `corridor_surface_geometry_service` did not lose supplemental sampling at all: it still implements it, but `ff3a74c "Add Curve guide in Alignment, Profile"` narrowed the rule so a span is densified only when the tangent delta exceeds `SUPPLEMENTAL_FRAME_TANGENT_DELTA_THRESHOLD_DEG` or the chord deviation exceeds `SUPPLEMENTAL_FRAME_CHORD_DEVIATION_THRESHOLD`. Uniform spacing alone no longer densifies. The four failing service tests supplied straight two-station spans and expected spacing-driven densification. The maintainer confirmed the curve-driven rule is correct, and the four tests were rewritten against measured behavior while keeping each test's original subject: mismatched side slope row preservation, ditch row preservation, and drainage source tag preservation.

Measured reference values, straight versus curved span with the same geometry:

| Span | station_count | daylight vertices | supplemental vertices |
| --- | --- | --- | --- |
| tangent 0 to 0 | 2 | 2 | 0 |
| tangent 0 to 25 | 5 | 8 | 24 |

Rewriting all four against the straight case would have left supplemental sampling, a live feature with 51 code references, without any test. `test_corridor_surface_geometry_service_densifies_a_curved_daylight_span` was added to keep that coverage, and the straight-span test names it.

Three stale assumptions in those tests were only found by measuring rather than reasoning: vertex notes carry a `role=` prefix, so the existing `daylight_marker` filter had already been matching nothing; the `drainage_source_missing_point_count` quality row no longer exists; and the ditch scenario reports `section_point_count` 4 rather than 2.

**Family 2: benched slope.** The maintainer decided that derived bench segments must be expanded into `AppliedSection.subassembly_rows`, so this was a code gap rather than a stale test.

The investigation first cleared the recent refactoring of suspicion. `_build_subassembly_rows` is byte-identical at the `1.0.9` release and at HEAD, neither version ever emitted a bench row, and `SubassemblyBenchProfileService` returns a bench segment correctly for the preset parameters. The test could not have passed at the release either; the complete suite had never been run to completion, so nobody saw it.

`_rows_with_derived_bench_rows` now expands bench intent stored on side_slope parameters into derived rows. Segments come from the same service that produces the `bench_surface` points, so rows and geometry cannot disagree. Authored rows are preserved, each derived row carries `source_instance_ref` back to its owner, and derived rows carry no definition or preset ref so preset diagnostics skip them and the point, link, and shape resolvers, which look rows up by id, see no new referenced subassembly.

One consequential test changed as a result: `test_applied_section_service_evaluates_side_slope_bench_rows` asserted an exact row-kind list and now expects `["lane", "side_slope", "bench"]`, plus the derived row's traceability.

**Obsolete tests deleted.** 26 failing tests referenced 13 private functions of `cmd_build_corridor` that no longer exist, having been extracted into services under Workstream C. 17 were in `test_build_corridor_command.py` and 9 in `test_intersection_shared_boundary_graph_builder.py`, which kept its other 22 tests. The extracted behavior is covered by 35 service contract tests across seven modules, all passing, so the deletion removed dead references rather than coverage. No new lint finding resulted; the two F841 warnings in the touched file are present at the same lines at HEAD.

Not deleted, and why:

- Watertight Solid failures were marked skipped rather than deleted, see below.
- The value-mismatch failures stay. They assert different values for behavior that still exists, and as the two families above showed, such a test can be either a stale expectation or a real regression. Deleting them without deciding which would hide a regression permanently.

### Watertight Solid failures marked skipped

18 failing tests sit inside the paused Watertight Solid area: 17 in `test_watertight_solids_command.py` and 1 in `test_watertight_simulation_qa_service.py`. `AGENTS.md` lists keeping existing tests operational as allowed work during the pause, so deleting them would contradict the project's own policy and discard the record needed when development resumes.

Each of the 18 now carries `@pytest.mark.skip` naming the pause and this plan. The other 43 tests in those two files still run and pass, so the compatibility guard the pause policy asks for stays in place. Reversing this is one decorator line per test.

Their failure signatures point at a single upstream cause rather than 18 independent defects:

| Count | Signature |
| --- | --- |
| 6 | `'not_validated' == 'ok'` |
| 3 | `'not_built' == 'built'` |
| 3 | `assert False is True` |
| 2 | `assert None is not None` |
| 2 | `'NoneType' object has no attribute 'solid_rows'` |
| 2 | other assertion mismatches |

Every one says the same thing: the Watertight build and validate path produces no output at all in this state. Whoever resumes Watertight development should look for one root cause first, not triage eighteen.

Validation:

- level 1 compile: passes.
- level 2 architecture: 9 tests pass.
- level 3 contracts: `-Tier Fast` passes with 312 tests. The complete suite moved from 131 failed and 1,336 passed to 125 failed and 1,342 passed with no new failure. Removing the 26 obsolete tests then brought it to 99 failed and 1,342 passed, again with no new failure.

### Repository note: mixed line endings

Several tracked files store mixed line endings in the blob itself. `test_build_corridor_command.py`, for example, holds 4,755 CRLF lines out of 11,833. Any edit that rewrites a whole file normalizes it to one ending and produces thousands of spurious changed lines, and `git add` does not clean that up. It happened twice during this plan, in M1 and again in M8, with different tools each time.

Before committing a large edit, check `git diff --numstat` against the expected edit size. If it is inflated, realign the file to the HEAD blob and restore each line's original ending rather than accepting the churn, which otherwise buries the real change and makes later archaeology on these files much harder. M4 through M6 all involve large mechanical edits to exactly these files, so expect this every time.

### Intersection aggregate-status cluster, 2026-09-05

Eight failing tests asserted an aggregate status equal to `warning` and got `error`. None of them is about the aggregate; each checks the source status of one row family. Probing showed every row-level assertion already passed, and the aggregate turned error only because `281c0b0 "Done Cross Intersection"` added corner-graph completeness validation that these deliberately minimal fixtures do not satisfy. Four carry `error:intersection_corner_graph_leg_count_insufficient` from a fixture declaring a `t_intersection` with one leg; three carry missing curb-return policy, radius, or arc points.

Those errors are correct, and this needed no product decision: a T intersection with one leg and a curb return with no radius cannot be built. Each aggregate assertion was replaced by one stating that no error comes from the family under test, which still fails if an unrelated new error appears. Five tests passed as a result.

Three then failed on deeper assertions the aggregate check had masked. The maintainer decided to remove them. The observations are recorded here because the tests no longer carry them:

| Removed test | Observed |
| --- | --- |
| `test_intersection_surface_zone_evaluation_warns_when_slope_zone_lacks_pavement_or_curb_tie_edges` | `slope_zone_count` 0, expected 3; `zone_rows` empty |
| `test_intersection_drainage_hint_evaluation_warns_without_drainage_policy` | `hint_row_count` 0, expected 6; `hint_rows` empty |
| `test_corridor_intersection_contract_review_rows_expose_source_status_warnings` | a contract row reports an `output_path` other than `contract_consumed` |

The first two share one open question that is now untested: whether surface zone and drainage hint evaluation should produce no rows at all when the corner graph is invalid. Both fixtures fail corner-graph validation with missing curb-return policy, radius, and arc points, and both evaluations return a completely empty result rather than rows carrying a warning. Both test names say "warns when ... lacks" and "warns without ...", so the original intent was rows plus a warning. If a later design promoted the corner graph to a precondition, the current behavior is right and the fixtures were simply incomplete. That was not established, and no test now covers either path.

### Result builder cluster and the first real regression, 2026-09-05

`test_result_builders.py` held 13 failures. Seven were mechanical drift with unchanged meaning and needed no decision: four bench and daylight tests filtered vertex notes without the `role=` prefix, one read `TINQualityRow.metric` where the field is `kind`, one compared an accumulated volume with `==` and failed on `12.000000000000002`, and one constructed `SubassemblySectionTemplate` without the now-required `template_kind`, set to `"roadway"` like every other call site. All seven pass after the fix.

**Ditch flowline elevation was a real regression, not a stale test.** `test_applied_section_service_starts_benched_slope_after_ditch_outer_edge` failed with `18.96 == 8.96`, an offset of exactly the profile elevation. Dumping the section's point rows showed why:

| role | offset | z |
| --- | --- | --- |
| `ditch_surface` outer edge | -4.50 | 9.96 |
| `ditch_flowline` | -4.50 | **19.96** |
| `side_slope_surface` | -6.50 | 18.96 |
| `bench_surface` | -7.50 | 18.94 |
| `daylight_marker` | -8.50 | 18.44 |

`_oriented_ditch_rows` returns absolute elevations (`edge_z + z_delta`), and the `ditch_surface` points use them directly, which is why the edge is correct. The flowline loop received the same rows under the name `z_delta` and computed `base_z + z_delta`, adding the frame elevation a second time. Every bench slope point is chained from the flowline, so the whole benched side slope sat one profile elevation too high. The failure predates this plan: the same `18.96 == 8.96` appears in the M2 baseline run, and the flowline construction dates from `9b718c6`.

The fix removes the second `base_z` and renames the value to `flow_z`, with the helper's variable renamed to match. `_ditch_flowline_rows` and the point roles are otherwise unchanged. `ditch_flowline` is consumed by `drainage_review_mapper.py` and the subassembly definition presets; running the three drainage and applied-section contract modules before and after showed no new failure. An earlier draft of this record, and the commit message of `e0a74ab`, claimed that `test_drainage_editor_validate_shows_flow_route_summary` also passed as a result; that was a misreading of the comparison output. The test fails alone and in the full suite before and after the fix, on `'Flow Route Summary:' in ...`, and is unrelated to the flowline elevation.

This is a user-visible change to drainage flowline and benched side slope elevations and needs level 5 smokes and level 7 manual confirmation before it is called complete.

Three more tests in the same module were stale in ways that measurement settled without a product decision:

- `test_corridor_surface_geometry_service_uses_superelevation_resolved_section_points` asserted elevations by positional vertex id (`v1:p2`). Vertices are now emitted per point and `subassembly_ref`, so a shared offset carries two vertices and the ids shift. The resolved elevations at every offset were exactly as expected (10.30, 10.21, 10.00, 9.93), so the test now asserts elevation by offset, which is what superelevation is a property of.
- `test_corridor_surface_geometry_service_builds_drainage_surface_from_ditch_points` expected 6 triangles, `section_point_count` 4, provenance kind `applied_section_points`, a positional `quality_rows[1]`, and a `drainage_source_missing_point_count` row. The drainage surface now builds one strip per ditch group and does not span the roadway between them: `strip_group_count` 2, 4 triangles, `section_point_count` 8, provenance kind `applied_section_drainage_points`, and no missing-point row. The test now asserts those and looks quality rows up by kind.
- `test_corridor_surface_service_adds_drainage_surface_when_ditch_points_exist` compared an `operation_summary` string that gained the words "and Subassembly drainage links". Wording only.

Two remain and are decisions:

- `test_applied_section_service_orients_bench_side_slope_up_for_cut_context` expects the resolved section to expand a side slope in cut context into derived `side_slope` and `daylight` rows under `side-slope-right:*`, with the slope reoriented upward (`slope == 0.5`) and clipped at the terrain (`width == 4.0`). No release ever emitted those derived rows; the service has no `kind="side_slope"` or `kind="daylight"` row construction at `1.0.9` or now. The point geometry and the `bench_cut_fill_context` diagnostic the test also checks are already correct: the slope rises from 10.0 to meet existing ground at 12.0 over 4.0 of width. The M8 bench decision covered bench segments only; whether the expansion should extend to reoriented side slope and daylight rows is a design question. The bench row this plan added, `side-slope-right:bench:1`, also matches the test's prefix filter, so the test's expected list can no longer be satisfied as written under either answer.
- `test_quantity_build_service_adds_structure_quantity_fragments` expects `culvert_wall_volume` 27.5 for a two-barrel box culvert and gets 55.0. `_culvert_wall_volume` has multiplied by `barrel_count` since `46fd04a`, the same commit that wrote the fixture with `barrel_count=2` and the expectation of 27.5, so at that time the count did not reach the function and the test passed by accident of plumbing. Now it does. The formula's stated intent is per-barrel wall volume times barrel count; the test's 27.5 was never what the author wrote the formula to produce. Note that `culvert_barrel_volume` (60.0) and `culvert_opening_area` (6.0) are not multiplied by the count, so the multi-barrel semantics of the quantity set are not consistent among themselves, and two adjacent barrels share a wall that the count formula counts twice. Which convention the quantity report should follow is a decision.

### Applied Sections, 3D Centerline default, and two label drifts, 2026-09-07

**Applied Sections supplemental pair.** `test_build_document_applied_section_set_uses_v1_sources` and `test_apply_v1_applied_section_set_creates_result_object` still expected 5 station rows and 5 template ids. They belong to the supplemental sampling family already decided on 2026-09-05. Measured: 5 `regular_sample` rows plus 22 `vertical_curve_supplemental` and 13 `curve_supplemental`, 40 in all. The tests now assert the five source rows by kind, that supplemental kinds are present, and on the persisted object that `SourceSectionCount` is 5 and `StationCount` equals `TotalSectionCount` and the source plus supplemental counts, with one template id per row. No number 40 is hard-coded.

**3D Centerline default display mode.** Four tests expected `source_geometry` as the default: `_normalized_display_mode("")`, the panel combo's current text and item labels, the preview object's `CurveKind` and `CenterlineDisplayMode`, and Build Parametric's `DisplayCurveKind`. `git log -S` shows `41b0346 "feat. Geometry 3D centerline"` introduced Source Geometry with a `source_geometry` fallback and these expectations together, and `fad9e6f "Change screenshot images in README and apply Parametric philosophy"` then changed all three places in one commit: both normalizer fallbacks to `bspline`, the combo default to `B-spline (Display)`, and the item labels to `B-spline (Display)`, `Source Geometry (Engineering)`, `Polyline (Diagnostic)`. That is a coordinated product decision by the maintainer, not drift, and the tests were left behind. The normalization and panel tests now assert the B-spline default. The preview routing test is different: fifteen of its assertions cover Source Geometry interval diagnostics, which would all collapse to zero under the display default, so instead of asserting the default it now passes `display_mode="source_geometry"` explicitly and keeps that coverage intact. The Build Parametric test keeps asserting that the shared Centerline3D result is still the consumed source, because `PreviewSource` and `ConsumedCenterlineSourceMode` remain `centerline3d_source_geometry` and only the display curve changed.

**Two label and field drifts.** The drainage editor's element table header is `Subassembly`, not `Assembly`, consistent with the SubAssembly Designer naming; the test was updated. `SectionEarthworkAreaService.to_section_quantity_rows` never sets `subassembly_ref`, and area rows describe the whole section rather than one Subassembly, so the test's expectation that the field would carry `section_earthwork_area` misused a reference field; it now asserts the field is empty while `quantity_kind` carries the meaning.

### M3 batch 1 on 2026-09-07: rewire shim-backed assertions to service APIs

Entry: `test_build_corridor_command.py` referenced 72 private functions of `cmd_build_corridor.py`, 22 of them single-`return` delegation shims. One of the 22, `_region_surface_role_uses_intersection_exclusion`, is an inline predicate rather than a delegate and stays in the command. The other 21 were rewired.

Method. Each shim's untruncated return expression was read from the AST, the service target was imported and checked to exist, and each service signature was crossed with every call form the test uses (positional count and keyword names). Seventeen matched directly; the remaining four target `*args, **kwargs` wrappers in `intersection_exclusion_geometry_service` and `shared_breakline_tin_builder_service`, which the shims already call with the same forms, so a rename is equally safe there. A first pass was aborted by that pre-check because a method name had been reconstructed from a truncated listing (`boundary_tin_vertices` where the service has `patch_boundary_vertices`); nothing was written until the mapping was verified against source.

Result. 70 call sites across 21 shims now call the service API directly, with 24 import lines added after the file's last top-level import. `test_build_corridor_command.py` no longer references any of the 21; its private reference count fell from 72 to 51, and the shim-backed count from 22 to 1. Five of the 21 are still referenced from other test modules, `architecture/test_v1_package_boundaries.py::test_build_corridor_phase2_owners_are_outside_the_command_module`, `contracts/v1/test_polygon_boundary_service.py::test_xyz_exterior_hull_preserves_turn_tolerance_and_command_wrappers`, `contracts/v1/test_polygon_topology_service.py::test_build_corridor_polygon_topology_wrappers_match_service`. Those references are deliberate: they check that the command's compatibility wrappers delegate to the geometry and shared-breakline services, so they are M4 material to be retired together with the wrappers they guard, not M3 leftovers. The module's failing set is unchanged at 19 before and after, with no new and no resolved test, which is the expected signature of a behavior-preserving rewire; those 19 are pre-existing M8 items unrelated to the shims. Fast tier passes.

M4 readiness for these 21. Still called inside the command module and therefore not deletable yet: `_intersection_tie_in_strip_polygon` (1), `_intersection_practical_exclusion_polygon_candidate_from_boundary_segments` (1), `_tin_surface_with_shared_breakline_constraint_edges` (7), `_tin_surface_with_shared_breakline_metadata` (11), `_suppress_daylight_triangles_above_intersection_surface` (1), `_suppress_daylight_triangles_inside_intersection_slope_face_loop_footprint` (1), `_suppress_daylight_triangles_inside_intersection_surface_footprint` (1), `_trim_daylight_triangles_above_intersection_surface_by_intersection_lines` (1), `_xy_area_from_xyz_points` (1), `_xy_xyz_polygon_self_crossing` (2). These appear in the architecture ratchet's wrapper limits and must be removed from it in the same change that deletes them: `_intersection_surface_tin_with_shared_breakline_constraint_edges`, `_tin_surface_with_shared_breakline_constraint_edges`.

### M3 batch 2 scope and M4 readiness, measured 2026-09-07

The 51 command-module privates still referenced by `test_build_corridor_command.py` are not one population:

| Count | Kind | Disposition |
| --- | --- | --- |
| 2 | thin logic that calls one service (`_build_intersection_slope_face_surface_from_ready_loops`, `_intersection_slope_face_boundary_target_segments`) | M3 batch 2: move the assertion to the service API |
| 19 | orchestration that creates or reads FreeCAD objects (`_corridor_build_review_row`, `_create_corridor_intersection_slope_face_surface_preview`, `_select_and_fit_objects`, ...) | stays in the command test; this is what the command test is for |
| 29 | pure logic with no FreeCAD dependency (`_tin_quality_float` 82 uses, `_set_preview_*` 173 uses, `_shared_breakline_recommended_action`, `_intersection_surface_boundary_review` 137 lines, ...) | not M3: these are M5 extraction candidates, review-row and preview-property logic that belongs in `services/mapping` or `ui/presentation`; their tests move when they do |
| 1 | inline predicate `_region_surface_role_uses_intersection_exclusion` | stays |

So M3 batch 2 is small, and the bulk of the remaining coupling is M5 work rather than M3 work.

M4 readiness for the 21 shims rewired in batch 1. Ten are still called inside `cmd_build_corridor.py` itself (27 call sites; `_tin_surface_with_shared_breakline_metadata` 11, `_tin_surface_with_shared_breakline_constraint_edges` 7, the rest one or two each). Every internal call form matches its service signature, so the internal rewire is a rename like the test rewire was. Deleting the 21 then requires, in the same change: removing the three entries the architecture ratchet keeps in `wrapper_limits` for functions this batch deletes (`_tin_surface_with_shared_breakline_constraint_edges`, `_intersection_surface_tin_with_shared_breakline_constraint_edges`, and the batch-2 wrapper `_build_intersection_slope_face_surface_from_ready_loops`; an earlier line here said two), and removing the three wrapper assertions in `test_polygon_boundary_service.py` and `test_polygon_topology_service.py` that compare `_xy_polygon_exterior_hull_boundary`, `_xy_area_from_xyz_points`, and `_xy_xyz_polygon_self_crossing` against the services. Those two tests are not retired as a whole: each also asserts other command privates that are not in this batch (`_xyz_tuple`, `_intersection_patch_boundary_has_self_crossing`, `_intersection_patch_boundary_rings_intersect`), and the service-side assertions beside them already cover the behavior the wrapper lines duplicated. The M3 batch-1 commit message says "retire"; this record is the accurate version.

How the ratchet enforces `wrapper_limits` settles the mechanics: the loop indexes `command_functions[name]`, so a listed function must exist or the guard errors, which is why the three entries have to go in the same change as the deletions. Directly below it the same test keeps `removed_implementation_names`, a set asserting that named implementations have not been reintroduced into the command module. M4 batch 1 should add all 23 deleted wrapper names to that set, so the deletion becomes a guarded invariant rather than a one-time cleanup, and the guard fails loudly if a wrapper is ever restored under its old name.

### M3 batch 2 on 2026-09-07: the two compatibility wrappers

`_build_intersection_slope_face_surface_from_ready_loops` and `_intersection_slope_face_boundary_target_segments` are documented compatibility wrappers whose bodies are a docstring and one keyword-for-keyword pass-through to `build_intersection_slope_face_surface_from_ready_loops` (`services.builders`) and `intersection_slope_face_boundary_target_segments` (`services.evaluation.intersection_slope_face_boundary_evaluation_service`). They escaped the batch-1 shim count only because a docstring makes the body two statements. The three test call sites now call the services directly; two imports were added. Private references from the command test are now 49, down from 72 at the M3 entry, and every remaining one is either FreeCAD orchestration that belongs in a command test or pure review/preview logic that moves with M5.

### M4 batch 1 on 2026-09-07: delete the 23 rewired wrappers

Scope: the 21 shims rewired in M3 batch 1 plus the two documented compatibility wrappers from M3 batch 2. Preconditions established before editing: no other product module imports any of the 23 from `cmd_build_corridor`; inside the command module every reference is a direct call or the definition itself, with no callback, table, or string reference; and every internal call form matches the service signature it now targets.

Applied in one atomic pass, each replacement expression taken from the wrapper's own body by AST rather than reconstructed by hand:

- 30 internal call sites across 11 names rewired to the service APIs. The count exceeds the 27 measured for the 21 shims because the two batch-2 wrappers also had internal callers.
- 23 wrapper definitions deleted, 239 lines. Compile passes and an AST check confirms no remaining reference or definition of any of the 23 in the module.
- Architecture ratchet: the three `wrapper_limits` entries for deleted functions removed, since the loop indexes them and they must exist; all 23 names added to `removed_implementation_names`, so restoring any of them under its old name now fails the guard. 9 architecture tests pass.
- `test_polygon_boundary_service.py` and `test_polygon_topology_service.py`: three wrapper-equals-service assertions removed; the tests themselves stay because they also cover other command privates and the service-side assertions beside them cover the deleted lines' behavior. Both modules pass, 15 tests.

Fast tier 312 passed. `test_build_corridor_command.py` failing set unchanged at 19, no new and no resolved test. Diff spot-check: every rewired line is a service call, and every deleted span begins at its `def` and is followed by the next `def`, leaving no orphaned docstring or comment. Because this changes a product file, the complete contract suite and the short-term smokes were run before commit: 54 failed / 1,366 passed / 18 skipped before and after with no new failure, and 26 smoke scripts at exit code 0 with no failure output.

### M4 batch 2 scope, measured 2026-09-07 after batch 1

81 single-`return` call-delegating functions remain in `cmd_build_corridor.py`. A pre-check that resolved each one's callee found that 19 of them are not service shims at all: they wrap builtins such as `str`, `max`, `sorted`, `any`, `all` and `'; '.join`, or other command-local helpers (`_audit_field`, `_join_review_notes`, `_project_id`, `_section_region_id`, ...). Those are legitimate one-line helpers of the command module and stay. The M4 population is the other 62: 41 whose every internal call form matches the service signature (rename), 20 with no caller anywhere (delete), and one, `_point_segment_distance_with_ratio`, whose single internal call passes six positionals to a service that takes keywords and needs its arguments rewritten. Classified by who references them, before that exclusion:

| Count | Referenced by | Disposition |
| --- | --- | --- |
| 29 | nothing, anywhere | delete outright; add the names to `removed_implementation_names` |
| 25 | the command module only | rename the internal callers to the service API, then delete |
| 27 | tests | see below |
| 0 | other product modules via `cmd_build_corridor` | none |

The 27 test-referenced shims are not referenced from the command test at all. They are referenced from the service contract tests, `test_xy_geometry_primitives.py`, `test_segment_geometry_service.py`, `test_polygon_boundary_service.py`, `test_polygon_relations_service.py`, `test_polygon_triangulation_service.py`, and `test_convex_polygon_clipping_service.py`, as wrapper-equals-service equivalence assertions, the same pattern as the three assertions trimmed in batch 1. One entry, `_tin_rows_with_shared_breakline_constraint_edges`, is referenced only by the architecture ratchet's last `wrapper_limits` line, not by a behavioral test. The heaviest internal callers are `_xy_distance` and `_xyz_tuple` at 18 sites each and `_xy_polygon_area` at 7.

So batch 2 is the same mechanical cycle as batch 1 with the test-side step being assertion trimming rather than call-site rewiring: verify each internal call form against the service signature, rename internal callers, trim the equivalence assertions, delete, extend the ratchet's removed-names set, and remove the one remaining `wrapper_limits` entry. Test-side handling was enumerated exactly: 26 wrapper-equals-service assertions across six service contract modules. Six of the tests holding them exist only for that comparison, their names say so (`..._wrappers_match_geometry_service`, `..._wrappers_use_geometry_service_results`), and trimming would leave them with no assertion; five of those six test functions are deleted, since the service behavior they compared against is asserted directly elsewhere in the same modules; that was verified for 18 of the 19 compared services. The exception is `triangulate_simple_polygon_points`, asserted only through `test_build_corridor_segment_and_simple_triangulation_wrappers_match_services`, so in that test the wrapper assertion is converted to a direct call of the service with the same expected value rather than removed, and the test is kept under that single assertion. Two tests mix wrapper lines with real service assertions, `test_xyz_exterior_hull_preserves_turn_tolerance_and_command_wrappers` and `test_triangle_relation_handles_touch_disjoint_degenerate_and_touching_cases`, and lose only their wrapper lines. The one argument-form rewrite, `_point_segment_distance_with_ratio`, packs six scalars into three coordinate pairs for `xy_point_segment_distance_with_ratio(point, segment_start, segment_end)`; its single internal caller at the `_intersection_tie_slope_endpoint_pair` area is rewritten to pass the pairs directly.

After it, the shim layer described in section 3.2 is gone and M4 is complete.
### M4 batch 2 on 2026-09-07: delete the remaining 62 delegation shims

Executed by the same AST-driven cycle as batch 1, re-parsing from disk before every step and preserving each line's own ending. Two defects in the batch script were fixed first: the test-editing step was made idempotent so a re-run after a partial application does not fail on already-deleted tests, and the external-reference rule was corrected. The rule had counted a plain name match anywhere in the product tree, which flagged 26 shims falsely because the services define identically named private helpers, `_xy_distance` in the geometry service and `_tin_rows_with_shared_breakline_constraint_edges` in the shared-breakline builder among them. Reference through the command module is what matters, so the check now scans the product tree by AST for a from-import of `cmd_build_corridor` or an attribute on a `*build_corridor*` alias, and keeps the plain-name match only for the test tree. That produced the expected split: 19 local helpers kept, 17 renamed, 44 dead, 1 rewritten.

- Six service contract modules edited as scoped: five wrapper-only tests deleted, one wrapper assertion converted to a direct `triangulate_simple_polygon_points` call, and the wrapper lines trimmed from the two mixed tests. 39 tests pass across the six modules.
- 64 internal call sites rewired across 17 names; the six-positional call of `_point_segment_distance_with_ratio` rewritten to `xy_point_segment_distance_with_ratio((x, y), (x1, y1), (x2, y2))` with its float conversions intact.
- 62 wrapper definitions deleted. The module goes from 24,759 to 24,392 lines and from 779 to 717 top-level functions; the 81 single-`return` call-delegating functions drop to the 19 legitimate local helpers, so the shim layer of section 3.2 is gone.
- Architecture ratchet: the last `wrapper_limits` entry removed and all 62 names added to `removed_implementation_names`. 9 architecture tests pass.
- flake8 then reported 46 imports left unused by the deletion, 40 names in the command module and the now-unused `cmd_build_corridor` import in six test modules. All were removed after confirming by regex that none is reachable through the command module. `flake8 freecad tests` shows no new warning against the pre-existing set.
- Private `cmd_build_corridor._x` references in the contract tests fall from 54 to 28.

Validation: the contract suite was run in four chunks rather than one 46-minute pass, and every chunk matched its slice of the 54-failure baseline exactly, 21 + 2 + 12 + 19, with no new and no resolved test. The chunks total 1,433 tests, the same population as the single-pass run. 26 smoke scripts pass at exit code 0.

One process lesson is recorded here because it cost a full suite run. The first attempt ran the suite in the background and the flake8 import cleanup was applied while it was still running. Four tests that read the command module through `inspect.getsource` failed in that run and passed in isolation afterwards: editing a source file under a running suite shifts the line numbers those tests resolve. A run used as a commit gate must not overlap an edit to the tree it is measuring.

### M5 open decision 2 resolved on 2026-09-10: ownership by consumer, not by content

Measured entry state: 33 `*_rows` functions totalling 2,643 lines, two fewer than the plan's 35 because M3 and M4 removed row-shaped shims. The decision the plan deferred, `services/mapping` or `ui/presentation`, is settled by evidence rather than by taste, and the deciding fact is how the command module and the panel are wired to each other.

`ui/viewers/build_corridor_view.py` never imports the command module. It declares module-level placeholders set to `None` and the command module calls `configure_build_corridor_task_panel_runtime(globals())` at import time, which copies every binding into the viewer's namespace. The row builders sit in the command module because that injection made it possible, not because the command owns them. Two facts follow. A row builder can move to `ui/presentation` without breaking the panel, because the command re-imports it and the injection still carries it across. And `ui/presentation` already contains the pattern to imitate: `shared_breakline_audit_presentation.py` maps a duck-typed audit source through `_value()`, so it reads document objects without importing FreeCAD.

The rule adopted, consistent with the plan's task 1:

- Rows whose consumer is a panel table go to `ui/presentation`, including rows read off document object properties, since duck-typed access keeps the layer free of FreeCAD. Display-only parameters such as an `include_internal` toggle are the signature of this class.
- Rows that feed a normalized output contract go to `services/mapping`, next to the existing 15 mappers.
- Discovery of the document and its objects, `App.ActiveDocument` and the preview-object lookup, stays in the command module. It is the only part that genuinely needs FreeCAD.

### M5 chunk 1 on 2026-09-10: the shared-breakline audit display rows

The plan's task 2, the largest family, taken first. `shared_breakline_audit_display_rows` is 499 lines and pure, and its transitive closure inside the command module is 18 functions and 856 lines with no FreeCAD reference anywhere in it. Two closure members were excluded after measuring their callers: `_unique_text_values` has 65 callers across the command module and `_join_review_notes` has 16, so they are general utilities rather than audit-row code. Fourteen other product modules each define their own `_unique_text_values`, so the presentation module received private copies in the same style instead of an import that would have created a new dependency.

Moved into `ui/presentation/shared_breakline_audit_presentation.py`: 16 functions and 6 constants, 907 lines. The constant set grew from the 4 the functions name directly to 6 once their own references were closed over, and they are emitted in source order because they build on each other. The command module keeps the document read and imports the moved names back; the two import blocks from that module were merged into one, and 11 names with no remaining reference in the command were dropped from it. `shared_breakline_audit_display_rows` is imported with no local caller and marked, because the panel receives it only through the runtime binding map.

`cmd_build_corridor.py` falls from 24,392 to 23,457 lines, and the presentation module grows from 89 to 1,055. The moved code imports no FreeCAD, Part, or Qt, satisfying the milestone's third acceptance criterion for this family.

Validation: compile, flake8 with no new warning, 9 architecture tests, and the contract suite in three chunks totalling 1,433 tests, each matching its slice of the 54-failure baseline exactly, 21 + 19 + 14, with no new and no resolved test. 26 smoke scripts pass at exit code 0. Review tables are unchanged by construction, since the moved functions are byte-identical and the panel resolves them through the same binding, but the milestone still carries a level 7 requirement and the audit table should be confirmed in the GUI before M5 is called complete.

### M5 chunk 2 on 2026-09-10: the intersection contract review rows

The plan's task 3. The naive reading of it, move `corridor_intersection_contract_review_rows` and everything it calls, does not survive measurement: its transitive closure is 110 functions and 3,122 lines and pulls in evaluation orchestration and document access that the ownership rule keeps in the command. `corridor_intersection_patch_prerequisite_result` has 11 callers elsewhere in the module, `_corridor_build_preview_object` has 19, `_section_station` 16, `_unique_text_values` 60. That function is not a display leaf; it evaluates, reads the document, and shapes rows in one body.

So the chunk took the row-shaping leaves instead, the five functions that only format contract rows: `_roundabout_boundary_readiness_contract_review_row`, `_intersection_contract_display_status`, and the three `*_contract_review_rows` builders for the upper slope-face panel, the slope-face cells, and the shared-boundary graph. All five are pure; together with their closure they are 302 lines with no FreeCAD reference.

Two moved unchanged. The other three began by looking their own preview object up, all three with the same role, `intersection_slope`, on the same document, so the lookup moved out rather than in: the caller resolves the object once and passes it, and each function now takes `obj`. Naming the parameter after the variable the bodies already used means not one body line changed, which an AST comparison against the previous commit confirms for all five, byte for byte after the removed lookup.

They went into a new `ui/presentation/intersection_contract_review_presentation.py`, which imports the two audit-row parsers from its sibling module where chunk 1 put them, and carries its own private `_unique_text_values` and `_join_review_notes` for the same reason chunk 1 did. That is now the second copy of those two helpers inside `ui/presentation`; a shared helper module is worth doing when a third module needs them, and is not worth the churn yet. No test referenced any of the five functions, so no test changed.

`cmd_build_corridor.py` falls from 23,457 to 23,185 lines. Remaining in it from this family is the evaluation and document work the rule assigns to a command.

Validation: compile, flake8 clean on both files, 9 architecture tests, the contract suite in three chunks totalling 1,433 tests each matching its slice of the 54-failure baseline, 21 + 19 + 14, with no new and no resolved test, and 26 smoke scripts at exit code 0.

### M5 chunk 3 on 2026-09-10: the audit rows rejoin their display rows

Chunk 1 moved `shared_breakline_audit_display_rows`; this moves the builder that feeds it, `corridor_shared_breakline_audit_rows`, the largest remaining row function at 318 lines. Its closure is small, 9 functions and 513 lines, and only the top function touches FreeCAD, through `App.ActiveDocument` and the preview-object lookup.

The lookup sat inside the loop, so the split falls out of the shape: the command resolves the document, walks `CORRIDOR_BUILD_REVIEW_OBJECTS`, and collects `(role, title, object_name, obj)` entries, and presentation loops over those entries and shapes every row. Naming the tuple after the four variables the loop already bound leaves the 307-line body untouched, confirmed line by line against the previous commit, with the new `for` header the only difference. What remains in the command is twelve lines of document discovery.

Six helpers moved with it into the same module chunk 1 created, all byte-identical: `_shared_boundary_graph_pair_audit_rows`, `_shared_boundary_graph_consumer_audit_rows`, `_shared_breakline_recommended_action`, the two near-kept-warning helpers, and `_normalize_corridor_build_review_status` with its status-value constant. The module already held `_shared_breakline_recommended_action_from_notes` and the audit-row parsers from chunk 1, so the moved code found its callees locally. Three helpers stayed: `_corridor_build_preview_object` with 18 callers elsewhere, `_join_review_notes` with 9, and the review-status normalizer is imported back for its 4 remaining callers.

Fourteen test call sites reached three of the moved helpers through the command module and were rewired to the presentation module, 11 in `test_build_corridor_command.py` and 3 in `test_intersection_shared_boundary_graph_builder.py`. They were found the way M3 found its own: by running the suite, not by reading the diff. The audit that only checks the command module's own body would have missed them, and that is worth remembering for the remaining chunks.

`cmd_build_corridor.py` falls from 23,185 to 22,694 lines, 2,065 below where M4 started. `shared_breakline_audit_presentation.py` is now 1,562 lines and still imports no FreeCAD, Part, or Qt.

Validation: compile, flake8, 9 architecture tests, the contract suite in three chunks totalling 1,433 tests each matching its slice of the 54-failure baseline, 21 + 19 + 14, and 26 smoke scripts at exit code 0.

### Level 7 manual confirmation on 2026-09-13

The maintainer confirmed in the FreeCAD GUI that the review surfaces touched by M5 chunks 1 to 3 render as before: the shared-breakline audit table, including its internal-row toggle, and the intersection contract review table. The same session confirmed the M8 ditch flowline elevation fix in the Cross Section viewer, where the benched side slope and flowline now run continuous with the ditch bottom instead of sitting one profile elevation above it. This closes the level 7 requirement for the work committed so far; chunks after this point need their own confirmation.

### M5 chunk 4 on 2026-09-13: the drainage flow review rows, and a shared review_text helper

The drainage review family was measured before choosing. `corridor_drainage_review_rows` and `corridor_intersection_drainage_review_rows` both reach `corridor_intersection_patch_prerequisite_result` and the region-boundary machinery, closures of well over a hundred functions, so they wait until the evaluation they call has an owner. `corridor_drainage_flow_review_rows` is separable: 104 lines whose helpers are pure.

It is also the first row builder in M5 with document side effects interleaved with the shaping. It removes the `ReviewIssueDrainageFlowRoutes` preview object on each of its three placeholder paths, and computes a per-route highlight mode by reading the applied sections from the document. Both stay in the command. The split:

- `ui/presentation/drainage_flow_review_presentation.py` shapes one row per Flow Route from the drainage and structure models and returns an empty list when there are none. The highlight mode arrives as a `highlight_mode_for_route` callable, so presentation never sees the document and the lookups still happen once per row in the original order. The three placeholder rows come from `drainage_flow_review_placeholder_row` with the original notes as named constants.
- The command resolves the document and both models, removes the preview object and returns a placeholder on the missing-model, preset-model, and no-routes paths exactly as before, and passes the highlight lookup in. The structure model is still looked up only after the two early exits.

Verified against the previous commit rather than by reading: the three moved helpers are byte-identical, the row loop differs in exactly one line, the highlight call, the three setup statements are AST-identical, and the three placeholder rows are equal to the original literals in values and in key order. A synthetic model exercising the ready, broken-ref, empty-chain, and no-structure paths produced the expected statuses and station span.

This chunk is also where the text helpers stopped being copied. Chunk 2 recorded that a shared module was worth it once a third presentation module needed `_unique_text_values` and `_join_review_notes`; this was the third. `ui/presentation/review_text.py` now holds `unique_text_values`, `join_review_notes`, and `display_source_ref`, their bodies identical to the command's, and the two earlier modules import them under their private names instead of carrying copies, so none of their call sites changed. The command keeps its own copies, which have 50 and more callers there.

`cmd_build_corridor.py` falls from 22,694 to 22,560 lines.

Validation: compile, flake8, 9 architecture tests, the contract suite in three chunks totalling 1,433 tests each matching its slice of the 54-failure baseline, 21 + 19 + 14, and 26 smoke scripts at exit code 0. The Drainage Flow review table is a user-visible surface changed after the 2026-09-13 confirmation and needs its own level 7 check.

### M8 decisions A and B on 2026-09-13

The two `test_result_builders.py` failures that needed a product decision were settled by the maintainer, both on the recommended option.

- Decision A, A-2. `test_applied_section_service_orients_bench_side_slope_up_for_cut_context` expected derived `side_slope` and `daylight` rows in `subassembly_rows`, an expansion no release has implemented and no product code reads. The test keeps what it was really protecting, that in a cut context the benched side slope climbs to existing ground, through its point-elevation and `bench_cut_fill_context` diagnostic assertions, and drops the four lines about derived rows. No product change.
- Decision B, B-1. `culvert_wall_volume` for a two-barrel culvert is 55.0, the formula's `x barrel_count` as its author wrote it; the old 27.5 only passed while `barrel_count` failed to reach the function. The test now expects 55.0 with a comment naming the convention. No product change.

B-1 leaves two known inconsistencies open, recorded here so they are not mistaken for settled: adjacent barrels share a wall, so multiplying by the barrel count overstates wall volume, and `culvert_barrel_volume` and `culvert_opening_area` are still per-structure while wall volume is per-barrel. Both belong to a quantity report design task, and matter because quantities feed estimates.

The light contract chunk went from 21 failures to 19, the two resolved tests being exactly these, with no new failure. The contract baseline is now 52.

One run of that chunk hung and was stopped: the test process sat with a window titled "ParametricRoad v1 - Structures" open and 38 seconds of CPU after more than ten minutes, a modal dialog waiting for input. The same chunk had finished in 70 seconds an hour earlier on code that differed only in these two tests, and the verbose re-run under a hard timeout finished in 156 seconds without hanging, so the hang did not reproduce and the test that opened the window was not identified. If it recurs, the verbose log's last started test names it.

### M5 chunk 5 on 2026-09-13: the subassembly kind guided review rows

The next three candidates were measured first. `corridor_build_review_rows` is a hub, 43 functions and 1,472 lines reaching intersection, drainage, and Applied Section review, so it is not a chunk. The two small ones are `_corridor_roundabout_build_review_rows` and `corridor_subassembly_kind_guided_review_rows`; this chunk takes the second.

Its split is the cleanest so far because the document work is all at the top. The command resolves the document, converts the Applied Section set, returns an empty list when there is none, and orders the sections by station with `_station_ordered_applied_sections`, which has 20 other callers and stays. Everything after that reads only `sections`: the per-kind aggregation of sections, points, links, shapes, surface roles, and preset statuses, then the ordered rows with their warnings. The extraction script asserts that none of the moved statements load `doc`, `document`, `applied`, or `App` before writing anything.

The shaping went into `ui/presentation/subassembly_guided_review_presentation.py` as `subassembly_kind_guided_review_rows(sections)` together with `SUBASSEMBLY_GUIDED_REVIEW_KIND_ORDER`, which had no other use in the command. `_subassembly_kind_display_name` and `_format_count_summary` still have callers in the command's highlight and summary code, so the module holds private copies, and imports `display_source_ref` from `review_text`. The moved body, both copies, and the constant are identical to the previous commit. `corridor_subassembly_kind_guided_review_rows` keeps its name and signature, which `test_intersection_command.py` imports; no test changed.

Two editing slips were caught before validation rather than after. The script left one blank line without a carriage return where the constant had been, which surfaced as a new line-ending warning on a file that had shown none; and that blank line was itself an addition the original layout did not have. Both were removed, and the command diff is now two added lines and 128 removed.

`cmd_build_corridor.py` falls from 22,560 to 22,434 lines.

Validation: compile, flake8, 9 architecture tests, and the contract suite in three chunks, each run verbosely under a hard timeout after the earlier hang, totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14. The two roundabout guided-review tests that call this function passed. 26 smoke scripts pass at exit code 0. The guided review step list in the Build Corridor panel is user-visible and needs a level 7 check alongside the Drainage Flow table.

### Level 7 manual confirmation of M5 chunks 4 and 5, on 2026-09-13

The maintainer checked the Drainage Flow review table and the subassembly-kind guided review steps in the Build Corridor panel and found no problems.

### M5 chunk 6 on 2026-09-13: the roundabout Results tab rows

`_corridor_roundabout_build_review_rows` is 87 lines with one caller, `corridor_build_review_rows`, and its only helper `_corridor_roundabout_review_row` has no other caller. It differs from the earlier chunks in where the document work sits: after the roundabout gate, three `doc.getObject` reads for the apron, subgrade, and slope-face previews are interleaved with the row appends.

Those reads are side-effect free and nothing between them touches the document, so the command now performs them up front and passes the objects in. The command keeps the document, the intersection preview lookup, and the `IntersectionKind` roundabout gate; `roundabout_build_review_rows(intersection_obj, *, apron_obj, subgrade_obj, slope_face_obj)` in the new `ui/presentation/build_review_presentation.py` shapes the circulatory, apron, subgrade, and breakline-readiness rows. The parameters carry the names the body already used, so the moved lines are the original lines with the three lookups removed and nothing else changed, confirmed against the previous commit for all 75 lines and for the helper.

Because the reads moved, identity of text was not treated as enough. The previous commit's function and the new command-plus-presentation pair were executed side by side against the same fake documents: not a roundabout, no intersection object, all outputs ready, a shared-breakline mismatch, and a missing subgrade with an empty circulatory surface. Rows matched in values and key order in every case, and both return an empty list for no document.

The module is named for the Results tab review rather than for roundabouts because the remaining leaves of `corridor_build_review_rows`, the hub this function feeds, belong in the same place.

`cmd_build_corridor.py` falls from 22,434 to 22,339 lines.

Validation: compile, flake8, 9 architecture tests, the contract suite in three verbose, time-limited chunks totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, and 26 smoke scripts at exit code 0. The roundabout Results tab rows need a level 7 check.

### Level 7 manual confirmation of M5 chunk 6, on 2026-09-13

The maintainer checked the roundabout rows in the Build Corridor Results tab and confirmed them.

### M5 chunk 7 on 2026-09-13: the Results tab review row and its note helpers

`corridor_build_review_rows`, the Results tab hub, stays in the command for now; this chunk moved its main leaf. `_corridor_build_review_row` is 153 lines, and its closure adds 13 pure note helpers, among them `_intersection_surface_review_notes` at 179 lines, `_with_corridor_consumer_hardening_warning`, `_shared_breakline_review_note`, and `_corridor_build_review_output_path`.

The row function touched the document in exactly two lines. When a preview object is missing and no diagnostic object explains it, it called `_intersection_slope_face_surface_absent_note(document)` or `_intersection_tie_slope_surface_absent_note(document)`, which look up the Intersection Surface preview to say why the dedicated surface is absent. Those two helpers stay in the command. The row function's `document=None` parameter became `absent_note_for_role`, a callable the hub supplies through a small new command helper, `_corridor_build_review_absent_note(document, role)`, that dispatches to the same two functions. The callable is invoked only on the branches that called the helpers before, so the lookups still happen only when they did. Against the previous commit, the row function changed in its signature and those two lines and nowhere else, and all 13 helpers and the private `_display_source_id` copy are identical.

Because a signature changed, the previous commit's row function and the new one were also run side by side over ten cases: a missing slope, tie-slope, and design preview with and without diagnostic text or status, a centerline, a design surface with clipping and applied-section diagnostics, an empty daylight surface, an intersection slope face, and a roundabout ownership warning. Rows matched in values and key order.

One behaviour narrowed, deliberately: called with no callable, a missing slope or tie-slope preview now gets an empty note where the old function would have fallen back to `App.ActiveDocument`. No production caller omits it, since the hub always passes one, and every test that calls the row directly passes a built object, so that branch is not reached.

Four helpers keep callers in the command and are imported back: the row itself, `_intersection_surface_review_notes` for the surface preview it annotates, `_intersection_slope_face_upper_panel_review_note`, and `_surface_patch_review_status_note`. Eight test call sites in `test_build_corridor_command.py` now reach the moved helpers through `build_review_presentation`, and all eight tests that hold them pass.

`cmd_build_corridor.py` falls from 22,339 to 21,655 lines, and `build_review_presentation.py` is 842 lines.

Validation: compile, flake8, 9 architecture tests, the contract suite in three verbose, time-limited chunks totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, and 26 smoke scripts at exit code 0. `test_corridor_build_review_rows_summarize_preview_outputs`, which exercises the hub and is in the baseline, fails with the same assertion as before; its reported line moved from 8925 to 8926 because the test module's presentation import grew by one line.

The intermittent hang seen earlier recurred once, on the first run of `test_build_corridor_command.py`, at `test_build_corridor_panel_updates_selected_surface_transition_spacing`. The hard timeout stopped it. Run alone, that test fails in four seconds on its known baseline assertion, and the whole module then ran to completion in 68 seconds on the same tree with the same result as the baseline. The hang has now appeared on two unrelated trees and follows panel tests that fail in the baseline, which points at state a failing Qt panel test leaves behind rather than at either change. It is not diagnosed; the verbose log under a timeout is how the next occurrence will be located.

### M5 chunk 8 on 2026-09-13: two review helpers nothing referenced

A survey of the remaining review functions, 46 of them and about 2,000 lines, found two with no reference anywhere in the repository except their own definitions: `corridor_subassembly_guided_review_summary`, 80 lines, and `_intersection_drainage_element_rows`, 2 lines. `git grep` over every tracked file returns only the `def` line for each. Deleting them strands nothing else: `_intersection_drainage_coverage`, the second one's only callee, has another caller, and flake8 reports no import left unused. Both names were added to `removed_implementation_names` in the architecture ratchet so they cannot quietly return. `cmd_build_corridor.py` falls from 21,655 to 21,569 lines.

Validation: compile, flake8, 9 architecture tests, and the contract suite in three chunks matching the 52-failure baseline, 19 + 19 + 14, with no new and no resolved test.

### The intermittent test hang: cause found

The hang recorded under chunk 7 and the M8 decisions happened again during this chunk's gate, this time at `test_structure_editor_command.py::test_structure_editor_reopens_with_applied_rows_and_selected_detail`, matching the "ParametricRoad v1 - Structures" window seen the first time.

The cause is in how the suites were being run, not in the code under test. `scripts/run_local_validation.ps1` runs contract tests through `scripts/run_pytest_with_qt.py`, which creates the QApplication and replaces `QMessageBox.information`, `warning`, `critical`, and `question` with functions that return immediately, so that unattended runs never block on a modal dialog. The M4 and M5 gates recorded above ran `python -m pytest` directly and so ran without that replacement. Any test path that reaches a real message box then waits for a click that never comes.

That test shows the mechanism. It suppresses `cmd_structure_editor._show_message` around its first apply, but the Structures panel in `ui/editors/structure_editor.py` receives `_show_message` through the same globals-injection pattern as the Build Corridor panel and holds its own reference, so replacing the command module's attribute does not reach the panel, and the panel's apply opens `QMessageBox.information`. Why the block is intermittent rather than constant was not established; it does not need to be, since the documented runner removes the modal entirely.

Consequences for the record above. The before-and-after comparisons remain valid, because every baseline and every chunk result was produced the same way. But those runs were not the documented tier commands, and the failure baseline may differ under the Qt runner if some baseline failures come from unpatched message boxes. From M5 chunk 9 on, gates use `scripts/run_pytest_with_qt.py`, starting from a baseline re-measured with it. The test's ineffective patch is a separate, small test defect worth fixing on its own.

### Qt runner baseline, re-measured on 2026-09-13

Before chunk 9 the contract baseline was measured again on the committed tree with `scripts/run_pytest_with_qt.py`, the runner the validation script uses. It is identical to the plain-pytest baseline: 19 + 19 + 14 = 52 failures, the same tests. The earlier comparisons therefore stand, and the only effect of the runner is that modal message boxes no longer block. None of the runs below hung.

### M5 chunk 9 on 2026-09-13: the Intersections guided review notes

`corridor_intersection_review_summary` builds the Intersections guided review step. Its closure is 58 functions because it calls `corridor_intersection_patch_prerequisite_result` and the region-boundary rows, both evaluation, so the summary itself stays. Its four note helpers do not evaluate: `_intersection_patch_boundary_review_notes`, `_intersection_grading_review_notes`, and `_intersection_surface_quality_review_notes` each resolve the document, look up the intersection preview, and shape notes from its properties, and `_intersection_exclusion_review_notes` does the same over the design and daylight previews.

The command helpers keep their names and signatures, because the summary calls them after its early returns and `test_build_corridor_command.py` calls the exclusion helper with a document. Each is now document resolution and the preview lookup followed by a call into the new `ui/presentation/intersection_review_presentation.py`. The three single-preview functions there take `obj` and carry the original lines from the None guard on, unchanged. The exclusion function takes the two previews by role, and its loop's lookup became a dictionary read, the only line that differs; the command builds that dictionary in the same design-then-daylight order the loop looked them up. `_intersection_exclusion_practical_footprint_recommended_action`, used only by the exclusion notes, moved with them unchanged.

The previous commit's four helpers and the new command-plus-presentation pairs were run side by side over five document states: none, empty, intersection preview only, all previews with warnings on every path, and a bare intersection with a clipped design preview. All returned identical values.

Two smaller moves followed from the rules recorded earlier. `_display_source_id` is now needed by two presentation modules, so it joined `review_text` as `display_source_id` and `build_review_presentation` imports it instead of keeping its copy; the command keeps its own for three callers and the panel binding. And `_surface_patch_review_status_note`, imported back into the command in chunk 7 for the surface quality notes, lost its last command caller and left that import. Four test assertions on the recommended action now reach it through its new owner.

`cmd_build_corridor.py` falls from 21,569 to 21,420 lines.

Validation, with the Qt runner: compile, flake8, 9 architecture tests, the contract suite in three chunks totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, including the skewed-footprint guided review test and the recommended-action test, and 26 smoke scripts at exit code 0. The Intersections guided review step and the Results tab review rows from chunk 7 need a level 7 check.

### M5 chunk 10 on 2026-09-13: the Applied Sections summary and surface-role notes of the Results tab

Two more leaves of `corridor_build_review_rows`. `corridor_applied_sections_review_summary`, 64 lines, gives every Results tab row its Applied Section context; `_subassembly_surface_role_review_note`, 62 lines, appends the Subassembly link coverage for a row's surface role. Both convert the document's Applied Section set on their first line and read only that set afterwards.

Both keep their names and signatures, since the panel binding and `test_build_corridor_command.py` call the summary with a document, and are reduced to that conversion followed by a call into `build_review_presentation`: `applied_sections_review_summary(applied)` and `subassembly_surface_role_review_note(applied, *, surface_role)`, each carrying the original lines from the None guard on without a change.

With them moved the two row decorators the hub applies, `_with_applied_section_review_summary` unchanged and `_with_subassembly_surface_role_review_note`, plus four pure helpers they used and nothing else calls: `_review_surface_role_for_result_role`, `_text_count_map`, `_first_active_structure_ref`, and `_section_structure_refs`. The surface-role decorator used to take the document and convert the Applied Section set only when a row's role maps to a surface role. It now takes a note callable in its place, which the hub supplies around the command helper, so the conversion still happens only for those rows; that parameter and the one call are the decorator's only changed lines.

`_format_count_summary` is now needed by two presentation modules, so it joined `review_text` as `format_count_summary` and the subassembly guided review module imports it instead of its copy. Inside `review_text` it calls `display_source_ref`, the one token that differs from the command's copy, which keeps its own for three callers. `build_review_presentation` also holds a private `_unique_refs`, as the other modules in the codebase do.

Run side by side with the previous commit's code: the summary over no document, no Applied Sections, an empty set, and a populated set with regions, assemblies, structures, ditch points, daylight widths, diagnostics, and an unparseable station; the surface-role note for three roles over those sets; the decorator over eight rows, where the note callable was invoked for exactly the roles with a surface role; and the count summary through the command's copy, `review_text`, and the guided review module. All matched.

`cmd_build_corridor.py` falls from 21,420 to 21,241 lines.

Validation with the Qt runner: compile, flake8, 9 architecture tests, the contract suite in three chunks totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, and 26 smoke scripts at exit code 0. The Applied Section columns and surface-role notes of the Results tab join the pending level 7 check.

What remains of the Results tab hub in the command is the hub itself and five intersection rows it adds after the `intersection` role, the upper slope-face panel, surface replacement readiness, tie-in continuity, grading ownership, and drainage handoff gate. Each reads intersection models or evaluates, so they need the evaluated result passed in rather than only a lookup lifted out.

### M5 chunk 11 on 2026-09-13: four intersection rows of the Results tab

Four of the five rows `corridor_build_review_rows` adds after its `intersection` role: the upper slope-face panel, surface replacement readiness, tie-in continuity, and grading ownership, 183 lines together. Each looks up an intersection preview and shapes a row from its properties. Two also read the document partway through, after their own early returns: tie-in continuity asks `_intersection_applied_section_station_span` for the Applied Section station span, and grading ownership asks for that span and for `_intersection_grading_profile_refs`. Nothing outside the command references any of the four.

Each command row keeps its name and signature, resolves the document and the preview exactly as before, and passes the object to a function of the same subject in `build_review_presentation`. The moved lines start at the None guard and are unchanged, except the three calls to the document helpers, which became calls to `station_span_for` and `profile_refs_for` callables that the command supplies around the same helpers.

Checked against the previous commit by running both side by side over five documents, none, empty, bare previews, fully populated previews, and a ready replacement gate, while recording every call to the two document helpers. All four rows returned identical results in every case, and the helpers were called in the same order with the same arguments, so a row that returns early still never reaches the document a second time.

`_intersection_slope_face_upper_panel_review_note` lost its last command caller and left the command's import. `cmd_build_corridor.py` falls from 21,241 to 21,083 lines.

Validation with the Qt runner: compile, flake8, 9 architecture tests, the contract suite in three chunks totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, and 26 smoke scripts at exit code 0. These rows join the pending level 7 check of the Results tab.

Left in the hub's intersection branch is `_corridor_intersection_drainage_handoff_gate_row`, which reads the drainage model.

### M5 chunk 12 on 2026-09-13: the Intersection Drainage Handoff Gate row

The last row of the Results tab hub's intersection branch, 85 lines. After looking up the intersection preview it reads two models from the document, the intersection's drainage policy rows through `_intersection_drainage_policy_rows` and the DrainageModel, and then decides from them whether accepted drainage references reach the model.

Unlike the rows in chunk 11, both reads happen unconditionally once the preview exists and before the row's gate, so no callable was needed. The command row keeps its name and signature, the lookup, the None guard, and both reads in their original order, and passes the policy rows and the model to `intersection_drainage_handoff_gate_row(obj, *, policy_rows, drainage_model)` in `build_review_presentation`. The moved body is the original from the intersection id on with exactly those two read lines removed. The command also recomputes the intersection id it needs for the policy lookup, a pure property read.

Run side by side with the previous commit over seven documents, recording each model read: no document, no preview, a preview with nothing to hand off, hints only, an accepted policy whose element and route are in the model, a locked policy referencing a missing element, and a policy with no model and no intersection id. Rows matched, and both versions read the intersection model then the DrainageModel in the same cases.

`cmd_build_corridor.py` falls from 21,083 to 21,008 lines.

Validation with the Qt runner: compile, flake8, 9 architecture tests, the contract suite in three chunks totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, and 26 smoke scripts at exit code 0. The row joins the pending level 7 check of the Results tab.

With this the hub's intersection branch has no row shaping left in the command. The hub itself, `corridor_build_review_rows`, is now iteration over `CORRIDOR_BUILD_REVIEW_OBJECTS`, preview and diagnostic lookups, and calls to the command rows, which is document coordination.

### M5 chunk 13 on 2026-09-13: the Roadside Drainage station review rows

`corridor_drainage_review_rows`, 115 lines, fills the Drainage Surface review table with one row per Applied Section station, then appends the intersection drainage row. Three kinds of work were mixed in it. It reads three models from the document, Applied Sections, the RegionModel, and the DrainageModel. For every station it finds the active ditch Drainage Elements through `_active_ditch_drainage_rows`, which runs `StationContextResolver`, an evaluation service. And at the end it calls `corridor_intersection_drainage_review_rows`, which evaluates intersection patch prerequisites. None of those belong in presentation; everything else in the function is row shaping.

The command keeps its name and signature and all three kinds of work. It reads the models, passes the Applied Section set to `drainage_review_station_rows(applied, *, active_ditch_rows_for)` in the new `ui/presentation/drainage_review_presentation.py`, and appends the intersection rows when there are station rows. The moved loop is unchanged except that the five-line lookup call became `active_ditch_rows_for(station)`, a callable the command builds around the same function and models, so the resolver still runs once per station in station order. The two placeholder rows, no Applied Sections and no station rows, come from `drainage_review_placeholder_row` with the original notes as named constants.

The original returned early without appending intersection rows exactly when its first row had an empty station, which only the placeholder has, since real rows carry a float. The command now tests the empty result directly, the same condition stated plainly.

Seven pure helpers the shaping used moved unchanged: the source-surface mismatch notes, the ditch point context by side, the two side-normalizing helpers, `_drainage_point_side`, the marker point, and `_drainage_review_marker_name`. The last two of those are imported back for the highlight and focus code and for the intersection drainage row, which share the marker naming. `_unique_refs` is now needed by two presentation modules, so it joined `review_text` as `unique_refs` and `build_review_presentation` imports it instead of its copy.

The previous commit's function and the new pair were run side by side on four documents, none, no Applied Sections, no station rows, and a mixed set with unsorted stations, a missing section, a one-sided section, a section without ditch points, and an active ditch element on both sides, while recording every model read, active-ditch lookup, and intersection call. Rows matched in values and key order, and the lookups and calls happened in the same order with the same arguments.

The note constants in this module and in `drainage_flow_review_presentation.py` from chunk 4 were written with single quotes by the extraction scripts; both now use the codebase's double quotes, with their values checked unchanged.

`cmd_build_corridor.py` falls from 21,008 to 20,810 lines.

Validation with the Qt runner: compile, flake8, 9 architecture tests, the contract suite in three chunks totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, including the four roadside drainage review tests and the three intersection drainage review tests, and 26 smoke scripts at exit code 0. The Drainage Surface review table needs a level 7 check.

### M5 chunk 14 on 2026-09-13: the intersection drainage review row

`corridor_intersection_drainage_review_rows`, 90 lines, adds the Suggested Inlet row at the end of the Drainage Surface review table. It is the first M5 target whose front half is mostly evaluation. It widens the Applied Section set with intersection tie-in sections, evaluates the patch prerequisites, collects patch finished-grade points, chooses the low point and the points level with it, reads the DrainageModel, and evaluates which Drainage Elements cover the control regions and the low-point station. Only then does it decide ready, warn, or missing and build the row.

So the split is by result rather than by lookup. The command keeps its name and signature, which three tests call directly, and every one of those steps, and passes their results, the prerequisite, the patch points, the low point and its level set, and the coverage, to `intersection_drainage_review_rows` in `drainage_review_presentation`. The presentation function is the original statements for the low-point elevation, the intersection id, the control region refs, and everything from the coverage rows on, in their original order and unchanged. The intersection id and control refs are pure reads of the prerequisite used only by the row, so they moved; the low-point elevation is also still computed in the command, where the level set needs it. `_intersection_patch_fg_points` and `_intersection_drainage_coverage` stay: they are engineering evaluation, candidates for `services/evaluation` rather than presentation.

The previous commit's function and the new pair were run side by side with each evaluation step replaced by a recording stub: no Applied Sections, a blocked prerequisite, no patch points, covered, candidates only, and no coverage with an empty intersection id, each at two marker start indexes. Rows matched in values and key order, and the evaluation steps ran in the same order with the same low-point station.

`cmd_build_corridor.py` falls from 20,810 to 20,755 lines.

Validation with the Qt runner: compile, flake8, 9 architecture tests, the contract suite in three chunks totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, including the three intersection drainage review tests, and 26 smoke scripts at exit code 0. The Suggested Inlet row joins the pending level 7 check of the Drainage Surface table.

### M5 chunk 15 on 2026-09-14: the intersection contract review body

`corridor_intersection_contract_review_rows`, 270 lines, is the function whose leaves chunk 2 took and which the plan named as task 3. Its first 22 statements are the part that stays in a command: the IntersectionModel and Applied Section reads, eight `IntersectionEvaluationService` calls, the tie-slope result and Applied Section window rows, which evaluate patch prerequisites, and three properties of the intersection preview. The rest, from `rows = []` to the return, is row shaping over those results, with one more preview lookup in the middle.

The command keeps its name and signature, which the panel binding, two contract modules, and two regression smokes use, all of that setup, and the missing-model placeholder. It now also performs the slope-face preview lookup before the shaping, and passes the twelve results the shaping reads to `intersection_contract_review_rows` in `intersection_contract_review_presentation`, next to the leaves chunk 2 put there. The moved lines are the original from `rows = []` on with the lookup removed and one call changed: `_intersection_slope_face_loop_row_blocking_reasons` stays in the command, because it runs the slope-face surface ring validity check that the command's surface generation readiness also uses, and arrives as a `slope_loop_blocking_reasons_for` callable.

Five pure text helpers moved unchanged: the contract source status and diagnostics, and the tie-slope window summary note with its diagnostics and endpoint-by-road helpers. The endpoint helper is imported back for the tie-slope surface builder's metadata. Five names the command had imported from this module in chunk 2 lost their last command use and left the import; none is reached through the command module anywhere.

Run side by side with the previous commit against a fake evaluation service and recording stubs for every other step, over a tee intersection with internal rows hidden and shown, a roundabout, and a missing model. Rows matched in values and key order, and every evaluation call and lookup happened in the same order, with one intended difference: the slope-face preview lookup now precedes the two blocking-reason callbacks instead of following them, which changes nothing since the callbacks never read the document.

`cmd_build_corridor.py` falls from 20,755 to 20,418 lines.

Validation with the Qt runner: compile, flake8, 9 architecture tests, the contract suite in three chunks totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, and 26 smoke scripts at exit code 0. Seven contract-review tests fail, all of them in the baseline. The Intersections contract table in the Build Corridor panel needs a level 7 check.

### M5 on 2026-09-14: the presentation half is done; what remains is services work

Two families were measured for chunk 16 and neither belongs in `ui/presentation`. Both were left in place, and the decision about them is recorded here rather than made by extraction.

**Region boundary rows.** `corridor_region_boundary_rows`, 99 lines, has a closure of 45 functions and 850 lines. Its core is `_region_boundary_diagnostics`, which compares adjacent Applied Sections against `REGION_BOUNDARY_WIDTH_JUMP_THRESHOLD`, the subgrade depth threshold, and two daylight thresholds: an engineering continuity rule. Its rows are consumed by `corridor_intersection_patch_prerequisite_result`, an evaluation; by `create_corridor_region_surface_previews` and the surface transition builders; and only then by the panel. Under the ownership rule, rows feeding evaluation and builders are not presentation. The pure part belongs in `services/evaluation`, next to `region_resolution_service.py` and `station_context_resolver.py`. The document-dependent parts are threaded through it: `_region_boundary_rows_from_source_regions` takes the document, `_region_generated_object_summary` checks which preview objects exist, and the preview object naming helpers are shared with the builders. So the split is a design change, not a move.

**Audit rows stored on preview objects.** `_shared_breakline_segment_rows`, `shared_breakline_solid_boundary_trace_rows`, `_intersection_shared_boundary_graph_audit_rows`, `_intersection_shared_boundary_graph_segment_rows`, and `_slope_face_issue_station_rows` serialize result models into string rows written to preview object properties by the `_attach_*_preview_metadata` functions. The solid boundary trace rows are documented as input for downstream solid boundary consumers, and the audit rows are read back by the parsers in `shared_breakline_audit_presentation`. That is a normalized contract, which the rule assigns to `services/mapping`. The evidence is stronger than the rule. `services/builders/intersection_slope_face_tin_builder_service.py` holds copies of three of these serializers, and `shared_breakline_tin_builder_service.py` holds a copy of one, all four identical to the command's. A single mapper would remove the duplication and let the builders and the command share one serializer.

**Where M5 stands.** Chunks 1 to 15 moved every review row builder whose job was to format results for a panel table. What remains in the command are evaluation rules and serialization contracts, both outside the presentation layer. The milestone's first acceptance criterion, no review row calculation in the command, can only be met by moving those into `services/evaluation` and `services/mapping`. That is new service design and deduplication against the builders, larger and riskier than the presentation moves. It is left as a decision for the maintainer: extend M5 to cover it, or close M5's presentation scope and continue with M6.

### M6 entry, measured 2026-09-14

20 `create_*_preview` functions totalling 3,157 lines, down from the plan's 26 and 3,243 because M3 to M5 removed some. The largest are `create_corridor_intersection_surface_preview` at 719 lines, `_create_corridor_intersection_slope_face_surface_preview` at 388, `create_corridor_daylight_surface_preview` at 242, and four roundabout and tie-slope previews between 148 and 181.

The 719-line function is 16 statements of setup and TIN construction followed by one 609-line `if preview_obj is not None:` block. That block is not "evaluation then object creation". It alternates evaluating a result, writing its fields onto the preview object, and creating a child preview object from it, about forty times, and several later evaluations read preview objects created earlier in the same block. A single cut into a builder service returning a typed result, as task 1 describes, would reorder document work that later steps depend on. M6 therefore proceeds in chunks that each keep the document work in the command and in its original order.

### M6 verification method

Because M6 changes the functions that build what the user sees and what is saved, text comparison and the contract suite are not enough. Each chunk is also checked by dumping the preview objects themselves. A pytest plugin wraps `App.closeDocument` and, as each test closes its document, records every `V1Corridor*` and `ReviewIssue*` object with its label, type, parents, and every property in `PropertiesList` order with its value; shapes are summarized by null state, face, edge, and vertex counts, and bounding box, and meshes by facet and point counts. It runs over the 74 contract tests that build intersection, roundabout, slope-face, shared-breakline, and intersection drainage previews, which close 44 documents holding 168 preview objects and 16,888 properties, including 19 intersection surface previews. Tests that fail in the baseline still build their objects before the assertion, so they are dumped too. The dump of the previous commit and the dump of the edited tree must match exactly.

Two HEAD runs were compared first to see whether that is possible. They differed in three places: `BuildDurationMs`, which is a timing; `Proxy`, whose text includes a memory address; and the order of `IntersectionBoundaryLoopGraphFilledEdgeRefs` on the Intersection Slope Face Surface preview in three tests. The last one is a finding in its own right: that list is built in string hash order, so the saved property can differ between two FreeCAD sessions building the same document. It is recorded here and not fixed, since M6 is extraction only. With the first two excluded and `PYTHONHASHSEED=0` set, two HEAD runs matched exactly, and that is the configuration every M6 comparison uses.

### M6 chunk 1 on 2026-09-14: the intersection patch surface properties

The first 60 statements of that block after the surface preview contract write the intersection id and kind, the grading policy, the slope-face policy metadata, 43 TIN quality values, and the prerequisite counts, refs, and diagnostics onto the preview object. Two of them were evaluations interleaved with the writes: `IntersectionPatchGradingService().select_policy` and `_intersection_slope_face_policy_for`, both pure functions of the IntersectionModel and the intersection id. They now run just before the writes, and the 58 writes move, in their original order, into `_attach_intersection_patch_surface_metadata(preview_obj, *, prerequisite, tin_surface, grading_policy, slope_face_policy)`, a command helper beside the existing `_attach_*` helpers since it writes document properties. The slope-face policy is still a local of the preview function, which it uses again later for the slope-face surface preview. The only behavioural difference is theoretical: if either policy lookup raised, it would now raise before the first of those properties is written rather than after two of them.

`create_corridor_intersection_surface_preview` falls from 719 to 664 lines; the module grows by 19 lines for the helper's signature and docstring.

Validation: compile, flake8, 9 architecture tests, the preview dump over 74 tests identical to the previous commit with an identical failing set, the contract suite in three chunks with the Qt runner totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, and 26 smoke scripts at exit code 0.

### M6 chunk 2 on 2026-09-18: the contract preview branches

Five self-contained pieces of `create_corridor_intersection_surface_preview` moved into command helpers beside it, keeping every line as written and only losing two levels of nesting: the tie-slope surface branch, 80 lines; the slope-face surface branch, 21; the roundabout entry-exit, splitter island, apron, subgrade and slope-face branch, 113; the slope-face surface metadata branch, 44; and finally the whole 116-line try block that contains them, which evaluates the intersection contracts and records their results. Each helper takes exactly the names its block reads from the enclosing function, and the document work stays in the command module. `create_corridor_intersection_surface_preview` falls from 664 to 353 lines, half its size at the start of M6.

A `locals()` lookup was checked before lifting anything, since moving code out of a function changes what `locals()` sees. Three names are read that way in this function: `patch_boundary_result` and `surface_boundary_review`, both assigned outside the lifted blocks and still local, and `surface_zone_surface_preview`, which turns out never to be assigned anywhere in the repository, at HEAD or now, so that lookup has always returned None.

The extraction script was wrong twice, and both times the checks caught it rather than the suite.

First, it treated `except ... as exc` and comprehension variables as free names, so the try block's helper took `exc` as a parameter and returned a comprehension's `value`. flake8 reported the undefined names; the fix was to count handler names as bound and keep comprehension targets local to their own scope.

Second, and more serious: the slope-face branch assigns `slope_face_preview`, which later statements read, so the helper returns it. But the branch only assigns it on the non-roundabout path; the `= None` that preceded it stayed in the caller. On the roundabout path the helper raised `UnboundLocalError`, the enclosing try recorded a slope-face loop error, and the apron, subgrade, and roundabout slope-face previews were never created. Text comparison and flake8 both pass on that version. The preview dump caught it: 52 differences over twelve roundabout tests, three missing objects each, with the exception text sitting in `IntersectionSlopeFaceLoopDiagnostics`. The generator now initialises a returned name to None inside the helper, the way the caller did.

After the fix the dump is identical to the baseline again, with the same failing set.

Validation: compile, flake8, 9 architecture tests, the preview dump over 74 tests identical to the pre-M6 baseline, the contract suite in three chunks with the Qt runner totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, and 26 smoke scripts at exit code 0.

### Level 7 manual confirmation of M6 chunk 2, on 2026-09-18

The maintainer confirmed the intersection previews in the GUI, including the roundabout apron, subgrade, and slope-face previews that the chunk's second defect had dropped before it was fixed.

### M6 chunk 3 on 2026-09-18: the remaining runs of the intersection preview

Chunk 2 lifted whole branches; this chunk lifts six contiguous runs of statements that each do one thing, using a generator that takes a statement range rather than a single statement. Each helper receives the names its run reads and returns the names the rest of the function still reads, so the caller keeps the same locals; every line is unchanged apart from one level of indentation.

- the Tie-In edge result, its properties, and its preview, returning the result the boundary segment step needs;
- the boundary segment result, its seven properties, and its preview, returning the result;
- the shared breakline, boundary loop, shared boundary graph, and patch boundary metadata;
- the exclusion zone preview and the tagging of the surfaces it clips;
- the intersection drainage low-point review row;
- the surface patch result with the implementation mode, replacement gate, handoff, and manual QA metadata.

`create_corridor_intersection_surface_preview` falls from 353 to 258 lines, from 719 at the start of M6. What is left is the document and prerequisite checks, the TIN build, the preview mapper call, and thirteen helper calls.

Two guards in the generator earned their place here. The first refused a range whose names a later statement reads through `locals()`, which is how the run boundaries were chosen rather than guessed. The second is the rule from chunk 2: a returned name is initialised to None inside the helper. The last run, the surface patch metadata, does read `patch_boundary_result` and `surface_boundary_review` through `locals()` inside the moved code; both are assigned unconditionally before the run and are passed in as parameters, so they are locals of the helper too and the tests still see the same values. `surface_zone_surface_preview`, read the same way, is assigned nowhere and stays None.

Validation: compile, flake8, 9 architecture tests, the preview dump over 74 tests identical to the pre-M6 baseline with the same failing set, the contract suite in three chunks with the Qt runner totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, and 26 smoke scripts at exit code 0.

### M6 chunk 4 on 2026-09-18: the intersection preview reaches its target size

Three more moves finish the first preview function.

Two runs became helpers the same way as chunk 3: the opening run that clears the build diagnostic and records the surface preview contract, the grading and slope-face policies, and the patch metadata, returning the slope-face policy the later steps use; and the run that evaluates the patch boundary and shared breakline contracts and records their metadata, returning the four results the contract previews and the surface patch step read.

The third is a deduplication rather than a lift. The applied-sections check, the prerequisite check, and the TIN build failure each removed the same eight intersection preview objects in the same order and then recorded a build diagnostic that differed only in status and notes. The generator verified that all three teardowns are identical before folding them into `_clear_intersection_surface_previews_with_diagnostic(doc, *, project, status, notes)`. Each caller keeps its own condition, its own status and notes, including the error path's `f"...: {exc}"`, and its own `return None`, so the control flow is untouched.

`create_corridor_intersection_surface_preview` is now 169 lines, from 719 at the start of M6, and reads as document checks, the TIN build, the preview mapper call, and eleven named steps. That satisfies the milestone's size criterion for this function, roughly 150 lines, closely enough that further splitting would cut across the steps rather than between them.

Validation: compile, flake8, 9 architecture tests, the preview dump over 74 tests identical to the pre-M6 baseline with the same failing set, the contract suite in three chunks with the Qt runner totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, and 26 smoke scripts at exit code 0.

### M6 chunk 5 on 2026-09-18: the intersection slope face surface preview

The second-largest preview function, `_create_corridor_intersection_slope_face_surface_preview` at 388 lines, turned out to be simpler than the first. After building the surface and creating the preview object, 105 of its statements do one thing: read a TIN quality row and write it to a property of the preview object. Nothing in that stretch touches the document, and the only inputs are the preview object, the surface, and the loop result.

It was split by subject rather than by size, into six helpers: the preview identity with the loop counts and boundary strip quality; the slope face cell counts, refs, and diagnostics; the upper slope face panel coverage, generation mode, and diagnostics; the shared boundary graph counts with the boundary loop shared breakline refs; the boundary loop transition strips, corners, and summaries; and the boundary loop graph coverage with its audit rows and owner fill readiness. Every line keeps its text and loses one level of indentation, and each helper takes only what its run reads.

The function is now 93 lines: the guard, the surface build, the empty-surface and mapper error paths, the preview object lookup, six named metadata steps, and the tree routing.

This used a third generator, which takes any command function and a range of its top-level statements, rather than the two written for the shape of the first preview function. The `locals()` guard from chunk 3 came along with it.

Validation: compile, flake8, 9 architecture tests, the preview dump over 74 tests identical to the pre-M6 baseline with the same failing set, the contract suite in three chunks with the Qt runner totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, and 26 smoke scripts at exit code 0.

Preview functions above 150 lines that remain: `create_corridor_daylight_surface_preview` at 242, `create_corridor_design_surface_preview` at 177, `_create_corridor_roundabout_slope_face_surface_preview` at 181, `_create_corridor_roundabout_subgrade_surface_preview` at 166, and `_create_corridor_roundabout_entry_exit_connector_surface_preview` at 151. The daylight and design surface previews are not covered by the current dump selection, so that selection needs widening before they are touched.

### M6 chunk 6 on 2026-09-18: the remaining preview functions, and a generator defect worth recording

The note in chunk 5 that the daylight and design previews are outside the dump selection was wrong, and is corrected here: the dump already covers them. The 74 tests it runs close 44 documents holding 8 daylight, 5 design, 3 subgrade, and 13 of each roundabout surface preview, so the same comparison applies to every function in this chunk.

`_create_corridor_roundabout_entry_exit_connector_surface_preview`, 153 lines, is called from nowhere in the repository. The roundabout generalization disabled that output, and the branch that used to create it now only removes the object and records `not_applicable`. It was deleted and its name added to `removed_implementation_names`.

Four functions lost their metadata and surface-preparation runs to helpers, each keeping every line and one less level of indentation: the daylight preview lost its 63-line preview metadata block, the 43-line shared breakline chain, and the 45-line intersection clip, suppress, and trim chain; the design preview lost its 42-line metadata block; and the roundabout slope face and subgrade previews each lost their metadata block, 90 and 75 lines. Sizes: daylight 242 to 122, design 177 to 149, roundabout slope face 181 to 97, roundabout subgrade 166 to 97. No preview function is now above 169 lines, the intersection surface preview from chunk 4, and the 20 of them total 1,896 lines, from 3,157 at the start of M6.

The generator had a defect that this chunk exposed twice, and the second form is the instructive one.

Its parameter rule was "names the run reads, minus names the run assigns". For `tin_surface = f(tin_surface)` that drops `tin_surface`, and because the generator also initialises returned names to None, the helper then clipped a surface that was None instead of the built one. flake8 and the contract suite passed; the preview dump caught it, with the daylight preview replaced by an error diagnostic reading "replace() should be called on dataclass instances" in four tests. The rule is now flow-sensitive: walking the run in source order, a name read before the run binds it is a parameter, and a parameter that is also returned is not re-initialised.

The first fix of that rule went too far the other way. Treating each top-level statement as one unit made names that a nested `try` binds and then reads inside itself look free, so the helper asked for `slope_intersection_model` and `slope_prerequisite`, which the caller does not have; flake8 caught that one. The walk now steps into the bodies of `if`, `for`, `while`, `with`, and `try` in source order.

Because chunks 2 to 5 used the earlier rules, the whole module was audited afterwards for the same defect: every top-level function walked in source order, reporting any name read before it is bound that is neither a parameter nor a module-level name. Across 678 functions there are none.

One deliberate move came out of that: the daylight preview initialised `general_shared_breakline_result`, `region_shared_breakline_result`, and `intersection_shared_breakline_result` to None before the try, and the lifted helper binds them only inside its own nested try. Those three initialisations moved into the helper, where they belong, rather than being deleted.

Validation: compile, flake8, 9 architecture tests, the module-wide free-name audit, the preview dump over 74 tests identical to the pre-M6 baseline with the same failing set, the contract suite in three chunks with the Qt runner totalling 1,433 tests and matching the 52-failure baseline, 19 + 19 + 14, and 26 smoke scripts at exit code 0.

### M8 batch 1 on 2026-09-18: twenty stale contract expectations

Twenty of the 52 failures were test drift, each one a test still stating a contract the product had moved past. They were taken module by module, every module re-run through the Qt runner before the next was touched, and nothing was changed on a guess: each failure was reproduced, its cause read in the current product code, and the test rewritten to state what the code now guarantees.

What the drift looked like, by family.

- Renames and relabels, 7 tests. `test_intersection_model.py` still rejected the roundabout kind and accepted `diverging_diamond`; the region editor's three labels now read "Assembly / Subassembly source"; the subassembly editor writes "material: concrete"; the stationing source object exposes `preview["station_rows"]`; the earthwork service reports an empty `subassembly_ref` where it used to invent one.
- Contracts that grew a dimension, 6 tests. The profile editor's "Starter Road" preset is gone and vertical curve length now comes from the design K value clamped by the adjacent spacing, so the four tests were rewritten around `profile_preset_names()[0]` and that relationship rather than a preset name and a fixed 30 m. The drainage source object gained `ElementSubassemblyRefs`, so four fixture rows carry `subassembly_ref="ditch:left"`.
- Environment assumptions, 2 tests. The applied sections test asserted a hidden count that only holds when view objects exist; it is now guarded for the headless run.
- Filters that caught more than they meant, 1 test. The section command bridge matched every quantity row; it now filters on `"section-earthwork-area" in row.quantity_row_id`.
- Fixtures the product outgrew, 2 tests. Both drainage editor failures. `test_drainage_editor_show_flow_network_applies_model_and_creates_preview` hand-seeded three Structures, but the "Drainage Structures Flow" preset now references five, so validation reported two missing Structure refs and returned before creating anything: the assertion `preview is not None` was reading a real error. It now seeds the paired Structure preset the way the flow route segment test beside it does, and gets `Validation: ok`, one network, four pipe segments. `test_drainage_editor_validate_shows_flow_route_summary` asserted the Flow Route Summary line on an empty model; that line is rendered from the capture/pipe summary diagnostic, which `DrainageValidationService` emits only when there are flow routes. Printing "capture-only=0; pipe-producing=0" beside "Flow Routes: 0" is noise, so the product is right and the test now states the contract on a preset that has routes: the summary is rendered as a line and the raw `info:flow_route_capture_pipe_summary` id is not dumped into the status.

One product change is in the batch. `leg_graph_order_refs` in `intersection_evaluation_service.py` was built in row order while reading as an ordering, and is now sorted by `leg_graph_order`.

Validation: the contract suite in three chunks with the Qt runner, 1,433 tests, 32 failures against the 52-failure baseline, 1 + 19 + 12; the failing set is a strict subset, with 20 resolved and none new. 9 architecture tests and 26 smoke scripts at exit code 0.

The 32 that remain are not drift of this kind and are taken next: 19 in `test_build_corridor_command.py`, 12 in `test_intersection_command.py`, and the boundary loop question below.

Open question for the maintainer, not decided here. `test_intersection_boundary_loop_prefers_topology_curb_return_envelope_for_cross` builds a ready loop through the curb-return envelope path, closed, 32 points, area 312, and yet `result.status == "error"` because of `error:intersection_boundary_authoritative_source_edges_missing`. That rule landed on 2026-07-02, the envelope feature and this test on 2026-07-06, so the rule predates what it now rejects. A sibling test locks error and no loops for the case with no envelope, so the rule itself is wanted; the question is whether a complete envelope loop should satisfy it.

## 11. Open Decisions

These require a decision before the affected milestone starts. None blocks M0.

1. Resolved on 2026-09-04. `ProjectDocumentAdapter.route_to_project_tree` already existed, and the adapter module already imported the legacy function at module level, which proved there was no circular-dependency reason for the 78 function-local imports. M1 was a call-site migration.
2. Resolved on 2026-09-10. Ownership follows the consumer: panel tables to `ui/presentation`, normalized output contracts to `services/mapping`, document discovery staying in the command. The injection in `configure_build_corridor_task_panel_runtime` is what makes the move safe, and the existing `shared_breakline_audit_presentation.py` is the pattern. See the M5 record in section 10.
3. M0 task 5: what is the target duration for the fast contract tier, and which modules belong to the long-running tier?
4. M7: is a legacy command with a complete v1 replacement removed from the toolbar in a later task, or retained indefinitely for user familiarity?
5. Resolved on 2026-09-14. M5 closes at its presentation scope and work continues with M6. Moving the region boundary continuity evaluation to `services/evaluation` and the preview audit serializers to `services/mapping`, replacing the identical copies in `services/builders`, is recorded as follow-up work outside M5. See the M5 record of 2026-09-14 in section 10.
