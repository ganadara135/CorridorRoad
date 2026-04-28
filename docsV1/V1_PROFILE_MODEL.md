# CorridorRoad V1 Profile Model

Date: 2026-04-25
Branch: `v1-dev`
Status: Draft baseline, parabolic vertical-curve evaluation complete
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_ALIGNMENT_MODEL.md`
- `docsV1/V1_PROFILE_OUTPUT_SCHEMA.md`
- `docsV1/V1_LANDXML_MAPPING_PLAN.md`
- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`

## 1. Purpose

This document defines the v1 internal source contract for vertical profile design.

It exists to make clear:

- what `ProfileModel` owns
- how profile source data relates to alignment station space
- how PVI, grade, and vertical curve intent should be preserved
- how profile data connects to sections, corridor evaluation, outputs, exchange, and earthwork review

## 2. Scope

This model covers:

- profile identity and source ownership
- station-elevation control data
- PVI and grade-transition intent
- vertical curve intent
- deterministic profile evaluation services
- validation and diagnostic rules

This model does not cover:

- horizontal alignment authoring
- superelevation authoring
- section template authoring
- final sheet layout behavior

## 3. Core Rule

`ProfileModel` is a durable vertical source-of-truth model.

This means:

- corridor evaluation reads from it
- `ProfileOutput` derives from it
- earthwork and mass-haul review may attach to it
- viewers may inspect it
- no derived output becomes the new profile truth

## 4. Relationship to Alignment

`ProfileModel` is defined in the station space established by `AlignmentModel`.

The relationship is:

- `AlignmentModel` owns horizontal station semantics
- `ProfileModel` owns vertical design intent along that station domain

`ProfileModel` must reference `alignment_id` explicitly.

It must not duplicate horizontal geometry internally.

Current implementation note:

- `Plan/Profile Review` exposes bridge diagnostic rows that confirm a v0 `VerticalAlignment` became a v1 `ProfileModel`, that `ProfileModel.alignment_id` matches the active `AlignmentModel.alignment_id`, and that profile control stations fit inside the alignment station range
- `V1Profile` document objects now provide the preferred v1-native profile source path before legacy vertical alignment fallback is used
- the sample v1 profile command creates or reuses a `V1Alignment`, stores profile controls and vertical-curve rows on a `V1Profile`, and routes it to `02_Alignment & Profile / Profiles`
- `Profile` provides the first v1-native tabbed profile editor for FG PVI rows, preset data loading, CSV import/export, editable vertical curve rows, EG reference status, and station-link checks
- `Profile` opens without immediately changing the document when no `V1Profile` exists; `Apply` creates or updates the source object and reports completion to the user
- `Plan/Profile Review` now prefers `V1Alignment` plus `V1Profile` sources when both exist, then falls back to legacy adapter sources only when native v1 sources are absent

## 5. Design Goals

The v1 profile subsystem should:

- preserve true vertical design intent
- support station-aware evaluation
- support PVI-driven authoring
- preserve vertical curve meaning where supported
- support imported and native profiles
- expose deterministic services for corridor, sheet, and earthwork consumers

## 6. Profile Scope in v1

Recommended early v1 support:

- [x] existing ground reference profiles from TIN sampling
- finished grade profiles
- design reference profiles
- PVI-based authoring
- tangent grades
- vertical curves
- [x] station range queries through alignment station sampling

Deferred or later refinements may include:

- richer profile set management
- more specialized jurisdiction-specific labels
- advanced multi-profile dependency automation

## 7. Profile Object Families

Recommended primary object families:

- `ProfileModel`
- `ProfileControlSequence`
- `ProfileControlPoint`
- `VerticalCurveRow`
- `ProfileConstraintSet`
- `ProfileEvaluationResult`
- `V1Profile` FreeCAD document source object

## 8. ProfileModel Root

### 8.1 Purpose

`ProfileModel` is the durable container for one vertical design profile.

### 8.2 Recommended root fields

- `schema_version`
- `profile_id`
- `project_id`
- `alignment_id`
- `label`
- `profile_kind`
- `control_sequence`
- `vertical_curve_rows`
- `constraint_rows`
- `unit_context`
- `coordinate_context`
- `source_refs`
- `diagnostic_rows`

### 8.3 Recommended profile kinds

- `existing_ground`
- `finished_grade`
- `design_reference`
- `temporary_candidate_profile`

### 8.4 Current FreeCAD Source Object

The current v1-native FreeCAD source object is `V1Profile`.

It stores the durable authoring fields needed to rebuild a `ProfileModel`:

