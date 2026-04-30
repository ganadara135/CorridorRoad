# CorridorRoad V1 Region Application Flow Plan

## 1. Purpose

This document defines how v1 should organize the authoring flow between `Assembly`, `Structure`, and `Region`.

It also fixes the Region ownership rule:

- one `RegionRow` uses one primary `Assembly`
- one `RegionRow` uses zero or one primary `Structure`

If a corridor range needs a different Assembly or a different Structure, create another Region row.

## 2. Core Rule

Use this authoring order:

1. `Assembly`
2. `Structure`
3. `Region`

`AssemblyModel` and `StructureModel` are reusable source definitions.

`RegionModel` is the station-range application layer that decides where one Assembly and one optional Structure are active.

## 3. Ownership Boundary

`AssemblyModel` owns reusable section composition.

`StructureModel` owns structure identity, placement, geometry intent, interaction policy, and exchange identity.

`RegionModel` owns station-range application, overlap, priority, and handoff context.

Region rows reference source definitions, but they must not copy or redefine those source models.

## 4. One Region Rule

One Region row should answer a simple question:

- from station A to station B, which Assembly is active, and which single Structure affects this range?

The preferred Region row shape is:

- `region_id`
- `station_start`
- `station_end`
- `primary_kind`
- `applied_layers`
- `assembly_ref`
- `structure_ref`
- `drainage_ref`
- `ramp_ref`
- `intersection_ref`
- `policy_set_ref`
- `template_ref`
- `superelevation_ref`
- `override_refs`
- `priority`
- `source_ref`
- `notes`

## 5. Why Region Comes After Assembly and Structure

Regions need to answer station-specific questions:

- Which Assembly is active here?
- Which Structure affects this range?
- Which source should win when Region rows overlap?
- Which source relationships should `AppliedSectionService` and `Build Corridor` consume?

Those questions cannot be answered cleanly until the reusable `AssemblyModel` and `StructureModel` sources already exist.

## 6. Recommended User Flow

The practical v1 workflow should be:

1. Create or import Alignment, Stations, Profile, and TIN context.
2. Create reusable `Assembly` definitions.
3. Create reusable `Structure` definitions.
4. Open `Regions`.
5. Add station ranges.
6. Assign one Assembly to each Region.
7. Assign zero or one Structure to each Region.
8. Validate overlap, priority, and missing references.
9. Generate `Applied Sections`.
10. Build corridor outputs.

## 7. When More Than One Assembly Is Needed

Do not put multiple Assemblies into one Region row.

Use one of these approaches instead:

- split the station range into multiple Region rows
- use `RegionTransition` when the Assembly changes over a transition range
- use `RegionPolicySet` or explicit override refs for narrow component exceptions

This keeps Region resolution deterministic.

## 8. When More Than One Structure Is Needed

Do not put multiple Structures into one Region row.

Use one of these approaches instead:

- split the station range into multiple Region rows
- create overlapping Region rows with different priorities when two structure effects must be reviewed separately
- model minor non-structural effects as `applied_layers` or policy context
- keep the actual structure meaning in `StructureModel`

If two major structures are truly active over the same station range, they should remain separate Region rows so each row has one clear structure owner.

## 9. Compatibility Strategy

The current implementation may still expose list-shaped fields such as:

- `RegionRow.structure_refs`
- `RegionRow.drainage_refs`

During migration, interpret `structure_refs` as a compatibility container.

The intended v1 behavior is:

- zero entries means no active Structure for the Region
- one entry means the Region's active `structure_ref`
- more than one entry should produce a validation diagnostic

New code should prefer a singular `structure_ref` concept even if the storage bridge still uses `structure_refs`.

`assembly_ref` remains singular.

## 10. Resolution Rules

Region resolution should happen in this order:

1. Resolve active `RegionRow` candidates by station.
2. Sort candidate Regions by priority and region index.
3. Read the winning Region's `assembly_ref`.
4. Read the winning Region's singular active `structure_ref`.
5. Preserve non-winning overlaps as diagnostics.
6. Return a normalized handoff payload for `AppliedSectionService`, `Build Corridor`, viewers, and exchange flows.

The handoff should expose:

