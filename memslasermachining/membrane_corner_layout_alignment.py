"""
Module containing the 'MembraneCornerLayoutAligner' class, which is used to align a layout with a stage-mounted square membrane.
"""

import numpy as np
from .interfaces import LayoutAligner

class MembraneCornerLayoutAligner(LayoutAligner):
    """
    Computes the transformations needed to align a layout with a stage-mounted square membrane, using the membrane's corners as reference points.
    Layout must be initially centered at (0,0).
    Refer to the diagram in the README for details.

    Arguments:
    - `nominal_membrane_side_length`: membrane side length assumed in the layout design
    - `dx`, `dy`: measured displacement components from the bottom-left to the bottom-right corner of the membrane
    - All arguments must use the same units

    Transformations:
    - Scaling corrects for differences between the nominal and actual membrane size
    - Rotation corrects for angular misalignment between the layout and the stage-mounted membrane
    - Translation shifts the layout origin (0,0) from the center to the membrane's bottom-right corner, where the stage must be zeroed
    """

    def __init__(self, nominal_membrane_side_length: float, dx: float, dy: float) -> None:
        super().__init__()
        
        # Scaling
        actual_membrane_side_length = np.sqrt(dx ** 2 + dy ** 2)
        scaling_factor = actual_membrane_side_length / nominal_membrane_side_length
        
        # Rotation
        rotation_angle = np.arctan2(dy, dx)
        if rotation_angle < -np.pi / 4 or rotation_angle > np.pi / 4:
            raise ValueError("Wrong corners chosen, membrane angle is not within [-45, 45] degrees")
        
        # Translation
        bottom_right_to_center_angle = np.pi / 4 - rotation_angle
        membrane_diag_half_length = (np.sqrt(2) / 2) * actual_membrane_side_length
        bottom_right_to_center_x = -membrane_diag_half_length * np.cos(bottom_right_to_center_angle)
        bottom_right_to_center_y = membrane_diag_half_length * np.sin(bottom_right_to_center_angle)
        
        # Store transformations
        # Scaling and rotation require layout to be centered at (0,0), so translation must be applied last
        self.transformations = [
            LayoutAligner.Scaling(scaling_factor, scaling_factor),
            LayoutAligner.Rotation(rotation_angle),
            LayoutAligner.Translation(bottom_right_to_center_x, bottom_right_to_center_y)
        ]

        # Log inputs
        self.log(f"Nominal membrane side length: {nominal_membrane_side_length}")
        self.log(f"Displacement from bottom-left to bottom-right corner of membrane: dx = {dx}, dy = {dy}")

    def get_transformations(self) -> list[LayoutAligner.Transformation]:
        return self.transformations