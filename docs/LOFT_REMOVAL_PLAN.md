# Loft Removal Plan

Current state:

- User-facing `Loft` wording cleanup is complete.
- Live runtime `Part.makeLoft(...)` usage is removed.
- Remaining work is compatibility-name retirement and historical-note cleanup.

## Goal

Retire `Loft` as the default corridor concept without breaking file compatibility or removing live runtime paths too early.

This plan separates three different kinds of `Loft` usage:

1. User-facing wording such as `Corridor Loft`
2. Internal compatibility names such as `CorridorLoft` and `CorridorRoad_GenerateCorridorLoft`
3. Runtime geometry dependencies such as `Part.makeLoft(...)`

They must not be removed in one pass.

## Principles

- `Corridor` is the preferred product term.
- `CorridorLoft` remains only where compatibility still requires it.
- `Part.makeLoft(...)` was a legacy runtime dependency and is now removed from live runtime paths.
- Documentation cleanup happens before code rename work.
- Runtime removal happens last.

## Phase Breakdown

### Phase 1. Documentation Cleanup

Status: completed

#### Phase 1A. Core docs

Scope:

- `docs/ARCHITECTURE.md`
- `docs/wiki/Developer-Guide.md`

Tasks:

1. Replace `Corridor Loft` with `Corridor` where the text describes the current product concept.
2. Rewrite `Loft`-centric explanations so the preferred runtime is described as corridor surface assembly or section-strip assembly.
3. Keep `CorridorLoft` only where the text is explicitly documenting internal compatibility names.
4. Mark `Part.makeLoft(...)` as a historical path during the migration window.

Done when:

- Core docs describe `Corridor` as the surface object concept.
- `Loft` appears only in compatibility notes, historical notes, or migration-plan notes.

#### Phase 1B. Workflow and reference docs

Scope:

- `docs/MIXED_WORKFLOW_VALIDATION_MATRIX.md`
- `docs/PRACTICAL_SAMPLE_SET.md`
- `docs/SURFACE_COMPARISON_SOURCE_MATRIX.md`
- `docs/TYPICAL_SECTION_DITCH_SHAPES_PLAN.md`
- `docs/TYPICAL_SECTION_EXECUTION_PLAN.md`
- `docs/CODEX_PROMPTS.md`

Tasks:

1. Replace user-facing `Corridor Loft` wording with `Corridor`.
2. Rewrite `ruled loft` wording into corridor-build wording unless the text is intentionally historical.
3. Keep internal symbol names such as `CorridorLoft` only when the document refers to code symbols or file compatibility.

Done when:

- Workflow docs no longer present `Loft` as the normal user term.

#### Phase 1C. Remaining doc audit

Scope:

- Remaining `docs/**` hits for `Loft`, `Corridor Loft`, `CorridorLoft`, and `makeLoft`

Tasks:

1. Classify each hit as one of:
   - historical note
   - compatibility note
   - active cleanup target
2. Add short notes to historical planning docs instead of rewriting past decisions beyond recognition.
3. Record any code follow-up needed by documentation findings.

Done when:

- Every remaining `Loft` mention in docs has an intentional reason to exist.

### Phase 2. User-Facing Code Wording Cleanup

Status: completed

#### Phase 2A. Commands, panels, and visible status text

Tasks:

1. Replace `Corridor Loft` labels with `Corridor`.
2. Remove `Loft`-centric status text such as `full loft failed` or `ruled loft`.
3. Keep legacy command aliases only where backward compatibility needs them.

#### Phase 2B. Test text and visible contract wording

Tasks:

1. Rename user-visible test expectations and messages to `Corridor` where appropriate.
2. Keep code-symbol references to `CorridorLoft` only where tests must target the current internal API.

### Phase 3. Internal Compatibility Isolation

Status: completed

#### Phase 3A. Alias boundaries

Tasks:

1. Route project links and command lookups through helpers rather than direct `CorridorLoft` name reads.
2. Document which internal names are still required for FCStd, macros, or toolbar compatibility.

Status note:

- Project and task-panel flows should prefer corridor helper functions over direct hidden-property reads.

#### Phase 3B. Compatibility notes

Tasks:

1. Document the compatibility window.
2. Define exit criteria for removing each alias.

Compatibility window targets:

1. Command alias
   - Keep: `CorridorRoad_GenerateCorridorLoft`
   - Why: older toolbar layouts and user macros may still call the legacy id
   - Remove only when:
     - `CorridorRoad_GenerateCorridor` is the only preferred id in docs and UI
     - release notes have warned about the alias retirement for at least one release cycle
     - toolbar/menu/macro compatibility is explicitly re-verified
2. Project hidden link property
   - Keep: hidden property `CorridorLoft`
   - Why: older FCStd files may restore project corridor links through that property name
   - Remove only when:
     - a replacement persistence path exists
     - old FCStd files reopen with corridor links preserved
     - project-link helpers no longer need the compatibility property
