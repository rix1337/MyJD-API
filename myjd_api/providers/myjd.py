# -*- coding: utf-8 -*-
# MyJD
# Project by https://github.com/rix1337

import myjd_api.providers.myjdapi
from myjd_api.providers.common import is_device
from myjd_api.providers.common import readable_size
from myjd_api.providers.common import readable_time
from myjd_api.providers.config import Config


def get_device(configfile):
    conf = Config('MyJD', configfile)
    myjd_user = str(conf.get('myjd_user'))
    myjd_pass = str(conf.get('myjd_pass'))
    myjd_device = str(conf.get('myjd_device'))

    jd = myjd_api.providers.myjdapi.Myjdapi()
    jd.set_app_key('MyJD')

    if myjd_user and myjd_pass and myjd_device:
        try:
            try:
                jd.connect(myjd_user, myjd_pass)
                jd.update_devices()
                device = jd.get_device(myjd_device)
            except myjd_api.providers.myjdapi.RequestTimeoutException:
                device = jd.get_device(myjd_device)
        except myjd_api.providers.myjdapi.MYJDException as e:
            print(u"Error connection to MyJDownloader: " + str(e))
            return False
        if not device or not is_device(device):
            return False
        return device
    elif myjd_user and myjd_pass:
        myjd_device = get_if_one_device(myjd_user, myjd_pass)
        if myjd_device:
            Config('MyJD', configfile).save("myjd_device", myjd_device)
        try:
            jd.connect(myjd_user, myjd_pass)
            jd.update_devices()
            device = jd.get_device(myjd_device)
        except myjd_api.providers.myjdapi.MYJDException as e:
            print(u"Error connection to MyJDownloader: " + str(e))
            return False
        if not device or not is_device(device):
            return False
        return device
    else:
        return False


def check_device(myjd_user, myjd_pass, myjd_device):
    jd = myjd_api.providers.myjdapi.Myjdapi()
    jd.set_app_key('MyJD')
    try:
        jd.connect(myjd_user, myjd_pass)
        jd.update_devices()
        device = jd.get_device(myjd_device)
    except myjd_api.providers.myjdapi.MYJDException as e:
        print(u"Error connection to MyJDownloader: " + str(e))
        return False
    return device


def get_if_one_device(myjd_user, myjd_pass):
    jd = myjd_api.providers.myjdapi.Myjdapi()
    jd.set_app_key('MyJD')
    try:
        jd.connect(myjd_user, myjd_pass)
        jd.update_devices()
        devices = jd.list_devices()
        if len(devices) == 1:
            return devices[0].get('name')
        else:
            return False
    except myjd_api.providers.myjdapi.MYJDException as e:
        print(u"Error connection to MyJDownloader: " + str(e))
        return False


def get_packages_in_downloader(device):
    links = device.downloads.query_links()

    packages = device.downloads.query_packages([{
        "bytesLoaded": True,
        "bytesTotal": True,
        "comment": False,
        "enabled": True,
        "eta": True,
        "priority": False,
        "finished": True,
        "running": True,
        "speed": True,
        "status": True,
        "childCount": True,
        "hosts": True,
        "saveTo": True,
        "maxResults": -1,
        "startAt": 0,
    }])

    if links and packages and len(packages) > 0:
        packages_by_type = check_packages_types(links, packages)
        failed = packages_by_type[0]
        offline = packages_by_type[1]
        decrypted = packages_by_type[2]
        return [failed, offline, decrypted]
    else:
        return [False, False, False]


def get_packages_in_linkgrabber(device):
    links = device.linkgrabber.query_links()

    packages = device.linkgrabber.query_packages(params=[
        {
            "bytesLoaded": True,
            "bytesTotal": True,
            "comment": False,
            "enabled": True,
            "eta": True,
            "priority": False,
            "finished": True,
            "running": True,
            "speed": True,
            "status": True,
            "childCount": True,
            "hosts": True,
            "saveTo": True,
            "maxResults": -1,
            "startAt": 0,
        }])
    if links and packages and len(packages) > 0:
        packages_by_type = check_packages_types(links, packages)
        failed = packages_by_type[0]
        offline = packages_by_type[1]
        decrypted = packages_by_type[2]
        return [failed, offline, decrypted]
    else:
        return [False, False, False]


