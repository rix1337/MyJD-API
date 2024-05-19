# -*- coding: utf-8 -*-
# MyJD
# Project by https://github.com/rix1337

import os
import sys

from myjd_api.providers.config import Config
from myjd_api.providers.myjd import get_device
from myjd_api.providers.myjd import get_if_one_device


def config():
    configfile = "MyJD.conf"
    configpath = ""
    if os.path.exists(configfile):
        f = open(configfile, "r")
        configpath = f.readline()
    if len(configpath) == 0:
        configpath = os.path.dirname(sys.argv[0])
        configpath = configpath.replace("\\", "/")
        configpath = configpath[:-1] if configpath.endswith('/') else configpath
        f = open(configfile, "w")
        f.write(configpath)
        f.close()
    configpath = configpath.replace("\\", "/")
    configpath = configpath[:-1] if configpath.endswith('/') else configpath
    if not os.path.exists(configpath):
        os.makedirs(configpath)
    return configpath


def myjd_input(configfile):
    print(u"Please enter your MyJDownloader credentials:")
    user = input("Username/Email:")
    password = input("Password:")
    device = get_if_one_device(user, password)
    if device:
        print(u"Device name " + device + " found automatically.")
    else:
        device = input(u"Device name :")
    port = input("What port should MyJD listen on? Leave blank to use default 8080:")
    if not port:
        port = '8080'
    Config('MyJD', configfile).save("myjd_user", user)
    Config('MyJD', configfile).save("myjd_pass", password)
    Config('MyJD', configfile).save("myjd_device", device)
    Config('MyJD', configfile).save("port", port)
    device = get_device(configfile)
    if device:
        return device
    else:
        return False
