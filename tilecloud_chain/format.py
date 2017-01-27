# -*- coding: utf-8 -*-


def default_int(number_array):
    return [
        int(n) if n % 1 == 0 else n
        for n in number_array
    ]


def size_format(number):
    for unit in ['o', 'Kio', 'Mio', 'Gio', 'Tio']:
        if number < 1024.0:
            if number < 10:
                return "{:.1f} {}".format(number, unit)
            else:
                return "{:.0f} {}".format(number, unit)
        number /= 1024.0


def duration_format(duration):
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if duration.days > 0:
        return '{} {}:{:02d}:{:02d}'.format(duration.days, hours, minutes, seconds)
    else:
        return '{}:{:02d}:{:02d}'.format(hours, minutes, seconds)
