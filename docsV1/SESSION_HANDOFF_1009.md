# V1 Session Handoff

Date: 2026-10-09
Branch: `ganada_0902`, 53 commits ahead of `main` (`1abad47`, the 1.1.0 release)
Head: `6200cea` Label the Intersection source object "Intersection Source"
Work covered: 2026-09-24 to 2026-10-09

## 1. What this document is

A handoff for whoever picks this branch up next. It records the decisions that were taken and
should not be re-litigated, the state of the branch, what is left, and the traps that cost time.
It does not repeat what the code, the git history or `AGENTS.md` already say.

To continue on another PC, start with section 8 (setup), then section 4 (what to do next).

The authoritative specification of intersections is
[V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md](./V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md). Its
section 8 records every phase (R1 to R7c-3) with its measurements and validation. The earlier
intersection plans, including
[V1_INTERSECTION_SCOPE_AND_IMPROVEMENT_PLAN.md](./V1_INTERSECTION_SCOPE_AND_IMPROVEMENT_PLAN.md),
are historical. Where this document and the plan disagree, the plan is right.

## 2. State of the intersection work

Every intersection is built by one parametric kernel,
`services/evaluation/intersection_kernel/`, from an `IntersectionSpec` and the roads' Applied
Sections: `build_intersection_geometry(spec, road_context)`. The legacy pipeline (boundary loops,
edge network, surface zones, tie slope, shared breakline contributions, patch triangulation) is
deleted, with the review of its source rows.

- **Source.** The spec is stored as `SpecJson` on the Intersection object, written when an
  intersection is created from a preset or from existing Alignments and by the panel's Apply
  Spec. Without it the spec is read from the rows (`spec_from_intersection_model`). The edge
  policy and lane connection rows no longer exist (decision D2).
- **Panel.** Preset, Create Sources (or Use Existing Alignments, Apply), then the Parametric Spec
  group: Load, Check (runs the kernel and lists every value with its origin), Apply. The spec's
  kind follows the preset and then the created source.
- **Applied Sections** add a section at every leg mouth; **Build Parametric** clips each road's
  corridor between its mouths and puts the kernel's intersection surface and side slope there.
