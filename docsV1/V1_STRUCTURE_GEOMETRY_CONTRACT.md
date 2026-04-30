# CorridorRoad V1 Structure Geometry Contract

Date: 2026-04-30
Status: Draft contract
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_STRUCTURE_MODEL.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_CORRIDOR_MODEL.md`
- `docsV1/V1_3D_REVIEW_DISPLAY_PLAN.md`
- `docsV1/V1_QUANTITY_MODEL.md`

## 1. Purpose

This document defines how v1 should represent structure-specific geometry intent.

It exists so bridges, culverts, retaining walls, and similar corridor structures can be authored with useful dimensions without turning generated 3D shapes into source truth.

## 2. Scope

This contract covers:

- structure geometry source parameters
- kind-specific geometry specs
- 3D review preview behavior
- later corridor solid and quantity handoff
- validation expectations

This contract does not cover:

- full bridge design or structural analysis
- reinforcement detailing
- arbitrary BIM authoring
- manual editing of generated preview geometry
- final IFC property-set mapping

## 3. Core Rule

`StructureModel` owns structure identity, placement, interaction, and geometry intent.

Generated structure preview solids, corridor solids, meshes, and exchange geometry are derived outputs.

They must not become the durable editing source.

## 4. Source Ownership

The ownership boundary is:

- `StructureRow` owns identity, kind, role, placement, reference mode, and geometry spec reference.
- `StructurePlacement` owns station range, offset, elevation reference, and orientation mode.
- `StructureGeometrySpec` owns dimensions and kind-specific shape parameters.
- `StructureInteractionRule` owns how the structure affects section and corridor evaluation.
- `StructureInfluenceZone` owns where the interaction applies beyond the physical structure footprint.
- `V1StructureShowPreview` is presentation geometry only.
- future structure corridor solids are output geometry only.

## 5. Design Goals

- Keep structure source rows small enough to scan.
- Keep kind-specific detail editable without crowding the main table.
- Support useful first-slice 3D review for bridges, culverts, and retaining walls.
- Allow later richer geometry without changing the source/output boundary.
- Preserve traceability from preview, AppliedSection, CorridorModel, quantities, and exchange rows back to `structure_id`.
- Allow referenced external geometry through `geometry_ref` without requiring every structure to be natively authored.

## 6. Object Families

Recommended object families:

- `StructureModel`
- `StructureRow`
- `StructurePlacement`
- `StructureGeometrySpec`
- `BridgeGeometrySpec`
- `CulvertGeometrySpec`
- `RetainingWallGeometrySpec`
- `UtilityGeometrySpec`
- `StructurePreviewOutput`
- `StructureSolidOutput`
- `StructureQuantityFragment`

The first implementation may store geometry spec fields as normalized parameter rows before dedicated dataclasses are introduced.

## 7. Root Fields

`StructureModel` should add or reference:

- `geometry_spec_rows`
- `geometry_profile_rows`
- `clearance_envelope_rows`
- `source_refs`
- `diagnostic_rows`

`StructureRow` should include:

- `structure_id`
- `structure_kind`
- `structure_role`
- `placement`
- `geometry_spec_ref`
- `geometry_ref`
- `reference_mode`
- `notes`

`geometry_ref` points to external or detailed geometry.

`geometry_spec_ref` points to native v1 source dimensions.

## 8. Common Geometry Fields

Every native structure geometry spec should support:

- `geometry_spec_id`
- `structure_ref`
- `shape_kind`
- `width`
- `height`
- `length_mode`
- `skew_angle_deg`
- `vertical_position_mode`
- `base_elevation`
- `top_elevation`
- `material`
- `style_role`
- `notes`

Recommended `length_mode` values:

- `station_range`
- `explicit_length`
- `reference_geometry`

Recommended `vertical_position_mode` values:

- `profile_frame`
- `absolute_elevation`
- `terrain_relative`
- `structure_reference`

## 9. Bridge Geometry Spec

Bridge specs should preserve corridor-facing bridge intent.

Recommended fields:

- `deck_width`
- `deck_thickness`
- `girder_depth`
- `barrier_height`
- `clearance_height`
- `abutment_start_offset`
- `abutment_end_offset`
- `pier_station_refs`
- `approach_slab_length`
- `bearing_elevation_mode`

First-slice preview rule:

- show a deck/slab volume along the selected path
- use `deck_width` and `deck_thickness` when present
- use `clearance_height` as a review envelope when present
- do not infer structural adequacy from the preview

## 10. Culvert Geometry Spec

Culvert specs should preserve barrel and crossing intent.

Recommended fields:

- `barrel_shape`
- `barrel_count`
- `span`
- `rise`
- `diameter`
- `wall_thickness`
- `length`
- `invert_elevation`
- `inlet_skew_angle_deg`
- `outlet_skew_angle_deg`
- `headwall_type`
- `wingwall_type`

Recommended `barrel_shape` values:

- `box`
- `circular`
- `pipe_arch`
- `custom_profile`

First-slice preview rule:

- `box` should show a rectangular or hollow-box body when wall thickness is available
- `circular` should show a pipe-like envelope or simplified cylinder
- if detailed shape is not yet implemented, show a clear simplified envelope and emit a review note

## 11. Retaining Wall Geometry Spec

Retaining wall specs should preserve wall body and side intent.

Recommended fields:

- `wall_height`
- `wall_thickness`
- `footing_width`
- `footing_thickness`
- `retained_side`
- `top_elevation_mode`
- `bottom_elevation_mode`
- `batter_slope`
- `coping_height`
- `drainage_layer_ref`

Recommended `retained_side` values:

- `left`
- `right`
- `inside`
- `outside`

First-slice preview rule:

- show a narrow wall volume following the path at the selected offset
- use `retained_side` to orient local review labels and future clearance checks
- do not merge wall behavior into side-slope output without a traceable interaction rule

## 12. Utility Geometry Spec

Utility specs should preserve crossing or longitudinal utility envelopes.

Recommended fields:

- `utility_kind`
- `diameter`
- `duct_width`
- `duct_height`
- `cover_depth`
- `crossing_angle_deg`
- `owner_ref`
- `clearance_margin`

First-slice preview rule:

- show an envelope suitable for clearance and coordination review
- keep utility ownership separate from drainage or structural components unless explicitly linked

## 13. Profiles and Custom Geometry

Some structures need local profile geometry.

Use `geometry_profile_rows` for:

- custom culvert profiles
- variable-height walls
- bridge deck edge profiles
- clearance envelope sections

Recommended profile row fields:

- `profile_row_id`
- `geometry_spec_ref`
- `station`
- `offset_left`
- `offset_right`
- `height`
- `elevation`
- `role`

Custom profile rows are source intent.

Generated polylines and solids are outputs.

## 14. Placement Path Rule

Structure preview and derived solids should follow this path priority:

1. AppliedSection frames or generated 3D Centerline result when available.
2. v1 Alignment evaluation when AppliedSection frames are unavailable.
3. Station/offset fallback only when no evaluated path exists.

The preview should record the path source, for example:

- `3d_centerline`
- `alignment`
- `station_offset_fallback`

A structure should not be represented as one chord rectangle across a curved station range.

It should be sampled along the path and generated as segmented output geometry or a path-following sweep.

## 15. Editor UX

The v1 Structures editor should use:

- a compact structure list table
- a selected-structure detail panel
- kind-specific geometry controls
- validation and 3D review actions

Main table fields:

- `Structure Id`
- `Kind`
- `Role`
- `Start STA`
- `End STA`
- `Offset`
- `Geometry Ref`
- `Notes`

Detail panel fields should change by `structure_kind`.

Do not place every possible bridge, culvert, and wall field in the main table.

## 16. Preview and Output Rule

`V1StructureShowPreview` is a review output.

It may:

- show simplified geometry
- follow 3D Centerline or Alignment
- expose path source and structure count
- be selected and fit in the 3D view

It must not:

- become the editable source
- hide missing geometry spec fields
- silently replace corridor build solids
- drive quantities directly without normalized output rows

Future `StructureSolidOutput` should be generated from the same source specs but can use richer geometry than the review preview.

## 17. Relationship to AppliedSection

`AppliedSection` should receive structure context through evaluation results.

It may store:

- active `structure_ids`
- active interaction rule ids
- active influence zone ids
- clearance diagnostics
- structure-specific component or point roles where relevant

It should not store editable structure geometry.

## 18. Relationship to CorridorModel

`CorridorModel` should consume resolved structure interaction and geometry specs to create corridor outputs.

Possible outputs:

- bridge deck solids
- culvert bodies
- retaining wall solids
- clearance envelopes
- structure-adjacent surface splits
- structure quantity fragments

Corridor build code should not invent new structure meaning from preview objects.

## 19. Relationship to Quantities

Structure quantities should be traceable to:

- `structure_id`
- `geometry_spec_id`
- output object id
- station range
- material

Recommended first quantity kinds:

- `bridge_deck_volume`
- `culvert_body_volume`
- `culvert_opening_area`
- `wall_face_area`
- `wall_body_volume`
- `clearance_envelope_conflict_count`

Quantities should consume normalized output fragments, not raw viewer geometry.

## 20. Diagnostics

Diagnostics should be emitted when:

- a geometry spec is missing for a native structure
- required kind-specific fields are missing
- dimensions are zero or negative
- `station_end` is before `station_start`
- path source falls back to `station_offset_fallback`
- a skew angle is unsupported by the current preview builder
- a referenced external geometry object cannot be found
- a structure has both native spec and external reference with conflicting modes

Recommended diagnostic fields:

- `diagnostic_id`
- `severity`
- `kind`
- `structure_ref`
- optional `geometry_spec_ref`
- optional `station`
- `message`
- `notes`

## 21. Implementation Order

Recommended implementation order:

1. Add normalized geometry spec storage to `StructureModel`.
2. Add common fields: width, height, skew, vertical position mode.
3. Add kind-specific specs for bridge, culvert, and retaining wall.
4. Add selected-row detail panel in the Structures editor.
5. Make `V1StructureShowPreview` read geometry specs.
6. Add validation for required fields by kind.
7. Add AppliedSection structure-context rows.
8. Add corridor structure solid outputs.
9. Add structure quantity fragments.
10. Add exchange mapping for structure output geometry.

## 21.1 Execution Breakdown

Current execution status:

- [x] Step 1: Add normalized geometry spec storage to `StructureModel`.
  - Add a traceable `geometry_spec_ref` from `StructureRow` to native geometry source rows.
  - Add `StructureGeometrySpec` as the first normalized source row for common geometry dimensions.
  - Persist geometry spec rows on the FreeCAD v1 Structure source object.
  - Round-trip geometry spec rows through `to_structure_model`.
  - Keep generated preview geometry as an output, not the source.
- [x] Step 2: Add common editable fields.
  - Expose `width`, `height`, `skew_angle_deg`, and `vertical_position_mode` in source editing flows.
  - Preserve `length_mode`, elevation fields, material, style role, and notes.
  - Validate zero or negative dimensions once the editor can author them.
- [x] Step 3: Add kind-specific specs.
  - Add bridge deck, girder, barrier, clearance, and support fields.
  - Add culvert barrel, wall, invert, inlet, outlet, headwall, and wingwall fields.
  - Add retaining wall body, footing, side, batter, coping, and drainage reference fields.
- [x] Step 4: Add selected-row detail panel.
  - Keep the main Structures table compact.
  - Show kind-specific geometry controls only for the selected structure.
  - Preserve same-row selection after apply and rebuild where practical.
- [x] Step 5: Make `V1StructureShowPreview` read geometry specs.
  - Use native spec dimensions before fallback preview sizes.
  - Report path source and unsupported simplifications as review diagnostics.
  - Keep preview objects marked as presentation output.
- [x] Step 6: Add validation for required fields by kind.
  - Emit diagnostics for missing native specs, missing required fields, invalid dimensions, unsupported skew, and reference conflicts.
  - Keep validation messages traceable to `structure_id` and `geometry_spec_id`.
- [x] Step 7: Add AppliedSection structure-context rows.
  - Pass active structures, interaction rules, influence zones, and clearance diagnostics through evaluation results.
  - Do not copy editable geometry into `AppliedSection`.
- [x] Step 8: Add corridor structure solid outputs.
  - Generate bridge, culvert, wall, clearance, and adjacent-surface outputs from source specs and resolved interactions.
  - Keep corridor build code from inventing structure meaning from preview geometry.
- [x] Step 9: Add structure quantity fragments.
  - Normalize quantities by `structure_id`, `geometry_spec_id`, output id, station range, and material.
  - Consume output fragments rather than raw viewer geometry.
- [x] Step 10: Add exchange mapping for structure output geometry.
  - Map normalized structure outputs into exchange packages.
  - Preserve source traceability and external reference identity.

## 21.2 Workflow Hookup

Current execution status:

- [x] Add a Build Corridor helper for structure output handoff.
  - Resolve `AppliedSectionSet`, `CorridorModel`, and `StructureModel` from the active document.
  - Build `StructureSolidOutput` from source geometry specs.
  - Build structure quantity fragments from normalized solid output rows.
  - Map structure solids and quantity output into one exchange package.
  - Keep this as a workflow handoff helper, not a geometry editor or preview mutation path.
- [x] Expose the structure output package from the Build Corridor panel.
  - Add a user-facing action that builds structure solids, quantities, and exchange output after corridor review inputs exist.
  - Report output ids and counts in the panel summary.
  - Keep package results in command state until a dedicated persisted output/export command is added.
- [x] Persist the structure output package as a v1 `ExchangePackage` object.
  - Store exchange metadata, payload rows, output ids, and source/result refs on a document object.
  - Route the object to `09_Outputs & Exchange / Exchange Packages`.
  - Keep persisted payloads derived from normalized outputs, not preview geometry.
- [x] Add a JSON export adapter for persisted structure exchange packages.
  - Export the persisted `ExchangePackage` snapshot, including exchange metadata, structure solid rows, and quantity fragment rows.
  - Add a Build Corridor panel action for JSON export.
  - Keep this as a normalized package export, not a full IFC writer.
- [x] Add an IFC4 handoff adapter for persisted structure exchange packages.
  - Consume normalized structure solid rows from the persisted `ExchangePackage`.
  - Emit deterministic `IfcBuildingElementProxy` rows with CorridorRoad property sets.
  - Add a Build Corridor panel action for IFC export.
- [x] Add basic IFC shape representations.
  - Emit local placement, rectangle profile, extruded solid, shape representation, and product definition shape rows.
  - Derive swept dimensions from normalized structure solid width, height, and length.
  - Keep property sets as the traceable engineering payload.
- [x] Orient IFC shape placement from evaluated 3D centerline context.
  - Carry placement x, y, z, and tangent direction through normalized structure solid rows.
  - Interpolate placement from AppliedSection frames when 3D centerline context exists.
  - Use IFC local placement reference direction for structure tangent orientation.

## 21.3 Remaining Work Plan

The remaining Structure work should proceed in small slices that preserve the v1 source/result/output boundary.

Do not make generated preview or export geometry editable source state.

### Phase 1: Start/End Frame Output

Status: completed.

Purpose:

- Make each structure output row reconstructable across its full station range.
- Support curved or changing-tangent alignments without relying on one anchor placement.

Scope:

- Add `start_x`, `start_y`, `start_z`, `end_x`, `end_y`, `end_z`.
- Add `start_tangent_direction_deg` and `end_tangent_direction_deg`.
- Keep existing `placement_x`, `placement_y`, `placement_z`, and `tangent_direction_deg` as the anchor placement.
- Build these fields from AppliedSection frame interpolation.
- Fall back to station-range coordinates when AppliedSections are unavailable.

Acceptance criteria:

- A structure crossing two AppliedSection frames records both start and end frame coordinates.
- Existing exchange payloads include the new fields.
- IFC export preserves start/end frame fields in CorridorRoad property sets.

### Phase 2: Segmented Structure Geometry

Status: completed.

Purpose:

- Represent structure ranges that cross curved or changing-tangent alignments more honestly.
- Avoid pretending a long curved bridge or wall is one straight extrusion when enough frame context exists.

Scope:

- Split long structure solids into station segments using available AppliedSection frames.
- Emit segment rows or child geometry rows linked to the parent `structure_id`.
- Keep parent structure source rows unchanged.
- Add diagnostics when segmentation falls back to a single straight extrusion.

Acceptance criteria:

- A structure spanning multiple frames produces traceable segment metadata.
- Segment geometry remains output-only.
- Quantity totals still aggregate back to the parent `structure_id`.

### Phase 3: IFC Shape Refinement

Status: completed.

Purpose:

- Move the IFC handoff from simple rectangular swept solids toward reviewable corridor-following geometry.

Scope:

- Consume start/end or segment geometry from `StructureSolidOutput`.
- Export segmented swept solids for curved/path-following structure rows.
- Preserve `IfcBuildingElementProxy` and CorridorRoad property sets until a stricter IFC class mapping is ready.
- Add explicit export diagnostics for simplified geometry.

Acceptance criteria:

- IFC rows show segment placements and directions where segmentation exists.
- Simplified IFC geometry is clearly labeled in properties or diagnostics.
- Export remains deterministic for contract tests.

### Phase 4: Structure Export Command Separation

Status: completed.

Purpose:

- Reduce Build Corridor panel clutter and make structure export a dedicated workflow.

Scope:

- Move `Build Structure Package`, `Export Package JSON`, and `Export IFC` into a dedicated Structure Output or Exchange command.
- Keep Build Corridor focused on corridor result build and review.
- Preserve a thin bridge from Build Corridor only if it improves handoff.

Acceptance criteria:

- Build Corridor panel has a compact action area.
- Structure package/export workflows remain discoverable from v1 outputs or structures.
- Existing command helpers remain callable for tests and automation.

Completed implementation:

- Add `CorridorRoad_V1StructureOutput` as the dedicated Structure Output command.
- Register Structure Output under the Outputs & Exchange workflow.
- Keep Build Corridor limited to corridor build, review, visibility, and a thin `Structure Output...` handoff.
- Move package build, JSON export, and IFC export panel actions into the Structure Output task panel.
- Preserve top-level structure package/export helpers for tests and automation.

### Phase 5: Validation And Export Readiness

Status: completed.

Purpose:

- Prevent incomplete structure geometry from silently becoming misleading output.

Scope:

- Add export-readiness diagnostics for missing dimensions, missing frame context, zero lengths, unsupported skew, and simplified IFC geometry.
- Separate source validation from output/export validation.
- Surface readiness state in Structure editor and export command.

Acceptance criteria:

- Missing required geometry blocks export or emits explicit warnings according to severity.
- Diagnostics identify `structure_id`, `geometry_spec_id`, and output row id.
- Users can see why a structure exported as a simplified proxy or segment.

Completed implementation:

- Add output/export-readiness diagnostics to `StructureSolidOutput`.
- Diagnose missing or invalid output dimensions, zero output length, missing frame context, unsupported skew, simplified IFC proxy geometry, and segmented proxy geometry.
- Persist export readiness status, diagnostic count, and diagnostic rows on the v1 `ExchangePackage` object.
- Include export diagnostics in normalized JSON exchange payloads.
- Block IFC export when readiness diagnostics contain errors.
- Add IFC property-set fields for export readiness status, diagnostic count, and diagnostic kinds.
- Surface readiness status and diagnostic counts in the Structure Output command.
- Surface the last persisted export-readiness state in the Structure editor status text.

### Phase 6: Kind-Specific Quantity Detail

Status: completed.

Purpose:

- Make quantities useful for bridge, culvert, and retaining-wall review instead of only envelope volume.

Scope:

- Split bridge quantities into deck, girder, barrier, approach slab, and support placeholders where source fields exist.
- Split culvert quantities into barrel, opening, wall, headwall, and wingwall placeholders.
- Split retaining wall quantities into wall body, footing, coping, and drainage layer placeholders.
- Keep every quantity fragment traceable to source geometry specs and output solids.

Acceptance criteria:

- Quantity output exposes kind-specific fragment rows.
- Aggregate totals still match parent structure totals.
- Missing optional detail fields do not invent engineering quantities.

Completed implementation:

- Pass `StructureModel` source specs into structure quantity building.
- Preserve parent structure body/deck/barrel volume fragments from normalized structure solid outputs.
- Add bridge detail fragments when source fields exist:
  - `bridge_deck_volume`
  - `bridge_girder_depth_length`
  - `bridge_barrier_face_area`
  - `bridge_approach_slab_area`
  - `bridge_support_count`
- Add culvert detail fragments when source fields exist:
  - `culvert_barrel_volume`
  - `culvert_opening_area`
  - `culvert_barrel_count`
  - `culvert_wall_volume`
  - `culvert_headwall_count`
  - `culvert_wingwall_count`
- Add retaining-wall detail fragments when source fields exist:
  - `wall_body_volume`
  - `wall_footing_volume`
  - `wall_coping_volume`
  - `wall_drainage_layer_length`
- Carry `structure_ref` through quantity output fragment rows for traceability.

### Phase 7: Persistence Scaling

Status: completed.

Purpose:

- Avoid overloading FreeCAD string properties as exchange packages grow.

Scope:

- Review `ExchangePackage` JSON property size limits.
- Decide whether large payload rows should become child output objects, document attachments, or external package files.
- Keep source/result/output identity stable across save and reload.

Acceptance criteria:

- Large structure packages can be persisted without truncating payload data.
- Export can rebuild from persisted package data.
- The v1 project tree still routes packages under Outputs & Exchange.

Completed implementation:

- Add chunked JSON payload persistence for large `ExchangePackage` sections.
- Keep small payloads in inline JSON string properties for simple inspection and backward compatibility.
- Store large payload sections in `PropertyStringList` chunk properties:
  - `PayloadMetadataJsonChunks`
  - `FormatPayloadJsonChunks`
  - `StructureSolidRowsJsonChunks`
  - `StructureSolidSegmentRowsJsonChunks`
  - `ExportDiagnosticRowsJsonChunks`
  - `QuantityFragmentRowsJsonChunks`
- Store `PayloadStorageMode` and `PayloadByteCount` on the persisted exchange package.
- Make JSON and IFC export rebuild payloads from chunks before falling back to inline JSON.
- Verify chunked payloads survive FCStd save and reload.
- Keep exchange packages routed through the existing Outputs & Exchange tree path.

## 22. Acceptance Criteria

First-slice implementation is acceptable when:

- structure source rows can store kind-specific dimensions
- each supported kind has visible 3D review geometry
- preview geometry follows 3D Centerline when AppliedSections exist
- preview geometry follows Alignment when AppliedSections do not exist
- missing geometry fields produce diagnostics rather than silent defaults
- Cross Section Viewer source ownership still resolves to `StructureModel`
- generated preview objects remain clearly marked as outputs

## 23. Non-goals

This contract does not make CorridorRoad a structural design package.

It does not replace bridge, culvert, or retaining wall engineering tools.

It does not require exact final construction geometry for the first v1 slice.

It does not allow users to edit generated structure preview solids as source.

## 24. Summary

Structure geometry in v1 should be authored as normalized source intent and consumed by evaluation, review, corridor build, quantities, and exchange outputs.

The immediate next step is to review the completed structure geometry sequence as a whole and decide whether to start a polish pass, broader integration tests, or the next v1 domain.

The preview should stay lightweight, traceable, and rebuildable from `StructureModel`.
