# Parametric Road V1 General Road Workflow Improvement Plan

Date: 2026-10-16
Branch: `ganada_0902`
Status: In progress. GR-1 to GR-7 done and D1-D3 decided on 2026-10-16; GR-8 next
Scope: the ordinary road workflow from Project to Build Parametric, before the Drainage rework
Related:

- [V1_GENERAL_ROAD_PARAMETRIC_DESIGN_AUDIT_PLAN.md](./V1_GENERAL_ROAD_PARAMETRIC_DESIGN_AUDIT_PLAN.md) (earlier audit, Watertight oriented)
- [V1_REGION_SURFACE_TRANSITION_PLAN.md](./V1_REGION_SURFACE_TRANSITION_PLAN.md)
- [V1_CENTERLINE_OWNERSHIP_CONSOLIDATION_PLAN.md](./V1_CENTERLINE_OWNERSHIP_CONSOLIDATION_PLAN.md)
- [SESSION_HANDOFF_1014.md](./SESSION_HANDOFF_1014.md)

## 1. Purpose

Drainage, and after it Structure, will be rebuilt. Both sit on the ordinary road workflow:

```text
Project -> TIN -> Alignment -> Stations -> Profile -> 3D Centerline -> Superelevation
        -> Assembly / Subassembly -> Regions -> Applied Sections -> Build Parametric -> Review
```

A review of that workflow on 2026-10-16 found structural problems that would carry straight into the
new Drainage. This plan fixes them first, so Drainage is built on a workflow that knows which results
are current, reads one source per concern, and keeps authoring out of viewers.

## 2. Decisions already taken

- Existing work needs no migration. Saved documents from before a phase may lose data the phase
  removes; no fallback or conversion code is written for them.
- Features that are not needed are removed, not hidden behind flags.
- Ramp stays out of scope and Watertight stays paused until decided otherwise (section 4).
- A document is a General Road document with one Alignment or an Intersection document, never both;
  Drainage and Structure work happens in both kinds (GR-1B).
- CI stays frozen.

## 3. Findings

| Id | Finding | Evidence |
| --- | --- | --- |
| F1 | Upstream edits never mark downstream results stale. Alignment and Profile Apply write the source and call `doc.recompute()`; result objects do nothing in `execute()`, so Stations, Applied Sections and Corridor keep the old state with no sign of it. | `ui/editors/alignment_editor.py` `_apply`, `ui/editors/profile_editor.py` `_apply` |
| F2 | The parts of a stale check exist but are not connected. Stationing stores `SourceGeometrySignature` and only writes a note; `IncrementalRebuildService` is used only by Build Parametric; `make_incremental_record` fingerprints the list of consumed ids, not their content, so a content change is not detected. | `commands/cmd_generate_stations.py` `_previous_stationing_stale_note`, `objects/persistence_payload_adapter.py` `make_incremental_record` |
| F3 | Every `find_v1_*` returns the first matching object in document order. Intersection presets write their own `V1IntersectionPresetSuperelevation*` and `V1IntersectionPresetDrainage` objects beside the editor's objects, so an edit can land in a source the build does not read. Superelevation only reports the shadowing. | `objects/obj_drainage.py` `find_v1_drainage_model`, `commands/cmd_intersection_presets.py` (1476, 1573), `commands/cmd_generate_applied_sections.py` `superelevation_source_rows` |
| F4 | Applied Sections has two build paths: one Alignment through `find_v1_alignment`, several through source bundles. The same request is assembled twice. | `commands/cmd_generate_applied_sections.py` `_build_applied_section_set_pass`, `_build_multi_alignment_applied_section_set` |
| F5 | Applied Sections rebuilds the 3D Centerline itself and swallows every failure (`except Exception: return None`), then continues on a different frame source. The 3D Centerline toolbar stage is a review screen only. | `commands/cmd_generate_applied_sections.py` `_build_applied_sections_centerline3d_result` |
| F6 | The Build Parametric viewer authors source: its Transitions tab creates, updates and toggles `SurfaceTransitionModel` rows. | `ui/viewers/build_corridor_view.py` (Update / Toggle Enabled), `commands/cmd_build_corridor.py` `create_corridor_surface_transition_from_region_boundary` |
| F7 | `OverrideModel` is always built as `overrides:empty`; there is no editor. `OverrideResolutionService` and the request plumbing serve nothing. | `commands/cmd_generate_applied_sections.py` (235, 318) |
| F8 | Ramp has a model and an evaluation service but no command, editor or consumer in the build. | `models/source/ramp_model.py`, `services/evaluation/ramp_evaluation_service.py` |
| F9 | `cmd_build_corridor.py` is 8,468 lines and 340 functions. Shared breakline construction, Drainage and Intersection review rows live in the command instead of services and presentation. | `commands/cmd_build_corridor.py` |
| F10 | The end-to-end smoke skips TIN, 3D Centerline and Superelevation, so terrain daylight and crossfall are never exercised end to end. | `tests/regression/smoke_v1_workflow.py` `_build` |