def check_packages_types(links, packages):
    decrypted = []
    failed = []
    offline = []
    for package in packages:
        name = package.get('name')
        total_links = package.get('childCount')
        enabled = package.get('enabled')
        size = package.get('bytesTotal')
        done = package.get('bytesLoaded')
        if done and size:
            completed = 100 * done // size
        else:
            completed = 0
        size = readable_size(size)
        done = readable_size(done)
        if not done:
            done = "0"
        speed = package.get('speed')
        if speed:
            speed = readable_size(speed) + "/s"
        hosts = package.get('hosts')
        save_to = package.get('saveTo')
        eta = package.get('eta')
        if eta:
            eta = readable_time(eta)
        uuid = package.get('uuid')
        url = False
        urls = []
        filenames = []
        linkids = []
        package_failed = False
        package_offline = False
        if links:
            for link in links:
                if uuid == link.get('packageUUID'):
                    if link.get('availability') == 'OFFLINE' or link.get('status') == 'Datei nicht gefunden':
                        package_offline = True
                    if 'Falscher Captcha Code!' in link.get('name') or 'Wrong Captcha!' in link.get('name') or (
                            link.get('comment') and 'BLOCK_HOSTER' in link.get('comment')):
                        package_failed = True
                    url = link.get('url')
                    if url:
                        url = str(url)
                        if url not in urls:
                            urls.append(url)
                        filename = str(link.get('name'))
                        if filename not in filenames:
                            filenames.append(filename)
                    linkids.append(link.get('uuid'))
        for h in hosts:
            if h == 'linkcrawlerretry':
                package_failed = True
        status = package.get('status')
        if status:
            if 'Ein Fehler ist aufgetreten!' in status or 'An error occurred!' in status:
                package_failed = True
        if package_failed:
            package_offline = False
        if package_failed and not package_offline and len(urls) == 1:
            url = urls[0]
        elif urls:
            urls = "\n".join(urls)
        if package_failed and not package_offline:
            failed.append({"name": name,
                           "path": save_to,
                           "urls": urls,
                           "url": url,
                           "linkids": linkids,
                           "uuid": uuid})
        elif package_offline:
            offline.append({"name": name,
                            "path": save_to,
                            "urls": urls,
                            "linkids": linkids,
                            "uuid": uuid})
        else:
            decrypted.append({"name": name,
                              "links": total_links,
                              "enabled": enabled,
                              "hosts": hosts,
                              "path": save_to,
                              "size": size,
                              "done": done,
                              "percentage": completed,
                              "speed": speed,
                              "eta": eta,
                              "urls": urls,
                              "filenames": filenames,
                              "linkids": linkids,
                              "uuid": uuid})
    if not failed:
        failed = False
    if not offline:
        offline = False
    if not decrypted:
        decrypted = False
    return [failed, offline, decrypted]


def get_state(configfile, device):
    try:
        if not device or not is_device(device):
            device = get_device(configfile)
        if device:
            try:
                downloader_state = device.downloadcontroller.get_current_state()
                grabber_collecting = device.linkgrabber.is_collecting()
            except myjd_api.providers.myjdapi.TokenExpiredException:
                device = get_device(configfile)
                if not device or not is_device(device):
                    return False
                downloader_state = device.downloadcontroller.get_current_state()
                grabber_collecting = device.linkgrabber.is_collecting()
            return [device, downloader_state, grabber_collecting]
        else:
            return False
    except myjd_api.providers.myjdapi.MYJDException as e:
        print(u"Error connection to MyJDownloader: " + str(e))
        return False


def get_info(configfile, device):
    try:
        if not device or not is_device(device):
            device = get_device(configfile)
        if device:
            try:
                downloader_state = device.downloadcontroller.get_current_state()
                grabber_collecting = device.linkgrabber.is_collecting()
                device.update.run_update_check()
                update_ready = device.update.is_update_available()

                packages_in_downloader = get_packages_in_downloader(device)
                packages_in_downloader_failed = packages_in_downloader[0]
                packages_in_downloader_offline = packages_in_downloader[1]
                packages_in_downloader_decrypted = packages_in_downloader[2]

                packages_in_linkgrabber = get_packages_in_linkgrabber(device)
                packages_in_linkgrabber_failed = packages_in_linkgrabber[0]
                packages_in_linkgrabber_offline = packages_in_linkgrabber[1]
                packages_in_linkgrabber_decrypted = packages_in_linkgrabber[2]
            except myjd_api.providers.myjdapi.TokenExpiredException:
                device = get_device(configfile)
                if not device or not is_device(device):
                    return False
                downloader_state = device.downloadcontroller.get_current_state()
                grabber_collecting = device.linkgrabber.is_collecting()
                device.update.run_update_check()
                update_ready = device.update.is_update_available()

                packages_in_downloader = get_packages_in_downloader(device)
                packages_in_downloader_failed = packages_in_downloader[0]
                packages_in_downloader_offline = packages_in_downloader[1]
                packages_in_downloader_decrypted = packages_in_downloader[2]

                packages_in_linkgrabber = get_packages_in_linkgrabber(device)
                packages_in_linkgrabber_failed = packages_in_linkgrabber[0]
                packages_in_linkgrabber_offline = packages_in_linkgrabber[1]
                packages_in_linkgrabber_decrypted = packages_in_linkgrabber[2]

            if packages_in_downloader_failed and packages_in_linkgrabber_failed:
                packages_failed = packages_in_downloader_failed + packages_in_linkgrabber_failed
            elif packages_in_downloader_failed:
                packages_failed = packages_in_downloader_failed
            else:
                packages_failed = packages_in_linkgrabber_failed

            if packages_in_downloader_offline and packages_in_linkgrabber_offline:
                packages_offline = packages_in_downloader_offline + packages_in_linkgrabber_offline
            elif packages_in_downloader_offline:
                packages_offline = packages_in_downloader_offline
            else:
                packages_offline = packages_in_linkgrabber_offline

            return [device, downloader_state, grabber_collecting, update_ready,
                    [packages_in_downloader_decrypted, packages_in_linkgrabber_decrypted,
                     packages_offline,
                     packages_failed]]
        else:
            return False
    except myjd_api.providers.myjdapi.MYJDException as e:
        print(u"Error connection to MyJDownloader: " + str(e))
        return False


