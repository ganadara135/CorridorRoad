# V1 Session Handoff

Date: 2026-10-05
Branch: `ganada_0902`, 24 commits ahead of `main` (`1abad47`, the 1.1.0 release)
Head: `b2b1de0` Give the curb return radius and the design vehicle a review state (plan item 5.11)
Work covered: 2026-09-24 to 2026-09-28

## 1. What this document is

A handoff for whoever picks this branch up next. It records what the session set out to
do, the decisions that were taken and should not be re-litigated, what changed, what is
left, and the traps that cost time. It does not repeat what the code, the git history or
`AGENTS.md` already say.

The authoritative plan for the intersection work is
[V1_INTERSECTION_SCOPE_AND_IMPROVEMENT_PLAN.md](./V1_INTERSECTION_SCOPE_AND_IMPROVEMENT_PLAN.md).
Where this document and that plan disagree, the plan is right: it carries the measurements.

## 2. Goals, in the order they were set

1. Put `02_Surfaces` before `03_Alignment & Profile` in the project tree.
2. Decide how multiple roads are organised, and write down when a Region applies.
3. Delete what nothing reaches, in four sweeps: `docsV0`, `docsV1`, `tests`, then code.
4. Reduce the intersection scope to three kinds and plan the improvements the remaining
   flow needs.
5. Execute those improvements one item at a time, reporting the next step after each.

## 3. Decisions taken

These were settled with the user and are not open questions.

**Multiple roads: one road per document.** A separate document per independent route;
`AlignmentModel` for roads that actually meet; `RegionRow` only for policy that varies
along one axis. Written up in
[V1_ROUTE_SEPARATION_AND_REGION_CRITERIA.md](./V1_ROUTE_SEPARATION_AND_REGION_CRITERIA.md).
Region must not absorb Structure, Drainage or Intersection semantics.

**Intersections: T, Cross and Roundabout only.** `Skewed`, `Urban Curb/Gutter`,
`Drainage-Sensitive Sag` and `Y` were removed with their kind-dependent branches. The panel
never exposed them. A document saved against a removed kind still opens and falls through
to the default corner and radius behaviour. Reinstating them is out of scope.

**The Roundabout stays arc-based.** The question of a polyline approximation was raised and
closed: item 5.4 is per-approach geometry, not a change of primitive.

**`docsV0` is deleted**, along with the 1.0.1 announcement draft. Both live in git history.
The 5-level Document Classification in `V1_SUPPORTED_DOMAIN_STATUS.md` exists to **retain**
historical plans, not to prune them, so `docsV1` was swept conservatively.

**Item 5.10's three open questions** were delegated and answered in the plan:
`edge_policy_rows.source_method` may be promoted to `subassembly_derived` but only as its
own separately-labelled action, never inside `Accept Reviewed Rows`;
`drainage_policy_rows.intent_status` is not touched, because promoting a drainage hint to
drainage intent inside an intersection review would have the Intersection absorb Drainage's
meaning; the five families' diagnostics are cleared, with provenance left to `source_method`.

**Item 5.11's compatibility rule:** a stored row missing `approval_status` restores as
`accepted`, the same fallback the other nine families use. Inventing `draft` for it would be
a guess about a history the document does not record.

## 4. What changed

### Tree and documentation

- `objects/obj_project.py` swapped the first two tree roots. The **object names were kept**
  (`CRV1_03_Surfaces`, `CRV1_02_Alignment_Profile`) so saved documents keep their folders;
  only labels and order change, applied with `force=True` on existing documents.
- `docsV1/V1_ROUTE_SEPARATION_AND_REGION_CRITERIA.md` added. Its §4.4 was **corrected** in
  `f86fc34`: the first draft wrongly claimed Applied Sections was single-alignment.

### Deletions

7 v0 task panels, 11 legacy command modules, 9 placeholder modules, `v1/common/schema.py`,
13 unused module-level names, 2 icons, 27 regression scripts, and all of `docsV0`.

### Intersection improvements (plan §5)

| item | state | what it did |
| --- | --- | --- |
| 5.1 | already implemented | unsupported-kind diagnosis |
| 5.2 | closed 2026-09-27 | was a test defect, not a code defect |
| 5.3 | done | the panel's source review table, `Refresh Review` / `Accept Reviewed Rows` |
| 5.4 | **done except authoring** | per-approach apron width (`roundabout_approach_apron_width`) and entry / exit flare radius (`roundabout_approach_entry_radius` / `..._exit_radius`, right-hand traffic fixed in code); no editor field yet; Roundabout still creates no slope face preview |
| 5.5 | done | superelevation paired per Alignment |
| 5.6 | done | Applied Sections names the Alignments it skips |
| 5.7 | closed 2026-10-05, no cache | the chain costs 0.3 s of a 5.9 s T build; the time was in the shared breakline audit and patch constraint matching, which was then made 3 to 8 times faster with identical output on 2026-10-07 |
| 5.8 | done 2026-10-06 | `Use Existing Alignments` adds overlay control Regions to the user's Region models and writes the Superelevation and Drainage handoff sources |
| 5.9 | done | the preset-default checklist in the panel |
| 5.10 | done 2026-10-05 | the review covers the five remaining families; the edge-family adoption is its own action |
| 5.11 | done | gave the curb return radius and the design vehicle a review state |