## 4. Decisions to take before starting

All three were decided by the user on 2026-10-16, each as recommended: remove Ramp (D1), take
Watertight off the toolbar and menu (D2), and store 3D Centerline as a result stage (D3).

| Id | Question | Recommendation |
| --- | --- | --- |
| D1 | Remove Ramp code (F8)? `AGENTS.md` currently says to preserve Ramp compatibility. | Remove, and change the `AGENTS.md` scope line in the same commit. |
| D2 | Watertight Solids (`cmd_watertight_solids.py`, 5,705 lines, plus Simulation package services): remove, or keep paused but take it off the toolbar? | Take it off the toolbar now; decide removal with the Drainage pipe rework, which owns most of its Drainage inputs. |
| D3 | 3D Centerline: review stage only, or a stored result stage that Applied Sections reads? | Stored result stage (GR-4): one owner of the frame, and it fits the stale check of GR-3. |

## 5. Phases

Each phase is one or a few commits, runs the gate of section 7, and adds a CHANGELOG line when the
user sees a difference.

### GR-1. One source object per concern

Goal: a source concern has exactly one document object per Alignment, so every reader and every
editor works on the same rows.

- Rule: the identity of a source object is `(source type, alignment_id)`; types that are project wide
  (Region, Structure, Drainage, Intersection) have one object per project.
- Intersection presets write into the canonical objects instead of creating
  `V1IntersectionPresetSuperelevation*` and `V1IntersectionPresetDrainage`. The preset's Drainage
  low-point handoff is dropped; the intersection kernel already reports the low point as a drainage
  candidate.
- `find_v1_*` for these types resolves the canonical object; a second object of the same identity is a
  validation error, not a silent winner. `superelevation_source_rows` reduces to that error.

Acceptance:

- A document made from an intersection preset and then edited in the Superelevation and Drainage
  editors builds Applied Sections from the edited rows.
- Contract tests cover the canonical lookup and the duplicate error.

Done on 2026-10-16:

- Identity: Profile, Region, Stationing and Superelevation by `AlignmentId`; Drainage per project.
  `find_v1_*` of these types and `find_v1_alignment` take `alignment_id=`; `list_v1_*` lists them.
- Writers resolve the object by identity: `create_or_update_v1_region_model_object`,
  `create_or_update_v1_superelevation_source_object`, `create_or_update_v1_drainage_model_object`
  and `create_v1_stationing`. `object_name` only names a new object.
- Editors work on one road: Regions and Superelevation open the source of the Alignment selected in
  the tree (the first otherwise); the Stations panel pairs a Stationing with its own Alignment and no
  longer takes the first Stationing when something else is selected; the Profile command opens the
  selected road's Profile; editor Apply keeps the object's label.
- Intersection presets write no Drainage source and keep a road's existing Superelevation source.
  The Build Parametric branch for the preset Drainage object is removed.
- `v1/objects/source_identity.py` reports duplicates; Applied Sections refuses to build and lists them
  in its panel. `superelevation_source_rows` and the "authored source wins" pairing rule are removed.
- Tests: `tests/contracts/v1/test_source_identity.py` (new), and updated preset, superelevation and
  Build Parametric tests.
- Left for later: Structure and Intersection keep fixed object names (Structure will be rebuilt);
  the Superelevation and Region panels show no road selector, so another road is chosen by selecting
  it in the tree before opening the panel.

### GR-1B. Document kind: General Road or Intersection

Decided by the user on 2026-10-16: a document is either a general road or an intersection, never
both. A General Road document holds exactly one Alignment. An Intersection document holds the roads of
one intersection, and Drainage and Structure work is done in it too.

Today nothing in the code knows the kind: the toolbar offers Intersection Presets in every document,
Build Parametric shows its Intersections tab and intersection drainage rows everywhere, and Applied
Sections always runs the intersection pass and the multi-Alignment bundle path.

