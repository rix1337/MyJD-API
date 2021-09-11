# -*- coding: utf-8 -*-
# MyJD
# Project by https://github.com/rix1337

"""MyJD-API.

Usage:
  web.py        [--jd-user=<USERNAME>]
                [--jd-pass=<PASSWORD>]
                [--jd-device=<DEVICENAME>]
                [--port=<PORT>]
                [--docker]

Options:
  --jd-user=USERNAME        Stores the username for My JDownloader
  --jd-pass=PASSWORD        Stores the password for My JDownloader
  --jd-device=DEVICENAME    Stores the device name for My JDownloader
  --port=<PORT>             Legt den Port des Webservers fest
  --docker                  Internal: Locks path and port to Docker default values (preventing wrong settings)
"""

import ast
import json
import os
import sys
import time

from docopt import docopt
from flask import Flask, request, jsonify
from gevent.pywsgi import WSGIServer

from myjd_api.common import check_ip
from myjd_api.common import decode_base64
from myjd_api.config import Config
from myjd_api.files import config
from myjd_api.files import myjd_input
from myjd_api.myjd import get_device
from myjd_api.myjd import get_if_one_device
from myjd_api.myjd import get_info
from myjd_api.myjd import get_state
from myjd_api.myjd import jdownloader_pause
from myjd_api.myjd import jdownloader_start
from myjd_api.myjd import jdownloader_stop
from myjd_api.myjd import move_to_downloads
from myjd_api.myjd import remove_from_linkgrabber
from myjd_api.myjd import retry_decrypt
from myjd_api.myjd import update_jdownloader
from myjd_api.version import get_version


def app_container(port, configfile, _device):
    global device
    device = _device

    app = Flask(__name__, template_folder='web')

    @app.route("/", methods=['GET'])
    def myjd_info():
        global device
        if request.method == 'GET':
            myjd = get_info(configfile, device)
            device = myjd[0]
            if myjd:
                return jsonify(
                    {
                        "downloader_state": myjd[1],
                        "grabber_collecting": myjd[2],
                        "update_ready": myjd[3],
                        "packages": {
                            "downloader": myjd[4][0],
                            "linkgrabber_decrypted": myjd[4][1],
                            "linkgrabber_offline": myjd[4][2],
                            "linkgrabber_failed": myjd[4][3]
                        }
                    }
                ), 200
            else:
                return "Failed", 400
        else:
            return "Failed", 405

    @app.route("/myjd_state/", methods=['GET'])
    def myjd_state():
        global device
        if request.method == 'GET':
            myjd = get_state(configfile, device)
            device = myjd[0]
            if myjd:
                return jsonify(
                    {
                        "downloader_state": myjd[1],
                        "grabber_collecting": myjd[2]
                    }
                ), 200
            else:
                return "Failed", 400
        else:
            return "Failed", 405

    @app.route("/myjd_move/<linkids>&<uuids>", methods=['POST'])
    def myjd_move(linkids, uuids):
        global device
        if request.method == 'POST':
            linkids_raw = ast.literal_eval(linkids)
            linkids = []
            if isinstance(linkids_raw, (list, tuple)):
                for linkid in linkids_raw:
                    linkids.append(linkid)
            else:
                linkids.append(linkids_raw)
            uuids_raw = ast.literal_eval(uuids)
            uuids = []
            if isinstance(uuids_raw, (list, tuple)):
                for uuid in uuids_raw:
                    uuids.append(uuid)
            else:
                uuids.append(uuids_raw)
            device = move_to_downloads(configfile, device, linkids, uuids)
            if device:
                return "Success", 200
            else:
                return "Failed", 400
        else:
            return "Failed", 405

    @app.route("/myjd_remove/<linkids>&<uuids>", methods=['POST'])
    def myjd_remove(linkids, uuids):
        global device
        if request.method == 'POST':
            linkids_raw = ast.literal_eval(linkids)
            linkids = []
            if isinstance(linkids_raw, (list, tuple)):
                for linkid in linkids_raw:
                    linkids.append(linkid)
            else:
                linkids.append(linkids_raw)
            uuids_raw = ast.literal_eval(uuids)
            uuids = []
            if isinstance(uuids_raw, (list, tuple)):
                for uuid in uuids_raw:
                    uuids.append(uuid)
            else:
                uuids.append(uuids_raw)
            device = remove_from_linkgrabber(configfile, device, linkids, uuids)
            if device:
                return "Success", 200
            else:
                return "Failed", 400
        else:
            return "Failed", 405

    @app.route("/myjd_retry/<linkids>&<uuids>&<b64_links>", methods=['POST'])
    def myjd_retry(linkids, uuids, b64_links):
        global device
        if request.method == 'POST':
            linkids_raw = ast.literal_eval(linkids)
            linkids = []
            if isinstance(linkids_raw, (list, tuple)):
                for linkid in linkids_raw:
                    linkids.append(linkid)
            else:
                linkids.append(linkids_raw)
            uuids_raw = ast.literal_eval(uuids)
            uuids = []
            if isinstance(uuids_raw, (list, tuple)):
                for uuid in uuids_raw:
                    uuids.append(uuid)
            else:
                uuids.append(uuids_raw)
            links = decode_base64(b64_links)
            links = links.split("\n")
            device = retry_decrypt(configfile, device, linkids, uuids, links)
            if device:
                return "Success", 200
            else:
                return "Failed", 400
        else:
            return "Failed", 405

    @app.route("/myjd_update/", methods=['POST'])
    def myjd_update():
        global device
        if request.method == 'POST':
            device = update_jdownloader(configfile, device)
            if device:
                return "Success", 200
            else:
                return "Failed", 400
        else:
            return "Failed", 405

    @app.route("/myjd_start/", methods=['POST'])
    def myjd_start():
        global device
        if request.method == 'POST':
            device = jdownloader_start(configfile, device)
            if device:
                return "Success", 200
            else:
                return "Failed", 400
        else:
            return "Failed", 405

    @app.route("/myjd_pause/<bl>", methods=['POST'])
    def myjd_pause(bl):
        global device
        bl = json.loads(bl)
        if request.method == 'POST':
            device = jdownloader_pause(configfile, device, bl)
            if device:
                return "Success", 200
            else:
                return "Failed", 400
        else:
            return "Failed", 405

    @app.route("/myjd_stop/", methods=['POST'])
    def myjd_stop():
        global device
        if request.method == 'POST':
            device = jdownloader_stop(configfile, device)
            if device:
                return "Success", 200
            else:
                return "Failed", 400
        else:
            return "Failed", 405

    http_server = WSGIServer(('0.0.0.0', port), app)
    http_server.serve_forever()