def move_to_downloads(configfile, device, linkids, uuid):
    try:
        if not device or not is_device(device):
            device = get_device(configfile)
        if device:
            try:
                device.linkgrabber.move_to_downloadlist(linkids, uuid)
            except myjd_api.providers.myjdapi.TokenExpiredException:
                device = get_device(configfile)
                if not device or not is_device(device):
                    return False
                device.linkgrabber.move_to_downloadlist(linkids, uuid)
            return device
        else:
            return False
    except myjd_api.providers.myjdapi.MYJDException as e:
        print(u"Error connection to MyJDownloader: " + str(e))
        return False


def remove_from_linkgrabber(configfile, device, linkids, uuid):
    try:
        if not device or not is_device(device):
            device = get_device(configfile)
        if device:
            try:
                device.linkgrabber.remove_links(linkids, uuid)
                device.downloads.remove_links(linkids, uuid)
            except myjd_api.providers.myjdapi.TokenExpiredException:
                device = get_device(configfile)
                if not device or not is_device(device):
                    return False
                device.linkgrabber.remove_links(linkids, uuid)
                device.downloads.remove_links(linkids, uuid)
            return device
        else:
            return False
    except myjd_api.providers.myjdapi.MYJDException as e:
        print(u"Error connection to MyJDownloader: " + str(e))
        return False


def download(configfile, device, title, subdir, links, password, full_path=None):
    try:
        if not device or not is_device(device):
            device = get_device(configfile)

        links = str(links)
        crawljobs = Config('Crawljobs', configfile)
        autostart = crawljobs.get("autostart")
        usesubdir = crawljobs.get("subdir")
        priority = "DEFAULT"

        if full_path:
            path = full_path
        else:
            if usesubdir:
                path = subdir + "/<jd:packagename>"
            else:
                path = "<jd:packagename>"
        if "Remux" in path:
            priority = "LOWER"

        try:
            device.linkgrabber.add_links(params=[
                {
                    "autostart": autostart,
                    "links": links,
                    "packageName": title,
                    "extractPassword": password,
                    "priority": priority,
                    "downloadPassword": password,
                    "destinationFolder": path,
                    "overwritePackagizerRules": False
                }])
        except myjd_api.providers.myjdapi.TokenExpiredException:
            device = get_device(configfile)
            if not device or not is_device(device):
                return False
            device.linkgrabber.add_links(params=[
                {
                    "autostart": autostart,
                    "links": links,
                    "packageName": title,
                    "extractPassword": password,
                    "priority": priority,
                    "downloadPassword": password,
                    "destinationFolder": path,
                    "overwritePackagizerRules": False
                }])
        return device
    except myjd_api.providers.myjdapi.MYJDException as e:
        print(u"Error connection to MyJDownloader: " + str(e))
        return False


