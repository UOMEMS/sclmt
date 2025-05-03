"""
Module containing the 'Loggable' class, which provides a simple logging system.
"""

import datetime

class Loggable:
    def __init__(self) -> None:
        self._log = []

    def log(self, message: str) -> None:
        self._log.append(message)

    def get_log(self) -> str:
        return "\n".join(self._log)

    def write_log_to_file(self, filepath: str) -> None:
        date = datetime.datetime.now().strftime("%d-%m-%Y")

        filename_parts = filepath.rsplit('.', 1)
        dated_filepath = f"{filename_parts[0]}_{date}"
        if len(filename_parts) > 1:
            dated_filepath += f".{filename_parts[1]}"
        
        with open(dated_filepath, "w") as f:
            f.write(f"Date: {date}\n")
            f.write(self.get_log())