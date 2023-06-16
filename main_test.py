# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

import json
import time
import copy
import sys
import os
import logging
import numpy as np
from os.path import isfile, join
from bs4 import BeautifulSoup
import pandas as pd
from multiprocessing import Pool
from itertools import repeat
from tqdm import tqdm
from datetime import datetime, timedelta

import hattrick_manager.scrappers as rap
import hattrick_manager.navigators as nav
import hattrick_manager.computers as comp
import hattrick_manager.readers as read
import hattrick_manager.checkers as che

transfer_dict_init = {
    "Age": {"Years": {"Min": 17,
                      "Max": 17,
                      },
            "Days": {"Min": 0,
                     "Max": 1,
                     },
            },
    "Skills": {"Skill_1": {"Name": "Winger",
                           "Min": 6,
                           "Max": 8,
                           },
               "Skill_2": {"Name": None,
                           "Min": 17,
                           "Max": 17,
                           },
               "Skill_3": {"Name": None,
                           "Min": 17,
                           "Max": 17,
                           },
               "Skill_4": {"Name": None,
                           "Min": 17,
                           "Max": 17,
                           },
               },
}

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

n_procs = 40
timeout = 2
skill = 'playmaking'
df_skill_search_cases = read.get_search_pattern(skill, transfer_tracker=False)

# 0a) We start be defining or retrieving the transfer tracker for the given skill
# This csv file is a bit different than the one used for the search pattern determination
# It has more columns and tracks also the pages that were searched for each transfer query
csv_track = skill + "_transfer_tracker.csv"
csv_db = skill + "_transfer_data.csv"
out_dir = os.path.join(os.path.dirname(__file__), 'hattrick_manager', 'output', 'transfer_data')
log_dir = os.path.join(os.path.dirname(__file__), 'hattrick_manager', 'log')
log_name = "open_transfer_log"

if not os.path.isfile(csv_track):
    df_transfer_tracker = read.get_search_pattern(skill, transfer_tracker=True)
else:
    df_transfer_tracker = pd.read_csv(csv_track, index_col=False)

df_split = np.array_split(df_transfer_tracker, n_procs)
split_index = np.arange(0, n_procs, 1)

split_index = 20
df_transfer_tracker = df_split[split_index]
df_transfer_tracker.reset_index(inplace=True, drop=True)

# Now we will  configure the logger
log_file_path = os.path.join(log_dir, f"{log_name}_{split_index}.log")
logging.basicConfig(filename=log_file_path, format='%(asctime)s %(message)s', filemode='w')
# We create the logger object
logger = logging.getLogger()
# Now we are going to set the threshold of logger to DEBUG
logger.setLevel(logging.CRITICAL)

# Beginning of function
skill_cap = skill.capitalize()
csv_name = skill + "_transfer_tracker_" + str(split_index) + ".csv"
csv_db = skill + "_transfer_data_" + str(split_index) + ".csv"
df_open_transfer_data = pd.DataFrame()  # the DataFrame that will group all the transfer data results for the given skill
transfer_page_id = "ctl00_ctl00_CPContent_CPMain_ucPager_repPages_ctl0"
timeout = 3
break_it = False

