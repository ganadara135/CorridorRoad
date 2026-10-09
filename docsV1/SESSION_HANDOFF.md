# V1 Session Handoff

Date: 2026-10-09
Branch: `ganada_0902`, 51 commits ahead of `main` (`1abad47`, the 1.1.0 release)
Head: `8fbbae0` Remove edge policy and lane connection rows and the row review (plan R7c-3)
Work covered: 2026-09-24 to 2026-10-09

## 1. What this document is

A handoff for whoever picks this branch up next. It records the decisions that were taken and
should not be re-litigated, the state of the branch, what is left, and the traps that cost time.
It does not repeat what the code, the git history or `AGENTS.md` already say.

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
- **GUI.** The user built the starter T, Cross and roundabout after R7c-1, checked the
  Intersections tab and its highlight after R7c-2, and the tab's `ready` after R7c-3.

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

### Intersections

- **GUI checks not yet reported:** a roundabout document created before R7c-3 rebuilding the
  same ring (it now comes from the curb return radius when no spec is stored); the drainage
  review's low point and the cross section viewer's intersection rows (R7c-2).
- **Circulation direction** of a roundabout is in the spec (`ccw`/`cw`); there is no project
  setting for it.
- **The Breakline Audit tab** shows the corridor's own breaklines only; its intersection parsing
  and the command's legacy intersection metadata were removed after R7c-3 (plan, section 8).

### Repository-wide

- **Legacy retirement is blocked.** Unreachable v0 modules cannot go until a stored-`Proxy`
  migration exists. See section 5.
- `cmd_project_setup` has no v1 successor. It is the one surfaced workflow stage still driven by
  a v0 task panel.
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

Result at `8fbbae0`: flake8 clean on the touched files, 9 architecture tests, **1,179 passed /
18 skipped / 0 failed**, all three runners PASS. The contract suite takes about 6 minutes.

The architecture ratchet forbids removed names reappearing and forbids a command importing an
underscore-prefixed service symbol. A service may not import from a command.

## 7. What the gate does not cover

No part of the above opens a window.
[V1_INTERSECTION_MANUAL_QA.md](./V1_INTERSECTION_MANUAL_QA.md) is the intersection GUI
procedure and [V1_UNRELEASED_CHANGES_MANUAL_QA.md](./V1_UNRELEASED_CHANGES_MANUAL_QA.md) the one
for the rest of the branch. `AGENTS.md` is explicit that GUI integration must not be claimed when
only headless tests ran.
