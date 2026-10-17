# V1 Session Handoff

Date: 2026-10-17
Branch: `ganada_0902`
Head: the commit that adds this document (the one after `1e0d700`)
Supersedes: [SESSION_HANDOFF_1014.md](./SESSION_HANDOFF_1014.md), which stays as the record up to
`e8532e5`. Its traps still hold; section 5 repeats the ones that matter and adds the new ones.

## 1. What this document is

The starting point for continuing on another PC. Read `AGENTS.md` first, as always. Then section 2
(setup), the gate of section 6 to prove the checkout, then section 4 (what is next).

Two plans were finished since the last handoff, both checked in the FreeCAD GUI by the user:

- [V1_GENERAL_ROAD_WORKFLOW_IMPROVEMENT_PLAN.md](./V1_GENERAL_ROAD_WORKFLOW_IMPROVEMENT_PLAN.md)
  (GR-1 to GR-8): one source per road, Document Kind, result freshness and Rebuild Downstream,
  the stored 3D Centerline as frame owner, Surface Transitions in Regions, one Applied Sections
  path, Build Parametric split, and continuous station frames.
- [V1_DRAINAGE_REWORK_PLAN.md](./V1_DRAINAGE_REWORK_PLAN.md) (DR-1 to DR-5): Drainage rebuilt from
  scratch. The current model is [V1_DRAINAGE_MODEL.md](./V1_DRAINAGE_MODEL.md).

## 2. Setting up the other PC

### Get the branch

The workbench must sit in FreeCAD's user `Mod` folder under the name `CorridorRoad`.

New checkout:

```powershell
cd "$env:APPDATA\FreeCAD\v1-1\Mod"
git clone https://github.com/ganadara135/CorridorRoad.git CorridorRoad
cd CorridorRoad
git config core.autocrlf true
git checkout ganada_0902
```

Existing folder:

```powershell
cd "$env:APPDATA\FreeCAD\v1-1\Mod\CorridorRoad"
git fetch origin
git checkout ganada_0902
git pull --ff-only
```

Check that `git log --oneline -1` shows the commit that adds this document (or later). If it
shows `e8532e5` or an earlier one, the first PC has not pushed yet: run `git push` on
`ganada_0902` there first.

### Environment

- FreeCAD 1.1 at `C:\Program Files\FreeCAD 1.1`. Every Python command (tests, flake8, pyflakes,
  helper scripts) uses `C:\Program Files\FreeCAD 1.1\bin\python.exe`. Never `python`, `py` or a
  venv.
- Development tools, once:
  `& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pip install -r requirements-dev.txt`
- Run `scripts\check_freecad_environment.ps1`, then the gate of section 6.
- Start FreeCAD, choose the Parametric Road workbench and check the Report view for Python errors.

### What does not travel

- Helper scripts of the first PC (section 5.6 lists what to rebuild).
- Test documents (FCStd). Make new ones from the presets.
- Claude Code memory and sessions are per PC.

### Documents from before this branch state

No migration was written (standing decision). On this branch:

- A Drainage object from before 2026-10-16 opens **empty**; its Elements, Policies and Flow Routes
  do not carry over.
- Documents with Ramp or Override data drop those properties on the next write.
- Results built before freshness was recorded read as stale until Rebuild Downstream runs once.
- A Drainage source applied before the 2026-10-17 fix may hold Ditch Run ends rounded to 3
  decimals. Run **Fill from Assembly**, Apply and Rebuild Downstream once.

## 3. State of the branch

`ganada_0902` is ahead of `origin/ganada_0902` by the 23 commits below plus this document; push
them before switching PCs. All changes are under CHANGELOG `[Unreleased]`.

### General road plan (GR)

