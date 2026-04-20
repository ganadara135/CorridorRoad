Date: 2026-03-29

# Practical Sample Set

This document defines the current practical-engineering sample inventory for Long-Term item `8. Expand practical engineering scope`.

It is the source of truth for:
- which sample files are expected to exist under `tests/samples`
- which samples are recommended for each practical workflow
- which regression bundles should be used to keep the practical scope stable

## Current Sample Inventory

### Terrain / Alignment
- `tests/samples/pointcloud_utm_realistic_hilly.csv`
- `tests/samples/alignment_utm_realistic_hilly.csv`

### Profile FG Starter CSVs
- `tests/samples/profile_fg_manual_import_basic.csv`
  - starter `Station,FG` import example for `Edit Profiles -> Import FG CSV`
  - good for first manual FG round-trip checks
- `tests/samples/profile_fg_manual_import_aliases.csv`
  - alias-header example using `PK,DesignElevation`
  - validates flexible header handling in FG import

### Structure Starter CSVs
- `tests/samples/structure_utm_realistic_hilly.csv`
  - baseline simple-geometry structure starter
  - includes `none`, `split_only`, and `skip_zone` corridor modes
- `tests/samples/structure_utm_realistic_hilly_notch.csv`
  - focused notch starter
  - includes `culvert` and `crossing` rows with `CorridorMode=notch`
- `tests/samples/structure_utm_realistic_hilly_template.csv`
  - focused template-geometry starter
  - includes `box_culvert`, `retaining_wall`, and `abutment_block`
- `tests/samples/structure_utm_realistic_hilly_external_shape.csv`
  - focused external-shape starter
  - contains placeholder `ShapeSourcePath` values that must be replaced before field use

### Structure Combined / Profile-Driven CSVs
- `tests/samples/structure_utm_realistic_hilly_station_profile_headers.csv`
- `tests/samples/structure_utm_realistic_hilly_station_profile_points.csv`
- `tests/samples/structure_utm_realistic_hilly_mixed.csv`
- `tests/samples/structure_utm_realistic_hilly_mixed_profile_points.csv`

### Typical Section CSVs
- `tests/samples/typical_section_basic_rural.csv`
- `tests/samples/typical_section_urban_complete_street.csv`
- `tests/samples/typical_section_with_ditch.csv`
- `tests/samples/typical_section_pavement_basic.csv`

## Recommended Scenario Bundles

### 1. Practical Roadway Baseline
- Terrain: `pointcloud_utm_realistic_hilly.csv`
- Alignment: `alignment_utm_realistic_hilly.csv`
- Typical Section: `typical_section_basic_rural.csv`
- Structures: `structure_utm_realistic_hilly.csv`
- Goal:
  - baseline roadway section generation
  - simple structure overlays
  - `skip_zone` / `split_only` corridor checks

### 2. Urban Curb / Sidewalk Workflow
- Terrain: `pointcloud_utm_realistic_hilly.csv`
- Alignment: `alignment_utm_realistic_hilly.csv`
- Typical Section: `typical_section_urban_complete_street.csv`
- Pavement: `typical_section_pavement_basic.csv`
- Goal:
  - advanced practical subassembly contract
  - roadside library summary
  - structured report/export rows

### 3. Ditch / Berm Workflow
- Terrain: `pointcloud_utm_realistic_hilly.csv`
- Alignment: `alignment_utm_realistic_hilly.csv`
- Typical Section: `typical_section_with_ditch.csv`
- Goal:
  - ditch / berm top-edge handling
  - pavement and roadside summary stability
  - downstream `SectionSet -> Corridor -> DesignGradingSurface` checks

### 4. Structure Notch / Template Workflow
- Structures:
  - `structure_utm_realistic_hilly_notch.csv`
  - `structure_utm_realistic_hilly_template.csv`
- Optional profile control:
  - `structure_utm_realistic_hilly_station_profile_headers.csv`
  - `structure_utm_realistic_hilly_station_profile_points.csv`
- Goal:
  - `notch` contract validation
  - template display and section-overlay checks
  - structure-aware station merge and corridor segmentation

### 5. Mixed Practical Workflow
- Terrain: `pointcloud_utm_realistic_hilly.csv`
- Alignment: `alignment_utm_realistic_hilly.csv`
- Typical Section:
  - `typical_section_urban_complete_street.csv`
  - `typical_section_pavement_basic.csv`
- Structures:
  - `structure_utm_realistic_hilly_mixed.csv`
  - `structure_utm_realistic_hilly_mixed_profile_points.csv`
- Goal:
  - mixed `notch` / `split_only` / `skip_zone`
  - structured reports
  - practical status wording
  - downstream grading/corridor stability

### 6. External Shape Starter Workflow
- Structures: `structure_utm_realistic_hilly_external_shape.csv`
- Goal:
  - validate starter CSV format for `GeometryMode=external_shape`
  - validate placeholder-path warning behavior
  - confirm current scope is `external_shape_proxy`, not direct boolean cutting

### 7. Manual FG Import Workflow
- Terrain: `pointcloud_utm_realistic_hilly.csv`
- Alignment: `alignment_utm_realistic_hilly.csv`
- FG import:
  - `profile_fg_manual_import_basic.csv`
  - `profile_fg_manual_import_aliases.csv`
- Goal:
  - validate `Edit Profiles -> Import FG CSV`
  - validate station update + append behavior
  - validate header alias support for manual FG onboarding

## Regression Mapping

### Practical Scope Runner
- Use `tests/regression/run_practical_scope_smokes.ps1`

### Practical Scope Smoke Coverage
- `smoke_practical_subassembly_contract.py`
  - practical subassembly schema baseline
- `smoke_practical_roadside_library.py`
  - reusable roadside bundle expansion and downstream propagation
- `smoke_practical_report_contract.py`
  - structured report rows and export contract
- `smoke_practical_sample_driven_workflow.py`
  - real sample CSV presence and mixed sample-driven workflow
- `smoke_typical_section_pipeline.py`
  - typical section to corridor pipeline
- `smoke_typical_section_pavement_report.py`
  - pavement reporting
- `smoke_structure_station_merge.py`
  - structure station merge and tagging
- `smoke_notch_profile_contract.py`
  - notch schema contract
- `smoke_notch_neighbor_modes.py`
  - notch with neighboring corridor modes
- `smoke_external_shape_earthwork_proxy.py`
  - `external_shape_proxy` earthwork consumption
- `smoke_cutfill_source_matrix.py`
  - comparison source/domain/bin reporting
- `smoke_cutfill_quality_review.py`
  - trust/quality/review summary outputs

## Scope Notes

- `boolean_cut` remains excluded from the current long-term roadmap scope.
- `release-readiness` packaging/documentation work remains excluded from the current long-term roadmap scope.
- `external_shape` is currently validated as `display + proxy earthwork` support.
- `structure_utm_realistic_hilly_external_shape.csv` is a starter file only; it is not a ready-to-run field model because the shape path is intentionally a placeholder.
