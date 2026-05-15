# Parametric Road Current Release Preparation

Date: 2026-05-15
Status: prepared for `1.0.1` release
Scope: post-`1.0.0` v1 updates

## Purpose

This document tracks release cleanup for the current v1 work after the initial `1.0.0` release baseline.

Use it to keep documentation, release notes, and validation aligned before tagging the next public release.

## Current User-Facing Scope

Available or actively represented in the current v1 workflow:

- shared `3D Centerline` stage after Plan/Profile review
- Assembly and continuous Region source editing
- Structures source editing with Native/External geometry source modes
- Structure connection points for drainage-ready ports
- Native inlet, pipe culvert, outlet, and headwall 3D review details
- Drainage Elements, Policies, and Flow Routes
- Structure-backed Drainage Flow Network preview
- Drainage Review tables for pipeline candidates, segments, networks, and junctions
- Build Corridor Region Boundary and Surface Transition review
- Watertight Solids target discovery, validation, selected/enabled build actions, display controls, and package export

## Current Future Work

Keep these listed as future or incremental work:

- advanced hydraulic analysis
- automatic pipe sizing
- full drainage reports
- complete drawing-sheet production
- complete LandXML/DXF/IFC coverage
- terrain-inclusive final boolean composition after independent watertight target validation

## Documentation Cleanup Checklist

- [x] README scope updated from Drainage placeholder wording to current Drainage source/editor workflow.
- [x] Addon overview updated for 3D Centerline, Drainage Flow Routes, Structures connection points, and Watertight Solids.
- [x] Wiki Home updated for current toolbar order and current scope.
- [x] Wiki Quick Start updated with Review Plan/Profile, 3D Centerline, Structures after Regions, Drainage, and Watertight Solids.
- [x] Wiki Troubleshooting updated for Drainage Flow Network, Structure preview, and Watertight Solids.
- [x] Wiki Structures page updated for drainage-ready native Structure previews.
- [x] Wiki Review page updated for 3D Centerline and Drainage Review.
- [x] CHANGELOG Unreleased contains recent documentation and Drainage/Structure preview notes.

## Historical Document Notes

The `1.0.0` release planning and validation records still mention Drainage as a placeholder or under-development stage because that was true for the `2026-05-02` release baseline.

Do not rewrite those historical records as current behavior. Current user-facing behavior is tracked in this document, README, Addon overview, Wiki pages, and the `Unreleased` changelog section.

## Release Validation Checklist

Before tagging the next release:

1. Restart FreeCAD.
2. Activate the Parametric Road workbench.
3. Confirm toolbar order:
   `Project -> TIN -> Alignment -> Stations/Profile/3D Centerline -> Assembly/Regions/Structures -> Drainage -> Applied Sections -> Build Corridor -> Review -> Outputs -> AI Assist -> Watertight Solids`
4. Open each primary panel.
5. Run a minimal Alignment -> Stations -> Profile -> 3D Centerline path.
6. Apply Assembly and Regions.
7. Apply Structures `Drainage Structures` preset and preview it.
8. Apply Drainage `Drainage Structures Flow` preset and show Flow Network.
9. Run Applied Sections.
10. Run Build Corridor.
11. Open Watertight Solids and confirm target discovery.
12. Build one Structure or Drainage target where prerequisites are available.
13. Confirm the report view has no unexpected traceback.

## Release Notes Draft

Suggested short release description:

`This v1 update expands Parametric Road beyond the initial workflow reset with a shared 3D Centerline baseline, drainage-ready Structures, Flow Route based Drainage, Structure-backed pipe network previews, and a more capable Watertight Solids final stage. Advanced hydraulic analysis, automatic pipe sizing, and complete exchange coverage remain future work.`

Suggested highlights:

- Shared 3D Centerline review and downstream coordinate ownership.
- Region source simplification: Regions own station spans and Assembly; Structures and Drainage own their own Region/context refs.
- Structures now support connection-ready native drainage objects and clearer 3D review geometry.
- Drainage now has Elements, Policies, Flow Routes, Structure refs, and Flow Network preview.
- Watertight Solids now discovers and builds road, component, drainage, and structure targets with package handoff.

## Tag Readiness

Do not tag the next release until:

- focused tests for Structures, Drainage, 3D Centerline, Build Corridor, and Watertight Solids pass
- manual FreeCAD smoke QA is complete
- [x] `CHANGELOG.md` is converted from `Unreleased` into the intended version/date section
- [x] `package.xml` version/date is updated for the intended tag
- final `git status` contains only intended release changes

Current packaging state:

- `package.xml` declares version `1.0.1` and date `2026-05-15`.
- The intended release tag is `v1.0.1`.