3. Proxy/module/type naming
   - Keep: proxy/type/module compatibility names such as `CorridorLoft`
   - Why: FCStd proxy restore and legacy module-path recovery still depend on them
   - Remove only when:
     - virtual path alias coverage handles the rename
     - old FCStd files reopen without proxy restore regressions
     - targeted restore/recompute smokes cover the renamed path

Done when:

- Every retained `CorridorLoft` compatibility point has a written owner, reason, and removal gate.
- New code paths use helpers instead of reading compatibility names directly.

### Phase 4. Runtime `Part.makeLoft(...)` Removal

Status: completed

#### Phase 4A. Section-strip fallback review

Status: completed

Tasks:

1. Verify whether `section_strip_builder.py` still needs the pair-surface `makeLoft` fallback.
2. Remove it only if strip assembly fully covers the behavior.

#### Phase 4B. StructureSet solid replacement

Status: completed

Tasks:

1. Replace `obj_structure_set.py` profile-segment solid generation that still depends on `Part.makeLoft`.
2. Add focused regression coverage before removal.

#### Phase 4C. Corridor internal solid-path cleanup

Status: completed

Tasks:

1. Retire `obj_corridor_loft.py` solid-path `makeLoft` use only after equivalent behavior exists.
2. Keep surface-only corridor behavior stable during the transition.

### Phase 5. Final Legacy Removal

Status: in progress

Tasks:

1. Move live code paths to preferred names while keeping compatibility aliases where FCStd/macros still require them.
2. Remove stale aliases and migration notes after the compatibility window closes.
3. Update remaining tests and docs to match the final naming state.
4. Re-run targeted regression coverage for corridor, section, structure, and cut-fill workflows.

Current Phase 5 note:

- Current active step: `Phase 5D - bundled retirement-gate rerun and release handoff prep`
- Preferred command path already uses `CorridorRoad_GenerateCorridor`.
- Preferred command module path now uses `cmd_generate_corridor.py`, while `cmd_generate_corridor_loft.py` remains as a compatibility wrapper.
- Preferred task-panel class path now uses `CorridorTaskPanel`, while `CorridorLoftTaskPanel` remains as a compatibility alias.
- Preferred task-panel module path now uses `task_corridor.py`, while `task_corridor_loft.py` remains as a compatibility wrapper.
- Corridor compatibility names are now centralized in `freecad/Corridor_Road/corridor_compat.py`.
- Raw compatibility literals in recompute routing and task-panel corridor creation now also resolve through `corridor_compat.py`.
- Legacy corridor command id is now expected to remain only inside the compatibility-registration boundary, not in normal workbench UI wiring.
- Legacy task-panel module/class aliases are now expected to remain only inside the compatibility import boundary, not in normal runtime imports.
- Hidden corridor project-link property is now expected to remain only inside the project-link helper boundary, not in normal runtime feature code.
- Corridor child-link ownership property is now expected to remain only inside the corridor ownership-recovery boundary, not in unrelated runtime code.
- Corridor proxy/type/name-prefix compatibility is now expected to remain only inside the FCStd restore and corridor-routing boundary, not in unrelated runtime code.
- Compatibility gates now have direct regression coverage:
  - `tests/regression/smoke_corridor_compat_aliases.py`
  - `tests/regression/smoke_corridor_child_link_boundary.py`
  - `tests/regression/smoke_corridor_command_alias_boundary.py`
  - `tests/regression/smoke_corridor_project_link_boundary.py`
  - `tests/regression/smoke_corridor_proxy_boundary.py`
  - `tests/regression/smoke_corridor_taskpanel_alias_boundary.py`
  - `tests/regression/smoke_corridor_fcstd_restore.py`
  - `tests/regression/smoke_tree_schema.py`
  - bundled runner: `tests/regression/run_loft_retirement_gate_smokes.ps1`
- Hard blockers still preventing full internal-name removal:
  - FCStd proxy/type restore still depends on `CorridorLoft`
  - hidden project link property `CorridorLoft` is still part of compatibility reopen logic
  - generated child-link property `ParentCorridorLoft` is still part of corridor segment/skip-marker ownership recovery
  - legacy command id `CorridorRoad_GenerateCorridorLoft` is still retained for older toolbars/macros

Recommended retirement order from this point:

1. Command alias retirement
   - target: `CorridorRoad_GenerateCorridorLoft`
   - why first: it is the least persistence-sensitive compatibility point
   - gate:
     - preferred command id has stayed documented for at least one release cycle
     - in-repo workbench wiring and internal code no longer reference the legacy id except at the compatibility registration boundary
     - toolbar/menu/macro compatibility has been manually re-checked
     - release notes explicitly announce alias removal
