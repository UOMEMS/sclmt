"""
Module containing constants that define default behaviour.
"""

### Sequencing ###

DEFAULT_LENGTH_UNIT: str = "um"

# Separation is measured between hole centers
HOLE_DIAMETER: float = 1.0
DEFAULT_TARGET_INIT_SEPARATION: float = HOLE_DIAMETER + 5.0
DEFAULT_TARGET_SEPARATION: float = HOLE_DIAMETER / 2

### Visualization ###

PLOT_MARGIN_FACTOR = 0.2