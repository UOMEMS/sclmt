"""
Module containing functions for unit conversion.
"""

unit_conversion_factors: dict[str, float] = {
    "mm": 1e-3,
    "um": 1e-6,
    "nm": 1e-9
}

def get_valid_units() -> str:
    """
    Returns string containing recognized units.
    """
    return ', '.join(unit_conversion_factors.keys())

def is_valid_unit(unit: str) -> bool:
    """
    Returns True if input is a recognized unit.
    """
    return unit in unit_conversion_factors

def validate_unit(unit: str) -> None:
    """
    Raises ValueError if unit is unrecognized.
    """
    if not is_valid_unit(unit):
        error_lines = [
            f"Unit '{unit}' is unrecognized",
            f"Use the following units instead: {get_valid_units()}"
        ]
        raise ValueError("\n".join(error_lines))
    
def convert_units(value: float, from_unit: str, to_unit: str) -> float:
    """
    Converts a value from one unit to another.
    Raises ValueError if units are unrecognized.
    """
    validate_unit(from_unit)
    validate_unit(to_unit)
    return (value * unit_conversion_factors[from_unit]) / unit_conversion_factors[to_unit]