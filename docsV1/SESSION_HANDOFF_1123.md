# V1 Session Handoff

Date: 2026-11-23
Branch: `ganada_0902`
Head: the commit that adds this document (the one after `33a89a0`)
Supersedes: [SESSION_HANDOFF_1017.md](./SESSION_HANDOFF_1017.md), which stays as the record of the
general road plan and the Drainage rework. Its section 4.2 leftovers are resolved here except
Outputs/Exchange and AI Assist.

## 1. What this document is

The starting point for continuing on another PC, with any AI agent or by hand. Read in this order:

1. `AGENTS.md`, completely. It holds the architecture and the binding project rules.
2. Section 2 (setup), then the gate of section 7 to prove the checkout.
3. Section 3 (state), section 5 (what is next), section 6 (traps).

Current product scope is in [V1_SUPPORTED_DOMAIN_STATUS.md](./V1_SUPPORTED_DOMAIN_STATUS.md), the
active architecture plan in
[V1_PROJECT_ARCHITECTURE_IMPROVEMENT_IMPLEMENTATION_PLAN.md](./V1_PROJECT_ARCHITECTURE_IMPROVEMENT_IMPLEMENTATION_PLAN.md).

### How the user works

- The user writes in Korean. Reply in Korean. Repository documents and commit messages are English.
- Report the result, then wait. Commit only when the user says so ("커밋해", or "작업 트리 변경 사항을
  적절한 메시지와 함께 커밋하세요."). Never push unless the user asks.
- For anything visible in FreeCAD, the user checks the GUI before asking for the commit.
- "남은 작업 알려줘" means: list what is left, numbered. The user then picks by number
  ("8번 하자"), so keep the numbering of the most recent list.

## 2. Setting up the other PC

### Get the branch

**The first PC must push first.** `origin/ganada_0902` is still at `0839a79`; the 15 commits of
section 3 and this document exist only on the first PC until then:

```powershell
git push origin ganada_0902
```

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

Check that `docsV1/SESSION_HANDOFF_1123.md` exists and `git log --oneline -2` shows `33a89a0`
directly under the commit that adds it (or later work). If the head is `0839a79`, the first PC has
not pushed.

### Environment

- FreeCAD 1.1 at `C:\Program Files\FreeCAD 1.1`. Every Python command (tests, flake8, helper
  scripts, pip) uses `C:\Program Files\FreeCAD 1.1\bin\python.exe`. Never `python`, `py` or a venv.
- Development tools, once:
  `& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pip install -r requirements-dev.txt`
- Run `scripts\check_freecad_environment.ps1`, then the gate of section 7. It stops if more than one
  `CorridorRoad` or `Corridor-Road` workbench is under the active `Mod` folder.
- Start FreeCAD, choose the Parametric Road workbench and check the Report view for Python errors.

### What does not travel

- Helper scripts of the first PC (section 6.2 shows how to rebuild them).
- Test documents (FCStd). Make new ones from the presets.
- Claude Code memory, sessions and `.claude/worktrees` are per PC and ignored by git. Other agents
  have only this document and the repository.

### Documents from before this branch state

No migration was written (standing decision). The notes in section 2 of
[SESSION_HANDOFF_1017.md](./SESSION_HANDOFF_1017.md) still apply to old Drainage, Ramp and Override
data. After this session, rebuild old documents with **Rebuild Downstream** so the curve sampling
and clipping fixes below reach their results.

## 3. State of the branch

- Public release: `1.1.2`, tag `v1.1.2` at `2d033ef`. `main` and `origin/main` are at `0839a79`.
- `ganada_0902` is ahead of `origin/ganada_0902` by the 15 commits below plus this document.
- User-visible changes are under CHANGELOG `[Unreleased]` and reach `main` with the next release.

### Product fixes

| Commit | Change | GUI checked by user |
| --- | --- | --- |
| `8dcf3ef` | Intersection low points on the Drainage Review tab | **not yet** |
| `1c8a3c2` | Sample Alignment curve is tangent to its straights | **not yet** |
| `e84b395` | Stations past the Profile keep their plan frame: held elevation, grade 0, status warning, source mode `alignment_profile_fallback`, diagnostic `profile_station_out_of_range` (`centerline3d_source_geometry_service.py`) | yes |
| `03e6b99` | Overlap clipping no longer folds the Daylight surface (`applied_section_service.py`: `_nearest_crossing_sections`, `_section_elevation_at_clip`; `corridor_surface_geometry_service.py`: `_strip_triangle_faces_up`) | yes |
| `c69991b` | Compiled PI curves stay within 1 cm of the true curve (`cmd_alignment_editor.py`: `MAX_CURVE_CHORD_ERROR_M`, `MAX_CURVE_CHORDS_PER_PART`, `_chord_steps_for_curve`) | yes |

### Documents and test maintenance

| Commit | Change |
| --- | --- |
| `f8dd6a6` | 1.1.2 smoke QA and Wiki update marked complete |
| `f3ef6d0` | Superseded and completed documents removed from `docsV1` |
| `52fe313` | Alignment and Plan/Profile tests run alone |
| `cbadfab` | Fast validation tier repaired, empty test files dropped |
| `9fb1f2a` | `__main__` blocks removed from 60 contract tests |
| `e778d3e` | flake8 findings cleared, so the Lint tier passes (25 files) |
| `b639442` | The three unit-policy smokes joined the short-term regression set |
| `6a947c0` | 15 sample CSVs no feature can read removed (8 Structure, 7 Typical Section) |
| `a299042`, `33a89a0` | One QApplication helper: `ensure_qapp` in `tests/qt_app_support.py` |

### Rules that came out of this work

- Qt tests call `ensure_qapp()` from `qt_app_support`. pytest puts `tests/` on `sys.path` through
  `tests/conftest.py`. Regression smokes run under FreeCAD without pytest, so they cannot rely on
  this and keep their own setup (`smoke_project_setup_unit_policy.py`).
- `tests/conftest.py` stubs modal `QMessageBox` calls for every test.
- Kept samples without a code reference are manual-check inputs for live importers:
  `alignment_utm_realistic_hilly.csv`, `profile_fg_manual_import_aliases.csv`,
  `profile_fg_manual_import_basic.csv`. Do not delete them as unused.
- There is no Structure CSV importer and no Typical Section CSV importer.

## 4. Known limits of the fixes above

- **Clipped slopes.** On the inside of a tight curve, a clipped side slope ends at the clip point
  and does not reach the ground. The Daylight outer boundary can keep a notch there.
- **Stations past the Profile** use a held elevation by design and report a warning. They are not
  a designed grade.
- **Stations outside the Alignment** are still held at the end point with a warning. Whether to
  block them is an open decision (section 5, item 6).

## 5. What is next

The numbering matches the last list given to the user.

### Check and release

1. **FreeCAD GUI check:** the intersection low points on the Drainage Review tab, and the sample
   Alignment curve. Both have passed headless tests only.
2. **Push** the 15 commits and this document (section 2).
3. **Wiki sync:** `docsV1/wiki/Developer-Guide.md` lost three links to deleted documents and that
   edit had not reached the GitHub Wiki when last checked. The Wiki's Menu Reference also needs an
   update. The Wiki is a separate repository whose branch is `master`.
4. **Forum announcement** of 1.1.2. This is outward-facing: only the user decides when and what.

### Defects and decisions

5. **Clipped slope tie-in to the ground** (section 4). The next recommended code task, because it
   affects real surface quality. Start from `_section_elevation_at_clip` and the Daylight strip
   join in `corridor_surface_geometry_service.py`.
6. **Stations outside the Alignment:** keep the held fallback with a warning, or block. The user
   decides.
7. **`V1_LEGACY_PROXY_MIGRATION_DESIGN.md`** points to `tests/legacy_proxy_corpus.py` and
   `tests/samples/legacy_proxy_corpus/`, and neither exists. Check the history and correct the
   document.

### Tests

8. **Split the large test files.** On hold; do not start without the user.

### Larger feature work (each needs the user's agreement first)

9. **Structure rebuild,** from scratch as Drainage was. Review the current code
   (`models/source/structure_model.py`, `obj_structure.py`, `cmd_structure_editor.py`,
   `structure_interaction_service.py`, Structure Output), list defects and removal candidates,
   agree the approach, write `V1_STRUCTURE_REWORK_PLAN.md`, then go phase by phase. Decide early
   how Drainage Links relate to Structure ports.
10. **Outputs/Exchange and AI Assist** are still legacy commands. Decide whether they move to v1.
11. **Q4 pipe volumes:** excluded by the user for now.

Recommended order: 1, 2, then 5.

## 6. Traps

### 6.1 Line endings

The repository mixes CRLF and LF, and `core.autocrlf` is `true`. Some editors and agent edit tools
normalize a whole file. After every edit compare:

```powershell
git diff --numstat
git diff --numstat --ignore-cr-at-eol
```

If the numbers differ, restore the original endings line by line. A file whose committed blob has
CRLF lines (for example `docsV1/README.md`) can show as fully changed after commit. Stage and
commit it with `git -c core.autocrlf=false add <file>` and `git -c core.autocrlf=false commit`,
then check `git diff --numstat HEAD~1 HEAD` against `--ignore-cr-at-eol`.

### 6.2 Helper scripts to rebuild

Keep them outside the repository.

- **Block edit:** read bytes, build a regex from the old block with `\r?\n` between its lines,
  assert exactly one match, and write the new block using the line ending the match had.
- **Line-ending restore:** run `difflib.SequenceMatcher` between `git show HEAD:<path>` and the
  file, comparing lines without `\r`. For equal lines, put back the ending from HEAD.

### 6.3 Scripts and shell

- Heredocs with nested quotes broke Python edits. Write the script to a file and run it.
- **Use a new script name each time, or read the old file first.** On 2026-11-22 a failed write
  left an older `qapp_fix.py` in place, the command ran it anyway, and it edited a test file. Check
  that the write succeeded before running.
- PowerShell 5.1 has no `&&`. Call FreeCAD Python with `&` because the path has spaces.

### 6.4 Validation

- Do not edit files while a gate run is in the background; rerun after the last edit.
- The whole gate can exceed 10 minutes, so run it in the background or in parts.
- Lint covers both `freecad` and `tests`. Checking only `tests` under-reports it.
- Headless tests are not GUI validation. Never claim a GUI check the user has not made.

### 6.5 Architecture and scope

- UI modules never import commands. A command injects its functions with `configure_*_runtime(...)`.
- Ramp is removed. Watertight Solid is paused. CI is frozen except the release guard.

### 6.6 Commits

End messages with the co-author line the current tool requires; this session used
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Add a CHANGELOG `[Unreleased]` line for
each user-visible change.

## 7. Validation gate

Run from the repository root:

```powershell
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pytest tests\architecture tests\contracts -q -p no:cacheprovider
```

```powershell
.\tests\regression\run_short_term_smokes.ps1
```

```powershell
.\tests\regression\run_practical_scope_smokes.ps1
```

```powershell
.\tests\regression\run_loft_retirement_gate_smokes.ps1
```

Expected at `33a89a0`: **1,219 passed / 11 skipped / 0 failed** (about 6 minutes), and all three
runners PASS. The 11 skips are the paused Watertight tests.

Local tiers are also available:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_local_validation.ps1 -Tier Fast
```

The tiers are `Compile`, `Lint`, `Architecture`, `Fast`, `Contracts`, `ContractsFull`, `Smokes` and
`Full`. Run the smallest relevant test first.

## 8. Plan

1. Push `ganada_0902` from the first PC and pull on the other (section 2).
2. Run the gate there.
3. Ask the user to make the two open GUI checks (section 5, item 1).
4. Continue with what the user picks. The recommended code task is item 5.