- Project property `DocumentKind`: `general_road`, `intersection`, or empty.
  - Project Setup offers the choice. It can change only while the document has no Alignment.
  - Intersection Presets (both Create From Preset and Use Existing Alignments) sets `intersection` on a
    project whose kind is empty, and refuses on a `general_road` document.
  - An empty kind restricts nothing. The kind is never inferred from the document content.
- Commands, through `IsActive`:

  | Command | General Road | Intersection |
  | --- | --- | --- |
  | Intersection Presets | inactive | active |
  | every other workflow command, Drainage and Structures included | active | active |

- General Road rules:
  - One Alignment. The Alignment editor edits it; creating a second one, or importing one from LandXML
    when one exists, is refused with a message.
  - Applied Sections builds one road: no intersection kernel pass, and an Intersection source in the
    document is an error.
  - Intersection content is not shown: the Build Parametric Intersections tab and intersection
    drainage rows, the Cross Section viewer's intersection rows, and the `Intersections:` line of the
    Applied Sections summary.
  - Editors need no road selection; the GR-1 selection rule simply finds the one road.
- Intersection rules:
  - Several Alignments; the editors follow the Alignment selected in the tree (GR-1).
  - Drainage and Structure stay available; their sources are project wide (GR-1).

Acceptance:

- On a General Road document Intersection Presets is inactive, a second Alignment cannot be created
  or imported, and Build Parametric shows no Intersections tab.
- A preset document is `intersection` and offers every command.
- A document with an empty kind behaves as today.

Done on 2026-10-16:

- `DocumentKind` on the Project (`objects/obj_project.py`), read and written by Project Setup, which
  has a Document Kind field. `document_kind_change_refusal` (Project Setup service) fixes the kind
  once an Alignment exists.
- `v1/objects/document_kind.py`: `document_kind`, `mark_intersection_document` and
  `require_alignment_slot`. The sample, blank and LandXML Alignment creators call
  `require_alignment_slot`; LandXML checks every Alignment id before it writes anything.
- Intersection Presets: `IsActive` is false on a General Road document, both source modes refuse
  one, and both mark an unset document `intersection`.
- Applied Sections refuses an Intersection source in a General Road document and drops the
  `Intersections:` and `Intersection supplemental:` summary lines there. Build Parametric drops the
  Intersections tab and guided step. The Cross Section source owner table drops the Intersection
  row. The intersection drainage rows need an Intersection source, so they were already absent.
- Tests: `tests/contracts/v1/test_document_kind.py` (new).
- Left for later: Project Setup refuses a kind change on Apply rather than disabling the field.
- Changed on 2026-10-16 after review (user decision): "Not set" is removed. A new project stores
  `general_road`. A project that stores no kind (made before the kind existed) is judged by its
  content when read, without writing it: an Intersection source or two or more Alignments make it
  an Intersection document (`inferred_document_kind`). Intersection Presets are available in an
  Intersection document and in a General Road document without an Alignment, and switch the
  latter to `intersection`. This replaces "an empty kind restricts nothing" and "the kind is never
  inferred" above.

### GR-2. Remove dead paths

- Override: remove `OverrideModel`, `OverrideResolutionService`, the request field and the two
  `overrides:empty` constructions (F7).
- Ramp (D1): remove the model, the evaluation service, their exports, the tree routing
  entries and the Region preset text that mentions ramps (F8).
- Watertight (per D2): remove the command from the workbench toolbar and menu.

Acceptance: architecture and contract suites pass; `rg -i "override_model|ramp_model"` finds nothing
in `freecad/`.

Done on 2026-10-16:

- Override: `OverrideModel`, `OverrideResolutionService`, both request fields, the two empty
  constructions, the result rows' `override_ids` and the Region `override_refs` (`OverrideRefRows`)
  were removed. Applied Section subassembly rows keep slot 16 empty so the stored layout is unchanged.
- Ramp: `RampModel`, `RampEvaluationService`, the Ramps tree folder and routing, the "Ramp Tie-In"
  Region preset and the `ramp_ref` / `ramp_policy` fields of Region, Region context and Drainage were
  removed. The unused `ContextReviewOutput` (with its `ramp_rows`) went with them. The Overrides tree
  folder was removed too.
