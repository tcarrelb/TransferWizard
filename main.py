# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from multiprocessing import Pool
from itertools import repeat
from selenium.common.exceptions import TimeoutException

import json
import time
import copy
import sys
import os
import pandas as pd

import hattrick_manager as hatman
import hattrick_manager.reference_data.global_vars as glova
import hattrick_manager.scrappers as rap
import hattrick_manager.navigators as nav
import hattrick_manager.computers as comp
import hattrick_manager.readers as read
import hattrick_manager.checkers as che

'''
How to update the Chrome Driver:
1) Find the version of the Google Chrome Browser (in the browser settings)
2) Download the appropriate ChromeDriver (win32)
https://sites.google.com/a/chromium.org/chromedriver/downloads
https://sites.google.com/chromium.org/driver/
3) Unzip the folder, a chromedriver executable will be created
4) Copy this chromedriver where the PATH indicates: C:\Program Files (x86)
'''

# df = read.collect_team_data()
# df_top_scorers = visu.display_top_scorers()

procs = 4
ref_data_dir = os.path.join(hatman.__path__[0], 'reference_data')
f = open(os.path.join(ref_data_dir, 'login_info.json'))
launch_info = json.load(f)
timeout = 2

if __name__ == '__main__':
    print(f"Launching transfer scrapping with {str(procs)} processor(s)...\n")
    start = time.perf_counter()
    df_open_transfer_data = rap.scrap_transfer_market(launch_info, "keeper", n_procs=procs)
    # df_closed_transfer_data = rap.enrich_transfer_database(launch_info, "playmaking", n_procs=procs)
    end = time.perf_counter()
    print(f"\nFinished in {round(end-start, 2)} second(s)")

