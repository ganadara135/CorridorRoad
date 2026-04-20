<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Structure In Sections Plan

## Goal
Add structured infrastructure input to the section-generation workflow without overloading the current `Generate Sections` panel.

See also:
1. `docs/STRUCTURE_SECTION_EXECUTION_PLAN.md` for file-by-file implementation tasks.
2. `docs/CORRIDOR_STRUCTURE_NOTCH_PLAN.md` for corridor-level `skip_zone` / `notch` / `boolean_cut` roadmap.

The immediate target is:
1. Define structure data explicitly.
2. Merge structure-driven stations into `SectionSet`.
3. Tag and optionally modify section results where structures are active.

This is still primarily a section-aware structure handling plan.
However, the plan now includes a staged 3D geometry roadmap so the same `StructureSet`
can evolve from simple visual placeholders to reusable parametric or external structure models.

## Current Implementation Status

Already implemented:
1. `StructureSet` object exists.
2. `Edit Structures` task panel exists.
3. project-tree adoption under `Inputs/Structures` exists.
4. basic 3D display exists using simple alignment-based solids.

Sprint status:
1. `Sprint 1` is functionally complete.
2. automated/runtime verification is still pending.

Not yet implemented:
1. `SectionSet` structure-link integration
2. structure station merge into section generation
3. structure-tagged child sections
4. template-based complex structure geometry
5. external structure-shape linking

## Current Baseline

Current `SectionSet` support is limited to:
1. `IncludeStructureStations`
2. `StructureStationText`

This means the code already supports "merge extra structure-related stations into the section list", but only as free-form text.
That is the correct insertion point for the next step.

## Design Principle

Keep structure data separate from section-generation settings.

Recommended ownership split:
1. `StructureSet`
   - owns structure definitions
   - import/edit/report source of truth
2. `SectionSet`
   - resolves active structures by station
   - merges key stations
   - tags section outputs
   - optionally applies structure-specific overrides

This avoids turning `Generate Sections` into a large data-entry form.

## Recommended Scope

### Phase 1 scope
Support structure-aware sections for:
1. crossing structure
2. culvert / box
3. retaining wall
4. bridge zone / abutment zone

### Not in Phase 1
1. boolean subtraction from corridor solids
2. full bridge or culvert production modeling
3. automatic design grading around complex structure solids

## Proposed Object Model

### 1. StructureSet
New document object under `Inputs/Structures`.

Suggested role:
1. container of structure records
2. import target for CSV later
3. shared source for `SectionSet`

Suggested top-level properties:
1. `StructureIds` (`App::PropertyStringList`)
2. `StructureTypes` (`App::PropertyStringList`)
3. `StartStations` (`App::PropertyFloatList`)
4. `EndStations` (`App::PropertyFloatList`)
5. `CenterStations` (`App::PropertyFloatList`)
6. `Sides` (`App::PropertyStringList`)
7. `Offsets` (`App::PropertyFloatList`)
8. `Widths` (`App::PropertyFloatList`)
9. `Heights` (`App::PropertyFloatList`)
10. `BottomElevations` (`App::PropertyFloatList`)
11. `Covers` (`App::PropertyFloatList`)
12. `RotationsDeg` (`App::PropertyFloatList`)
13. `BehaviorModes` (`App::PropertyStringList`)
14. `Notes` (`App::PropertyStringList`)
15. `Status` (`App::PropertyString`)
16. `GeometryModes` (`App::PropertyStringList`) for future shape strategy
17. `TemplateNames` (`App::PropertyStringList`) for library-based geometry
18. `ShapeSourcePaths` (`App::PropertyStringList`) for external-shape placement
19. `ScaleFactors` (`App::PropertyFloatList`) for external-shape scaling

Recommended behavior-mode values:
1. `tag_only`
2. `section_overlay`
3. `assembly_override`

Recommended geometry-mode values:
1. `box`
2. `template`
3. `external_shape`

### 2. SectionSet additions
Keep backward compatibility, but shift the primary workflow to a linked structure source.

