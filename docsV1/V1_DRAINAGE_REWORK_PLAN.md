# Parametric Road V1 Drainage Rework Plan

Date: 2026-10-16
Branch: `ganada_0902`
Status: Done on 2026-10-16 (DR-1 to DR-5); the current model is in V1_DRAINAGE_MODEL.md. DR-6
(authoring by flow) is planned, section 8
Scope: Drainage rewritten from scratch for road-side drainage: ditch runs, inlets, outfalls and
culverts, flowline checks against a policy, and their review
Related:

- [V1_GENERAL_ROAD_WORKFLOW_IMPROVEMENT_PLAN.md](./V1_GENERAL_ROAD_WORKFLOW_IMPROVEMENT_PLAN.md) (done; this plan builds on GR-1 and GR-3)
- [V1_DRAINAGE_MODEL.md](./V1_DRAINAGE_MODEL.md) (the model this plan built; the earlier
  implementation and Flow Route plans were removed in DR-5 and live in git history)
- [V1_STRUCTURE_CONNECTION_NODE_PLAN.md](./V1_STRUCTURE_CONNECTION_NODE_PLAN.md) (pipe ports; revisited in the Structure rebuild)

## 1. Purpose

The current Drainage is about 12,900 lines across source, services, mappers, editor, review and
tests, and still misses its main engineering check. A review on 2026-10-16 found:

- ditch points take the first Drainage element active on their side, whatever its kind; an inlet or
  an outfall can tag a ditch, two ditches on one side get the same ref, and a fallback guesses the
  side from "left"/"right" in the id;
- `_element_route_offset` reads an `offset` field elements do not have, so it is always 0;
- policy families are guessed from words such as "culvert" or "outfall" in ids and free text;
- `min_grade_rule` and `low_point_rule` are stored but never used: the flowline grade check
  (ok / flat / reverse) does not compare with the policy's minimum grade;
- `direction` holds a preset's route label (`ditch_to_inlet`), which nothing reads;
- the editor offers 7 element kinds, services carry their own alias sets (gutter, swale, channel,
  lined_ditch, catch_basin, outlet_reference), and Applied Sections only ever produce `ditch`;
- pipe results take six steps (candidate, segment, geometry, solid, network, junction); solid,
  network and junction feed only the paused Watertight Solids and the Simulation package.

The rework starts from what a user does, asks for the least input, and derives everything else
from the road results.

## 2. Decisions taken

- Rewrite, not repair. The old Drainage source, services, mappers, editor, review and their tests
  are removed; existing documents need no migration (standing rule of this branch). A saved
  document's old Drainage object is replaced when the new editor first applies.
- Kept: the command IDs `CorridorRoad_V1EditDrainage` and `CorridorRoad_V1DrainageReview`, the
  `05_Drainage` tree folder, the icons, and the Assembly `ditch` subassembly with its
  `ditch_surface` point role and the corridor `drainage_surface`.
- Drainage owns where water is collected and where it goes. The ditch shape stays owned by the
  Assembly; Drainage never edits section geometry.
- Flow direction, grades, low points and elevations are evaluated, never authored.
- Kinds are a closed list. No kind, family or side is ever inferred from an id or a label.
- Pipes stop at a checked link: from, to, length and grade. Pipe bodies wait for the Drainage
  structure work in `V1_DRAINAGE_STRUCTURE_PLAN.md` (decided 2026-11-08: Drainage owns culverts and
  pipes; Structure interaction rules and zones are removed).
- The Drainage paths of Watertight Solids and the Simulation package are removed with the old
  pipe results (D2 of the general road plan deferred this to here).

## 3. User workflow

```text
1. Which ditches drain the road?        -> Ditch Runs (prefilled from the Assembly)
2. Where is water collected or let out? -> Points: inlet, outfall, culvert (suggested at low points)
3. What flows where?                     -> Links: from -> to
4. Does it drain?                        -> Review: flowline profile and checks against the Policy
```

Every step has a default or a suggestion, so a road with a ditch gets a complete, checked Drainage
in a few clicks: open the editor, accept the prefilled runs, accept the suggested inlets, Apply.

