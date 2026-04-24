# CorridorRoad V1 Earthwork Balance Plan

Date: 2026-04-22
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_OUTPUT_STRATEGY.md`

## 1. Purpose

This document defines how CorridorRoad v1 should approach cut/fill balancing, mass-haul analysis, and earthwork-aware optimization.

The feature should not be treated as a single "zero-balance button."

Instead, it should be designed as a staged system for:

- earthwork analysis
- balance diagnostics
- scenario comparison
- rule-based recommendations
- constrained optimization

## 2. Core Direction

The preferred v1 product direction is:

`Earthwork Balance` rather than `force exact zero cut/fill`.

This is important because practical roadway design must also consider:

- material usability
- swell and shrink factors
- haul distance
- borrow and waste locations
- drainage constraints
- profile constraints
- structure constraints
- fixed project controls

Therefore, v1 should optimize toward balance while preserving engineering realism.

## 3. Product Goal

The earthwork balance feature should help users answer questions such as:

- How much cut and fill does the current design produce?
- Where do surplus and deficit occur?
- How much of the cut is actually usable as fill?
- Where are the balance points?
- Where are borrow or waste locations needed?
- Which design changes improve balance with acceptable engineering tradeoffs?
- Which alternative design is best under the current constraints?

## 4. Feature Position in V1

Earthwork balance is not just a report.

It is a corridor-level analysis and optimization subsystem that sits between:

- section evaluation
- surface generation
- quantity reporting
- design iteration

It should connect to:

- `ProfileModel`
- `AssemblyModel`
- `RegionModel`
- `StructureModel`
- `CorridorModel`
- `SurfaceModel`
- `QuantityModel`

## 5. Design Principles

### 5.1 TIN-first

Earthwork analysis should use the v1 TIN-first terrain and design-surface model.

### 5.2 Section-aware

Earthwork balance must be computed from station-aware corridor results, not from isolated top-level volume snapshots only.

### 5.3 Material-aware

Usable and unusable cut must be distinguishable.

### 5.4 Scenario-based

Optimization should compare alternatives, not silently override the user's design.

### 5.5 Explainable

Recommendations and optimization proposals must explain:

- what was changed
- why it improved balance
- what constraints limited the result
- what tradeoffs remain

## 6. Recommended Capability Stages

### 6.1 Stage 1: Earthwork Analysis

First deliverable for v1.

Core outputs:

- total cut
- total fill
- usable cut
- unusable cut
- borrow requirement
- waste requirement
- balance ratio
- station-by-station cumulative mass values

### 6.2 Stage 2: Mass-Haul Review

Add mass-haul interpretation and visualization.

Core outputs:

- cumulative mass curve
- balance points
- haul direction
- free-haul / overhaul interpretation where supported
- borrow and waste candidate markers

### 6.3 Stage 3: Rule-Based Rebalance Assistance

Add guided design recommendations without full automatic optimization.

Examples:

- suggest a local profile adjustment
- suggest a side-slope policy change
- suggest a region-specific template change
- suggest a daylight-policy adjustment

### 6.4 Stage 4: Constrained Optimization

Add controlled automatic optimization under explicit user-set objectives and constraints.

The system should generate candidates, not silently replace the accepted design.

## 7. Domain Objects

Recommended v1 earthwork balance object families:

### 7.1 EarthworkBalanceModel

Purpose:

- compute station-based and project-based cut/fill balance results

Typical responsibilities:

- cut/fill totals
- usable/unusable separation
- balance ratio
- diagnostics summary

### 7.2 MassHaulModel

Purpose:

- compute cumulative mass flow and related hauling behavior

Typical responsibilities:

- cumulative mass curve
- balance points
- haul direction
- borrow and waste need summaries

### 7.3 BalanceOptimizationScenario

Purpose:

- store user goals, constraints, candidate alternatives, and selected outcomes

Typical responsibilities:

- optimization objective settings
- fixed controls
- candidate results
- score summaries
- recommendation explanations

## 8. Required Inputs

The earthwork balance system should be able to use the following data:

- `ExistingGroundTIN`
- `FG_TIN`
- `Subgrade_TIN`
- `Daylight_TIN` where relevant
- `AppliedSectionSet`
- station ranges
- region assignments
- structure interaction results

Optional but highly valuable inputs:

- material zones
- material usability classification
- swell factors
- shrink factors
- borrow locations
- waste locations
- haul-cost assumptions

## 9. Core Calculations

### 9.1 Section area calculation

For each evaluated station, compute the relevant cut and fill areas using:

- applied section geometry
- existing ground
- subgrade and daylight interpretation where needed

### 9.2 Volume between stations

Compute incremental volumes between adjacent stations or analysis slices.

### 9.3 Material separation

Split volumes into:

- usable cut
- unusable cut
- fill demand

### 9.4 Cumulative mass curve

Compute cumulative difference across station order to support mass-haul interpretation.

### 9.5 Balance-point detection

Locate where cumulative mass crosses or approaches balance.

### 9.6 Borrow and waste estimation

Estimate required import or export material when usable cut and fill cannot be matched.

### 9.7 Haul cost estimation

Where enough data exists, estimate relative haul cost or penalty.

## 10. Practical Material Logic

Exact cut and fill equality is not enough in practical design.

The system should eventually support:

- percentages of usable cut by material type
- different behaviors for topsoil, rock, unsuitable material, and engineered fill
- shrink/swell adjusted balance
- material-specific haul assumptions

The first v1 implementation may start simpler, but the model should leave room for this.

## 11. Optimization Objectives

The optimization system should support weighted multi-objective behavior rather than a single hard-coded target.

Recommended objective terms:

- minimize `|usable_cut - fill|`
- minimize borrow volume
- minimize waste volume
- minimize haul effort or haul cost
- minimize profile disturbance from the accepted design
- minimize structure impact
- preserve drainage viability
- preserve standards compliance

This allows `near-zero balance` to be one goal among several, not the only goal.

## 12. Optimization Variables

Recommended early adjustable variables:

- PVI elevations
- local profile smoothing within limits
- side-slope policy
- ditch or berm rule selection
- daylight policy
- region-specific template selection
- limited roadside earthwork-related widths where safe

Do not treat the following as freely adjustable by default:

- fixed alignment control points
- locked structure zones
- legally fixed geometry
- bridge/tunnel/culvert critical controls
- user-locked design points

## 13. Constraints

The optimization and recommendation system must respect:

- maximum and minimum grades
- drainage-related minimum grade
- crest/sag or vertical-curve rules
- template and region rules
- structure clearance rules
- fixed station constraints
- user-locked geometry
- environmental or exclusion zones where relevant

## 14. Output Strategy

Earthwork balance should generate standardized output families rather than one-off dialogs.

Recommended output families:

- `EarthworkBalanceOutput`
- `MassHaulOutput`
- `BalanceScenarioOutput`
- `BalanceRecommendationOutput`

These should connect cleanly into the broader v1 output system.

## 15. Reports and Review Outputs

### 15.1 Engineering report outputs

Priority report outputs:

- total cut/fill summary
- usable/unusable material summary
- borrow/waste summary
- station-range summary
- region summary

### 15.2 Review outputs

Priority review outputs:

- mass-haul curve
- balance-point markers
- surplus/deficit station highlighting
- affected-region highlighting

### 15.3 Drawing outputs

Potential drawing outputs:

- profile plus mass-haul diagram sheet
- section sheets with balance issue flags
- plan sheets with borrow/waste markers

## 16. UI Strategy

Recommended top-level command:

- `Earthwork Balance`

Recommended tabs or panels:

- `Overview`
- `Mass Haul`
- `Constraints`
- `Scenarios`
- `Recommendations`
- `Apply Candidate`

## 17. Viewer Integration

Cross Section Viewer should not become the earthwork-balance editor, but it should become a strong review entry point.

Recommended viewer integrations:

- show local cut/fill state at the active station
- show whether the active area is in surplus or deficit context
- show related region and structure context
- show recommendation hints when available
- allow jump to the relevant profile, region, or template editor

Example use cases:

- "This station is inside a deficit zone."
- "Reducing FG by 0.15 m over this local range may improve balance."
- "This region's side-slope policy drives excess cut."

## 18. 3D and Profile Review Integration

Earthwork balance should also connect to v1 review displays.

Recommended integrations:

- 3D coloring of surplus and deficit ranges
- 3D markers for borrow and waste candidates
- profile overlays for cumulative mass behavior
- region-boundary highlighting where balance state changes sharply

## 19. Candidate Comparison Workflow

The preferred workflow is:

1. analyze current design
2. identify imbalance and major drivers
3. define objectives and fixed controls
4. generate recommendations or candidates
5. compare candidates by score and engineering impact
6. review sections, profiles, and 3D outputs
7. accept one candidate explicitly

This is safer and more transparent than one-click silent automatic reshaping.

## 20. Diagnostics

The system should report failures and weak confidence clearly.

Examples:

- missing terrain source
- incomplete section evaluation
- invalid material parameters
- insufficient station density for confidence
- conflicting fixed constraints
- optimization infeasible under current locks

## 21. Performance Strategy

Earthwork balance may become expensive over long corridors.

Recommended controls:

- analysis range selection
- coarse vs fine station density
- preview mode vs final mode
- deferred recommendation generation
- candidate-count limit

## 22. Initial V1 Roadmap

### 22.1 V1.0 target

- earthwork totals
- station-based incremental volume
- balance ratio
- mass-haul curve
- borrow/waste summary

### 22.2 V1.1 target

- rule-based rebalance recommendations
- scenario comparison
- viewer integration
- profile review integration

### 22.3 V1.2 target

- constrained multi-objective optimization
- candidate ranking
- explanation logs
- optional AI-assisted recommendation layer

## 23. Recommended Follow-Up Documents

This plan should be followed by:

1. `V1_EARTHWORK_OUTPUT_SCHEMA.md`
2. `V1_MASS_HAUL_VIEW_PLAN.md`
3. `V1_BALANCE_OPTIMIZATION_SCHEMA.md`
4. `V1_PROFILE_MASS_HAUL_SHEET_PLAN.md`

## 24. Final Rule

In v1, earthwork balance should not be a black-box "make it zero" feature.

It should be a transparent, TIN-aware, section-aware, scenario-driven system that helps users move toward better balance while preserving engineering intent and practical constructability.
