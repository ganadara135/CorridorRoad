# Unit Scale Refactor Plan

## Current Status
- `PR-1`: completed
- `PR-2`: completed
- `PR-3`: completed
- `PR-4`: completed
- `PR-5`: completed
- `PR-6`: completed
- `PR-7`: completed

## 1. Goal
- Internal geometry and engineering calculations use `meter` as the single canonical unit.
- Unit conversion happens only at the boundary:
  - task-panel input
  - CSV import/export
  - report/display formatting
  - external adapter-specific parsing
- `Project.LengthScale` is not part of the unit model.
- Project coordinate setup and project unit setup are separate concerns.

## 2. Core Policy

### 2.1 Canonical Internal Unit
- All stored engineering length values are meters.
- All geometry/runtime calculations assume meters.
- Default property values are defined in meters.

### 2.2 Conversion Boundary Rule
- Convert incoming user/file values into meters before storing them.
- Convert stored meter values into the selected display/export unit only when showing or exporting them.
- Do not apply a project-wide runtime scale factor inside geometry code.

### 2.3 Coordinate Rule
- CRS/EPSG, origin, and north rotation answer `where`.
- Linear unit display/import/export settings answer `how values are entered and shown`.
- These concerns must not be mixed.

## 3. Project Data Model

### 3.1 Project Unit Properties
- `LinearUnitDisplay`
  - values: `m`, `mm`
  - purpose: task-panel and report formatting
- `LinearUnitImportDefault`
  - values: `m`, `mm`, `custom`
  - purpose: default interpretation for numeric input without explicit unit metadata
- `LinearUnitExportDefault`
  - values: `m`, `mm`, `custom`
  - purpose: default output/report formatting for exports
- `CustomLinearUnitScale`
  - meaning: `meters per user-unit`
  - used only when import/export chooses `custom`

### 3.2 Non-Goal
- `LengthScale` is not used to derive project unit defaults.
- `LengthScale` is not a user workflow control.
- `LengthScale` is not a safe geometric rewrite switch.

## 4. Runtime Rules

### 4.1 Object Storage
- Alignment scalar lengths are meter-native.
- Stationing scalar values are meter-native.
- Typical section scalar values are meter-native.
- SectionSet station inputs and outputs are meter-native.
- Corridor and grading runtime spacing/threshold inputs are meter-native.

### 4.2 UI Behavior
- Task panels read meter-native values and show them in the selected display unit.
- Task panels convert edited values back to meters on apply.
- Completion dialogs and summaries report the active display unit explicitly.

### 4.3 IO Behavior
- CSV/file imports parse numbers into meters immediately.
- CSV/file exports format values using the explicit export unit.
- If an importer has no unit metadata, it uses `LinearUnitImportDefault`.

## 5. Shared Helpers

### 5.1 Unit Policy Module
- Module: `freecad/Corridor_Road/objects/unit_policy.py`

### 5.2 Required Helper Surface
- `get_linear_display_unit(doc_or_project) -> str`
- `get_linear_import_unit(doc_or_project) -> str`
- `get_linear_export_unit(doc_or_project) -> str`
- `get_custom_linear_scale(doc_or_project) -> float`
- `meters_from_user_length(doc_or_project, value, unit="", use_default="import") -> float`
- `user_length_from_meters(doc_or_project, meters, unit="", use_default="display") -> float`
- `format_length(doc_or_project, meters, digits=3, unit="", use_default="display") -> str`
- `meters_from_model_length(doc_or_project, model_value) -> float`
- `model_length_from_meters(doc_or_project, meters) -> float`
- `format_internal_length(doc_or_project, internal_value, digits=3, unit="", use_default="display") -> str`
- `format_internal_area(doc_or_project, internal_area, digits=3, unit="", use_default="display") -> str`
- `format_internal_volume(doc_or_project, internal_volume, digits=3, unit="", use_default="display") -> str`

### 5.3 Helper Rules
- Geometry code uses meter-native values for engineering logic.
- UI code uses formatting helpers instead of manual scale math.
- Import/export code uses conversion helpers instead of direct multiplication.
- Any remaining model-space bridge stays centralized in `unit_policy.py`.

## 6. Scope

### 6.1 Core Objects
- Horizontal alignment
- Stationing
- Typical section
- Assembly template
- Section set
- Corridor
- Design terrain
- Cut/fill
- Point-cloud/DEM tools
- Related display objects and reporting helpers

