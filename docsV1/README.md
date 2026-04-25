# docsV1

This folder contains the CorridorRoad v1 redesign documents.

Baseline document:

- [V1_MASTER_PLAN.md](./V1_MASTER_PLAN.md)
- [V1_ARCHITECTURE.md](./V1_ARCHITECTURE.md)
- [V1_ALIGNMENT_MODEL.md](./V1_ALIGNMENT_MODEL.md)
- [V1_RAMP_MODEL.md](./V1_RAMP_MODEL.md)
- [V1_INTERSECTION_MODEL.md](./V1_INTERSECTION_MODEL.md)
- [V1_PROFILE_MODEL.md](./V1_PROFILE_MODEL.md)
- [V1_SUPERELEVATION_MODEL.md](./V1_SUPERELEVATION_MODEL.md)
- [V1_REGION_MODEL.md](./V1_REGION_MODEL.md)
- [V1_DRAINAGE_MODEL.md](./V1_DRAINAGE_MODEL.md)
- [V1_OVERRIDE_MODEL.md](./V1_OVERRIDE_MODEL.md)
- [V1_STRUCTURE_MODEL.md](./V1_STRUCTURE_MODEL.md)
- [V1_SURFACE_MODEL.md](./V1_SURFACE_MODEL.md)
- [V1_QUANTITY_MODEL.md](./V1_QUANTITY_MODEL.md)
- [V1_QUANTITY_OUTPUT_SCHEMA.md](./V1_QUANTITY_OUTPUT_SCHEMA.md)
- [V1_EARTHWORK_OUTPUT_SCHEMA.md](./V1_EARTHWORK_OUTPUT_SCHEMA.md)
- [V1_SURFACE_OUTPUT_SCHEMA.md](./V1_SURFACE_OUTPUT_SCHEMA.md)
- [V1_CORRIDOR_MODEL.md](./V1_CORRIDOR_MODEL.md)
- [V1_SECTION_MODEL.md](./V1_SECTION_MODEL.md)
- [V1_TIN_ENGINE_PLAN.md](./V1_TIN_ENGINE_PLAN.md)
- [V1_TIN_DATA_SCHEMA.md](./V1_TIN_DATA_SCHEMA.md)
- [V1_TIN_SAMPLING_CONTRACT.md](./V1_TIN_SAMPLING_CONTRACT.md)
- [V1_TIN_CORE_IMPLEMENTATION_PLAN.md](./V1_TIN_CORE_IMPLEMENTATION_PLAN.md)
- [V1_TIN_REVIEW_NEXT_STEP_PLAN.md](./V1_TIN_REVIEW_NEXT_STEP_PLAN.md)
- [V1_PROJECT_TREE_REDESIGN_PLAN.md](./V1_PROJECT_TREE_REDESIGN_PLAN.md)
- [V1_VIEWER_PLAN.md](./V1_VIEWER_PLAN.md)
- [V1_UX_RESET_PLAN.md](./V1_UX_RESET_PLAN.md)
- [V1_ACTION_LABEL_RESET_PLAN.md](./V1_ACTION_LABEL_RESET_PLAN.md)
- [V1_REVIEW_STAGE_SPLIT_PLAN.md](./V1_REVIEW_STAGE_SPLIT_PLAN.md)
- [V1_CROSS_SECTION_VIEWER_EXECUTION_PLAN.md](./V1_CROSS_SECTION_VIEWER_EXECUTION_PLAN.md)
- [V1_CROSS_SECTION_VIEWER_WORK_CHECKLIST.md](./V1_CROSS_SECTION_VIEWER_WORK_CHECKLIST.md)
- [V1_VIEWER_ROUNDTRIP_MANUAL_QA.md](./V1_VIEWER_ROUNDTRIP_MANUAL_QA.md)
- [V1_REAL_DOCUMENT_VIEWER_CHECKLIST.md](./V1_REAL_DOCUMENT_VIEWER_CHECKLIST.md)
- [V1_MAIN_REVIEW_COMMAND_MANUAL_RECORD.md](./V1_MAIN_REVIEW_COMMAND_MANUAL_RECORD.md)
- [V1_MANUAL_QA_QUICKSTART.md](./V1_MANUAL_QA_QUICKSTART.md)
- [V1_PLAN_PROFILE_REVIEW_EXECUTION_PLAN.md](./V1_PLAN_PROFILE_REVIEW_EXECUTION_PLAN.md)
- [V1_EARTHWORK_REVIEW_EXECUTION_PLAN.md](./V1_EARTHWORK_REVIEW_EXECUTION_PLAN.md)
- [V1_SECTION_OUTPUT_SCHEMA.md](./V1_SECTION_OUTPUT_SCHEMA.md)
- [V1_3D_REVIEW_DISPLAY_PLAN.md](./V1_3D_REVIEW_DISPLAY_PLAN.md)
- [V1_EXCHANGE_PLAN.md](./V1_EXCHANGE_PLAN.md)
- [V1_LANDXML_MAPPING_PLAN.md](./V1_LANDXML_MAPPING_PLAN.md)
- [V1_EXCHANGE_OUTPUT_SCHEMA.md](./V1_EXCHANGE_OUTPUT_SCHEMA.md)
- [V1_AI_ASSIST_PLAN.md](./V1_AI_ASSIST_PLAN.md)
- [V1_AI_OUTPUT_SCHEMA.md](./V1_AI_OUTPUT_SCHEMA.md)
- [V1_PLAN_PROFILE_SHEET_PLAN.md](./V1_PLAN_PROFILE_SHEET_PLAN.md)
- [V1_PLAN_OUTPUT_SCHEMA.md](./V1_PLAN_OUTPUT_SCHEMA.md)
- [V1_PROFILE_OUTPUT_SCHEMA.md](./V1_PROFILE_OUTPUT_SCHEMA.md)
- [V1_SHEET_LAYOUT_HINT_SCHEMA.md](./V1_SHEET_LAYOUT_HINT_SCHEMA.md)
- [V1_OUTPUT_STRATEGY.md](./V1_OUTPUT_STRATEGY.md)
- [V1_EARTHWORK_BALANCE_PLAN.md](./V1_EARTHWORK_BALANCE_PLAN.md)
- [V1_IMPLEMENTATION_PHASE_PLAN.md](./V1_IMPLEMENTATION_PHASE_PLAN.md)
- [V1_MODULE_LAYOUT.md](./V1_MODULE_LAYOUT.md)