## 4. Source model (`v1/models/source/drainage_model.py`, rewritten)

| Row | Fields | Notes |
|---|---|---|
| `DrainagePolicy` (one per document) | `min_grade_percent`, `max_inlet_spacing_m`, `low_point_rule` (`require_inlet`, `allow_ponding`) | numbers and choices only |
| `DitchRun` | `ditch_run_id`, `side` (`left`/`right`), `subassembly_ref`, `station_start`, `station_end` | the subassembly must be an Assembly `ditch`; one run per ditch and span |
| `DrainagePoint` | `point_id`, `kind` (`inlet`/`outfall`/`culvert`), `station`, `side` or `offset_m`, `ditch_run_ref` | an inlet on a run takes the run's side and flowline; a culvert crosses the road and has both sides |
| `DrainageLink` | `link_id`, `from_ref`, `to_ref` | refs to points; a run drains to the points on it by evaluation, not by a link |

- Units are explicit in field names: stations and offsets in meters, grade in percent.
- Identity: one Drainage object per project, as GR-1 settled. Ids are stable and generated by the
  editor (`ditch:left:1`, `inlet:3`).
- Persistence follows the object adapter pattern (`obj_drainage.py` rewritten): one property per
  column, `if not hasattr` guards, no schema migration.

## 5. Evaluation and result

```text
Applied Sections -> Drainage evaluation -> Drainage result -> Build Parametric tags / Review / Outputs
```

`v1/services/evaluation/drainage_evaluation_service.py` (new, pure Python):

- Flowline per Ditch Run: the run's `ditch_surface` low point at every Applied Section in its span,
  with station, x, y, z.
- Derived per run: grade between sections, low points, high points, and the flow direction of each
  segment.
- Checks against the Policy, each with run or point ref, station and status:
  - grade below `min_grade_percent` (flat) or against the outlet (reverse);
  - a low point with no inlet or outfall within one section spacing (`require_inlet`);
  - inlet spacing above `max_inlet_spacing_m`;
  - a point off its run's span, or a culvert outside the road;
  - a link whose `to` is higher than its `from`, a link loop, a point that drains nowhere.
- Suggestions: an inlet at each uncovered low point, and inlets where spacing is exceeded, as
  rows the editor can apply.

`DrainageResult` (`v1/models/result/drainage_result.py`, replaces `drainage_pipeline.py`) holds the
flowlines, checks, suggestions and links with length and grade. It is stored on its object and is a
freshness stage after Applied Sections (GR-3): Profile, Superelevation, Assembly or Drainage source
edits make it stale, and Rebuild Downstream rebuilds it.

Applied Sections tag `ditch_surface` points with the `ditch_run_id` whose `subassembly_ref` and side
match the point's own subassembly, and nothing else. The Region/station context no longer carries
Drainage refs.

## 6. UI

- **Drainage editor** (`ui/editors/drainage_editor.py`, rewritten): one panel.
  - Policy: three fields at the top.
  - Ditch Runs table: prefilled from the active Assembly's ditches over the Region spans when the
    source is empty; editing is by station range and on/off.
  - Points table in station order, with a Suggestions list beside it; "Apply suggestion" adds the
    point to the table, not to the document.
  - Links table with from/to pickers listing the points.
  - Nothing is written until Apply; Cancel writes nothing; opening the editor never creates sample
    data.
- **Drainage Review** (`ui/viewers/drainage_review_view.py`, rewritten): a flowline profile per
  run with points, low points and failing segments marked, a checks table that focuses the 3D view
  on a row, and the GR-3 freshness line. It edits nothing.
- **Build Parametric** keeps one Drainage line: the result's status and check count, with a button
  to open the review. The old Drainage and flow review rows and highlights leave the command.

## 7. Removal list

Removed with DR-1 unless noted (roughly 7,500 lines of code and tests):

- `services/evaluation/drainage_resolution_service.py`
- `services/mapping/drainage_review_mapper.py`, `drainage_pipeline_geometry_mapper.py`,
  `drainage_pipeline_solid_mapper.py`, `drainage_pipeline_network_mapper.py`
