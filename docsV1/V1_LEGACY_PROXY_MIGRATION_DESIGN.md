# Parametric Road V1 Legacy Proxy Migration Design

Date: 2026-10-11
Branch: `ganada_0902` (measured at `22df633`)
Status: Decided on 2026-10-11 (section 11). Phases P0 and P1 done (section 12), P2 (section 13), P3 (section 14), P4 (section 15), bridge fallbacks (section 16), P5 done (section 17). Converters dropped (section 18). Stubs removed (section 19). obj_project cleaned (section 20).
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
| Contract tests | none | (corrected on 2026-10-11: the first count of 20 matched `v1/objects` modules with the same names, such as `v1.objects.obj_alignment`) |
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

## 11. Decisions Taken, on 2026-10-11

The maintainer decided the four questions of section 9:

1. **Option C.** An older document must open, keep its last saved results, and its source-role
   legacy objects must be convertible into v1 sources through an explicit command. Phases P2 to P5
   apply as written; a converter phase follows them.
2. **Unregister** `CorridorRoad_EditAlignment`, `CorridorRoad_EditRegions` and
   `CorridorRoad_EditTypicalSection`, the hidden commands that create legacy objects.
3. **Retire** the runner smoke scripts that import legacy proxy modules (27 of 36) rather than
   rewrite them.
4. **Drop** the Plan/Profile legacy fallback: a document without a v1 Alignment or Profile shows
   nothing there, and `LegacyDocumentAdapter` no longer calls legacy class helpers.

## 12. P0 and P1 Results, on 2026-10-11

**P0.** `virtual_paths._PROXY_OBJECT_MODULES` names all 19 modules that define a proxy class.
`tests/contracts/v1/test_legacy_proxy_corpus.py` checks the list against a scan of the `objects`
package, so a module added or emptied later cannot drift from it.

**P1.** The corpus is in `tests/samples/legacy_proxy_corpus/`, written by the legacy classes on
2026-10-11 by `tests/legacy_proxy_corpus.py`:

| Document | Written by | Holds |
| --- | --- | --- |
| `legacy_chain.FCStd` | headless | one object of each of the 20 legacy proxy classes, linked as the legacy workflow linked them: alignment, profile, typical section, structure set, section set, corridor (with real geometry), surfaces, displays |
| `legacy_chain_prefixed.FCStd` | headless | the same, saved under the legacy module prefix `objects.` |
| `legacy_chain_gui.FCStd` | FreeCAD GUI | the same, with each class's stored view provider |

`manifest.json` and `manifest_gui.json` record each object's properties, live proxy class and
stored proxy entry. The contract test opens each document, compares it with the manifest, saves
it, reopens the copy, and repeats; every stored proxy must come back with the same class and
state. The GUI document's view providers were checked the same way inside the GUI by
`build_gui`, which recorded the result in its manifest.

Two findings, neither introduced here:

- **Headless restore of legacy-prefixed documents.** The GUI installs the eager path mappings at
  startup (`init_gui.py`). Headless FreeCADCmd stops at the basic level (`init.py`), and there a
  proxy saved as `objects.obj_section_set` restores from a second copy of the module rather than
  the canonical one. The object works, but class identity differs from the canonical class. The
  contract test runs with the eager mappings, as the GUI does.
- **Four legacy view providers cannot save their state.** `ViewProviderHorizontalAlignment`,
  `ViewProviderCenterline3D`, `ViewProviderCenterline3DDisplay` and `ViewProviderStationing` keep
  the FreeCAD object in their state and define no `__getstate__` or `dumps`, so FreeCAD's JSON
  save of that state fails. Their module and class are stored, so they restore; what is written
  as state (`""` or `{"Object": null}`) depends on whether the provider was attached. `attach()`
  rebuilds the back-reference, so nothing is lost. The round trip compares only module and class
  for these four. Their stubs in phase P5 should define `dumps` returning `None`.

**Rebuilding the corpus.** Only while the legacy classes still have their behavior: after phase P5
the builder would record the stubs. It refuses to overwrite an existing manifest without
`--force`.

