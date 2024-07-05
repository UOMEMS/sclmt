"""
Module containing a function for visualizing laser machining sequences.
"""

import random
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from .config import PLOT_MARGIN_FACTOR
from .points import Point, PointArray

def animate_sequence(vertices: PointArray, sequence: list[list[Point]], animation_interval_ms: int) -> None:
    """
    Animates a machining sequence. Each color represents a different pass.
    """

    # Set plot bounds
    min_point, max_point = vertices.bounding_points(margin_factor = PLOT_MARGIN_FACTOR)
    fig, ax = plt.subplots()
    ax.set_xlim(min_point.x, max_point.x)
    ax.set_ylim(min_point.y, max_point.y)
    ax.set_xlabel('µm')
    ax.set_ylabel('µm')
    ax.set_aspect('equal')
    
    # Split sequence into x and y values
    split_sequence = [[],[]]
    for current_pass in sequence:
        split_sequence[0].append([point.x for point in current_pass])
        split_sequence[1].append([point.y for point in current_pass])
    sequence = split_sequence

    # Generate a unique random color for each pass
    colors = [f"#{random.randint(0, 0xFFFFFF):06x}" for _ in range(len(sequence[0]))]
    
    # Dictionary to hold circle patches by pass
    patches = {i: [] for i in range(len(sequence[0]))}

    def update(num):
        # Determine the pass to animate based on the current frame number
        current_pass = 0
        total_frames = 0
        for i in range(len(sequence[0])):
            if num < total_frames + len(sequence[0][i]):
                current_pass = i
                break
            total_frames += len(sequence[0][i])

        # Calculate the frame index within the current pass
        frame_within_pass = num - total_frames

        # Add new circles for the current pass and frame
        if frame_within_pass < len(sequence[0][current_pass]):
            x = sequence[0][current_pass][frame_within_pass]
            y = sequence[1][current_pass][frame_within_pass]
            circle = plt.Circle((x, y), 0.5, color=colors[current_pass], alpha=0.6)
            ax.add_patch(circle)
            patches[current_pass].append(circle)

        return [circle for sublist in patches.values() for circle in sublist]

    total_frames = sum(map(len, sequence[0]))  # Total frames needed to complete all passes
    ani = animation.FuncAnimation(fig, update, frames = total_frames, interval = animation_interval_ms, repeat = False)
    plt.show()