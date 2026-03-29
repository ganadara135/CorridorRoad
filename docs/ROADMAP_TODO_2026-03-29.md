Date: 2026-03-29

<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# CorridorRoad Roadmap To-Do

This document converts the current roadmap discussion into a practical to-do list.
Priority order is:
1. `skip_zone` / validation / regression tests
2. `notch`
3. `external_shape` earthwork consumption
4. `Typical Section` advanced modeling
5. `boolean_cut`

## Short Term

### Short-Term Sprint Breakdown

#### Sprint 1. `skip_zone` baseline + validation matrix
- [x] Complete `1-1. Data and span resolution`
- [x] Complete `1-2. CorridorLoft range splitting`
- [x] Complete `1-4. Status and diagnostics`
- [x] Complete `2-1. Validation matrix definition`
- [x] Define the minimum regression set from `3-1. Test target definition`

Sprint 1 goal:
- Establish a clear `skip_zone` rule set.
- Make the runtime behavior visible in status output.
- Freeze the validation/test target before heavier geometry work.

#### Sprint 2. `skip_zone` output + first regression coverage
- [x] Complete `1-3. Output generation`
- [x] Complete `1-5. Failure and edge-case handling`
- [x] Complete `2-2. Runtime validation rules`
- [x] Complete `2-3. User-facing warnings`
- [x] Complete `3-2. Typical-section pipeline tests`
- [x] Complete `3-3. Structure workflow tests`

Sprint 2 goal:
- Make `skip_zone` usable in practice.
- Cover the highest-risk workflow combinations with validation and tests.
- Reduce the chance of silent geometry misunderstandings.

#### Sprint 3. status cleanup + terrain/coordinate regression hardening
- [x] Complete `2-4. Status message cleanup`
- [x] Complete `2-5. Documentation sync`
- [x] Complete `3-4. Coordinate and terrain interpretation tests`
- [x] Complete `3-5. Test suite maintenance`

Sprint 3 goal:
- Normalize the user-facing messaging.
- Lock down terrain/coordinate edge cases.
- Leave behind a repeatable short-term verification routine.

### 1. Structure corridor handling: stabilize `skip_zone`

#### 1-1. Data and span resolution
- [x] Review current `StructureSet` record fields related to corridor handling.
- [x] Confirm the resolved source of `StartStation`, `EndStation`, and optional corridor margin values.
- [x] Define the exact station-envelope rule for `skip_zone`.
- [x] Document fallback behavior when structure station fields are incomplete or inconsistent.

#### 1-2. CorridorLoft range splitting
- [x] Identify the current section grouping/splitting logic inside `CorridorLoft`.
- [x] Add logic that classifies kept ranges versus skipped ranges from structure-active spans.
- [x] Preserve valid pre-structure and post-structure loft segments as separate build ranges.
- [x] Confirm behavior when multiple structure zones overlap or touch.

#### 1-3. Output generation
- [x] Omit loft generation inside `skip_zone` spans.
- [x] Combine surviving loft bodies into a stable compound result.
- [x] Decide whether skipped-span caps are deferred or partially supported in this phase.
- [x] Confirm behavior when the skipped span is at corridor start or end.

#### 1-4. Status and diagnostics
- [x] Add result/status reporting for active corridor mode, skip-zone count, and skipped station ranges.
- [x] Expose enough information to debug which structures created the skipped ranges.
- [x] Make sure status text distinguishes between `split_only` and `skip_zone`.

#### 1-5. Failure and edge-case handling
- [x] Confirm failure handling when a skip zone covers the full corridor station range.
- [x] Add safe handling for zero-length or near-zero structure spans.
- [x] Add safe handling for station ordering errors and invalid span reversal.
- [x] Confirm recompute behavior after structure edits.

Reference:
- `docs/CORRIDOR_STRUCTURE_NOTCH_PLAN.md`

### 2. Validation and warning UX for mixed workflows

#### 2-1. Validation matrix definition
- [x] List the highest-risk mixed workflows involving `TypicalSection`, `StructureSet`, daylight, pavement, and coordinate workflow.
- [x] Separate them into supported, partially supported, and unsupported combinations.
- [x] Define which combinations should warn, block apply, or silently fall back.

#### 2-2. Runtime validation rules
- [x] Add stronger runtime validation for mixed workflows involving `TypicalSection`, `StructureSet`, daylight, and coordinate workflow settings.
- [x] Add validation for partial-feature combinations where geometry is shown but earthwork logic is simplified.
- [x] Confirm that validation does not break legacy simple workflows.

#### 2-3. User-facing warnings
- [x] Warn clearly when user expectations and runtime behavior differ, especially for `external_shape`.
- [x] Add focused warnings for display-only versus analysis-affecting behavior.
- [x] Review task panels for places where warnings should appear before `Apply`.

#### 2-4. Status message cleanup
- [x] Improve status messages so users can tell whether a result is using display-only logic, simplified earthwork logic, or a full corridor rule.
- [x] Normalize wording across `SectionSet`, `CorridorLoft`, `DesignGradingSurface`, and related panels.
- [x] Review existing status text for ambiguity, duplication, or missing next-step guidance.

