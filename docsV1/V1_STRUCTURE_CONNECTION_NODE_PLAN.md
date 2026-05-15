# Parametric Road V1 Structure Connection Node Plan

Date: 2026-05-12
Status: Planning baseline before Drainage Pipeline implementation

Current first implementation slice:

- `StructureRow` records explicit `geometry_source_mode` and `native_type`.
- `StructureModel` persists `StructureConnectionPoint` source rows.
- Structures editor Selected Detail exposes `Geometry Source` and `Native Type`.
- Structures editor Selected Detail exposes a `Connection Points` table.
- `Derive Defaults` can create first-slice connection points for culvert/inlet/outlet/headwall-style rows.
- `Pick From 3D` can fill a connection point row from the current FreeCAD 3D selection by projecting the selected point to Alignment station/offset.
- `Preview Points` can show selected Structure connection points as 3D review markers, and row double-click can focus one point.
- Drainage Elements can now store a `connection_point_ref` to a selected Structure connection point.
- External Ref bodies remain separate from connection point endpoints.
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_STRUCTURE_MODEL.md`
- `docsV1/V1_STRUCTURE_GEOMETRY_CONTRACT.md`
- `docsV1/V1_DRAINAGE_IMPLEMENTATION_PLAN.md`
- `docsV1/V1_DRAINAGE_FLOW_ROUTE_IMPLEMENTATION_PLAN.md`

## 1. Purpose

This document defines how Structures should be upgraded before advanced Drainage work.

The immediate goal is to move Structures from visible 3D objects into connection-ready source nodes that Drainage can use to build pipeline segments.

The long-term goal is:

`Structure source node -> connection points -> Drainage Flow Route -> Pipeline Segment -> preview/quantity/solid/exchange`

## 2. Scope

This plan covers:

- Structure roles needed by Drainage.
- Native vs External Structure geometry source behavior.
- Structure connection point source intent.
- External geometry connection point mapping.
- invert and connection elevation requirements.
- structure placement checks before Drainage consumes them.
- Structures UI changes needed before Pipeline authoring.
- validation and review handoff.

This plan does not cover:

- hydraulic calculation.
- automatic pipe sizing.
- final pipe network optimization.
- replacing Structure Output solids.
- renaming internal `CorridorRoad` package, object, or command ids.

## 3. Core Rule

Drainage should not connect directly to anonymous preview geometry.

Drainage should connect to `StructureModel` source rows through explicit connection points.

Structure preview objects remain presentation outputs. They are not the source of pipe endpoints.

## 4. Current Baseline

Current implementation already has:

- `StructureModel`
- `StructureRow`
- `StructurePlacement`
- common and kind-specific geometry specs
- optional external geometry references through `geometry_ref`
- Structure editor presets
- Structure-to-Region assignment
- Structure preview/output handoff
- Drainage Element `structure_ref`
- Flow Route rows that can reference Drainage Elements and Outlet refs

Current limitation:

- visible Structures are not yet formal pipeline nodes
- connection points are implicit
- Native and External geometry source choices are not explicit enough in the editor
- External geometry cannot yet map stable Drainage pipe endpoints
- invert elevations are not consistently exposed as node endpoints
- Drainage Flow review can show route context, but it cannot yet build physical pipe links

## 5. Target Mental Model

Use four distinct layers:

| Layer | Owner | Meaning |
|---|---|---|
| Structure | `StructureModel` | A physical or reference object placed in station space |
| Geometry Source | `StructureModel` | Native parametric shape or external referenced shape |
| Connection Point | `StructureModel` | A named inlet/outlet/port on a Structure |
| Pipeline Segment | Drainage result/output | A generated pipe or channel connection between connection points |

Drainage uses Structures as nodes.
Geometry Source defines the body.
Flow Routes use connection points as endpoints.
Pipeline Segments are evaluated results.

Do not use generated preview faces, Part edge ids, or imported solid face ids as Drainage endpoints.

Drainage endpoints must be stable source ids.

Pipeline network solids are grouped from resolved Drainage pipeline segment outputs, not from Structure preview bodies.

## 5.1 Geometry Source Strategy

Each Structure should have one explicit geometry source mode.

Recommended modes:

| Mode | Meaning | User action | Drainage behavior |
|---|---|---|---|
| `native` | Parametric Road creates a simplified parametric body from source dimensions | choose a Native Type and key dimensions | derive default connection points where possible |
| `external_ref` | Structure uses a referenced FreeCAD object, STEP/IFC import, or other detailed body | choose/pick external object and map anchors | require explicit connection point mapping for Drainage-ready use |

Native and External geometry must share the same connection point contract.

The difference is how the physical body is authored.

Drainage should not care whether the body is native or external once connection points are available.

## 5.2 Native Geometry Authoring Strategy

Native geometry should be a simple parametric shape builder, not a detailed bridge or drainage CAD modeler.

The editor should ask for practical engineering dimensions only.

Recommended Native Types:

| Native Type | Primary use | Key inputs |
|---|---|---|
| `box_culvert` | drainage crossing | width, height, wall thickness, invert, skew, headwall option |
| `pipe_culvert` | drainage crossing | diameter, wall thickness, invert, skew, end treatment |
| `bridge_deck` | bridge/overpass body | deck width, deck thickness, girder depth, barrier height |
| `retaining_wall` | wall body | height, thickness, footing width, side, top mode |
| `headwall` | drainage endpoint | width, height, thickness, invert, opening size |
| `inlet` | drainage intake | width, depth, height, grate/cover type, pipe outlet size |
| `outlet` | drainage discharge | width, height, apron/wingwall option, pipe inlet size |

Default rules:

- Structure length is derived from `Start STA` and `End STA`.
- `Vertical Mode` defaults to `profile_frame`.
- `Length Mode`, internal `Spec Id`, and `Structure Ref` are not primary user-edit fields.
- `Skew`, `Top Elev`, and advanced elevation behavior belong in the selected Structure detail area.
- Native culvert, inlet, outlet, and headwall rows may derive default connection points.

The visible UX should use practical names such as `Box Culvert` instead of internal shape names such as `box`.

## 5.3 External Geometry Connection Mapping Strategy

External geometry is the visible/physical body.

It should not be treated as the source of Drainage topology by itself.

For Drainage-ready external Structures, add explicit connection point mapping rows.

Recommended workflow:

```text
Geometry Source: External Ref
External Object: culvert_headwall_solid
Drainage Ready: Yes