## 13. P2 Result, on 2026-10-11

`CorridorRoad_EditAlignment`, `CorridorRoad_EditRegions` and `CorridorRoad_EditTypicalSection` are
unregistered and their command modules removed; `V1_LEGACY_COMMAND_RETIREMENT_BOUNDARY.md`
section 11 records it, and `test_legacy_command_retirement.py` keeps them unregistered.

One path that creates legacy objects remains, found while doing P2: the surfaced Review
Plan/Profile command (`commands/cmd_review_plan_profile.py`) opens the v0 alignment or profile
editor when the v1 viewer raises, and those editors create `HorizontalAlignment`,
`VerticalAlignment`, `ProfileBundle` and `FGDisplay` objects. It is the Plan/Profile legacy
fallback of decision 4, so phase P3 removes it together with the adapter's legacy reads.

## 14. P3 Result, on 2026-10-11

The Plan/Profile legacy fallback is gone, in both of its forms:

- **Data.** `build_document_plan_profile_preview` reads the v1 Alignment and Profile only. A
  document that holds only legacy alignment and profile objects builds no document preview, and
  the command shows the demo preview, as it does for an empty document; its diagnostics say the
  document needs a v1 Alignment and Profile. `v1/services/evaluation/legacy_document_adapter.py`
  had no other production user (the Cross Section viewer called only its `_find_project`, now
  `objects.obj_project.find_project`) and is removed with its test, so nothing in v1 calls a
  legacy class helper any more.
- **Editors.** The Review Plan/Profile bridge (`commands/cmd_review_plan_profile.py`) reports a
  v1 viewer failure on the console instead of opening the v0 alignment or profile editor, the last
  surfaced path that created legacy objects.

`test_legacy_proxy_corpus.py` opens the corpus document and checks that it builds no Plan/Profile
preview; against the code before P3 that check fails. The v0 alignment and profile panels are now
reached only by runner smoke scripts and `cmd_review_alignment`; P4 retires them with the scripts.

## 15. P4 Result, on 2026-10-11

- **`CorridorRoad_ReviewAlignment` unregistered** (the maintainer extended decision 2 to it). It
  was read-only but kept the v0 alignment panel alive; its v1 successor is
  `CorridorRoad_V1ReviewPlanProfile`. `test_legacy_command_retirement.py` lists it with the other
  three.
- **65 smoke scripts retired**, every regression script that imports a legacy proxy module or
  one of the v0 panels removed below: 28 from the runners (27 importing legacy proxy modules,
  plus `smoke_profile_fg_tools.py` for the v0 profile editor) and 37 that no runner ran. The runners
  now hold 1 (short-term), 2 (practical scope) and 6 (loft retirement gate) scripts; the 14 kept
  scripts all pass.
- **v0 panels removed** now that nothing reaches them: `ui/task_alignment_editor`,
  `ui/task_region_editor`, `ui/task_typical_section_editor`, `ui/task_profile_editor`,
  `ui/task_pvi_editor`, with `ui/common/profile_fg_helpers` and the helpers only they used
  (`TerrainSampler`, two `unit_policy` conversions). The contract test of the alignment panel's
  preview launch order went with it.

Still open, outside the decisions so far: the surfaced Cross Section and Earthwork bridges
(`commands/cmd_view_cross_section.py`, `commands/cmd_generate_cut_fill_calc.py`) fall back to v0
panels when their v1 viewer raises, as Plan/Profile did. The cut/fill panel creates `CutFillCalc`
objects, which phase P5 turns into inert stubs, so that fallback needs a decision before P5. The
v0 corridor panel (`ui/task_corridor`) is still named by `corridor_compat` and checked by the loft
retirement gate.

## 16. Cross Section and Earthwork Fallbacks Removed, on 2026-10-11

