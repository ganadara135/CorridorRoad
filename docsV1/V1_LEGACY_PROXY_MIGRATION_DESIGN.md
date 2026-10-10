# Parametric Road V1 Legacy Proxy Migration Design

Date: 2026-10-11
Branch: `ganada_0902` (measured at `22df633`)
Status: Design for decision. No code is changed by this document.
Depends on:

- `docsV1/V1_LEGACY_COMMAND_RETIREMENT_BOUNDARY.md` (sections 5 and 6, frozen legacy persistence surfaces)
- `docsV1/V1_ARCHITECTURE_DEBT_EXECUTION_PLAN.md` (open decision 4)
- `docsV1/V1_PERSISTENCE_SCHEMA_INVENTORY.md`
- `AGENTS.md` (Persistence and Backward Compatibility)

## 1. Purpose

The legacy `objects` package cannot shrink while saved documents name its modules as the home of
their objects' `Proxy` classes. Every handoff since September has recorded this as "legacy
retirement is blocked until a stored-`Proxy` migration exists", without saying what such a
migration would be or what it would cost.

This document measures how FreeCAD restores a proxy whose module is gone, inventories the legacy
proxy classes and everything that still depends on their behavior, and sets out three options with
their consequences. It ends with the decisions only the maintainer can take.

## 2. What This Document Does Not Do

- It removes no module, class, command, or test.
- It does not decide what an older document must still be able to do. That is decision 1 in
  section 9.
- It does not touch `obj_project.py`. `CorridorRoadProject` is the live v1 project root and is out
  of scope.
- It does not touch Ramp or Watertight Solid code.

## 3. How FreeCAD Restores a Proxy (measured)

`Document.xml` stores each Python proxy as a module path and a class name, with the proxy state
beside them. A document saved today records the canonical path:

```xml
<Python value="..." encoded="yes" module="freecad.Corridor_Road.objects.obj_alignment" class="HorizontalAlignment"/>
```

On restore FreeCAD imports that module and rebuilds the class from the stored state. A headless
experiment under FreeCAD 1.1 (`App::FeaturePython` with two data properties, saved, then reopened
in a fresh process where the proxy module could not be imported) gave:

| Step | Result |
| --- | --- |
| reopen without the module | the document opens; `Proxy` is `None`; data properties keep their values; no message reached stdout |
| `recompute()` | nothing runs; the object stays `Up-to-date` |
| edit a property, `save()` | succeeds |
| reopen **with** the module back | `Proxy` is still `None`: the save wrote the object without its module and class |

Two conclusions follow.

1. **A missing module does not lose data on open.** Properties, and for `Part::FeaturePython`
   objects the stored `Shape`, survive. What is lost is behavior: `execute`, `onChanged`, the
   state in `dumps`/`loads`, and anything that identifies the object by its proxy type.
2. **One save in that state makes the loss permanent.** The proxy reference, and the proxy state,
   are dropped from the file. Restoring the module afterwards does not bring them back. This is the
   real data-loss risk, and any option below must make sure a module is never missing at restore.

View providers are stored the same way in `GuiDocument.xml`. Their behavior without the module
was not measured here; it needs a GUI session (section 8, phase P1).

## 4. Inventory

### 4.1 Legacy proxy classes

19 modules in the legacy `objects` package assign `.Proxy = self`. Excluding the live
`obj_project.py`, 18 remain, 20,604 lines of the package's 25,878.

