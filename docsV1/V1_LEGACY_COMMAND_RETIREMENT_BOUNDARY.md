# Parametric Road V1 Legacy Command Retirement Boundary

Date: 2026-09-05
Branch: `ganada_0902`
Status: Decision record. No code is removed by this document.
Depends on:

- `docsV1/V1_ARCHITECTURE_DEBT_EXECUTION_PLAN.md` milestone M7
- `docsV1/V1_SUPPORTED_DOMAIN_STATUS.md`
- `AGENTS.md`

## 1. Purpose

`freecad/Corridor_Road/{objects,ui,commands}` outside the `v1` package holds 51,368 lines, and `init_gui.py` imports 13 command modules from the legacy `commands` package. Until now there was no record of which of those still matter, which are already v1 in everything but their file location, and what removing any of them would actually cost.

This document is that record. It deletes nothing and changes no behavior. It exists so that a later retirement task starts from measurement rather than from the word "legacy".

## 2. What This Record Does Not Do

- It does not remove any module, command, or command ID.
- It does not change the toolbar or the menus.
- It does not decide whether a command should eventually be retired. That remains open decision 4 in the execution plan.
- It does not authorize touching Ramp or Watertight Solid code.

## 3. Registration Inventory

Measured on 2026-09-05 from `init_gui.py` and the command modules themselves.

`init_gui.Initialize` imports 13 modules from the legacy `commands` package and 21 from `v1/commands`. The workbench surfaces 24 command ids across the toolbar and menus.

| Legacy module | Command id | Surfaced | Lines | What backs it |
| --- | --- | --- | --- | --- |
| `cmd_generate_corridor` | `CorridorRoad_GenerateCorridor` | yes | 40 | v1 `cmd_build_corridor` |
| `cmd_view_cross_section` | `CorridorRoad_ViewCrossSection` | yes | 63 | v1 `cmd_view_sections` |
| `cmd_review_plan_profile` | `CorridorRoad_ReviewPlanProfile` | yes | 93 | v1 `cmd_review_plan_profile` |
| `cmd_generate_cut_fill_calc` | `CorridorRoad_GenerateCutFillCalc` | yes | 64 | v1 `cmd_earthwork_balance` |
| `cmd_project_setup` | `CorridorRoad_ProjectSetup` | yes | 62 | v0 `ui/task_project_setup` |
| `cmd_outputs_exchange` | `CorridorRoad_OutputsExchange` | yes | 45 | self-contained |
| `cmd_ai_assist` | `CorridorRoad_AIAssist` | yes | 43 | self-contained |
| `cmd_new_project` | `CorridorRoad_NewProject` | no | 98 | v0 `ui/task_project_setup` |
| `cmd_create_alignment` | `CorridorRoad_CreateAlignment` | no | 59 | self-contained |
| `cmd_edit_alignment` | `CorridorRoad_EditAlignment` | no | 27 | v0 `ui/task_alignment_editor` |
| `cmd_review_alignment` | `CorridorRoad_ReviewAlignment` | no | 80 | v0 `ui/task_alignment_editor` |
| `cmd_edit_typical_section` | `CorridorRoad_EditTypicalSection` | no | 25 | v0 `ui/task_typical_section_editor` |
| `cmd_edit_regions` | `CorridorRoad_EditRegions` | no | 27 | v0 `ui/task_region_editor` |

"Surfaced" means the command id appears in `corridorroad_workflow_command_groups`, and therefore in the toolbar and a menu. A module that is not surfaced is still imported, so its command id is still registered and still reachable from a macro, a custom toolbar, or `Gui.runCommand`.

## 4. Classification

### 4.1 Four surfaced modules are v1 bridges, not v0 code

`cmd_generate_corridor`, `cmd_view_cross_section`, `cmd_review_plan_profile`, and `cmd_generate_cut_fill_calc` total 260 lines and contain no engineering behavior. Each registers a stable command id and calls a v1 entry point. `cmd_generate_corridor` is the clearest case:

```python
class CmdGenerateCorridor:
    def Activated(self):
        from freecad.Corridor_Road.v1.commands.cmd_build_corridor import (
            run_v1_build_corridor_command,
        )
        run_v1_build_corridor_command()
```

The command id `CorridorRoad_GenerateCorridor` is recorded in `corridor_compat.PREFERRED_COMMAND_ID`, and `AGENTS.md` requires command ids to stay stable.

These four are the compatibility mechanism, not the debt. Retiring them would mean changing user-visible command ids for Build Parametric, Cross Section review, Plan/Profile review, and Earthwork, which the general development rules forbid. **Recommendation: keep, and stop describing them as legacy.** The accurate description is "stable command id bridging to a v1 engine". Only their file location is legacy, and moving them is a cosmetic change with a compatibility cost.

### 4.2 Three surfaced modules are genuinely non-v1

