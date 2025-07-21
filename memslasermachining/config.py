"""
Module containing constants that define default behaviour.
"""

# Length unit used for constants below and all pipeline methods
# Defined as a scaling factor with respect to meters (e.g., 1e-6 → μm)
WORKING_LENGTH_UNIT: float = 1e-6

# Spacing is measured between the centers of adjacent holes along polygon perimeter
HOLE_DIAMETER: float = 1.0
DEFAULT_MIN_INITIAL_HOLE_SPACING: float = HOLE_DIAMETER + 5.0
DEFAULT_TARGET_FINAL_HOLE_SPACING: float = HOLE_DIAMETER / 2

# Visualization plot parameters
PLOT_MARGIN_FACTOR: float = 0.2
FILL_OPACITY: float = 0.6