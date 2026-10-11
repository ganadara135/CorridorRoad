# V1 Session Handoff

Date: 2026-10-11
Branch: `ganada_0902`, 5 commits ahead of `main`
`main`: `8ee738b`, the 1.1.1 release (tag `v1.1.1`, GitHub Release "Parametric Road 1.1.1")
Head: `06fe861` Note the mesh quality check of the v1 workflow smoke in the handoff
Supersedes: [SESSION_HANDOFF_1009.md](./SESSION_HANDOFF_1009.md), which stays as the record of the
intersection redesign and the legacy removal up to the release

## 1. What this document is

The starting point for continuing on another PC. It covers the setup (section 2), the state of
the branch (section 3), what is left (section 4), the traps that cost time (section 5), the
validation gate (section 6) and the plan after that (section 7). It does not repeat the code, the
git history or `AGENTS.md`; read `AGENTS.md` first, as always.

Order on the new PC: section 2, then the gate of section 6 to prove the checkout, then section 4.

## 2. Setting up the other PC

### Get the branch

The branch is pushed; `git status -sb` showed `## ganada_0902...origin/ganada_0902` with nothing
ahead. The workbench must sit in FreeCAD's user `Mod` folder under the name `CorridorRoad`:

```powershell
cd "$env:APPDATA\FreeCAD\v1-1\Mod"
git clone https://github.com/ganadara135/CorridorRoad.git CorridorRoad
cd CorridorRoad
git config core.autocrlf true
git checkout ganada_0902
```

If the folder already exists: `git fetch origin`, `git checkout ganada_0902`,
`git pull --ff-only`. Check that `git log --oneline -1` shows `06fe861` (or a later commit
pushed after this document).

Set `core.autocrlf` to `true` before the checkout, as on the first PC. Another setting rewrites
the line endings of the working tree and every later diff becomes noise (section 5.1).

### Environment

- FreeCAD 1.1 at `C:\Program Files\FreeCAD 1.1`. Every Python command, tests and helper scripts
  included, uses `C:\Program Files\FreeCAD 1.1\bin\python.exe` (`AGENTS.md`). If FreeCAD is
  installed elsewhere, adjust `scripts\freecad_environment.ps1`.
- Development tools, once:
  `& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pip install -r requirements-dev.txt`
  (flake8 and pytest).
- Run `scripts\check_freecad_environment.ps1`, then the gate of section 6. Matching numbers mean
  the checkout is complete.
- Start FreeCAD, choose the Parametric Road workbench and check the Report view for Python errors.

### What does not travel

- **Helper scripts.** The scratch scripts of the first PC are not in the repository. Section 5.7
  lists what they did, so they can be rebuilt when needed.
- **Test documents.** FCStd files from the GUI checks are not committed. Make new ones from the
  presets. A roundabout document from before R7c-3 (section 4.1) is made by checking out
  `fdc36d0`, creating the roundabout preset, saving, and returning to `ganada_0902`.
- **Claude Code memory and sessions** are per PC. This document, `AGENTS.md` and the docsV1
  plans carry what is needed.

## 3. State of the branch

### Released as 1.1.1 (`main`, `8ee738b`)

- The intersection redesign (R1 to R7c-3): one parametric kernel for every intersection. See
  [V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md](./V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md).
- Project Setup v1: `v1/commands/cmd_project_setup.py`, `v1/ui/editors/project_setup_editor.py`,
  `v1/services/editing/project_setup_service.py`, `v1/objects/project_setup_adapter.py`. The v0
  bug where a locked coordinate workflow blocked Apply is fixed.
- Legacy removal: all 18 legacy proxy modules are deleted; `virtual_paths._PROXY_OBJECT_MODULES`
  is `("obj_project",)`. Retired command ids are listed in
  `tests/contracts/v1/test_legacy_command_retirement.py`. The design and its decisions are in
  [V1_LEGACY_PROXY_MIGRATION_DESIGN.md](./V1_LEGACY_PROXY_MIGRATION_DESIGN.md) and
  [V1_LEGACY_COMMAND_RETIREMENT_BOUNDARY.md](./V1_LEGACY_COMMAND_RETIREMENT_BOUNDARY.md).
