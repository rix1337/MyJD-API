# -*- coding: utf-8 -*-
# MyJD-API
# Project by https://github.com/rix1337

import multiprocessing

from myjd_api import run

if __name__ == '__main__':
    multiprocessing.freeze_support()
    run.main()
