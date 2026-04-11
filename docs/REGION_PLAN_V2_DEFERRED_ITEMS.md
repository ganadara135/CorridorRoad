<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Region Plan V2 Deferred Items

Date: 2026-04-10

## Purpose

This document holds follow-up work that is intentionally outside the completed `RegionPlan V2` migration.

Use this as a backlog for:

1. polish work
2. optional workflow upgrades
3. future cleanup after a compatibility window

`RegionPlan V2` itself is considered complete.
Items here are not blockers for the main workflow.

## Priority

### P1. Workflow polish

Status on 2026-04-10:

1. completed

Delivered:

1. `Station Timeline` readability was improved with grouped timeline rows, clearer row type/state columns, and lighter workflow wording
2. workflow buttons now enable or disable more aggressively based on the current base / override / hint / timeline selection
3. grouped editor affordances are stronger through per-group counts, clearer selection-driven controls, and visual distinction between confirmed data and hints

### P2. Timeline interaction

Status on 2026-04-10:

1. completed for selection sync and direct span editing
2. remaining optional upgrade: drag-editing on the visual timeline

Delivered:

1. grouped tables and timeline selection stay synchronized
2. direct split / move / resize operations are available from the timeline selection card

Still optional:

1. true drag-editing for base spans on a graphical timeline surface
2. richer station-graphic affordances beyond the current table + span editor workflow

### P3. Import / export

Status on 2026-04-10:

1. completed for CSV import/export

Delivered:

1. CSV import for base / override / hint rows
2. CSV export for diagnostics or template reuse
3. round-trip preservation for managed hint metadata in the current `COL_HEADERS` schema

Still optional:

1. alternate formats besides CSV
2. stricter product rules for managed-hint round-trip constraints

### P4. Better automatic hints

Status on 2026-04-10:

1. completed

Delivered:

1. hint confidence is now visible in the grouped workflow and stored with `RegionPlan` rows
2. hint family is now surfaced through `RuleSet`-driven source/family labels in the workflow
3. `Seed From Project` now expands beyond the original ditch/urban cases with additional shoulder-edge, practical-mode, retaining-wall, and bridge/abutment hint rules
4. standards-driven hint generation is now included through `DesignStandard` and alignment design-speed review hints

Still optional:

1. broader automation beyond current project / typical / structure context still needs product decisions

### P5. Legacy retirement

Status on 2026-04-10:

1. completed

Delivered:

1. `Project` and `SectionSet` authoring/runtime paths now use `RegionPlan` only
2. hidden legacy region fallback and usage sync paths were removed from the active workflow
3. the compatibility wrapper file and legacy migration-specific smokes were removed

## Recommended Next Order

If follow-up work starts now, use this order:

1. no required backlog items remain

## Exit Criteria

This backlog can be considered healthy if:

1. the main workflow remains `Workflow`-first
2. `Advanced` remains a diagnostics / compatibility surface, not the default editing path
3. any new automation still preserves the rule that hints do not silently become design data