Rules:

- use `V1_MASTER_PLAN.md` as the reference baseline for new v1 documents
- treat `docsV0/` as archived legacy reference material
- record any intentional deviations from the master plan explicitly

Preferred review workflow:

- start section review from the v1 `Cross Section Viewer`
- start plan/profile review from the v1 `Plan/Profile Viewer`
- start earthwork review from the v1 `Earthwork Viewer`
- use the single `Alignment` command as the first native alignment-source editor for element station ranges and sampled XY rows
- use `Generate Stations (v1)` as the first native station-grid builder after alignment edits
- use `Edit Profile (v1)` as the first native profile-source editor for PVI station/elevation rows
- use the existing v0 viewers as secondary support paths during transition
- use the existing v0 editors only as secondary source-authoring support where a v1-native editor is not available yet
- in the active workbench layout, keep the three v1 review commands grouped ahead of the old review surfaces where practical
- in the active workbench layout, keep the `Corridor` stage centered on `Build Corridor` rather than exposing low-level intermediate generators
- in the active workbench layout, expose `Outputs & Exchange` and `AI Assist` as explicit top-level stages even before their detailed v1-native hubs are fully implemented
- in the active workbench layout, keep `Survey & Surface` aligned to the TIN-first strategy and avoid exposing DEM-first terrain workflow as a primary stage action

UX reset rule:

- treat bridge workflows as temporary implementation support, not as final product UX
- design user-facing v1 workflow from stage intent rather than from old v0 panel boundaries
- avoid exposing `preview`, `bridge`, or migration terminology as normal user actions
- keep implementation-only utilities out of the primary workbench flow
