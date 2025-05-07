"""
Module containing the 'AeroBasicFileWriter' class, which writes the laser machining sequence of a layout to an AeroBasic program file.
"""

from .interfaces import FileWriter

class AeroBasicFileWriter(FileWriter):
    """
    Writes the laser machining sequence of a layout to an AeroBasic program file.
    """

    # Stage precision is 200 nm = 0.0002 mm → 4 decimal places + 2 for safety
    COORD_NUM_DIGITS = 6

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
        self.prev_hole: tuple[float, float] = (0, 0)
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
        prev_x_coord, prev_y_coord = self.prev_hole
        distance = ((x_coord - prev_x_coord)**2 + (y_coord - prev_y_coord)**2)**0.5
        should_reduce_feedrate = (
            self.transition_feedrate_reduction_enabled and
            distance >= self.transition_feedrate_reduction_distance_threshold_mm
        )
        commands = []
        
        # Feedrate reduction
        if should_reduce_feedrate:
            commands.append(f"G63\nF {self.transition_feedrate/self.transition_feedrate_reduction_factor}")

        # X,Y manipulation needed to match stage coordinate system
        commands.append(f"G1 X {-y_coord:.{self.COORD_NUM_DIGITS}f} Y {x_coord:.{self.COORD_NUM_DIGITS}f}")

        # Feedrate reset
        if should_reduce_feedrate:
            commands.append(f"F {self.transition_feedrate}\nG64")

        # Subroutine to make hole
        commands.append("CALL MAKEHOLE")

        self.hole_commands += "\n".join(commands) + "\n"
        self.prev_hole = (x_coord, y_coord)

    def write_file(self) -> None:
        with open(self.filename, 'w') as file:
            file.write(self.start_commands() + "\n\n" + self.hole_commands + "\n" + self.end_commands())