- `models/result/drainage_pipeline.py`; `models/output/drainage_output.py` is rewritten in DR-5
- `ui/presentation/drainage_review_presentation.py`, `drainage_flow_review_presentation.py`
- the Drainage review, flow review, highlight and pipe preview functions of `cmd_build_corridor.py`
  (`corridor_drainage_*`, `_drainage_*`, `create_corridor_drainage_surface_preview` is kept)
- the Drainage refs in `station_context_resolver.py` and the side guessing in
  `applied_section_service.py` (`_section_row_drainage_refs` and helpers)
- the Drainage paths of `cmd_watertight_solids.py`, `watertight_simulation_*`,
  `solid_target_discovery_service.py` and the Simulation package (DR-4)
- the old tests: `test_v1_drainage_source_object.py`, `test_drainage_editor_command.py`,
  `test_drainage_review_command.py` and Drainage cases elsewhere, replaced phase by phase
- `V1_DRAINAGE_MODEL.md`, `V1_DRAINAGE_IMPLEMENTATION_PLAN.md`,
  `V1_DRAINAGE_FLOW_ROUTE_IMPLEMENTATION_PLAN.md` and `wiki/Drainage.md`, rewritten in DR-5

Between DR-1 and DR-5 the Drainage Review command stays registered and shows "being rebuilt"; this
branch is not released in between.

## 8. Phases

### DR-1 Source model and Ditch Runs

- Rewrite `drainage_model.py` and `obj_drainage.py`; remove the files in section 7.
- Applied Sections tag ditch points by `subassembly_ref` and side through the Ditch Run.
- Editor: Policy and Ditch Runs, with prefill from the Assembly.
- Tests: model round trip and save/reopen; prefill from "Full Set Road"; two ditches on one side
  get their own runs; a ditch outside every run is untagged.

Done on 2026-10-16:

- `drainage_model.py` holds `DrainagePolicy`, `DitchRun`, `DrainagePoint` and `DrainageLink`
  (points and links are stored now and edited from DR-3 and DR-4). A Ditch Run also names its road
  (`alignment_ref`), so an Intersection document's roads keep their own runs.
- `obj_drainage.py` stores the model in its payload only, with count and policy properties for the
  property view. An object from before restores empty and drops its old row properties on write.
