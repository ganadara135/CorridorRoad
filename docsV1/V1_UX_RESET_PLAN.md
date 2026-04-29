# CorridorRoad V1 UX Reset Plan

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline

## 1. Purpose

This document resets the v1 UX direction from a user-first point of view.

It explicitly does **not** start from:

- preserving the existing v0 task-panel structure
- preserving bridge workflows as part of the final product
- exposing architecture migration steps directly to users

It starts from one question instead:

- what is the simplest and least confusing workflow for a user designing a road corridor in CorridorRoad v1

## 2. Core Product Rule

The final v1 product UX should be designed as if the old v0 UI did not exist.

Practical meaning:

- user-facing workflows should be defined from task intent, not from old panel names
- old v0 editors and bridge buttons must not define the final information architecture
- transitional bridge logic may exist temporarily in code, but it is not a product feature

## 3. Why the Current Bridge UX Is Not the End-State

The current bridge approach helped validate:

- v1 viewers
- context handoff
- same-context return
- main review command routing

That was useful during implementation, but it creates user confusion when exposed as normal UX.

Examples of confusion:

- `Apply + v1 Preview` does not tell the user which review surface will open
- `Alignment` can unexpectedly jump into `Plan/Profile Viewer`
- users see stage boundaries blur before stationing, profiles, and corridor results exist
- `Open v1 Preview` describes an internal migration concept rather than a user task

Conclusion:

- bridge behavior may stay in code for development and fallback
- bridge behavior should not shape the final user-facing workflow

## 4. Product UX Principles

### 4.1 Workflow is stage-based

The primary UX should follow the natural design sequence:

1. project setup
2. survey and terrain
3. alignment
4. stationing and profile
5. assembly and regions
6. corridor build
7. review
8. outputs and exchange

### 4.2 Review happens at the right stage

Each review surface should appear only when it matches the current design stage.

Examples:

- `Alignment` stage should review alignment, not pretend full plan/profile is ready
- `Plan/Profile Viewer` should become primary only after stationing/profile context exists
- `Cross Section Viewer` should become primary only after section/corridor context exists
- `Earthwork Viewer` should become primary only after cut/fill or earthwork results exist

### 4.3 Buttons should describe user actions

Avoid labels that expose implementation or migration vocabulary.

Bad examples:

- `Open v1 Preview`
- `Apply + v1 Preview`
- `Fallback`

Preferred examples:

- `Apply`
- `Review Alignment`
- `Generate Stations`
- `Review Plan/Profile`
- `Review Cross Sections`
- `Review Earthwork`
- `Next: Profiles`

### 4.4 The UI should answer “what next?”

Each stage should present:

- what the user is editing now
- what can be reviewed now
- what the next valid step is

### 4.5 Missing prerequisites must be explicit

If a review surface depends on data that does not exist yet, the UI should say so directly.

Examples:

- `Stations not generated yet`
- `No profile controls yet`
- `Corridor build required before cross-section review`
- `Earthwork results not available yet`

The UI should never silently route the user into a different stage and hope they infer why.

## 5. Bridge Policy

### 5.1 Final product rule

Bridge UX is not part of the final v1 product.

### 5.2 Temporary implementation rule

Bridge logic may remain temporarily for:

- developer verification
- same-context debugging
- fallback during migration
- side-by-side validation against old behavior

### 5.3 User-facing rule

If bridge logic remains in code, it should be:

- hidden from normal user workflows where practical
- described as temporary in internal docs only
- removed from primary button labels and menu flow

### 5.4 Removal target

The long-term direction is:

- no visible `Open v1 Preview`
- no visible `Apply + v1 Preview`
- no user workflow that depends on “viewer -> old panel -> viewer” as the main happy path

## 6. New V1 UX Shape

### 6.1 Project

Purpose:

- create or load a project
- set units and coordinate system
- establish project defaults

Primary actions:

- `New/Project Setup`
- `Open Project`
- `Project Settings` through the same setup entry point

### 6.2 Survey & Surface

Purpose:

- import or build terrain from TIN
- inspect terrain sources and extents

Primary actions:

- `Import TIN`
- `Import Survey`
- `Review Terrain`
- `Next: Alignment`

### 6.3 Alignment

Purpose:

- author and refine horizontal alignment only

Primary actions:

- `Apply`
- `Review Alignment`
- `Next: Generate Stations`

Important rule:

- this stage must not automatically jump into full plan/profile review
- if stations are missing, the UX should direct the user to create them

### 6.4 Stations & Profile

Purpose:

- generate stations
- sample existing ground
- create and adjust finished grade

Primary actions:

- `Generate Stations`
- `Profile`
- `Review Plan/Profile`
- `Next: Assembly & Regions`

### 6.5 Assembly & Regions

Purpose:

- define typical section logic
- define region policies
- define structure interaction rules

Primary actions:

- `Edit Assemblies`
- `Edit Regions`
- `Edit Structures`
- `Review Section Rules`
- `Next: Build Corridor`

### 6.6 Corridor

Purpose:

- evaluate applied sections
- build corridor surfaces and solids
- produce diagnostics

Primary actions:

- `Build Corridor`
- `Rebuild Corridor`
- `Review Build Status`
- `Next: Review`

