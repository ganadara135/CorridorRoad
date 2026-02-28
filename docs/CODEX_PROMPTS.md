# Codex Prompt Templates (CorridorRoad)

## Session Boot Prompt
Read README_Codex.md first. Follow the architecture rules strictly.
Work in small patches. Provide patch-like diffs.

## Task: Update references after removing VA FG properties
Search the workspace for references to:
ShowFGWire, FGCurvesOnly, FGWireZOffset
Replace logic to use FGDisplay (Finished Grade (FG)):
- Show FG → FGDisplay.ShowWire
- Curves only → FGDisplay.CurvesOnly
- Z offset → FGDisplay.ZOffset
Ensure no UI references remain to removed VA props.

## Task: Ensure FGDisplay auto-creation
When opening Edit Profiles or saving PVI:
- if FGDisplay missing, create it
- set Label = "Finished Grade (FG)"
- link SourceVA to current VerticalAlignment

## Task: Validation
1) Summarize changed files and reasoning.