The maintainer took the recommendation of section 15: the Cross Section and Earthwork bridges
(`commands/cmd_view_cross_section.py`, `commands/cmd_generate_cut_fill_calc.py`) now report a v1
viewer failure on the console, as Plan/Profile does, instead of opening a v0 panel. The v0 panels
`ui/task_cross_section_viewer` and `ui/task_cut_fill_calc` (which created `CutFillCalc` objects)
are removed, with the contract test of the v0 cross-section panel's preview launch order, the
non-runner smoke of its display units, and the helpers only those panels used
(`ui/common/coord_ui`, `ui/common/perf_quality`, four `unit_policy` area and volume formatters).
No surfaced command creates a legacy proxy object any more. The only v0 panel left is
`ui/task_corridor`.

## 17. P5 Progress

**The stub.** `objects/legacy_proxy_stub.py` holds `RestoreOnlyProxy` and
`RestoreOnlyViewProvider`. A stub keeps the state FreeCAD restores it with (every legacy proxy
stored its `__dict__`, such as `{"Type": "Stationing"}`; view providers `{}` or
`{"Object": null}`), exposes its keys as attributes as the legacy class did, and returns it
unchanged on save. It defines no `execute`, so a legacy object keeps its saved properties and
geometry. Its `__init__` raises: nothing may create a new legacy object.

**Checks for every stubbed module.** The contract test round-trips the three corpus documents
(and now counts stub subclasses in its preload and coverage scans). `check_gui()` in
`tests/legacy_proxy_corpus.py`, run inside the FreeCAD GUI, round-trips the GUI corpus document,
view providers included, against the committed manifest. A stub whose `dumps` lost the state
failed all three document round trips.

**Batch 1, 2026-10-11: the eight modules nothing else imports.**

| Module | Lines before | Stubbed classes |
| --- | ---: | --- |
| `obj_profile_bundle` | 109 | `ProfileBundle` |
| `obj_stationing` | 135 | `Stationing` |
| `obj_fg_display` | 170 | `FGDisplay` |
| `obj_design_grading_surface` | 483 | `DesignGradingSurface` |
| `obj_pointcloud_dem` | 546 | `PointCloudDEM` |
| `obj_design_terrain` | 617 | `DesignTerrain` |
| `obj_centerline3d_display` | 1,198 | `Centerline3DDisplay` |
| `obj_cut_fill_calc` | 1,425 | `CutFillCalc` |

with a view provider each. Headless and GUI round trips pass.

**Batch 2, 2026-10-11: the remaining ten modules.** They import one another (the corridor and
section set import the structure set, region plan, templates and centerline, which import the
alignments), so they were stubbed together in one commit, in import order:

- `ui/task_corridor`, the last v0 panel and the only importer of `obj_corridor`, is removed with
  `corridor_compat.PREFERRED_TASK_MODULE`/`PREFERRED_TASK_PANEL_CLASS`. The maintainer retired
  the three loft-gate smokes that read its source and `obj_corridor`'s
  (`smoke_corridor_child_link_boundary`, `smoke_corridor_proxy_boundary`,
  `smoke_corridor_taskpanel_alias_boundary`); the gate keeps `command_alias`, `project_link` and
  `tree_schema`.
- `obj_corridor`, `obj_section_set`, `obj_region_plan`, `obj_structure_set`, `obj_centerline3d`,
  `obj_typical_section_template` (three proxies), `obj_assembly_template`,
  `obj_cross_section_edit_plan`, `obj_vertical_alignment` and `obj_alignment` are stubs.
- `obj_project._migrate_region_plan_links` imported three region-plan helpers from
  `obj_section_set` and already fell back to reading and writing `RegionPlan`/`UseRegionPlan`
  when they were missing; it now uses that path only.
- Helpers only the legacy implementations used are removed: `corridor_segment_builder`,
  `section_strip_builder` (with its non-runner smoke), `coord_transform`, `doc_query`,
  `terrain_sampler`, and the dead functions of `unit_policy` and `surface_sampling_core`.

**What changed in the corpus manifests.** The first property snapshots were taken by reopening
the corpus with the legacy classes, which rewrote properties while a document loaded:
`NeedsRecompute`, `Status` and a ` [Recompute]` label suffix on Corridor, SectionSet,
DesignGradingSurface, DesignTerrain and CutFillCalc. The stubs run nothing on load and show the
values the files hold (checked against `Document.xml`). `refresh_snapshots()` re-recorded the
snapshots; exactly those 11 (object, property) pairs changed in each document, and every stored
proxy and view-provider entry, the legacy reference, is unchanged. Headless and GUI round trips
pass.