| Commit | Change |
| --- | --- |
| `2af2b9f` | The general road workflow improvement plan |
| `858db7a` | One source object per road (Profile, Region, Stationing, Superelevation by `AlignmentId`; Drainage per project) |
| `23f0afa` | Document Kind: General Road or Intersection (`project_setup_service`, `objects/document_kind.py`) |
| `69e2199` | Ramp and Override removed; Watertight Solids off the toolbar and menu |
| `99f2727` | Result freshness (`objects/stage_inputs.py`, `result_freshness_service.py`, `objects/result_freshness.py`) and Rebuild Downstream (`cmd_rebuild_downstream.py`) |
| `8b55d52` | The stored 3D Centerline owns the station frames; Applied Sections refuse a missing or stale one |
| `cc8ae78` | Surface Transitions authored in Regions; the unset document kind removed |
| `c9fddab` | One Applied Sections build path for every document |
| `c813dd1`, `cf17ea6`, `b443e8c`, `c77beec`, `e5feaa3` | Build Parametric split: shared breaklines to a service, Guided Review, Region review and intersection summary rows to presentation |
| `6266fbd` | Station frames turn continuously through sampled Alignment elements; the rounded last station resolves |
| `6bb6745`, `a0c86c9`, `ac9035f` | Workflow smoke with terrain, superelevation, 3D Centerline and Rebuild Downstream; plan records |

### Drainage rework (DR)

| Commit | Change |
| --- | --- |
| `69db7b2` | The Drainage rework plan |
| `a5ae5be` | DR-1: Policy and Ditch Runs, prefill from Regions and Assembly, ditch points tagged by their own ditch and side; the old Drainage removed (about 13,000 lines) |
| `ef5e476` | DR-2: flowline evaluation, `DrainageResult` on `V1DrainageResult`, freshness stage `drainage` |
| `7dbb810` | DR-3: points, low point and inlet spacing checks, suggestions |
| `dbfb466` | DR-4: links and their checks, Link Downhill; Watertight and Simulation Drainage handoff removed |
| `1e0d700` | DR-5: Drainage Review, `DrainageOutput`, Build Parametric Drainage line; GUI review fixes (exact stations in the panel tables, reverse-flow check by draining length, highlight above the flowline, panel and review open each other, Rebuild Downstream window with a progress bar, resizable Cross Section viewer columns) |

### Rules that came out of this work

- **Result stages.** A result records its consumed inputs with `record_stage_inputs(obj, inputs,
  options)`. Its freshness row lives in `objects/result_freshness.py`, and its stage, upstream
  stage and label in `result_freshness_service.py`. Rebuild Downstream gets a rebuilder in
  `_REBUILDERS`. Order:
  `stationing -> centerline3d -> applied_sections -> drainage / build_parametric`.
- **Applied Sections read only what they use.** From the Drainage source they record only the
  Ditch Runs (`drainage_ditch_runs`), so Policy, point and link edits leave them current.
- **Station frames** come from the stored `Centerline3DResult` only; there is no fallback.
- **One source per road** for Profile, Region, Stationing and Superelevation; one Drainage per
  project. Writers update the existing object.
- **Panel tables showing stations** keep the exact value behind the shown text (`_station_item` /
  `_station` in `ui/editors/drainage_editor.py`). Reuse that pattern; never write back rounded
  text.
- **Drainage owns no geometry.** Flow direction, grades, low points and elevations are evaluated;
  suggestions become source points only through the panel.
- **Panels and commands.** UI modules never import commands; a command injects its functions with
  `configure_*_runtime(...)`. The Build Parametric view takes `name = None` placeholders that
  `cmd_build_corridor` globals fill in (`test_build_corridor_runtime_bindings.py` guards this).
  Commands do not import private (`_`) names from services.

## 4. What is next

### 4.1 Structure rebuild

The next agreed step. Structure will be rebuilt from scratch, as Drainage was. Pipes, manholes
and Structure ports wait for it: Drainage Links are checked lines until then. Start the same way:

1. Review the current Structure code (`models/source/structure_model.py`, `obj_structure.py`,
   `cmd_structure_editor.py`, `structure_interaction_service.py`, Structure Output) and list
   defects and removal candidates.
2. Agree the approach with the user, write `V1_STRUCTURE_REWORK_PLAN.md` with phases, and go
   phase by phase. After each phase: the gate, then the user's GUI check, then a commit.

Decide early, with the user, how Drainage Links become pipes between Structure ports.