- `V1ObjectType`
- `SchemaVersion`
- `ProjectId`
- `ProfileId`
- `AlignmentId`
- `ProfileKind`
- `ControlPointIds`
- `ControlStations`
- `ControlElevations`
- `ControlKinds`
- `VerticalCurveIds`
- `VerticalCurveKinds`
- `VerticalCurveStationStarts`
- `VerticalCurveStationEnds`
- `VerticalCurveLengths`
- `VerticalCurveParameters`

Current routing rule:

- `V1Profile` belongs under `02_Alignment & Profile / Profiles`
- if a sample profile is created without an alignment, the command creates a matching `V1Alignment` first
- downstream review converts `V1Profile` into `ProfileModel` through the v1 object adapter before using legacy profile adapters

Current editor rule:

- `Profile` opens the selected or first document `V1Profile`
- if no `V1Profile` exists, the editor opens from generated `V1Stationing` station rows when available and does not create document objects until `Apply`
- if no generated `V1Stationing` rows exist, the editor leaves the PVI table empty and informs the user to run `Stations` first
- the editor uses one task panel with `FG Profile`, `Vertical Curves`, `EG Reference`, and `Station Check` tabs
- the Profile panel exposes `Preset Data`, `Import CSV`, `Export CSV`, and `Random Elevation` actions above the tab area for v1 PVI/control rows
- `Random Elevation` fills the current station rows with smooth temporary FG elevations so station-generated profile rows can be tested before final design values are entered
- Profile CSV uses `station,elevation,kind` as the standard export schema and accepts v0-style aliases such as `STA`, `FG`, `elevation`, and `z` on import
- repository sample CSVs for manual checks are `tests/samples/profile_v1_pvi_rolling.csv` and `tests/samples/profile_v1_pvi_mountain_valley_plain.csv`
- `EG Reference` is an active TIN reference tab: it lists TIN-capable Mesh/Shape candidates, supports `Use Selected`, samples EG by interval over the current profile station range, and shows station, XY, EG elevation, status, face, and notes rows
- `Station Check` is an active validation tab: it checks current profile station rows against the active `V1Alignment` range and generated `V1Stationing` rows, then reports OK/WARN/ERROR rows before review/corridor handoff
- `Show` creates or updates a reusable framed `Profile Show Preview` sheet in the 3D View from the current editor table without writing the `V1Profile` source object; it draws distance/station along the bottom axis, elevation along the left axis, FG in orange, and TIN-sampled EG in green when a TIN surface is available
- `Show` uses the selected `EG Reference` TIN when one is selected, otherwise it falls back to the first resolvable document terrain/TIN candidate
- `Show` places the framed profile preview away from existing document geometry and switches the 3D View toward Front/selection focus when FreeCAD GUI view controls are available
- in the `Vertical Curves` tab, `Add Curve` inserts a blank manual curve row; it does not infer station values
- the `Vertical Curves.Kind` cell is a combo box; only `Parabolic` is active, while `Crest` and `Sag` show an in-progress message and revert to `Parabolic`
- the `Vertical Curves` tab includes `Auto from PVI`, which creates symmetric parabolic curve rows centered on interior PVI controls using a user-entered default curve length and clamps curve length to nearby tangent clearance
- `Auto from PVI` requires FG Profile station/elevation rows first; station-only rows generated from `Stations` must be completed manually or replaced through `Preset Data` / `Import CSV` before vertical curves can be generated
- `Apply` creates the `V1Profile` when needed and writes sorted PVI/control rows back to the source object
- `Apply` also writes sorted vertical curve rows back to `VerticalCurveIds`, `VerticalCurveKinds`, `VerticalCurveStationStarts`, `VerticalCurveStationEnds`, `VerticalCurveLengths`, and `VerticalCurveParameters`
- vertical-curve apply validation rejects zero-length windows and overlapping curve ranges before writing to `V1Profile`
- duplicate stations are rejected before writing
- `V1Profile` builds a lightweight 3D finished-grade display shape on recompute by sampling the linked `V1Alignment` and evaluated profile elevations; display diagnostics are stored in `DisplayStatus` and `DisplayPointCount`
- `Review Plan/Profile` opens the v1 Plan/Profile Review after the profile has been applied

## 9. ProfileControlSequence

### 9.1 Purpose

`ProfileControlSequence` preserves the ordered station-based control structure of the profile.

### 9.2 Rule

The control sequence must preserve engineering meaning, not just a sampled polyline.

### 9.3 Recommended fields

- `control_sequence_id`
- `profile_id`
- `control_rows`
- `start_station`
- `end_station`
- `notes`

