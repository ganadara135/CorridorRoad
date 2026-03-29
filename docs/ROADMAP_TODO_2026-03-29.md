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

### Mid-Term Sprint Breakdown

#### Sprint 4. `notch` schema + resolved-profile integration
- [x] Complete `4-1. Notch schema baseline`
- [x] Complete `4-2. Resolved structure profile usage`
- [x] Complete the schema/contract portion of `4-4. Diagnostics and reporting`

Sprint 4 goal:
- Lock down what a notch-aware corridor section means.
- Make `culvert` / `crossing` notch inputs deterministic before pushing harder on geometry.
- Freeze the first notch-aware data contract and status outputs.

#### Sprint 5. `notch` loft safety + regression hardening
- [x] Complete `4-3. Loft-safe notch generation`
- [x] Complete the regression portion of `4-4. Diagnostics and reporting`
- [x] Complete `4-5. Boolean-cut boundary preservation`

Sprint 5 goal:
- Make notch geometry survive neighboring stations and mixed corridor ranges.
- Add enough tests and diagnostics that notch work can evolve without destabilizing `skip_zone`.
- Keep the implementation clearly separate from later `boolean_cut`.

#### Sprint 6. `external_shape` first earthwork consumption step
- [x] Complete `5-1. Supported first-consumption target`
- [x] Complete `5-2. Runtime consumption and fallback`
- [x] Complete `5-3. Validation and docs sync`

Sprint 6 goal:
- Move `external_shape` one step beyond display-only behavior.
- Keep the first supported behavior narrow and explicit rather than over-promising solid-driven earthwork.
- Leave behind validation and status text that makes the supported scope obvious.

#### Sprint 7. Advanced `Typical Section` modeling + downstream verification
- [x] Complete `6-1. Component parameter expansion`
- [x] Complete `6-2. Presets and editing helpers`
- [x] Complete `6-3. Pavement geometry/report promotion`
- [x] Complete `6-4. Stability re-verification`

Sprint 7 goal:
- Increase practical section-modeling power for ditch/curb/berm workflows.
- Promote pavement data from summary-only toward real outputs where feasible.
- Re-verify the full downstream chain before moving on to long-term scope.

### 4. Structure corridor handling: implement `notch`

#### 4-1. Notch schema baseline
- [x] Define the first notch-aware closed-profile schema for `culvert` and `crossing`.
- [x] Decide the minimum station tags / structure tags needed to mark notch-active sections.
- [x] Document when schema `1` is still used versus when notch-aware schema is required.

#### 4-2. Resolved structure profile usage
- [x] Reuse `StructureSet.resolve_profile_at_station(...)` / `resolve_profile_span(...)` as the notch input contract.
- [x] Confirm which profile fields may vary along the notch span without changing schema shape unexpectedly.
- [x] Add safe fallback behavior when profile data is incomplete or sparse.

#### 4-3. Loft-safe notch generation
- [x] Keep notch generation loft-safe across neighboring stations.
- [x] Review transition-station insertion rules so notch entry/exit does not create degenerate neighboring sections.
- [x] Confirm behavior when a notch span overlaps `split_only` or `skip_zone` structure areas.

#### 4-4. Diagnostics and reporting
- [x] Report notch-aware counts and schema details in corridor completion/status output.
- [x] Add regression coverage for notch-aware station counts, schema propagation, and fallback warnings.
- [x] Make sure diagnostics identify whether the runtime used notch schema, notch cutters, or fallback behavior.

#### 4-5. Boolean-cut boundary preservation
- [x] Validate that notch behavior remains distinct from later `boolean_cut`.
- [x] Keep naming, status text, and validation messages from implying direct imported-solid boolean behavior.
- [x] Document the handoff point where later `boolean_cut` work should begin instead of extending notch logic.

Reference:
- `docs/CORRIDOR_STRUCTURE_NOTCH_PLAN.md`

### 5. Promote `external_shape` beyond display-only usage

#### 5-1. Supported first-consumption target
- [x] Define the first practical step for consuming `external_shape` in section/corridor/earthwork logic.
- [x] Choose one narrow target first: section override envelope, corridor notch seed, or simplified grading void proxy.
- [x] Explicitly defer any wider solid-driven interpretation that is not stable enough yet.

#### 5-2. Runtime consumption and fallback
- [x] Reduce the gap between imported structure appearance and actual earthwork behavior.
- [x] Add a bounded runtime path that uses derived dimensions or a simplified proxy from `external_shape`.
- [x] Keep safe fallback behavior when imported solids are invalid, too complex, or unsupported for the chosen consumer.

#### 5-3. Validation and docs sync
- [x] Document exact supported behavior so users know what is display-only versus analysis-affecting.
- [x] Add validation and fallback rules for unstable or partial `external_shape` consumption.
- [x] Update status outputs so users can tell when imported solids are used directly, indirectly, or not at all.