def main():
    arguments = docopt(__doc__, version='MyJD-API')

    if arguments['--docker']:
        configfile = '/config/MyJD.ini'
    else:
        configfile = config() + "/MyJD.ini"
    port = 8080
    if not os.path.exists(configfile):
        if arguments['--docker']:
            if arguments['--jd-user'] and arguments['--jd-pass']:
                Config('MyJD', configfile).save("myjd_user", arguments['--jd-user'])
                Config('MyJD', configfile).save("myjd_pass", arguments['--jd-pass'])
                if arguments['--jd-device']:
                    Config('MyJD', configfile).save("myjd_device", arguments['--jd-device'])
                else:
                    device_name = get_if_one_device(arguments['--jd-user'], arguments['--jd-pass'])
                    if device_name:
                        print(u"Device name " + device_name + " found automatically.")
                        Config('MyJD', configfile).save("myjd_device", device_name)
                    else:
                        print(
                            'Please provide "-e PARAMETER=[--jd-device=<DEVICENAME>]" for the first run of this docker image!')
                        print(u'Could not connect to My JDownloader! Exiting...')
                        time.sleep(10)
                        sys.exit(1)
                Config('MyJD', configfile).save("port", "8080")
                _device = get_device(configfile)
            else:
                print(
                    u'Please provide "-e PARAMETER=[--jd-user=<USERNAME> --jd-pass=<PASSWORD>" for the first run of this docker image!')
                print(u'Could not connect to My JDownloader! Exiting...')
                time.sleep(10)
                sys.exit(1)
        else:
            _device = myjd_input(configfile)
            settings = Config('MyJD', configfile)
            port = int(settings.get('port'))
    else:
        if arguments['--jd-user']:
            Config('MyJD', configfile).save("myjd_user", arguments['--jd-user'])
        if arguments['--jd-pass']:
            Config('MyJD', configfile).save("myjd_pass", arguments['--jd-pass'])
        if arguments['--jd-device']:
            Config('MyJD', configfile).save("myjd_device", arguments['--jd-device'])
        if arguments['--port'] and not arguments['--docker']:
            Config('MyJD', configfile).save("port", arguments['--port'])
        settings = Config('MyJD', configfile)
        user = settings.get('myjd_user')
        password = settings.get('myjd_pass')
        if not arguments['--docker']:
            port = int(settings.get('port'))
            if not port:
                port = 8080
        if not user and not password and not arguments['--docker']:
            _device = myjd_input(configfile)
            settings = Config('MyJD', configfile)
            user = settings.get('myjd_user')
            password = settings.get('myjd_pass')
            port = int(settings.get('port'))
        if user and password:
            _device = get_device(configfile)
            if not _device:
                _device = get_if_one_device(user, password)
                if _device:
                    print(u"Device name " + _device + " found automatically.")
                    settings.save('myjd_device', _device)
                    _device = get_device(configfile)
                else:
                    print(u'Could not connect to My JDownloader! Exiting...')
                    time.sleep(10)
                    sys.exit(1)
        else:
            print(u'Could not connect to My JDownloader! Exiting...')
            time.sleep(10)
            sys.exit(1)
    if _device:
        if not arguments['--docker']:
            print(u'MyJD-API (v.' + get_version() + ') is available at http://' + check_ip() + ':' + str(
                port) + u'/ connected with: ' + _device.name)
        else:
            print(u'MyJD-API (v.' + get_version() + ') is available and connected with: ' + _device.name)
        app_container(port, configfile, _device)
    else:
        print(u'Could not connect to My JDownloader! Exiting...')
        time.sleep(10)
        sys.exit(1)
