# Parametric Road V1 Drainage Structure Plan

Status: planned on 2026-11-08, not started. Starts after DR-6 (see `V1_DRAINAGE_REWORK_PLAN.md`).
Replaces the "Structure rebuild" for drainage that the Drainage plan deferred, and makes
`V1_STRUCTURE_CONNECTION_NODE_PLAN.md` obsolete.

## 1. Purpose

Culverts and pipes are part of the drainage flow, so the Drainage source owns them. Today the same
culvert exists twice, as a Drainage point and as a Structure with connection points, and the two
positions can disagree. After this plan there is one place to author them, the Flow tab, and one
pipe geometry.

## 2. Decisions taken (2026-11-08)

- D1: Drainage owns culverts and pipes. Structure keeps the non-drainage kinds only (`bridge`,
  `retaining_wall`, `wall`, `utility`, `custom`).
- D2: Pipes are included, in the simplest form: a pipe is an attribute of a `DrainageLink`, always
  circular, always straight between its two points.
- D3: Structure interaction rules and influence zones are removed. They only produced diagnostics.

## 3. Simplified model

| Item | Source | Evaluated, never authored |
|---|---|---|
| Pipe | `DrainageLink.pipe_diameter_m` (`0` = open flow, no pipe) | length, invert at both ends (the flowline of each point), grade, barrel volume |
| Culvert | a `DrainagePoint` of kind `culvert`, as today; its barrel is the pipe of its outgoing link | crossing length, from the road section width at its station |
| Inlet, outfall | unchanged | unchanged |

- One pipe geometry: a straight circular tube between the two 3D point positions. No manholes,
  headwalls, wingwalls, skew, wall thickness or barrel count.
- Position lives in the Drainage point only. Structure connection points are not needed for it.
- The pipe body is a result of the Drainage stage (`pipe_rows` of `DrainageResult`), never source.
- Units follow the Drainage source: meters, grade in percent.

## 4. Phases

### DS-1 Pipe on the link

- `DrainageLink.pipe_diameter_m`, its object property with an `if not hasattr` guard, the Links
  tab column and the Flow tab text (`... into outfall:1 via pipe 0.60 m`).
- Diagnostics: a negative or non-numeric diameter is rejected at Apply.
- Tests: source round trip, save and reopen, editor column, node text.

Done on 2026-11-08 (gate passed; GUI check pending):

- `DrainageLink.pipe_diameter_m` (default 0, so a link stored before pipes restores as open flow;
  a test writes such a payload). The Links tab has a `Pipe (m)` column, blank for open flow; a
  number that is not one is refused when the table is read, and Apply refuses a negative or
  non-finite diameter. Reconnect To keeps a link's pipe. The Flow tab reads
  `... into outfall:1 via pipe 0.60 m`.

### DS-2 Pipe results and review

- The evaluation adds `pipe_rows` (link, from and to invert, length, grade, diameter, volume). The
  link checks judge the pipe's grade (see the note below). Freshness stays the `drainage` stage.
- Drainage Review lists pipes and previews them as tubes; the Drainage output carries the rows and
  their traceability to the link ids.
- Tests: grade and length on the sample road, stale detection when a point moves, output rows.

Done on 2026-11-08 (gate pending; GUI check pending):

- `DrainageResult.pipe_rows` (`DrainagePipeRow`): the links with a diameter, measured between their
  points' places. Decision: no `pipe_uphill` or `pipe_flat` checks, which this plan first listed; a
  pipe is a link, so `link_uphill`, `link_flat` and `link_unplaced` already judge it and a second
  check would report each problem twice.
- `DrainageOutput.pipe_rows` (`DrainagePipeOutputRow`) through the mapper, so reports and exchange
  see the pipes with their link ids.
- Drainage Review has a Pipes table (double-click draws that pipe) and Show All Pipes; both draw
  cylinders into one `ReviewDrainagePipes` object, replaced each time. It is a preview of the
  stored result, never a source.