### 6.2 UI Panels
- Project Setup
- Alignment Editor
- Station Generator
- PVI Editor
- Section Generator
- Corridor
- Design Terrain
- Cut/Fill
- Point Cloud / DEM
- Region-related editors where engineering lengths are displayed

## 7. Project Setup Policy

### 7.1 UI Contract
- Project Setup exposes:
  - `Display Unit`
  - `Default Import Unit`
  - `Default Export Unit`
  - `Custom Unit Scale`
- Project Setup explains clearly:
  - stored geometry remains in meters
  - unit settings affect parsing, display, and export only
  - coordinate setup is separate

### 7.2 Apply Contract
- Applying unit settings updates only the explicit unit properties.
- Applying unit settings does not rescale existing geometry.
- Applying unit settings does not mutate unrelated runtime geometry state.

## 8. Refactor Plan

### PR-1: Introduce Shared Unit Policy
- add `unit_policy.py`
- add explicit project unit properties
- establish meter-native formatting/conversion helpers

### PR-2: Project Setup Split
- replace project-wide scale editing with explicit unit settings
- make Project Setup explain the meter-native storage rule
- separate coordinate workflow from unit workflow

### PR-3: Input/Display Adoption
- update task panels to parse user input into meters
- update task panels to display meter-native values in the selected display unit
- remove ad-hoc scale math from panel defaults, labels, and summaries

### PR-4: Core Runtime Cleanup
- replace direct runtime scale reads in core objects
- migrate scalar property storage to meters
- keep geometry/model-space bridge centralized where still required

### PR-5: Surface, Corridor, Region, and Reporting Cleanup
- extend explicit unit handling into corridor/surface/region panels
- ensure summaries, tables, and completion messages show the chosen unit clearly
- reduce duplicate formatting logic across tools

### PR-6: Remove LengthScale From Unit Behavior
- stop deriving project unit defaults from `LengthScale`
- stop treating `LengthScale` as a runtime unit source
- remove dead compatibility helpers from the unit-policy layer
- keep only the minimum internal bridge required for model-space migration boundaries
- new project schema should not auto-create `LengthScale`
- regression coverage should prefer explicit unit settings over manually seeding `LengthScale`
- schema refresh tests should validate meter-native value preservation instead of legacy scale migration
- `unit_policy` internal/model length helpers now behave as meter-identity conversions
- `legacy_length_scale_is_active()` has been removed from runtime behavior and regression coverage

### PR-7: Final Simplification
- remove any remaining non-essential `LengthScale` dependency from runtime code
- keep the unit model fully explicit and meter-native
- leave only the smallest possible model-space conversion boundary where geometry carriers still require it

## 9. Validation Matrix

### 9.1 Required Checks
- new project defaults to meter display/import/export
- switching display unit changes only shown values, not stored geometry
- custom import/export scale converts correctly at the boundary
- task-panel defaults, suffixes, and summaries stay consistent with the selected display unit
- CSV import/export respects explicit unit settings
- corridor/surface/section workflows remain numerically stable for meter-native storage

### 9.2 Regression Areas
- alignment
- stationing
- profile/PVI
- typical section
- section generation
- corridor
- grading surface
- cut/fill
- point-cloud/DEM
- region editor and timeline tables

## 10. Guardrails

### 10.1 Do Not Do
- do not automatically rescale all existing geometry when the display/import unit changes
- do not mix CRS logic with unit logic
- do not reintroduce per-panel manual scale math
- do not treat `LengthScale` as a recommended workflow control

### 10.2 Must Preserve
- tree structure and project links remain intact
- meter-native projects stay numerically unchanged
- object properties store engineering scalars in meters
- UI/export behavior reflects explicit unit settings consistently

## 11. Documentation Follow-Up
- `docs/ARCHITECTURE.md`
  - describe meter-canonical runtime and boundary-only conversion
- `docs/wiki/Developer-Guide.md`
  - explain helper usage and meter-native storage policy
- `docs/wiki/CSV-Format.md`
  - explain explicit import/export unit rules
- `docs/wiki/Menu-Reference.md`
  - update Project Setup and panel descriptions
- `docs/wiki/Troubleshooting.md`
  - clarify units vs coordinates

## 12. Final Mental Model
- coordinates decide `where`
- meters decide `how big`
- UI/file adapters decide `how users enter and see values`
