# CorridorRoad V1 LandXML Mapping Plan

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_EXCHANGE_PLAN.md`
- `docsV1/V1_EXCHANGE_OUTPUT_SCHEMA.md`
- `docsV1/V1_TIN_DATA_SCHEMA.md`
- `docsV1/V1_PLAN_OUTPUT_SCHEMA.md`
- `docsV1/V1_PROFILE_OUTPUT_SCHEMA.md`

## 1. Purpose

This document defines how `LandXML` should map into and out of the CorridorRoad v1 architecture.

It exists to answer four practical questions:

- what `LandXML` content v1 will accept first
- which internal source and result contracts imported content must normalize into
- which internal output contracts export should read from
- what is intentionally deferred or treated as degraded exchange

## 2. Scope

This plan covers:

- `LandXML` import mapping
- `LandXML` export mapping
- alignment-related mapping
- profile-related mapping
- TIN surface-related mapping
- feature-line and diagnostic handling

This plan does not define:

- full `LandXML` specification compliance
- parser implementation details
- exact XML element names for every future extension
- direct UI workflow design

## 3. Core Rule

`LandXML` should be treated as a civil exchange format, not as the internal engineering truth.

The main architectural rule is:

- import normalizes `LandXML` content into v1 source or result contracts
- export packages v1 source, result, and output contracts into `LandXML`

The system must not keep downstream engineering logic dependent on raw `LandXML` object shapes.

## 4. Why LandXML Comes First

`LandXML` is the strongest first exchange target for v1 because it aligns with the redesign priorities:

- horizontal alignment exchange
- profile exchange
- TIN surface exchange
- civil-oriented interoperability

It also fits the v1 philosophy better than treating drawing files as the main engineering interchange format.

## 5. Mapping Philosophy

### 5.1 Normalize by meaning

Imported objects should be classified by engineering meaning before they are stored.

Examples:

- an alignment should become an `AlignmentModel` source object
- a profile should become a `ProfileModel` source object
- a surface should become a TIN-related object family

### 5.2 Separate source and result roles

Some imported `LandXML` content is best treated as source authoring input, while some exported `LandXML` content is best treated as packaged design result.

This distinction must stay explicit.

### 5.3 Preserve provenance

All imported or exported `LandXML` packages should record:

- file origin
- mapping decisions
- degraded or skipped content
- coordinate and unit interpretation

### 5.4 Avoid fake round-trip promises

v1 should not promise perfect round-tripping for every unsupported or loosely defined `LandXML` feature.

## 6. Priority Coverage

Recommended initial `LandXML` coverage:

1. alignment import/export
2. profile import/export
3. TIN surface import/export
4. feature-line import where practical
5. diagnostic reporting for unsupported content

Deferred or lower-priority topics:

- corridor-specific schema ambitions beyond stable v1 contracts
- sheet-oriented annotation exchange
- structure-rich exchange that is better suited to `IFC`

## 7. Import Architecture

### 7.1 Import pipeline

Recommended import stages:

1. file read
2. unit and coordinate interpretation
3. external object discovery
4. semantic classification
5. normalization into v1 contracts
6. diagnostic reporting

### 7.2 Import targets

Early `LandXML` import should target:

- `AlignmentModel`
- `ProfileModel`
- TIN object families defined in `V1_TIN_DATA_SCHEMA.md`

### 7.3 Import package kinds

Recommended internal classification:

- `source_exchange` for alignment and profile authoring data
- `source_exchange` or `result_exchange` for surfaces depending on project intent

## 8. Export Architecture

### 8.1 Export pipeline

Recommended export stages:

1. source and result selection
2. output contract selection
3. package normalization through `ExchangeOutputSchema`
4. `LandXML` payload construction
5. diagnostic recording

### 8.2 Export readers

Early `LandXML` export should read from:

- normalized alignment source contracts
- normalized profile source contracts
- normalized surface result contracts
- `ExchangeOutputSchema` package metadata

### 8.3 Export package kinds

Recommended internal classification:

- `source_exchange` for alignment and profile export
- `result_exchange` for surface export
- `mixed_exchange` only when an export intentionally combines both

## 9. Alignment Mapping

### 9.1 Import role

Imported alignment content should become durable alignment source data.

### 9.2 Import target

Recommended target:

- `AlignmentModel`

### 9.3 Import mapping expectations

Imported alignment normalization should preserve:

- alignment identity
- ordered geometry sequence
- station reference context
- curve and transition meaning where supported
- diagnostic rows for unsupported geometry cases

### 9.4 Export source

Alignment export should read from:

- normalized alignment source contracts
- optional `PlanOutput` only for derived packaging support, not as the source of truth

### 9.5 Rule

`PlanOutput` may help package station or annotation context, but the actual alignment definition must come from `AlignmentModel`.

## 10. Profile Mapping

### 10.1 Import role

Imported profile content should become durable vertical-design source data or design reference data.

### 10.2 Import target

Recommended target:

- `ProfileModel`

### 10.3 Import mapping expectations

Imported profile normalization should preserve:

- profile identity
- station-elevation rows
- PVI meaning where available
- vertical curve or transition meaning where available
- explicit diagnostic rows when a profile must be simplified

### 10.4 Export source

Profile export should read from:

- normalized profile source contracts
- `ProfileOutput` where packaged review metadata is useful

### 10.5 Rule

`ProfileOutput` is not the authoring truth. It may support export packaging, but `ProfileModel` remains the primary export source.

## 11. TIN Surface Mapping

### 11.1 Import role

Imported surface content should become normalized TIN-related objects rather than freeform mesh leftovers.

### 11.2 Import targets

Recommended targets:

- `SurveyPointSet`
- `BreaklineSet` where the source makes that meaning available
- `BoundarySet`
- `VoidBoundarySet`
- `SurveyTIN` or `ExistingGroundTIN`

### 11.3 Import mapping expectations

Imported surface normalization should preserve:

- vertex coordinates
- face topology where available
- boundary and void meaning
- provenance rows
- coordinate and unit context
- quality and diagnostic rows

### 11.4 Export sources

Surface export should read from normalized result families such as:

- `ExistingGroundTIN`
- `DesignTIN`
- `SubgradeTIN`
- `DaylightTIN`

### 11.5 Rule

Export should not serialize arbitrary display meshes. It should serialize normalized TIN result objects.

## 12. Feature-Line Mapping

### 12.1 Import role

Feature lines are useful, but they should be treated carefully because their engineering meaning can vary.

### 12.2 Recommended import treatment

Recommended mappings:

- terrain-supporting feature lines -> `BreaklineSet`
- reference-only linear content -> reference geometry with diagnostics

### 12.3 Rule

The importer must not silently upgrade every imported polyline into a hard engineering breakline.

## 13. Mapping Matrix

### 13.1 Import matrix

- `LandXML alignment` -> `AlignmentModel`
- `LandXML profile` -> `ProfileModel`
- `LandXML surface vertices/faces` -> TIN source/result families
- `LandXML feature line` -> `BreaklineSet` or reference geometry with diagnostics
- unknown or unsupported civil content -> diagnostic rows and skipped-content report

### 13.2 Export matrix

- `AlignmentModel` -> `LandXML alignment payload`
- `ProfileModel` -> `LandXML profile payload`
- normalized TIN result families -> `LandXML surface payload`
- `ExchangeOutputSchema` metadata -> package-level `LandXML` metadata context

## 14. Unit and Coordinate Mapping

### 14.1 Import rule

`LandXML` import must explicitly resolve:

- linear unit
- area unit where relevant
- volume unit where relevant
- coordinate interpretation
- vertical reference assumptions

### 14.2 Export rule

Every export package should carry enough metadata to make numeric interpretation explicit through `ExchangeOutputSchema`.

### 14.3 Anti-rule

No `LandXML` path should depend on silent assumptions like:

- "meters unless the user knows otherwise"
- "local coordinates because that is what the current FreeCAD scene looks like"

## 15. Identity and Provenance

### 15.1 Import provenance

Imported objects should preserve:

- original file identity
- external object labels where useful
- import timestamp
- mapping notes
- degraded-import diagnostics

### 15.2 Export provenance

Export packages should preserve:

- internal source references
- internal result references
- internal output references
- export selection scope
- diagnostic rows

## 16. Diagnostics

### 16.1 Required diagnostic situations

Diagnostics should be generated when:

- a geometry type is unsupported
- a profile must be simplified
- a surface is incomplete
- unit interpretation is ambiguous
- a coordinate context is missing or degraded
- a feature line cannot be trusted as a breakline automatically

### 16.2 Diagnostic outputs

Recommended reporting:

- import diagnostic rows attached to normalized objects
- exchange-package diagnostic rows
- skipped-content summary

## 17. Degraded Exchange Policy

Not every `LandXML` file will map cleanly into v1.

The correct behavior is:

- import what can be normalized safely
- mark what was simplified
- report what was skipped

The system should prefer explicit degraded exchange over silent corruption.

## 18. Round-Trip Expectations

### 18.1 Supported round-trip baseline

Reasonable early round-trip expectations:

- alignment import then export with identity and geometry preserved as far as v1 contracts support
- profile import then export with meaningful vertical geometry preserved as far as v1 contracts support
- TIN surface import then export with topology and boundary meaning preserved where possible

### 18.2 Non-goal

Exact binary or schema-faithful round-trip of every unsupported `LandXML` construct is not a v1 goal.

## 19. Delivery Order

Recommended implementation order:

1. `LandXML` alignment import
2. `LandXML` profile import
3. `LandXML` TIN import
4. `LandXML` alignment export
5. `LandXML` profile export
6. `LandXML` TIN export
7. feature-line refinement and richer diagnostics

## 20. Anti-Patterns

The following should be avoided:

- exporting from viewer geometry instead of normalized source/result contracts
- treating `PlanOutput` or `ProfileOutput` as authoring truth
- importing unknown linear geometry as hard breaklines by default
- keeping raw `LandXML` runtime objects as long-term engineering dependencies
- hiding degraded import/export behavior from the user

## 21. Summary

In v1, `LandXML` should function as the first-class civil exchange format for:

- alignments
- profiles
- TIN surfaces

Its architectural role is to connect external civil data with normalized v1 contracts, not to bypass them.

That means:

- import normalizes into `AlignmentModel`, `ProfileModel`, and TIN object families
- export reads from normalized source/result/output contracts through `ExchangeOutputSchema`
- unsupported content is handled through diagnostics instead of hidden assumptions