- Region and Drainage objects drop the retired properties when they are next written; no migration.
- Watertight: off the toolbar and menu; the command stays registered.
- `AGENTS.md`, `V1_SUPPORTED_DOMAIN_STATUS.md`, `V1_PERSISTENCE_SCHEMA_INVENTORY.md` and the two model
  documents say so; other historical documents that mention Ramp were left as they are.

### GR-3. Result freshness

Goal: every result knows whether it is current, and the user can rebuild everything downstream from one
place.

- Each result stage records the content fingerprint of the sources and results it consumed:
  Stationing (Alignment), 3D Centerline (Alignment, Profile, Stationing), Applied Sections (Alignment,
  Profile, Stationing, Superelevation, Assembly, Regions, Structure, Drainage, Intersection, TIN),
  Corridor and Surfaces (Applied Sections, Surface Transitions, TIN).
- `make_incremental_record` fingerprints content instead of id lists (F2); the Stationing signature
  becomes one case of the same rule.
- A shared service compares recorded and current fingerprints and returns `current`, `stale` (with the
  changed inputs) or `missing`. It reads sources; it never writes them.
- Presentation: a freshness line in the Applied Sections, Build Parametric and Cross Section panels and
  a `ResultStatus` property on each result object.
- A "Rebuild Downstream" action runs the stale stages in workflow order with their stored options
  (station interval, supplemental sampling settings). It is an explicit action, never a callback.

Rebuild Downstream rules:

- It rebuilds result stages only: Stationing, 3D Centerline, Applied Sections, Corridor and Surfaces.
  It never writes a source and never runs a review.
- A stage runs only when it is stale or a stage it consumes was rebuilt in the same run; current stages
  are skipped. Examples: a Profile edit rebuilds 3D Centerline, Applied Sections, Corridor and Surfaces
  but not Stationing; a Surface Transition edit rebuilds Corridor and Surfaces only.
- Stored options are reused; no dialog is shown. A failing stage stops the run and reports the stage,
  the object and the diagnostic; the stages after it stay stale.

Where it is exposed:

| Place | Form | Scope |
| --- | --- | --- |
| Workbench toolbar and menu | command `CorridorRoad_RebuildDownstream`, placed next to Build Parametric; disabled when nothing is stale | every stale stage |
| Applied Sections panel | button beside the freshness line | stale stages up to and including Applied Sections |
| Build Parametric panel | button beside the freshness line; the panel refreshes afterwards | every stale stage |

Review viewers (Cross Section, Earthwork, Drainage Review, Plan/Profile) show the freshness line and a
hint to run Rebuild Downstream, but no button: viewers stay review surfaces and start no builds. The
project tree context menu does not get the action; it would duplicate the toolbar.

Acceptance:

- Editing a Profile PVI after a full build reports Applied Sections and Corridor as stale with
  `profile` as the changed input; Rebuild Downstream makes them current and leaves Stationing untouched.
- The toolbar command is disabled on a document whose results are all current.
- The Applied Sections panel button does not rebuild Corridor or Surfaces.
- Opening a viewer never changes a fingerprint or a result.

Done on 2026-10-16:

- Stages: Stations (one record per road), 3D Centerline (its review object
  `V1Centerline3DPreview`, regenerated with its recorded display options), Applied Sections and
  Build Parametric (recorded on the Corridor object; Surfaces are built in the same run). Applied
  Sections still evaluate their own centerline, so 3D Centerline and Applied Sections both consume
  Stations directly until GR-4 makes the stored 3D Centerline their shared input.
- `v1/objects/stage_inputs.py` records `StageInputRows` (input key -> content fingerprint) and
  `StageBuildOptions` on each result when it is built: `update_v1_stationing_from_alignment`,
  `show_v1_centerline3d_preview_object`, `apply_v1_applied_section_set` (new `build_options`) and
  `apply_v1_corridor_model`. The Stationing
  `SourceGeometrySignature` and its "previous stationing was stale" note are replaced by it.
- `v1/services/evaluation/result_freshness_service.py` holds the rules (changed keys, upstream
  propagation, text); `v1/objects/result_freshness.py` reads the current inputs. Fingerprints are of
  source model content without labels and display fields. The terrain is fingerprinted by its
  objects' names, counts, bounds and placement, not by converting it to a TIN.
- `CorridorRoad_RebuildDownstream` (toolbar and Corridor menu after Build Parametric): enabled when
  a stage is stale, answer cached for 2 seconds per document because FreeCAD asks often.
  Applied Sections panel button (through Applied Sections), Build Parametric panel button (all).