Important rule:

- corridor-stage surface and terrain derivatives may exist as internal or advanced tools during implementation
- they must not become separate first-class toolbar or menu steps before the final v1 surface workflow is intentionally designed
- the main user workflow should read as one corridor build step, not as a chain of low-level intermediate generators

### 6.7 Review

Purpose:

- inspect derived results after build

Primary review surfaces:

- `Cross Section Viewer`
- `Plan/Profile Viewer`
- `Earthwork Viewer`
- `3D Review`

Important rule:

- this stage is the center of v1 result verification
- it must not depend on old v0 viewers as the main path

### 6.7A Hidden Utilities

Purpose:

- retain implementation-support or specialist tools that are not part of the primary user workflow

Examples:

- `3D Centerline Utility`
- `Advanced Cross Section Editor`

Important rule:

- these tools may remain useful during transition
- but they should not redefine the main user task order
- users should be able to complete the core design workflow without opening them first
- they should not be exposed as primary toolbar or menu entries in the normal v1 workbench layout

### 6.8 Outputs & Exchange

Purpose:

- produce sheets, reports, and exchange files

Primary actions:

- `Review Outputs`
- `Export DXF`
- `Export LandXML`
- `Export IFC`

Current implementation rule:

- this stage should appear explicitly in the primary workbench flow
- if the full output-review hub is not implemented yet, a stage-entry command is still preferable to hiding the stage entirely

### 6.9 AI Assist

Purpose:

- generate recommendations and alternative candidates
- compare alternatives with explanation and approval

Primary actions:

- `AI Assist`
- `Compare Alternatives`
- `Review AI Explanation`
- `Accept Candidate`

Current implementation rule:

- this stage should appear explicitly in the primary workbench flow
- if the full AI assist UI is not implemented yet, a stage-entry command is still preferable to hiding the stage entirely

## 7. Viewer Rules

### 7.1 Alignment review

`Review Alignment` should be an alignment-stage review surface, not a disguised plan/profile jump.

Minimum expectations:

- alignment summary
- geometry element count
- constraint or diagnostic summary
- next-step guidance toward stationing

### 7.2 Plan/Profile Viewer

`Plan/Profile Viewer` should be treated as a stationing/profile-stage viewer.

It should not be the default result of saving alignment alone unless stationing/profile context exists.

### 7.3 Cross Section Viewer

`Cross Section Viewer` should be treated as a corridor/section-stage viewer.

It should clearly indicate:

- whether the section comes from real document data or a placeholder/demo path
- whether corridor or section prerequisites are missing
- what source objects own the result

### 7.4 Earthwork Viewer

`Earthwork Viewer` should be treated as an analytical result viewer.

It should open only when earthwork results exist, or clearly state that they do not.

## 8. Naming Rules

User-visible labels should follow these rules:

- use task language, not migration language
- use nouns for stages and verbs for actions
- avoid `preview`, `bridge`, `handoff`, `legacy`, `fallback` in normal user labels

Preferred action naming examples:

- `Review Alignment`
- `Review Plan/Profile`
- `Review Cross Sections`
- `Review Earthwork`
- `Generate Stations`
- `Build Corridor`
- `Export LandXML`

## 9. Transitional Code Policy

During implementation, the codebase may still contain:

- bridge helpers
- same-context return helpers
- old v0 editor launch paths
- fallback routing

That is acceptable temporarily.

But the UX policy must remain:

- new user-facing buttons should not be added in bridge vocabulary
- menus and toolbars should move toward stage-based task language
- old editor access should be treated as implementation support, not as the product center

## 10. Immediate UX Corrections

These items should be treated as near-term cleanup targets.

### 10.1 Remove bridge wording from visible buttons

Examples:

- replace `Open v1 Preview`
- replace `Apply + v1 Preview`

### 10.2 Stop stage-jumping without explanation

Examples:

- `Alignment` save should not unexpectedly feel like a `Plan/Profile` action
- viewers should not imply later-stage readiness when prerequisites are missing

### 10.3 Add explicit next-step guidance

Examples:

- after alignment apply: `Next: Generate Stations`
- after station generation: `Next: Profile`
- after corridor build: `Next: Review Cross Sections`

### 10.4 Make prerequisite states visible

Examples:

- `Stations not generated yet`
- `No finished-grade profile yet`
- `Corridor not built yet`
- `Earthwork not calculated yet`

## 11. Recommended Transition Path

1. define the stage-based v1 UX model
2. rename visible actions away from bridge vocabulary
3. separate `Review Alignment` from `Review Plan/Profile`
4. make prerequisite messaging explicit
5. move old v0 editor access behind secondary paths
6. keep bridge code only as hidden migration support
7. remove bridge UX entirely once v1-native screens cover the workflow

## 12. Non-Goals

Avoid the following:

- preserving confusing bridge buttons just because they already work
- exposing old v0 migration structure as a product concept
- forcing users to understand internal viewer/editor routing
- letting architecture validation shortcuts define the final UX

## 13. Final Rule

If a UI choice helps migration code but makes the user workflow harder to understand, it is the wrong product choice.

V1 should be designed as a clean road-design workflow product first.

Migration helpers may exist temporarily, but they must never become the primary UX model.