### DS-3 Remove the Structure culvert, interaction rules and zones

#### Inspection results (read-only, 2026-11-08)

- **Rules and zones are inert.** `StructureInteractionService.resolve_station` returns the active
  structure ids, rule ids and zone ids of a station. Only the structure ids are used (Applied
  Sections, Region review, solid target discovery, the section viewer, Build Parametric). The rule
  and zone ids are stored on each Applied Section (`active_structure_rule_ids`,
  `active_structure_influence_zone_ids`, the properties `ActiveStructureRuleRows` and
  `ActiveStructureInfluenceZoneRows`), copied through `corridor_surface_geometry_service.py`, and
  turned into two diagnostics in `applied_section_service.py` (`structure_interaction_rule` warns
  when a structure has no rule; `structure_influence_zone` informs the same for zones). Nothing
  reads them to decide geometry. The service itself stays: its job is "which structures are active
  here", and it loses only the rule and zone parts.
- **Connection points are drainage-only.** The two places that require them
  (`_structure_requires_connection_points` in `solid_target_discovery_service.py` and
  `_external_structure_requires_connection_points` in `cmd_watertight_solids.py`) test a closed
  token list that is all drainage: `culvert`, `box_culvert`, `pipe_culvert`, `drainage_crossing`,
  `drainage_node`, `headwall`, `inlet`, `outlet`, `junction_box`, `manhole`. No bridge, wall,
  retaining wall, utility or custom structure needs them, so they go with the culvert.
- **Persistence tolerates removed fields.** A probe wrote a payload with a row field and a whole row
  list that the model class no longer has and restored it: the extra data was ignored and the rest
  restored. So deleting dataclass fields and rows does not break older documents. The old
  FeaturePython properties stay on an old object until it is next written; `obj_structure.py` and
  `obj_applied_section.py` remove them then, the way `obj_drainage.py` removes its retired ones.
- **Applied Sections do not need a forced rebuild.** Freshness follows the inputs, not the schema,
  and an old stored set simply restores without the two removed lists. (This corrects the first
  version of this plan, which said they become stale.)
- **Size.** Culvert and connection-point lines: `cmd_structure_editor.py` 212 of 2,927,
  `structure_editor.py` 99 of 1,545, `obj_structure.py` 60 of 811, `cmd_watertight_solids.py` 38 of
  5,182, `corridor_solid_service.py` 29, `quantity_build_service.py` 23,
  `solid_target_discovery_service.py` 15. Tests: `test_structure_editor_command.py` 247 matching
  lines, `test_v1_structure_source_object.py` 79, `test_watertight_solids_command.py` 39,
  `test_result_builders.py` 33, `test_solid_target_discovery_service.py` 12, and nine smaller files.
- **Tests that use "culvert" only as a kind label** (`test_resolution_services.py`,
  `test_section_command_bridge.py`, `test_build_corridor_command.py`,
  `test_editor_source_edit_service.py`, `test_persistence_payload_object_adapters.py`) are
  relabelled `bridge`; they test something else. The ones that test culvert behaviour are deleted.
- **Outside the code:** `scripts/run_local_validation.ps1` names the test
  `test_structure_editor_normalizes_connection_points_after_station_edits`; it is updated when that
  test goes. The "Drainage Control" Region preset only has the words "ditch and culvert references"
  in its note. The project tree keeps the legacy `CulvertModel` alias to the Drainage folder.
  Culvert quantities (`culvert_barrel_volume`, opening area, barrel count, wall volume, headwall
  count) disappear with the culvert solid; pipe volumes are in the Drainage output and are not yet
  a quantity (Q4).

#### Steps, one commit each, each ending with the gate

