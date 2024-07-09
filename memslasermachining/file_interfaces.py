"""
Module containing interfaces (abstract classes) for reading and writing files.
"""

from abc import ABC, abstractmethod
from numpy.typing import ArrayLike

class FileReader(ABC):
    """
    Used to set a layout to be laser machined from the contents of a file.
    """

    @abstractmethod
    def get_length_unit(self) -> str:
        """
        Returns a string containing the length unit used by the file being read.
        """
        pass
    
    @abstractmethod
    def get_polygons_as_vertices(self) -> list[ArrayLike]:
        """
        Returns the layout (list of polygons) to be laser machined from the file being read.
        Each ArrayLike instance in the returned list is of shape [N][2].
        The returned list is sorted by machining order.
        """
        pass

class FileWriter(ABC):
    """
    Used to write the laser machining sequence of a layout to a file.
    """

    @abstractmethod
    def get_length_unit(self) -> str:
        """
        Returns a string containing the length unit used by the file being written.
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