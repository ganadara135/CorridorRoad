# CorridorRoad V1 Module Layout

Date: 2026-04-24
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_IMPLEMENTATION_PHASE_PLAN.md`
- `docsV1/V1_MASTER_PLAN.md`

## 1. Purpose

This document defines the recommended code and package layout for implementing CorridorRoad v1 inside the current repository.

It exists to answer:

- where new v1 code should live
- how v1 should coexist with legacy v0 code during transition
- how source, service, result, output, UI, and exchange layers should map to packages

## 2. Core Rule

V1 code should not be mixed directly into the legacy v0 `objects/`, `ui/`, and `commands/` folders unless the file is explicitly acting as a compatibility bridge.

The preferred approach is:

- keep legacy code stable
- create a new explicit v1 package tree
- let thin command and UI adapters call into v1 modules

## 3. Recommended Root Strategy

Inside the existing package:

- current runtime root: `freecad/Corridor_Road/`

Recommended new v1 root:

- `freecad/Corridor_Road/v1/`

This keeps:

- v0 code in place for transition
- v1 code clearly separated by architecture layer
- migration risk lower than attempting a full in-place rewrite on day one

## 4. Why a Dedicated `v1/` Package Is Better

The current layout is strongly v0-shaped:

- `objects/` mixes source intent, derived logic, and helpers
- `ui/` contains editor and viewer code interwoven with logic assumptions
- `commands/` assume older task-panel workflows

A dedicated `v1/` package allows us to:

- implement the new architecture without constant naming collision
- avoid partial rewrites inside legacy files
- keep the migration path understandable

## 5. Recommended High-Level Package Tree

Recommended package tree:

- `freecad/Corridor_Road/v1/`
- `freecad/Corridor_Road/v1/common/`
- `freecad/Corridor_Road/v1/models/`
- `freecad/Corridor_Road/v1/models/source/`
- `freecad/Corridor_Road/v1/models/result/`
- `freecad/Corridor_Road/v1/models/output/`
- `freecad/Corridor_Road/v1/services/`
- `freecad/Corridor_Road/v1/services/evaluation/`
- `freecad/Corridor_Road/v1/services/builders/`
- `freecad/Corridor_Road/v1/services/mapping/`
- `freecad/Corridor_Road/v1/ui/`
- `freecad/Corridor_Road/v1/ui/editors/`
- `freecad/Corridor_Road/v1/ui/viewers/`
- `freecad/Corridor_Road/v1/ui/common/`
- `freecad/Corridor_Road/v1/commands/`
- `freecad/Corridor_Road/v1/exchange/`
- `freecad/Corridor_Road/v1/testing/`

## 6. Recommended Package Roles

### 6.1 `common/`

Purpose:

- shared identity helpers
- schema version helpers
- unit and coordinate context helpers
- shared enums and constants
- lightweight diagnostics utilities

### 6.2 `models/source/`

Purpose:

- durable source-of-truth models only

Typical modules:

- `project_model.py`
- `alignment_model.py`
- `ramp_model.py`
- `intersection_model.py`
- `profile_model.py`
- `superelevation_model.py`
- `assembly_model.py`
- `region_model.py`
- `drainage_model.py`
- `override_model.py`
- `structure_model.py`

### 6.3 `models/result/`

Purpose:

- rebuildable engineering result families

Typical modules:

- `applied_section.py`
- `applied_section_set.py`
- `corridor_model.py`
- `surface_model.py`
- `quantity_model.py`
- `earthwork_balance_model.py`
- `mass_haul_model.py`

### 6.4 `models/output/`

Purpose:

- normalized output contracts only

Typical modules:

- `section_output.py`
- `context_review_output.py`
- `plan_output.py`
- `profile_output.py`
- `drainage_output.py`
- `surface_output.py`
- `quantity_output.py`
- `earthwork_output.py`
- `exchange_output.py`

### 6.5 `services/evaluation/`

Purpose:

- deterministic evaluation services over source models

Typical modules:

- `alignment_evaluation_service.py`
- `ramp_evaluation_service.py`
- `intersection_evaluation_service.py`
- `profile_evaluation_service.py`
- `superelevation_service.py`
- `region_resolution_service.py`
- `drainage_resolution_service.py`
- `override_resolution_service.py`
- `structure_interaction_service.py`
- `tin_sampling_service.py`

### 6.6 `services/builders/`

Purpose:

- build derived result families from sources and evaluated context

Typical modules:

- `applied_section_service.py`
- `corridor_surface_service.py`
- `corridor_solid_service.py`
- `quantity_build_service.py`
- `earthwork_balance_service.py`
- `mass_haul_service.py`

### 6.7 `services/mapping/`

Purpose:

- map results into output contracts
- map external formats into normalized internal contracts

Typical modules:

- `section_output_mapper.py`
- `surface_output_mapper.py`
- `quantity_output_mapper.py`
- `earthwork_output_mapper.py`
- `landxml_mapping_service.py`
- `dxf_mapping_service.py`
- `ifc_mapping_service.py`

### 6.8 `ui/editors/`

Purpose:

- source-editing UI only

Typical modules:

- `alignment_editor.py`
- `ramp_editor.py`
- `intersection_editor.py`
- `profile_editor.py`
- `template_editor.py`
- `region_editor.py`
- `drainage_editor.py`
- `override_manager.py`
- `structure_editor.py`

### 6.9 `ui/viewers/`

Purpose:

- read-only review consumers over outputs and result payloads

Typical modules:

- `cross_section_viewer.py`
- `profile_review_view.py`
- `junction_review_view.py`
- `three_d_review_view.py`
- `earthwork_review_view.py`

### 6.10 `commands/`

Purpose:

- thin command entry points only

Commands should:

- validate the document context
- open an editor or viewer
- dispatch to v1 services

Commands should not own engineering logic.

### 6.11 `exchange/`

Purpose:

- file readers/writers
- exchange package builders
- degraded import/export diagnostics

Typical modules:

- `landxml_import.py`
- `landxml_export.py`
- `dxf_import.py`
- `dxf_export.py`
- `ifc_import.py`
- `ifc_export.py`

## 7. Recommended V1 Skeleton Under Current Repo

Recommended first physical layout:

- `freecad/Corridor_Road/v1/__init__.py`
- `freecad/Corridor_Road/v1/common/__init__.py`
- `freecad/Corridor_Road/v1/models/__init__.py`
- `freecad/Corridor_Road/v1/models/source/__init__.py`
- `freecad/Corridor_Road/v1/models/result/__init__.py`
- `freecad/Corridor_Road/v1/models/output/__init__.py`
- `freecad/Corridor_Road/v1/services/__init__.py`
- `freecad/Corridor_Road/v1/services/evaluation/__init__.py`
- `freecad/Corridor_Road/v1/services/builders/__init__.py`
- `freecad/Corridor_Road/v1/services/mapping/__init__.py`
- `freecad/Corridor_Road/v1/ui/__init__.py`
- `freecad/Corridor_Road/v1/ui/editors/__init__.py`
- `freecad/Corridor_Road/v1/ui/viewers/__init__.py`
- `freecad/Corridor_Road/v1/ui/common/__init__.py`
- `freecad/Corridor_Road/v1/commands/__init__.py`
- `freecad/Corridor_Road/v1/exchange/__init__.py`

## 8. Legacy Coexistence Policy

During transition:

- existing v0 files remain in:
- `freecad/Corridor_Road/objects/`
- `freecad/Corridor_Road/ui/`
- `freecad/Corridor_Road/commands/`

V1 should coexist by:

- adding new v1 modules under `freecad/Corridor_Road/v1/`
- keeping old commands working until replacement commands exist
- gradually redirecting command entry points to v1 implementations

## 9. Command Migration Strategy

Recommended migration path:

1. keep legacy command file names for user-facing continuity where practical
2. move logic into `v1/commands/` and `v1/ui/`
3. leave thin compatibility wrappers in old command files when needed

Example:

- legacy entry: `commands/cmd_view_cross_section.py`
- new logic target: `v1/commands/cmd_view_cross_section.py`
- viewer implementation: `v1/ui/viewers/cross_section_viewer.py`

## 10. Model Naming Strategy

Recommended naming style:

- source models end with `_model.py`
- result models use clear engineering names such as `_set.py`, `_result.py`, `_model.py`
- output payload files end with `_output.py`
- services end with `_service.py`
- mappers end with `_mapper.py`

Avoid:

- `obj_*` naming for v1 modules
- ambiguous "manager" names for core engineering logic
- mixing editor/viewer naming with model naming

## 11. Current-to-V1 Mapping Guidance

Recommended rough mapping from legacy layout:

- legacy `objects/obj_alignment.py` -> v1 `models/source/alignment_model.py` plus `services/evaluation/alignment_evaluation_service.py`
- legacy `objects/obj_vertical_alignment.py` -> v1 `models/source/profile_model.py`
- legacy `objects/obj_typical_section_template.py` -> v1 `models/source/assembly_model.py`
- legacy `objects/obj_region_plan.py` -> v1 `models/source/region_model.py`
- legacy `objects/obj_structure_set.py` -> v1 `models/source/structure_model.py`
- legacy `objects/obj_section_set.py` -> v1 `models/result/applied_section.py` and `applied_section_set.py`
- legacy `objects/obj_corridor.py` -> v1 `models/result/corridor_model.py`
- legacy `objects/obj_cut_fill_calc.py` -> v1 `models/result/earthwork_balance_model.py` and related services

This mapping is conceptual.

It should guide decomposition, not force one-to-one file migration.

## 12. Testing Layout Guidance

Recommended test grouping:

- `tests/contracts/v1/source/`
- `tests/contracts/v1/result/`
- `tests/contracts/v1/output/`
- `tests/services/v1/`
- `tests/exchange/v1/`
- `tests/ui/v1/`

Recommended early focus:

- source identity tests
- TIN and station evaluation tests
- applied-section contract tests
- corridor/surface/quantity/earthwork contract tests
- output schema tests

## 13. UI File Policy

Editor and viewer modules should stay thin.

Recommended rule:

- UI gathers user intent
- UI calls services
- UI renders outputs

UI should not:

- resolve station math itself
- interpret TIN data directly
- compute quantities or earthwork internally
- own exchange mapping logic

## 14. Exchange File Policy

Exchange modules should stay format-focused.

Recommended rule:

- importers normalize into source/result families
- exporters consume normalized outputs and exchange packages

Exchange modules should not:

- invent engineering semantics
- own corridor evaluation logic
- bypass output contracts for convenience

## 15. Near-Term Implementation Recommendation

Recommended first code-generation target:

1. create `freecad/Corridor_Road/v1/`
2. create all package `__init__.py` files
3. add `common/identity.py` and `common/schema.py`
4. add empty source-model skeleton modules
5. add service skeleton modules for geometry and TIN

This gives Phase 1 and early Phase 2 a clear landing zone.

## 16. Acceptance Criteria

This module layout should be considered good enough when:

- every core v1 document maps to a clear package location
- new code can be added without ambiguity about layer ownership
- legacy and v1 code can coexist without constant file collision
- command and UI migration can proceed incrementally

## 17. Anti-Patterns

The following should be avoided:

- putting new v1 engineering logic into legacy `objects/` by default
- adding new `obj_*` files for v1 contracts
- creating direct UI-to-mesh calculation shortcuts
- mixing source, result, and output classes in one module
- letting exchange modules call into random UI code

## 18. Summary

The recommended implementation layout for v1 is:

- keep legacy code where it is for transition
- create a clean `freecad/Corridor_Road/v1/` package tree
- separate source models, result models, output contracts, services, UI, and exchange
- migrate commands through thin wrappers instead of large in-place rewrites

This is the safest module layout for turning the v1 documents into actual code without slipping back into the mixed v0 architecture.
