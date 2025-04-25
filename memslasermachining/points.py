"""
Module containing numpy NDArray wrapper classes for working with points.
Point and PointArray classes use numpy's efficient linear algebra operations while providing full type hinting.
"""

from __future__ import annotations
from typing import overload
from collections.abc import Iterator
import numpy as np
from numpy.typing import NDArray

class Point:
    def __init__(self, coords: NDArray[np.float64]) -> None:
        """
        Argument 'coords' must be a 2-element array.
        """
        self.coords = coords
    
    def __str__(self) -> str:
        return str(self.coords)

    @property
    def x(self) -> np.float64:
        return self.coords[0]

    @property
    def y(self) -> np.float64:
        return self.coords[1]
    
    @staticmethod
    def distance_between_points(p1: Point, p2: Point) -> np.float64:
        """
        Returns the Euclidean distance between two points.
        """
        return np.linalg.norm(p2.coords - p1.coords)
    
    @staticmethod
    def point_between_points(p1: Point, p2: Point, distance: float) -> Point:
        """
        Returns a point on the line defined by two points at a given distance from the first.
        """
        vector = p2.coords - p1.coords
        unit_vector = vector / np.linalg.norm(vector)
        return Point(p1.coords + distance * unit_vector)

class PointArray:
    def __init__(self, points: NDArray[np.float64]) -> None:
        """
        Argument 'points' must be of shape [N][2].
        """
        self.points = points

    def __str__(self) -> str:
        return str(self.points)

    def __len__(self) -> int:
        return len(self.points)

    @overload
    def __getitem__(self, index: int) -> Point: ...
    
    @overload
    def __getitem__(self, index: slice) -> PointArray: ...

    def __getitem__(self, index: int | slice) -> Point | PointArray:
        if isinstance(index, int):
            return Point(self.points[index])
        elif isinstance(index, slice):
            return PointArray(self.points[index])

    def __iter__(self) -> Iterator[Point]:
        for point in self.points:
            yield Point(point)
    
    def scale(self, scaling_factor: float) -> None:
        """
        Multiplies the coordinates of each point in this PointArray by the provided factor.
        """
        self.points = self.points * scaling_factor
    
    def rotate(self, angle_rad: float) -> None:
        """
        Rotates each point in this PointArray about the origin (0,0) by the provided angle.
        Positive angles cause counterclockwise rotations.
        """
        rotation_matrix = np.array([
            [np.cos(angle_rad), -np.sin(angle_rad)],
            [np.sin(angle_rad), np.cos(angle_rad)]
        ])
        self.points = np.dot(self.points, rotation_matrix.T)

    def translate(self, dx: float, dy: float) -> None:
        """
        Translates all points in this PointArray by the provided changes in x and y.
        """
        self.points = self.points + np.array([dx, dy])

    def bounding_points(self, margin_factor: float = 0) -> tuple[Point, Point]:
        """
        Returns min and max Point instances that bound this PointArray.
        """

        # Use 'axis = 0' to perform operation down the columns
        points = self.points
        min_point = np.min(points, axis = 0)
        max_point = np.max(points, axis = 0)
        
        # Shift bound if at origin
        origin = np.array([0, 0])
        if np.array_equal(min_point, origin):
            min_point = np.array([-1, -1])
        elif np.array_equal(max_point, origin):
            max_point = np.array([1, 1])

        # Add margins
        x_range = max_point[0] - min_point[0]
        y_range = max_point[1] - min_point[1]
        x_margin = x_range * margin_factor
        y_margin = y_range * margin_factor
        min_point_adjusted = [
            min_point[0] - x_margin,
            min_point[1] - y_margin
        ]
        max_point_adjusted = [
            max_point[0] + x_margin,
            max_point[1] + y_margin
        ]

        return Point(min_point_adjusted), Point(max_point_adjusted)

    def sum_of_distances(self, wraparound: bool = False) -> np.float64:
        """
        Returns the sum of Euclidean distances between adjacent points.
        If 'wraparound' is true, distance between the first and last point is included.
        """
        # Use np.roll to shift array and find differences between adjacent points including wraparound
        diffs = self.points - np.roll(self.points, -1, axis = 0)
        distances = np.sqrt(np.sum(diffs**2, axis = 1))
        adjustment = 0 if wraparound == True else np.linalg.norm(self.points[0] - self.points[-1])
        return np.sum(distances) - adjustment

    @staticmethod
    def concatenate(point_arrays: list[PointArray]) -> PointArray:
        """
        Returns the concatenation of a list of PointArray instances.
        """
        ndarrays = [point_array.points for point_array in point_arrays]
        return PointArray(np.concatenate(ndarrays))