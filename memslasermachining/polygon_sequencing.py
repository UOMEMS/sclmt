"""
Module containing the 'PolygonSequencer' class, which generates the laser machining sequence for individual polygons.
"""

from dataclasses import dataclass
import numpy as np
from config import TARGET_SEPARATION
from points import Point, PointArray
from visualization import animate_sequence

@dataclass
class PolygonSequenceParams:
    num_passes: int
    init_num_holes: int
    num_holes: int
    init_separation: float
    separation: float

class PolygonSequencingError(Exception):
    pass

def decompose_polygon(vertices: PointArray, target_init_separation: float) -> PolygonSequenceParams:
    """
    Returns object containing no. passes (excluding initial pass), no. holes, and hole separation required to machine a polygon.
    """
    if target_init_separation <= TARGET_SEPARATION:
        raise PolygonSequencingError(f"Targeted initial hole separation must be larger than final separation ({TARGET_SEPARATION} µm)")
    perimeter = vertices.sum_of_distances(wraparound = True)
    if target_init_separation >= perimeter:
        raise PolygonSequencingError(f"Targeted initial hole separation must be smaller than polygon perimeter ({perimeter} µm)")
    init_num_holes = round(perimeter / target_init_separation)
    if init_num_holes < 2:
        raise PolygonSequencingError("Targeted initial hole separation yielded less than 2 initial holes")
    num_passes = round(np.log2(perimeter / (init_num_holes * TARGET_SEPARATION)))
    num_holes = init_num_holes + ((2 ** num_passes) - 1) * init_num_holes
    init_separation = perimeter / init_num_holes
    separation = perimeter / num_holes
    return PolygonSequenceParams(num_passes, init_num_holes, num_holes, init_separation, separation)

def densify_polygon(vertices: PointArray, num_points: int, separation: np.float64) -> list[Point]:
    """
    Returns list of points placed equidistantly along a polygon's perimeter.
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

def generate_segment_sequence_template(num_passes: int) -> list[list[int]]:
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
    def recurse(segment_sequence_template: list[list[int]], partition: list[int], pass_index: int) -> None:
        partition_length = len(partition)
        # Base case: no middle element
        if partition_length < 3: return
        # General case: append middle element to this pass
        segment_sequence_template[pass_index].append(partition[middle_index(partition)])
        # Recursive case: partition can be decomposed further
        if partition_length == 3: return
        left = left_partition(partition)
        right = right_partition(partition)
        recurse(segment_sequence_template, left, pass_index + 1)
        recurse(segment_sequence_template, right, pass_index + 1)

    # Initiate sequencing
    # There are 2^num_passes - 1 internal + 2 bounding holes per segment
    segment_num_holes = ((2 ** num_passes) - 1) + 2
    segment_hole_indices = [i for i in range(segment_num_holes)]
    segment_sequence_template = [[] for _ in range(num_passes)]
    recurse(segment_sequence_template, segment_hole_indices, 0)
    return segment_sequence_template

def generate_polygon_sequence(holes: list[Point], segment_sequence_template: list[list[int]], num_passes: int, init_num_holes: int) -> list[list[Point]]:
    """
    Returns a list, where each element is a list of Point instances representing holes belonging to a specific machining pass.
    Argument 'num_passes' excludes the initial pass.
    """
    
    # Each segment of the polygon contains the same number of holes
    # The sequence of a single segment can be used to sequence the entire polygon in O(num_holes) time
    # Indices of equivalent holes in adjacent segments are separated by an offset = 2^num_passes
    num_segments = init_num_holes
    base_index_offset = 2 ** num_passes
    polygon_sequence = [[] for _ in range(num_passes)]
    for pass_index in range(num_passes):
        segment_hole_indices = segment_sequence_template[pass_index]
        for segment_index in range(num_segments):
            for segment_hole_index in segment_hole_indices:
                target_hole = holes[segment_hole_index + base_index_offset * segment_index]
                polygon_sequence[pass_index].append(target_hole)
    
    # Add initial holes
    polygon_sequence.insert(0, [])
    for init_hole_index in [base_index_offset * i for i in range(init_num_holes)]:
        init_hole = holes[init_hole_index]
        polygon_sequence[0].append(init_hole)
    return polygon_sequence

class PolygonSequencer:
    """
    Generates the laser machining sequence for individual polygons.
    """
    def __init__(self, vertices: PointArray, target_init_separation: float) -> None:
        params = decompose_polygon(vertices, target_init_separation)
        holes = densify_polygon(vertices, params.num_holes, params.separation)
        segment_sequence_template = generate_segment_sequence_template(params.num_passes)
        sequence = generate_polygon_sequence(holes, segment_sequence_template, params.num_passes, params.init_num_holes)
        self.vertices = vertices
        self.params = params
        params.num_passes += 1
        self.sequence = sequence
    
    def __str__(self) -> str:
        lines = [
            "***Polygon Sequencer***",
            f"No. passes: {self.params.num_passes}",
            f"Initial pass no. holes: {self.params.init_num_holes}",
            f"No. holes: {self.params.num_holes}",
            f"Initial pass hole separation: {self.params.init_separation} µm",
            f"Hole separation: {self.params.separation} µm"
        ]
        return "\n".join(lines)
    
    def view_sequence(self, animation_interval_ms: int) -> None:
        """
        Animates the laser machining sequence of this polygon. Each color represents a different pass.
        """
        animate_sequence(self.vertices, self.sequence, animation_interval_ms)