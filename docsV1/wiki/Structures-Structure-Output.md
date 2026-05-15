# Structures and Structure Output

Structures are source models for bridge, culvert, retaining-wall, and related corridor structure intent.

## Structure Editor

Use Structures to define source intent such as:

- bridge
- culvert
- retaining wall
- inlet
- outlet or headwall
- custom structure
- station ranges and placement context
- connection points for drainage-ready pipe ports

Generated previews and exchange geometry are outputs.

## Drainage-Ready Structures

Drainage-ready Structures use explicit connection points.

Typical roles:

- `pipe_in`
- `pipe_out`
- `upstream`
- `downstream`
- `inlet`
- `discharge`

Native inlet previews show a catch-basin body, grate, ditch intake mouth, and pipe port stubs.

Native pipe culvert previews use a circular pipe body when the culvert source says `pipe_culvert` or circular. If `headwall_type` or `wingwall_type` is set, endpoint headwall and wingwall details are shown in review geometry.

Native outlet/headwall previews show a headwall slab, outfall apron, side guide walls, pipe-in stub, and discharge mouth.

These details help review the drainage chain. They do not replace the Structure source rows or connection point rows.

## Structure Output

Structure Output builds source-traceable output packages.

It can prepare:

- structure output summaries
- structure quantity fragments where available
- exchange package payloads
- export-readiness diagnostics

## Export Readiness

Check diagnostics before relying on exports.

Errors should block export. Warnings should remain visible in the output package.

## Limit

Not every exchange format is complete in `1.0.0`.