- **Review.** The Build Parametric Intersections tab, its highlight, the guided review, the
  drainage review (the kernel's low points), the roundabout intrusion check and the cross section
  viewer's intersection rows all read the kernel result.
- **Legacy cleanup** (`275ca65`). The Build Parametric metadata, highlights and Breakline Audit
  rows that only the deleted pipeline produced are gone, with three modules
  (`intersection_shared_boundary_graph_evaluation_service`, `intersection_daylight_tin_service`,
  `models/result/intersection_shared_boundary_graph`). The daylight surface is clipped by the
  kernel's station spans like the other corridor surfaces. Plan, section 8.
- **Label** (`6200cea`). The Intersection source object is labelled `Intersection Source`
  (`INTERSECTION_SOURCE_LABEL` in `objects/obj_intersection.py`). It used to share the label
  `Intersections` with its tree folder, so FreeCAD showed it as `Intersections001`. The object
  name `V1IntersectionModel` and the folder are unchanged.
- **GUI.** The user built the starter T, Cross and roundabout after R7c-1, checked the
  Intersections tab and its highlight after R7c-2, and the tab's `ready` after R7c-3. Nothing
  after `8fbbae0` has been checked in a window.

## 3. Decisions taken

These were settled with the user and are not open questions.

**The redesign decisions D1 to D6** are in section 3 of the redesign plan: Applied Sections own
the pavement edge; the lane connection, edge policy and surface zone rows are removed without
migration; a T is recognised automatically; the radii defaults are constants; the plan is the
single intersection specification.

**The source row review is gone.** Measured before removing it (plan, R7c-3): accepting rows or
adopting edge families changed nothing the kernel builds, neither the geometry nor the Build
Parametric review. Do not bring back approval states as build inputs.

**Watertight Solids stay paused.** Each intersection offers planned, disabled targets for its
pavement with the subgrade under it and for its side slope. Nothing builds them.

**Multiple roads: one road per document.** A separate document per independent route;
`AlignmentModel` for roads that actually meet; `RegionRow` only for policy that varies along one
axis. Written up in
[V1_ROUTE_SEPARATION_AND_REGION_CRITERIA.md](./V1_ROUTE_SEPARATION_AND_REGION_CRITERIA.md). Region
must not absorb Structure, Drainage or Intersection semantics.

**Intersections: T, Cross and Roundabout only.** Reinstating the removed kinds is out of scope.

**`docsV0` is deleted** and lives in git history. The 5-level Document Classification in
`V1_SUPPORTED_DOMAIN_STATUS.md` exists to retain historical plans, not to prune them.

## 4. What is left

### Done on 2026-10-10 (head `8836924`, gate 1,146 passed / 18 skipped, runners PASS)

- `5f33cb2`: the cross section viewer lists intersection rows for every section inside the kernel
  clip span, not only inside the source control area (with the panel's roundabout defaults the clip
  span was STA 74.5-185.5 and the control area STA 111.25-148.75). Checked in FreeCAD.
- `e4db4f5`: Next/Previous find the current row by its Applied Section, so they stay on the current
  road. Checked in FreeCAD.
- `cf80c0d`: Station Navigation lists the primary road's stations first, then the other roads.
- `fbb8ed8`: the Structure Output and Review TIN buttons call runtime-bound commands; their lazy
  imports pointed at modules that do not exist. A contract test now resolves every relative import
  in `ui`.
- `5699e31`: the dead intersection code this handoff listed, found by a reachability pass (section 5).
  `_intersection_trim_pair_rows_from_object` (Watertight, paused) was left in place.
- `7997082`: the Results tab no longer reads the 106 legacy preview properties nothing writes, and
  the kernel surfaces' Output Path reads `contract_consumed` instead of `legacy_output` /
  `inferred_fallback`.
- `4f50ae2`: the geometry modules only the legacy intersection chain used (convex polygon
  clipping, polygon boundary, polygon triangulation) and their tests.
- `aa4c6c9`: 30 private helpers nothing called.
- `8e52a20`: public functions only tests reached. Tests of thin wrappers now call the live function
  they wrapped. Kept because docsV1 names them as contracts: `ProjectModel`, `ContextReviewOutput`,
  `DrainageResolutionService`, `shared_breakline_adjacency_graph`,
  `corridor_build_review_outcome_matrix`, `SurfaceOutputMapper`.
- `8836924`: Project Setup is a v1 panel (service, objects adapter, command, `ui/editors`); the
  command id stays as a bridge and the v0 panel is gone. Apply no longer recomputes the document,
  and the panel keeps the stored Coordinate Workflow (the v0 panel replaced it with the CRS
  recommendation, which blocked every Apply on a locked setup). Record:
  [V1_LEGACY_COMMAND_RETIREMENT_BOUNDARY.md](./V1_LEGACY_COMMAND_RETIREMENT_BOUNDARY.md) section 10.
  Checked in FreeCAD on 2026-10-11.
- `071aa5c`: unused helpers in the legacy `objects` package and `misc/resources`.

### Next steps, in order

1. **GUI checks (user, in FreeCAD).** Procedure in
   [V1_INTERSECTION_MANUAL_QA.md](./V1_INTERSECTION_MANUAL_QA.md); record results in its table.
   Done: `Intersection Source` label, cross section viewer rows (section 6), Next, Station
   Navigation order, Results tab Output Path, Breakline Audit rows, and Project Setup (`8836924`:
   create, apply and reopen, stored workflow kept under the lock, locked field refused, context
   menu, Close writes nothing; checked by the user on 2026-10-11).
   - the Structure Output button (Build Parametric) and Review TIN button (TIN editor), `fbb8ed8`;
   - a roundabout document created before R7c-3 rebuilds the same ring, section 7 step 4;
   - the Drainage tab's low point and `Suggested Inlet` marker, section 5.
2. **Remaining dead code.** The reachability pass lists 29 v1 definitions, all kept on purpose:
   the six documented contracts above, Watertight and simulation code (paused), Ramp (out of
   scope), and `objects/` persistence adapters. `071aa5c` removed the unused v0 helpers; the 34 v0
   definitions left are ViewProvider classes (restored by name from saved documents), the dead
   alignment-tree chain in the frozen `obj_project` (the loft retirement gate checks its source
   text), and four helpers the smoke runners call.

### Open questions for the user

- **Circulation direction** of a roundabout is in the spec (`ccw`/`cw`); there is no project
  setting for it. Whether to add one is undecided.

### Repository-wide

- **Legacy retirement is blocked.** Unreachable v0 modules cannot go until a stored-`Proxy`
  migration exists. See section 5. The options, measurements and the decisions it needs are in
  [V1_LEGACY_PROXY_MIGRATION_DESIGN.md](./V1_LEGACY_PROXY_MIGRATION_DESIGN.md) (`c2377ab`).
- No surfaced workflow stage is driven by a v0 task panel since `8836924`. `cmd_outputs_exchange`
  and `cmd_ai_assist` are still self-contained legacy entry points.
- `main` is still at `1abad47` (1.1.0). Whether to advance it is **undecided** and is the user's
  call.

## 5. Cautions

### Line endings will burn you

Tracked files store **mixed CRLF and LF inside the same file**, and `core.autocrlf` is on. The
`Edit` tool, `Write` and `sed -i` normalise them and produce thousands of spurious diff lines
(`cmd_view_sections.py`, 2,500 lines, in R7c-2). Check every modified file with

```bash
git diff HEAD --numstat -- <file>
git diff HEAD --numstat --ignore-cr-at-eol -- <file>
```

and if the two differ, restore HEAD's per-line endings (match the unchanged lines with `difflib`
and give new lines the ending of the line before them). For a scripted edit, keep each line's own
ending:

```python
text = io.open(path, "r", encoding="utf-8", newline="").read()
lines = text.split("\n")                      # each element keeps its own trailing "\r"
...                                           # splice whole lines, never rewrite the file
updated = "\n".join(lines)
assert updated.endswith("\n") == text.endswith("\n")   # the trailing-newline guard
io.open(path, "w", encoding="utf-8", newline="").write(updated)
```

### Finding dead code

Name searches misattribute across v0 and v1 and across same-named helpers. What worked in R7c-2
and R7c-3 is a whole-program reachability analysis over the AST with real import resolution
(package re-exports included). Its roots must include:

- every module's top-level code (command registration);
- modules named in strings, such as `virtual_paths._PROXY_OBJECT_MODULES`;
- the names a viewer declares as `name = None` placeholders, which
  `configure_*_runtime(globals())` fills from a command module **including names that module only
  imports**.

After deleting, check that every `from X import name` in the package and the tests still
resolves, and that every viewer placeholder is bound after importing its command module. An
unused-import trim can remove a name another module imports from that module: it happened to
`AlignmentIntersectionDetectionService`, which the Presets panel imports through
`cmd_intersection_editor`, and the analysis then reported a live service as dead.

### Two hard constraints on deleting code

- `virtual_paths._PROXY_OBJECT_MODULES` lists the modules that keep saved documents
  restorable, because a FreeCAD object's `Proxy` is stored by module path. Deleting one is
  data loss, not cleanup.
- The maintained smoke runners would lose most of their scripts if the legacy surface went.

### Deleting a condition is not deleting a branch

Removing only the `if` lines left unreachable `return` statements twice. It parses, and
flake8 says nothing. Delete whole clauses and read the resulting function back.

### A synthetic default becomes geometry

