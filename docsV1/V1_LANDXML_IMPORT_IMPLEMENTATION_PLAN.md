# Parametric Road V1 LandXML Import Implementation Plan

Date: 2026-05-31
Branch: `v1-0503`
Status: Draft implementation plan
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_ARCHITECTURE.md`
- `docsV1/V1_EXCHANGE_PLAN.md`
- `docsV1/V1_LANDXML_MAPPING_PLAN.md`
- `docsV1/V1_ALIGNMENT_MODEL.md`
- `docsV1/V1_PROFILE_MODEL.md`
- `docsV1/V1_TIN_DATA_SCHEMA.md`
- `docsV1/V1_COORDINATE_IMPORT_POLICY.md`

## 1. Purpose

This document defines how Parametric Road v1 should implement LandXML import.

The first implementation target is Autodesk Civil 3D LandXML only.

OpenRoads Designer LandXML and other producer dialects are future compatibility targets and must not be presented as supported in the first user-facing workflow.

The goal is to read externally designed road data and normalize it into v1 source and result contracts so the existing workflow can continue through:

1. Alignment
2. Stations
3. Profile
4. 3D Centerline
5. Superelevation
6. Assembly and Regions
7. Applied Sections
8. Build Parametric
9. Watertight Solids and exchange outputs

## 2. Scope

Initial LandXML import should support Autodesk Civil 3D LandXML content for:

- horizontal alignments
- profile PVI and vertical curve data where practical
- station range and station equation context where practical
- TIN surface points and triangle faces
- CgPoints as survey/reference points
- feature-line references as source references or diagnostics
- import diagnostics and provenance

Deferred scope:

- OpenRoads Designer LandXML compatibility
- unknown-producer LandXML compatibility
- direct full-corridor reconstruction from LandXML
- automatic Assembly creation from LandXML cross sections
- automatic Region creation from LandXML corridor regions
- drainage network reconstruction beyond reference mapping
- structure import beyond reference diagnostics
- guaranteed round-trip equivalence with Civil 3D
- guaranteed round-trip equivalence with every LandXML producer

## 3. Core Rule

LandXML import must not create editable engineering truth directly from display geometry.

The import pipeline must normalize external content into v1 contracts:

- LandXML alignments -> `AlignmentModel`
- LandXML profiles -> `ProfileModel`
- LandXML surfaces -> TIN source/result contracts
- LandXML points -> survey/reference source objects
- unsupported content -> diagnostics and provenance records

Generated FreeCAD shapes, previews, and meshes are review outputs only.

The first implementation must reject or warn on non-Civil 3D producer metadata instead of silently treating every LandXML file as supported.

## 4. Architecture

### 4.1 Import layers

Implementation should use four layers:

1. XML reader
2. LandXML semantic parser
3. v1 normalization service
4. FreeCAD document writer

The parser should not create FreeCAD objects directly.

The document writer should not contain LandXML-specific engineering rules.

### 4.2 Proposed modules

Recommended module layout:

- `freecad/Corridor_Road/v1/exchange/landxml_import.py`
- `freecad/Corridor_Road/v1/exchange/landxml_import_contracts.py`
- `freecad/Corridor_Road/v1/exchange/landxml_alignment_mapper.py`
- `freecad/Corridor_Road/v1/exchange/landxml_profile_mapper.py`
- `freecad/Corridor_Road/v1/exchange/landxml_surface_mapper.py`
- `freecad/Corridor_Road/v1/commands/cmd_landxml_import.py`

Optional later UI:

- `freecad/Corridor_Road/v1/ui/editors/landxml_import_panel.py`

### 4.3 Internal contracts

The import layer should return an intermediate result before writing to the document.

Suggested contract families:

- `LandXMLImportResult`
- `LandXMLImportSummary`
- `LandXMLImportDiagnostic`
- `LandXMLAlignmentCandidate`
- `LandXMLProfileCandidate`
- `LandXMLSurfaceCandidate`
- `LandXMLPointCandidate`
- `LandXMLFeatureCandidate`

These contracts should preserve:

- source file path
- detected producer
- supported producer status
- LandXML version if available
- unit interpretation
- coordinate interpretation
- source element id/name
- imported object count
- skipped object count
- degradation decisions
- warnings and errors

## 5. Import Workflow

### 5.1 User workflow

Recommended UI flow:

1. User opens `Outputs & Exchange`.
2. User clicks `Import LandXML`.
3. User selects a `.xml` or `.landxml` file.
4. Import panel previews discovered content.
5. Panel clearly shows `Supported source: Autodesk Civil 3D LandXML`.
6. User selects which supported Civil 3D content to import.
7. User reviews diagnostics.
8. User clicks `Apply`.
9. Parametric Road creates or updates v1 source/result objects.
10. User continues with Stations, Profile, 3D Centerline, and downstream build stages.

The panel also provides `Preset Data` for a packaged Civil 3D starter LandXML file.

The preset is for onboarding and smoke testing only; it must follow the same scan-first and no-document-mutation behavior as a user-selected external file.

The packaged `Civil 3D Starter Road` preset should be large enough to exercise practical workflows:

- one multi-element road alignment
- one finished-grade profile with multiple PVI rows
- one existing-ground TIN surface with dozens of points and faces
- multiple CgPoints for survey/reference context

The panel should also show the immediate next workflow so users understand what to do after import:

```text
Next workflow: LandXML Import -> Stations -> 3D Centerline -> Superelevation -> Assembly -> Regions -> Structures/Drainage -> Build Sections
```

### 5.2 Supported format UX

The import panel must show the supported format near the top, before file scanning details.

Recommended text:

```text
Supported source: Autodesk Civil 3D LandXML
Supported content: Alignment, Profile, TIN Surface, CgPoints
Not supported in this phase: OpenRoads LandXML, full Corridor reconstruction, Pipe Networks, Assemblies, Regions
```

If the selected file is not recognized as Civil 3D LandXML, the panel should show:

```text
Producer: Unknown or unsupported
Status: Not supported in this phase
```

The user may still view diagnostics, but `Import Selected` should stay disabled unless a future explicit "experimental import" mode is added.

### 5.3 Tree placement

Imported objects should be routed to the normal v1 tree:

- alignments -> `02_Alignment & Profile / Alignments`
- profiles -> `02_Alignment & Profile / Profiles`
- survey points -> `01_Source Data / Survey Points`
- TIN source data -> `03_Surfaces / Existing Ground TIN / Source`
- TIN result or preview -> `03_Surfaces / Existing Ground TIN / TIN Result`
- import diagnostics -> `09_Outputs & Exchange / LandXML` or exchange package diagnostics

If a dedicated `LandXML Imports` group is added later, it should store provenance and diagnostics, not replace the normalized source objects.

## 6. Mapping Rules

### 6.1 Alignment

Import target:

- `AlignmentModel`

Required mapping:

- alignment name/id
- ordered horizontal elements
- start station if available
- tangent segments
- circular curves where available
- station equations where available

Supported fallback:

- unsupported transition or compound geometry may become sampled alignment geometry only if diagnostics clearly mark the degradation.

Diagnostics:

- unsupported geometry type
- invalid element order
- non-continuous geometry
- missing station reference
- unit or coordinate uncertainty

### 6.2 Profile

Import target:

- `ProfileModel`

Required mapping:

- profile name/id
- station/elevation rows
- PVI rows where available
- vertical curve parameters where supported
- parent alignment reference where available

Diagnostics:

- profile without matching alignment
- profile station outside alignment range
- unsupported vertical curve type
- duplicate profile rows
- elevation unit uncertainty

### 6.3 Surface and TIN

Import target:

- TIN source/result contract

Required mapping:

- points
- faces/triangles
- surface name/id
- optional breaklines and boundaries where available

Diagnostics:

- missing point reference
- invalid triangle
- duplicate point id
- non-manifold or degenerate faces
- boundary import skipped

### 6.4 Survey points

Import target:

- survey/reference source object

Required mapping:

- point id
- local or world coordinate
- elevation
- description where available

Coordinate conversion must follow `V1_COORDINATE_IMPORT_POLICY.md`.

### 6.5 Feature lines

Initial handling:

- import as reference features when cleanly mappable
- otherwise store diagnostics and provenance only

Feature lines must not silently become corridor source truth.

## 7. Unit and Coordinate Policy

LandXML import must resolve:

- linear unit
- angular unit where relevant
- coordinate basis
- elevation unit
- local/world interpretation

Rules:

- use project coordinate setup when available
- follow `V1_COORDINATE_IMPORT_POLICY.md`
- preserve original coordinates in provenance when practical
- do not silently rescale mixed-unit files
- warn when units are missing or ambiguous

## 8. Diagnostics

Every import run should produce diagnostics.

Diagnostic severity:

- `info`
- `warning`
- `error`

Errors should block document writing only for the affected item, not necessarily the whole file.

Examples:

- `landxml_civil3d_source_detected`
- `landxml_unsupported_producer`
- `landxml_alignment_imported`
- `landxml_profile_imported`
- `landxml_surface_imported`
- `landxml_unsupported_geometry`
- `landxml_profile_without_alignment`
- `landxml_station_outside_alignment_range`
- `landxml_invalid_tin_face`
- `landxml_unit_ambiguous`

## 9. Implementation Order

### Phase LX-I1 - Contract and sample fixtures

Status: Done

Tasks:

- [x] add import contract dataclasses
- [x] add small Civil 3D LandXML sample files for alignment, profile, and surface
- [x] add unsupported-producer LandXML sample file
- [x] add parser unit tests that do not require FreeCAD GUI

Acceptance criteria:

- [x] parser returns `LandXMLImportResult`
- [x] parser reports detected producer and supported producer status
- [x] diagnostics are structured
- [x] no FreeCAD document object is created in parser tests

Implemented baseline:

- `landxml_import_contracts.py` defines import result, summary, diagnostic, alignment, profile, surface, and point candidates.
- `landxml_import.py` scans Civil 3D LandXML files without mutating the FreeCAD document.
- Tests cover Civil 3D detection, Alignment/Profile/TIN/CgPoints candidate counts, unsupported producer diagnostics, and parse failure diagnostics.

### Phase LX-I2 - Alignment import MVP

Status: Done

Tasks:

- [x] parse alignment names and horizontal geometry
- [x] map tangents and circular curves into `AlignmentModel`
- [x] create/update v1 alignment source object
- [x] route object under `02_Alignment & Profile / Alignments`

Acceptance criteria:

- [x] imported alignment is stored as a v1 Alignment object and routed under the v1 Alignment tree
- [x] imported alignment can be converted back to `AlignmentModel`
- [x] unsupported geometry produces diagnostics in the parser
- [ ] UI command/panel flow appears in the user-facing Alignment import workflow
- [ ] station generation from imported alignment is covered by focused integration tests

Implemented baseline:

- `landxml_alignment_mapper.py` maps `LandXMLAlignmentCandidate` rows into `AlignmentModel`.
- The mapper creates or updates a FreeCAD `V1Alignment` object without duplicating the same imported Alignment ID.
- Focused FreeCADCmd tests confirm v1 tree routing and object-to-model conversion.

### Phase LX-I3 - Profile import MVP

Status: Done

Tasks:

- [x] parse profile rows
- [x] map profile station/elevation data into `ProfileModel`
- [x] link profile to imported or selected alignment
- [x] create/update v1 profile source object

Acceptance criteria:

- [x] imported profile is stored as a v1 Profile object and routed under the v1 Profile tree
- [x] imported profile can be converted back to `ProfileModel`
- [x] imported profile keeps the linked imported Alignment ID
- [x] imported profile appears in the Profile panel through the user-facing LandXML import workflow
- [x] 3D Centerline can be built from imported Alignment/Profile through focused integration tests
- [x] station range diagnostics are visible in the import panel

Implemented baseline:

- `landxml_profile_mapper.py` maps `LandXMLProfileCandidate` rows into `ProfileModel`.
- The mapper creates or updates a FreeCAD `V1Profile` object without duplicating the same imported Profile ID.
- Focused FreeCADCmd tests confirm v1 tree routing, Alignment ID linking, and object-to-model conversion.

### Phase LX-I4 - Surface/TIN import MVP

Status: Done

Tasks:

- [x] parse surface points and triangle faces
- [x] normalize into TIN contract
- [x] create result objects under the v1 surface tree
- [x] show imported surface preview where practical

Acceptance criteria:

- [x] imported TIN can be previewed as a mesh object
- [x] invalid faces are diagnosed by the parser before mapper creation
- [x] imported surface summary routes under `03_Surfaces / Existing Ground TIN / TIN Result`
- [x] imported TIN preview routes under `03_Surfaces / Existing Ground TIN / Mesh Preview`
- [ ] terrain sampling can use the imported TIN through focused integration tests

Implemented baseline:

- `landxml_surface_mapper.py` maps `LandXMLSurfaceCandidate` rows into `TINSurface`.
- The mapper creates or updates a v1 `SurfaceModel` summary object with `tin_surface_result` routing.
- The mapper creates or updates a reusable mesh preview through `TINMeshPreviewMapper`.
- Focused FreeCADCmd tests confirm result-tree routing, mesh-preview routing, and object-to-model conversion.

### Phase LX-I5 - Import command and panel

Status: Done

Tasks:

- [x] add `Import LandXML` command under `Outputs & Exchange`
- [x] add file picker
- [x] add packaged Civil 3D `Preset Data` sample
- [x] show the supported source as `Autodesk Civil 3D LandXML`
- [x] show discovered content summary
- [x] allow supported Civil 3D import through `Import Selected`
- [x] disable import for unsupported producer status
- [x] show diagnostics before `Apply`

Acceptance criteria:

- [x] opening the panel does not mutate the document
- [x] loading `Preset Data` fills the file path and scans a packaged Civil 3D LandXML sample
- [x] `Scan File` reads the LandXML file and reports supported producer status
- [x] `Import Selected` writes normalized Alignment, Profile, and TIN Surface objects
- [x] import summary is visible after apply
- [x] unsupported producer import is blocked
- [ ] row-level item selection is available for partial import

Implemented baseline:

- `cmd_landxml_import.py` adds `Import LandXML` under `Outputs & Exchange`.
- The panel shows `Supported source: Autodesk Civil 3D LandXML` and the supported/unsupported scope at the top.
- The panel shows the next workflow through `Build Sections` near the top.
- The panel includes a `Civil 3D Starter Road` preset that fills the file path with a packaged LandXML sample and scans it.
- The panel uses scan-first behavior; unsupported producers keep import disabled.
- Headless command tests cover the shared import function, command resources, and output workflow grouping.

### Phase LX-I6 - Provenance and exchange package integration

Status: Done

Tasks:

- [x] persist import provenance
- [x] record source file and mapping decisions
- [x] expose import diagnostics in an exchange-tree provenance object
- [x] prepare future re-import/update behavior

Acceptance criteria:

- [x] imported objects identify their LandXML source context
- [x] diagnostics can be inspected after closing the import panel
- [x] re-import updates the same provenance object for the same source file
- [x] provenance routes under `09_Outputs & Exchange / Exchange Packages`
- [ ] richer exchange package payload integration is available for downstream export workflows

Implemented baseline:

- `obj_landxml_import.py` stores one LandXML import provenance object per source file.
- The provenance object records source path, LandXML version, detected producer, supported-producer status, imported object refs, counts, and diagnostic rows.
- The shared import function creates or updates the provenance object after importing supported Civil 3D Alignment, Profile, and TIN Surface content.
- Focused FreeCADCmd tests confirm provenance update behavior and exchange tree routing.

## 10. Testing Plan

Focused tests:

- parser contract tests
- alignment mapper tests
- profile mapper tests
- TIN mapper tests
- coordinate/unit conversion tests
- FreeCAD object creation smoke tests
- tree routing tests

Recommended sample files:

- Civil 3D simple tangent-only alignment
- Civil 3D tangent plus circular curve alignment
- Civil 3D alignment plus profile
- Civil 3D TIN surface with valid triangles
- Civil 3D TIN surface with one invalid face
- Civil 3D unsupported geometry fixture
- unsupported-producer fixture

## 11. UI Plan

Initial command placement:

- `Outputs & Exchange / Import LandXML`

Panel sections:

- Supported Format
- File
- Discovered Content
- Import Targets
- Units and Coordinates
- Diagnostics
- Apply / Close

The panel should avoid advanced mapping settings at first.

Default behavior should be:

- show `Supported source: Autodesk Civil 3D LandXML`
- read-only preview after file selection
- no document mutation until `Apply`
- import selected items only
- block import for unsupported producer status
- diagnostics always visible

The support matrix should be short and explicit:

| Content | Status | Target |
|---|---|---|
| Civil 3D Alignment | Supported | `AlignmentModel` |
| Civil 3D Profile | Supported | `ProfileModel` |
| Civil 3D TIN Surface | Supported | Existing Ground TIN |
| Civil 3D CgPoints | Supported | Survey Points |
| Civil 3D Breaklines | Partial | TIN source/reference |
| Civil 3D Superelevation | Future | `SuperelevationModel` |
| Civil 3D Pipe Networks | Future | `DrainageModel` |
| Civil 3D Corridor/Carriageways | Not supported | Diagnostics only |
| OpenRoads LandXML | Not supported in this phase | Diagnostics only |

## 12. Risks

| Risk | Mitigation |
|---|---|
| Civil 3D export option differences | Start with small supported subset and diagnostic fallback. |
| Users expect OpenRoads support | Show `Supported source: Autodesk Civil 3D LandXML` clearly in the panel and block unsupported producer import. |
| Unsupported spiral or vertical curve types | Preserve provenance and degrade only with explicit diagnostics. |
| Coordinate/unit ambiguity | Use project coordinate policy and warn before writing. |
| Imported data bypasses v1 source ownership | Keep parser separate from document writer and always normalize into source/result contracts. |
| Full corridor import expectation grows too early | Document corridor reconstruction as deferred. |
| Surface import creates unstable meshes | Validate TIN faces before preview/result creation. |

## 13. Non-goals

- full LandXML specification compliance in the first implementation
- OpenRoads Designer LandXML import in the first implementation
- direct conversion of LandXML corridors into final Build Parametric outputs
- automatic Assembly, Region, Drainage, or Structure authoring from LandXML
- hidden overwrite of existing user-authored source objects
- treating LandXML as the internal data model

## 14. First Implementation Candidate

The recommended first coding task is Phase LX-I1 plus the parser shell:

1. replace the current `landxml_import.py` placeholder with a parser facade
2. add import contract dataclasses
3. add one tiny Civil 3D LandXML alignment fixture
4. add a focused parser test

This creates a safe foundation before document-writing behavior is introduced.
