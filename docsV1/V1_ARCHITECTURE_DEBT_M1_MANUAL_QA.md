# Parametric Road V1 Architecture Debt M1 Manual QA

Date: 2026-09-04
Branch: `v1-0503`
Status: Executed 2026-09-04, all parts pass
Depends on:

- `docsV1/V1_ARCHITECTURE_DEBT_EXECUTION_PLAN.md`
- `docsV1/V1_MANUAL_QA_QUICKSTART.md`
- `scripts/check_freecad_environment.ps1`
- `tests/regression/run_short_term_smokes.ps1`

## 1. Purpose

M1 replaced 78 function-local imports of the legacy `route_to_v1_tree` across 31 v1 modules with one module-level import per module, routed through `route_object_to_project_tree` in `v1/objects/project_document_adapter.py`.

The change is intended to be behavior-preserving. Automated validation supports that:

- compile passes
- 8 architecture boundary tests pass, including a tightened routing guard
- the complete contract suite produced an identical failing set before and after: 131 failed and 1,331 passed both times, same test identifiers

Contract tests do not fully cover project-tree placement, because tree routing is a FreeCAD document-persistence behavior observed in the GUI tree. This document covers what the automated levels cannot.

The single question this QA answers:

> Does every v1 object still land in its correct project-tree folder, and does that placement survive save and reopen?

If M1 broke something, the symptom is an object appearing at the document root or under the wrong folder. It is not a crash and not a geometry difference.

## 2. Prerequisites

Run in order. Do not start the GUI walkthrough until both pass.

```powershell
cd "c:\Users\ganad\AppData\Roaming\FreeCAD\v1-1\Mod\CorridorRoad"
.\scripts\check_freecad_environment.ps1
```

Expect `[PASS]`, a single workbench installation, FreeCAD API `1.1.3`, and both `pytest` and `flake8` reported.

```powershell
powershell -ExecutionPolicy Bypass -File tests\regression\run_short_term_smokes.ps1
```

This is validation level 5 and is still outstanding for M1. Headless failures are cheaper to diagnose than GUI ones, so clear this first.

Launch:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\launch_v1_manual_review.ps1
```

## 3. What Not To Attribute To M1

The contract suite had 131 pre-existing failures before M1 and the same 131 after. They are recorded as milestone M8 in the execution plan. If you see behavior matching one of those families during this QA, it is not an M1 regression:

- Applied Section station rows appearing as supplemental rows in larger numbers than an older expectation
- a benched-slope assembly producing no bench row
- intersection contract or shared-breakline review rows differing from an older expectation

Record such observations under M8, not here.

## 4. Part A: Tree Routing Walkthrough

Create a new project and run the workflow in order. At each step the check is the same and takes a few seconds: **the newly created object appears under the listed folder, and not at the document root.**

Folder names below are the labels as they appear in the tree.

| # | Command | Expected tree location | M1-touched module |
| --- | --- | --- | --- |
| 1 | Project Setup | `00_Project Setup` subtree is created | none |
| 2 | TIN | `03_Surfaces` > `Existing Ground TIN` > `Source`, `TIN Result`, `Diagnostics` | `cmd_edit_tin.py` |
| 3 | Alignment | `02_Alignment & Profile` > `Alignments` | `obj_alignment.py` |
| 4 | Stations | `02_Alignment & Profile` > `Stations` | none, control check |
| 5 | Profile | `02_Alignment & Profile` > `Profiles` | `obj_profile.py`, `cmd_profile_editor.py` |
| 6 | Review Plan/Profile | `08_Review` > `Plan Profile Review` | none, control check |
| 7 | 3D Centerline | `02_Alignment & Profile` > `3D Centerline` | `cmd_centerline3d.py` |
| 8 | Superelevation | `02_Alignment & Profile` > `Superelevation` | `obj_superelevation.py`, `cmd_superelevation_editor.py` |
| 9 | SubAssembly Designer | `04_Parametric Model` > `Assemblies` | `obj_subassembly_library.py`, `obj_subassembly_preset_library.py` |
| 10 | Assembly / Subassembly | `04_Parametric Model` > `Assemblies` | `obj_subassembly_assembly.py` |
| 11 | Regions | `04_Parametric Model` > `Regions` | `obj_region.py`, `obj_surface_transition.py` |
| 12 | Intersection Presets | `04_Parametric Model` > `Intersections` | `cmd_intersection_presets.py`, see Part B |
| 13 | Intersection Editor | `04_Parametric Model` > `Intersections` | `obj_intersection.py`, `cmd_intersection_editor.py` |
| 14 | Structures | `06_Structures` and its subfolders | `obj_structure.py`, `cmd_structure_editor.py` |
| 15 | Drainage | `05_Drainage` | `obj_drainage.py` |
| 16 | Drainage Review | `05_Drainage`, `05_Drainage` > `Drainage Diagnostics`, `06_Structures` | `cmd_drainage_review.py` |
| 17 | Applied Sections | `04_Parametric Model` > `Applied Sections` | `obj_applied_section.py`, `cmd_generate_applied_sections.py` |
| 18 | Build Parametric | `04_Parametric Model` > `Build Parametric Outputs`; intersection outputs under `Intersections`; review issues under `08_Review` > `Issues` | `cmd_build_corridor.py`, `obj_corridor.py`, `obj_surface.py` |
| 19 | Review Cross Sections | `08_Review` > `Section Review` | none, control check |
| 20 | Review Earthwork | `07_Quantities & Earthwork` > `Quantities`, `Cut Fill`, `Mass Haul` | `obj_quantity.py` |
| 21 | Outputs & Exchange | `09_Outputs & Exchange` > `Exchange Packages` | `obj_exchange_package.py` |
| 22 | Import LandXML | `09_Outputs & Exchange` > `Exchange Packages`; imported surface under `03_Surfaces` > `Existing Ground TIN` > `TIN Result` | `obj_landxml_import.py`, `landxml_*_mapper.py` |
| 23 | Structure Output | `09_Outputs & Exchange` > `Reports` | `obj_simulation_qa.py`, `obj_simulation_package.py` |
| 24 | Watertight Solids | `09_Outputs & Exchange` > `Watertight Solids` | `cmd_watertight_solids.py`, `obj_watertight_solid.py`, see Part B |

Steps 4, 6, 19 and 24 include control checks whose routing M1 did not touch. If those also misplace objects, the cause is not M1.

Some objects route by name and type rather than by a fixed record kind. Where the table lists a parent folder without a leaf, any correct leaf under that parent passes. What fails is placement at the document root or under an unrelated top-level folder.

## 5. Part B: The Two Behavioral Change Points

These are the only places where M1 changed behavior rather than only structure.

Both `cmd_intersection_presets.py` and `cmd_watertight_solids.py` previously wrapped the routing import in an availability guard:

```python
try:
    from freecad.Corridor_Road.objects.obj_project import route_to_v1_tree