Suggested new properties:
1. `StructureSet` (`App::PropertyLink`)
2. `UseStructureSet` (`App::PropertyBool`)
3. `IncludeStructureStartEnd` (`App::PropertyBool`)
4. `IncludeStructureCenters` (`App::PropertyBool`)
5. `StructureBufferBefore` (`App::PropertyFloat`)
6. `StructureBufferAfter` (`App::PropertyFloat`)
7. `CreateStructureTaggedChildren` (`App::PropertyBool`)
8. `ApplyStructureOverrides` (`App::PropertyBool`)
9. `ResolvedStructureCount` (`App::PropertyInteger`)
10. `ResolvedStructureTags` (`App::PropertyStringList`)

Backward compatibility policy:
1. Keep `IncludeStructureStations`
2. Keep `StructureStationText`
3. If `UseStructureSet=False`, old text-based station merge still works

## Suggested Record Schema

Each structure record should be interpretable at section time without needing a full solid model.

Recommended logical fields:
1. `Id`
2. `Type`
3. `StartStation`
4. `EndStation`
5. `CenterStation`
6. `Side`
7. `Offset`
8. `Width`
9. `Height`
10. `BottomElevation`
11. `Cover`
12. `RotationDeg`
13. `BehaviorMode`
14. `Notes`
15. `GeometryMode`
16. `TemplateName`
17. `ShapeSourcePath`
18. `ScaleFactor`

Field meaning:
1. `StartStation` / `EndStation`
   - active structure range on alignment
2. `CenterStation`
   - used for a key tagged section
3. `Side`
   - `left`, `right`, `center`, `both`
4. `Offset`
   - transverse offset from centerline
5. `Width`
   - transverse width or effective influence width
6. `Height`
   - section overlay height or envelope height
7. `BottomElevation`
   - optional explicit invert/base elevation
8. `Cover`
   - optional burial/depth-like control if `BottomElevation` is absent
9. `GeometryMode`
   - how the 3D shape is produced
10. `TemplateName`
   - parametric library type such as culvert or retaining wall template
11. `ShapeSourcePath`
   - path to external STEP/BREP/FreeCAD source geometry
12. `ScaleFactor`
   - optional scale for imported external geometry

## UI Placement Plan

### 1. New task panel: `Edit Structures`
Recommended new menu/panel, separate from `Generate Sections`.

Purpose:
1. create/edit/import structure records
2. validate structure ranges
3. preview active ranges

Recommended controls:
1. structure table
2. add/remove/sort rows
3. import CSV
4. create/update `StructureSet`
5. optional quick filters by type

### 2. Changes to `Generate Sections`
Keep this panel as a generator, not as the main structure editor.

Recommended additions:
1. `Use StructureSet`
2. `Structure Source`
3. `Include start/end stations`
4. `Include center stations`
5. `Buffer before`
6. `Buffer after`
7. `Create structure-tagged child sections`
8. `Apply structure overrides`

Recommended removal over time:
1. de-emphasize `StructureStationText`
2. mark it as legacy/manual fallback in the UI

## Section Resolution Rules

### Station merge rule
When `UseStructureSet=True`, the section station list should be merged with:
1. structure start station
2. structure end station
3. structure center station
4. optional pre-buffer station
5. optional post-buffer station

This should happen after base range/manual station resolution, but before dedup/sort finalization.

### Section tagging rule
Each resolved station may receive tags such as:
1. `[STR]`
2. `[STR_START]`
3. `[STR_CENTER]`
4. `[STR_END]`

If more than one structure is active, section metadata should record all contributing structure IDs.

### Child section metadata
Suggested child section properties:
1. `StructureIds`
2. `StructureTypes`
3. `SectionRole`
4. `HasStructure`

This is important because later corridor, reports, and quantity logic can use these tags.

## Geometry Behavior Plan

### Stage A: simple 3D visualization
This is the current implementation baseline.

Behavior:
1. create simple alignment-based box solids in 3D view
2. use `StartStation`/`EndStation`, `Width`, `Height`, `Offset`, `RotationDeg`
3. give users immediate spatial feedback before section integration exists

Purpose:
1. validate station range placement
2. validate side and offset direction
3. keep implementation low-risk while structure data model stabilizes

### Stage B: tag and overlay in sections
At first, structure handling should not change corridor generation globally.

Behavior:
1. add structure stations
2. tag sections
3. optionally draw structure envelope lines/markers in section children

