"""
Module containing the 'PolygonHoleSequenceGenerator' class, which generates the hole sequence needed to laser machine a single polygon.
"""

from dataclasses import dataclass
import numpy as np
from .points import Point, PointArray
from .logging import Loggable

@dataclass
class PolygonHoleSequencePlan:
    num_passes: int
    initial_num_holes: int
    total_num_holes: int
    initial_hole_separation: float
    final_hole_separation: float

class PolygonHoleSequencePlanningError(Exception):
    pass

def plan_polygon_hole_sequence(polygon_perimeter: float, target_initial_hole_separation: float, target_final_hole_separation: float) -> PolygonHoleSequencePlan:
    """
    Returns object containing no. passes excluding initial pass, initial and total no. holes, and initial and final hole separations needed to laser machine a polygon.
    Raises 'PolygonHoleSequencePlanningError' if input is invalid.
    """
    
    # Validate input
    if target_initial_hole_separation <= target_final_hole_separation:
        raise PolygonHoleSequencePlanningError(f"Target initial hole separation ({target_initial_hole_separation}) must be larger than target final hole separation ({target_final_hole_separation})")
    if target_initial_hole_separation >= polygon_perimeter:
        raise PolygonHoleSequencePlanningError(f"Target initial hole separation ({target_initial_hole_separation}) must be smaller than polygon perimeter ({polygon_perimeter})")
    initial_num_holes = round(polygon_perimeter / target_initial_hole_separation)
    if initial_num_holes < 2:
        raise PolygonHoleSequencePlanningError(f"Target initial hole separation ({target_initial_hole_separation}) yielded less than 2 initial holes")
    
    # Generate plan
    num_passes = round(np.log2(polygon_perimeter / (initial_num_holes * target_final_hole_separation)))
    total_num_holes = initial_num_holes * 2**num_passes
    initial_hole_separation = polygon_perimeter / initial_num_holes
    final_hole_separation = polygon_perimeter / total_num_holes
    return PolygonHoleSequencePlan(num_passes, initial_num_holes, total_num_holes, initial_hole_separation, final_hole_separation)

def generate_polygon_holes(vertices: PointArray, num_points: int, separation: float) -> list[Point]:
    """
    Returns list of Point instances placed equidistantly along a polygon's perimeter, representing the holes to be laser machined.
    """

    # Select first vertex as first point
    # Use first point and second vertex as bounds for additional points (note: no. vertices >= 3)
    p1 = vertices[0]
    p2 = vertices[1]
    points = [p1]

    # Initialize vertex pointer to second vertex and carried distance to 0
    vertex_ptr = 1
    carry = 0.0

    # Travel along perimeter, placing equidistant points
    while len(points) < num_points:
        
        # Get distance between points and effective separation (adjusted for carried distance)
        dist_between_points = Point.distance_between_points(p1, p2)
        separation_eff = separation - carry

        # If distance is insufficient, shift bounds and carry distance over to next iteration
        # Modular incr. of vertex pointer induces wraparound when final vertex is reached
        if dist_between_points <= separation_eff:
            carry += dist_between_points
            vertex_ptr = (vertex_ptr + 1) % len(vertices)
            p1 = p2
            p2 = vertices[vertex_ptr]
        
        # Else place point between bounds and continue with new point as starting bound
        else:
            p_between = Point.point_between_points(p1, p2, separation_eff)
            points.append(p_between)
            p1 = p_between
            carry = 0

        # Note: when point to be added coincides with a vertex, first conditional block is triggered,
        # bounds are shifted, and in next iteration, point is placed at previous ending bound
        # since separation_eff = 0!

    return points

def generate_segment_hole_sequence_template(num_passes: int) -> list[list[int]]:
    """
    Returns a list, where each element is a list of segment hole indices belonging to a specific machining pass.
    Assumes segments are bounded by two initial holes which are excluded from the sequence.
    Argument 'num_passes' excludes the initial pass.
    """
    
    # Partitioning helpers
    def middle_index(lst: list) -> int: return int((len(lst) - 1) / 2)
    def left_partition(lst: list) -> list: return lst[0 : middle_index(lst) + 1]
    def right_partition(lst: list) -> list: return lst[middle_index(lst) : len(lst)]
    
    # Logarithmically partitions list of segment hole indices
    # Assigns the index of each hole to a machining pass
    def recurse(segment_hole_sequence_template: list[list[int]], partition: list[int], pass_index: int) -> None:
        partition_length = len(partition)
        # Base case: no middle element
        if partition_length < 3: return
        # General case: append middle element to this pass
        segment_hole_sequence_template[pass_index].append(partition[middle_index(partition)])
        # Recursive case: partition can be decomposed further
        if partition_length == 3: return
        left = left_partition(partition)
        right = right_partition(partition)
        recurse(segment_hole_sequence_template, left, pass_index + 1)
        recurse(segment_hole_sequence_template, right, pass_index + 1)

    # Initiate sequencing
    # There are 2^num_passes - 1 internal + 2 bounding holes per segment
    segment_num_holes = ((2 ** num_passes) - 1) + 2
    segment_hole_indices = [i for i in range(segment_num_holes)]
    segment_hole_sequence_template = [[] for _ in range(num_passes)]
    recurse(segment_hole_sequence_template, segment_hole_indices, 0)
    return segment_hole_sequence_template