Reference:
- `docs/ARCHITECTURE.md`
- `docs/STRUCTURE_SPRINT5_EXTERNAL_SHAPE_PLAN.md`
- `README.md`

### 6. Advance `Typical Section` modeling

#### 6-1. Component parameter expansion
- [x] Add advanced parameterization for `ditch`, `curb`, and `berm`.
- [x] Decide which parameters belong in the core component schema versus preset-only metadata.
- [x] Keep default/simple templates stable while richer components are introduced.

#### 6-2. Presets and editing helpers
- [x] Expand component presets and editing helpers where they improve repeatable workflows.
- [x] Add editor-side affordances for common roadside combinations instead of requiring fully manual entry every time.
- [x] Confirm that richer preset usage still serializes into a stable template contract.

#### 6-3. Pavement geometry/report promotion
- [x] Promote pavement layers from summary-only data to separate geometry/reporting outputs when feasible.
- [x] Decide whether pavement promotion starts with section-only wires/faces or full downstream corridor solids.
- [x] Keep summary totals available even when richer pavement outputs are not generated.

#### 6-4. Stability re-verification
- [x] Re-verify that `SectionSet`, `CorridorLoft`, and `DesignGradingSurface` remain stable with richer component definitions.
- [x] Extend regression coverage for richer component definitions, pavement outputs, and downstream status propagation.
- [x] Re-check UI/task-panel messaging so advanced templates do not imply unsupported production outputs.

Reference:
- `docs/TYPICAL_SECTION_EXECUTION_PLAN.md`

## Long Term

### 7. Add opt-in `boolean_cut`
Status:
- Excluded from the current roadmap scope.
- Do not schedule new work here unless long-term scope is re-opened explicitly.

Reference:
- `docs/CORRIDOR_STRUCTURE_NOTCH_PLAN.md`

### 8. Expand practical engineering scope

#### Item 8 Sprint Breakdown

##### Sprint 8A. Subassembly core contract
- [x] Complete `8-1. Assembly/Subassembly role split`
- [x] Complete `8-2. Core subassembly schema`
- [x] Complete `8-3. Validation/status baseline`

Sprint 8A goal:
- Freeze the core data contract before adding many new practical section types.
- Separate geometry-driving fields from report-only fields.
- Keep fallback behavior simple and deterministic.

##### Sprint 8B. Practical roadside library
- [x] Complete `8-4. Reusable roadside component set`
- [x] Complete `8-5. Preset/mirroring consistency`
- [x] Complete `8-6. Rich-section downstream safety`

Sprint 8B goal:
- Make common practical roadside assemblies reusable without custom row editing each time.
- Stabilize richer sections through `SectionSet`, `CorridorLoft`, and `DesignGradingSurface`.
- Leave behind a repeatable preset contract.

##### Sprint 8C. Report data contract
- [x] Complete `8-7. Structured report rows`
- [x] Complete `8-8. Quantity/schedule outputs`
- [x] Complete `8-9. Export-ready summaries`

Sprint 8C goal:
- Promote design results from UI-only summaries to structured report data.
- Keep section, pavement, structure, and corridor results exportable.
- Make report outputs regression-testable.

##### Sprint 8D. Surface comparison mode expansion
- [x] Complete `8-10. Comparison source matrix`
- [x] Complete `8-11. Domain/clip controls`
- [x] Complete `8-12. Station-binned analysis`

Sprint 8D goal:
- Expand `CutFillCalc` beyond the current phase-1 surface comparison.
- Make comparison targets and domain selection explicit.
- Support practical corridor-focused and station-range-focused review.

##### Sprint 8E. Review-quality metrics and outputs
- [x] Complete `8-13. Quality/confidence metrics`
- [x] Complete `8-14. Review-oriented outputs`
- [x] Complete `8-15. Runtime messaging cleanup`

Sprint 8E goal:
- Make comparison/report outputs trustworthy enough for design review.
- Show not just values, but also quality indicators and fallback conditions.
- Align runtime status with exported/reportable data.

##### Sprint 8F. Sample-driven field validation
- [x] Complete `8-16. Practical sample set`
- [x] Complete `8-17. Extended regression set`
- [x] Complete `8-18. User/developer doc sync`

Sprint 8F goal:
- Validate the practical-engineering scope against realistic sample projects.
- Lock the new contracts with regression coverage.
- Leave documentation synchronized with the real supported scope.

#### 8-1. Assembly/Subassembly role split
- [x] Reconfirm the responsibility boundary between `AssemblyTemplate` and `TypicalSectionTemplate`.
- [x] Decide which practical-engineering features should live in a future subassembly contract versus remain in the current typical-section contract.
- [x] Define which fields are geometry-driving, which are analysis-driving, and which are report-only.

