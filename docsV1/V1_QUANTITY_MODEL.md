# CorridorRoad V1 Quantity Model

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_CORRIDOR_MODEL.md`
- `docsV1/V1_SURFACE_MODEL.md`
- `docsV1/V1_OUTPUT_STRATEGY.md`

## 1. Purpose

This document defines the v1 internal model for normalized quantity results.

It exists to make clear:

- what `QuantityModel` owns
- how quantities derive from section, corridor, and surface semantics
- how quantity groupings and summaries should be structured
- how quantities feed outputs and review workflows

## 2. Scope

This model covers:

- quantity identity and grouping
- station-based quantity fragments
- component, pavement, region, and structure-related summaries
- quantity aggregation rules
- diagnostics and traceability

This model does not cover:

- final report layout templates
- direct mesh-based measurement tools
- earthwork optimization logic
- viewer-only display styling

## 3. Core Rule

`QuantityModel` is a derived analytical result system built from normalized engineering results.

This means:

- it is not a primary source authoring model
- it should reuse section, corridor, and surface semantics
- quantity results must remain traceable to engineering inputs
- quantities must not be reverse-engineered from unlabeled display geometry

## 4. Quantity Philosophy in v1

In v1, quantities are not side notes in a UI panel.

They are:

- first-class analytical outputs
- traceable engineering summaries
- station-aware and region-aware result families
- inputs to reporting, review, and comparison workflows

## 5. Main Upstream Inputs

`QuantityModel` depends primarily on:

- `AppliedSection`
- `AppliedSectionSet`
- `CorridorModel`
- `SurfaceModel`
- structure interaction results where relevant

It may also use:

- region identity and policy context
- scenario identity
- unit context and measurement rules

## 6. Quantity Scope in v1

Recommended early v1 support:

- pavement quantities
- section-based component quantities
- station-range quantity summaries
- region-based quantity summaries
- structure-related quantity notes
- cut/fill-linked quantity groupings where practical

Deferred or later refinements may include:

- richer cost-code mapping
- advanced bill-of-quantities formatting
- procurement-specific export packaging

## 7. Quantity Object Families

Recommended primary object families:

- `QuantityModel`
- `QuantityFragment`
- `QuantityAggregate`
- `QuantityGroupingSet`
- `QuantityResolutionResult`
- `QuantityComparisonSet`

## 8. QuantityModel Root

### 8.1 Purpose

`QuantityModel` is the durable identity container for grouped quantity results within a project or corridor context.

### 8.2 Recommended root fields

- `schema_version`
- `quantity_model_id`
- `project_id`
- optional `corridor_id`
- `label`
- `fragment_rows`
- `aggregate_rows`
- `grouping_rows`
- `comparison_rows`
- `source_refs`
- `diagnostic_rows`

### 8.3 Rule

The quantity model should keep fragment and aggregate relationships explicit instead of scattering totals across many unrelated outputs.

## 9. QuantityFragment

### 9.1 Purpose

Each `QuantityFragment` represents a small, traceable quantity contribution from a station, component, or surface-derived segment.

### 9.2 Recommended fields

- `fragment_id`
- `quantity_kind`
- `measurement_kind`
- `value`
- `unit`
- `station_start`
- `station_end`
- optional `applied_section_ref`
- optional `component_ref`
- optional `region_ref`
- optional `structure_ref`
- `source_ref`
- `notes`

### 9.3 Recommended quantity kinds

- `pavement_quantity`
- `component_quantity`
- `surface_area_quantity`
- `linear_quantity`
- `structure_adjacent_quantity`
- `earthwork_linked_quantity`

### 9.4 Rule

Fragments should preserve enough semantics to support later regrouping and reporting without recomputing raw engineering meaning.

## 10. QuantityAggregate

### 10.1 Purpose

`QuantityAggregate` represents a grouped or summarized quantity result.

### 10.2 Recommended fields

- `aggregate_id`
- `aggregate_kind`
- `grouping_ref`
- `value`
- `unit`
- `fragment_refs`
- `notes`

### 10.3 Recommended aggregate kinds

- `project_total`
- `station_range_total`
- `region_total`
- `component_total`
- `pavement_total`
- `structure_note_total`

### 10.4 Rule

Aggregates should be derived from explicit fragment references rather than being stored as disconnected magic totals.

## 11. QuantityGroupingSet

### 11.1 Purpose

`QuantityGroupingSet` preserves how quantity fragments are grouped for analysis or output.

### 11.2 Recommended fields

- `grouping_id`
- `grouping_kind`
- `grouping_key`
- `station_start`
- `station_end`
- `notes`

### 11.3 Recommended grouping kinds

- `by_component`
- `by_region`
- `by_station_range`
- `by_structure_context`
- `by_scenario`

### 11.4 Rule

Grouping semantics should be explicit and reusable by outputs instead of being hidden in one report generator.

## 12. Pavement Quantity Policy

### 12.1 Rule

Pavement quantities should derive from labeled section and corridor semantics, not from guessed solid volumes alone.

### 12.2 Typical quantity bases

- lane width and thickness semantics
- shoulder and auxiliary pavement components
- pavement layer identity
- station range and region context

### 12.3 Result expectation

Pavement quantity outputs should remain traceable to:

- component identity
- station range
- source template or region context where relevant

## 13. Region and Structure Quantity Policy

### 13.1 Region quantities

Region-based summaries should be first-class supported outputs.

They are useful for:

- policy comparison
- phased reporting
- corridor review

### 13.2 Structure-related quantities

Structure interaction may affect quantities through:

- local replacement or omission
- wall-adjacent treatments
- structure-zone component changes
- structure-related notes and exceptions

### 13.3 Rule

Structure-related quantity notes should remain traceable to structure interaction results, not merged invisibly into generic totals.

## 14. Quantity Build Services

Recommended service families:

- `QuantityBuildService`
- `QuantityAggregationService`
- `QuantityGroupingService`
- `QuantityComparisonService`

These services should consume normalized section, corridor, and surface results rather than inventing their own geometric interpretations.

## 15. QuantityResolutionResult

### 15.1 Purpose

This result object captures selected quantity views for downstream consumers.

### 15.2 Recommended fields

- `resolution_id`
- `selected_fragment_ids`
- `selected_aggregate_ids`
- `selected_grouping_ids`
- `diagnostic_rows`
- `notes`

### 15.3 Rule

Resolution results are derived helper objects, not new source data.

## 16. QuantityComparisonSet

### 16.1 Purpose

`QuantityComparisonSet` preserves meaningful quantity comparisons across alternatives or scenarios.

### 16.2 Recommended fields

- `comparison_id`
- `base_quantity_model_ref`
- `compare_quantity_model_ref`
- `comparison_kind`
- `delta_rows`
- `notes`

### 16.3 Recommended kinds

- `baseline_vs_candidate`
- `region_policy_comparison`
- `earthwork_aware_comparison`
- `scenario_total_comparison`

### 16.4 Rule

Quantity comparison should rely on normalized fragments and aggregates rather than comparing presentation-layer tables only.

## 17. Relationship to Earthwork Balance

Quantity and earthwork are related but not identical systems.

The architectural distinction is:

- `QuantityModel` handles measurable component and surface-related quantities
- `EarthworkBalanceModel` handles cut/fill, mass-haul, borrow, waste, and balance analysis

They may share:

- section semantics
- corridor surfaces
- station ranges
- scenario identity

But one should not absorb the other.

## 18. Relationship to Outputs

The quantity subsystem is a main upstream source for:

- `QuantityOutput`
- quantity snippets in section sheets where needed
- comparison reports
- AI comparison summaries

Output systems should consume normalized fragments, aggregates, and grouping semantics instead of recomputing totals independently.

## 19. Relationship to Viewer and Review

Viewer and review systems may consume quantity-derived context through:

- station-level quantity notes
- region summary callouts
- structure-adjacent quantity notes
- scenario comparison summaries

But they must not become the new quantity source.

Review systems should inspect quantity provenance, not mutate quantity definitions directly.

## 20. Diagnostics

Diagnostics should be produced when:

- a fragment loses component identity
- an aggregate references missing fragments
- region grouping is inconsistent
- structure-related quantity notes lose source references
- quantity totals disagree with required upstream semantics

Recommended diagnostic fields:

- `diagnostic_id`
- `severity`
- `kind`
- `source_ref`
- optional `fragment_ref`
- `message`
- `notes`

## 21. Identity and Provenance

Quantity objects should preserve:

- stable `quantity_model_id`
- related `corridor_id` where applicable
- fragment and aggregate identity
- grouping identity
- scenario or candidate identity where applicable
- build provenance

This is important for:

- quantity review
- scenario comparison
- output packaging
- AI recommendation evaluation

## 22. Validation Rules

Validation should check for:

- missing fragment references
- inconsistent units within a grouping
- orphaned aggregates
- invalid station-range summaries
- lost region or structure traceability
- comparison sets with incompatible grouping semantics

Validation results should be recorded in `diagnostic_rows`.

## 23. AI and Alternative Design

AI-assisted workflows may propose:

- quantity-aware alternative comparisons
- grouping recommendations for clearer reporting
- suspicious override-heavy quantity diagnostics
- scenario ranking by quantity impact

But accepted changes must still flow through normalized source edits and recompute.

The AI layer must not keep separate hidden quantity totals outside the quantity contracts.

## 24. Anti-Patterns

The following should be avoided:

- computing quantities from unlabeled viewer meshes
- hiding quantity grouping logic inside one report panel
- merging structure notes into totals with no traceability
- letting presentation tables become the quantity truth
- collapsing earthwork and quantity logic into one oversized subsystem

## 25. Summary

In v1, `QuantityModel` is the derived analytical result model for:

- station-based quantity fragments
- component, pavement, region, and structure-related aggregates
- grouping and comparison semantics
- traceable quantity provenance

It should remain section-aware and corridor-aware, so that:

- `AppliedSection` and `CorridorModel` provide stable measurement semantics
- outputs can package quantities consistently
- review and AI workflows can compare totals meaningfully
- quantity logic stays separate from earthwork while sharing the same engineering foundation
