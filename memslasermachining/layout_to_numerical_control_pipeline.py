"""
Module containing the 'LayoutToNumericalControlPipeline' class, which orchestrates the generation of laser machining numerical control code from a layout.
"""

from typing import Callable, Any, Self
from functools import wraps
import numpy as np
from numpy.typing import ArrayLike

from .logging import Loggable
from .config import DEFAULT_LENGTH_UNIT, DEFAULT_MIN_INITIAL_HOLE_SEPARATION, DEFAULT_TARGET_FINAL_HOLE_SEPARATION
from .points import Point, PointArray
from .polygon_hole_sequence_generation import PolygonHoleSequencePlanningError, PolygonHoleSequenceGenerator
from .visualization import plot_polygons, animate_sequence
from .interfaces import LayoutFileReader, LayoutAligner, LayoutHoleSequenceAssembler, NumericalControlFileWriter

class LayoutToNumericalControlPipeline(Loggable):
    """
    Orchestrates the generation of laser machining numerical control code from a layout.
    """

    # ----------------------------
    # Construction and state validation
    # ----------------------------

    def __init__(self) -> None:
        super().__init__()
        self.length_unit: float = DEFAULT_LENGTH_UNIT
        self.polygons_as_vertices: list[PointArray] = None
        self.num_polygons: int = None
        self.min_initial_hole_separation: list[float] = None
        self.target_initial_hole_separation: list[float] = None
        self.target_final_hole_separation: list[float] = None
        self.polygon_hole_sequence_generators: list[PolygonHoleSequenceGenerator] = None
        self.layout_hole_sequence: list[list[Point]] = None

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
                        "layout_hole_sequence" : "Generate hole sequence"
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
        # Store number of polygons for later convenience
        self.num_polygons = len(self.polygons_as_vertices)
        
        return self

    def read_layout_file(self, layout_file_reader: LayoutFileReader) -> Self:
        """
        Sets the layout to be laser machined from the contents of a file.
        Adopts the length unit of the file being read.
        """
        self.set_length_unit(layout_file_reader.get_length_unit())
        self.set_polygons(layout_file_reader.get_polygons_as_vertices())
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
    # Hole sequence generation and assembly
    # ----------------------------

    @validate_state('polygons_as_vertices')
    def set_hole_separation(self,
                            min_initial_hole_separation: float | list[float] | None = None,
                            target_initial_hole_separation: float | list[float] | None = None,
                            target_final_hole_separation: float | list[float] | None = None) -> Self:
        """
        Sets the minimum initial, target initial, and target final pass hole separation between adjacent hole centers for each polygon.
        Target and actual hole separation may vary due to rounding.
        
        Only arguments that are provided (i.e., not None) will be used.
        Each argument can be a single value for all polygons or a list of values for each polygon.
        
        If `min_initial_hole_separation` and `target_final_hole_separation` are not provided, they will be set to the default values 
        specified in `config.py` when `generate_hole_sequence()` is called. 

        If `target_initial_hole_separation` is not provided, optimal initial hole separations will be automatically chosen 
        for each polygon when `generate_hole_sequence()` is called. An optimal initial hole separation is larger than the minimum 
        initial hole separation, and minimizes the difference between the target and actual final hole separation.
        """

        def set_validated_hole_separation(name: str, value: float | list[float] | None) -> None:
            # Prevent modification if corresponding argument is None since users can call set_hole_separation() multiple times
            if value is None:
                return
            if isinstance(value, list):
                if len(value) != self.num_polygons:
                    natural_name = name.replace("_", " ")
                    raise ValueError(f"Length of {natural_name} list does not equal the number of polygons")
            else:
                value = [value for _ in range(self.num_polygons)]
            setattr(self, name, value)
        
        set_validated_hole_separation('min_initial_hole_separation', min_initial_hole_separation)
        set_validated_hole_separation('target_initial_hole_separation', target_initial_hole_separation)
        set_validated_hole_separation('target_final_hole_separation', target_final_hole_separation)
        
        return self

    @validate_state('polygons_as_vertices')
    def generate_hole_sequence(self, layout_hole_sequence_assembler: LayoutHoleSequenceAssembler) -> Self:
        """
        Generates the hole sequence used to laser machine the loaded layout.
        Polygon hole sequences are generated separately then assembled into a single layout-wide sequence according to the provided 'layout_hole_sequence_assembler'.
        All configurations and layout transformations should be set before calling this method.
        """
        # Just-in-time default binding of hole separations
        # If target_initial_hole_separation is None, optimal initial hole separation will be found in PHSG
        if self.min_initial_hole_separation is None:
            self.set_hole_separation(min_initial_hole_separation = DEFAULT_MIN_INITIAL_HOLE_SEPARATION)
        if self.target_initial_hole_separation is None:
            self.target_initial_hole_separation = [None for _ in range(self.num_polygons)]
        if self.target_final_hole_separation is None:
            self.set_hole_separation(target_final_hole_separation = DEFAULT_TARGET_FINAL_HOLE_SEPARATION)
        
        # Try to sequence polygons
        self.polygon_hole_sequence_generators = []
        for polygon_index in range(self.num_polygons):
            vertices = self.polygons_as_vertices[polygon_index]
            min_initial_hole_separation = self.min_initial_hole_separation[polygon_index]
            target_initial_hole_separation = self.target_initial_hole_separation[polygon_index]
            target_final_hole_separation = self.target_final_hole_separation[polygon_index]
            try:
                args = (vertices, min_initial_hole_separation, target_initial_hole_separation, target_final_hole_separation)
                polygon_hole_sequence_generator = PolygonHoleSequenceGenerator(*args)
            except PolygonHoleSequencePlanningError as error:
                raise ValueError(f"Polygon hole sequence could not be generated for polygon {polygon_index + 1}\n{error}")
            self.polygon_hole_sequence_generators.append(polygon_hole_sequence_generator)

        # Assemble polygon hole sequences
        polygon_hole_sequences = [generator.get_polygon_hole_sequence() for generator in self.polygon_hole_sequence_generators]
        self.layout_hole_sequence = layout_hole_sequence_assembler.get_layout_hole_sequence(polygon_hole_sequences)

        # Log polygon hole sequence plans
        for polygon_index in range(self.num_polygons):
            self.log(f"***Polygon {polygon_index + 1}***")
            self.log(f"Target initial hole separation: {self.target_initial_hole_separation[polygon_index]}")
            self.log(f"Target final hole separation: {self.target_final_hole_separation[polygon_index]}")
            self.log(self.polygon_hole_sequence_generators[polygon_index].get_log())

        return self

    # ----------------------------
    # Numerical control generation
    # ----------------------------

    @validate_state('layout_hole_sequence')
    def write_numerical_control_file(self, numerical_control_file_writer: NumericalControlFileWriter) -> Self:
        """
        Writes the hole sequence for the loaded layout to a numerical control file.
        Converts the length unit of hole coordinates to that of the file being written.
        """
        unit_conversion_factor = self.length_unit / numerical_control_file_writer.get_length_unit()
        for current_pass in self.layout_hole_sequence:
            for point in current_pass:
                numerical_control_file_writer.add_hole(point.x * unit_conversion_factor, point.y * unit_conversion_factor)
        numerical_control_file_writer.write_file()
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

    @validate_state('layout_hole_sequence')
    def view_sequence(self, individually: bool = False, animation_interval_ms: int = 200) -> Self:
        """
        Animates the laser machining sequence of the loaded layout. Each color represents a different pass.
        If argument 'individually' is True, each polygon's sequence is shown individually.
        """
        if individually:
            for (vertices, generator) in zip(self.polygons_as_vertices, self.polygon_hole_sequence_generators):
                animate_sequence(vertices, generator.get_polygon_hole_sequence(), animation_interval_ms)
        else:
            polygons_as_vertices_merged = PointArray.concatenate(self.polygons_as_vertices)
            animate_sequence(polygons_as_vertices_merged, self.layout_hole_sequence, animation_interval_ms)
        return self