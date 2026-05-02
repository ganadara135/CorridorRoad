# CorridorRoad V1 Wiki 1.0.0 Update Checklist

Date: 2026-05-02
Status: Draft checklist
Target release: `v1.0.0`

Depends on:

- `docsV1/V1_RELEASE_1_0_0_PLAN.md`
- `README.md`
- `ADDON_OVERVIEW.md`

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

- [ ] Identify `1.0.0` as the v1 workflow release.
- [ ] Link Quick Start, Workflow, Troubleshooting, and Developer Guide.
- [ ] Mention Drainage as an in-progress stage.

### Quick Start

- [ ] Use the current toolbar order:
  `Project -> TIN -> Alignment -> Stations/Profile -> Assembly/Structures/Region -> Drainage -> Applied Sections -> Build Corridor -> Review -> Outputs`
- [ ] Add a note that Drainage currently opens an under-development message.
- [ ] Include minimal smoke workflow for Applied Sections, Build Corridor, and Review.

### Workflow

- [ ] Explain source -> evaluation -> result -> output -> presentation.
- [ ] Separate source editors from generated review/output surfaces.
- [ ] Remove legacy v0 corridor loft as the main workflow.

### TIN / Terrain

- [ ] Present TIN-first terrain preparation.
- [ ] Mention terrain as a downstream input for Applied Sections, Corridor Build, and Earthwork.

### Alignment / Stations / Profile

- [ ] Update command names to v1 wording.
- [ ] Include Auto Interpolate Elevations in Profile guidance.
- [ ] Mention station checks and review handoff.

### Assembly / Region

- [ ] Describe Assembly as reusable section source intent.
- [ ] Describe Region as station-range application control.
- [ ] Mention ditch, side slope, bench, Structure refs, and Drainage refs.

### Applied Sections / Build Corridor

- [ ] Describe Applied Sections as generated station-wise results.
- [ ] Describe Build Corridor as consuming Applied Sections.
- [ ] Mention progress bars, diagnostics, and preview surfaces.

### Review

- [ ] Add Cross Section Viewer.
- [ ] Add Plan/Profile Connection Review.
- [ ] Add Earthwork Viewer.
- [ ] Mention handoff between review panels and source editors.

### Earthwork

- [ ] Describe v1-native earthwork analysis from Applied Sections and EG terrain.
- [ ] Mention cut/fill area, quantity, balance, and mass-haul review.
- [ ] State known limitations clearly.

### Structures / Structure Output

- [ ] Describe Structure source editing.
- [ ] Describe Structure Output package and export-readiness diagnostics.
- [ ] Avoid implying every exchange format is complete.

### Drainage

- [ ] Add or update a Drainage page/section.
- [ ] State that the toolbar/menu entry exists.
- [ ] State that the full Drainage Editor is planned after `1.0.0`.
- [ ] Mention current links through Assembly ditch shapes, Applied Section `ditch_surface` rows, and Build Corridor drainage diagnostics.

### Troubleshooting

- [ ] Add "restart FreeCAD or reload the workbench after addon update".
- [ ] Add guidance for missing command registration errors.
- [ ] Add guidance for placeholder stages such as Drainage.
- [ ] Add prerequisite notes for Applied Sections, Build Corridor, and Earthwork Review.

### Developer Guide

- [ ] Link to `docsV1/`.
- [ ] Explain source/result/output package boundaries.
- [ ] Mention preferred FreeCAD Python path for local validation.

## 4. Completion Criteria

- [ ] Wiki Quick Start matches README workflow order.
- [ ] Wiki Home links to the `1.0.0` release.
- [ ] Drainage limitations are visible in user-facing Wiki pages.
- [ ] Troubleshooting covers workbench reload and command registration.
- [ ] No main page presents v0 as the primary workflow.