def generate_polygon_hole_sequence(holes: list[Point], segment_hole_sequence_template: list[list[int]], num_passes: int, initial_num_holes: int) -> list[list[Point]]:
    """
    Returns a list, where each element is a list of Point instances representing holes belonging to a specific machining pass.
    Argument 'num_passes' excludes the initial pass.
    """
    
    # Each segment of the polygon contains the same number of holes
    # The sequence of a single segment can be used to sequence the entire polygon in O(num_holes) time
    # Indices of equivalent holes in adjacent segments are separated by an offset = 2^num_passes
    num_segments = initial_num_holes
    base_index_offset = 2 ** num_passes
    polygon_hole_sequence = [[] for _ in range(num_passes)]
    for pass_index in range(num_passes):
        segment_hole_indices = segment_hole_sequence_template[pass_index]
        for segment_index in range(num_segments):
            for segment_hole_index in segment_hole_indices:
                target_hole = holes[segment_hole_index + base_index_offset * segment_index]
                polygon_hole_sequence[pass_index].append(target_hole)
    
    # Add initial holes
    polygon_hole_sequence.insert(0, [])
    for initial_hole_index in [base_index_offset * i for i in range(initial_num_holes)]:
        initial_hole = holes[initial_hole_index]
        polygon_hole_sequence[0].append(initial_hole)
    return polygon_hole_sequence

class PolygonHoleSequenceGenerator(Loggable):
    """
    Generates the hole sequence needed to laser machine a single polygon.
    """
    def __init__(self, vertices: PointArray, target_initial_hole_separation: float, target_final_hole_separation: float) -> None:
        super().__init__()

        # Generate polygon hole sequence
        polygon_perimeter = vertices.sum_of_distances(wraparound = True)
        polygon_hole_sequence_plan = plan_polygon_hole_sequence(polygon_perimeter, target_initial_hole_separation, target_final_hole_separation)
        polygon_holes = generate_polygon_holes(vertices, polygon_hole_sequence_plan.total_num_holes, polygon_hole_sequence_plan.final_hole_separation)
        segment_hole_sequence_template = generate_segment_hole_sequence_template(polygon_hole_sequence_plan.num_passes)
        polygon_hole_sequence = generate_polygon_hole_sequence(
            polygon_holes, segment_hole_sequence_template, polygon_hole_sequence_plan.num_passes, polygon_hole_sequence_plan.initial_num_holes
        )
        self.polygon_hole_sequence_plan = polygon_hole_sequence_plan
        self.polygon_hole_sequence = polygon_hole_sequence

        # Log plan
        log_lines = [
            f"No. passes (excluding initial pass): {self.polygon_hole_sequence_plan.num_passes}",
            f"Initial pass no. holes: {self.polygon_hole_sequence_plan.initial_num_holes}",
            f"Total no. holes: {self.polygon_hole_sequence_plan.total_num_holes}",
            f"Initial pass hole separation: {self.polygon_hole_sequence_plan.initial_hole_separation}",
            f"Final pass hole separation: {self.polygon_hole_sequence_plan.final_hole_separation}"
        ]
        self.log("\n".join(log_lines))
    
    def get_polygon_hole_sequence_plan(self) -> PolygonHoleSequencePlan:
        """
        Returns the polygon hole sequence plan as an object containing no. passes excluding initial pass, initial and total no. holes, and initial and final hole separations.
        """
        return self.polygon_hole_sequence_plan

    def get_polygon_hole_sequence(self) -> list[list[Point]]:
        """
        Returns the polygon hole sequence as a list of lists, where each element is a list of Point instances representing holes belonging to a specific machining pass.
        """
        return self.polygon_hole_sequence