- Freshness lines in the Applied Sections and Build Parametric summaries; the Cross Section viewer
  reports stale Applied Sections as its result state.
- Tests: `tests/contracts/v1/test_result_freshness.py` (new), updated Stationing tests.
- Left for later:
  - the `ResultStatus` property: keeping it current would mean writing to result objects whenever
    a source changes or a panel reads freshness, which the read-only rule forbids;
  - freshness lines in Plan/Profile (with GR-4), Drainage Review (with the Drainage rework) and
    Earthwork review: their panels are built from preview payloads without the document;
  - `make_incremental_record` still fingerprints the consumed id lists; the stage records above are
    what freshness reads.

### GR-4. 3D Centerline as the frame owner

- Per D3, Build stores `Centerline3DResult`; Applied Sections reads the stored result and reports a
  stale or missing Centerline through GR-3 instead of rebuilding it.
- Remove the `except Exception: return None` fallback (F5). A failed Centerline blocks Applied
  Sections with a diagnostic that names the Alignment and the failing input.

Acceptance: a Centerline failure is visible in the Applied Sections status and diagnostics; no silent
frame switch remains.

Done on 2026-10-16. Decided by the user: Applied Sections require the stored 3D Centerline, and the
separate Alignment/Profile fallback frame is removed.

- `v1/objects/obj_centerline3d.py` stores the `Centerline3DResult` as a typed payload on the 3D
  Centerline object; `show_v1_centerline3d_preview_object` writes it.
- Applied Sections read it through `stored_centerline3d_result`: missing, stale (with the changed
  inputs), unreadable or not ready stops the build with a message that says which and what to run.
  The panel's validation shows the same as `centerline3d_not_usable`. Freshness: Applied Sections
  consume the 3D Centerline stage and record its result fingerprint as the `centerline3d` input.
- The `alignment_profile_fallback` frame is gone. A station the 3D Centerline gives no frame for
  stops the build with the road, the station and the causes: a section without a frame has no
  position, so it is not built rather than marked. Within the 3D Centerline frame service, the
  exact source-geometry frame and the interpolation of the stored result are both 3D Centerline
  frames and stay; each records its `source_mode`.
- Build Parametric's centerline preview, supplemental frames and consumed-centerline ids read the
  stored result; its `except Exception: return None` evaluation is gone.
- Rebuild Downstream generates a missing 3D Centerline, with the default options, when the run
  reaches existing Applied Sections.
- Tests: `tests/contracts/v1/test_centerline3d_stored_result.py` (new). Applied Sections, Build
  Parametric and result-builder tests now generate the 3D Centerline, or give their synthetic roads
  coordinates and a second profile point, which the removed fallback used to cover.
- Left for later: the Superelevation, Structure and Intersection editors and Drainage Review still
  evaluate a centerline for their own previews; Applied Section readers keep recognising
  `alignment_profile_fallback` in results stored before this change.

### GR-5. Surface Transitions authored in Regions

- Move create, update and enable/disable of Surface Transition ranges to the Regions editor, next to
  the Region boundaries they belong to.
- The Build Parametric Transitions tab becomes read-only review (boundary list, highlight).

Acceptance: Build Parametric writes no source object; the Region editor round-trips transition rows.

Done on 2026-10-16:

- `v1/services/editing/surface_transition_editing_service.py`: editor rows (station, half length,
  spacing, enabled) become `SurfaceTransitionRange`s. From and To follow from the Region rows at
  Apply, so a transition keeps its station when the editor renumbers Regions; a row on an existing
  range's station keeps that range's mode, targets and approval. Ranges are owned per road
  (`source_ref` `region-editor:<alignment id>`); in a one-road document every range is the road's.
- Regions panel: a Surface Transitions table with Add at Region Boundaries, Add Transition and
  Delete Transition, validated with the Regions and stored on the same Apply
  (`apply_v1_surface_transition_rows`).
- Build Parametric: the transition list is review only. The boundary combo, spacing controls,
  Update and Toggle Enabled and the five command functions behind them are removed. Build
  Parametric's transition options also allowed a station inside a Region (from = to); the Regions
  panel keeps that through Add Transition and an edited STA.
- Tests: `tests/contracts/v1/test_region_surface_transitions.py` (new); Build Parametric tests store
  transitions through a helper instead of the removed functions.

