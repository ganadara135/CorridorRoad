# CorridorRoad V1 Alignment Model

Date: 2026-04-25
Branch: `v1-dev`
Status: Draft baseline, v0-style Alignment UI migrated into v1 entrypoint
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_LANDXML_MAPPING_PLAN.md`
- `docsV1/V1_PLAN_OUTPUT_SCHEMA.md`
- `docsV1/V1_SECTION_MODEL.md`

## 1. Purpose

This document defines the v1 internal source contract for horizontal alignment.

It exists to make clear:

- what `AlignmentModel` owns
- which object families belong inside the alignment subsystem
- how station evaluation should work
- how alignment interacts with profiles, sections, outputs, and exchange

Current implementation note:

- `AlignmentEvaluationService.evaluate_station()` resolves station to active element, XY, tangent direction, and offset-on-element for tangent or sampled-polyline geometry
- `AlignmentEvaluationService.station_offset_to_xy()` provides the shared station/offset frame needed by section, TIN, and corridor consumers
- `AlignmentStationSamplingService.sample_alignment()` and `sample_range()` generate shared evaluated station grids over an alignment range
- `V1Alignment` FreeCAD source objects can store the minimal v1 `AlignmentModel` contract directly in document properties
- the visible workbench Alignment entrypoint is now a single `Alignment` command backed by the v1 alignment editor
- the single `Alignment` command opens the editor without immediately changing the document when no `V1Alignment` exists
- the v1 alignment editor now uses the v0-style PI workflow as the primary UI: sketch import, CSV import/export, presets, X/Y, radius, transition length, and geometry/criteria controls
- `Apply` creates a `V1Alignment` when needed, stores the PI/criteria input, compiles it into v1 station geometry rows for downstream tools, and reports completion to the user
- PI rows with radius now compile into tangent plus sampled curve geometry, so v1 station evaluation follows a curved XY path instead of a simple PI chord
- transition length input now compiles into approximate S-C-S sampled geometry using linear curvature ramps; full analytic clothoid objects remain planned
- `V1AlignmentObject.execute()` now builds a FreeCAD display `Shape` from compiled v1 geometry rows so alignment edits are visible in the model view after recompute
- `Review Alignment` now reports PI-level curve review rows with input/applied R/Ls, clamp status, approximate TS/SC/CS/ST stations, curve length, and point count
- `Stations` opens the unified v1 stationing workflow without immediately changing the document
- `Apply` in the `Stations` panel creates or updates a `V1Stationing` object from `AlignmentStationSamplingService` and stores station, XY, tangent, active-element, and source-reason rows
- `Apply` in the `Stations` panel includes curve/transition midpoint stations so generated stationing rows expose non-tangent alignment zones
- `V1Stationing` stores source geometry signature, element-count metadata, active-element kind summary, curve/transition station counts, and compact station review rows
- `V1Stationing` now builds FreeCAD tick display geometry from sampled XY/tangent rows and classifies stations as key, major, or minor
- `V1Stationing` supports station display offset and label formats including decimal STA labels and plus-style stationing
- the `Stations` panel provides station row review/settings for key/major/minor classification, labels, element kind, tangent direction, and tick display settings
- `Plan/Profile Review` enriches key station rows with evaluated alignment frame fields
- `Plan/Profile Review` prefers `V1Stationing` rows for `PlanOutput.station_rows` and compact key-station navigation when a stationing object exists
- `Plan/Profile Review` prefers a document `V1Alignment` source object before falling back to legacy alignment adaptation
- `Plan/Profile Review` alignment handoff now opens the single v1 `Alignment` editor for native alignment-source edits
- `Plan/Profile Review` reports bridge diagnostics that confirm whether the active v0 `HorizontalAlignment` resolved into a v1 `AlignmentModel`, whether the paired `ProfileModel.alignment_id` matches, and whether profile stations fit the alignment range
- `Cross Section Viewer` can use `AlignmentEvaluationService.station_offset_adapter()` for TIN section terrain sampling when an `AlignmentModel` is available
- circular and transition curve parametric evaluation remain planned; current sampled curve support preserves downstream workflow while avoiding a false full-curve claim

## 2. Scope

This model covers:

- horizontal geometry definition
- station reference behavior
- station equations
- geometric evaluation services
- diagnostic and validation rules
- alignment identity and provenance

This model does not cover:

- vertical profile authoring
- superelevation logic
- section template authoring
- final plan sheet layout behavior

## 3. Core Rule

`AlignmentModel` is a durable source-of-truth model.

This means:

- corridor evaluation reads from it
- plan and exchange outputs derive from it
- viewers may inspect it
- no downstream output contract becomes the new alignment truth

## 4. Design Goals

The v1 alignment subsystem should:

- represent civil road alignment intentionally
- support tangent, curve, and transition geometry
- support `station` as a first-class evaluation domain
- preserve traceability to external imports such as `LandXML`
- expose deterministic evaluation services for corridor and output consumers

## 5. Alignment Scope in v1

Recommended early v1 support:

- [x] tangent segments
- [x] sampled circular curve geometry from PI radius input
- [x] approximate sampled transition curves from PI transition length input
- [ ] analytic `clothoid` / Euler spiral geometry objects
- [ ] station equations
- [x] station range queries
- [x] sampled-polyline evaluation for imported or degraded geometry
- [x] station range to sampled geometry
- [ ] plan-geometry extraction through a dedicated service
- [x] minimal plan-geometry extraction through `PlanOutputMapper`
- [x] minimal FreeCAD source object storage through `V1Alignment`
- [x] minimal FreeCAD source object editing through the single `Alignment` command
- [x] v0-style PI/radius/transition/criteria input migrated into the v1 `Alignment` command
- [x] FreeCAD display shape generation from compiled v1 alignment geometry
- [x] PI and compiled-geometry review summaries in the v1 Alignment editor
- [x] minimal FreeCAD stationing storage through `V1Stationing`
- [x] station grid generation through the unified `Stations` command
- [x] v1 station tick display shape generation
- [x] v1 station label offset, plus-format labels, and key/major/minor station classification
- [x] v1 stationing generation/review/settings command

Current editor rule:

- `Alignment` opens the selected or first document `V1Alignment`
- if no `V1Alignment` exists, the editor opens without creating sample data; `Apply` creates the source object from the current PI table
- `PI Geometry` is the primary editing tab and follows the previous v0 Alignment UI structure: sketch import, CSV import/export, presets, X, Y, radius, transition length, transition toggle, spiral segments, design speed, superelevation, side friction, and minimum criteria values
- Design Standard is owned by `Project Setup`; the Alignment editor only displays the project standard and stores it as the applied `CriteriaStandard` snapshot when the alignment is applied
- preset loading supports `Pattern only`, `Center on terrain`, and `Center on project origin`; `Center on terrain` uses the selected/project/document surface bounds when available and falls back to project origin when no terrain surface is found
- `Apply` stores PI rows, radius rows, transition rows, and criteria values on the `V1Alignment` source object
- `Apply` compiles consecutive PI rows into station-based v1 geometry rows consumed by stations, profile, section, and corridor services
- internal PI rows with radius generate tangent chunks plus sampled curve chunks between computed tangent points
- internal PI rows with radius and transition length generate approximate sampled S-C-S chunks using curvature ramp-in, circular arc, and curvature ramp-out
- curve setback is clamped against adjacent segment lengths to avoid invalid overlapping geometry in short test layouts
- `Compiled v1 Geometry` is a read-only inspection tab for the station rows produced by the PI input
- `Compiled v1 Geometry` shows element kind, station start/end, length, point count, and XY rows
- `Review Alignment` lists PI review rows and compiled geometry rows for quick design verification
- recompute builds a display shape from compiled geometry rows and records display point, edge, curve, and transition counts
- endpoint radius and transition values are forced to 0
- consecutive duplicate PI rows are rejected
- `Review Alignment` remains an alignment-stage review action
- the editor intentionally does not show `Review Plan/Profile` or `Next: Generate Stations` actions in the alignment stage

Current stationing rule:

- `V1Stationing` belongs under `02_Alignment & Profile / Stations`
- `Stations` opens without generating stations; the panel `Apply` action creates a sample `V1Alignment` first when no v1 alignment exists
- station rows store `StationValues`, `StationLabels`, `XValues`, `YValues`, `TangentDirections`, `ActiveElementIds`, `ActiveElementKinds`, and `SourceReasons`
- station rows now also store review strings plus source alignment label, source geometry signature, active-element kind summary, tangent/curve/transition station counts, and stale-source notes when a previous stationing object was based on older alignment geometry
- curve and transition elements contribute midpoint extra stations so `ActiveElementKinds` reliably includes `sampled_curve` or `transition_curve` when those zones exist
- station display properties include `ShowTicks`, `MinorTickLength`, `MajorTickLength`, `MajorInterval`, `StationStartOffset`, and `StationLabelFormat`
- station display recompute builds tick geometry normal to the evaluated tangent direction
- `Apply` in `Stations` can generate/update stations, apply label/tick settings, and refresh the station table without leaving the stationing workflow
- Plan/Profile Review uses `V1Stationing` as the preferred station grid before falling back to ad-hoc interval sampling

Deferred or later refinements may include:

- richer compound alignment authoring UX
- specialized jurisdiction-specific annotations
- advanced multi-alignment corridor relationships

## 6. Alignment Object Families

Recommended primary object families:

- `AlignmentModel`
- `AlignmentGeometrySequence`
- `AlignmentElement`
- `StationEquationSet`
- `AlignmentConstraintSet`
- `AlignmentEvaluationResult`

## 7. AlignmentModel Root

### 7.1 Purpose

`AlignmentModel` is the durable container for one horizontal design alignment.

### 7.2 Recommended root fields

- `schema_version`
- `alignment_id`
- `project_id`
- `label`
- `alignment_kind`
- `geometry_sequence`
- `station_equations`
- `constraint_rows`
- `unit_context`
- `coordinate_context`
- `source_refs`
- `diagnostic_rows`

### 7.3 Recommended alignment kinds

- `road_centerline`
- `offset_alignment`
- `reference_alignment`
- `temporary_candidate_alignment`

## 8. AlignmentGeometrySequence

### 8.1 Purpose

`AlignmentGeometrySequence` preserves the ordered horizontal geometry definition.

### 8.2 Rule

The sequence must preserve engineering order, not just a display polyline.

### 8.3 Recommended fields

- `geometry_sequence_id`
- `alignment_id`
- `element_rows`
- `start_station`
- `end_station`
- `notes`

## 9. AlignmentElement

### 9.1 Purpose

Each `AlignmentElement` represents one meaningful geometric element in the horizontal sequence.

### 9.2 Recommended element fields

- `element_id`
- `element_index`
- `kind`
- `station_start`
- `station_end`
- `length`
- `geometry_payload`
- `incoming_tangent_ref`
- `outgoing_tangent_ref`
- `source_ref`
- `notes`

### 9.3 Recommended element kinds

- `tangent`
- `circular_curve`
- `transition_curve`
- `imported_unknown_curve`

### 9.4 Geometry payload rule

`geometry_payload` should preserve parametric meaning rather than collapsing immediately to sampled points.

Examples of payload meaning:

- tangent start and end definition
- circular radius and rotation direction
- transition length and curvature progression intent

## 10. Transition Curve Policy

### 10.1 Purpose

Transition curves are important in v1 because road design should not treat every non-tangent geometry as a simple circular arc.

### 10.2 Recommended policy

Transition geometry should preserve:

- curve family intent
- start and end station
- transition length
- curvature progression direction

### 10.3 Recommended early family support

- `clothoid`
- `unknown_transition_with_diagnostics`

### 10.4 Rule

If imported transition geometry cannot be represented exactly, the model should preserve the best supported form and emit diagnostics.

## 11. StationEquationSet

### 11.1 Purpose

`StationEquationSet` preserves station discontinuity or remapping rules.

### 11.2 Recommended fields

- `station_equation_set_id`
- `alignment_id`
- `equation_rows`
- `notes`

### 11.3 Recommended equation row fields

- `equation_id`
- `station_back`
- `station_ahead`
- `equation_kind`
- `notes`

### 11.4 Recommended kinds

- `station_ahead`
- `station_back`
- `station_reset`

### 11.5 Rule

Evaluation services must use station equations explicitly rather than assuming monotonic simple chainage only.

## 12. AlignmentConstraintSet

### 12.1 Purpose

Constraint rows capture design intent and validation context without turning the model into a UI-only preference store.

### 12.2 Recommended fields

- `constraint_id`
- `kind`
- `value`
- `unit`
- `hard_or_soft`
- `notes`

### 12.3 Recommended kinds

- `design_speed`
- `min_radius`
- `max_deflection`
- `transition_required`
- `protected_station_range`

## 13. Evaluation Services

Recommended service families:

- `AlignmentEvaluationService`
- `StationResolutionService`
- `PlanGeometryExtractionService`

## 14. AlignmentEvaluationService

### 14.1 Purpose

This service evaluates station-based horizontal geometry in deterministic form.

Initial implementation status:

- tangent and sampled-polyline elements can return `x`, `y`, `tangent_direction_deg`, `active_element_id`, `active_element_kind`, and `offset_on_element`
- out-of-range stations return explicit status instead of silent zero coordinates
- station/offset conversion uses positive offset to the left of the alignment tangent
- consumers should use `station_offset_adapter()` when they need to pass station/offset sampling into TIN or section services

### 14.2 Typical queries

- [x] station to XY position
- [x] station to tangent direction
- [x] station to local frame
- [x] station range to sampled geometry
- [x] station to active element

### 14.3 Rule

Corridor, section, superelevation, and plan output consumers should use this service rather than implementing their own geometry interpretation.

## 15. StationResolutionService

### 15.1 Purpose

This service resolves station semantics consistently across the model.

### 15.2 Typical responsibilities

- normalize station input
- apply station equations
- validate station range membership
- report ambiguous station references

### 15.3 Rule

No major consumer should silently interpret station values outside the shared station-resolution policy.

## 16. PlanGeometryExtractionService

### 16.1 Purpose

This service produces plan-ready geometry rows from alignment source data without replacing the source contract.

### 16.2 Typical consumers

- `PlanOutput`
- 3D plan overlay
- diagnostic preview tools
- export packaging helpers

### 16.3 Rule

Extracted geometry is derived output. It must not be written back as new alignment truth.

## 17. Validation Rules

Validation should check for:

- broken element ordering
- zero-length or invalid segments
- unsupported transition encoding
- inconsistent station ranges
- ambiguous station equation behavior
- coordinate or unit ambiguity

Validation results should be recorded in `diagnostic_rows`.

## 17.1 Focused Validation Command

Preferred FreeCAD command-line location:

```powershell
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_alignment_evaluation_service.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_alignment_station_sampling_service.py', 'r', encoding='utf-8').read())"
```

Related regression checks:

```powershell
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "exec(open(r'tests\contracts\v1\test_v1_alignment_source_object.py', 'r', encoding='utf-8').read())"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "ns={}; exec(open(r'tests\contracts\v1\test_alignment_profile_bridge_diagnostics.py', 'r', encoding='utf-8').read(), ns); [fn() for name, fn in sorted(ns.items()) if name.startswith('test_') and callable(fn)]; print('[PASS] v1 alignment/profile bridge diagnostics contract tests completed.')"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "ns={}; exec(open(r'tests\contracts\v1\test_plan_profile_command_bridge.py', 'r', encoding='utf-8').read(), ns); [fn() for name, fn in sorted(ns.items()) if name.startswith('test_') and callable(fn)]; print('[PASS] v1 plan/profile command bridge contract tests completed.')"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "ns={}; exec(open(r'tests\contracts\v1\test_section_command_bridge.py', 'r', encoding='utf-8').read(), ns); [fn() for name, fn in sorted(ns.items()) if name.startswith('test_') and callable(fn)]; print('[PASS] v1 section command bridge contract tests completed.')"
& "D:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" -c "ns={}; exec(open(r'tests\contracts\v1\test_output_mappers.py', 'r', encoding='utf-8').read(), ns); [fn() for name, fn in sorted(ns.items()) if name.startswith('test_') and callable(fn)]; print('[PASS] v1 output mapper contract tests completed.')"
```

## 18. Diagnostics

Diagnostics should be produced when:

- imported geometry does not map cleanly
- a transition curve is simplified
- station equations are incomplete or conflicting
- an evaluation query lands in an invalid gap
- plan extraction requires degraded sampling

Recommended diagnostic fields:

- `diagnostic_id`
- `severity`
- `kind`
- `source_ref`
- `message`
- `notes`

## 19. Identity and Provenance

Alignment objects should preserve:

- stable `alignment_id`
- imported external identity where relevant
- source file reference
- import or edit provenance
- candidate-vs-approved status where applicable

This is especially important for:

- `LandXML` exchange
- AI candidate comparison
- plan/profile linkage

## 20. Relationship to ProfileModel

`AlignmentModel` and `ProfileModel` are separate source systems.

The relationship is:

- alignment defines horizontal station space
- profile defines vertical behavior along that station space

`ProfileModel` must reference alignment identity explicitly rather than copying alignment geometry internally.

## 21. Relationship to Section and Corridor

`AppliedSection` evaluation depends on alignment for:

- station position
- local frame
- left/right orientation
- plan path continuity

`CorridorModel` must consume evaluated alignment frames rather than re-deriving them independently.

## 22. Relationship to Outputs

### 22.1 PlanOutput

`PlanOutput` may consume sampled or extracted geometry from alignment services.

It must not become the new authoring source.

### 22.2 ProfileOutput

`ProfileOutput` depends on the station domain defined by `AlignmentModel`.

### 22.3 SectionOutput

`SectionOutput` depends on the alignment-local frame and station identity resolved from `AlignmentModel`.

## 23. Relationship to LandXML

`LandXML` alignment import should normalize into `AlignmentModel`.

`LandXML` alignment export should primarily read from:

- `AlignmentModel`
- related metadata in `ExchangeOutputSchema`

`PlanOutput` may support packaging context, but not replace the source contract.

## 24. AI and Alternative Design

AI-assisted workflows may propose:

- candidate tangency revisions
- candidate transition lengths
- candidate curve radius changes
- candidate alignment alternatives

But any accepted result must still be written into normalized alignment source objects.

The AI layer must not invent a parallel alignment representation.

## 25. Recommended Minimal Schema Version

Recommended initial version:

- `AlignmentModelSchemaVersion = 1`

## 26. Anti-Patterns

The following should be avoided:

- storing only sampled polylines as the alignment truth
- letting plan display geometry become the editable source
- duplicating station logic across corridor and output code
- hiding transition-curve degradation
- embedding profile or superelevation state directly into the alignment source contract

## 27. Summary

In v1, `AlignmentModel` is the durable horizontal source contract for:

- geometry sequence
- station semantics
- design constraints
- deterministic evaluation

It should remain parametric and station-aware, so that:

- profile logic can reference it cleanly
- section and corridor evaluation can trust it
- `LandXML` exchange can normalize through it
- plan outputs and 3D overlays can derive from it without replacing it
