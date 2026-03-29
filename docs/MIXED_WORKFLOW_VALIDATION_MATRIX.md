Date: 2026-03-29

<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Mixed Workflow Validation Matrix

This document defines the current short-term validation stance for mixed workflows.
It is intended to support Sprint 1 and Sprint 2 validation/warning work.

## Validation Policy

Supported:
- Workflow is expected to work in the current implementation.
- Runtime may still emit normal status text, but no special compatibility warning is required.

Partially Supported:
- Workflow is intentionally allowed.
- Runtime should warn clearly when geometry, earthwork, or analysis behavior is simplified.
- Fallback behavior must be explicit in status text or task-panel messaging.

Unsupported:
- Workflow should be blocked, warned strongly, or treated as future scope.
- Do not imply that the current output is physically equivalent to the requested intent.

## Matrix

### 1. Typical Section + Sections + Corridor Loft
Status:
- Supported

Expected behavior:
- `TypicalSectionTemplate` drives the finished-grade top profile.
- `SectionSchemaVersion=2` may be used.
- `CorridorLoft` may auto-prefer ruled loft for richer profiles.

Validation expectation:
- Confirm section schema, top-profile source, and pavement summary propagation.

### 2. Typical Section + Pavement Layers
Status:
- Partially Supported

Expected behavior:
- pavement layers are stored, previewed, and summarized
- pavement total thickness propagates to downstream objects

Current limitation:
- pavement layers are not yet separate corridor solids

Validation expectation:
- warn only when users may assume separate physical pavement geometry already exists

### 3. StructureSet + split_only
Status:
- Supported

Expected behavior:
- corridor can split at structure boundaries
- structure-aware section tagging and segmentation are valid

Validation expectation:
- report structure segment counts and split stations

### 4. StructureSet + skip_zone
Status:
- Supported, with active diagnostics

Expected behavior:
- corridor omits structure-active spans
- surviving pre/post spans remain loftable

Validation expectation:
- report skipped ranges, skip markers, and corridor mode summary
- warn when structure spans are point-like or poorly defined

### 5. StructureSet + notch
Status:
- Partially Supported

Expected behavior:
- notch-capable workflows may work for first-pass corridor behavior

Current limitation:
- notch behavior is still under staged rollout
- geometry stability and per-type behavior are not yet fully generalized

Validation expectation:
- warn when a workflow depends on notch-specific assumptions outside current safe cases

### 6. GeometryMode=template
Status:
- Supported for display/reference and current type-driven earthwork workflows

Expected behavior:
- template geometry improves structure display and section/corridor context

Validation expectation:
- require valid template fields
- keep structure `Type` as the current earthwork driver

### 7. GeometryMode=external_shape
Status:
- Partially Supported

Expected behavior:
- imported external shapes improve 3D display and reference placement

Current limitation:
- imported `STEP` / `BREP` / `FCStd` solids are not yet consumed directly as earthwork-cutting geometry
- sections, grading, and corridor handling still follow structure `Type` and simple dimensional fields

Validation expectation:
- warn that `external_shape` is display/reference placement only
- warn when users combine `external_shape` with expectations of direct notch or boolean consumption
- runtime status should expose `earthwork=simplified_type_driven` plus `displayOnly=external_shape:N`

### 8. external_shape + notch / boolean_cut expectations
Status:
- Unsupported as direct imported-solid consumption

Expected behavior:
- current runtime must not imply that the imported solid directly defines the notch or boolean cutter

Validation expectation:
- emit explicit warnings
- treat as future-scope behavior

### 9. Structure station-profile data + structure display
Status:
- Supported

Expected behavior:
- structure size and related dimensions can vary by station-profile control points

Validation expectation:
- require at least 2 profile points per structure
- warn on duplicate or unsorted profile stations

### 10. Structure station-profile data + section overrides / corridor handling
Status:
- Partially Supported

Expected behavior:
- resolved profile values may influence section overlays and corridor behavior

Current limitation:
- not every downstream consumer is equally mature

Validation expectation:
- warn when users assume full direct shape consumption everywhere

### 11. Daylight terrain sampling + Local/World terrain coordinates
Status:
- Supported

Expected behavior:
- terrain coordinate interpretation may be `Local` or `World`
- missing or failed terrain sampling falls back to fixed side widths

Validation expectation:
- status should distinguish between no terrain source, sampler failure, and successful daylight resolution
- preferred tokens are `daylight=fallback:no_terrain`, `daylight=fallback:sampler_failed`, `daylight=terrain:local`, and `daylight=terrain:world`

### 12. Coordinate workflow recommendation + task-panel defaults
Status:
- Supported

Expected behavior:
- initialized CRS workflows prefer world-first defaults
- blank CRS workflows prefer local-first defaults

Validation expectation:
- task panels should reflect the recommended mode consistently

## Current Warning Rules

The runtime should warn for the following short-term cases:
- `external_shape` is used and the user may assume direct earthwork consumption
- `external_shape` is paired with `notch` or `boolean_cut` expectations
- a structure corridor mode is defined with no usable station span
- a `skip_zone` or `notch` span is effectively point-like without corridor margin
- mixed workflows rely on partial-support behavior that is currently data-driven or type-driven rather than true solid-driven

## Current Block Rules

The runtime should block or fail clearly for the following:
- invalid required fields for the chosen geometry mode
- invalid corridor span ordering that cannot be resolved safely
- impossible loft input such as fully skipped corridor station coverage

## References

- `docs/ARCHITECTURE.md`
- `docs/CORRIDOR_STRUCTURE_NOTCH_PLAN.md`
- `docs/TYPICAL_SECTION_EXECUTION_PLAN.md`
- `docs/RUNTIME_VALIDATION_CHECKLIST.md`
- `README.md`