### 4.2 Recorded leftovers

- Overlap clipping stacks points into a vertical face where section lines still cross (GR-8; the
  Daylight strip join is the place to fix it).
- The sample Alignment's three-point "curve" is not tangent to its straights, so its frames jump
  at both ends (demo data).
- A station past the Profile's end falls back to coarse 3D Centerline interpolation.
- Drainage Review does not show the intersection kernel's low points.
- `test_v1_alignment_editor.py` crashes when run alone but passes in the full suite (from 1014).
- Outputs/Exchange and AI Assist are still legacy commands; decide whether they move to v1 (from
  1014).

### 4.3 Release

The `[Unreleased]` changes reach `main` with the next release; follow
[V1_RELEASE_CURRENT_PREP.md](./V1_RELEASE_CURRENT_PREP.md). The GitHub Wiki is updated by the
user in one pass; `docsV1/wiki/Drainage.md` is rewritten for the new Drainage.

## 5. Traps

### 5.1 Line endings

The repository mixes CRLF and LF files, and `core.autocrlf` is `true`. After every edit compare:

```powershell
git diff --numstat
git diff --numstat --ignore-cr-at-eol
```

If the numbers differ, restore the original endings line by line (difflib against
`git cat-file --filters HEAD:<path>`). When a script edits a file, read it with `newline=""`,
normalize to `\n`, and write the file's own ending back.

A file whose committed blob has CRLF lines (for example `docsV1/README.md`) is normalized by
`autocrlf` on commit, and the whole file shows as changed. Stage and commit it with
`git -c core.autocrlf=false add <file>` and `git -c core.autocrlf=false commit`. Check the
committed result with `git diff --numstat HEAD~1 HEAD` against `--ignore-cr-at-eol`.

### 5.2 Shell escaping

Heredocs with nested quotes broke Python edits several times. Write edit scripts to the
scratchpad and run them. Never put `cat > file` without a heredoc in a command: it waits on stdin.

### 5.3 Gate and edits

Do not edit files while a gate run is in the background; rerun cleanly after the last edit.

### 5.4 Offscreen Qt

Panel tests run headless with a `QApplication`. A panel that opens a modal message box hangs a
probe: patch it, or use the panel's status text as the panels here do.

### 5.5 Commits

Messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Add a CHANGELOG
`[Unreleased]` line for each user-visible change. The user's pattern is: report a phase, wait for
"GUI 확인 완료, ... 커밋하고 ... 진행해", then commit.

### 5.6 Helper scripts to rebuild if needed

- line-ending restorer (section 5.1)
- `edlib.py`: `edit(path, [(old, new), ...], cut=..., cut_to=..., insert=...)` with unique-match
  asserts and line-ending preservation
- `drop_functions.py FILE NAME...`: remove top-level functions by name
- `callers.py FILE --re PATTERN`: which top-level functions reference which
- `deps.py`: AST dependency closure of top-level functions
- Drainage probe: build the workflow smoke document (`smoke_v1_workflow._build`) and print
  `drainage_result_summary` and the suggestions

## 6. Validation gate

```powershell
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pytest tests\architecture tests\contracts -q -p no:cacheprovider
.\tests\regression\run_short_term_smokes.ps1
.\tests\regression\run_practical_scope_smokes.ps1
.\tests\regression\run_loft_retirement_gate_smokes.ps1
```

Run from the repository root (in PowerShell, `Set-Location` there first). Expected at this
document's commit: **1,137 passed / 14 skipped / 0 failed** (about 6 minutes), and all three
runners PASS. `smoke_v1_workflow.py` now covers terrain daylight, superelevation, the 3D
Centerline, Drainage (runs, accepted suggestions, downhill links) and Rebuild Downstream. Run the
smallest relevant test first. The gate is headless; never claim GUI validation from it.

## 7. Plan

1. Push `ganada_0902` from the first PC; pull on the other (section 2).
2. Run the gate there.
3. Structure rebuild (section 4.1).
4. Leftovers of section 4.2 when they block or when the user asks.
5. Next release (section 4.3).
