"""
Module containing the 'AeroBasicFileWriter' class, which writes a layout hole sequence to an AeroBasic program file.
"""

from .interfaces import NumericalControlFileWriter

class AeroBasicFileWriter(NumericalControlFileWriter):
    """
    Writes the laser machining sequence of a layout to an AeroBasic program file.
    """

    # Stage precision is 200 nm = 0.0002 mm → 4 decimal places + 2 for safety
    COORD_NUM_DIGITS = 6

    def __init__(
        self, 
        filename: str,
        # Stage parameters
        transition_feedrate: float = 0.2,
        shape_feedrate: float = 0.2,
        transition_feedrate_reduction_enabled: bool = False,
        transition_feedrate_reduction_distance_threshold_mm: float = 300/1000,
        transition_feedrate_reduction_factor: float = 3,
        # Laser parameters
        pulse_num: int = 3,
        frequency_Hz: int = 200000
    ) -> None:
        super().__init__()
        self.filename = filename

        # Set stage and laser parameters
        self.transition_feedrate = transition_feedrate
        self.shape_feedrate = shape_feedrate
        self.transition_feedrate_reduction_enabled = transition_feedrate_reduction_enabled
        self.transition_feedrate_reduction_distance_threshold_mm = transition_feedrate_reduction_distance_threshold_mm
        self.transition_feedrate_reduction_factor = transition_feedrate_reduction_factor
        self.pulse_num = pulse_num
        self.frequency_Hz = frequency_Hz
        
        # Initialize previous hole coordinates and string for hole commands
        self.prev_hole: tuple[float, float] = (0, 0)
        self.hole_commands: str = ""

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

    def add_hole(self, x: float, y: float) -> None:
        prev_x, prev_y = self.prev_hole
        distance = ((x - prev_x)**2 + (y - prev_y)**2)**0.5
        should_reduce_feedrate = (
            self.transition_feedrate_reduction_enabled and
            distance >= self.transition_feedrate_reduction_distance_threshold_mm
        )
        commands = []
        
        # Feedrate reduction
        if should_reduce_feedrate:
            commands.append(f"G63\nF {self.transition_feedrate/self.transition_feedrate_reduction_factor}")

        # X,Y manipulation needed to match stage coordinate system
        commands.append(f"G1 X {-y:.{self.COORD_NUM_DIGITS}f} Y {x:.{self.COORD_NUM_DIGITS}f}")

        # Feedrate reset
        if should_reduce_feedrate:
            commands.append(f"F {self.transition_feedrate}\nG64")

        # Subroutine to make hole
        commands.append("CALL MAKEHOLE")

        self.hole_commands += "\n".join(commands) + "\n"
        self.prev_hole = (x, y)

    def write_file(self) -> None:
        with open(self.filename, 'w') as file:
            file.write(self.start_commands() + "\n\n" + self.hole_commands + "\n" + self.end_commands())
        
        # Log inputs/parameters
        self.log(f"File path/name: {self.filename}")
        self.log(f"Transition feedrate: {self.transition_feedrate}")
        self.log(f"Shape feedrate: {self.shape_feedrate}")
        self.log(f"Transition feedrate reduction enabled: {self.transition_feedrate_reduction_enabled}")
        self.log(f"Transition feedrate reduction distance threshold (mm): {self.transition_feedrate_reduction_distance_threshold_mm}")
        self.log(f"Transition feedrate reduction factor: {self.transition_feedrate_reduction_factor}")
        self.log(f"Pulse number: {self.pulse_num}")
        self.log(f"Frequency (Hz): {self.frequency_Hz}")