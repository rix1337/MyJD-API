# -*- coding: utf-8 -*-
# MyJD
# Project by https://github.com/rix1337

import argparse
import ast
import json
import os
import sys
import time
from functools import wraps
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler

from Cryptodome.Protocol.KDF import scrypt
from Cryptodome.Random import get_random_bytes
from bottle import Bottle, request, redirect, abort, HTTPError
from myjd_api.providers.common import check_ip
from myjd_api.providers.common import decode_base64
from myjd_api.providers.config import Config
from myjd_api.providers.files import config
from myjd_api.providers.files import myjd_input
from myjd_api.providers.myjd import get_device
from myjd_api.providers.myjd import get_if_one_device
from myjd_api.providers.myjd import get_info
from myjd_api.providers.myjd import get_state
from myjd_api.providers.myjd import jdownloader_pause
from myjd_api.providers.myjd import jdownloader_start
from myjd_api.providers.myjd import jdownloader_stop
from myjd_api.providers.myjd import move_to_downloads
from myjd_api.providers.myjd import remove_from_linkgrabber
from myjd_api.providers.myjd import retry_decrypt
from myjd_api.providers.myjd import update_jdownloader
from myjd_api.providers.version import get_version


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class NoLoggingWSGIRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


class Server:
    def __init__(self, wsgi_app, listen='127.0.0.1', port=8080):
        self.wsgi_app = wsgi_app
        self.listen = listen
        self.port = port
        self.server = make_server(self.listen, self.port, self.wsgi_app,
                                  ThreadingWSGIServer, handler_class=NoLoggingWSGIRequestHandler)

    def serve_forever(self):
        self.server.serve_forever()


device = False
auth_user = False
auth_hash = False
known_hashes = {}


