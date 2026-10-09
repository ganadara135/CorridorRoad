"""Kernel constants (decision D4 of `V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md`, section 5.3).

There is no Project design standard table yet; these are the values the current presets use.
Lengths in metres, angles in degrees.
"""

# corner radius when neither the spec nor a corner override gives one
T_CORNER_RADIUS_M = 12.0
CROSS_CORNER_RADIUS_M = 10.0
ROUNDABOUT_INSCRIBED_RADIUS_M = 18.0
# the starter preset derives the central island as 0.45 of the outer radius, so the circulatory
# roadway is the other 0.55, and its outer apron as 0.15 of the circulatory width
ROUNDABOUT_CIRCULATORY_WIDTH_RATIO = 0.55
ROUNDABOUT_APRON_WIDTH_RATIO = 0.15
# entry and exit flare radii, as a fraction of the ring's outer edge radius: the current preset has
# none (a square corner, which leaves no room for a side slope where the approach edge meets the
# ring), and a fixed radius cannot suit every ring: a flare of radius R meets a ring of outer radius
# r at asin((w + R) / (r + R)) off the approach, so on the starter's 13 m ring 15 m flares would
# overlap their neighbours. Half the ring for the entry and a little more for the exit leave ring
# between the flares of two approaches at right angles to each other (36 + 38 of the 90 degrees
# there); the exit is the larger, as usual
ROUNDABOUT_ENTRY_RADIUS_RATIO = 0.5
ROUNDABOUT_EXIT_RADIUS_RATIO = 0.6
# the circulatory roadway falls outward from the central island at this crossfall (2 %)
ROUNDABOUT_RING_CROSSFALL = 0.02

DEFAULT_GRADING_MODE = "flatten_intersection"

# the leg mouth is the outermost curb return tangent point; no extra length beyond it
MOUTH_CLEARANCE_M = 0.0

# a road must extend this far past the anchor to make a leg: guards against station noise at a
# road that starts or ends at the anchor (a T's side road), far below any real leg length
LEG_MIN_LENGTH_M = 0.5

# arc sampling: the chord error R (1 - cos(step / 2)) is 0.1 % of R, 12 mm at R = 12 m
ARC_MAX_STEP_DEG = 5.0

# edge sampling between alignment vertices and Applied Section stations, so a pavement width
# that changes along the leg is followed; on a straight leg of constant width it changes nothing
EDGE_SAMPLE_STEP_M = 1.0

# a fillet is searched along each leg at most this far from the anchor
FILLET_SEARCH_LENGTH_M = 200.0

# patch vertices within this height of the lowest one are the same low point (1 mm, below any
# design tolerance for a sag, above the rounding of the Applied Section heights)
LOW_POINT_TOLERANCE_M = 0.001

# manual anchor stations whose road points are further apart than this do not meet
ANCHOR_MEET_TOLERANCE_M = 0.05