### GR-6. One Applied Sections build path

- Build every document through source bundles (F4): a General Road document is one bundle, an
  Intersection document one bundle per road plus the intersection kernel passes (GR-1B).
- Remove the single-Alignment `find_v1_alignment` / `find_v1_profile` path from the build.

Acceptance: section results of the workflow smoke and the intersection kernel smokes are unchanged.

Done on 2026-10-16:

- `_build_applied_section_set_pass` builds every road from its bundle (`_bundle_build_request`) and
  reads the project-wide sources once. One road returns its set as `applied-sections:main`, as the
  single-road path did; several are merged (`_merged_applied_section_set`) as before.
- The `find_v1_alignment` / `find_v1_profile` / `find_v1_region_model` / `find_v1_stationing` path
  and its unused Assembly fallback are gone. A missing source is reported from the bundles in the
  same words ("Required v1 sources are missing: ...").
- Checked: the Applied Sections of the workflow document and of the T, Cross and Roundabout presets
  have the same section count, set id and content fingerprint before and after.
- Behaviour change: a Profile, Region, Stationing or Superelevation source of another Alignment is
  no longer read for a road; the single-road path took the first object of each kind.
- Tests: `tests/contracts/v1/test_applied_sections_one_build_path.py` (new).

### GR-7. Split `cmd_build_corridor.py`

- Move shared breakline construction to `services/builders/`.
- Move Guided Review, Region and Intersection review rows to `ui/presentation/`.
- The Drainage review rows are not moved; the Drainage rework replaces them.
- Behavior does not change; one move per commit.

Acceptance: the command module keeps only document, service and UI coordination.

Done on 2026-10-16, one commit per move, no behaviour change:

1. Shared breakline construction (23 pure functions) to
   `services/builders/corridor_shared_breakline_service.py`.
2. Guided Review step table and step rules to `ui/presentation/guided_review_presentation.py`.
3. Region review rows to `ui/presentation/region_review_presentation.py`; the command passes the
   generated-object check, which reads the document, as a function.
4. The intersection Guided Review summary to `ui/presentation/intersection_kernel_review_presentation.py`,
   next to the kernel review rows that were already there.

The command imports the moved names back, so callers, tests and the Build Parametric panel's
runtime bindings are unchanged; `tests/contracts/v1/test_build_corridor_runtime_bindings.py` (new)
checks that every collaborator the panel expects is still bound. `cmd_build_corridor.py` went from
8,957 lines and 330 functions to 7,844 lines and 292 functions.

Not met yet: the module still holds the FreeCAD preview builders (surfaces, Region previews,
highlights, markers), which are document coordination, and some pure helpers they use. Splitting
the preview builders into an adapter is a separate step; the Drainage review rows wait for the
Drainage rework, as planned.

### GR-8. Workflow smoke coverage

- Extend `smoke_v1_workflow.py` with a TIN existing ground, the 3D Centerline stage and a
  Superelevation source, and with the GR-3 stale and rebuild check.

## 6. Order and relation to Drainage

```text
GR-1 -> GR-1B -> D1-D3 -> GR-2 -> GR-3 -> GR-4 -> GR-5 -> GR-6 -> GR-8 -> Drainage rework -> Structure rebuild
                                                         GR-7 (with or after Drainage)
```

GR-1 removes the cause of the Drainage object ambiguity. GR-1B fixes the scope every later phase
works in: one road for General Road documents, and intersection content only where it belongs. GR-3 gives the new Drainage results a
freshness state from the start. GR-7 can wait: the Drainage rework rewrites the largest part of the
review code it would move.

## 7. Validation per phase

```powershell
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m flake8 <touched files>
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pytest tests\architecture tests\contracts -q -p no:cacheprovider
.\tests\regression\run_short_term_smokes.ps1
.\tests\regression\run_practical_scope_smokes.ps1
.\tests\regression\run_loft_retirement_gate_smokes.ps1
```

The gate is headless. GR-3, GR-4 and GR-5 change what the user sees and need a GUI check: edit
upstream, see the stale state, rebuild downstream, and author a transition in Regions.

## 8. Non-goals

- New engineering features (new subassemblies, new superelevation rules, new TIN tools).
- Automatic recompute on every edit; rebuilding stays an explicit action.
- Performance work beyond not rebuilding current stages.
- Drainage, Structure and Intersection behavior beyond what GR-1 and GR-3 require.