| Module | Lines | Proxy classes (plus one view provider each) | Role | v1 owner today |
| --- | ---: | --- | --- | --- |
| `obj_alignment` | 1,125 | `HorizontalAlignment` | source | `V1Alignment` |
| `obj_vertical_alignment` | 250 | `VerticalAlignment` | source | `V1Profile` |
| `obj_profile_bundle` | 109 | `ProfileBundle` | source | `V1Profile` |
| `obj_stationing` | 135 | `Stationing` | generated | `V1Stationing` |
| `obj_assembly_template` | 643 | `AssemblyTemplate` | source | Assembly / Subassembly |
| `obj_typical_section_template` | 1,377 | `TypicalSectionTemplate`, `TypicalSectionPavementDisplay`, `TypicalSectionSelectionDisplay` | source and display | Assembly / Subassembly |
| `obj_region_plan` | 1,026 | `RegionPlan` | source | `V1Region` |
| `obj_structure_set` | 2,247 | `StructureSet` | source | `V1Structure` |
| `obj_cross_section_edit_plan` | 343 | `CrossSectionEditPlan` | source | none (Applied Sections are generated) |
| `obj_centerline3d` | 395 | `Centerline3D` | result | `Centerline3DResult` |
| `obj_centerline3d_display` | 1,198 | `Centerline3DDisplay` | display | 3D Centerline preview |
| `obj_fg_display` | 170 | `FGDisplay` | display | Plan/Profile review |
| `obj_section_set` | 5,541 | `SectionSet` | result | `AppliedSectionSet` |
| `obj_corridor` | 2,974 | `Corridor` | result | Build Parametric corridor |
| `obj_design_grading_surface` | 483 | `DesignGradingSurface` | result | corridor surfaces |
| `obj_design_terrain` | 617 | `DesignTerrain` | result | corridor surfaces |
| `obj_pointcloud_dem` | 546 | `PointCloudDEM` | terrain import | TIN |
| `obj_cut_fill_calc` | 1,425 | `CutFillCalc` | result | Earthwork review |

The role column follows each class's v1 counterpart; it decides what a conversion would have to
carry (section 6, option C). Results and displays can be rebuilt in v1 and carry nothing.

### 4.2 The preload list is shorter than the set of proxy modules

`virtual_paths._PROXY_OBJECT_MODULES` preloads 15 modules so that documents saved under a legacy
module prefix (`CorridorRoad.objects...`, `objects...`) find an alias in `sys.modules`. Four proxy
modules are not on it: `obj_region_plan`, `obj_structure_set`, `obj_typical_section_template` and
`obj_cross_section_edit_plan`. Today all four are loaded anyway, because listed modules import
them (checked after `install_virtual_path_mappings(eager=True)`: canonical and legacy names are
both present). Any change that removes those imports would silently break legacy-prefix restore
for these four. **Whatever option is chosen, the list must name all 19 modules first.**

## 5. What Still Depends on Legacy Behavior

| Dependent | Measured | Depends on |
| --- | --- | --- |
| Short-term smoke runner | 24 of 26 scripts | importing legacy proxy modules |
| Practical-scope smoke runner | 12 of 14 scripts | importing legacy proxy modules |
| Loft retirement gate runner | 2 of 8 scripts | importing legacy proxy modules |
| All three runners, distinct scripts | 27 of 36 | (12 scripts run in more than one runner) |
| Contract tests | 20 files | importing legacy proxy modules |
| `v1/services/evaluation/legacy_document_adapter.py` | 4 calls | `VerticalAlignment._solve_curves`, `SectionSet.resolve_station_values` / `resolve_viewer_station_rows`, `obj_typical_section_template.pavement_rows`, `RegionPlan.resolve_station_context` |
| Plan/Profile review | fallback | reads a legacy alignment and profile through that adapter when the document has no v1 ones |
| Hidden, still-registered commands | 3 | `CorridorRoad_EditAlignment`, `CorridorRoad_EditRegions`, `CorridorRoad_EditTypicalSection` open v0 panels that create `HorizontalAlignment`, `RegionPlan` and `TypicalSectionTemplate` objects |

The smoke runners are the largest dependency. Most of their scripts build legacy objects to test
compatibility chains, so retiring legacy behavior retires most of the maintained regression gate
with it; replacing it is part of the cost, not an afterthought.

The hidden commands mean new legacy objects can still be created by command id, macro or custom
toolbar. Retiring the classes' behavior without retiring these commands would let a user create an
object that cannot compute.

## 6. Options

### Option A: keep the frozen surface (status quo)

All 19 modules stay as they are, under the frozen rule in the retirement boundary record: critical
repair, data-loss prevention and compatibility only.

- Older documents keep working exactly as today, including recompute of legacy objects.
- Cost: 20,604 lines stay; the dead-code passes keep reporting them; the smoke runners keep
  testing legacy chains rather than v1.
- Risk: none new. Only the section 4.2 list fix is worth doing.

### Option B: restore-only proxy stubs

Each legacy module is replaced by a small module at the same path that keeps its class names and
nothing else:

- the proxy class keeps the stored state verbatim (`loads` stores what it receives, `dumps` returns
  it unchanged), so a reopen-and-save cycle loses nothing, including state written by versions
  this code no longer understands;
- it has no `execute`, so a legacy object keeps its last saved properties and `Shape` and never
  recomputes;