while not df_transfer_tracker["researched"].all(axis=0):
    # 1) Get the transfer dictionary for the current transfer query and launch the query
    che.check_wifi_connection()
    driver = nav.launch_web_browser()
    try:
        time_dict_ref = read.get_hattrick_date(driver, time_ref_dict=None, transfer_deadline=None)
    except TimeoutException:
        print("\nProcess {} restarting".format(str(split_index)))
        logger.critical("TimeoutException getting hattrick date. Process {} restarting".format(str(split_index)))
        driver.quit()
    except nav.NoInternetException:
        sys.exit(0, "Reconnect to Wifi before launching script again.")

    for i_row, row in df_transfer_tracker.iterrows():
        if break_it:
            break_it = False
            break
        current_query_data_collected = row["researched"]
        if not current_query_data_collected:
            transfer_dict = copy.deepcopy(transfer_dict_init)  # intialize search dictionary
            transfer_dict["Age"]["Years"]["Min"] = row["min_year"]
            transfer_dict["Age"]["Years"]["Max"] = row["max_year"]
            transfer_dict["Age"]["Days"]["Min"] = row["min_days"]
            transfer_dict["Age"]["Days"]["Max"] = row["max_days"]
            transfer_dict["Skills"]["Skill_1"]["Name"] = skill_cap
            transfer_dict["Skills"]["Skill_1"]["Min"] = row["section_min"]
            transfer_dict["Skills"]["Skill_1"]["Max"] = row["section_max"]
            try:
                n_pages, n_results = rap.launch_transfer_search(driver, transfer_dict)
            except TimeoutException:
                print("\nTimeoutException launching transfer search. Process {} restarting".format(str(split_index)))
                logger.critical(
                    "TimeoutException launching transfer search. Process {} restarting".format(str(split_index))
                )
                driver.quit()
                break

            except nav.NoInternetException:
                sys.exit(0, "Reconnect to Wifi before launching script again.")

            # 2) Write the number of results found in tracking csv
            df_transfer_tracker.at[i_row, "n_results"] = n_results

            # 3) Establish the next page (1, 2, 3 or 4) that needs to be scrapped
            # A function that looks at columns page1_collected, page2_collected...
            # in the transfer tracker needs to be created to get this page.
            next_page_to_scrap = read.get_next_page_to_scrap(row)  # 3 for example

            while not current_query_data_collected:
                che.check_wifi_connection()

                # 4) Go to that page using the htlm id key
                try:
                    if next_page_to_scrap > 1:
                        xtransfer_page_id = transfer_page_id + str(next_page_to_scrap - 1) + \
                                            "_p" + str(next_page_to_scrap - 1)
                        nav.wait("id", xtransfer_page_id, timeout, driver)
                        driver.find_element_by_id(xtransfer_page_id).click()
                except TimeoutException:
                    print("\nProcess {} restarting".format(str(split_index)))
                    logger.critical(
                        "TimeoutException finding transfer page. Process {} restarting".format(str(split_index))
                    )
                    break_it = True
                    driver.quit()
                    break
                except nav.NoInternetException:
                    sys.exit(0, "Reconnect to Wifi before launching script again.")

                # 5) Collect page transfer data
                try:
                    che.check_wifi_connection()
                    df_page_transfer = read.collect_1p_transfer_search_data(driver)
                except TimeoutException:
                    print("\nProcess {} restarting".format(str(split_index)))
                    logger.critical(
                        "TimeoutException collecting page data transfer. Process {} restarting".format(str(split_index))
                    )
                    break_it = True
                    driver.quit()
                    break
                except nav.NoInternetException:
                    sys.exit(0, "Reconnect to Wifi before launching script again.")

                # 6) Add transfer ID, Hattrick Dates
                if not df_page_transfer.empty:
                    df_page_transfer["Unique_Transfer_Key"] = ""
                    df_page_transfer["Searched_Skill_Name"] = ""
                    df_page_transfer["Searched_Age_Range"] = ""
                    df_page_transfer["Searched_Skill_Range"] = ""
                    df_page_transfer["Number_Search_Results"] = 0

                    for i, row2 in df_page_transfer.iterrows():
                        run_dict = row2.to_dict()
                        keys_to_keep = ["Nationality", "Transfer_ID", "Speciality", "Transfer_Time"]
                        run_dict2 = {k: v for k, v in run_dict.items() if k not in keys_to_keep}
                        df_page_transfer.at[i, "Unique_Transfer_Key"] = str(
                            comp.generate_transfer_key(run_dict2))
                        df_page_transfer.at[i, "Search_Date"] = time_dict_ref["launch_time"]["date"]
                        time_dict = read.get_hattrick_date(driver, time_ref_dict=time_dict_ref,
                                                          transfer_deadline=df_page_transfer.at[
                                                              i, "Transfer_Date"])
                        df_page_transfer.at[i, "Transfer_Date_Day"] = time_dict["transfer_time"]["day_name"]
                        df_page_transfer.at[i, "Transfer_Date_Week"] = time_dict["transfer_time"][
                            "week"]  # TODO: Fix Hattrick Week
                        df_page_transfer.at[i, "Transfer_Date_Season"] = time_dict["transfer_time"]["season"]

                        # 7) Add this DF to the df_open_transfer_data DF. Keep unique transfer player ID
                        df_page_transfer.at[i, "Searched_Skill_Name"] = skill
                        df_page_transfer.at[i, "Searched_Age_Range"] = \
                            str(transfer_dict["Age"]["Years"]["Min"]) + "." + \
                            str(transfer_dict["Age"]["Days"]["Min"]).zfill(3) + "_" + \
                            str(transfer_dict["Age"]["Years"]["Max"]) + "." + \
                            str(transfer_dict["Age"]["Days"]["Max"]).zfill(3)
                        df_page_transfer.at[i, "Searched_Skill_Range"] = \
                            str(transfer_dict["Skills"]["Skill_1"]["Min"]) + "_" + \
                            str(transfer_dict["Skills"]["Skill_1"]["Max"])
                        df_page_transfer.at[i, "Number_Search_Results"] = n_results

                # 8) Add this DF to the df_open_transfer_data DF. Keep unique transfer player ID
                if not df_page_transfer.empty:
                    df_open_transfer_data = pd.concat([df_open_transfer_data, df_page_transfer], sort=False,
                                                      ignore_index=True)
                df_open_transfer_data.drop_duplicates(subset="Unique_Transfer_Key", inplace=True)

                # 9) Write the df_open_transfer_data to update the csv
                df_open_transfer_data.to_csv(os.path.join(out_dir, csv_db), index=False)

                # 10) Update the df_transfer_tracker to say that the page has been searched
                df_transfer_tracker.at[i_row, "searched_p" + str(next_page_to_scrap)] = True

                # 11) Establish if all pages have been searched for this transfer query
                current_query_data_collected = che.check_search_status(df_transfer_tracker, i_row, n_pages)
                if current_query_data_collected:
                    df_transfer_tracker.at[i_row, "researched"] = True
                df_transfer_tracker.to_csv(os.path.join(out_dir, csv_name), index=False)

                # 12) Increment of the next page to search
                next_page_to_scrap += 1

            # Print to log
            logger.critical(
                f"Open data collection. Skill: {skill} / Index: {split_index} out of {n_procs} / Transfer Search no. "
                f"{str(i_row + 1).zfill(3)} out of {str(df_transfer_tracker.shape[0]).zfill(3)} --> COMPLETE"
            )