2. Task-panel import alias retirement
   - targets: `task_corridor_loft.py`, `CorridorLoftTaskPanel`
   - why second: import compatibility is easier to remove than persisted proxy/type names once command alias fallout is understood
   - gate:
     - in-repo runtime imports no longer reference the legacy task-panel module/class except at the compatibility import boundary
     - no in-repo imports still depend on the legacy task-panel path
     - compatibility smoke no longer needs the legacy import branch
3. Hidden project link retirement
   - target: hidden property `CorridorLoft`
   - why third: FCStd project reopen still depends on it today
   - gate:
     - in-repo runtime code no longer references the hidden compatibility property except through the project-link helper boundary
     - replacement persistence path exists
     - FCStd reopen smokes pass without resynchronizing through the compatibility property
4. Child-link property retirement
   - target: `ParentCorridorLoft`
   - why fourth: generated child ownership still persists through that compatibility name
   - gate:
     - in-repo runtime code no longer references the compatibility child-link except through the corridor ownership-recovery boundary
     - segment/skip-marker ownership recovery uses a replacement property name
     - tree/adoption and reopen smokes pass with the replacement path
5. Proxy/module/type retirement
   - targets: `CorridorLoft`, `obj_corridor_loft.py`, virtual-path alias mapping
   - why last: this is the highest-risk FCStd restore boundary
   - gate:
     - in-repo runtime code no longer references proxy/type/name-prefix compatibility except through FCStd restore and corridor-routing boundaries
     - canonical replacement proxy/type/module path exists
     - FCStd reopen/restore smokes pass for the renamed path
     - virtual-path fallback can be removed without restore regressions

## Current Phase 1 Work Log

- [x] Draft the phased plan
- [x] Start Phase 1A core documentation cleanup
- [x] Complete Phase 1B workflow/reference documentation cleanup
- [x] Complete Phase 1C remaining doc audit
- [x] Summarize remaining code tasks uncovered by docs

## Phase 1 Audit Snapshot

Intentional remaining `Loft` mentions in `docs/` now fall into these buckets:

1. Historical migration plans
   - `docs/CORRIDOR_V2_REGION_PLAN.md`
   - `docs/CORRIDOR_V2_REGION_EXECUTION_PLAN.md`
   - `docs/ROADMAP_TODO_2026-03-29.md`
2. Historical architecture note
   - `docs/ARCHITECTURE.md` records the removed `Part.makeLoft(...)` path for migration context
3. This plan document
   - `docs/LOFT_REMOVAL_PLAN.md`

Code follow-up identified by the doc audit:

1. Remove remaining user-facing `Loft` wording from command and panel code.
2. Keep `CorridorLoft` internal names only behind compatibility boundaries.
3. Runtime `Part.makeLoft(...)` removal is complete; remaining work is compatibility-name retirement only.

## Progress Snapshot

- [x] Phase 1 documentation cleanup
- [x] Phase 2 user-facing wording cleanup in code and regression messages
- [x] Phase 3A helper-first corridor resolution in task panels and project-link flows
- [x] Phase 3B compatibility-window documentation
- [x] Phase 4A section-strip fallback removal
- [x] Phase 4B StructureSet solid replacement
- [x] Phase 4C corridor solid-path replacement/removal
- [x] Phase 5A preferred task-panel path cleanup (`CorridorTaskPanel`)
- [x] Phase 5A2 preferred module path cleanup (`cmd_generate_corridor.py`, `task_corridor.py`)
- [x] Phase 5B compatibility gate regression coverage
- [x] Phase 5B2 compatibility-name centralization (`corridor_compat.py`)
- [x] Phase 5C1 child-link compatibility retirement gate (`ParentCorridorLoft`)
- [x] Phase 5C2 FCStd restore/reopen smoke coverage (`smoke_corridor_fcstd_restore.py`)
- [x] Phase 5C3 raw compatibility literal isolation (`obj_region_plan.py`, `obj_structure_set.py`, `task_corridor.py`)
- [x] Phase 5C4 alias retirement sequencing and exit-check ownership
- [x] Phase 5C5 command alias boundary coverage (`smoke_corridor_command_alias_boundary.py`)
- [x] Phase 5C6 task-panel alias boundary coverage (`smoke_corridor_taskpanel_alias_boundary.py`)
- [x] Phase 5C7 hidden project-link boundary coverage (`smoke_corridor_project_link_boundary.py`)
- [x] Phase 5C8 child-link ownership boundary coverage (`smoke_corridor_child_link_boundary.py`)
- [x] Phase 5C9 proxy/type/module boundary coverage (`smoke_corridor_proxy_boundary.py`)
- [x] Phase 5C compatibility alias retirement gates
- [x] Phase 5D bundled retirement-gate runner (`run_loft_retirement_gate_smokes.ps1`)