- its view provider keeps the object displayed with its saved shape;
- any static helper v1 still calls moves to a v1 service first (the 4 adapter calls in section 5).

What a user gets: an older document opens and shows what it showed when it was saved. Its legacy
objects are frozen; changing them means re-authoring the design in the v1 editors.

- Cost: about 20,000 lines removed, replaced by roughly 30 to 50 lines per module.
- Preconditions: open decision 4 resolved for the 3 hidden commands that create legacy objects;
  the smoke runners rewritten for v1 or retired; the 4 adapter helpers moved.
- Risks: a stub's `loads`/`dumps` must round-trip every state shape the real class ever wrote
  (proved per class on a document corpus, section 8); the real classes add missing properties when
  they recompute (`HorizontalAlignment.execute` starts with `ensure_alignment_properties`), so a
  stub leaves a document from an older schema at that schema.

### Option C: convert to v1 sources, then stubs

As option B, plus an explicit command that converts the source-role legacy objects of section 4.1
into v1 source objects (Alignment, Profile, Assembly/Subassembly, Region, Structure), after which
the user rebuilds the results in v1.

- What a user gets: an older design becomes editable in v1 without re-entering it.
- Cost: one converter per source type with unit, station and orientation checks, on top of
  option B. The legacy section templates and region plans do not map one to one onto v1
  Assembly/Subassembly and Region rows, so those converters are design work of their own.
- Constraints: conversion must be an explicit command with a report, never something that happens
  on open (`AGENTS.md`: opening must not mutate the document). Converted sources must keep a trace
  back to the legacy object.

## 7. Recommendation

Option B, in phases, with option C only for the source types users actually ask to convert.

- Option A leaves the blocking condition in place indefinitely, and the handoff already treats it
  as the main obstacle to legacy retirement.
- Option B removes almost all legacy code while keeping the one guarantee that matters for an older
  document: it opens and nothing in it is lost. Section 3 shows what it must never do: let a module
  go missing.
- Option C is the most work, and its value depends on whether older v0 designs still need to be
  edited. That is a product fact this branch cannot measure.

Fix the section 4.2 preload list in any case.

## 8. Phases for Option B

| Phase | Work | Exit check |
| --- | --- | --- |
| P0 | Complete `_PROXY_OBJECT_MODULES` to all 19 modules | contract test: every module assigning `.Proxy` is listed |
| P1 | Build a corpus: one document per legacy class, written by the current code from the smoke builders, plus any older user documents available; check view providers in a GUI session | every corpus document opens, saves, reopens with `Proxy` class and properties intact |
| P2 | Resolve open decision 4 for the 3 hidden commands that create legacy objects | the commands are unregistered or kept with their panels |
| P3 | Move the 4 adapter helpers into a v1 service, or drop the Plan/Profile legacy fallback | the adapter imports no legacy module |
| P4 | Rewrite the smoke scripts that test v1 behavior through legacy objects; retire the ones that only test legacy chains | the three runners pass with no legacy proxy import |
| P5 | Replace modules with stubs, smallest first (`obj_profile_bundle`, `obj_stationing`, `obj_fg_display`), one per commit | the corpus round-trips twice; the full gate passes |
| P6 | Update the retirement boundary record, the persistence inventory and the handoff | |

P0 and P1 are useful under every option and change no behavior.

## 9. Decisions for the Maintainer

1. **What an older document must still do.** Recompute its legacy objects (option A), open and
   show its last saved results (option B), or become editable in v1 (option C).
2. **Open decision 4 for the 3 hidden commands that create legacy objects.** Options B and C
   require unregistering them or keeping their panels.
3. **The smoke runners.** Under options B and C, 27 of the 36 distinct runner scripts import legacy
   proxy modules. Rewrite them for v1 coverage, or retire the ones that only exercise legacy chains.
4. **The Plan/Profile legacy fallback.** Keep it (move its 4 helpers into v1) or drop it, so that a
   document with no v1 Alignment or Profile shows nothing in Plan/Profile review.

## 10. Validation for Any Option

- the corpus round trip of phase P1: open, save, reopen, twice, comparing proxy class, proxy
  state and every property
- a GUI session for view providers, which a headless run cannot check
- the full gate: contract and architecture tests and the three smoke runners
- `AGENTS.md` persistence rules: stable ids, link targets and unknown legacy data preserved