- active Region id
- active Assembly ref
- active Structure ref
- active layers
- unresolved references
- overlap diagnostics
- source traceability rows

## 11. Region Editor Direction

The Region editor should remain a station-range application editor.

It should not become the Assembly editor or Structure editor.

Recommended UI structure:

- one main Region table
- one `Assembly` column
- one `Structure` column
- context columns for layers, drainage, ramp, intersection, policy, and notes
- validation summary
- source handoff summary

The editor may keep list-like compatibility storage internally, but the user-facing Region row should present one Assembly and one optional Structure.

## 12. Implementation Order

### Phase RAF1: Document and Contract Alignment

Tasks:

- [x] document the `Assembly -> Structure -> Region` authoring order
- [x] define one Assembly per Region
- [x] define zero or one Structure per Region
- [x] update `V1_REGION_MODEL.md` to reference this flow
- [x] register this plan in `docsV1/README.md`
- [x] update implementation checklists with singular Structure follow-ups

Acceptance criteria:

- [x] docs state that Region applies one Assembly source
- [x] docs state that Region applies zero or one Structure source
- [x] docs keep Assembly and Structure ownership outside Region

### Phase RAF2: Source Model Alignment

Tasks:

- [x] add or expose a singular `structure_ref` concept
- [x] keep `structure_refs` as compatibility storage during migration
- [x] validate that `structure_refs` has at most one active entry
- [x] keep `assembly_ref` singular
- [x] add focused model contract tests

Acceptance criteria:

- [x] one Region can store one Assembly ref
- [x] one Region can store zero or one Structure ref
- [x] more than one Structure ref produces a diagnostic
- [x] compatibility `structure_refs` still round-trips

### Phase RAF3: Validation and Resolution

Tasks:

- [x] validate unknown Assembly refs against available Assembly source ids
- [x] validate unknown Structure refs against available Structure source ids
- [x] validate missing Structure refs when `primary_kind` requires a Structure
- [x] validate more than one active Structure ref as an error or warning
- [x] resolve active Assembly by winning Region row
- [x] resolve active Structure by winning Region row

Acceptance criteria:

- [ ] overlapping Region rows resolve deterministically
- [x] one winning Region returns one Assembly ref
- [x] one winning Region returns zero or one Structure ref
- [x] diagnostics explain missing Assembly and Structure source refs when known source ids are provided
- [x] diagnostics explain when bridge, culvert, or structure influence Regions are missing `structure_ref`
- [x] diagnostics explain conflicting Structure refs

### Phase RAF4: Region Editor

Tasks:

- [x] keep one Region table as the primary UI
- [x] expose one Assembly selector per Region row
- [x] expose one Structure selector per Region row
- [x] preserve existing simple Region table workflow
- [x] show compatibility warnings when stored Structure data has more than one ref
- [x] show missing or unknown Structure refs in Region editor validation output

Acceptance criteria:

- [x] a user can assign one Assembly to one Region
- [x] a user can assign one Structure to one Region
- [x] applying changes updates one durable v1 Region source object

### Phase RAF5: Downstream Consumers

Tasks:

- [x] pass resolved Assembly ref into `AppliedSectionService`
- [x] pass resolved Structure ref into `AppliedSectionService`
- [x] filter structure interaction context by resolved Region `structure_ref`
- [x] keep quantity fragments singular when component compatibility rows contain multiple structure ids
- [x] pass resolved Structure ref into structure output filtering
- [x] show singular Assembly and Structure ownership in Cross Section Viewer source rows
- [x] include singular Region source refs in review and exchange diagnostics where relevant

Acceptance criteria:

- [x] Applied Sections can explain which Assembly was used
- [x] Applied Sections can carry the resolved singular Structure context
- [x] Build Corridor summary can report active Structure ownership from Applied Sections
- [x] Cross Section Viewer can show the active Structure for a station
- [x] Structure output and exchange payloads can carry singular `region_ref`, `assembly_ref`, and `structure_ref` context rows

## 13. Non-goals

This plan does not make Region own Assembly component geometry.

This plan does not make Region own Structure geometry.

This plan does not introduce multiple Assembly applications inside one Region.

This plan does not introduce multiple Structure applications inside one Region.

This plan does not require corridor solids before source and result contracts are stable.
