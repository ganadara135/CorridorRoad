# V1 Session Handoff

Date: 2026-10-14
Branch: `ganada_0902`, ahead of `main` by the commits listed in section 3
`main`: `8ee738b`, the 1.1.1 release (tag `v1.1.1`, GitHub Release "Parametric Road 1.1.1")
Head: the commit that adds this document (the one after `5782d0c`)
Supersedes: [SESSION_HANDOFF_1011.md](./SESSION_HANDOFF_1011.md), which stays as the record up to
`06fe861`. Its traps (section 5) still hold; this document repeats the ones that matter.

## 1. What this document is

The starting point for continuing on another PC. Read `AGENTS.md` first, as always. Then:
section 2 (setup), the gate of section 6 to prove the checkout, then section 4 (what is left).

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

Check that `git log --oneline -1` shows the commit that adds this document (or later). If it shows
`06fe861` or `5782d0c`, the first PC has not pushed yet: push there first (`git push` on
`ganada_0902`).

Set `core.autocrlf` to `true` before the checkout. Another setting rewrites the working tree's line
endings and every later diff becomes noise (section 5.1).

### Environment

- FreeCAD 1.1 at `C:\Program Files\FreeCAD 1.1`. Every Python command, tests, flake8 and helper
  scripts included, uses `C:\Program Files\FreeCAD 1.1\bin\python.exe` (`AGENTS.md`). Never
  `python`, `py` or a venv.
- Development tools, once:
  `& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pip install -r requirements-dev.txt`
- Run `scripts\check_freecad_environment.ps1`, then the gate of section 6.
- Start FreeCAD, choose the Parametric Road workbench and check the Report view for Python errors.

### What does not travel

- **Helper scripts** of the first PC (section 5.7 says what they did).
- **Test documents** (FCStd from GUI checks). Make new ones from the presets.
- **Claude Code memory, sessions and task chips** are per PC. A chip for the isolated
  `test_v1_alignment_editor.py` crash (section 4.3) was created on the first PC only.

## 3. State of the branch

### On `ganada_0902` only (CHANGELOG `[Unreleased]`)

Up to `06fe861` (see SESSION_HANDOFF_1011.md section 3): hidden New Project / Create Alignment
commands unregistered, `smoke_v1_workflow.py` in the short-term runner, v0 tree schema removed from
`obj_project.py`, no zero-area corridor surface triangles.

Added on 2026-10-12, all checked in the FreeCAD GUI by the user:

| Commit | Change |
| --- | --- |
| `78bd3c3` | Cross Section viewer no longer reads `project.Corridor` / `project.CutFillCalc`; `_build_earthwork_hint_rows` lost its `cut_fill_calc` argument |
| `8606f57` | Every corridor surface faces up: `_upward_triangle` in `v1/services/builders/corridor_surface_geometry_service.py` winds point-grid and drainage triangles counterclockwise in plan. Test `test_corridor_surface_facet_orientation.py`; `smoke_v1_workflow.py` fails on any downward facet |
| `4299285` | Alignment panel fits the task panel (`_narrow_combo`, `_button_row`, one `source_form`) |
| `7735d16` | Every v1 task panel fits the task panel: new `v1/ui/common/panel_width.py` (`fit_task_panel_width`, `FlowLayout`); 22 panels call it. Test `test_task_panel_width.py` |
| `5782d0c` | Handoff notes for the above |

Decisions already taken: v0 documents need no migration or fallback. Ramp is out of scope,
Watertight is paused, CI is frozen (keep the release guard).

### Rules that came out of this work

- **New task panel**: build the form, then `self.form = fit_task_panel_width(self._build_ui())`
  (import from `freecad.Corridor_Road.v1.ui.common.panel_width`). A row of buttons is a
  `QHBoxLayout`, not a `QGridLayout`; grid rows are not wrapped. A row wraps when it is wider than
  44 average characters of the panel font (`TASK_PANEL_ROW_CHARACTERS`).
- **New surface builder**: triangles must be counterclockwise in plan (XY signed area > 0), so the
  normal points up. Reuse `_upward_triangle`.

## 4. What is left

### 4.1 FreeCAD GUI checks (open 1.1.1 smoke QA)

Procedures: [V1_UNRELEASED_CHANGES_MANUAL_QA.md](./V1_UNRELEASED_CHANGES_MANUAL_QA.md) and
[V1_INTERSECTION_MANUAL_QA.md](./V1_INTERSECTION_MANUAL_QA.md).

1. Structure Output and the Review TIN buttons.
2. Rebuilding a roundabout document saved before R7c-3 (make one by checking out `fdc36d0`,
   creating the roundabout preset, saving, and returning to `ganada_0902`).
