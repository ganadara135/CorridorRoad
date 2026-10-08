"""Kernel constants (decision D4 of `V1_INTERSECTION_PARAMETRIC_REDESIGN_PLAN.md`, section 5.3).

There is no Project design standard table yet; these are the values the current presets use.
Lengths in metres, angles in degrees.
"""

# corner radius when neither the spec nor a corner override gives one
T_CORNER_RADIUS_M = 12.0
CROSS_CORNER_RADIUS_M = 10.0
ROUNDABOUT_INSCRIBED_RADIUS_M = 18.0

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

# manual anchor stations whose road points are further apart than this do not meet
ANCHOR_MEET_TOLERANCE_M = 0.05