def app_container(port, configfile, _device):
    global device
    global auth_user
    global auth_hash
    global known_hashes

    device = _device

    app = Bottle()

    def to_str(i):
        return '' if i is None else str(i)

    def auth_basic(check_func, realm="private", text="Access denied"):
        def decorator(func):
            @wraps(func)
            def wrapper(*a, **ka):
                global auth_user
                global auth_hash
                _config = Config('Auth', configfile)
                auth_user = _config.get('auth_user')
                auth_hash = _config.get('auth_hash')
                user, password = request.auth or (None, None)
                if auth_user and auth_hash:
                    if user is None or not check_func(user, password):
                        err = HTTPError(401, text)
                        err.add_header('WWW-Authenticate', 'Basic realm="%s"' % realm)
                        return err
                return func(*a, **ka)

            return wrapper

        return decorator

    def is_authenticated_user(user, password):
        global auth_user
        global auth_hash
        _config = Config('Auth', configfile)
        auth_user = _config.get('auth_user')
        auth_hash = _config.get('auth_hash')
        if auth_user and auth_hash:
            if auth_hash and "scrypt|" not in auth_hash:
                salt = get_random_bytes(16).hex()
                key = scrypt(auth_hash, salt, 16, N=2 ** 14, r=8, p=1).hex()
                auth_hash = "scrypt|" + salt + "|" + key
                _config.save("auth_hash", to_str(auth_hash))
            secrets = auth_hash.split("|")
            salt = secrets[1]
            config_hash = secrets[2]
            if password not in known_hashes:
                # Remember the hash for up to three passwords
                if len(known_hashes) > 2:
                    known_hashes.clear()
                sent_hash = scrypt(password, salt, 16, N=2 ** 14, r=8, p=1).hex()
                known_hashes[password] = sent_hash
            else:
                sent_hash = known_hashes[password]
            return user == _config.get("auth_user") and config_hash == sent_hash
        else:
            return True

    @app.get("/")
    @auth_basic(is_authenticated_user)
    def myjd_info():
        global device
        myjd = get_info(configfile, device)
        device = myjd[0]
        if myjd:
            return {
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
        else:
            return abort(400, "Failed")

    @app.hook('before_request')
    def redirect_without_trailing_slash():
        no_trailing_slash = [
            "/api/myjd_move/",
            "/api/myjd_remove/",
            "/api/myjd_retry/",
            "/api/myjd_pause/"
        ]
        if not request.path.endswith('/') and not any(s in request.path for s in no_trailing_slash):
            raise redirect(request.url + '/')

    @app.get("/myjd_state/")
    @auth_basic(is_authenticated_user)
    def myjd_state():
        global device
        myjd = get_state(configfile, device)
        device = myjd[0]
        if myjd:
            return {
                "downloader_state": myjd[1],
                "grabber_collecting": myjd[2]
            }
        else:
            return abort(400, "Failed")

    @app.post("/myjd_move/<linkids>&<uuids>")
    @auth_basic(is_authenticated_user)
    def myjd_move(linkids, uuids):
        global device

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
            return "Success"
        else:
            return abort(400, "Failed")

    @app.post("/myjd_remove/<linkids>&<uuids>")
    @auth_basic(is_authenticated_user)
    def myjd_remove(linkids, uuids):
        global device
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
            return "Success"
        else:
            return abort(400, "Failed")

    @app.post("/myjd_retry/<linkids>&<uuids>&<b64_links>")
    @auth_basic(is_authenticated_user)
    def myjd_retry(linkids, uuids, b64_links):
        global device
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
            return "Success"
        else:
            return abort(400, "Failed")

    @app.post("/myjd_update/")
    @auth_basic(is_authenticated_user)
    def myjd_update():
        global device
        device = update_jdownloader(configfile, device)
        if device:
            return "Success"
        else:
            return abort(400, "Failed")

    @app.post("/myjd_start/")
    @auth_basic(is_authenticated_user)
    def myjd_start():
        global device
        device = jdownloader_start(configfile, device)
        if device:
            return "Success"
        else:
            return abort(400, "Failed")

    @app.post("/myjd_pause/<bl>")
    @auth_basic(is_authenticated_user)
    def myjd_pause(bl):
        global device
        bl = json.loads(bl)
        device = jdownloader_pause(configfile, device, bl)
        if device:
            return "Success"
        else:
            return abort(400, "Failed")

    @app.post("/myjd_stop/")
    @auth_basic(is_authenticated_user)
    def myjd_stop():
        global device
        device = jdownloader_stop(configfile, device)
        if device:
            return "Success"
        else:
            return abort(400, "Failed")

    Server(app, listen='0.0.0.0', port=port).serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jd-user", help="Set your My JDownloader username")
    parser.add_argument("--jd-pass", help="Set your My JDownloader password")
    parser.add_argument("--jd-device", help="Set your My JDownloader device name")
    parser.add_argument("--port", help="Optional: Set desired Port to serve the API")
    parser.add_argument("--username", help="Optional: Set desired username for the API")
    parser.add_argument("--password", help="Optional: Set desired username for the API")
    parser.add_argument("--docker", action='store_true',
                        help="Internal: Locks config path and API port to docker defaults")
    arguments = parser.parse_args()

    if arguments.docker:
        configfile = '/config/MyJD.ini'
    else:
        configfile = config() + "/MyJD.ini"
    port = 8080
    if not os.path.exists(configfile):
        if arguments.docker or (arguments.jd_user and arguments.jd_pass):
            if arguments.jd_user and arguments.jd_pass:
                Config('MyJD', configfile).save("myjd_user", arguments.jd_user)
                Config('MyJD', configfile).save("myjd_pass", arguments.jd_pass)
                if arguments.jd_device:
                    Config('MyJD', configfile).save("myjd_device", arguments.jd_device)
                else:
                    device_name = get_if_one_device(arguments.jd_user, arguments.jd_pass)
                    if device_name:
                        print(u"Device name " + device_name + " found automatically.")
                        Config('MyJD', configfile).save("myjd_device", device_name)
                    else:
                        if arguments.docker:
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
        if arguments.jd_user:
            Config('MyJD', configfile).save("myjd_user", arguments.jd_user)
        if arguments.jd_pass:
            Config('MyJD', configfile).save("myjd_pass", arguments.jd_pass)
        if arguments.jd_device:
            Config('MyJD', configfile).save("myjd_device", arguments.jd_device)
        if arguments.port and not arguments.docker:
            Config('MyJD', configfile).save("port", arguments.port)
        settings = Config('MyJD', configfile)
        user = settings.get('myjd_user')
        password = settings.get('myjd_pass')
        if not arguments.docker:
            port = int(settings.get('port'))
            if not port:
                port = 8080
        if not user and not password and not arguments.docker:
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

    if arguments.username and arguments.password:
        Config('Auth', configfile).save("auth_user", arguments.username)
        Config('Auth', configfile).save("auth_hash", arguments.password)

    if _device:
        if not arguments.docker:
            print(u'MyJD-API (v.' + get_version() + ') is available at http://' + check_ip() + ':' + str(
                port) + u'/ connected with: ' + _device.name)
        else:
            print(u'MyJD-API (v.' + get_version() + ') is available and connected with: ' + _device.name)
        app_container(port, configfile, _device)
    else:
        print(u'Could not connect to My JDownloader! Exiting...')
        time.sleep(10)
        sys.exit(1)

if __name__ == "__main__":
    main()
