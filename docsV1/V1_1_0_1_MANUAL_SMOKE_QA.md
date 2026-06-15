# Parametric Road 1.0.1 Manual Smoke QA

Date: 2026-05-19
Target: `v1.0.1`
Status: completed by manual smoke QA

Use this checklist to verify the published `1.0.1` release in FreeCAD.

## 1. Startup

- [x] Install or update the addon to the `v1.0.1` release.
- [x] Restart FreeCAD.
- [x] Confirm the workbench name is `Parametric Road`.
- [x] Confirm no startup traceback appears in the Report View.
- [x] Confirm the toolbar/menu still loads even though the internal Mod folder remains `CorridorRoad`.

## 2. Release Identity

- [x] Confirm `package.xml` reports version `1.0.1`.
- [x] Confirm README / Addon overview describe `Parametric Road`, not `Corridor Road`, as the user-facing name.
- [x] Confirm the GitHub Release link points to `v1.0.1`.
- [x] Confirm the tutorial video link is reachable from README or Addon overview.

## 3. Toolbar Order

Confirm the main workflow order is visible and understandable:

- [x] Project
- [x] TIN
- [x] Alignment
- [x] Stations
- [x] Profile
- [x] Review Plan/Profile
- [x] 3D Centerline
- [x] Assembly
- [x] Region
- [x] Structures
- [x] Drainage
- [x] Applied Sections
- [x] Build Corridor
- [x] Review outputs
- [x] AI Assist
- [x] Watertight Solids

## 4. Minimal Project Workflow

- [x] Create a new Parametric Road project.
- [x] Create or load sample TIN terrain.
- [x] Create or apply sample Alignment.
- [x] Generate Stations.
- [x] Open Profile and apply preset/profile data.
- [x] Open Review Plan/Profile and confirm the review opens without traceback.
- [x] Open 3D Centerline.
- [x] Apply 3D Centerline.
- [x] Confirm the 3D Centerline object appears under the Alignment/Profile tree group.
- [x] Toggle station markers if available.
- [x] Confirm the 3D Centerline display is smooth enough for review.

## 5. Assembly And Regions

- [x] Open Assembly.
- [x] Load or keep a road/ditch-capable Assembly preset.
- [x] Apply Assembly.
- [x] Open Regions.
- [x] Confirm Region rows use `Start STA` with auto-derived end ranges.
- [x] Apply Regions.
- [x] Confirm Regions do not require Structure or Drainage assignment in the Region table.

## 6. Structures

- [x] Open Structures.
- [x] Load the `Drainage Structures` preset.
- [x] Confirm rows include practical drainage structures such as inlet, culvert, and outlet/headwall.
- [x] Confirm Structure ID rows hide the `structure:` prefix.
- [x] Click each Structure row and confirm `Selected Structure Detail` updates.
- [x] Preview Structures.
- [x] Preview connection points.
- [x] Confirm Pipe In / Pipe Out connection points are visible as clear markers.
- [x] Confirm inlet, culvert, and outlet/headwall preview sizes are readable in 3D.
- [x] Apply Structures.
- [x] Close and reopen Structures.
- [x] Confirm applied rows reload into the panel.

## 7. Drainage

- [x] Open Drainage.
- [x] Load the `Drainage Structures Flow` preset.
- [x] Confirm Elements include ditch segments, inlet elements, culvert, and outlet.
- [x] Confirm Element `Policy` cells use combo boxes.
- [x] Confirm Structure Ref cells use Structure ID combo boxes.
- [x] Confirm Flow Route IDs use the expected `flowId-##` visible format.
- [x] Confirm Outlet cells are only enabled for routes whose To Element is an outlet/outfall.
- [x] Validate Drainage.
- [x] Confirm validation completes without unexpected errors.
- [x] Apply Drainage.
- [x] Click `Show Flow Network`.
- [x] Confirm ditch-to-inlet relationships do not create misleading pipe warnings.
- [x] Confirm inlet-to-inlet, inlet-to-culvert, and culvert-to-outlet pipe previews connect through Structure connection points.
- [x] Double-click a Flow Route row and confirm the matching 3D pipe segment is highlighted.

## 8. Applied Sections

- [x] Open Applied Sections.
- [x] Validate.
- [x] Confirm missing Region assignment errors do not appear for valid Drainage rows.
- [x] Apply Applied Sections.
- [x] Double-click a station row.
- [x] Confirm the selected station is visible in 3D.
- [x] Confirm Assembly and Template columns do not show redundant prefixes.

## 9. Build Corridor

- [x] Open Build Corridor.
- [x] Apply or build the corridor.
- [x] Confirm Design Surface is generated or reports a clear diagnostic.
- [x] Confirm Drainage Surface row is present.
- [x] Confirm Drainage Flow row is present.
- [x] Double-click Region Boundary rows.
- [x] Confirm the selected Region displays the built Region objects, not only the centerline.
- [ ] Confirm Surface Transition controls use `Spacing` and `Update`.
- [x] Confirm no traceback appears during Build Corridor review.

## 10. Review Outputs

- [x] Open Cross Section Viewer.
- [x] Confirm it loads Applied Section data.
- [x] Open Drainage Review.
- [x] Confirm source rows, pipeline candidates/segments/networks, and diagnostics are visible where available.
- [x] Open Earthwork Viewer if terrain and corridor prerequisites are available.
- [ ] Confirm no review panel opens with stale `Corridor Road` branding.

## 11. Watertight Solids

- [x] Open Watertight Solids after Build Corridor.
- [x] Confirm target discovery is available.
- [x] Confirm road, Subassembly, drainage, or structure targets appear where prerequisites exist.
- [ ] Select one available Structure or Drainage target.
- [x] Validate selected target.
- [x] Build selected target.
- [x] Show / Hide / Focus the built solid.
- [x] Confirm generated solid follows the 3D Centerline frame rather than the old 2D Alignment-only path.
- [x] Confirm button rows fit the panel width, with `Export Package` and later actions on the second row.

## 12. Documentation And Support Links

- [x] README points to `v1.0.1`.
- [x] Addon overview points to `v1.0.1`.
- [x] Wiki draft Home and Quick Start point to `v1.0.1`.
- [x] Tutorial video link works: https://youtu.be/_xpqwnXPUU8
- [x] Forum thread link works: https://forum.freecad.org/viewtopic.php?t=103783

## 13. Pass Criteria

The smoke QA passes when:

- [x] FreeCAD starts and loads the `Parametric Road` workbench without traceback.
- [x] The minimal workflow reaches Build Corridor.
- [x] Structures and Drainage source rows can be applied.
- [x] Drainage Flow Network preview is usable.
- [x] Watertight Solids opens and can validate/build at least one available target when prerequisites exist.
- [x] Documentation links match `1.0.1`.

## 14. Known Acceptable Limitations

These should not block `1.0.1` smoke QA:

- advanced hydraulic analysis is not complete
- automatic pipe sizing is not complete
- full drainage reports are not complete
- complete drawing-sheet production is not complete
- full terrain-inclusive final boolean composition remains future work