New service: `v1/services/editing/intersection_review_service.py`, a document-free,
widget-free review of intersection source rows. New presentation rows:
`intersection_leg_section_coverage_rows` in
`ui/presentation/intersection_contract_review_presentation.py`.

Review row counts after 5.10: **T 18, Cross 30, Roundabout 24**, all reaching `n of n` from
`Accept Reviewed Rows` alone. A T and a Cross both take the curb return envelope path since 2026-10-07, which
is built from the corner fillets and does not read the edge rows, so `IntersectionBoundaryOwnerStatus` is
`ready` without adopting: 4 owners for a T, 8 for a Cross. (A T used to need `Adopt Edge Families From
Subassembly` and showed 15 owners.) The loop coverage stays 0 of 32 filled for a Cross, since no face
fills the arcs; the plan's §5.10 Outcome records the measurement.

## 5. What is left

### Intersection plan, in order

1. **5.4, authoring** — the per-approach apron and flare rows exist only as source rows; there is no editor
   field. Circulation direction is fixed to right-hand traffic in code; a project setting would be its own item.
0. **The fixed frame of the intersection evaluation** — `evaluate_topology`, `evaluate_edge_network` and
   `evaluate_boundary_loops` place the legs on the X and Y axes (`_intersection_alignment_axis`); nothing in the
   source or topology carries an alignment bearing. On a document whose roads lean, the boundary loop and the patch
   rectangles it shapes are turned wrong (the user's captures of 2026-10-07). The patch boundary's curb returns are
   real fillets since 2026-10-07 and build the arc slope face strip (plan section 5.10, "The arcs the build draws").
   Next: carry each alignment's direction at the intersection from the commands into the evaluation.
2. **The slope face fill of the curb return arcs** — a Cross's and a T's arcs are now fillets tangent to the
   pavement edge (done 2026-10-07, plan section 5.10 "Curb return fillet for a Cross" and "for a T"). The fill
   (`curb_return_slope_face_perimeter_outer_point_missing`, Cross loop coverage 0 of 32) can be revisited now
   that the arcs are on the pavement edge, and is still undone. It is now the only thing keeping the T's boundary
   loop coverage at `warning` (27 of 43 filled, the 16 unfilled are exactly the arcs, which
   `smoke_intersection_t_slope_face_surface.py` pins). The T work was checked headless and by the regression
   runners only; a new Build Parametric capture of the same T view is the check that matters. The T's leg edge rows
   stay one-sided, and the curb return arc role now lists the ordinary slope face as a consumer.
3. **The 160 constraint support triangles** — every `constraint_support_triangle` of the Cross patch
   (`shared_breakline_constraint_edge`) is skinny, minimum quality 0.0122, before and after the fillet. The
   fillet's boundary polygon triangles are fixed (Delaunay flips, 12 skinny to 0, done 2026-10-07). The edge
   offset rule `lane_width_from_arm_policy` also reads the arm policy now (2026-10-07: half the lanes, plus
   shoulder, plus half the median; the starter gives 4.5 m, unchanged), so the fillet follows the arm.

### Repository-wide

- **Legacy retirement is blocked.** 8 unreachable modules, 7,045 lines, cannot go until a
  stored-`Proxy` migration exists. See §6.
- `cmd_project_setup` has no v1 successor. It is the one surfaced workflow stage still
  driven by a v0 task panel.
- `main` is still at `1abad47` (1.1.0). Whether to advance it is **undecided** and is the
  user's call.
- `V1_RELEASE_CURRENT_PREP.md`'s `- [ ] FreeCAD manual smoke QA for the published tag.`
  stays unchecked on purpose: the new procedure covers the unreleased branch, which is a
  different claim from the tag.

## 6. Cautions

### Line endings will burn you

Tracked files store **mixed CRLF and LF inside the same file**. `Edit`, `Write` and
`sed -i` normalise them and produce thousands of spurious diff lines. This happened to
`docsV1/README.md` (139 lines) and `V1_MASTER_PLAN.md` (384 lines) and needed
`git checkout` to undo.

Edit an existing tracked file only through a line-based script:

```python
text = io.open(path, "r", encoding="utf-8", newline="").read()
lines = text.split("\n")                      # each element keeps its own trailing "\r"
...                                           # splice whole lines, never rewrite the file
updated = "\n".join(lines)
assert updated.endswith("\n") == text.endswith("\n")   # the trailing-newline guard
io.open(path, "w", encoding="utf-8", newline="").write(updated)
```

Dropping the final empty element of the split loses the trailing newline and produces a
whole-file diff. A brand-new file is safe to write normally.

### Anchors, not names

`list.index(...)` returns the **first** match, and this repository has duplicate lines:
`row = intersection_preset_row_from_label(self._selected_label())` appears in two methods of
the same class, and targeting the wrong one nearly deleted a line that is read. Anchor every
splice inside its enclosing `def`.

Name-based searching misattributes across v0 and v1, which both have `obj_corridor.py`,
`obj_stationing.py` and `obj_alignment.py`; and `by_intersection` contains `y_intersection`
as a substring. Use an AST graph with resolved relative imports.

### The AST graph is not enough either

It misses module names held in strings. Two modules were nearly deleted that way:
`obj_pointcloud_dem`, named in `_PROXY_OBJECT_MODULES`, and `ui/task_corridor.py`, named as
`corridor_compat.PREFERRED_TASK_MODULE` and asserted by 3 gate smokes.

### Two hard constraints on deleting code

- `virtual_paths._PROXY_OBJECT_MODULES` lists **15 modules** that keep saved documents
  restorable, because a FreeCAD object's `Proxy` is stored by module path. Deleting one is
  data loss, not cleanup.
- The maintained smoke runners would lose **26 of 36** scripts if the legacy surface went.

### Deleting a condition is not deleting a branch

Removing only the `if` lines left unreachable `return` statements twice. It parses, and
flake8 says nothing. Delete whole clauses and read the resulting function back.

### A synthetic default becomes geometry

`_evaluate_superelevation` returning a synthetic result instead of `None` did not merely
record a value: the caller feeds it into the subassembly template, and a 2 percent lane
became 3 percent. Caught only by `test_section_preview_consistency` in the full gate. When
no source applies, return `None`.

### Smaller ones

- `_show_message` takes `self.form`, not `self.widget`. Only the panel test caught it.
- `IntersectionLegRow` and `IntersectionControlArea` default to `approval_status="accepted"`;
  the preset writes `"draft"` explicitly at construction. The completeness pass's
  `getattr(row, "approval_status", "") or "draft"` therefore **preserves** an existing value
  rather than forcing a draft — which is what makes re-applying a preset safe after a review.
- `git add -A` is refused by the auto-mode classifier on a large deletion. Stage explicitly.
- Four of the nine original plan items were **wrong** on inspection and one was a test
  defect. Measure before asserting; the plan records each correction with its measurement.

## 7. The validation gate

Everything below runs headless through the FreeCAD interpreter, which `AGENTS.md` requires
for every Python command in this repository:

```powershell
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m flake8 <touched files>
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pytest tests\architecture\test_v1_package_boundaries.py -q
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pytest tests\contracts\v1 -q --ignore=tests\contracts\v1\test_intersection_command.py
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pytest tests\contracts\v1\test_intersection_command.py -q
.\tests\regression\run_short_term_smokes.ps1
.\tests\regression\run_practical_scope_smokes.ps1
.\tests\regression\run_loft_retirement_gate_smokes.ps1
```

Result at `b2b1de0`: flake8 clean, 9 architecture tests, **1,368 passed / 18 skipped / 0
failed**, 78 intersection command tests, all three runners PASS. The contract suite takes
about 14 minutes and the intersection chunk about 3.

The architecture ratchet forbids removed names reappearing and forbids a command importing an
underscore-prefixed service symbol. A service may not import from a command.

## 8. What the gate does not cover

No part of the above opens a window.
[V1_UNRELEASED_CHANGES_MANUAL_QA.md](./V1_UNRELEASED_CHANGES_MANUAL_QA.md) is the GUI
procedure, and its §5, an existing document restoring after the tree swap, is the only
blocking check.

**That pass is partly stale.** The user reported the GUI checks complete on 2026-09-28, but
that was **before** items 5.9, 5.11 and 5.10 landed. 5.11 changed the review table from 5 rows
to 8 for a T preset and from 7 to 12 for a Cross, and 5.10 took them to 18 and 30 and added the
`Adopt Edge Families From Subassembly` button, whose confirmation dialog was stubbed in the harness. Sections 7 and 9 of the procedure were
updated to the new numbers and have **not** been re-run in the GUI. Section 5 is unaffected.

The user confirmed the 5.10 procedure (QA section 7: 18 review rows and the `Adopt Edge Families From
Subassembly` button) in the GUI on 2026-10-07. The 5.8 procedure (QA section 6a, `Use Existing
Alignments`) has not been reported yet.

`AGENTS.md` is explicit that GUI integration must not be claimed when only headless tests
ran.
