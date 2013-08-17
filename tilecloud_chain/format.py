# -*- coding: utf-8 -*-


def size_format(number):
    for unit in ['o', 'Kio', 'Mio', 'Gio', 'Tio']:
        if number < 1024.0:
            if number < 10:
                return "%.1f %s" % (number, unit)
            else:
                return "%.0f %s" % (number, unit)
        number /= 1024.0


def duration_format(duration):
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if duration.days > 0:
        return '%i %i:%02i:%02i' % (duration.days, hours, minutes, seconds)
    else:
        return '%i:%02i:%02i' % (hours, minutes, seconds)
