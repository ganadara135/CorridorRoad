# Loft Alias Retirement Execution Plan

Current state:

- `Phase 5C` retirement-gate coverage is in place.
- `tests/regression/run_loft_retirement_gate_smokes.ps1` can rerun the bundled gate set.
- Command and task-panel alias retirement is complete under a no-compatibility override.

## Goal

Retire the remaining `Loft` compatibility aliases in a staged order, with each step independently verifiable.

## Execution Principles

- Remove one compatibility axis at a time.
- Start with the least persistence-sensitive alias.
- Keep FCStd persistence and proxy-restore work for the final stages.
- Do not start a higher-risk removal until the current step passes its smoke checks.

## Retirement Order

### Step 1. Command Alias Retirement

Target:

- `CorridorRoad_GenerateCorridorLoft`

Why first:

- It is the least persistence-sensitive compatibility point.

Preconditions:

1. `CorridorRoad_GenerateCorridor` is the only preferred command id in docs and UI.

Current readiness snapshot:

- Status: completed under compatibility override
- Ready:
  - preferred command id in code/workbench UI is already `CorridorRoad_GenerateCorridor`
  - legacy command registration and wrapper can now be removed without preserving toolbar/macro compatibility

Implementation:

1. Remove legacy command registration from `freecad/Corridor_Road/commands/cmd_generate_corridor.py`.
2. Remove now-unused legacy command constants from `freecad/Corridor_Road/corridor_compat.py`.
3. Remove `freecad/Corridor_Road/commands/cmd_generate_corridor_loft.py`.
4. Update command-boundary smoke coverage.

Validation:

1. Run `tests/regression/run_loft_retirement_gate_smokes.ps1`.

### Step 2. Task-Panel Import Alias Retirement

Targets:

- `freecad/Corridor_Road/ui/task_corridor_loft.py`
- `CorridorLoftTaskPanel`

Why second:

- Import compatibility is easier to retire than persisted project/proxy compatibility.

Preconditions:

1. In-repo runtime imports no longer depend on the legacy task-panel path/class.
2. External import compatibility is no longer required.

Current readiness snapshot:

- Status: completed under compatibility override
- Ready:
  - canonical runtime imports already point to `task_corridor.py` and `CorridorTaskPanel`
  - wrapper file and class alias can now be removed outright

Implementation:

1. Remove `task_corridor_loft.py`.
2. Remove `CorridorLoftTaskPanel = CorridorTaskPanel` from `task_corridor.py`.
3. Update task-panel boundary and compatibility smokes.

Validation:

1. Run `tests/regression/run_loft_retirement_gate_smokes.ps1`.
2. Recheck panel open/build smoke coverage.

### Step 3. Hidden Project-Link Migration Introduction

Target:

- hidden property `CorridorLoft`

Why third:

- Older FCStd project reopen still depends on this property name.

Preconditions:

1. Replacement persistence path is designed.
2. `assign_project_corridor()` / `resolve_project_corridor()` can prefer the new path while preserving fallback behavior.

Implementation:

1. Add the replacement project corridor persistence property/path.
2. Add migration-on-open or helper resynchronization logic.
3. Keep old hidden property read fallback during the migration cycle.

Validation:

1. Reopen older FCStd samples.
2. Save/reopen new files using the new path.
3. Extend project-link and FCStd restore smokes as needed.

### Step 4. Hidden Project-Link Retirement

Target:

- hidden property `CorridorLoft`

Preconditions:

1. Older FCStd reopen succeeds through the replacement path.
2. Smokes pass without resynchronizing through the compatibility property.

Implementation:

1. Remove hidden compatibility property creation from `obj_project.py`.
2. Remove old fallback read/write paths.
3. Update project-link boundary smokes.

Validation:

1. Run `tests/regression/run_loft_retirement_gate_smokes.ps1`.
2. Recheck old/new FCStd reopen manually.

### Step 5. Child-Link Migration Introduction

Target:

- `ParentCorridorLoft`

Why fourth:

- Generated corridor child ownership still persists through this compatibility name.

Preconditions:

1. Replacement child ownership property/path is designed.
2. Segment/skip-marker creation, adoption, and recovery understand the new path.

Implementation:

1. Add a replacement child-link property.
2. Write the new property during generation while keeping old read fallback.
3. Update `obj_corridor_loft.py`, `obj_project.py`, and `task_corridor.py`.

Validation:

1. Re-run tree/adoption coverage.
2. Extend child-link and restore smokes as needed.

### Step 6. Child-Link Retirement

Target:

- `ParentCorridorLoft`

Preconditions:

1. Tree/adoption/restore smokes pass without the compatibility child-link.

Implementation:

1. Remove old property creation and lookup paths.
2. Keep only the replacement ownership path.

Validation:

1. Run `tests/regression/run_loft_retirement_gate_smokes.ps1`.
2. Manually verify skip-marker and segment ownership recovery.

### Step 7. Proxy/Type/Module Rename Introduction

Targets:

- `CorridorLoft`
- `obj_corridor_loft.py`
- virtual-path alias mapping

Why last:

- This is the highest-risk FCStd restore boundary.

Preconditions:

1. Canonical replacement proxy/type/module name is chosen.
2. Restore-bridge strategy is designed.
3. New canonical path exists before old compatibility is removed.

Implementation:

1. Introduce the new proxy/type/module path.
2. Keep restore bridge and virtual-path fallback during the migration window.
3. Update routing/helpers to prefer the new canonical path.

Validation:

1. Reopen older FCStd files.
2. Save/reopen new files using the renamed path.
3. Extend proxy and FCStd restore smokes.

### Step 8. Proxy/Type/Module Retirement

Targets:

- old `CorridorLoft` proxy/type/module path
- `obj_corridor_loft.py` compatibility path
- related virtual-path fallback

Preconditions:

1. The renamed path has passed restore/reopen validation.
2. Compatibility fallback is no longer required for supported files/macros.

Implementation:

1. Remove old proxy/type/module compatibility code.
2. Remove obsolete entries from `virtual_paths.py`.
3. Clean up remaining compatibility-only documentation.

Validation:

1. Run `tests/regression/run_loft_retirement_gate_smokes.ps1`.
2. Re-run additional practical/regression coverage as needed.

## PR Breakdown

Recommended pull-request sequence:

1. PR-1: command alias retirement
2. PR-2: task-panel alias retirement
3. PR-3: hidden project-link migration introduction
4. PR-4: hidden project-link retirement
5. PR-5: child-link migration introduction and retirement
6. PR-6: proxy/type/module rename introduction
7. PR-7: proxy/type/module retirement

## Common Checklist

Apply this checklist to every retirement step:

1. Update code for only one compatibility axis.
2. Update or replace the matching boundary smoke.
3. Run `tests/regression/run_loft_retirement_gate_smokes.ps1`.
4. Update `docs/LOFT_REMOVAL_PLAN.md` progress and active step.