| Module | Status |
| --- | --- |
| `cmd_project_setup` | opens the v0 task panel `ui/task_project_setup`. Project Setup is stage 1 of the v1 workflow and has no v1 replacement command. |
| `cmd_outputs_exchange` | self-contained entry point. `V1_SUPPORTED_DOMAIN_STATUS.md` lists Exchange as "supported current paths" with complete format coverage as future work. |
| `cmd_ai_assist` | self-contained entry point. The status index lists AI Assist as review and proposal only. |

None of the three has a v1 replacement, so none is a retirement candidate today. `cmd_project_setup` is the one with a real successor gap: it is the only surfaced workflow stage still driven by a v0 task panel.

### 4.3 Six modules are registered but not surfaced

`cmd_new_project`, `cmd_create_alignment`, `cmd_edit_alignment`, `cmd_review_alignment`, `cmd_edit_typical_section`, and `cmd_edit_regions` total 316 lines. Each has a v1 successor that is surfaced instead:

| Not surfaced | Surfaced v1 successor |
| --- | --- |
| `CorridorRoad_NewProject` | `CorridorRoad_ProjectSetup` |
| `CorridorRoad_CreateAlignment`, `CorridorRoad_EditAlignment`, `CorridorRoad_ReviewAlignment` | `CorridorRoad_V1EditAlignment` |
| `CorridorRoad_EditTypicalSection` | `CorridorRoad_V1EditAssemblySubassembly` |
| `CorridorRoad_EditRegions` | `CorridorRoad_V1EditRegions` |

This is the real retirement candidate set. These commands are already invisible in normal use; the only cost of unregistering them is to a user who invokes the id directly.

## 5. Document Restoration Impact

The decisive question for any retirement is whether an existing FCStd document depends on a command module. It does not.

- No module in `commands` or `v1/commands` assigns `.Proxy`. Persisted proxies therefore never name a command module.
- `virtual_paths._PROXY_OBJECT_MODULES` lists exactly 15 modules for eager restore, and all 15 are `obj_*` modules in the legacy `objects` package.
- `virtual_paths._LEGACY_PREFIX_TO_CANONICAL` does map a bare `commands` prefix to the canonical namespace, but that is a defensive prefix rule, not evidence that a proxy lives in a command module.

**Removing a legacy command from the toolbar, from a menu, or from `init_gui.Initialize` cannot break document restoration.** What it can break is different and smaller:

- a user macro or custom toolbar that invokes the command id
- a workflow habit, where a familiar button disappears

That distinction matters, because it moves the retirement question out of compatibility risk and into user-experience judgement.

## 6. Frozen Legacy Persistence Surfaces

The following are declared frozen read-and-restore compatibility surfaces. They keep working, they receive only critical repair, data-loss prevention, and compatibility fixes, and they receive no feature work.

| Module | Lines | Note |
| --- | --- | --- |
| `objects/obj_section_set.py` | 5,569 | largest legacy persistence module |
| `objects/obj_corridor.py` | 2,974 | legacy corridor proxy |
| `objects/obj_project.py` | 2,747 | still live, see below |

`obj_project.py` is frozen in the sense above but is **not** dormant. 23 v1 modules import it, and since milestone M1 the single v1 entry point for project-tree routing, `route_object_to_project_tree`, delegates to `route_to_v1_tree` in this module. Freezing it means no new legacy behavior, not no use.

The whole legacy `objects` package is 31 files and 25,945 lines; legacy `ui` is 21 files and 24,255 lines. Neither is a candidate for removal while `_PROXY_OBJECT_MODULES` and the surfaced v0 panels depend on them.

## 7. Retirement Status Summary

| Status | Count | Modules |
| --- | --- | --- |
| Keep, stable-id bridge to v1 | 4 | `cmd_generate_corridor`, `cmd_view_cross_section`, `cmd_review_plan_profile`, `cmd_generate_cut_fill_calc` |
| Keep, no v1 successor exists | 3 | `cmd_project_setup`, `cmd_outputs_exchange`, `cmd_ai_assist` |
| Retirement candidate, v1 successor surfaced, currently hidden | 6 | `cmd_new_project`, `cmd_create_alignment`, `cmd_edit_alignment`, `cmd_review_alignment`, `cmd_edit_typical_section`, `cmd_edit_regions` |

No module is removed by this record.

## 8. Open Decision

Execution plan open decision 4 remains open and is the maintainer's call:

> Is a legacy command with a complete v1 replacement unregistered in a later task, or retained indefinitely for user familiarity?

The measurement above narrows it. The decision applies to the 6 modules in section 4.3 only, it carries no document-restoration risk, and the cost is limited to macros, custom toolbars, and familiarity. The other 7 modules are not part of the question.

A separate and larger question, out of scope here, is whether `cmd_project_setup` should gain a v1 successor so that no surfaced workflow stage is driven by a v0 task panel.