- Roundabout circulation fixed to counterclockwise (`constants.ROUNDABOUT_CIRCULATION = "ccw"`);
  the panel no longer offers the choice. KDS and AASHTO are both right-hand traffic.

### On `ganada_0902` only (CHANGELOG `[Unreleased]`)

| Commit | Change |
| --- | --- |
| `4eadf11` | Hidden `CorridorRoad_NewProject` and `CorridorRoad_CreateAlignment` unregistered; `create_corridorroad_project` now lives in `v1/commands/cmd_project_setup.py` |
| `41c3f30` | `tests/regression/smoke_v1_workflow.py` added to the short-term runner |
| `6b82e04` | v0 tree schema, legacy link properties and the `DesignCriteria` migration removed from `obj_project.py` |
| `dbd32e6` | Corridor surface strips no longer build zero-area triangles (the "mesh data structure has some defects" warning at document open) |
| `06fe861` | Handoff note |

Decision already taken: **documents made with v0 need no consideration.** Do not add migration
or fallback code for v0 files.

### What is left of the legacy tree

- `objects/`: `obj_project.py` (project root and v1 tree folders), `csv_alignment_import`,
  `sketch_alignment_import`, `surface_sampling_core`, `project_links`, `design_standards`,
  `unit_policy`.
- `commands/`: the bridges `cmd_generate_corridor`, `cmd_view_cross_section`,
  `cmd_review_plan_profile`, `cmd_generate_cut_fill_calc`, `cmd_project_setup` (each calls its v1
  command and reports failure; there is no v0 fallback), plus `cmd_outputs_exchange` and
  `cmd_ai_assist` (section 4.2).
- `ui/`: only `__init__` and `common/__init__`.

## 4. What is left

### 4.1 FreeCAD GUI checks (the open 1.1.1 smoke QA)

Headless tests do not cover these. Procedures are in
[V1_UNRELEASED_CHANGES_MANUAL_QA.md](./V1_UNRELEASED_CHANGES_MANUAL_QA.md) and
[V1_INTERSECTION_MANUAL_QA.md](./V1_INTERSECTION_MANUAL_QA.md).

1. Structure Output and the Review TIN buttons.
2. Rebuilding a roundabout document saved before R7c-3 (see section 2 for making one).
3. Drainage low point and Suggested Inlet.
4. New since the release: open a saved document with corridor surfaces and confirm the Report
   view no longer shows "The mesh data structure has some defects".
5. New since the release: `New/Project Setup` on an empty document creates the project root
   (the hidden New Project command is gone).

### 4.2 Decisions to take

- **Outputs/Exchange** (`commands/cmd_outputs_exchange.py`) and **AI Assist**
  (`commands/cmd_ai_assist.py`) are still legacy commands. Decide whether each moves to v1
  (Source -> Evaluation -> Result -> Output layering) or stays as is. Inspect callers and output
  contracts before moving anything.

### 4.3 Small follow-ups

- **Surface facet orientation.** Every real corridor surface triangle faces down. It is
  consistent, so the mesh is valid, but shading or any consumer using normals (export, slope
  analysis) may expect up. Check consumers before flipping the winding in
  `v1/services/builders/corridor_surface_geometry_service.py`; flipping changes exported data.
- **Cross Section viewer** (`v1/commands/cmd_view_sections.py`, around line 1679) still reads
  `project.Corridor` and `project.CutFillCalc` through
  `getattr`. Those properties are no longer created, so the reads always miss. A small v1-side
  legacy trace to remove.
- **Watertight** reads `DesignTerrain`. Watertight is paused; leave it.

### 4.4 Release and communication

- GitHub Wiki: the user will update it separately, in one pass. Do not edit the wiki drafts for
  it unless asked.
- 1.1.1 forum announcement: optional.
- The `[Unreleased]` changes reach `main` with the next release (section 7).

## 5. Traps

### 5.1 Line endings

The repository mixes CRLF and LF files (`docsV1/README.md` even mixes both in one file). A
whole-file rewrite normalizes the endings and turns a three-line change into hundreds. After every
edit compare:

```powershell
git diff --numstat
git diff --numstat --ignore-cr-at-eol
```