- `services/editing/drainage_editing_service.py`: the prefill (one run per ditch and side, joined
  across Regions that use it, split where a Region's Assembly has none) and the run and policy
  checks. `cmd_drainage_editor.py` reads the document and applies; the panel edits the Policy and
  the runs, prefills them when the source has none, and writes only on Apply.
- `StationContext` carries the runs covering a station on its road; Applied Sections tag a ditch
  point and a ditch Subassembly row only with the run of the same Subassembly and side. The
  `"left"`/`"right"`-in-id guess and the first-element fallback are gone.
- Removed as planned, and also (moved here from DR-4, since the old model they read is gone): the
  Drainage pipe and network targets and builds of Watertight Solids; their Drainage handoff now
  counts lined ditch bodies only. Build Parametric's Drainage tab and the Drainage Flow step are
  removed; the Drainage Surface step counts the ditch points no run covers until DR-5 adds the
  Drainage line. Drainage Review shows a "being rebuilt" note.
- Tests: `test_drainage_editing_service.py` and `test_drainage_source_and_editor.py` (new); the
  ditch tagging, station context, quantity, section viewer, solid target and Watertight tests
  follow the runs; the old Drainage editor, review, source and validation tests are removed.
- Left for later: the solid target families `drainage_pipeline_body` and
  `drainage_pipeline_network_body` stay listed in the Watertight QA service; DR-4 removes them with
  the rest of the pipe handoff.

### DR-2 Flowline evaluation and checks

- `drainage_evaluation_service.py` and `DrainageResult` with flowlines and the grade checks.
- Freshness stage `drainage` after `applied_sections`; Rebuild Downstream includes it.
- Tests: grade, low point and direction on a profile with a sag; flat and reverse against the
  policy; stale after a Profile edit and current after a rebuild.

Done on 2026-10-16:

- `models/result/drainage_result.py`: `DrainageResult` with one `DitchRunFlowline` per enabled run
  (stations, segments with plan length, grade and flow direction, low and high points) and
  `DrainageCheck` rows. Stored on `V1DrainageResult` in the Drainage folder
  (`objects/obj_drainage_result.py`), with the check rows as text for the property view.
- `services/evaluation/drainage_evaluation_service.py`: the flowline is the run's tagged
  `ditch_flowline` point at each Applied Section in its span; a grade is the rise over the plan
  length along the flowline. Low points are where it turns from falling to rising (the lowest
  station of a flat bottom) and the ends it falls toward; high points the reverse. Checks:
  `flowline_missing` (error: fewer than two stations), `flat_grade` (warning: under the Policy
  minimum, one row per stretch) and `low_point` (info).
- Freshness stage `drainage` after `applied_sections`: it reads the Applied Sections result and the
  whole Drainage source. Applied Sections now record only the Ditch Runs of the Drainage
  (`drainage_ditch_runs`), so a Policy edit leaves them current. Rebuild Downstream rebuilds a stale
  Drainage result and makes the first one when a Drainage with runs meets existing Applied Sections
  (`commands/cmd_drainage_result.py`).
- The Drainage panel shows the stored result and whether it is current when it opens. Apply
  evaluates at once when the Applied Sections are current (a Policy edit) and otherwise says to run
  Rebuild Downstream (a run edit retags the ditch points first).
- Ditch Run ids are shorter: `ditch-run:ditch:left`, with the road only in a document of several.
- The workflow smoke fills the Drainage from the Assembly, evaluates it, checks both flowlines and no
  errors, and expects the Drainage stage stale after the Profile edit and rebuilt by Rebuild
  Downstream.
- Tests: `test_drainage_evaluation_service.py` (new); the stage test in
  `test_drainage_source_and_editor.py`.
- Moved: the "reverse" check needs to know where the water must go, so it comes with the outfalls
  and links (DR-3, DR-4): a run draining away from its outfall is the reverse case.

### DR-3 Points and suggestions

- Points table, suggestions and "Apply suggestion"; low point and spacing checks.
- Tests: a sag yields one inlet suggestion; applying it clears the check; spacing suggestion count.

Done on 2026-10-16:

- Collectors of a run: its own inlets and outfalls, and culverts that name no run and cross its
  road. A run's point outside its flowline stations collects nothing and is a `point_off_run`
  warning.
- `low_point_uncollected` (warning, under `require_inlet`): no collector within one section spacing
  of a low point (the larger station step beside it). The suggestion is an outfall at a run end the
  flowline falls toward and an inlet elsewhere. Under `allow_ponding` the low point stays an info
  row.
- `inlet_spacing` (warning): a stretch between collectors, suggested low-point collectors, high
  points and run ends longer than the maximum spacing, measured along the flowline. Inlets are
  suggested to split it into equal parts.
- `DrainageResult.suggestion_rows`; the source checks refuse a point with an unknown kind, an
  unknown run, a repeated id, or an inlet or outfall without a run
  (`drainage_editing_service.point_diagnostics`).
- The Drainage panel has Ditch Runs and Points tabs. The Points tab adds inlets, outfalls and
  culverts, and lists the current result's suggestions: Add Selected and Add All put them in the
  table (once), Apply writes them and evaluates at once, since points do not change the Applied
  Sections. A stale result offers no suggestions.
- Tests: the sag, collector, culvert, ponding, spacing and off-run cases in
  `test_drainage_evaluation_service.py`; the point checks in `test_drainage_editing_service.py`;
  the panel adding every suggestion of the sample road and Apply clearing its checks in
  `test_drainage_source_and_editor.py`.

### DR-4 Links

- Links table and checks (uphill link, loop, point draining nowhere); length and grade per link.
- Remove what is left of the Drainage paths of Watertight Solids and the Simulation package (DR-1
  removed the pipe bodies).
- Tests: link grade and length; uphill and loop diagnostics; Watertight smokes still pass without
  Drainage input.

Done on 2026-10-16:

- A point sits on its run's flowline at its station (a culvert that names no run on the lowest
  flowline of its road there); `point_places` in the evaluation service. A Link is measured between
  its points' places: `DrainageResult.link_rows` hold its plan length, end elevations and grade.
