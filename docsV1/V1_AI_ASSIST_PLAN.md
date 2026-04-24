# CorridorRoad V1 AI Assist Plan

Date: 2026-04-24
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_SECTION_MODEL.md`
- `docsV1/V1_RAMP_MODEL.md`
- `docsV1/V1_INTERSECTION_MODEL.md`
- `docsV1/V1_DRAINAGE_MODEL.md`
- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`
- `docsV1/V1_OUTPUT_STRATEGY.md`

## 1. Purpose

This document defines the v1 AI-assist strategy.

It exists to clarify:

- what AI is allowed to do
- what AI is not allowed to do
- how AI interacts with the parametric corridor model
- how recommendations and alternatives should be represented
- where human approval is required

## 2. Core Direction

AI in v1 is an assistive design layer.

It is not an unreviewed authoring engine.

The preferred model is:

- propose
- explain
- compare
- require approval

not:

- silently rewrite the project

## 3. Product Role

AI assist should help users with tasks like:

- generating alignment alternatives
- generating ramp alternatives
- comparing intersection policy alternatives
- generating profile alternatives
- suggesting section-policy changes
- suggesting drainage-policy changes
- highlighting risk zones
- suggesting earthwork-balance improvements
- explaining which design levers drive a problem

## 4. Architectural Role

The AI-assist subsystem belongs above the core engineering model.

It should consume:

- source models
- result models
- output contracts
- user goals and constraints

It should produce:

- recommendations
- scenarios
- alternative candidates
- explanations

It should not become the source-of-truth owner of engineering geometry.

## 5. AI Principles

### 5.1 Assist, do not replace

AI should support the user's engineering process rather than bypass it.

### 5.2 Explainability required

Every meaningful AI output should explain:

- what inputs were considered
- what assumptions were made
- what constraints were active
- what objective improved
- what risks remain

### 5.3 Human approval required

No AI-proposed state should become the accepted project state without explicit user approval.

### 5.4 Parametric consistency required

AI suggestions must map back to:

- source objects
- override rows
- scenario objects

and not to hidden geometry patches.

## 6. Capability Levels

### 6.1 Level 1: Explain and diagnose

AI can:

- summarize current project issues
- explain likely drivers of a section or earthwork problem
- rank likely source owners of a visible issue

### 6.2 Level 2: Recommend edits

AI can:

- recommend profile adjustments
- recommend region-policy changes
- recommend template swaps
- recommend ramp tie-in changes
- recommend intersection control-area changes
- recommend side-slope or daylight changes

### 6.3 Level 3: Generate alternatives

AI can:

- generate multiple candidate alignments
- generate multiple candidate ramps or tie-in variants
- generate multiple candidate profiles
- generate candidate region and section-policy variations
- generate candidate intersection and drainage-policy variations
- generate earthwork-balance scenarios

### 6.4 Level 4: Guided optimization assistant

AI can work with optimization outputs and help compare candidates, but still should not auto-accept them.

## 7. Non-Goals

AI assist in v1 should not:

- edit generated section geometry directly
- silently modify accepted designs
- replace engineering constraints with vague language guesses
- invent unsupported source mappings
- act as a substitute for deterministic evaluation services

## 8. Main AI Use Cases

### 8.1 Alignment alternative generation

Example requests:

- reduce curvature severity
- avoid a structure zone
- simplify this ramp merge
- reduce overall earthwork

### 8.2 Profile alternative generation

Example requests:

- reduce embankment
- improve drainage viability
- avoid ponding near a sag
- reduce cut in a specific range

### 8.3 Section-policy recommendation

Example requests:

- reduce excessive cut on the left side
- evaluate alternate ditch policy
- compare gutter versus ditch treatment through a ramp tie-in
- compare retaining treatment against slope daylight

### 8.4 Junction and ramp recommendation

Example requests:

- reduce conflict at this merge area
- compare two ramp tie-in strategies
- simplify this intersection control area

### 8.5 Earthwork-balance recommendation

Example requests:

- reduce borrow requirement
- improve usable-cut-to-fill balance
- minimize waste while preserving current design intent

### 8.6 Review explanation

Example requests:

- explain why this station changed
- explain which source owns this section behavior
- explain why the AI prefers candidate B over candidate A

## 9. Input Model

The AI-assist subsystem should be able to consume:

- project goals
- user constraints
- source object state
- ramp, intersection, and drainage source state
- applied-section summaries
- surface summaries
- earthwork-balance summaries
- quantity summaries
- review diagnostics

Optional higher-value context:

- user-locked geometry
- excluded areas
- cost or priority weights
- preferred design standards

## 10. Output Model

AI assist should produce normalized output families.

