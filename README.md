#  MyJD-API

[![PyPI version](https://badge.fury.io/py/myjd-api.svg)](https://badge.fury.io/py/myjd-api)
[![Github Sponsorship](https://img.shields.io/badge/support-me-red.svg)](https://github.com/users/rix1337/sponsorship)

This is a standalone version of [FeedCrawler](https://github.com/rix1337/FeedCrawler)'s MyJDownloader API for use with projects like [Organizr](https://github.com/causefx/Organizr).

The official docker image is available at [Docker Hub](https://hub.docker.com/r/rix1337/docker-myjd-api).

# Setup

`pip install myjd-api`

# Run

`myjd_api`

## Parameters
* `--jd-user` Set your My JDownloader username 
* `--jd-pass` Set your My JDownloader password 
* `--jd-device` Set your My JDownloader device name 
* `--port` _Optional:_ Set desired Port to serve the API 
* `--username` _Optional:_ Set desired username for the API 
* `--password` _Optional:_ Set desired username for the API 

# Docker
```
docker run -d \
  --name="MyJD-API" \
  -p port:8080 \
  -v /path/to/config/:/config:rw \
  -e USER=USERNAME \ 
  -e PASS=PASSWORD \
  -e DEVICE=DEVICENAME \
  rix1337/docker-myjd-api
  ```
  
## Optional Parameters
 - `-e USER` (after first run, if unchanged)
 - `-e PASS` (after first run, if unchanged)
 - `-e DEVICE` (always, if only one device is present at MyJD-Account, otherwise after first run, if unchanged)


## Credits

* [mmarquezs](https://github.com/mmarquezs/)
