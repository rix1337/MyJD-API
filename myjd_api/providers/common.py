# -*- coding: utf-8 -*-
# MyJD
# Project by https://github.com/rix1337


import base64
import socket

from myjd_api.providers import myjdapi


def check_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 0))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def decode_base64(value):
    return base64.b64decode(value).decode()


def readable_size(size):
    if size:
        power = 2 ** 10
        n = 0
        powers = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        while size > power:
            size /= power
            n += 1
        size = round(size, 2)
        size = str(size) + " " + powers[n] + 'B'
        return size
    else:
        return ""


def readable_time(time):
    if time < 0:
        return ""
    else:
        days = time // 86400
        hours = (time - days * 86400) // 3600
        minutes = (time - days * 86400 - hours * 3600) // 60
        seconds = round((time - days * 86400 - hours * 3600 - minutes * 60), 2)
        time = ("{}d:".format(days) if days else "") + \
               ("{}h:".format(hours) if hours else "") + \
               ("{}m:".format(minutes) if minutes else "") + \
               ("{}s".format(seconds) if seconds else "")
    return time


def is_device(device):
    return isinstance(device, (type, myjdapi.Jddevice))
