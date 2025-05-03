"""
Module containing the 'LayoutSequencer' class, which generates the laser machining sequence for entire layouts.
"""

from typing import Callable, Any, Self
from functools import wraps
import numpy as np
from numpy.typing import ArrayLike
from .config import DEFAULT_LENGTH_UNIT, DEFAULT_TARGET_INIT_SEPARATION, DEFAULT_TARGET_SEPARATION
from .points import Point, PointArray
from .polygon_sequencing import PolygonSequencer, PolygonSequencingError
from .visualization import plot_polygons, animate_sequence
from .interfaces import FileReader, LayoutAligner, HoleSequenceMerger, FileWriter

class LayoutSequencer:
    """
    Generates the laser machining sequence for entire layouts.
    """

    # ----------------------------
    # Construction and state validation
    # ----------------------------

    def __init__(self) -> None:
        self.length_unit: float = DEFAULT_LENGTH_UNIT
        self.polygons_as_vertices: list[PointArray] = None
        self.num_polygons: int = None
        self.target_init_separation: list[float] = None
        self.target_separation: list[float] = None
        self.polygon_sequencers: list[PolygonSequencer] = None
        self.sequence: list[list[Point]] = None

    def validate_state(attribute_name: str) -> Callable:
        """
        Decorator to validate that a specific attribute is not None.
        """
        def decorator(method: Callable) -> Callable:
            @wraps(method)
            def wrapper(self, *args: Any, **kwargs: Any) -> Any:
                if getattr(self, attribute_name) is None:
                    error_message_roots = {
                        "polygons_as_vertices" : "Set polygons",
                        "polygon_sequencers" : "Generate polygon hole sequences",
                        "sequence" : "Generate sequence"
                    }
                    error_message = error_message_roots[attribute_name] + " before invoking " + method.__name__ + "()"
                    raise RuntimeError(error_message)
                return method(self, *args, **kwargs)
            return wrapper
        return decorator

    # ----------------------------
    # Layout loading
    # ----------------------------

    def set_length_unit(self, unit: float) -> Self:
        """
        Sets unit of length for the layout and all configurations.
        Provide unit as a scaling factor with respect to meters (e.g., um → 1e-6).
        Does not perform a unit conversion when invoked multiple times.
        """
        self.length_unit = unit
        return self

    def set_polygons(self, polygons_as_vertices: list[ArrayLike]) -> Self:
        """
        Sets the layout (list of polygons) to be laser machined.
        Each ArrayLike instance in argument 'polygons_as_vertices' must be of shape [N][2].
        Provide polygons in the desired machining order.
        """
        self.polygons_as_vertices = []
        for vertices_arraylike in polygons_as_vertices:
            # Try to convert ArrayLike of vertices to NDArray
            try:
                vertices_ndarray = np.array(vertices_arraylike, dtype = np.float64, copy = False)
            except (TypeError, ValueError):
                raise ValueError("Input arrays cannot be converted to numpy arrays")
            # Check NDArray of vertices has correct shape
            if vertices_ndarray.ndim!= 2 or vertices_ndarray.shape[1] != 2:
                raise ValueError("Input arrays violate [N][2] shape requirement")
            # Convert NDArray of vertices to PointArray before storing
            self.polygons_as_vertices.append(PointArray(vertices_ndarray))
        # Set target initial and final pass separation to default
        self.num_polygons = len(self.polygons_as_vertices)
        self.target_init_separation = [DEFAULT_TARGET_INIT_SEPARATION for _ in range(self.num_polygons)]
        self.target_separation = [DEFAULT_TARGET_SEPARATION for _ in range(self.num_polygons)]
        return self

    def read_file(self, file_reader: FileReader) -> Self:
        """
        Sets the layout to be laser machined from the contents of a file.
        Adopts the length unit of the file being read.
        """
        self.set_length_unit(file_reader.get_length_unit())
        self.set_polygons(file_reader.get_polygons_as_vertices())
        return self

    # ----------------------------
    # Layout transformations
    # ----------------------------

    @validate_state('polygons_as_vertices')
    def translate_layout(self, dx: float, dy: float) -> Self:
        """
        Translates all polygons in the loaded layout by the provided offsets.
        """
        for vertices in self.polygons_as_vertices:
            vertices.translate(dx, dy)
        return self

    @validate_state('polygons_as_vertices')
    def scale_layout(self, scaling_factor_x: float, scaling_factor_y: float | None = None) -> Self:
        """
        Scales all polygons in the loaded layout by the provided factors.
        If `scaling_factor_y` is not provided, it will use the same value as `scaling_factor_x`.
        """
        for vertices in self.polygons_as_vertices:
            vertices.scale(scaling_factor_x, scaling_factor_y)
        return self

    @validate_state('polygons_as_vertices')
    def rotate_layout(self, angle_rad: float) -> Self:
        """
        Rotates all polygons in the loaded layout about (0,0) by the provided angle.
        """
        for vertices in self.polygons_as_vertices:
            vertices.rotate(angle_rad)
        return self

    @validate_state('polygons_as_vertices')
    def align_layout(self, layout_aligner: LayoutAligner) -> Self:
        """
        Aligns the loaded layout with the physical substrate to be laser machined.
        """
        transformations = layout_aligner.get_transformations()
        for transformation in transformations:
            if isinstance(transformation, LayoutAligner.Translation):
                self.translate_layout(transformation.dx, transformation.dy)
            elif isinstance(transformation, LayoutAligner.Scaling):
                self.scale_layout(transformation.scaling_factor_x, transformation.scaling_factor_y)
            elif isinstance(transformation, LayoutAligner.Rotation):
                self.rotate_layout(transformation.angle_rad)
        return self

    # ----------------------------
    # Hole sequence generation and merging
    # ----------------------------

    @validate_state('polygons_as_vertices')
    def set_target_separation(self, target_separation: float | list[float], init_pass: bool) -> Self:
        """
        Sets the targeted initial or final pass separation between adjacent hole centers for each polygon (actual values vary due to rounding).
        If argument 'init_pass' is True, the initial separation is set, otherwise, the final separation is set.
        Provide as many values as polygons, or a single value for all polygons.
        """
        if isinstance(target_separation, list):
            if len(target_separation) != self.num_polygons:
                raise ValueError("List of target separations does not match the number of polygons")
        else:
            target_separation = [target_separation for _ in range(self.num_polygons)]
        if init_pass:
            self.target_init_separation = target_separation
        else:
            self.target_separation = target_separation
        return self

    @validate_state('polygons_as_vertices')
    def generate_layout_hole_sequence(self, hole_sequence_merger: HoleSequenceMerger) -> Self:
        """
        Generates the hole sequence needed to laser machine the loaded layout.
        Polygon hole sequences are generated separately then merged into a single layout hole sequence according to the provided 'hole_sequence_merger'.
        All configurations and layout transformations should be set before calling this method.
        """
        # Try to sequence polygons
        self.polygon_sequencers = []
        for polygon_index in range(self.num_polygons):
            vertices = self.polygons_as_vertices[polygon_index]
            target_init_separation = self.target_init_separation[polygon_index]
            target_separation = self.target_separation[polygon_index]
            try:
                polygon_sequencer = PolygonSequencer(vertices, target_init_separation, target_separation)
            except PolygonSequencingError as error:
                raise ValueError(f"Polygons could not be sequenced\n{error}")
            self.polygon_sequencers.append(polygon_sequencer)

        # Merge polygon hole sequences
        polygon_hole_sequences = [polygon_sequencer.sequence for polygon_sequencer in self.polygon_sequencers]
        self.sequence = hole_sequence_merger.get_merged_hole_sequence(polygon_hole_sequences)
        return self

    # ----------------------------
    # Numerical control generation
    # ----------------------------

    @validate_state('sequence')
    def write_file(self, file_writer: FileWriter) -> Self:
        """
        Writes the laser machining sequence of the loaded layout to a file.
        Converts the length unit of hole coordinates to that of the file being written.
        """
        unit_conversion_factor = self.length_unit / file_writer.get_length_unit()
        for current_pass in self.sequence:
            for point in current_pass:
                file_writer.add_hole(point.x * unit_conversion_factor, point.y * unit_conversion_factor)
        file_writer.write_file()
        return self

    # ----------------------------
    # Visualization
    # ----------------------------

    @validate_state('polygons_as_vertices')
    def view_layout(self) -> Self:
        """
        Plots the loaded layout. Colors represent machining order.
        Useful for checking a layout after applying a transformation.
        """
        plot_polygons(self.polygons_as_vertices)
        return self

    @validate_state('sequence')
    def view_sequence(self, individually: bool = False, animation_interval_ms: int = 200) -> None:
        """
        Animates the laser machining sequence of the loaded layout. Each color represents a different pass.
        If argument 'individually' is True, each polygon's sequence is shown individually.
        """
        if individually:
            for polygon_sequencer in self.polygon_sequencers:
                polygon_sequencer.view_sequence(animation_interval_ms)
        else:
            polygons_as_vertices_merged = PointArray.concatenate(self.polygons_as_vertices)
            animate_sequence(polygons_as_vertices_merged, self.sequence, animation_interval_ms)