def retry_decrypt(configfile, device, linkids, uuid, links):
    try:
        if not device or not is_device(device):
            device = get_device(configfile)
        if device:
            try:
                package = device.linkgrabber.query_packages(params=[
                    {
                        "availableOfflineCount": True,
                        "availableOnlineCount": True,
                        "availableTempUnknownCount": True,
                        "availableUnknownCount": True,
                        "bytesTotal": True,
                        "childCount": True,
                        "comment": True,
                        "enabled": True,
                        "hosts": True,
                        "maxResults": -1,
                        "packageUUIDs": uuid,
                        "priority": True,
                        "saveTo": True,
                        "startAt": 0,
                        "status": True
                    }])
            except myjd_api.providers.myjdapi.TokenExpiredException:
                device = get_device(configfile)
                if not device or not is_device(device):
                    return False
                package = device.linkgrabber.query_packages(params=[
                    {
                        "availableOfflineCount": True,
                        "availableOnlineCount": True,
                        "availableTempUnknownCount": True,
                        "availableUnknownCount": True,
                        "bytesTotal": True,
                        "childCount": True,
                        "comment": True,
                        "enabled": True,
                        "hosts": True,
                        "maxResults": -1,
                        "packageUUIDs": uuid,
                        "priority": True,
                        "saveTo": True,
                        "startAt": 0,
                        "status": True
                    }])
            if not package:
                try:
                    package = device.downloads.query_packages(params=[
                        {
                            "bytesLoaded": True,
                            "bytesTotal": True,
                            "comment": True,
                            "enabled": True,
                            "eta": True,
                            "priority": True,
                            "finished": True,
                            "running": True,
                            "speed": True,
                            "status": True,
                            "childCount": True,
                            "hosts": True,
                            "saveTo": True,
                            "maxResults": -1,
                            "packageUUIDs": uuid,
                            "startAt": 0,
                        }])
                except myjd_api.providers.myjdapi.TokenExpiredException:
                    device = get_device(configfile)
                    if not device or not is_device(device):
                        return False
                    package = device.downloads.query_packages(params=[
                        {
                            "bytesLoaded": True,
                            "bytesTotal": True,
                            "comment": True,
                            "enabled": True,
                            "eta": True,
                            "priority": True,
                            "finished": True,
                            "running": True,
                            "speed": True,
                            "status": True,
                            "childCount": True,
                            "hosts": True,
                            "saveTo": True,
                            "maxResults": -1,
                            "packageUUIDs": uuid,
                            "startAt": 0,
                        }])
            if package:
                remove_from_linkgrabber(configfile, device, linkids, uuid)
                title = package[0].get('name')
                full_path = package[0].get('saveTo')
                download(configfile, device, title, None, links, None, full_path)
                return device
            else:
                return False
        else:
            return False
    except myjd_api.providers.myjdapi.MYJDException as e:
        print(u"Error connection to MyJDownloader: " + str(e))
        return False


def update_jdownloader(configfile, device):
    try:
        if not device or not is_device(device):
            device = get_device(configfile)
        if device:
            try:
                device.update.restart_and_update()
            except myjd_api.providers.myjdapi.TokenExpiredException:
                device = get_device(configfile)
                if not device or not is_device(device):
                    return False
                device.update.restart_and_update()
            return device
        else:
            return False
    except myjd_api.providers.myjdapi.MYJDException as e:
        print(u"Error connection to MyJDownloader: " + str(e))
        return False


def jdownloader_start(configfile, device):
    try:
        if not device or not is_device(device):
            device = get_device(configfile)
        if device:
            try:
                device.downloadcontroller.start_downloads()
            except myjd_api.providers.myjdapi.TokenExpiredException:
                device = get_device(configfile)
                if not device or not is_device(device):
                    return False
                device.downloadcontroller.start_downloads()
            return device
        else:
            return False
    except myjd_api.providers.myjdapi.MYJDException as e:
        print(u"Error connection to MyJDownloader: " + str(e))
        return False


def jdownloader_pause(configfile, device, bl):
    try:
        if not device or not is_device(device):
            device = get_device(configfile)
        if device:
            try:
                device.downloadcontroller.pause_downloads(bl)
            except myjd_api.providers.myjdapi.TokenExpiredException:
                device = get_device(configfile)
                if not device or not is_device(device):
                    return False
                device.downloadcontroller.pause_downloads(bl)
            return device
        else:
            return False
    except myjd_api.providers.myjdapi.MYJDException as e:
        print(u"Error connection to MyJDownloader: " + str(e))
        return False


def jdownloader_stop(configfile, device):
    try:
        if not device or not is_device(device):
            device = get_device(configfile)
        if device:
            try:
                device.downloadcontroller.stop_downloads()
            except myjd_api.providers.myjdapi.TokenExpiredException:
                device = get_device(configfile)
                if not device or not is_device(device):
                    return False
                device.downloadcontroller.stop_downloads()
            return device
        else:
            return False
    except myjd_api.providers.myjdapi.MYJDException as e:
        print(u"Error connection to MyJDownloader: " + str(e))
        return False


def myjd_download(configfile, device, title, subdir, links, password):
    if device:
        device = download(configfile, device, title, subdir, links, password)
        if device:
            return device
    return False