3. Drainage low point and Suggested Inlet.
4. A saved document with corridor surfaces opens without "The mesh data structure has some
   defects".
5. `New/Project Setup` on an empty document creates the project root.

Already checked by the user: Cross Section viewer, surface shading (light on top, also after
Build Parametric), every task panel's right-hand buttons visible.

### 4.2 Decision to take

**Outputs/Exchange** (`commands/cmd_outputs_exchange.py`) and **AI Assist**
(`commands/cmd_ai_assist.py`) are still legacy commands. Decide whether each moves to v1 (Source ->
Evaluation -> Result -> Output layering) or stays. Inspect callers and output contracts first; if
they move, write a short design note, then one command per commit.

### 4.3 Small follow-ups

- `tests/contracts/v1/test_v1_alignment_editor.py` crashes when run alone (exit 127 under Git Bash,
  9 under PowerShell); the crash predates the panel changes. It passes inside the full contract suite. Likely
  a missing Qt application or import-order setup in the test; fix the test, not the editor.
- Watertight reads `DesignTerrain`. Watertight is paused; leave it.

### 4.4 Release and communication

- GitHub Wiki: the user updates it separately, in one pass. Do not edit wiki drafts unless asked.
- The `[Unreleased]` changes reach `main` with the next release (section 7).

## 5. Traps

### 5.1 Line endings

The repository mixes CRLF and LF files. Whole-file rewrites (including some editor tools) normalize
endings and turn a three-line change into hundreds. After every edit compare:

```powershell
git diff --numstat
git diff --numstat --ignore-cr-at-eol
```

If the numbers differ, restore the original endings line by line (difflib against
`git cat-file --filters HEAD:<path>`). When a script writes a file, read with `newline=""` and
write the ending the file used.

### 5.2 Gate and edits

Do not edit files while a gate run is in the background. Rerun cleanly after the last edit.

### 5.3 Offscreen Qt measurements

Panel probes run with `QT_QPA_PLATFORM=offscreen`. Fonts there are about 1.8 times larger than in
the GUI, so the wrap limit is about 576 px offscreen. Run each panel in its own process with a
timeout, and patch `QMessageBox` so a modal dialog cannot hang the probe. A command module may
inject its panel's runtime (for example `cmd_alignment_editor` before the Alignment editor), so
import the command first.

### 5.4 Dead-code searches and names v1 still depends on

Anchor patterns on `freecad\.Corridor_Road\.objects\.`; `objects\.obj_x` also matches
`v1.objects.obj_x`. Keep `FinishedGradeFG`, `_looks_like_horizontal_alignment`,
`V1_LEGACY_TREE_LABELS` and every module in `virtual_paths._PROXY_OBJECT_MODULES`
(`test_proxy_module_preload.py`).

### 5.5 Shell escaping

Heredocs and inline `-c` scripts broke Python edits several times. Write the script to a file and
run it.

### 5.6 Commits

Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Add a line
under CHANGELOG `[Unreleased]` for each user-visible fix.

### 5.7 Helper scripts to rebuild if needed

- line-ending restorer (section 5.1)
- facet probe: build the workflow smoke document and count facets with `Normal.z < 0` per surface
- panel probe: open each task panel offscreen, print `form.minimumSizeHint().width()`, the widest
  rows, and controls whose geometry lies outside the form (skip table cell widgets)
- viewer probe: the same for the review viewers, on a document built by `smoke_v1_workflow.py`
- routing recorder for `obj_project.py` routing changes (SESSION_HANDOFF_1011.md section 5.5)

## 6. Validation gate

```powershell
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m flake8 <touched files>
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pytest tests\architecture tests\contracts -q -p no:cacheprovider
.\tests\regression\run_short_term_smokes.ps1
.\tests\regression\run_practical_scope_smokes.ps1
.\tests\regression\run_loft_retirement_gate_smokes.ps1
```

Expected at this document's commit: **1,149 passed / 18 skipped / 0 failed** (about 6.5 minutes),
and all three runners PASS. Run the smallest relevant test first. The gate is headless; never claim
GUI validation from it.

## 7. Plan

1. GUI checks of section 4.1; record the results in the manual QA documents.
2. Decide Outputs/Exchange and AI Assist (section 4.2).
3. Fix the isolated alignment editor test (section 4.3) when convenient.
4. Next release (1.1.2 or 1.2.0): follow [V1_RELEASE_CURRENT_PREP.md](./V1_RELEASE_CURRENT_PREP.md).
   Bump `package.xml` version and date, move `[Unreleased]` in CHANGELOG to the new version, update
   README, ADDON_OVERVIEW, AGENTS and the status documents, fast-forward `main`, tag (annotated),
   push, and check the release guard before publishing the GitHub Release.
5. GitHub Wiki, by the user, in one pass.