- Link checks: `link_uphill` (warning: the To point is higher), `link_flat` (warning: falls less
  than the Policy minimum grade), `link_loop` (error, each loop once), `link_unplaced` (warning: an
  end on no flowline), `drains_nowhere` (warning: an inlet without an outgoing link; outfalls and
  culverts may end the water's way) and `drains_twice` (warning: more than one outgoing link).
- The reverse check from DR-2: `reverse_flow` (warning) for an inlet or outfall where the flowline
  falls away on every side, so no water reaches it.
- Source checks refuse a link with a repeated id, an unknown point, the same point at both ends or a
  repeated pair (`link_diagnostics`). The panel's Links tab adds and deletes links; Link Downhill
  joins every inlet that drains nowhere to the nearest lower point on its run (or a culvert crossing
  its road), from the current result's flowlines.
- Removed: the Drainage readiness of the Simulation package (its 13 fields, the object properties
  and the export block) and the per-solid drainage refs; the Drainage handoff summary and status
  lines of Watertight Solids; the pipe families `drainage_pipeline_body` and
  `drainage_pipeline_network_body` with their labels, and the Simulation QA pipe-to-Structure port
  check (`port_connection_status`, `port_issue_count`), which only pipe bodies could fail. Lined
  ditch bodies stay; they are Assembly ditch solids and carry their Ditch Run.
- Tests: the link, loop, reverse, culvert and unplaced cases in `test_drainage_evaluation_service.py`;
  the link checks and Link Downhill in `test_drainage_editing_service.py`; the panel test links the
  sample road's inlets downhill and checks the links fall. The Watertight and Simulation tests use
  lined ditch bodies; their port and Drainage handoff tests are removed.

### DR-5 Review and outputs

- Drainage Review rewritten; Build Parametric Drainage line; `drainage_output.py` rewritten from the
  result; docs and wiki rewritten.
- `smoke_v1_workflow.py` adds a ditch run, an accepted inlet suggestion and a link, and checks the
  Drainage stage goes stale and current with the others.

Done on 2026-10-16:

- `models/output/drainage_output.py` and `services/mapping/drainage_output_mapper.py`: the Drainage
  output from the source and result (flowlines with profile and grade range, points with their
  places, links, checks), `source_and_result` in the output traceability rules again.
- `ui/presentation/drainage_review_presentation.py`: run rows, the flowline profile (points, low and
  high points, stretches flagged by `flat_grade` and `inlet_spacing`), the checks table (errors
  first) and the summary line.
- Drainage Review (`ui/viewers/drainage_review_view.py`, `commands/cmd_drainage_review.py`): a run
  picker, a painted flowline profile, the checks table and the freshness line. Double-clicking a
  check draws `ReviewDrainageCheckHighlight` on the flowline (the flagged stretch and a sphere at its
  station) and selects it.
- Build Parametric: the summary has a Drainage line, Guided Review "6. Drainage Surface" takes the
  result's status and counts, and a Drainage Review button closes Build Parametric and opens it.
- The workflow smoke accepts every suggestion, links the inlets downhill, and checks that no low
  point, spacing, link or drains-nowhere check is left and every link falls.
- Docs: `V1_DRAINAGE_MODEL.md` and `wiki/Drainage.md` are rewritten for this model;
  `V1_DRAINAGE_IMPLEMENTATION_PLAN.md` and `V1_DRAINAGE_FLOW_ROUTE_IMPLEMENTATION_PLAN.md` are
  removed (git history keeps them). The 1.0.0 release plan and record still name the old plan; they
  are records of that release.
- Tests: `test_drainage_review_presentation.py` (new); the Review panel, highlight and Build
  Parametric line in `test_drainage_source_and_editor.py`; `DrainageOutput` back in
  `test_supported_output_traceability.py`.
- Left for later: the intersection kernel's low points are not in the Drainage Review; pipes and
  their Structure ports come with the Structure rebuild.

GUI review fixes, 2026-10-17:

- The panel tables kept only the 3 decimals they show, so Apply moved run ends and suggested end
  outfalls (a Policy-only Apply made the Applied Sections stale; an end outfall stayed suggested).
  The cells now keep the exact station (`_station_item`, `_station` in `drainage_editor.py`), and
  a point within 0.5 mm of a flowline end (`STATION_ENTRY_TOLERANCE_M`) lies on it.
- `reverse_flow` measures the flowline length draining to the point and warns below one section
  step, so a point beside a crest between sections is caught.
- The check highlight stands 1.5 m above the flowline on a stem, its stretch 0.05 m above, so it no
  longer shares the ditch surface's faces.
- Drainage panel and Drainage Review buttons open each other; the panel's message box is 160 px.
- Rebuild Downstream on the toolbar opens a window (`ui/viewers/rebuild_downstream_view.py`) with
  the stage freshness, a per-stage progress bar (`rebuild_downstream(progress=...)`) and the report.
- Cross Section viewer columns are user-resizable.

### DR-6 Authoring by flow

Planned on 2026-11-08. Not started.

Why. DR-1 to DR-5 made the model and its checks right, but the panel still authors it as three flat
tables. A user adds a point (its station starts at 0.0 and is typed), adds a Link in another tab and
picks both ends from combo boxes, and sees what drains where only by reading the rows or opening
Drainage Review. The only helpers are the suggestions and Link Downhill. The panel does not show the
checks at all. Drainage is a network, so it should be built and read as one: start from where the
water leaves, and continue upstream along the flow.

Decisions:

- No source change. `DrainagePoint` and `DrainageLink` stay as they are; the flow tree is a view of
  them, and every action only adds, changes or removes points and links in the panel's tables.
  Nothing is written before Apply, Cancel writes nothing, and opening the panel creates nothing.
- Station, side and elevation of a new point come from the stored result's flowlines, as the
  suggestions do; the user never types a station for a continued point. A stale result disables
  Continue and Trace with the same note the suggestions use.
- The tree follows the model's own rules: a point drains into one point at most (`drains_twice`), a
  loop is an error (`link_loop`), so the structure is a forest. Roots are the points with no
  outgoing link (outfalls, culverts, and an inlet that drains nowhere, which is flagged). A loop
  is shown under a separate "Loop" node and never hangs the builder.
- Logic is pure Python and UI-independent: `services/editing/drainage_flow_service.py` (tree,
  continue, trace) and `ui/presentation/drainage_flow_tree_presentation.py` (rows and text).
  `drainage_editing_service.downhill_links` and the suggestion rules are reused, not copied: the
  per-inlet "nearest lower point" step becomes one public function both Link Downhill and Continue
  Downstream call.
- Checks reach a node through the check id (`kind:point_id`, `kind:link_id`); no result field is
  added. Station-only checks (`low_point_uncollected`, `inlet_spacing`) attach to the nearest node
  of the run.
- Existing documents keep working: the new tab reads the same points and links.

#### DR-6a Flow tree

- A Flow tab between Ditch Runs and Points: one tree per document (roads in a multi-road document
  are top-level groups), nodes ordered by station. A node reads like
  `inlet:3  STA 120.000  falls 0.8 % to outfall:1`, and carries a severity mark from its checks.
- Selecting a node selects its row in the Points table; selecting a link target selects its Link
  row. The tree is read-only in this phase.
- Tests: tree of the sample road after Accept All and Link Downhill (roots are the outfalls, every
  inlet sits under exactly one root, no orphan); a loop and a link to a missing point do not hang
  or raise; checks attach by id; the presentation text.

Done on 2026-11-08 (gate passed; GUI check pending):

- `services/editing/drainage_flow_service.py`: `build_flow_tree` makes the forest from the points
  and links (iterative, so a long chain cannot hit the recursion limit); `FlowNode`, `FlowTree`,
  `walk_flow_nodes`, `flow_node_severity`. A point with two outgoing links follows the first; a link
  to a missing point or to itself leaves a root that says so; duplicate point ids make one node.
- Checks attach by id (`kind:point_id`, or `kind:link_id` to the link's From point); only
  `low_point_uncollected` and `inlet_spacing` go to the nearest point of their run. No result field
  was added.
- `ui/presentation/drainage_flow_tree_presentation.py` holds the node, group and note text.
- The Flow tab sits between Ditch Runs and Points. It rebuilds from the tables as they stand when
  the tab opens, after load and after Apply; the stored result's checks and link grades show only
  while it is current (`drainage_flow_result` in `cmd_drainage_editor.py`). Selecting a node selects
  its Points row and its outgoing Link row.
- Tests: `test_drainage_flow_tree.py` (new, 13) and the Flow tab case in
  `test_drainage_source_and_editor.py`. Gate 1,151 passed / 14 skipped, three runners PASS.

#### DR-6b Continue from a node

- **Add Upstream** on a selected node: a new inlet on the node's run, linked into the node. It sits
  one equal step up the flowline, with the step taken from the stretch to the next collector, high
  point or run end, so the Policy's maximum spacing holds and pressing it repeatedly walks up to the
  crest. At the crest or a run end it says there is nothing upstream and adds nothing.
- **Add Downstream** on a node that drains nowhere: a link to the nearest lower point on its run (or
  a culvert crossing its road), and if there is none, a new outfall at the run end the flowline
  falls toward, linked. A node that already drains refuses and names where.
- Both put the new rows in the tables and select the new node.
- Tests: placement on the sample flowline; repeated Add Upstream clears `inlet_spacing` up to the
  crest; Add Downstream never creates a second outgoing link; ids stay unique; refusals.

Done on 2026-11-08 (gate passed; GUI check pending):

- `add_upstream` and `add_downstream` in `drainage_flow_service.py` return a `FlowContinuation`
  (points, links, the node to select, a message); an empty one is a refusal with its reason.
- Add Upstream measures the stretch from the node to the next point, high point or run end on the
  rising side, along the flowline's plan length, and places the inlet one equal part up
  (`ceil(stretch / maximum spacing)` parts, the same split the spacing suggestions use). A
  stretch already within the spacing adds nothing, so the walk ends one spacing short of the crest
  and never puts an inlet where `reverse_flow` would flag it. A culvert has no ditch and refuses.
- Add Downstream links to the nearest lower point (a culvert crossing counts); with none it adds an
  outfall at the run end the ditch falls to all the way, and refuses at a crest-less pocket that
  rises again first. A node that drains, and an outfall, refuse.
- The Flow tab has the two buttons; the new rows go into the tables, the tree is rebuilt and the new
  node selected, so pressing again walks on. `drainage_flowlines` in `cmd_drainage_editor.py` gives
  the stored flowlines only while the result is current.

#### DR-6c Trace Network

- One button builds the missing network as a proposal: the outfalls and inlets the suggestions
  would add, then a downhill link for every inlet that drains nowhere. The tree shows the proposal
  rows as pending; Accept moves them into the tables, Discard drops them. Existing points and
  links are never moved or removed, so it can be run again after hand edits to fill only the gaps.
- The proposal is computed from the current tables and the stored result's flowlines (the points'
  places already come from the flowlines, so unsaved points work). It is not stored anywhere.
- Tests: on the sample road the traced network leaves no low point, spacing, link or
  `drains_nowhere` check; a second trace proposes nothing; hand-placed points survive a trace.

Done on 2026-11-08 (gate passed; GUI check pending):

- `evaluation/drainage_evaluation_service.suggest_points` runs the evaluation's own suggestion
  rules on one stored flowline and any list of points, so unsaved points count; a test pins it to
  the suggestions the evaluation stores.
- `trace_network` in `drainage_flow_service.py` returns a `NetworkProposal` (points, links, the
  inlets it could not drain, a message). It adds the suggested points per run, then drains each
  inlet that drains nowhere, lowest first, with `add_downstream` (a nearest lower point, else a new
  outfall at the run end). An inlet at a low point with nothing lower stays undrained and is named.
- The Flow tab has Trace Network, Accept and Discard. A proposal shows in the tree as pending (`+`,
  `(proposed)`, `(proposed link)`, blue italics); Add Upstream and Add Downstream are off while it
  waits. Accept re-checks ids and refs and drops the proposal if the tables changed. Nothing is
  stored; a stale or missing result refuses with the Rebuild Downstream note (Q5).
- On the sample road the traced network, once Accepted and applied, leaves no low point, spacing,
  link or `drains_nowhere` check, and a second trace says there is nothing to add.

#### DR-6d Fix from the flow

- The Flow tab lists the selected node's checks (message and severity), with the action that fixes
  each: `drains_nowhere` and `low_point_uncollected` offer Add Downstream or the suggestion;
  `link_uphill`, `link_flat` and `drains_twice` offer Reconnect To (a list of the points lower than
  the From point) or Delete Link; `reverse_flow` and `point_off_run` offer Delete Point.
- Tests: each action clears its check after Apply on the sample road.

Done on 2026-11-08 (gate pending; GUI check pending):

- `fixes_for_check`, `reconnect_targets` and `edit_for_fix` in `drainage_flow_service.py` map a
  check kind to its fixes and return a `FlowEdit` (points and links to add, rows to remove, links to
  point elsewhere, or a refusal message): `drains_nowhere` Add Downstream; `low_point_uncollected`
  and `inlet_spacing` Add Suggested (only the suggestions inside the check's stations);
  `link_uphill` and `link_flat` Reconnect To (the lower points, nearest first) or Delete Link;
  `link_loop` Delete Link; `drains_twice` Delete Extra Links (keeps the first link, the one the tree
  follows); `reverse_flow` and `point_off_run` Delete Point (with the links that touched it).
- The Flow tab lists the selected point's checks with the fix each offers, and enables only the fix
  buttons of the selected check (none while a Trace Network proposal waits). Fixes change the tables;
  Apply keeps them and evaluates.
- On the sample road, Add Downstream, Reconnect To, Delete Point and Add Suggested each clear their
  check after Apply.

Out of scope for DR-6: picking points in the 3D view, hydraulics, pipe bodies and Structure ports
(Structure rebuild), automatic culvert placement, and a drag-and-drop graph editor.

Each phase ends with the gate, a GUI check, and a CHANGELOG `[Unreleased]` line, then a commit. DR-6
ends by updating section 6 of `V1_DRAINAGE_MODEL.md`; the wiki draft is changed only on request.

## 9. Validation per phase

```powershell
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" -m pytest tests\architecture tests\contracts -q -p no:cacheprovider
.\tests\regression\run_short_term_smokes.ps1
.\tests\regression\run_practical_scope_smokes.ps1
.\tests\regression\run_loft_retirement_gate_smokes.ps1
```

## 10. Non-goals

- Hydraulics: catchment areas, runoff, capacity and pipe sizing.
- Pipe bodies and manholes (pipe bodies: `V1_DRAINAGE_STRUCTURE_PLAN.md`; manholes stay out).
- Intersection drainage beyond what the intersection kernel already reports as a low point.
- Drainage in Watertight Solids or the Simulation package.

## 11. Open questions

- Q1: Should a culvert carry a diameter now, for review only, or wait for the Structure rebuild?
  Proposed: wait.
- Q2: Should the editor's Ditch Run prefill follow Region spans, or run over the whole Alignment
  where the Assembly has a ditch? Proposed: Region spans, since Regions own the Assembly assignment.
- Q3 (DR-6): Is a culvert a node like any other, tagged "crosses road", whose outgoing link goes to
  a point on either side? Proposed: yes; Continue never creates a crossing by itself.
- Q4 (DR-6): At a low point both directions rise, so which way does Add Upstream go? Proposed: the
  longer uncollected stretch first, and the next press takes the other.
- Q5 (DR-6): May Trace Network run on a stale result? Proposed: no, as for the suggestions; the
  note says to run Rebuild Downstream.
