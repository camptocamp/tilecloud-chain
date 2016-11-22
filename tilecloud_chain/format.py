# -*- coding: utf-8 -*-


def size_format(number):
    for unit in ['o', 'Kio', 'Mio', 'Gio', 'Tio']:
        if number < 1024.0:
            if number < 10:
                return "{0:.1f} {1!s}".format(number, unit)
            else:
                return "{0:.0f} {1!s}".format(number, unit)
        number /= 1024.0


def duration_format(duration):
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if duration.days > 0:
        return '{0:d} {1:d}:{2:02d}:{3:02d}'.format(duration.days, hours, minutes, seconds)
    else:
        return '{0:d}:{1:02d}:{2:02d}'.format(hours, minutes, seconds)
