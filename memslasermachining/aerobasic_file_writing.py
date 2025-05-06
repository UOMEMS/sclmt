"""
Module containing the 'AeroBasicFileWriter' class, which writes the laser machining sequence of a layout to an AeroBasic program file.
"""

from .points import Point
from .interfaces import FileWriter

class AeroBasicFileWriter(FileWriter):
    """
    Writes the laser machining sequence of a layout to an AeroBasic program file.
    """

    def __init__(self, filename: str) -> None:
        # Set default stage parameters
        self.transition_feedrate: float = 0.2
        self.shape_feedrate: float = 0.2
        self.transition_feedrate_reduction_enabled: bool = False
        self.transition_feedrate_reduction_distance_threshold_mm: float = 300/1000
        self.transition_feedrate_reduction_factor: float = 3
        # Set default laser parameters
        self.pulse_num: int = 3
        self.frequency_Hz: int = 200000
        # Initialize previous hole coordinates
        self.prev_hole: Point = Point([0, 0])
        # Initialize file name and string for hole commands
        self.filename: str = filename
        self.hole_commands: str = ""

    def _set_params(self, params: dict) -> None:
        """
        Private method for overwriting parameters if arguments are not None. 
        """
        for param, value in params.items():
            if param != 'self' and value is not None:
                setattr(self, param, value)

    def set_stage_params(self,
                         transition_feedrate: float = None,
                         shape_feedrate: float = None,
                         transition_feedrate_reduction_enabled: bool = None,
                         transition_feedrate_reduction_distance_threshold_mm: float = None,
                         transition_feedrate_reduction_factor: float = None) -> None:
        """
        Sets the parameters of the translational stage.
        Unspecified parameters will assume default values.
        """
        self._set_params(locals())
    
    def set_laser_params(self, pulse_num: int = None, frequency_Hz: int = None) -> None:
        """
        Sets the parameters of the laser.
        Unspecified parameters will assume default values.
        """
        self._set_params(locals())
    
    def start_commands(self) -> str:
        """
        String of commands at the start of the program.
        """
        lines = [
            f"#define CoordinatedMotionTransitionFeedrate {self.transition_feedrate}",
            f"#define ShapeFeedrate {self.shape_feedrate}\n",
            "DVAR $FREQUENCY",
            "DVAR $TOTtime",
            "DVAR $ONtime",
            "DVAR $PulseNum",
            "DVAR $DWELLTIME\n",
            "ABSOLUTE\n",
            "POSOFFSET SET X 0 Y 0\n",
            "'Default settings",
            f"$PulseNum = {self.pulse_num}",
            f"$FREQUENCY = {self.frequency_Hz}\n",
            "'Basics",
            "$ONtime = 1/$FREQUENCY * 1000000",
            "$TOTtime = $ONtime * 2\n",
            "'Start of laser machining",
            "$AO[0].X =5"
        ]
        return "\n".join(lines)
    
    def end_commands(self) -> str:
        """
        String of commands at the end of the program.
        """
        lines = [
            "'End of laser machining",
            "$AO[0].X =0\n",
            "G1 X 0 Y 0\n",
            "END PROGRAM\n",
            "'Subroutine to make hole (must be defined after end of program)",
            "DFS MAKEHOLE",
            "    PSOCONTROL X RESET",
            "    PSOPULSE X TIME $TOTtime, $ONtime CYCLES $PulseNum",
            "    PSOOUTPUT X PULSE",
            "    $DWELLTIME = $TOTtime/100000*$PulseNum",
            "    DWELL 0.08",
            "    PSOCONTROL X FIRE",
            "    DWELL $DWELLTIME",
            "ENDDFS"
        ]
        return "\n".join(lines)
    
    def get_length_unit(self) -> float:
        return 1e-3

    def add_hole(self, x_coord: float, y_coord: float) -> None:
        # Apply transition feedrate reduction if enabled and distance is greater than threshold
        curr_hole = Point([x_coord, y_coord])
        distance_to_prev_hole = Point.distance_between_points(curr_hole, self.prev_hole)
        reduce_transition_feedrate = self.transition_feedrate_reduction_enabled and distance_to_prev_hole >= self.transition_feedrate_reduction_distance_threshold_mm
        transition_feedrate_reduction = f"G63\nF {self.transition_feedrate/self.transition_feedrate_reduction_factor}" if reduce_transition_feedrate else ""
        transition_feedrate_reset = f"F {self.transition_feedrate}\nG64" if reduce_transition_feedrate else ""
        
        # Stage precision: 200 nm = 0.0002 mm accuracy → 4 decimal places + 2 for safety
        # Transform coordinates to match stage coordinate system
        num_digits = 6
        positioning = f"G1 X {-y_coord:.{num_digits}f} Y {x_coord:.{num_digits}f}"
        subroutine = "CALL MAKEHOLE"
        
        # Construct command string
        self.hole_commands += transition_feedrate_reduction + "\n" + positioning + "\n" + transition_feedrate_reset + "\n" + subroutine + "\n"
        
        # Update previous hole
        self.prev_hole = curr_hole

    def write_file(self) -> None:
        with open(self.filename, 'w') as file:
            file.write(self.start_commands() + "\n\n" + self.hole_commands + "\n" + self.end_commands())