except Exception:
    return
```

With the import hoisted to module level that guard became unreachable, so it was removed. A failure to import the routing symbol now fails module import instead of returning early from one function.

Check both explicitly:

1. **Intersection Presets.** Apply a preset. The command must complete without a Python error, and the created objects must appear under `04_Parametric Model` > `Intersections`. A silent no-op is a failure, because the old code could return early where the new code cannot.
2. **Watertight Solids.** Open the panel and build one enabled target. Output objects must appear under `09_Outputs & Exchange` > `Watertight Solids`. Watertight development is paused, so the bar is unchanged existing behavior, not new capability.

## 6. Part C: Save And Reopen

This is validation level 6 and is the most important part of this QA. Tree routing is persistence behavior.

1. Save the document built in Part A.
2. Close FreeCAD completely, not just the document.
3. Reopen the document.
4. Confirm every folder from Part A still holds the same objects.
5. Recompute the document and confirm no Python error appears in the report view.

## 7. Part D: Backward Compatibility

Open at least one FCStd document created before these changes, ideally one saved with the public `1.0.9` release.

1. The document opens without a Python error.
2. The existing project tree is intact and objects remain in their folders.
3. A recompute completes.
4. Running one source editor and applying a change routes the result to the expected folder.

Legacy documents restore proxies through the virtual path mapping in `freecad/Corridor_Road/__init__.py`. M1 did not touch that path, but it is the highest-consequence area if something is wrong.

## 8. Part E: Items Only Manual QA Can Cover

Two contract tests fail in a headless run because `ViewObject` is `None` without the GUI. They are counted in the pre-existing 131 and are legitimately verifiable only here:

- `test_hide_applied_sections_preview_objects_hides_existing_previews`
- `test_corridor_preview_visibility_helpers_target_roles_and_markers`

Check that hiding and showing Applied Section previews and Build Parametric preview objects behaves correctly through the panel controls.

## 9. Result Record

Executed 2026-09-04 on FreeCAD 1.1.3 build 2026/07/25.

| Part | Result | Notes |
| --- | --- | --- |
| Prerequisites: environment check | pass | single installation, FreeCAD API 1.1.3, pytest 8.4.2, flake8 7.3.0 |
| Prerequisites: short-term smokes | pass | 26 smoke scripts, exit code 0, no failure or traceback output |
| A: tree routing walkthrough | pass | reported by maintainer |
| B1: Intersection Presets | pass | reported by maintainer |
| B2: Watertight Solids | pass | reported by maintainer |
| C: save and reopen | pass | reported by maintainer |
| D: legacy document compatibility | pass | reported by maintainer |
| E: preview visibility | pass | reported by maintainer |

Parts A through E were executed by the maintainer in the FreeCAD GUI and reported as passing. The prerequisite rows were executed and observed directly.

M1 may be recorded as complete only when Parts A, B, C, and D pass and the short-term smokes pass. That condition is met.

## 10. If Something Fails

Capture, in this order:

1. the workflow step and command id
2. the object name and label, and where it actually appeared in the tree
3. the full Python traceback from the report view, not a summary
4. whether the same step misplaces objects in a control-check row from section 4

Then check whether the failing step is one of the two Part B change points, since those are the only intentional behavioral differences in M1. If it is not, and a control-check row fails the same way, the cause is likely older than M1 and belongs to M8 rather than here.
