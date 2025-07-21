"""
Module containing the `PolygonHoleSequenceGenerator` class, which generates the hole sequence needed to laser machine a single polygon.
"""

import numpy as np
from .points import Point, PointArray
from .logging import Loggable

class PolygonHoleSequencePlanningError(Exception):
    pass

class PolygonHoleSequencePlan:
    """
    Calculates and stores values needed to generate a polygon hole sequence:
    - Number of passes excluding initial pass
    - Initial and total number of holes
    - Initial and final hole spacings
    """

    def __init__(self, polygon_perimeter: float, initial_num_holes: int, target_final_hole_spacing: float): 
        self.num_passes = round(np.log2(polygon_perimeter / (initial_num_holes * target_final_hole_spacing)))
        self.initial_num_holes = initial_num_holes
        self.total_num_holes = initial_num_holes * 2**self.num_passes
        self.initial_hole_spacing = polygon_perimeter / initial_num_holes
        self.final_hole_spacing = polygon_perimeter / self.total_num_holes

def plan_polygon_hole_sequence(polygon_perimeter: float,
                               min_initial_hole_spacing: float,
                               target_initial_hole_spacing: float | None,
                               target_final_hole_spacing: float) -> PolygonHoleSequencePlan:
    """
    Returns object containing values needed to generate a polygon hole sequence.
    If `target_initial_hole_spacing` is not provided, the optimal initial hole spacing is found using `min_initial_hole_spacing`.
    Raises `PolygonHoleSequencePlanningError` if input is invalid.
    """
    
    # Initial hole spacing is defined only if there are at least 2 initial holes
    MIN_INITIAL_NUM_HOLES = 2

    # Input validation helper
    def validate(initial_hole_spacing: float, initial_hole_spacing_name: str, initial_num_holes: int) -> None:
        if initial_hole_spacing <= target_final_hole_spacing:
            error_message = f"{initial_hole_spacing_name} ({initial_hole_spacing}) must be larger than target final hole spacing ({target_final_hole_spacing})"
            raise PolygonHoleSequencePlanningError(error_message)
        if initial_num_holes < MIN_INITIAL_NUM_HOLES:
            error_message = f"{initial_hole_spacing_name} ({initial_hole_spacing}) is too large for polygon perimeter ({polygon_perimeter}); yielded less than {MIN_INITIAL_NUM_HOLES} initial holes"
            raise PolygonHoleSequencePlanningError(error_message)

    # Use target initial hole spacing if provided
    if target_initial_hole_spacing is not None:
        initial_num_holes = round(polygon_perimeter / target_initial_hole_spacing)
        validate(target_initial_hole_spacing, "Target initial hole spacing", initial_num_holes)
        return PolygonHoleSequencePlan(polygon_perimeter, initial_num_holes, target_final_hole_spacing)

    # Find plan with optimal initial hole spacing
    max_initial_num_holes = int(np.floor(polygon_perimeter / min_initial_hole_spacing))
    validate(min_initial_hole_spacing, "Could not find optimal initial spacing since min initial hole spacing", max_initial_num_holes)
    plans = [
        PolygonHoleSequencePlan(polygon_perimeter, initial_num_holes, target_final_hole_spacing)
        for initial_num_holes in range(MIN_INITIAL_NUM_HOLES, max_initial_num_holes + 1)
    ]
    optimal_plan = min(plans, key = lambda plan: abs(target_final_hole_spacing - plan.final_hole_spacing))
    return optimal_plan

def generate_polygon_holes(vertices: PointArray, num_points: int, spacing: float) -> list[Point]:
    """
    Returns list of `Point` instances placed equidistantly along a polygon's perimeter, representing the holes to be laser machined.
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
        
        # Get distance between points and effective spacing (adjusted for carried distance)
        dist_between_points = Point.distance_between_points(p1, p2)
        spacing_eff = spacing - carry

        # If distance is insufficient, shift bounds and carry distance over to next iteration
        # Modular incr. of vertex pointer induces wraparound when final vertex is reached
        if dist_between_points <= spacing_eff:
            carry += dist_between_points
            vertex_ptr = (vertex_ptr + 1) % len(vertices)
            p1 = p2
            p2 = vertices[vertex_ptr]
        
        # Else place point between bounds and continue with new point as starting bound
        else:
            p_between = Point.point_between_points(p1, p2, spacing_eff)
            points.append(p_between)
            p1 = p_between
            carry = 0

        # Note: when point to be added coincides with a vertex, first conditional block is triggered,
        # bounds are shifted, and in next iteration, point is placed at previous ending bound
        # since spacing_eff = 0!

    return points

def generate_segment_hole_sequence_template(num_passes: int) -> list[list[int]]:
    """
    Returns a list, where each element is a list of segment hole indices belonging to a specific machining pass.
    Assumes segments are bounded by two initial holes which are excluded from the sequence.
    Argument `num_passes` excludes the initial pass.
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
    Returns a list, where each element is a list of `Point` instances representing holes belonging to a specific machining pass.
    Argument `num_passes` excludes the initial pass.
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
    def __init__(self,
                 vertices: PointArray,
                 min_initial_hole_spacing: float,
                 target_initial_hole_spacing: float | None,
                 target_final_hole_spacing: float) -> None:
        # Initialize logging
        super().__init__()

        # Generate polygon hole sequence
        polygon_perimeter = vertices.sum_of_distances(wraparound = True)
        polygon_hole_sequence_plan = plan_polygon_hole_sequence(polygon_perimeter, min_initial_hole_spacing, target_initial_hole_spacing, target_final_hole_spacing)
        polygon_holes = generate_polygon_holes(vertices, polygon_hole_sequence_plan.total_num_holes, polygon_hole_sequence_plan.final_hole_spacing)
        segment_hole_sequence_template = generate_segment_hole_sequence_template(polygon_hole_sequence_plan.num_passes)
        polygon_hole_sequence = generate_polygon_hole_sequence(
            polygon_holes, segment_hole_sequence_template, polygon_hole_sequence_plan.num_passes, polygon_hole_sequence_plan.initial_num_holes
        )
        self.polygon_hole_sequence_plan = polygon_hole_sequence_plan
        self.polygon_hole_sequence = polygon_hole_sequence

        # Log plan
        log_lines = [
            f"Number of passes (including initial pass): {self.polygon_hole_sequence_plan.num_passes + 1}",
            f"Initial number of holes: {self.polygon_hole_sequence_plan.initial_num_holes}",
            f"Total number of holes: {self.polygon_hole_sequence_plan.total_num_holes}",
            f"Initial hole spacing: {self.polygon_hole_sequence_plan.initial_hole_spacing}",
            f"Final hole spacing: {self.polygon_hole_sequence_plan.final_hole_spacing}"
        ]
        for line in log_lines: self.log(line)
    
    def get_polygon_hole_sequence_plan(self) -> PolygonHoleSequencePlan:
        """
        Returns the polygon hole sequence plan as an object containing no. passes excluding initial pass, initial and total no. holes, and initial and final hole spacings.
        """
        return self.polygon_hole_sequence_plan

    def get_polygon_hole_sequence(self) -> list[list[Point]]:
        """
        Returns the polygon hole sequence as a list of lists, where each element is a list of `Point` instances representing holes belonging to a specific machining pass.
        """
        return self.polygon_hole_sequence