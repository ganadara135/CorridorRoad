# CorridorRoad V1 Wiki 1.0.0 Update Checklist

Date: 2026-05-02
Status: Local wiki drafts created under `docsV1/wiki/`
Target release: `v1.0.0`

Depends on:

- `docsV1/V1_RELEASE_1_0_0_PLAN.md`
- `README.md`
- `ADDON_OVERVIEW.md`
- `docsV1/wiki/WIKI_TOC.md`

## 1. Purpose

This checklist tracks the Wiki updates required for the CorridorRoad `1.0.0` release.

The Wiki should present v1 as the primary workflow and should not describe legacy v0 corridor loft behavior as the main product path.

## 2. Global Wiki Rules

- Use `1.0.0` and `v1 workflow` wording consistently.
- Keep Drainage visible as a planned stage, but state that the full Drainage Editor is still under development.
- Describe generated Applied Sections, corridor surfaces, review markers, and output packages as results or outputs.
- Do not describe generated meshes as source truth.
- Include restart/reload guidance after updating the addon.

## 3. Pages To Update

### Home

- [x] Identify `1.0.0` as the v1 workflow release.
- [x] Link Quick Start, Workflow, Troubleshooting, and Developer Guide.
- [x] Mention Drainage as an in-progress stage.

### Quick Start

- [x] Use the current toolbar order:
  `Project -> TIN -> Alignment -> Stations/Profile -> Assembly/Structures/Region -> Drainage -> Applied Sections -> Build Corridor -> Review -> Outputs`
- [x] Add a note that Drainage currently opens an under-development message.
- [x] Include minimal smoke workflow for Applied Sections, Build Corridor, and Review.

### Workflow

- [x] Explain source -> evaluation -> result -> output -> presentation.
- [x] Separate source editors from generated review/output surfaces.
- [x] Remove legacy v0 corridor loft as the main workflow.

### TIN / Terrain

- [x] Present TIN-first terrain preparation.
- [x] Mention terrain as a downstream input for Applied Sections, Corridor Build, and Earthwork.

### Alignment / Stations / Profile

- [x] Update command names to v1 wording.
- [x] Include Auto Interpolate Elevations in Profile guidance.
- [x] Mention station checks and review handoff.

### Assembly / Region

- [x] Describe Assembly as reusable section source intent.
- [x] Describe Region as station-range application control.
- [x] Mention ditch, side slope, bench, Structure refs, and Drainage refs.

### Applied Sections / Build Corridor

- [x] Describe Applied Sections as generated station-wise results.
- [x] Describe Build Corridor as consuming Applied Sections.
- [x] Mention diagnostics and preview surfaces.

### Review

- [x] Add Cross Section Viewer.
- [x] Add Plan/Profile Connection Review.
- [x] Add Earthwork Viewer.
- [x] Mention handoff between review panels and source editors.

### Earthwork

- [x] Describe v1-native earthwork analysis from Applied Sections and EG terrain.
- [x] Mention cut/fill area, quantity, balance, and mass-haul review.
- [x] State known limitations clearly.

### Structures / Structure Output

- [x] Describe Structure source editing.
- [x] Describe Structure Output package and export-readiness diagnostics.
- [x] Avoid implying every exchange format is complete.

### Drainage

- [x] Add or update a Drainage page/section.
- [x] State that the toolbar/menu entry exists.
- [x] State that the full Drainage Editor is planned after `1.0.0`.
- [x] Mention current links through Assembly ditch shapes, Applied Section `ditch_surface` rows, and Build Corridor drainage diagnostics.

### Troubleshooting

- [x] Add "restart FreeCAD or reload the workbench after addon update".
- [x] Add guidance for missing command registration errors.
- [x] Add guidance for placeholder stages such as Drainage.
- [x] Add prerequisite notes for Applied Sections, Build Corridor, and Earthwork Review.

### Developer Guide

- [x] Link to `docsV1/`.
- [x] Explain source/result/output package boundaries.
- [x] Mention preferred FreeCAD Python path for local validation.

## 4. Completion Criteria

- [x] Local Wiki Quick Start matches README workflow order.
- [x] Local Wiki Home links to the `1.0.0` release.
- [x] Drainage limitations are visible in user-facing Wiki pages.
- [x] Troubleshooting covers workbench reload and command registration.
- [x] No main page presents v0 as the primary workflow.

Publishing to the GitHub Wiki remains a release task outside this local document set.
