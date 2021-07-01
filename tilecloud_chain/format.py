from datetime import timedelta
from typing import List, Tuple

# -*- coding: utf-8 -*-


def default_int(number_array: Tuple[float, float, float, float]) -> List[float]:
    return [int(n) if n % 1 == 0 else n for n in number_array]


def size_format(number: float) -> str:
    for unit in ["o", "Kio", "Mio", "Gio", "Tio"]:
        if number < 1024.0:
            if number < 10:
                return f"{number:.1f} {unit}"
            else:
                return f"{number:.0f} {unit}"
        number /= 1024.0
    return f"{number:.0f} Tio"


def duration_format(duration: timedelta) -> str:
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if duration.days > 0:
        return f"{duration.days} {hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
