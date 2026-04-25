# CorridorRoad V1 Action Label Reset Plan

Date: 2026-04-23
Branch: `v1-dev`
Status: Draft baseline
Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_UX_RESET_PLAN.md`

## 1. Purpose

This document defines how visible actions should be renamed, grouped, or removed so that the v1 UX speaks in user-task language rather than migration language.

It exists to answer:

- which visible labels are misleading today
- which labels should be removed entirely
- which labels should be replaced by stage-based task labels
- which labels should remain internal only

## 2. Core Rule

Visible action names must describe:

- what the user is doing now
- what will happen next
- what design stage the action belongs to

Visible action names must not describe:

- migration state
- implementation generation
- viewer/editor bridge mechanics
- internal versioning

## 3. Banned User-Facing Vocabulary

The following words should not appear in normal end-user button labels, toolbar commands, or primary menu labels:

- `Preview`
- `Bridge`
- `Handoff`
- `Fallback`
- `Legacy`
- `v0`
- `v1`

Exception:

- technical/internal documentation may still use these words
- developer-only debug commands may still use these words if hidden from normal workflow

## 4. Preferred Vocabulary

Preferred verbs:

- `Apply`
- `Review`
- `Generate`
- `Build`
- `Export`
- `Open`
- `Next`

Preferred nouns:

- `Alignment`
- `Stations`
- `Profile`
- `Assemblies`
- `Regions`
- `Structures`
- `Corridor`
- `Cross Sections`
- `Earthwork`
- `Outputs`

## 5. Immediate Label Corrections

### 5.1 Remove bridge wording

These labels should be removed from user-facing UI:

- `Open v1 Preview`
- `Apply + v1 Preview`
- `Generate + v1 Preview`

### 5.2 Replace with task language

Recommended replacements:

- `Open v1 Preview` in alignment editor
  - replace with `Review Alignment`
- `Apply + v1 Preview` in alignment editor
  - replace with `Apply`
  - add separate `Next: Generate Stations`
- `Open v1 Preview` in profile editor
  - replace with `Review Plan/Profile`
- `Apply + v1 Preview` in profile editor
  - replace with `Apply`
  - keep a separate `Review Plan/Profile` action
- `Open v1 Preview` in PVI editor
  - replace with `Review Plan/Profile`
- `Generate + v1 Preview` in PVI editor
  - replace with `Generate FG`
  - keep a separate `Review Plan/Profile`
- `Open v1 Preview` in typical-section editor
  - replace with `Review Section Rules`
- `Apply + v1 Preview` in typical-section editor
  - replace with `Apply`
- `Open v1 Preview` in region editor
  - replace with `Review Section Rules`
- `Apply + v1 Preview` in region editor
  - replace with `Apply`
- `Open v1 Preview` in structure editor
  - replace with `Review Structure Impact`
- `Apply + v1 Preview` in structure editor
  - replace with `Apply`

## 6. Screen-by-Screen Label Matrix

### 6.1 Alignment screen

Primary actions:

- `Apply`
- `Review Alignment`

Secondary actions:

- `Import CSV`
- `Load from Sketch`

Do not show:

- `Open v1 Preview`
- `Apply + v1 Preview`
- `Review Plan/Profile`
- `Next: Generate Stations`

### 6.2 Stations & Profile screen

Primary actions:

- `Generate Stations`
- `Apply`
- `Review Plan/Profile`
- `Next: Assemblies & Regions`

Secondary actions:

- `FG Wizard`
- `Edit Profile`
- `Edit PVI`

Do not show:

- `Open v1 Preview`
- `Apply + v1 Preview`

### 6.3 PVI screen

Primary actions:

- `Apply`
- `Generate FG`
- `Review Plan/Profile`

Secondary actions:

- `Open Profile Editor`

Do not show:

- `Generate + v1 Preview`

### 6.4 Typical Section screen

Primary actions:

- `Apply`
- `Review Section Rules`
- `Next: Regions`

### 6.5 Region screen

Primary actions:

- `Apply`
- `Review Section Rules`
- `Next: Build Corridor`

### 6.6 Structure screen

Primary actions:

- `Apply`
- `Review Structure Impact`
- `Next: Build Corridor`

### 6.7 Review commands

Preferred top-level review commands:

- `Review Alignment`
- `Review Plan/Profile`
- `Review Cross Sections`
- `Review Earthwork`

Do not expose version terms in these command labels.

## 7. Menu and Toolbar Rule

Menu and toolbar order should follow workflow stage:

1. project
2. survey & surface
3. alignment
4. stations & profile
5. assemblies & regions
6. corridor
7. review
8. outputs

Within each stage, show the stage’s primary task actions first.

## 8. Result-State Messaging Rule

State labels may remain technical enough to be useful, but they should still be readable:

- `Current`
- `Needs Rebuild`
- `Blocked`
- `Missing Stations`
- `No Profile Yet`
- `Corridor Not Built`

Avoid:

- `Preview payload`
- `Bridge mode`
- `Fallback state`

in user-facing state summaries.

## 9. Conversion Strategy

Recommended conversion order:

1. rename visible buttons in editors
2. rename top-level commands
3. rename viewer window titles
4. update workflow docs and screenshots
5. remove migration wording from tooltips and help text

## 10. Acceptance Criteria

This label reset is complete when:

- no primary user-facing button uses migration vocabulary
- no main review command exposes version vocabulary
- stage progression can be understood from labels alone
- users can tell what happens next without knowing internal routing

## 11. Final Rule

If a label is only accurate to developers but confusing to users, it should be changed.

The label system should teach the road-design workflow itself, not the implementation history.
