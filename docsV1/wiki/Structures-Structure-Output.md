# Structures and Structure Output

Structures are source models for bridge, retaining-wall, and related corridor structure intent.

## Structure Editor

Use Structures to define source intent such as:

- bridge
- retaining wall
- wall
- utility
- custom structure
- station ranges and placement context

Generated previews and exchange geometry are outputs.

## Culverts and Pipes Are In Drainage

Culverts, inlets, outlets, headwalls, manholes and junction boxes are not Structures. Model them in Drainage: a culvert is a Drainage point, and the pipe is a link with a diameter. A document saved before keeps such Structure rows until the Structure is applied; the editor leaves them out with a note, and applying drops them.

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
