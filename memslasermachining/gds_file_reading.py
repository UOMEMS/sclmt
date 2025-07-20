"""
Module containing the 'GDSFileReader' class, which reads the layout to be laser machined from a GDS file.
"""

from numpy.typing import ArrayLike
import gdspy
from .interfaces import LayoutFileReader

class GDSFileReader(LayoutFileReader):
    """
    Reads the layout to be laser machined from a GDS file.
    """

    def __init__(self, filename: str) -> None:
        super().__init__()

        # Read GDS file into library
        self.gds_lib = gdspy.GdsLibrary(infile = filename)

        # Check if cells exist
        if not self.gds_lib.cells:
            raise ValueError(f"No cells found in {filename}")
        
        # Get first and only cell in library
        cell: gdspy.Cell = list(self.gds_lib.cells.values())[0]
        
        # Get dictionary of polygons
        # K : V = (layer, datatype) : [ array( [ [x1, y1], … ] ), … ]
        polygons_dict = cell.get_polygons(by_spec = True)

        # Get polygon vertices
        # Assume each polygon is on layer 0 and has a unique datatype
        self.polygons_as_vertices = [polygons_dict[key][0] for key in sorted(polygons_dict) if key[0] == 0]

        # Log input
        self.log(f"File path/name: {filename}")

    def get_length_unit(self) -> float:
        return self.gds_lib.unit
    
    def get_polygons_as_vertices(self) -> list[ArrayLike]:
        return self.polygons_as_vertices