Connection Points
| Point ID | Role | Station | Offset | Invert | Direction | Shape | Size |
| inlet-01 | inlet | 102.500 | -4.000 | 47.200 | upstream | circular | 0.800 |
| outlet-01 | outlet | 104.000 | 4.200 | 46.950 | downstream | circular | 0.800 |
```

External mapping rules:

- map pipe/channel endpoints to `StructureConnectionPoint`, not to external face or edge ids
- store station/offset/elevation or a resolved coordinate plus station context
- keep point ids stable even if the external body is replaced
- allow 3D picking later, but persist the picked result as source-level connection point data
- report warnings when an external Structure is marked Drainage-ready without connection points

First-slice mapping may be manual.

Later versions may add:

- [x] `Pick From 3D`
- station/offset reverse projection
- direction vector inference
- IFC property/name-based port detection
- circular face candidate suggestions

## 6. Structure Role Classification

Structures should be classified by whether they can participate in Drainage.

| Structure kind | Drainage role | Connection behavior |
|---|---|---|
| `inlet` | drainage node | receives surface/ditch flow and outputs to pipe |
| `outlet` | drainage node | receives pipe/channel flow and discharges out |
| `headwall` | drainage node | endpoint structure for culvert or pipe |
| `culvert` | drainage link or node pair | has upstream and downstream endpoints |
| `manhole` | drainage node | joins or redirects pipe segments |
| `junction_box` | drainage node | joins multiple pipe/channel paths |
| `retaining_wall` | corridor structure | may carry weep/drain refs later, not a default pipeline node |
| `bridge` | corridor structure | not a default pipeline node |

Initial implementation should prioritize:

- `culvert`
- `inlet`
- `outlet`
- `headwall`
- `manhole`
- `junction_box`

## 7. Connection Point Contract

Add or derive a source row family for structure connection points.

Recommended object family:

- `StructureConnectionPoint`

Recommended fields:

- `connection_point_id`
- `structure_ref`
- `point_role`
- `station`
- `offset`
- `elevation`
- `invert_elevation`
- `diameter`
- `width`
- `height`
- `shape_kind`
- `direction`
- `connection_order`
- `region_ref`
- `notes`

Recommended `point_role` values:

- `inlet`
- `outlet`
- `upstream`
- `downstream`
- `left_port`
- `right_port`
- `pipe_in`
- `pipe_out`
- `overflow`

Core rule:

Connection point ids should be stable and referenced by Drainage.

Example:

```text
structure:culvert-01
  connection:culvert-01:upstream
  connection:culvert-01:downstream
