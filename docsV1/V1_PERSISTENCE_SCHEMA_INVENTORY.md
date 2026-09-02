# V1 Persistence Schema Inventory

Status: Phase 4 baseline completed on 2026-07-13

## Purpose

This document records the active v1 persistence boundary for complex source, result, and output contracts.

The typed model payload is authoritative for newly written objects. Readable FreeCAD properties remain review and compatibility fields.

## Core Rule

- Write a versioned canonical payload with checksum, row counts, required refs, and a source/result fingerprint.
- Restore the typed payload before reading compatibility properties.
- Reject a present but malformed payload with a persistence diagnostic.
- Use compatibility properties only when no typed payload exists, as with an old document.
- Do not reconstruct missing engineering intent from `Shape`, mesh, preview, or viewer geometry.

## Active Typed Payload Adapters

| Family | Layer | Typed model | Counted nested rows | Required refs |
| --- | --- | --- | --- | --- |
| Structures | source | `StructureModel` | structures, geometry specs, kind specs, connection points, interaction rules, influence zones | `project_id`, `structure_model_id` |
| Drainage | source | `DrainageModel` | elements, policies, flow routes | `project_id`, `drainage_model_id` |
| SubAssembly Library | source | `SubassemblyLibrary` | definitions | `project_id`, `library_id` |
| Assembly/Subassembly | source | `AssemblySubassemblyModel` | templates and their nested placed rows | `project_id`, `assembly_id` |
| Regions | source | `RegionModel` | regions, policies, transitions, constraints | `project_id`, `region_model_id` |
| Applied Sections | result | `AppliedSectionSet` | station rows and evaluated sections | `project_id`, `applied_section_set_id` |
| Corridor | result | `CorridorModel` | stations and output-build refs | `project_id`, `corridor_id` |
| Surface | result | `SurfaceModel` | surfaces, build relations, comparisons, spans | `project_id`, `surface_model_id` |

## Parallel Property Inventory

The following active adapters still retain parallel `StringList` or numeric-list properties for property-panel review and old-document restoration:

- Alignment: 5 row-list properties
- Profile: 4
- Stationing: 6
- Region: 11
- Assembly/Subassembly: 21
- SubAssembly Library: 4
- SubAssembly Preset Library: 9
- Structure: 36
- Drainage: 27
- Intersection: 3
- Intersection Trim Boundary: 8
- Applied Sections: 42
- Corridor: 6
- Surface: 20
- Surface Transition: 10

These parallel properties are not a second source of truth for a newly written typed payload. Remaining families should adopt the same adapter only with focused round-trip and migration coverage.

## Schema and Restore Policy

Current envelope schema: `2`.

- Schema 1 to 2 migration explicitly adds row-count and required-ref metadata and recomputes the envelope checksum.
- A future schema change requires a registered one-version migration step.
- A payload from a newer unsupported schema is rejected.
- Embedded checksum, separate FreeCAD checksum, fingerprint, row counts, model type, and required refs are validated.
- Partial row arrays are not truncated or padded during typed restore.
- Old documents without `ModelPayloadJson` continue through their existing compatibility reader.

## Incremental Result Metadata

Applied Sections, Corridor, and Surface result objects expose:

- stage and service version
- engineering input and accepted result fingerprints
- consumed source and result refs
- accepted state
- build duration
- changed stages
- explicit stale reasons

Presentation-only fields such as visibility, colors, line width, transparency, display mode, and style are excluded from engineering fingerprints.

Build Parametric persists Corridor and Surface results through a single document transaction. Accepted unchanged result models are reused, presentation adapters may refresh separately, and the transaction performs one final recompute.

## Output Compatibility

Exchange packages already persist readable `SourceRefs`, `ResultRefs`, and packaged output ids together with chunk-safe JSON payloads. Existing FreeCAD save/reopen coverage verifies large output payload and traceability survival. This Phase does not expand exchange formats.

## Excluded Scope

- Ramp is removed. Historical Ramp properties are compatibility-only and are not migrated or expanded here.
- Watertight Solid development is paused. Existing rows remain compatibility surfaces; no target, topology, simulation, UI, or exchange expansion is included.
- CI remains unchanged. No CI development is allowed by this plan.

## Validation

- serializer round-trip and explicit schema migration contracts
- checksum, fingerprint, row-count, required-ref, and malformed payload rejection
- old-document compatibility fallback
- FreeCAD 1.1.1 source/result save and reopen
- existing exchange-package chunked payload save and reopen
- incremental reuse, stale-reason, interrupted-build, duration, and changed-stage contracts
- document transaction nesting, abort, and one-recompute contracts
