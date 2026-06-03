# Parametric Road V1 Wiki Drafts

Target release: `v1.0.3`

These files are draft source pages for the GitHub Wiki.

Current release links:

- GitHub Release: https://github.com/ganadara135/CorridorRoad/releases/tag/v1.0.3
- Tutorial video: https://youtu.be/_xpqwnXPUU8
- FreeCAD Forum: https://forum.freecad.org/viewtopic.php?t=103783

Recommended publish order:

1. [Home](./Home.md)
2. [Quick Start](./Quick-Start.md)
3. [Workflow](./Workflow.md)
4. [TIN Terrain](./TIN-Terrain.md)
5. [Alignment Stations Profile](./Alignment-Stations-Profile.md)
6. [Superelevation](./Superelevation.md)
7. [Assembly Region](./Assembly-Region.md)
8. [Intersections](./Intersections.md)
9. [Applied Sections Build Corridor](./Applied-Sections-Build-Corridor.md)
10. [Review](./Review.md)
11. [Earthwork](./Earthwork.md)
12. [Structures Structure Output](./Structures-Structure-Output.md)
13. [Drainage](./Drainage.md)
14. [Troubleshooting](./Troubleshooting.md)
15. [Developer Guide](./Developer-Guide.md)

Release rule:

- v1 is the primary workflow.
- Superelevation is the source stage after 3D Centerline and before Assembly.
- Intersections can create starter multi-alignment sources and a matching 3D Centerline preview.
- Drainage is an active source stage with Elements, Policies, Flow Routes, Structure refs, Flow Network preview, and Drainage Review.
- Advanced hydraulic analysis and automatic pipe sizing remain future work.
- Watertight Solids is the final output stage after AI Assist and is gated on Build Corridor prerequisites.
- Generated geometry, preview meshes, markers, and reports are outputs, not source truth.
