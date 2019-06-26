# -*- coding: utf-8 -*-
# MyJD
# Project by https://github.com/rix1337

import os
import sys

import six
from myjd_api.config import Config
from myjd_api.myjd import get_device
from myjd_api.myjd import get_if_one_device


def config():
    configfile = "MyJD.conf"
    if os.path.exists(configfile):
        f = open(configfile, "r")
        configpath = f.readline()
    else:
        print(u"Where do you want to store settings? Leave blank to use the current folder.")
        configpath = six.moves.input("Enter Path:")
        if len(configpath) > 0:
            f = open(configfile, "w")
            f.write(configpath)
            f.close()
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
    user = six.moves.input("Username/Email:")
    password = six.moves.input("Password:")
    device = get_if_one_device(user, password)
    if device:
        print(u"Device name " + device + " found automatically.")
    else:
        device = six.moves.input(u"Device name :")
    port = six.moves.input("What port should MyJD listen on? Leave blank to use default 8080:")
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