#### 2-5. Documentation sync
- [x] Align runtime warnings with README and architecture wording.
- [x] Make sure partial-support features are described consistently in user and developer docs.

Reference:
- `docs/ARCHITECTURE.md`
- `docs/RUNTIME_VALIDATION_CHECKLIST.md`

### 3. Regression test expansion

#### 3-1. Test target definition
- [x] Identify the minimum regression scenarios that must pass before new short-term work is merged.
- [x] Separate smoke tests, functional tests, and edge-case tests.
- [x] Reuse existing sample CSV inputs where possible.

#### 3-2. Typical-section pipeline tests
- [x] Add headless regression coverage for `Typical Section -> Sections -> Corridor Loft`.
- [x] Add at least one test for simple rural input and one for richer ditch/berm input.
- [x] Verify schema/version/status propagation as well as geometry generation.

#### 3-3. Structure workflow tests
- [x] Add regression cases for structure corridor modes and structure-station merge behavior.
- [x] Add coverage for overlapping structures and near-adjacent structure spans.
- [x] Add checks for structure-driven section tagging and structure-aware station expansion.

#### 3-4. Coordinate and terrain interpretation tests
- [x] Add regression coverage for coordinate workflow edge cases that affect section or terrain interpretation.
- [x] Add checks for `Local` versus `World` terrain interpretation where daylight sampling is involved.
- [x] Confirm that fallback behavior is stable when terrain sampling fails.

#### 3-5. Test suite maintenance
- [x] Keep the fixed-tree smoke test and extend the suite rather than replacing it.
- [x] Define naming and placement rules for new regression tests under `tests/regression`.
- [x] Document how to run the short-term regression set in a FreeCAD-capable environment.

Reference:
- `tests/regression/smoke_tree_schema.py`

## Mid Term

### 4. Structure corridor handling: implement `notch`
- [ ] Add a stable notch-aware section schema for `culvert` and `crossing` use cases.
- [ ] Keep notch generation loft-safe across neighboring stations.
- [ ] Use resolved structure profile values along the active station span when station-profile data exists.
- [ ] Report notch-aware counts and schema details in corridor completion/status output.
- [ ] Validate that notch behavior remains distinct from later `boolean_cut`.

Reference:
- `docs/CORRIDOR_STRUCTURE_NOTCH_PLAN.md`

### 5. Promote `external_shape` beyond display-only usage
- [ ] Define the first practical step for consuming `external_shape` in section/corridor/earthwork logic.
- [ ] Reduce the gap between imported structure appearance and actual earthwork behavior.
- [ ] Document exact supported behavior so users know what is display-only versus analysis-affecting.
- [ ] Add validation and fallback rules for unstable or partial `external_shape` consumption.

Reference:
- `docs/ARCHITECTURE.md`
- `docs/STRUCTURE_SPRINT5_EXTERNAL_SHAPE_PLAN.md`
- `README.md`

### 6. Advance `Typical Section` modeling
- [ ] Add advanced parameterization for `ditch`, `curb`, and `berm`.
- [ ] Expand component presets and editing helpers where they improve repeatable workflows.
- [ ] Promote pavement layers from summary-only data to separate geometry/reporting outputs when feasible.
- [ ] Re-verify that `SectionSet`, `CorridorLoft`, and `DesignGradingSurface` remain stable with richer component definitions.

Reference:
- `docs/TYPICAL_SECTION_EXECUTION_PLAN.md`

## Long Term

### 7. Add opt-in `boolean_cut`
- [ ] Keep `boolean_cut` as a later, explicit opt-in mode.
- [ ] Build the prerequisite validation needed for expensive or topology-sensitive boolean operations.
- [ ] Define when boolean cut should use simplified void solids versus imported structure solids.
- [ ] Add failure-safe fallback behavior so a boolean failure does not break the broader workflow.

Reference:
- `docs/CORRIDOR_STRUCTURE_NOTCH_PLAN.md`

### 8. Expand practical engineering scope
- [ ] Continue toward more detailed assembly/subassembly modeling.
- [ ] Expand advanced surface comparison options when the current mesh-based workflow is stable enough.
- [ ] Revisit output/reporting needs for more production-oriented design review workflows.

Reference:
- `README_Codex.md`

### 9. Standardize release readiness checks
- [ ] Create a repeatable release-readiness checklist based on sample data, regression tests, and manual FreeCAD smoke runs.
- [ ] Define the minimum verification set required before merging major development work into `main`.
- [ ] Keep documentation, sample files, and runtime status messaging synchronized with actual behavior.

Reference:
- `docs/RELEASE_OPERATING_MODEL.md`
- `README.md`

## Notes

- Current recommended implementation order remains:
  1. `skip_zone`
  2. validation and regression test reinforcement
  3. `notch`
  4. `external_shape` earthwork consumption
  5. `Typical Section` advanced modeling
  6. `boolean_cut`
- This order favors stability first, then geometry realism, then higher-risk automation.
