"""
Module containing visualization functions.
"""

import random
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.axes import Axes
from .config import HOLE_DIAMETER, PLOT_MARGIN_FACTOR, FILL_OPACITY
from .points import Point, PointArray

def set_plot_bounds(ax: Axes, point_array: PointArray) -> None:
    """
    Sets the plot bounds to hug the provided point array with a margin.
    Sets the aspect ratio to be equal.
    """
    min_point, max_point = point_array.bounding_points(margin_factor=PLOT_MARGIN_FACTOR)
    ax.set_xlim(min_point.x, max_point.x)
    ax.set_ylim(min_point.y, max_point.y)
    ax.set_aspect('equal')

def unique_random_colors(num_colors: int) -> list[str]:
    """
    Generates a list of unique random colors as hex code strings.
    """
    colors = set()
    while len(colors) < num_colors:
        colors.add(f"#{random.randint(0, 0xFFFFFF):06x}")
    return list(colors)

def plot_polygons(polygons_as_vertices: list[PointArray]) -> None:
    """
    Plots the provided polygons. Colors represent machining order.
    """
    # Create plot and set bounds around union of all polygons
    _, ax = plt.subplots()
    set_plot_bounds(ax, PointArray.concatenate(polygons_as_vertices))
    
    # Generate unique random colors for each polygon
    colors = unique_random_colors(len(polygons_as_vertices))
    
    # Plot each polygon
    for i, polygon in enumerate(polygons_as_vertices):
        x_coords = [point.x for point in polygon]
        y_coords = [point.y for point in polygon]
        ax.fill(x_coords, y_coords, color=colors[i], alpha=FILL_OPACITY, label=f"{i+1}")
    
    # Add legend
    ax.legend(loc='upper center', ncol=len(polygons_as_vertices), frameon=False)
    plt.show()

def animate_hole_sequence(vertices: PointArray, hole_sequence: list[list[Point]], animation_interval_ms: int) -> None:
    """
    Animates the provided hole sequence. Each color represents a different pass.
    Argument `vertices` should be a single polygon when animating a polygon hole sequence,
    or the union of all polygons when animating a layout hole sequence.
    """
    # Create plot and set bounds
    fig, ax = plt.subplots()
    set_plot_bounds(ax, vertices)
    
    # Generate unique random colors for each pass
    colors = unique_random_colors(len(hole_sequence))
    
    # Flatten the hole sequence into a list of (hole, pass_index) tuples
    flattened_hole_sequence = []
    for pass_index, holes in enumerate(hole_sequence):
        for hole in holes:
            flattened_hole_sequence.append((hole, pass_index))
    
    # List to store all circle patches for cleanup
    circles = []
    
    def update(frame):
        """Animation update function called for each frame."""
        if frame < len(flattened_hole_sequence):
            hole, pass_index = flattened_hole_sequence[frame]
            circle = plt.Circle((hole.x, hole.y), HOLE_DIAMETER / 2, color=colors[pass_index], alpha=FILL_OPACITY)
            ax.add_patch(circle)
            circles.append(circle)
        
        return circles
    
    # Create and run the animation
    total_frames = len(flattened_hole_sequence)
    ani = animation.FuncAnimation(
        fig, 
        update, 
        frames=total_frames, 
        interval=animation_interval_ms, 
        repeat=False
    )
    plt.show()