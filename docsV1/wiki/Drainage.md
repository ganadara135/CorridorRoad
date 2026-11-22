# Drainage

Drainage says where the road's water is collected and where it goes, and checks that it drains.
The ditch itself comes from the Assembly; Drainage never changes its shape.

## Where it sits

```text
Assembly (with a ditch) -> Regions -> Drainage (Ditch Runs) -> Applied Sections -> Rebuild Downstream -> Drainage (points, links, pipes, review)
```

You need an Assembly with a `ditch` Subassembly and Regions that use it. Applied Sections tag the
ditch points with the Ditch Run that drains them, and the Drainage checks read those points.

## A quick run

1. Open **Drainage**. With no runs yet, the Ditch Runs tab is filled from the Regions and the
   Assembly: one run per ditch and side. Press **Apply**.
2. Build **Applied Sections** if they are not built yet.
3. In the Drainage panel press **Rebuild Downstream** and, in its window, **Rebuild**. It retags
   the ditch points and evaluates the Drainage. The panel reads the result when it finishes: the
   drawing above the tabs now shows each run's flowline.
4. **Flow** tab: **Trace Network** proposes the missing outfalls, inlets and links for the whole
   network; **Accept** puts them in the tables. Or work by hand: the **Points** tab adds the
   suggested points, and **Link Downhill** in the **Links** tab links every inlet to the nearest
   lower point.
5. Give a link a **Pipe (m)** diameter where the water goes through a pipe.
6. **Apply**. The panel stores the tables, checks them again and draws the Drainage in the 3D view.
7. **Review** tab: the remaining checks and the pipes.

When the panel cannot go on it says what is missing first: apply the Ditch Runs, build Applied
Sections, or press Rebuild Downstream.

## The drawing above the tabs

The panel always shows one Ditch Run's flowline above its tabs. It follows the tables as they
stand, edits not yet applied included, so you can edit Points and Links with the drawing in view.

- blue line: the flowline; blue dots: low points; grey dots: high points
- squares: inlets (green), outfalls (blue), culverts (purple)
- brown band: a link with a pipe, with its diameter; green band: an open-flow link; the arrow
  points to where it drains
- thick orange or red: a stretch a check flags
- orange: the point or link selected in a table

Selecting a row in the Ditch Runs, Points or Links table switches the drawing to its run.

## Policy

| Field | Meaning |
|---|---|
| Minimum flowline grade (%) | a ditch stretch or link flatter than this is a warning |
| Maximum inlet spacing (m) | no stretch of ditch may run longer than this without an inlet |
| Low point | "Needs an inlet or outfall" warns at an uncollected low point; "May pond" allows it |

## Ditch Runs

A Ditch Run is one Assembly ditch on one side of the road over a station span. **Fill from
Assembly** replaces the runs with the prefill; **Add Run** and **Delete Run** edit them; **On**
switches a run off without deleting it. A ditch point no run covers is reported in Build
Parametric.

## Points

- **Inlet:** collects a run's water.
- **Outfall:** where a run's water leaves the road.
- **Culvert:** crosses the road; it names no run and collects from every run it meets.

The suggestion list shows what the current checks propose. **Add Selected** / **Add All** put
suggestions in the table (once each); **Apply** stores them and checks again at once.

## Links

A Link says which point drains into which. Links are measured between the points' places on the
flowlines: a link must fall, must not loop, and every inlet must drain somewhere, to one place.
**Link Downhill** adds a link for every inlet that drains nowhere.

**Pipe (m)** is the diameter of a circular pipe that carries the link's water; leave it blank for
open flow. The pipe is straight, between its two points on the flowlines; its length, end inverts,
grade and barrel volume are measured, never typed in. A culvert's barrel is the pipe of the link
leaving it.

## Flow

The Flow tab shows the network as a tree: each point sits under the point it drains into, with the
falling grade of its link, the pipe it carries and the checks of the last evaluation.

- **Add Upstream** places an inlet one step up the ditch from the selected point, draining into it.
- **Add Downstream** links a point that drains nowhere to the next lower point, or adds an outfall.
- **Trace Network** proposes the whole missing network; **Accept** keeps it, **Discard** drops it.
- Selecting a point lists its checks with the fix each offers: Add Downstream, Add Suggested,
  Reconnect To a lower point, Delete Link, Delete Extra Links, Delete Point.

Everything here changes the tables only; **Apply** keeps it.

## Checks

| Check | What to do |
|---|---|
| Flowline missing | Rebuild Applied Sections, or check the run's ditch and stations |
| Flat grade | steepen the Profile or the ditch, or accept a lower minimum |
| Low point without an inlet or outfall | add the suggested point |
| Inlet spacing | add the suggested inlets |
| Point outside its run / no water reaches it | move the point onto the run, to a low point |
| Link uphill, flat, loop, drains nowhere or twice | fix the link in the Links tab |

## Review tab

Read-only. It lists the checks of the drawn Ditch Run and the pipes on the links (diameter, length,
inverts, grade, volume), and says whether the result is current; when it is stale, press Rebuild
Downstream. Double-click a check to highlight it on the flowline in the 3D view; double-click a
pipe, or press **Show All Pipes**, to draw pipes as tubes.

In a document with an Intersection, the tab also lists the **intersection low points**: where water
standing on the intersection surface collects, one row per nearest road. Double-click a row to mark
those places in the 3D view. The list is for review: it adds no check or suggestion, so decide
yourself whether a point is needed there.

The **Drainage Review** command (Drainage menu) and the Drainage Review button of Build Parametric
open this same panel on the Review tab.

## The Drainage in the 3D view

**Apply** draws the stored Drainage in the 3D view, and **Show in 3D** draws it again at any time:
inlets (green), outfalls (blue) and culverts (purple) as markers at their places on the flowlines,
a piped link as a tube of its diameter, an open-flow link as a line. The objects sit in the
project tree's Drainage folder, one per kind, so each kind can be hidden. Once shown, they follow
every later evaluation.

The markers show where a point is; they are not the dimensions of a real inlet or headwall. Only
the pipes have their real diameter and length. Edits not yet applied are in the drawing above the
tabs, not in the 3D view.

## When results go stale

Editing the Profile, Regions, Assembly or Ditch Runs makes Applied Sections and the Drainage
stale; Rebuild Downstream rebuilds both. A Policy, point or link edit leaves Applied Sections
current, so the Drainage panel's Apply checks it again at once.

## Not included

Hydraulic sizing, catchment runoff and automatic pipe sizing are not part of Drainage. Pipes are
straight and circular; bends, manholes and detailed inlet or headwall bodies are not modelled.
Culverts and pipes are not Structures: a Structure of a culvert or drainage kind from an earlier
version is left out of the Structure editor and dropped when the Structure is next applied.