1. **Interaction rules and zones (done 2026-11-08).** Remove `StructureInteractionRule` and `StructureInfluenceZone`
   with their model rows, `obj_structure.py` properties and diagnostics, (the editor never had a tab or preset rows for them; it only wrote empty lists), the rule and zone parts of `StructureInteractionService` and `StructureResolutionResult`,
   the two Applied Section fields and properties, their pass-through in
   `corridor_surface_geometry_service.py`, and the two diagnostics. Tests: the Applied Section and
   Structure object tests lose the rule and zone assertions; a station with a structure no longer
   warns; an old payload with the fields restores.
2. **Culvert (done 2026-11-08).** Remove the `culvert` kind, `CulvertGeometrySpec` and its rows and validation, the
   "Culvert Crossing" and "Drainage Structures" presets, the culvert paths of the solid, quantity,
   target discovery and watertight code (Watertight Solid stays paused; only these paths and their
   tests go), and reword the Region preset note. A document whose Structure still holds culvert
   rows loses them when next applied, and the editor says so once on opening.

   Done: the `culvert` kind and the other drainage kinds (`inlet`, `outlet`, `headwall`, `manhole`,
   `junction_box`) and native types (`box_culvert`, `pipe_culvert`, `inlet`, `outlet`, `headwall`) are
   gone from the Structure editor (kind and native-type choices, the "Culvert Crossing" and
   "Drainage Structures" presets, the detail fields and defaults, the preview shapes and the
   derived connection points), from `CulvertGeometrySpec` and its rows and validation, from the
   solid output (`culvert_body_solid` and the inlet/outlet/headwall bodies), the quantities (the
   six culvert kinds), the solid target discovery (the drainage connection point requirement) and
   Watertight Solid (circular, inlet and headwall bodies and the connection point check of an
   external body). A document saved before keeps its rows until the Structure is applied: the
   editor leaves them out and says so once, validation warns `structure_moved_to_drainage`, and
   `prepare_structure_edit` drops them with their specs and connection points
   (`without_removed_drainage_structures`). The old `CulvertGeometrySpecRows` property goes when
   the object is next written. The Watertight and structure-extension plans still name culvert
   targets; they are paused plans and are corrected if that work resumes.
3. **Connection points.** Remove `StructureConnectionPoint`, its editor tab and preview, its
   diagnostics, and the two requirement checks above; update `scripts/run_local_validation.ps1`.
4. **Documents.** Delete `V1_STRUCTURE_CONNECTION_NODE_PLAN.md`; drop sections 12 and 13 and the
   culvert kind from `V1_STRUCTURE_MODEL.md`; update `V1_STRUCTURE_GEOMETRY_CONTRACT.md`,
   `V1_PERSISTENCE_SCHEMA_INVENTORY.md`, the CHANGELOG, and the line in `AGENTS.md` that says pipes
   wait for the Structure rebuild.

Order matters only between steps 2 and 3: connection points go last because the culvert is what
required them. Step 1 is independent and the smallest, so it goes first.

## 5. Order and gate

DR-6 first, then DS-1, DS-2, DS-3. Each phase ends with the gate in section 9 of the Drainage plan,
a GUI check, a CHANGELOG `[Unreleased]` line and a commit. DS-3 is the large one (the Structure
editor command alone is 2,927 lines) and is done in the four steps of its section, one commit each.

## 6. Non-goals

- Hydraulics and automatic pipe sizing.
- Box culverts, headwalls, wingwalls, manholes and pipe junctions.
- Bridge and retaining wall changes.

## 7. Questions answered on 2026-11-08

- Q1: Saved documents that hold culvert Structures need no migration; the removed rows are dropped.
- Q2: The culvert barrel is the pipe of the culvert point's outgoing link; a culvert has no size
  field of its own.
- Q3: The Region preset text "ditch and culvert references" is reworded in DS-3.

## 8. Open questions

- Q4: Should Quantities and Earthwork take the pipe volumes from the Drainage output, now that the
  culvert quantities go? Proposed: later, as its own step after DS-3; DS-3 only removes.
- Q5: Should `StructureInteractionService` be renamed once it only resolves active structures?
  Proposed: no; the name is exported and used widely, and a rename earns nothing.