This gives visibility without destabilizing loft generation.

### Stage C: template-driven geometry
After basic section-aware handling works, expand geometry from `box` to `template`.

Recommended initial templates:
1. `box_culvert`
2. `retaining_wall`
3. `abutment_zone`

Template behavior:
1. use structure parameters plus template-specific dimensions
2. generate more realistic solids than simple boxes
3. remain parametric and reproducible from CSV/UI data

### Stage D: local section overrides
Enable controlled template overrides when a structure is active.

Possible overrides:
1. local width override
2. side-slope suppression
3. daylight suppression in a structure zone
4. alternate depth/height rules

These overrides should be explicit and opt-in per structure behavior mode.

### Stage E: external shape linking
For detailed or custom structures, support direct placement of external geometry.

Recommended behavior:
1. load STEP/BREP/FreeCAD-based source geometry
2. place the shape by station, side, offset, elevation, and rotation
3. preserve alignment-aware placement rules

This is the preferred route for highly detailed bridge components or nonstandard structures.

### Stage F: downstream consumers
Only after section behavior is stable:
1. corridor loft can optionally skip or segment structure zones differently
2. design grading surface can optionally exclude structure void zones
3. reports can summarize structures by station range

See `docs/CORRIDOR_STRUCTURE_NOTCH_PLAN.md` for the recommended expansion order:
1. `split_only`
2. `skip_zone`
3. `notch`
4. later `boolean_cut`

## Recommended Expansion Order

To avoid destabilizing the core corridor workflow, extend structure support in this order:
1. stabilize `StructureSet` editing and simple 3D display
2. connect `StructureSet` to `SectionSet`
3. add structure station merge and child-section metadata
4. add template geometry for `box_culvert` and `retaining_wall`
5. add external shape placement for complex structures
6. only then evaluate corridor/grading consumers

## Recommended Property Names

For consistency with current codebase naming:

### New object
1. `StructureSet`

### New `SectionSet` properties
1. `StructureSet`
2. `UseStructureSet`
3. `IncludeStructureStartEnd`
4. `IncludeStructureCenters`
5. `StructureBufferBefore`
6. `StructureBufferAfter`
7. `CreateStructureTaggedChildren`
8. `ApplyStructureOverrides`
9. `ResolvedStructureCount`
10. `ResolvedStructureTags`

### Child section properties
1. `HasStructure`
2. `StructureIds`
3. `StructureTypes`
4. `StructureRole`

## Validation Rules

Minimum validation needed before generation:
1. `StartStation <= CenterStation <= EndStation` when all three exist
2. no negative width/height
3. side value must be from a fixed allowed set
4. station values must be inside alignment length range
5. behavior mode must be known

Recommended warnings:
1. overlapping structures of incompatible type
2. zero-length structure range
3. structure zone outside section generation range
4. structure override + daylight auto active together

## Implementation Sequence

### Step 1. Data object
1. add `obj_structure_set.py`
2. add basic view provider
3. add helper methods to read normalized records

### Step 2. Editing UI
1. add `task_structure_editor.py`
2. add create/apply/import flow
3. link created object into project `Inputs/Structures`

### Step 3. SectionSet integration
1. add new `SectionSet` link/properties
2. merge structure stations
3. resolve structure tags
4. expose structure info on child sections

### Step 4. Optional section overrides
1. disable daylight in structure zone
2. suppress side slopes or replace with fixed edges
3. add simple envelope overlay

### Step 5. Documentation and samples
1. add sample structure CSV
2. add wiki explanation
3. add regression case with structure-tagged sections

## Testing Strategy

### Required sample scenario
1. one culvert crossing
2. one retaining wall zone
3. one bridge/abutment zone

### Verify
1. structure stations are inserted correctly
2. tags appear on child sections
3. section count is stable and deterministic
4. corridor loft still works outside structure zones
5. daylight does not behave unexpectedly inside override zones

## Recommendation

Do not put full detailed structure editing inside `Generate Sections`.

Best architecture:
1. structure definitions live in `StructureSet`
2. `Edit Structures` manages the data
3. `Generate Sections` only selects the source and decides how to apply it

That keeps the current pipeline readable and makes later structure-aware corridor logic much safer.
