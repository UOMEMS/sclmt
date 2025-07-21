"""
Module containing the `Loggable` class, which provides a simple logging system.
"""

import datetime

class Loggable:
    
    INDENT = "  "

    def __init__(self) -> None:
        self._log = []

    def log(self, message: str, indent_level: int = 0) -> None:
        if message == "":
            return
        if indent_level > 0:
            message = self.INDENT * indent_level + message
        self._log.append(message)

    def get_log(self, indent_level: int = 0) -> str:
        if indent_level <= 0:
            return "\n".join(self._log)
        return "\n".join(self.INDENT * indent_level + line for line in self._log)

    def write_log_to_file(self, filepath: str) -> None:
        date = datetime.datetime.now().strftime("%d-%m-%Y")

        filename_parts = filepath.rsplit('.', 1)
        dated_filepath = f"{filename_parts[0]}_{date}"
        if len(filename_parts) > 1:
            dated_filepath += f".{filename_parts[1]}"
        
        with open(dated_filepath, "w") as f:
            f.write(f"Date: {date}\n")
            f.write(self.get_log())