Recommended families:

- `AIRecommendation`
- `AICandidate`
- `AIScenarioComparison`
- `AIExplanationLog`

### 10.1 AIRecommendation

Purpose:

- one bounded recommendation tied to a known source owner or scenario

### 10.2 AICandidate

Purpose:

- one candidate design alternative or bounded modification package

### 10.3 AIScenarioComparison

Purpose:

- side-by-side comparison of two or more candidates against explicit objectives

### 10.4 AIExplanationLog

Purpose:

- traceable explanation record of what AI considered and why it ranked outputs as it did

## 11. Candidate Representation

AI candidates should not be stored as opaque text only.

They should map into structured modifications such as:

- profile changes
- template selection changes
- region-policy changes
- override proposals
- earthwork-balance scenario settings

This allows deterministic evaluation after the candidate is proposed.

## 12. Relationship to Source Objects

AI should recommend changes against known source families, including:

- `AlignmentModel`
- `ProfileModel`
- `SectionTemplate`
- `RegionModel`
- `StructureModel`
- `SectionOverrideModel`
- `BalanceOptimizationScenario`

The AI layer should never own final engineering geometry independently of these sources.

## 13. Relationship to Earthwork Balance

Earthwork-balance is one of the highest-value AI-assist use cases.

AI should be able to:

- interpret balance outputs
- explain likely drivers of imbalance
- recommend bounded changes
- rank candidate scenarios

Examples:

- "Profile change is the dominant lever here, not template change."
- "This borrow requirement is mainly caused by two deficit regions."

## 14. Relationship to Viewer

The viewer should be able to surface AI context without becoming the AI engine itself.

Recommended integrations:

- show recommendation hints
- show candidate comparison context for the active station
- open AI-related explanation panels
- jump from a recommendation to the right editor or scenario view

## 15. Relationship to Output and Review Contracts

AI should consume normalized outputs and summaries whenever practical.

Preferred consumers:

- section outputs
- surface outputs
- quantity outputs
- earthwork-balance outputs
- diagnostics and ownership mappings

This reduces hidden special-case logic in the AI subsystem.

## 16. Prompt and Constraint Model

AI input should combine:

- natural-language goals
- explicit numeric constraints
- locked elements
- scenario scope

Examples:

- "reduce embankment while keeping current alignment and bridge zone fixed"
- "minimize retaining wall length without violating profile constraints"

## 17. Approval Workflow

Recommended workflow:

1. user defines a goal
2. AI proposes one or more candidates
3. system evaluates them deterministically
4. AI summarizes tradeoffs
5. user reviews outputs and diagnostics
6. user explicitly accepts one candidate
7. accepted candidate becomes the new project state or scenario branch

## 18. Scenario Workflow

AI assist works best when tied to explicit scenario objects.

Recommended scenario uses:

- compare baseline and candidate
- compare several profile alternatives
- compare earthwork-oriented alternatives
- preserve user trust through reversible evaluation

## 19. Deterministic Evaluation Rule

AI may propose.

Core engineering services must evaluate.

This means:

- AI cannot be the final authority on geometry
- section, surface, and earthwork results must come from deterministic v1 services
- AI summaries should refer to evaluated results, not imagined outcomes only

## 20. Diagnostics and Confidence

AI outputs should carry confidence and uncertainty context where useful.

Recommended fields:

- confidence note
- blocked constraints note
- missing-data note
- unsupported-request note

The system should admit uncertainty instead of pretending to know more than it does.

## 21. Safety and Trust Rules

Recommended trust rules:

- no silent acceptance
- no hidden geometry mutation
- no unsupported source mapping
- no deletion of locked user choices without approval
- clear distinction between recommendation and accepted design

## 22. Performance Strategy

AI-assist should not force expensive full-project recomputation for every conversational step if avoidable.

Recommended techniques:

- bounded scenario scope
- staged candidate generation
- reuse of cached deterministic results
- explicit final evaluation step for accepted candidates

## 23. Anti-Patterns to Avoid

Avoid the following:

- using AI text output as if it were the final engineering result
- letting AI write into random object fields without contract mapping
- mixing chat state and engineering state implicitly
- hiding objective weights from the user
- letting AI bypass deterministic validation

## 24. Recommended Follow-Up Documents

This AI plan should be followed by:

1. `V1_AI_OUTPUT_SCHEMA.md`
2. `V1_AI_SCENARIO_WORKFLOW.md`
3. `V1_AI_RECOMMENDATION_UI_PLAN.md`

## 25. Final Rule

In v1, AI should help users think, compare, and act with more confidence.

It should not become an opaque shortcut around the parametric corridor model or the deterministic engineering pipeline.
