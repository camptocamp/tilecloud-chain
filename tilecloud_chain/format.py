from datetime import timedelta
from typing import Tuple


def default_int(number_array: Tuple[float, float, float, float]) -> Tuple[int, int, int, int]:
    """Convert an array of float in an array of int."""
    return (int(number_array[0]), int(number_array[1]), int(number_array[2]), int(number_array[3]))


def size_format(number: float) -> str:
    """Get human readable size."""
    for unit in ["o", "Kio", "Mio", "Gio", "Tio"]:
        if number < 1024.0:
            if number < 10:
                return f"{number:.1f} {unit}"
            else:
                return f"{number:.0f} {unit}"
        number /= 1024.0
    return f"{number:.0f} Tio"


def duration_format(duration: timedelta) -> str:
    """Get human readable duration."""
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if duration.days > 0:
        return f"{duration.days} {hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