A function returning a synthetic result instead of `None` feeds the caller's template: a
2 percent lane became 3 percent once. When no source applies, return `None`.

### Smaller ones

- The TIN preview meshes are in metres, not millimetres.
- `_show_message` takes `self.form`, not `self.widget`.
- `git add -A` on a large deletion may be refused by the auto-mode classifier. Stage paths
  explicitly.
- Measure before asserting; the plan records each correction with its measurement.

## 6. The validation gate

Everything below runs headless through the FreeCAD interpreter, which `AGENTS.md` requires for
every Python command in this repository:

```powershell
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m flake8 <touched files>
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pytest tests\architecture -q
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pytest tests\contracts -q
.\tests\regression\run_short_term_smokes.ps1
.\tests\regression\run_practical_scope_smokes.ps1
.\tests\regression\run_loft_retirement_gate_smokes.ps1
```

Result at `6200cea`: flake8 clean on the touched files, 9 architecture tests, **1,163 passed /
18 skipped / 0 failed** (fewer than the 1,179 at `8fbbae0` because the tests of the deleted code
went with it), all three runners PASS. The contract suite takes about 6 minutes.

The architecture ratchet forbids removed names reappearing and forbids a command importing an
underscore-prefixed service symbol. A service may not import from a command.

## 7. What the gate does not cover

No part of the above opens a window.
[V1_INTERSECTION_MANUAL_QA.md](./V1_INTERSECTION_MANUAL_QA.md) is the intersection GUI
procedure and [V1_UNRELEASED_CHANGES_MANUAL_QA.md](./V1_UNRELEASED_CHANGES_MANUAL_QA.md) the one
for the rest of the branch. `AGENTS.md` is explicit that GUI integration must not be claimed when
only headless tests ran.

## 8. Resuming on another PC

### Get the branch

Push the branch from the first PC before switching (`git push origin ganada_0902`) and check
that `git status -sb` no longer says `ahead`.

On the other PC the workbench must sit in FreeCAD's user `Mod` folder, under the name
`CorridorRoad`:

```powershell
cd "$env:APPDATA\FreeCAD\v1-1\Mod"
git clone https://github.com/ganadara135/CorridorRoad.git CorridorRoad
cd CorridorRoad
git checkout ganada_0902
```

If the folder already exists, run `git fetch origin`, `git checkout ganada_0902` and
`git pull --ff-only`. Check that `git log --oneline -1` shows the head named at the top of this
document. Keep `core.autocrlf` as on the first PC (`true`): a different setting rewrites the
line endings of every file (section 5).

### Environment

- FreeCAD 1.1 installed at `C:\Program Files\FreeCAD 1.1`. Every Python command uses
  `C:\Program Files\FreeCAD 1.1\bin\python.exe` (`AGENTS.md`). If it is installed elsewhere,
  adjust the paths in `scripts\freecad_environment.ps1`.
- Development tools, once:
  `& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pip install -r requirements-dev.txt`
- Check `scripts\check_freecad_environment.ps1`, then run the gate of section 6. The numbers
  of section 6 mean the checkout is complete.
- Start FreeCAD, choose the Parametric Road workbench and look for Python errors in the Report
  view.

### What does not travel

- **Helper scripts.** The reachability analysis, the import and viewer binding checks, the test
  pruning and the line-ending repair used from R7c-2 to `275ca65` lived in a temporary folder of
  the first PC and are not in the repository. Section 5 describes what they did; rebuild them
  from it if the next cleanup needs them. The line-ending rule is the snippet in section 5.
- **Test documents.** The FCStd files made during the GUI checks are not committed. Make new
  ones from the presets. A roundabout document from before R7c-3 (step 1 of section 4) can be
  made by checking out `fdc36d0`, creating the roundabout preset, saving, and returning to
  `ganada_0902`.
- **Claude Code memory and sessions** are per PC. This document, `AGENTS.md` and the redesign
  plan carry everything needed.
