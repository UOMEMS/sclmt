"""
Module containing interfaces (abstract classes) for reading layout files, aligning layouts, assembling layout hole sequences, and writing numerical control files.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from numpy.typing import ArrayLike
from .logging import Loggable
from .points import Point

class LayoutFileReader(ABC, Loggable):
    """
    Used to set the layout to be laser machined from the contents of a file.
    """

    @abstractmethod
    def get_length_unit(self) -> float:
        """
        Returns length unit of the file being read as a scaling factor with respect to meters (e.g., 1e-6 → μm).
        """
        pass
    
    @abstractmethod
    def get_polygons_as_vertices(self) -> list[ArrayLike]:
        """
        Returns the layout to be laser machined as a list of polygons from the file being read.
        Each polygon is represented by a vertex coordinate array (ArrayLike instance of shape [N][2]).
        The returned list is sorted by machining order.
        """
        pass

class LayoutAligner(ABC, Loggable):
    """
    Used to compute the transformations needed to align a layout with the physical substrate to be laser machined.
    Any 2D affine transformation can be constructed by applying, in any order and any number of times, translation, 
    independent x/y scaling (including negative factors for reflection), and rotation about (0,0).
    Order matters since these operations are not generally commutative.
    """

    class Transformation(ABC):
        """
        Base class for all transformation types.
        """
        pass

    @dataclass
    class Translation(Transformation):
        """
        Represents a translation transformation.
        """
        dx: float
        dy: float

    @dataclass
    class Scaling(Transformation):
        """
        Represents a scaling transformation.
        """
        scaling_factor_x: float
        scaling_factor_y: float

    @dataclass
    class Rotation(Transformation):
        """
        Represents a rotation transformation about (0,0).
        """
        angle_rad: float

    @abstractmethod
    def get_transformations(self) -> list[Transformation]:
        """
        Returns a list of transformations to be applied to the layout.
        The order of transformations in the list determines the order of application.
        """
        pass

class LayoutHoleSequenceAssembler(ABC, Loggable):
    """
    Used to assemble polygon hole sequences into a single layout-wide sequence.
    """

    @abstractmethod
    def get_layout_hole_sequence(self, polygon_hole_sequences: list[list[list[Point]]]) -> list[list[Point]]:
        """
        Returns a layout hole sequence assembled from the given polygon hole sequences.
        Argument `polygon_hole_sequences` is a list of hole sequences.
        Each hole sequence is a list of passes.
        Each pass is a list of holes.
        Each hole is represented as a `Point` instance.
        """
        pass

class NumericalControlFileWriter(ABC, Loggable):
    """
    Used to write a layout hole sequence to a numerical control file.
    """

    @abstractmethod
    def get_length_unit(self) -> float:
        """
        Returns length unit of the file being written as a scaling factor with respect to meters (e.g., 1e-6 → μm).
        """
        pass
    
    @abstractmethod
    def add_hole(self, x: float, y: float) -> None:
        """
        Adds the commands required to create a hole at the provided X-Y coordinates to the numerical control program.
        Coordinates are provided in the file's length unit.

        This method appends commands to a buffer (e.g., string instance variable).
        The actual file is only written when `write_file()` is called.
        """
        pass
    
    @abstractmethod
    def write_file(self) -> None:
        """
        Writes the numerical control program to a file.
        """
        pass