**Result.** The legacy `objects` package went from 25,878 lines in 31 files to 4,531 in 27,
most of it the live `obj_project`; legacy `ui` holds two empty package files. Legacy documents
open, keep every object, property, shape and proxy reference, and no longer recompute their
legacy objects; their source objects become editable again through the converters.

## 18. Converters Dropped, on 2026-10-11

The maintainer decided that documents made with v0 need no further support. The converter phase
of option C (section 11, decision 1) is therefore dropped: no command converts legacy source
objects into v1 sources. What phases P0 to P5 built stays as it is: the restore-only stubs keep
any document that still holds a legacy object openable without losing data, and the corpus test
keeps that true.

## 19. Stubs Removed, on 2026-10-11

The maintainer then chose to remove the remaining legacy traces as well, accepting that a
document still holding a legacy object (from v0, or from a v1 session before the legacy paths
were closed) opens with that object's properties and shape but without its proxy, and loses the
proxy reference on its next save (section 3).

- The 18 stub modules and `objects/legacy_proxy_stub.py` are removed.
- `virtual_paths._PROXY_OBJECT_MODULES` lists only `obj_project`, the live project root; the
  `obj_corridor_loft` alias went with `obj_corridor`.
- The corpus (`tests/legacy_proxy_corpus.py`, `tests/samples/legacy_proxy_corpus/`) and its
  contract test are removed. `tests/contracts/v1/test_proxy_module_preload.py` keeps the one
  check that still applies: every proxy module of the `objects` package is preloaded.

What stays of the legacy `objects` package is `obj_project` and the helpers v1 imports
(`csv_alignment_import`, `sketch_alignment_import`, `surface_sampling_core`, `project_links`,
`design_standards`, `unit_policy`). `obj_project` still routed legacy object types into the tree
by name; section 20 removed that.

## 20. Legacy Handling Removed From obj_project, on 2026-10-11

`objects/obj_project.py` (the live project root) went from 2,734 to 1,821 lines:

- the dead alignment-tree chain (20 functions nothing called);
- the legacy type names in tree routing (`HorizontalAlignment`, `VerticalAlignment`,
  `ProfileBundle`, `Stationing`, `AssemblyTemplate`, `TypicalSectionTemplate`, `RegionPlan`,
  `SectionSet`, `StructureSet`, `Corridor`, the legacy surfaces, cut/fill and displays), with the
  classifiers only they used;
- the region-plan and corridor link helpers and `_migrate_region_plan_links`, which every project
  recompute ran over the whole document;
- `CorridorRoadProject.auto_link`'s search for legacy objects by name, and the legacy links among
  the adopted project links (`Terrain`, `Alignment` and `Stationing` stay; v1 sets `Alignment`,
  `Profile` and `Stationing` through `project_links.link_project`);
- `create_corridorroad_project`'s adoption of legacy links, and the `corridor_compat` names nothing
  uses any more (`PREFERRED_COMMAND_ID` and `CORRIDOR_PROJECT_PROPERTY` stay).

Kept on purpose: the project's properties, including the legacy hidden links, so saved documents
keep their schema; the alignment heuristic (v1 alignments carry IP rows); the `FinishedGradeFG`
name prefix, which the v1 profile editor's preview objects use; the terrain-mesh keyword
heuristic for imported meshes; the tree-folder migrations.

**How behaviour was held.** A pytest plugin recorded every routing (`resolve_v1_target_container`,
`_resolve_target_container`) and adoption decision across the whole contract suite before and
after the change: 456 distinct decisions, identical for every v1 and other object. The only
differences are the legacy names two tests created on purpose; those cases moved to a new test
asserting that legacy names route nowhere. The loft retirement gate's
`smoke_corridor_project_link_boundary`, which read this module's legacy corridor-link code, was
retired by the maintainer; the gate keeps `command_alias` and `tree_schema`.