```

## 8. Derived Defaults

The editor may derive connection points from existing geometry specs when explicit rows do not exist.

Examples:

- box culvert -> upstream/downstream points from placement start/end and invert elevation
- inlet -> one inlet point and one pipe_out point
- outlet/headwall -> one pipe_in point and one discharge outlet point
- manhole -> one or more pipe_in/pipe_out points

Derived defaults are allowed for preview and first-slice validation.

Durable source rows should be created before Drainage Pipeline authoring becomes editable.

## 9. Placement And Elevation Requirements

For Drainage-ready Structures, validate:

- `structure_id` exists and is unique
- `structure_kind` is a supported Drainage node kind
- `StructurePlacement.region_ref` is assigned
- placement station range is inside the referenced Region
- connection point station is inside the placement range or explicitly allowed as an extension
- connection point has an invert or connection elevation
- circular pipe endpoints have diameter
- box endpoints have width and height
- direction is known or derivable

Elevation sources should follow this priority:

1. explicit connection point `invert_elevation`
2. kind-specific geometry spec invert field
3. placement elevation reference plus vertical offset rule
4. profile/terrain fallback with warning

## 10. Structures UI Plan

The Structures panel should be upgraded before Drainage Pipeline UI.

### Main Table

Keep the main Structures table compact.

Recommended visible columns:

- `Structure ID`
- `Kind`
- `Region`
- `Start STA`
- `End STA`
- `Offset`
- `Role`
- `Drainage Ready`

### Detail Area

Add a detail area or tab for selected Structure.

Recommended tabs:

- `Geometry`
- `Connection Points`
- `Preview`
- `Diagnostics`

The `Geometry` detail area should expose:

- `Geometry Source`: `Native` or `External Ref`
- Native Type and simple dimensions when `Native` is selected
- `External Geometry Ref` and anchor/mapping controls when `External Ref` is selected

The main Structures table should not show this field because native v1 geometry is managed through the selected Structure detail area.

The visible `Geometry Specs` table is removed from the Structures panel.

Common native geometry fields such as shape, width, height, vertical mode, elevations, skew, material, and notes are edited in `Selected Structure Detail`.

The underlying `StructureGeometrySpec` rows remain an internal source contract.

The user should not need to edit `Spec Id`, `Structure Ref`, or `Length Mode` in the main table.

Those values are internal source links or advanced behavior.

### Connection Points Tab

Recommended columns:

- `Point ID`
- `Role`
- `Station`
- `Offset`
- `Invert`
- `Shape`
- `Size`
- `Direction`
- `Status`

Recommended actions:

- `Add Point`
- `Delete Point`
- `Derive Defaults`
- [x] `Pick From 3D`
- [x] `Preview Points`
- `Validate`

For Native geometry, `Derive Defaults` should create practical points from the selected Native Type.

For External Ref geometry, `Pick From 3D` should be a review/authoring helper, but the persisted result must still be a stable `StructureConnectionPoint` row.

First-slice behavior:

- read the current FreeCAD 3D selection
- accept selected vertex, edge/face/object center, or object placement
- project XY to the nearest Alignment segment
- fill `STA`, `Offset`, `Elev`, and `Invert`
- mark the row notes with `picked_from_3d`
- show connection point markers as `V1StructureConnectionPointPreview`
- route connection point preview objects into the Structures project-tree group

## 11. 3D Review Plan

Structure preview should distinguish:

- physical structure body
- connection points
- active selected structure
- drainage-ready vs incomplete nodes

Recommended first-slice display:

- structure body: existing preview color
- connection point: small non-solid marker or short axis tick
- selected connection point: highlighted marker
- incomplete drainage node: warning color in review only

Connection point markers are review helpers.
They should not be used as editable geometry.

## 12. Drainage Handoff Rule

Drainage should reference connection points instead of only Structure ids once this plan is implemented.

Current first-slice:

```text
DrainageElementRow.structure_ref = structure:culvert-01
```

Target:

```text
DrainageElementRow.structure_ref = structure:culvert-01
DrainageElementRow.connection_point_ref = connection:culvert-01:upstream
```

First-slice editor behavior:

- Drainage Elements keep `Structure Ref`.
- non-ditch rows expose a `Connection Point` combo.
- the combo is populated from the selected Structure's `StructureConnectionPoint` rows.
- validation reports missing connection point refs when a StructureModel is available.

Flow Route target:

```text
from_connection_ref -> to_connection_ref
```

Fallback rule:

If no connection point exists, Drainage may resolve the default connection point for the referenced Structure and report a warning.

## 13. Validation

Structure validation should add Drainage-readiness diagnostics.

Recommended diagnostics:

- missing Region assignment
- placement outside Region boundary
- missing geometry source mode
- missing Native Type for native geometry
- missing external object ref for external geometry
- external drainage-ready Structure has no mapped connection points
- unsupported drainage node kind
- missing connection points
- duplicate connection point ids
- missing invert elevation
- missing endpoint size
- invalid endpoint direction
- connection point outside placement station range
- culvert has only one endpoint
- inlet has no pipe_out point
- outlet has no pipe_in or discharge point

Diagnostic severity:

- `error`: source cannot be consumed safely
- `warning`: source can be previewed, but Pipeline output should be blocked or degraded
- `info`: source is complete enough for review

## 14. Implementation Order

### S1. Documentation Baseline

- Add this plan.
- Update `V1_STRUCTURE_MODEL.md` with connection-point ownership.
- Update `docsV1/README.md`.

Acceptance:

- Structures are documented as Drainage-ready nodes.
- Drainage Pipeline dependency on Structures is explicit.

### S2. Source Contract

- [x] Add explicit geometry source mode to Structure source rows or linked geometry source rows.
- [x] Keep Native geometry dimensions in normalized spec rows.
- [x] Keep External Ref body references separate from connection points.
- [x] Add `StructureConnectionPoint` dataclass.
- [x] Add rows to `StructureModel`.
- [x] Persist rows on `V1StructureModel`.
- Keep old Structure rows valid.

Acceptance:

- [x] Native and External geometry source modes are distinguishable from source rows.
- [x] External geometry references do not replace connection point rows.
- [x] Structure connection points round-trip through document object persistence.
- [x] Existing Structure tests still pass.

### S3. Validation Service

- Extend Structure validation for connection point diagnostics.
- Validate Region boundary consistency.
- Validate kind-specific endpoint requirements.

Acceptance:

- invalid culvert/inlet/outlet examples report targeted diagnostics.

### S4. Structures UI

- [x] Move Geometry Specs editing into the selected Structure detail flow.
- [x] Add `Geometry Source` selection.
- [x] Add Native Type selector for box culvert, pipe culvert, bridge deck, wall, headwall, inlet, and outlet.
- [x] Add simple type-specific Native geometry forms for box culvert, pipe culvert, bridge deck, wall, headwall, inlet, and outlet.
- [x] Reflect pipe culvert circular Native geometry in 3D preview and derived connection point defaults.
- [x] Derive inlet, outlet, and headwall connection point roles for pipeline handoff, including `pipe_out`, `pipe_in`, and `discharge`.
- Keep external body references under `External Ref`.
- [x] Add first-slice `Connection Points` table in selected Structure detail.
- [x] Add derive-default action for culvert/inlet/outlet/headwall-style rows.
- Add manual connection-point mapping for External Ref Structures.
- Add row-level validation status.

Acceptance:

- user can author a simple Native Structure without editing internal ids.
- user can map Drainage-ready connection points onto an External Ref Structure.
- [x] user can create or derive connection points without opening Drainage.

### S5. Structure Preview

- Show selected Structure body.
- Show connection points for selected Structure.
- Avoid creating permanent marker clutter.

Acceptance:

- selected Structure and its connection points can be reviewed in 3D.

### S6. Drainage Handoff Preparation

- Expose connection point choices to Drainage.
- Keep `structure_ref` compatibility while adding `connection_point_ref`.
- Document Flow Route endpoint migration.
- [x] Make Flow Routes consume connection point endpoints before building physical pipe segments.
- [x] Add first-slice pipeline segment candidates in Drainage Review from Flow Route endpoint connection points.
- [x] Add a lightweight 3D preview object for selected Drainage pipeline candidates.
- [x] Promote ready pipeline candidates into `DrainagePipelineSegment` result rows and dedicated Drainage output rows.
- [x] Add a lightweight 3D preview object for selected resolved Drainage pipeline segments.

Acceptance:

- Drainage can choose a Structure connection point as an endpoint.
- Drainage Review can report ready or incomplete pipeline segment candidates without reading generated preview geometry.
- Drainage Review pipeline candidate preview remains output-only and traceable to Flow Route and Structure connection point refs.
- Drainage Pipeline result rows are generated only from ready endpoint pairs and remain traceable to Flow Route and Structure connection point refs.
- Pipeline previews use the active Alignment station/offset frame when it exists, while preserving a fallback mode for documents that do not yet have an Alignment source.
- Pipeline preview geometry is fed by Drainage output `pipeline_geometry_rows`, not by Structure preview geometry or UI-only reconstruction.
- Ready pipeline geometry can produce first-slice capped pipe solid candidates and `drainage_pipeline_body` Watertight Solid targets.
- Ready pipeline solid candidates can be grouped into a `pipeline_network_rows` output contract and a `drainage_pipeline_network_body` Watertight Solid target.
- Grouped pipeline network rows can be reviewed as a 3D network preview without using Structure preview geometry as source.
- Pipeline network endpoint junctions are exposed as output rows before trimming, keeping Structure connection provenance visible for the later watertight connection step.
- Pipeline terminal rows preserve Structure connection point refs when available.
- Watertight pipeline network output carries Structure refs and connection point refs forward from terminal rows.
- The first network solid build adds junction connector bodies for degree greater than one endpoint junctions and terminal connector bodies for Structure-backed endpoints, tries best-effort boolean fuse, and falls back to a compound of capped segment solids.
- Watertight Solids can build a first-slice `structure_body` output directly from the StructureModel native geometry spec through `StructureSolidOutputService`.
- `pipe_culvert` and circular culvert native bodies build as cylindrical Part solids rather than rectangular envelopes.
- Circular culverts with `wall_thickness` build as hollow pipe wall solids by cutting the inner pipe volume from the outer cylinder.
- External Ref Structures can reuse a referenced FreeCAD object's Shape as the `structure_body` output when `geometry_ref` resolves to a document object.
- External Ref Structures that are Drainage-ready are blocked from Watertight Solid target discovery until they have at least one mapped source-level connection point.
- External Ref Structure body validation checks mapped connection point coordinates against the referenced Shape bounding box and blocks the build when points are outside the body tolerance.
- Drainage pipeline network builds auto-build available matching Structure body targets before network fuse.
- Structure-backed pipe terminals can add first-slice port bridge connector bodies when the terminal point does not overlap the Structure body.
- Port bridge connector sizing and direction prefer the owning Structure connection point fields before falling back to pipe diameter and Structure body center.
- Structure-backed pipe terminals that start inside a matched Structure body bounding box are trimmed to the Structure body exit face before pipe and connector solids are built.
- Native `inlet`, `outlet`, and `headwall` Structure bodies use their source connection point offset and invert/elevation as first-slice body placement when the Structure placement has no explicit offset.
- Native `inlet` Structure bodies build as a rectangular body with an internal chamber cut.
- Native `outlet` and `headwall` Structure bodies build as rectangular headwall bodies with a pipe opening cut from the owning connection point diameter when available.
- When matching `structure_body` Watertight Solid output objects already exist, the network solid build includes those Structure body shapes in the fuse input and records the matched output refs.
- Detailed wingwalls, inlet grates, external face/port inference, and terrain interaction remain later implementation steps.

## 15. Acceptance Criteria For Structures Before Drainage Pipeline

Drainage Pipeline work should not start until:

- Drainage-ready Structure kinds are classified.
- Native and External geometry source modes are explicit.
- Native geometry can be authored through simple type-specific fields.
- External geometry can be mapped to stable connection points.
- connection point source rows are persisted.
- at least culvert/inlet/outlet defaults can be derived.
- Structures UI exposes connection points.
- validation reports missing invert/size/Region context.
- 3D review can show selected connection points.

## 16. Non-goals

This plan does not make Parametric Road a hydraulic design package.

It does not size pipes automatically.

It does not require all Structures to be Drainage nodes.

It does not replace Structure Output solids.

It prepares source-level Structure nodes so Drainage can later build traceable pipeline results.
