# V1 Supported Domain Status

Status date: 2026-07-14

This is the single current-scope index for Parametric Road v1.

When an older plan, release note, wiki draft, or historical record conflicts with this index, this index and `AGENTS.md` define the active development scope.

## Runtime Policy

| Item | Current value |
| --- | --- |
| Public release | Parametric Road `1.0.9` |
| Package compatibility floor | FreeCAD `1.0.3` from `package.xml` |
| Recommended FreeCAD | FreeCAD `1.1.1` |
| Development and validated FreeCAD | FreeCAD `1.1.1` |
| Minimum Python | Python `3.10` |
| CI policy | Existing CI is frozen; additional CI development is prohibited |

The compatibility floor is package metadata, not a claim that the complete Phase 5 matrix was rerun on FreeCAD 1.0.3. Current engineering and manual QA conclusions apply to FreeCAD 1.1.1.

## Domain Status and Ownership

| Domain | Status | Source owner | Evaluated/result owner | Output or review boundary | Current exclusions |
| --- | --- | --- | --- | --- | --- |
| Project | Supported | Project properties and design standard | resolved project context | tree and property review | no generated geometry as project truth |
| TIN | Supported | terrain/TIN source and replayable edit operations | TIN sampling and edited TIN results | terrain preview and sampling handoff | no preview-mesh reverse authoring |
| Alignment | Supported | `AlignmentModel` | alignment evaluation and sampling results | Plan and 3D review | no corridor-surface inference |
| Stations | Supported | stationing source policy | sampled station rows | station table and highlight | no result-row editing as source |
| Profile | Supported | `ProfileModel` | profile station/elevation results | Profile review | no visual curve reverse authoring |
| 3D Centerline | Supported | Alignment and Profile | `Centerline3DResult` | source-geometry, B-spline, and polyline display | display modes are not source intent |
| Superelevation | Supported | `SuperelevationModel` | effective crossfall samples | station review and Applied Sections handoff | no Build Parametric re-evaluation of source intent |
| SubAssembly Designer | Supported | saved `SubassemblyDefinition` rows | temporary preview before save | Designer preview | closing without Save must not write source |
| Assembly/Subassembly | Supported | Assembly templates and placed rows | resolved template context | Section Preview | preview is not editable source |
| Region | Supported | `RegionModel` | resolved station context | Region table and boundary highlight | no ownership of Structure, Drainage, or Intersection meaning |
| Applied Sections | Supported | none; generated result | `AppliedSectionSet` | section review and normalized output mapping | supplemental rows remain result-only |
| Build Parametric | Supported | output/display options only | `CorridorModel` and `SurfaceModel` | previews, review rows, output handoff | no mesh repair as design intent |
| Intersections | Supported | `IntersectionModel` | typed topology, boundary, grading, TIN, and diagnostic results | intersection review geometry | presets are sample source creation, not engineering branches |
| Structures | Supported | `StructureModel` | connection, influence, and output results | source preview and Structure Output | preview geometry is not connection intent |
| Drainage | Supported | `DrainageModel` | pipeline and review results | Flow Network, Drainage Review, existing handoff | advanced hydraulics and automatic sizing are out of scope |
| Cross Section | Supported review | none | consumes Applied Sections | read-only viewer and drawing payload | not a geometry editor |
| Plan/Profile | Supported review | none | consumes Alignment, Profile, and optional earthwork results | read-only viewer | does not rewrite source |
| Quantity/Earthwork | Supported review/output | none | quantity, balance, and mass-haul results | normalized reports and navigation | no measurement inference from viewer geometry |
| Exchange | Supported current paths | none | consumes normalized source/result/output contracts | JSON and current IFC/LandXML/DXF paths | complete format coverage remains future work |
| AI Assist | Review/proposal only | none | consumes accepted contracts | explainable suggestions | no silent source rewriting |
| Ramp | Removed | historical compatibility only | none in active scope | none in active workflow | no authoring, evaluation, result, output, review, command, or UI expansion |
| Watertight Solid | Paused compatibility | output configuration only | existing accepted solid results | existing compatibility UI and packages | only critical repair, data-loss prevention, compatibility, and test preservation |

## Output Traceability Rule

Supported normalized outputs must identify the project and their required source/result owners.

- source-derived Plan and Profile outputs require source refs
- Applied Section, Section, Surface, Quantity, Earthwork, and Intersection outputs require result refs
- Drainage, Structure, and Exchange handoffs require both source and result refs
- missing ownership produces a typed diagnostic and returns to the owning stage
- review and presentation code must not repair the output from preview geometry

`OutputTraceabilityService` is the executable validation contract for this rule.

## Document Classification

The following precedence prevents historical plans from being read as current commitments:

1. Current status: this document, `AGENTS.md`, and `V1_PROJECT_ARCHITECTURE_IMPROVEMENT_IMPLEMENTATION_PLAN.md`.
2. Architecture and contract: `V1_MASTER_PLAN.md` subject to its current-scope override, `V1_ARCHITECTURE.md`, `*_MODEL.md`, `*_SCHEMA.md`, `*_CONTRACT.md`, and explicit policy documents.
3. Manual QA: `*_MANUAL_QA.md`, `*_CHECKLIST.md`, and manual review records. These validate behavior but do not expand scope.
4. Completed record: `*_RECORD.md`, release validation records, and completed sections embedded in implementation plans.
5. Historical proposal: every `*_PLAN.md` not explicitly identified as active by this index.

Current active plan:

- `V1_SIDE_SLOPE_REVIEW_UX_PLAN.md`, result-backed ordinary-road and Intersection Side Slope review

Completed architecture record:

- `V1_PROJECT_ARCHITECTURE_IMPROVEMENT_IMPLEMENTATION_PLAN.md`, Phase 5 closure and accepted Build Parametric performance maintenance

Current operational release status:

- `V1_RELEASE_CURRENT_PREP.md`

Special classifications:

- `V1_RAMP_MODEL.md` and Ramp-related plan content are historical compatibility references only.
- `V1_WATERTIGHT_SOLID_*.md` documents preserve existing compatibility behavior but are not active development plans while the pause is in effect.
- `docsV0/` is archived legacy reference only.

## Phase 5 Manual QA

Use `V1_PHASE5_SUPPORTED_DOMAIN_MANUAL_QA.md` for the final FreeCAD 1.1.1 acceptance pass. Automated validation is necessary but does not replace the listed GUI checks.