## 10. ProfileControlPoint

### 10.1 Purpose

Each control point represents a meaningful vertical control location in the profile.

### 10.2 Recommended fields

- `control_point_id`
- `control_index`
- `station`
- `elevation`
- `kind`
- `grade_in`
- `grade_out`
- `source_ref`
- `notes`

### 10.3 Recommended kinds

- `pvi`
- `grade_break`
- `reference_point`
- `imported_control_with_diagnostics`

### 10.4 Rule

Control points should preserve authoring intent even when rendered consumers only show simplified profile lines.

## 11. VerticalCurveRow

### 11.1 Purpose

`VerticalCurveRow` preserves transition intent between grades.

### 11.2 Recommended fields

- `vertical_curve_id`
- `kind`
- `station_start`
- `station_end`
- `pvi_ref`
- `curve_length`
- `curve_parameter`
- `source_ref`
- `notes`

### 11.3 Recommended kinds

- `crest_curve`
- `sag_curve`
- `generic_vertical_curve`
- `imported_unknown_vertical_curve`

### 11.4 Rule

Vertical curves should remain identifiable as parametric design elements rather than being flattened into sampled points only.

## 12. ProfileConstraintSet

### 12.1 Purpose

Constraint rows capture vertical-design intent and review context.

### 12.2 Recommended fields

- `constraint_id`
- `kind`
- `value`
- `unit`
- `hard_or_soft`
- `notes`

### 12.3 Recommended kinds

- `max_grade`
- `min_grade`
- `min_vertical_curve_length`
- `protected_station_range`
- `fixed_elevation_control`

## 13. Existing Ground vs Design Profiles

### 13.1 Rule

Existing ground and design profile families should stay explicitly distinguishable.

### 13.2 Why it matters

This distinction is required for:

- corridor evaluation
- profile review
- earthwork balance analysis
- exchange behavior

### 13.3 Recommended policy

`existing_ground` profiles may come from TIN sampling or import normalization.

`finished_grade` and `design_reference` profiles should remain durable design sources.

Current implementation note:

- `ProfileTinSamplingService` samples TIN elevations along an evaluated `AlignmentModel` station grid
- `Plan/Profile Review` can attach sampled TIN rows as `ProfileLineRow(kind="existing_ground_line")`
- no-hit samples keep `elevation=None` and are omitted from EG line segments rather than becoming zero elevation

## 14. Evaluation Services

Recommended service families:

- `ProfileEvaluationService`
- `ProfileSamplingService`
- `ProfileComparisonService`

## 15. ProfileEvaluationService

### 15.1 Purpose

This service evaluates station-based vertical geometry in deterministic form.

Current implementation status:

- [x] station to FG elevation by linear interpolation between ordered profile control points
- [x] station to tangent grade between active control points
- [x] active profile segment metadata for downstream station traceability
- [x] explicit `out_of_range`, `no_controls`, and `duplicate_station` statuses
- [x] active vertical-curve row metadata when the station falls inside a declared curve range
- [x] detailed parabolic vertical-curve elevation and grade evaluation for symmetric PVI-centered curves
- [x] v1-native PVI source edits can update `V1Profile` and feed the same evaluation path

### 15.2 Typical queries

- [x] station to elevation
- [x] station to grade
- [x] station to active control element
- [x] station range to sampled profile line for Plan/Profile Review output

Current vertical-curve behavior:

- `VerticalCurveRow.station_start` and `station_end` are treated as BVC/EVC
- the curve is evaluated as a symmetric parabolic curve centered on a matching PVI
- incoming and outgoing tangent grades come from the neighboring PVI control points, or explicit `grade_in` / `grade_out` where provided
- if the PVI-centered curve cannot be resolved, evaluation falls back to linear interpolation while keeping the active curve metadata visible

### 15.3 Rule

Corridor, section, output, and earthwork consumers should use shared evaluation services rather than interpreting profile geometry independently.

## 16. ProfileSamplingService

### 16.1 Purpose

This service produces sampled line data for review and output without replacing the profile source contract.

### 16.2 Typical consumers

- `ProfileOutput`
- 3D profile overlay
- profile preview tools
- export packaging helpers

Initial implementation status:

- [x] sample alignment stations against TIN XY elevations
- [x] attach EG line rows to `ProfileOutput`
- [x] expose configurable station interval in profile review UI
- [x] sample FG profile lines through `ProfileEvaluationService` so vertical curves affect review lines and earthwork hints
- [ ] support full EG/FG comparison rows

Current interval behavior:

