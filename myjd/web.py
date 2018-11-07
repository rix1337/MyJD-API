# -*- coding: utf-8 -*-
# MyJD
# Project by https://github.com/rix1337

import ast
import json
import os
import sys

from flask import Flask, request, jsonify
from gevent.pywsgi import WSGIServer

from myjd.common import decode_base64
from myjd.config import Config
from myjd.files import config
from myjd.files import myjd_input
from myjd.myjd import get_device
from myjd.myjd import get_if_one_device
from myjd.myjd import get_info
from myjd.myjd import get_state
from myjd.myjd import jdownloader_pause
from myjd.myjd import jdownloader_start
from myjd.myjd import jdownloader_stop
from myjd.myjd import move_to_downloads
from myjd.myjd import remove_from_linkgrabber
from myjd.myjd import retry_decrypt
from myjd.myjd import update_jdownloader


def app_container(port, configfile, _device):
    global device
    device = _device

    app = Flask(__name__, template_folder='web')

    @app.route("/myjd/", methods=['GET'])
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


if __name__ == '__main__':
    configfile = config()
    if not os.path.exists(configfile):
        _device = myjd_input(configfile)
    else:
        settings = Config('MyJD', configfile)
        user = settings.get('myjd_user')
        password = settings.get('myjd_pass')
        port = settings.get('port')
        if user and password:
            _device = get_device(configfile)
            if not _device:
                _device = get_if_one_device(user, password)
                if _device:
                    print(u"Device name " + device + " found automatically.")
                    settings.save('myjd_device', device)
                    _device = get_device(configfile)
                else:
                    print(u'Could not connect to My JDownloader! Exiting...')
                    sys.exit(0)
        else:
            _device = False

    app_container(port, configfile, _device)