If the numbers differ, restore the original endings line by line (difflib against
`git cat-file --filters HEAD:<path>`) or edit with a tool that keeps them. When a script writes a
file, read with `newline=""` and write the same ending the file used.

### 5.2 The gate and edits

Do not edit files while a gate run is in the background; the result mixes two states. Rerun the
gate cleanly after the last edit.

### 5.3 Dead-code searches

A pattern like `objects\.obj_x` also matches `v1.objects.obj_x`. This once retired a v1 smoke by
mistake. Anchor on `freecad\.Corridor_Road\.objects\.` or check every hit by hand.

### 5.4 Names v1 still depends on

- The `FinishedGradeFG` name prefix in `obj_project.py` is used by the v1 profile preview.
- `_looks_like_horizontal_alignment` stays: v1 alignments carry `IPPoints`.
- `V1_LEGACY_TREE_LABELS` maps old folder labels for v1 documents.
- `virtual_paths._PROXY_OBJECT_MODULES` must list every module that still defines a proxy class
  stored in documents. A missing module makes the proxy `None` on restore, and one save makes the
  loss permanent. `test_proxy_module_preload.py` checks it.

### 5.5 Routing changes

Any change to tree routing in `obj_project.py` (`resolve_v1_target_container`,
`_resolve_target_container`, `adopt`) should be proven by recording every routing decision of the
contract suite before and after; both obj_project cleanups did this (456 and 459 decisions,
identical). `smoke_v1_workflow.py` and `smoke_tree_schema.py` check the folders end to end.

### 5.6 Shell escaping

Heredocs and inline `-c` scripts broke Python edits several times, and a substitution helper
turned `\n` arguments into literal text in a handoff. Write the edit script to a file and run it.

### 5.7 Helper scripts to rebuild if needed

All were in the first PC's temporary folder:

- reachability of legacy modules from registered commands, and lazy-import checks
- block and definition removal with uniqueness asserts (fail if a block is not found exactly once)
- the line-ending restorer of section 5.1
- the routing recorder of section 5.5 (a pytest plugin wrapping the three routing functions and
  writing each decision to a file)
- a filter for the regression runner lists

### 5.8 Scope rules

CI is frozen (keep the release guard). Ramp is out of scope. Watertight is paused. Applied
Sections and supplemental station rows are results, never source. Viewers do not edit geometry.

## 6. Validation gate

```powershell
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m flake8 <touched files>
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pytest tests\architecture -q
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pytest tests\contracts -q
.\tests\regression\run_short_term_smokes.ps1
.\tests\regression\run_practical_scope_smokes.ps1
.\tests\regression\run_loft_retirement_gate_smokes.ps1
```

Expected at `06fe861`: **1,142 passed / 18 skipped / 0 failed** contract and architecture tests
together (about 6.5 minutes), and all three runners PASS. The runners hold:

- short-term: `smoke_v1_workflow.py` (the end-to-end gate: tree folders, surface facets, manifold
  meshes without zero-area facets, save, reopen and rebuild) and `smoke_tree_schema.py`
- practical scope: the two intersection kernel smokes
- loft retirement gate: `smoke_corridor_command_alias_boundary.py` and `smoke_tree_schema.py`

Run the smallest relevant test first. The gate is headless; never claim GUI validation from it.

## 7. Plan

1. Finish the GUI checks of section 4.1 and record the results in the manual QA documents.
2. Decide Outputs/Exchange and AI Assist (section 4.2). If they move to v1, write a short design
   note first, as was done for the legacy proxies, then move one command per commit.
3. Remove the Cross Section viewer's `Corridor`/`CutFillCalc` reads; look at facet orientation.
4. Next release (1.1.2 or 1.2.0, depending on what lands): follow
   [V1_RELEASE_CURRENT_PREP.md](./V1_RELEASE_CURRENT_PREP.md). Bump `package.xml` version and
   date, move `[Unreleased]` in CHANGELOG to the new version, update README, ADDON_OVERVIEW,
   AGENTS and the status documents, fast-forward `main`, tag (annotated), push, and check that the
   release guard passes before publishing the GitHub Release.
5. GitHub Wiki, by the user, in one pass.
