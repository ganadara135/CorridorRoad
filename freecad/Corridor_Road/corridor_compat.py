# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""Central compatibility names for corridor migration boundaries.

Keep these values stable until the FCStd/macro compatibility window closes.
"""

PREFERRED_COMMAND_ID = "CorridorRoad_GenerateCorridor"
LEGACY_COMMAND_ID = "CorridorRoad_GenerateCorridorLoft"

PREFERRED_COMMAND_MODULE = "freecad.Corridor_Road.commands.cmd_generate_corridor"
LEGACY_COMMAND_MODULE = "freecad.Corridor_Road.commands.cmd_generate_corridor_loft"

PREFERRED_TASK_MODULE = "freecad.Corridor_Road.ui.task_corridor"
LEGACY_TASK_MODULE = "freecad.Corridor_Road.ui.task_corridor_loft"

PREFERRED_TASK_PANEL_CLASS = "CorridorTaskPanel"
LEGACY_TASK_PANEL_CLASS = "CorridorLoftTaskPanel"

CORRIDOR_PROXY_TYPE = "CorridorLoft"
CORRIDOR_NAME_PREFIX = "CorridorLoft"
CORRIDOR_PROJECT_PROPERTY = "CorridorLoft"
CORRIDOR_CHILD_LINK_PROPERTY = "ParentCorridorLoft"
CORRIDOR_SKIP_MARKER_NAME = "CorridorSkipMarker"
CORRIDOR_SEGMENT_NAME = "CorridorSegment"
