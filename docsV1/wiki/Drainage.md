# Drainage

Drainage says where the road's water is collected and where it goes, and checks that it drains.
The ditch itself comes from the Assembly; Drainage never changes its shape.

## Where it sits

```text
Assembly (with a ditch) -> Regions -> Drainage -> Applied Sections -> Rebuild Downstream -> Drainage Review
```

You need an Assembly with a `ditch` Subassembly and Regions that use it. Applied Sections tag the
ditch points with the Ditch Run that drains them, and the Drainage checks read those points.

## A quick run

1. Open **Drainage**. With no runs yet, the Ditch Runs tab is filled from the Regions and the
   Assembly: one run per ditch and side. Press **Apply**.
2. Run **Rebuild Downstream**. It retags the ditch points and evaluates the Drainage.
3. Open **Drainage** again, **Points** tab: the checks suggest outfalls at the low ends of the
   ditches and inlets at other low points and along long stretches. **Add All**, then **Apply**.
4. **Links** tab: **Link Downhill** links every inlet to the nearest lower point. **Apply**.
5. Open **Drainage Review** to see each ditch's flowline profile and the remaining checks.

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

## Checks

| Check | What to do |
|---|---|
| Flowline missing | Rebuild Applied Sections, or check the run's ditch and stations |
| Flat grade | steepen the Profile or the ditch, or accept a lower minimum |
| Low point without an inlet or outfall | add the suggested point |
| Inlet spacing | add the suggested inlets |
| Point outside its run / no water reaches it | move the point onto the run, to a low point |
| Link uphill, flat, loop, drains nowhere or twice | fix the link in the Links tab |

## Drainage Review

Read-only. Pick a run to see its flowline profile: the blue line, flagged stretches in orange or
red, low points as blue dots, and inlets, outfalls and culverts as squares. Double-click a check to
highlight it on the flowline in the 3D view. The review says whether the result is current; when
it is stale, run Rebuild Downstream.

## When results go stale

Editing the Profile, Regions, Assembly or Ditch Runs makes Applied Sections and the Drainage
stale; Rebuild Downstream rebuilds both. A Policy, point or link edit leaves Applied Sections
current, so the Drainage panel's Apply checks it again at once.

## Not included

Hydraulic sizing, catchment runoff and pipe bodies are not part of Drainage. Pipes and their
Structure connections come with the Structure rebuild.
