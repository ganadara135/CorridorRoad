# Drainage

Drainage is a planned v1 stage.

In `1.0.0`, Drainage has a toolbar/menu entry and opens a clear under-development message. The full Drainage Editor is planned after the release.

## Why Drainage Is In The Toolbar

Drainage belongs after Region and before Applied Sections.

Reason:

- Region defines station range context.
- Drainage will define drainage elements and intent for those ranges.
- Applied Sections will evaluate the resolved drainage/ditch context.

## Current Behavior

Current drainage-related behavior appears through:

- Assembly ditch shapes
- Applied Section `ditch_surface` rows
- Build Corridor drainage diagnostics
- drainage surface preview where ditch points exist

## Planned Drainage Editor

Planned elements:

- ditch
- swale
- channel
- culvert reference
- inlet reference
- outfall reference
- low-point and minimum-grade policy
- discharge and collection context

## Not Included In 1.0.0

- full Drainage Editor
- hydraulic analysis
- automatic pipe sizing
- complete drainage report output

See `docsV1/V1_DRAINAGE_IMPLEMENTATION_PLAN.md` for the implementation plan.
