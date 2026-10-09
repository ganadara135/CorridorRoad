"""Item 5.4, second part: a roundabout approach can flare its connector mouth.

An approach takes an entry radius and an exit radius from edge policy rows of the roundabout
intent, with the rules `roundabout_approach_entry_radius` and `roundabout_approach_exit_radius`,
keyed by `leg_ref` and `side` like the per-approach apron. The flare is the arc tangent to the
connector's edge line and to the circulatory outer circle. For right-hand traffic circulating
counter-clockwise the entry side is the side `p` points to, `p` being the outward direction
turned a quarter turn counter-clockwise. Without a radius the connector is the rectangle it was.
"""

import math


from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import (
    create_intersection_preset_sources,
)
from freecad.Corridor_Road.v1.objects.obj_intersection import (
    find_v1_intersection_model,
    to_intersection_model,
)

ROUNDABOUT = "Roundabout - Single Lane"


def _model(doc):
    create_intersection_preset_sources(doc, preset_label=ROUNDABOUT)
    return to_intersection_model(find_v1_intersection_model(doc))


def _connector_loop(loops, approach_leg):
    suffix = approach_leg.approach_role.replace("_", "-")
    return next(
        row
        for row in loops.loop_rows
        if row.loop_role == "roundabout_entry_exit_connector_boundary"
        and approach_leg.approach_leg_id in row.source_refs
    ), suffix


def _local(point, center, angle_deg):
    angle = math.radians(angle_deg)
    ux, uy = math.cos(angle), math.sin(angle)
    dx, dy = point[0] - center[0], point[1] - center[1]
    return (dx * ux + dy * uy, -dx * uy + dy * ux)  # x along the approach, y along p
