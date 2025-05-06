"""
Module containing constants that define default behaviour.
"""

### Sequencing ###

DEFAULT_LENGTH_UNIT: float = 1e-6

# Separation is measured between hole centers
HOLE_DIAMETER: float = 1.0
DEFAULT_TARGET_INITIAL_HOLE_SEPARATION: float = HOLE_DIAMETER + 5.0
DEFAULT_TARGET_FINAL_HOLE_SEPARATION: float = HOLE_DIAMETER / 2
DEFAULT_MIN_INITIAL_HOLE_SEPARATION: float = HOLE_DIAMETER + 5.0
DEFAULT_AUTO_INITIAL_HOLE_SEPARATION: bool = False

### Visualization ###

PLOT_MARGIN_FACTOR: float = 0.2