- default Plan/Profile Review station interval is `20.000 m`
- the review panel can reopen itself with a user-selected interval
- the selected interval drives `PlanOutput.station_rows`, compact key-station navigation rows, and TIN-sampled existing-ground profile rows

### 16.3 Rule

Sampled rows are derived output, not authoring truth.

## 17. ProfileComparisonService

### 17.1 Purpose

This service compares multiple profile families in aligned station space.

### 17.2 Typical comparisons

- EG vs FG
- baseline vs candidate profile
- design profile vs constrained alternative

### 17.3 Rule

Comparison results should be explicit result objects or output rows, not hidden renderer-side calculations.

## 18. Validation Rules

Validation should check for:

- broken control ordering
- duplicate or ambiguous stations
- invalid vertical curve ranges
- missing alignment reference
- inconsistent unit or vertical reference
- unsupported imported curve definitions

Validation results should be recorded in `diagnostic_rows`.

## 19. Diagnostics

Diagnostics should be produced when:

- imported profile geometry does not map cleanly
- a vertical curve must be simplified
- control points are incomplete or conflicting
- a station query lands outside a valid profile domain
- profile comparison requires degraded handling

Recommended diagnostic fields:

- `diagnostic_id`
- `severity`
- `kind`
- `source_ref`
- `message`
- `notes`

Focused bridge validation:

```powershell
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_v1_profile_editor.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_profile_evaluation_service.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "ns={}; exec(open(r'tests\contracts\v1\test_alignment_profile_bridge_diagnostics.py', 'r', encoding='utf-8').read(), ns); [fn() for name, fn in sorted(ns.items()) if name.startswith('test_') and callable(fn)]; print('[PASS] v1 alignment/profile bridge diagnostics contract tests completed.')"
```

## 20. Identity and Provenance

Profile objects should preserve:

- stable `profile_id`
- referenced `alignment_id`
- external import identity where relevant
- source file reference
- import or edit provenance
- candidate-vs-approved status where applicable

This is important for:

- `LandXML` exchange
- AI alternative comparison
- earthwork scenario analysis
- profile output traceability

## 21. Relationship to Section and Corridor

`AppliedSection` evaluation depends on `ProfileModel` for:

- design elevation at station
- grade-derived context
- vertical position of section origin

`CorridorModel` must consume evaluated profile data rather than copying or re-deriving profile logic.

## 22. Relationship to Earthwork Balance

`ProfileModel` is a major driver of earthwork behavior.

Earthwork and mass-haul systems may:

- evaluate cut/fill consequences of profile changes
- compare baseline and candidate profiles
- attach derived balance rows to `ProfileOutput`

But they must not overwrite `ProfileModel` directly without explicit accepted source edits.

## 23. Relationship to Outputs

### 23.1 ProfileOutput

`ProfileOutput` should derive from `ProfileModel` plus related comparison and diagnostic context.

It must not become the new authoring source.

### 23.2 SectionOutput

`SectionOutput` depends on the evaluated elevation and station context provided through `ProfileModel`.

### 23.3 Plan/Profile Sheets

Sheet systems may consume sampled and annotated profile output rows, but should not own vertical design truth.

## 24. Relationship to LandXML

`LandXML` profile import should normalize into `ProfileModel`.

`LandXML` profile export should primarily read from:

- `ProfileModel`
- related metadata in `ExchangeOutputSchema`

`ProfileOutput` may support export packaging context, but not replace the source contract.

## 25. AI and Alternative Design

AI-assisted workflows may propose:

- PVI elevation changes
- vertical curve length changes
- profile smoothing candidates
- earthwork-aware alternative profiles

But accepted changes must still be written into normalized profile source objects.

The AI layer must not maintain a separate hidden profile representation.

## 26. Recommended Minimal Schema Version

Recommended initial version:

- `ProfileModelSchemaVersion = 1`

## 27. Anti-Patterns

The following should be avoided:

- storing only sampled FG lines as the profile truth
- letting profile display geometry become the editable source
- duplicating profile evaluation logic across corridor and output code
- hiding vertical-curve degradation
- embedding earthwork analysis results directly into the profile source contract

## 28. Summary

In v1, `ProfileModel` is the durable vertical source contract for:

- station-elevation control
- grade and vertical-curve intent
- profile constraints
- deterministic evaluation

It should remain alignment-referenced and parametric, so that:

- corridor and section evaluation can trust it
- `ProfileOutput` and sheets can derive from it
- `LandXML` exchange can normalize through it
- earthwork balance and AI alternatives can compare against it without replacing it
