# CorridorRoad V1 AI Output Schema

Date: 2026-04-22
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_AI_ASSIST_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_SECTION_OUTPUT_SCHEMA.md`
- `docsV1/V1_EARTHWORK_BALANCE_PLAN.md`

## 1. Purpose

This document defines the normalized AI-output contracts for v1.

It exists so that AI-related UI, comparison views, and approval workflows can operate on structured payloads instead of opaque text blobs.

## 2. Scope

This schema covers:

- `AIRecommendation`
- `AICandidate`
- `AIScenarioComparison`
- `AIExplanationLog`

It does not define:

- model prompting details
- inference provider configuration
- UI aesthetics

## 3. Core Rule

AI outputs are advisory and structured.

They must map back to internal source/result/output contracts and must not become hidden engineering truth on their own.

## 4. Schema Versioning

Recommended initial versions:

- `AIRecommendationSchemaVersion = 1`
- `AICandidateSchemaVersion = 1`
- `AIScenarioComparisonSchemaVersion = 1`
- `AIExplanationLogSchemaVersion = 1`

## 5. Shared Root Metadata

Recommended common fields across AI payloads:

- `schema_version`
- `ai_output_id`
- `project_id`
- `scenario_id`
- `goal_summary`
- `constraint_rows`
- `source_refs`
- `result_refs`
- `output_refs`
- `status`
- `diagnostic_rows`

## 6. Constraint Rows

### 6.1 Purpose

`constraint_rows` record what bounded the AI output.

### 6.2 Recommended fields

- `constraint_id`
- `kind`
- `target_kind`
- `target_id`
- `expression`
- `locked`
- `notes`

### 6.3 Recommended kinds

- `locked_alignment`
- `locked_profile`
- `locked_structure_zone`
- `grade_limit`
- `drainage_limit`
- `earthwork_limit`
- `template_lock`

## 7. Source / Result / Output References

AI payloads should carry explicit references to:

- internal source owners
- result objects
- output contracts used in evaluation

This improves:

- traceability
- explainability
- deterministic re-evaluation

## 8. AIRecommendation Structure

### 8.1 Purpose

`AIRecommendation` represents one bounded advisory suggestion.

### 8.2 Recommended fields

- `schema_version`
- `ai_output_id`
- `recommendation_kind`
- `title`
- `summary`
- `target_owner_kind`
- `target_owner_id`
- `target_scope`
- `proposed_change_rows`
- `expected_effect_rows`
- `confidence`
- `approval_required`
- `diagnostic_rows`

### 8.3 Recommended recommendation kinds

- `profile_adjustment`
- `template_change`
- `region_policy_change`
- `override_proposal`
- `earthwork_balance_adjustment`
- `risk_explanation`

## 9. Proposed Change Rows

### 9.1 Purpose

`proposed_change_rows` describe structured changes the recommendation is suggesting.

### 9.2 Recommended fields

- `change_id`
- `target_kind`
- `target_id`
- `parameter`
- `old_value`
- `proposed_value`
- `station_start`
- `station_end`
- `notes`

### 9.3 Rule

Changes should be representable as deterministic edits to source objects or scenario objects.

## 10. Expected Effect Rows

### 10.1 Purpose

`expected_effect_rows` describe what the recommendation is expected to improve.

### 10.2 Recommended fields

- `effect_id`
- `kind`
- `direction`
- `magnitude_note`
- `related_metric`
- `notes`

### 10.3 Recommended effect kinds

- `earthwork_improvement`
- `risk_reduction`
- `drainage_improvement`
- `structure_conflict_reduction`
- `quantity_change`

## 11. AICandidate Structure

### 11.1 Purpose

`AICandidate` represents one candidate design alternative or bounded modification package.

### 11.2 Recommended fields

- `schema_version`
- `ai_output_id`
- `candidate_id`
- `title`
- `candidate_kind`
- `summary`
- `change_package_rows`
- `score_rows`
- `risk_rows`
- `approval_required`
- `evaluation_status`
- `diagnostic_rows`

### 11.3 Recommended candidate kinds

- `alignment_alternative`
- `profile_alternative`
- `section_policy_alternative`
- `earthwork_balance_scenario`
- `mixed_alternative`

## 12. Change Package Rows

### 12.1 Purpose

`change_package_rows` are the structured mutation proposals that define a candidate.

### 12.2 Recommended fields

- `package_row_id`
- `target_kind`
- `target_id`
- `change_kind`
- `payload_ref`
- `notes`

### 12.3 Recommended target kinds

- `alignment`
- `profile`
- `template`
- `region`
- `override`
- `balance_scenario`

## 13. Score Rows

### 13.1 Purpose

`score_rows` let the user understand why a candidate was ranked the way it was.

### 13.2 Recommended fields

- `score_id`
- `metric`
- `value`
- `normalized_value`
- `weight`
- `direction`
- `notes`

### 13.3 Recommended metrics

- `earthwork_balance`
- `borrow_volume`
- `waste_volume`
- `haul_cost`
- `profile_disturbance`
- `structure_impact`
- `constraint_compliance`

## 14. Risk Rows

### 14.1 Purpose

`risk_rows` summarize meaningful concerns associated with a candidate.

### 14.2 Recommended fields

- `risk_id`
- `severity`
- `kind`
- `message`
- `related_target_id`
- `notes`

### 14.3 Recommended kinds

- `constraint_risk`
- `drainage_risk`
- `earthwork_risk`
- `structure_risk`
- `confidence_risk`

## 15. AIScenarioComparison Structure

### 15.1 Purpose

`AIScenarioComparison` compares several candidates against explicit objectives.

### 15.2 Recommended fields

- `schema_version`
- `ai_output_id`
- `comparison_id`
- `baseline_candidate_id`
- `candidate_ids`
- `objective_rows`
- `comparison_rows`
- `ranking_rows`
- `summary`
- `diagnostic_rows`

## 16. Objective Rows

### 16.1 Purpose

`objective_rows` describe what the comparison is optimizing or prioritizing.

### 16.2 Recommended fields

- `objective_id`
- `metric`
- `weight`
- `direction`
- `locked`
- `notes`

## 17. Comparison Rows

### 17.1 Purpose

`comparison_rows` record candidate-by-candidate performance on objectives.

### 17.2 Recommended fields

- `comparison_row_id`
- `candidate_id`
- `metric`
- `value`
- `delta_vs_baseline`
- `notes`

## 18. Ranking Rows

### 18.1 Purpose

`ranking_rows` make the comparison result explicit.

### 18.2 Recommended fields

- `ranking_id`
- `candidate_id`
- `rank`
- `overall_score`
- `selection_reason`

## 19. AIExplanationLog Structure

### 19.1 Purpose

`AIExplanationLog` preserves traceable reasoning context.

### 19.2 Recommended fields

- `schema_version`
- `ai_output_id`
- `log_id`
- `summary`
- `input_rows`
- `assumption_rows`
- `constraint_rows`
- `reason_rows`
- `warning_rows`

## 20. Input Rows

### 20.1 Purpose

`input_rows` describe what major inputs were considered.

### 20.2 Recommended fields

- `input_id`
- `kind`
- `ref_id`
- `summary`

## 21. Assumption Rows

### 21.1 Purpose

`assumption_rows` make hidden assumptions visible.

### 21.2 Recommended fields

- `assumption_id`
- `kind`
- `message`
- `confidence_note`

## 22. Reason Rows

### 22.1 Purpose

`reason_rows` explain why the AI preferred a recommendation or candidate.

### 22.2 Recommended fields

- `reason_id`
- `kind`
- `message`
- `related_metric`
- `related_candidate_id`

## 23. Warning Rows

### 23.1 Purpose

`warning_rows` capture limitations and cautionary notes.

### 23.2 Recommended fields

- `warning_id`
- `severity`
- `message`
- `action_hint`

## 24. Approval Rule

Every recommendation or candidate payload should indicate whether approval is required.

Recommended field:

- `approval_required = true`

Optional related fields:

- `approval_state`
- `approved_candidate_id`
- `approved_at`

## 25. Deterministic Evaluation Rule

AI payloads may propose and summarize.

Deterministic engineering services must still evaluate actual geometric and quantitative consequences.

This means AI payloads should be able to reference:

- evaluation status
- result refs
- output refs

rather than acting as if text-only output is sufficient.

## 26. Diagnostic Rows

### 26.1 Purpose

`diagnostic_rows` are shared diagnostic structures across AI payloads.

### 26.2 Recommended fields

- `diagnostic_id`
- `severity`
- `kind`
- `message`
- `related_ref_id`
- `action_hint`

### 26.3 Recommended kinds

- `missing_input`
- `blocked_constraint`
- `unsupported_request`
- `low_confidence`
- `evaluation_pending`
- `evaluation_failed`

## 27. Validation Rules

The AI-output schema should be validated for:

- missing required metadata
- candidate payloads with no structured change rows
- comparison payloads with unknown candidate ids
- explanation logs with no reasons or warnings
- approval-related fields inconsistent with payload type

## 28. Anti-Patterns to Avoid

Avoid the following:

- storing final engineering truth only in natural-language paragraphs
- generating candidates that cannot be mapped to source objects
- hiding objective weights from the comparison payload
- letting UI infer critical AI state that the schema should carry
- treating AI output text as evaluated geometry

## 29. Recommended Follow-Up Documents

This schema document should be followed by:

1. `V1_AI_SCENARIO_WORKFLOW.md`
2. `V1_AI_RECOMMENDATION_UI_PLAN.md`
3. `V1_PLAN_PROFILE_SHEET_PLAN.md`

## 30. Final Rule

In v1, AI output should be structured enough that recommendations, candidates, and explanations can be reviewed, compared, and approved without relying on hidden application state.