#### 8-2. Core subassembly schema
- [x] Define a shared row contract for practical subassemblies.
- [x] Include stable identity/order/side/offset fields so richer practical parts remain serializable.
- [x] Keep the first schema narrow enough that simple existing templates still map cleanly.

#### 8-3. Validation/status baseline
- [x] Add validation rules for subassembly combinations that are unsupported or ambiguous.
- [x] Define status tokens that distinguish simple, advanced, and fallback practical-section outputs.
- [x] Freeze the minimum regression expectations before larger geometry work begins.

#### 8-4. Reusable roadside component set
- [x] Build a first reusable library for lane/shoulder/curb-gutter/ditch/berm/sidewalk/median style parts.
- [x] Standardize parameter names and defaults across those reusable parts.
- [x] Confirm that left/right/both/center usage stays deterministic.

#### 8-5. Preset/mirroring consistency
- [x] Expand presets and bundle helpers to cover realistic roadside combinations.
- [x] Keep mirroring and side-conversion behavior stable for richer practical templates.
- [x] Confirm that helpers produce the same serialized contract as manual editing.

#### 8-6. Rich-section downstream safety
- [x] Re-verify richer practical sections through `SectionSet`.
- [x] Re-verify richer practical sections through `CorridorLoft`.
- [x] Re-verify richer practical sections through `DesignGradingSurface`.

#### 8-7. Structured report rows
- [x] Define structured result rows for section, pavement, structure, and corridor summaries.
- [x] Keep report rows machine-readable rather than UI-string-only.
- [x] Decide which report rows stay on source objects versus downstream consumer objects.

#### 8-8. Quantity/schedule outputs
- [x] Add first-pass quantity/schedule outputs for pavement layers and section components.
- [x] Add structure-interaction summary outputs where they materially affect interpretation.
- [x] Keep these outputs aligned with the same source contracts used by geometry generation.

#### 8-9. Export-ready summaries
- [x] Define a stable export shape for CSV/report outputs.
- [x] Keep export fields predictable across simple and advanced projects.
- [x] Add sample-based checks so export values remain consistent with geometry/status.

#### 8-10. Comparison source matrix
- [x] Define supported source combinations for advanced surface comparison.
- [x] Separate fully supported, partially supported, and deferred source pairs.
- [x] Keep comparison source rules explicit in validation and status messaging.

#### 8-11. Domain/clip controls
- [x] Add corridor-focused domain clipping options.
- [x] Add user-selected analysis-domain options when they can be represented safely.
- [x] Ensure clipped analysis reports what was excluded as well as what was compared.

#### 8-12. Station-binned analysis
- [x] Add station-range binning for cut/fill and deviation summaries.
- [x] Add side-aware summaries where left/right interpretation is meaningful.
- [x] Keep binning output aligned with the stationing/alignment contract already used elsewhere.

#### 8-13. Quality/confidence metrics
- [x] Add metrics such as compared-cell count, no-data ratio, and fallback/interpolation counts.
- [x] Surface coordinate/domain mismatch risks explicitly in status and reports.
- [x] Define which metrics should block trust versus merely warn.

#### 8-14. Review-oriented outputs
- [x] Define the minimum set of design-review outputs that should be available without manual spreadsheet cleanup.
- [x] Add section/corridor/pavement/surface summaries that are useful in review meetings.
- [x] Keep outputs concise and reproducible from the same saved project state.

#### 8-15. Runtime messaging cleanup
- [x] Align UI summaries, object `Status`, and export/report wording.
- [x] Remove wording that over-promises unsupported production outputs.
- [x] Make fallback and confidence messaging consistent across geometry and analysis tools.

#### 8-16. Practical sample set
  - [x] Prepare realistic sample projects for practical roadway, urban curb/sidewalk, and ditch/berm workflows.
  - [x] Add sample scenarios that stress advanced surface comparison and reporting.
  - [x] Keep sample names and scope understandable enough for repeatable validation.

#### 8-17. Extended regression set
  - [x] Add targeted regressions for richer practical section contracts.
  - [x] Add targeted regressions for structured report/export outputs.
  - [x] Add targeted regressions for advanced comparison modes and clipped/station-binned analysis.

#### 8-18. User/developer doc sync
  - [x] Update user docs for the practical-engineering workflow once contracts stabilize.
  - [x] Update developer docs with schema, result-field, and regression expectations.
  - [x] Keep sample files, docs, and runtime status text synchronized.

Reference:
- `README_Codex.md`

### 9. Standardize release readiness checks
Status:
- Excluded from the current roadmap scope.
- Do not schedule new work here unless release-operations work is re-opened explicitly.

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
  6. `Expand practical engineering scope`
- `boolean_cut` and release-readiness standardization are currently outside the active roadmap scope.
- This order favors stability first, then geometry realism, then practical engineering/reporting value.
