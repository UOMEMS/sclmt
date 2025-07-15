"""
Module containing interfaces (abstract classes) for reading files, aligning layouts, assembling layout hole sequences, and writing files.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from numpy.typing import ArrayLike
from .points import Point

class LayoutFileReader(ABC):
    """
    Used to set the layout to be laser machined from the contents of a file.
    """

    @abstractmethod
    def get_length_unit(self) -> float:
        """
        Returns length unit used by the file being read as a scaling factor with respect to meters.
        """
        pass
    
    @abstractmethod
    def get_polygons_as_vertices(self) -> list[ArrayLike]:
        """
        Returns the layout to be laser machined as a list of polygons from the file being read.
        Each polygon is represented by a vertex array (ArrayLike instance of shape [N][2]).
        The returned list is sorted by machining order.
        """
        pass

class LayoutAligner(ABC):
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

class LayoutHoleSequenceAssembler(ABC):
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
        Each hole is represented as a Point instance.
        """
        pass

class FileWriter(ABC):
    """
    Used to write the laser machining sequence of a layout to a file.
    """

    @abstractmethod
    def get_length_unit(self) -> float:
        """
        Returns length unit used by the file being written as a scaling factor with respect to meters.
        """
        pass
    
    @abstractmethod
    def add_hole(self, x_coord: float, y_coord: float) -> None:
        """
        Adds the content associated with a laser-machined hole to the file's contents.
        This method does not write to the file directly but modifies the in-memory contents that will be written in a later step. 
        Coordinates are provided in the file's length unit.
        """
        pass
    
    @abstractmethod
    def write_file(self) -> None:
        """
        Writes this instance's in-memory contents to a file.
        """
        pass