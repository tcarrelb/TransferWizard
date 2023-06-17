# -*- coding: utf-8 -*-
import hattrick_manager as hatman
import hattrick_manager.readers as read
import hattrick_manager.visualizers as visu
import hattrick_manager.computers_old as comp
import hattrick_manager.scrappers as rap
import numpy as np
import pandas as pd
from multiprocessing import Pool
from itertools import repeat

import os
import time
import json

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
    df_open_transfer_data = rap.scrap_transfer_market(launch_info, "playmaking", n_procs=procs)
    # df_closed_transfer_data = rap.enrich_transfer_database(launch_info, "playmaking", n_procs=procs)
    end = time.perf_counter()
    print(f"\nFinished in {round(end-start, 2)} second(s)")


# skill = 'playmaking'
# df_skill_search_cases = read.get_search_pattern(skill, transfer_tracker=False)
#
# # 0a) We start be defining or retrieving the transfer tracker for the given skill
# # This csv file is a bit different than the one used for the search pattern determination
# # It has more columns and tracks also the pages that were searched for each transfer query
# csv_track = skill + "_transfer_tracker.csv"
# csv_db = skill + "_transfer_data.csv"
#
# if not os.path.isfile(csv_track):
#     df_transfer_tracker = read.get_search_pattern(skill, transfer_tracker=True)
# else:
#     df_transfer_tracker = pd.read_csv(csv_track, index_col=False)
#
# # 0b) The transfer tracker is split in X blocks depending on the number of processors required
# # Note that the script does not use multi-threading, it uses multi-processing
# # https://blog.alexoglou.com/multithreading-or-multiprocessing-selenium-with-python/
# # https://stackoverflow.com/questions/53475578/python-selenium-multiprocessing
# # https://medium.com/geekculture/introduction-to-selenium-and-python-multi-threading-module-aa5b1c4386cb
# df_split = np.array_split(df_transfer_tracker, n_procs)
# split_index = np.arange(0, n_procs, 1)
#
# # 0c) Launch the pool of processes, with headless drivers
# # The below will probably be part of another function as all of this has to be performed per process
# # Everything now is per processor.
# scrap_transfer_inputs = zip(df_split, split_index, repeat(launch_info), repeat(skill))
# pool = Pool(n_procs)
# df_open_transfer_data = pd.concat(pool.map(scrap_transfer_market_per_process, scrap_transfer_inputs))
# pool.close()
# pool.join()
#
# # Clean the folder, combine results
# df_open_transfer_data.drop_duplicates(subset="Unique_Transfer_Key", inplace=True)
# df_open_transfer_data.reset_index(drop=True, inplace=True)
# df_open_transfer_data["Closed"] = False
# df_open_transfer_data.to_csv(csv_db, index=False)
#
# df_transfer_tracker_final = pd.DataFrame()
# for i in split_index:
#     csv_track_i = csv_track.split(".")[0] + "_" + str(i) + ".csv"
#     csv_db_i = csv_db.split(".")[0] + "_" + str(i) + ".csv"
#     df_csv_track_i = pd.read_csv(csv_track_i, index_col=False)
#     df_transfer_tracker_final = pd.concat([df_transfer_tracker_final, df_csv_track_i],
#                                           sort=False, ignore_index=True)
#     os.remove(csv_db_i)
#     os.remove(csv_track_i)
#
# df_transfer_tracker_final.reset_index(drop=True, inplace=True)
# df_transfer_tracker_final.to_csv(csv_track, index=False)
