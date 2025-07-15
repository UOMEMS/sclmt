from .points import Point
from .interfaces import LayoutHoleSequenceAssembler

class SequentialLayoutHoleSequenceAssembler(LayoutHoleSequenceAssembler):
    """
    Assembles layout hole sequence by concatenating polygon hole sequences in the order they are provided.
    """
    
    def get_layout_hole_sequence(self, polygon_hole_sequences: list[list[list[Point]]]) -> list[list[Point]]:
        layout_hole_sequence = []
        for hole_sequence in polygon_hole_sequences:
            layout_hole_sequence.extend(hole_sequence)
        return layout_hole_sequence

class InterleavedLayoutHoleSequenceAssembler(LayoutHoleSequenceAssembler):
    """
    Assembles layout hole sequence by interleaving the passes of polygon hole sequences.
    Pass i of layout hole sequence is the union of pass i of all provided polygon hole sequences.
    """
    
    def get_layout_hole_sequence(self, polygon_hole_sequences: list[list[list[Point]]]) -> list[list[Point]]:
        max_num_passes = max(len(hole_sequence) for hole_sequence in polygon_hole_sequences)
        layout_hole_sequence = [[] for _ in range(max_num_passes)]
        for hole_sequence in polygon_hole_sequences:
            for pass_index in range(len(hole_sequence)):
                layout_hole_sequence[pass_index].extend(hole_sequence[pass_index])
        return layout_hole_sequence