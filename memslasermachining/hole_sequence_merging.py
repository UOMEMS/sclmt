from .points import Point
from .interfaces import HoleSequenceMerger

class ConsecutiveHoleSequenceMerger(HoleSequenceMerger):
    """
    Merges hole sequences by concatenating them in the order they are provided.
    """
    
    def get_merged_hole_sequence(self, hole_sequences: list[list[list[Point]]]) -> list[list[Point]]:
        merged_hole_sequence = []
        for hole_sequence in hole_sequences:
            merged_hole_sequence.extend(hole_sequence)
        return merged_hole_sequence

class InterleavedHoleSequenceMerger(HoleSequenceMerger):
    """
    Merges hole sequences by interleaving their passes.
    Pass i of merged hole sequence is the union of pass i of all provided hole sequences.
    """
    
    def get_merged_hole_sequence(self, hole_sequences: list[list[list[Point]]]) -> list[list[Point]]:
        max_num_passes = max(len(hole_sequence) for hole_sequence in hole_sequences)
        merged_hole_sequence = [[] for _ in range(max_num_passes)]
        for hole_sequence in hole_sequences:
            for pass_index in range(len(hole_sequence)):
                merged_hole_sequence[pass_index].extend(hole_sequence[pass_index])
        return merged_hole_sequence