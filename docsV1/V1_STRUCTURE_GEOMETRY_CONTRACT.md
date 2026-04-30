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

The immediate next step is to add kind-specific geometry specs and a detail panel to the v1 Structures editor.

The preview should stay lightweight, traceable, and rebuildable from `StructureModel`.
