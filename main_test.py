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
from copy import deepcopy
import logging
import numpy as np
from os.path import isfile, join
from bs4 import BeautifulSoup
import pandas as pd
from multiprocessing import Pool
from itertools import repeat
from tqdm import tqdm
from datetime import datetime, timedelta

import hattrick_manager as hatman
import hattrick_manager.scrappers as rap
import hattrick_manager.navigators as nav
import hattrick_manager.computers as comp
import hattrick_manager.readers as read
import hattrick_manager.checkers as che
from hattrick_manager.reference_data.global_vars import html_keys, dict_transfer_closure_init, login_info


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


### START OF TEST FOR CLOSING TRANSFER SEARCH ###
def get_transfer_closure(player_id, transfer_deadline, driver):
    # Initialization of parameters:
    timeout = 2
    dict_transfer_closure = deepcopy(dict_transfer_closure_init)
    closing_latest_transfer = False
    incomplete_buyer_name = False
    transfer_closed = False
    player_exists = True
    empty_transfer_history = False
    only_older_transfers = False
    num_more_recent_transfers = 0

    """Navigating through the search menu to find transferred player"""
    # Click on the hattrick search icon:
    nav.wait("xpath", html_keys["xpath"]["search_icon"], timeout, driver)
    driver.find_element_by_xpath(html_keys["xpath"]["search_icon"]).click()
    # Select the "player" category:
    nav.wait("id", html_keys["id"]["search_drop_menu"], timeout, driver)
    drop = Select(driver.find_element_by_id(html_keys["id"]["search_drop_menu"]))
    drop.select_by_value("5")  # drop.select_by_value("Players")
    # Enter the player ID:
    nav.wait("id", html_keys["id"]["player_id_box"], timeout, driver)
    id_input = driver.find_element_by_id(html_keys["id"]["player_id_box"])
    id_input.send_keys(str(player_id))
    # Click on the "Search" button:
    nav.wait("xpath", html_keys["xpath"]["search_player_button"], timeout, driver)
    driver.find_element_by_xpath(html_keys["xpath"]["search_player_button"]).click()
    # Click on the search result link:
    nav.wait("id", html_keys["id"]["search_res_table"], timeout, driver)
    try:
        driver.find_element_by_id(html_keys["id"]["player_link"]).click()
    except NoSuchElementException:
        player_exists = False
        print("Player with ID {} retired".format(str(player_id)))

    # At this point, we know if the transferred player still exist or is retired:
    if player_exists:
        dict_transfer_closure["Player_ID"] = player_id
        time.sleep(0.1)
        """Having to deal with a dynamic table on the player page (https://www.tutorialspoint.com/
        how-to-click-on-a-button-with-javascript-executor-in-selenium-with-python) we locate the transfer history tab
        and we activate it to retrieve the right table."""
        transfer_history_tab = driver.find_element_by_xpath(html_keys["xpath"]["transfer_history_tab"])
        driver.execute_script("arguments[0].click();", transfer_history_tab)

        # Get player personality:
        dict_transfer_closure["Gentleness"] = \
            driver.find_element_by_xpath(html_keys["xpath"]["player_gentleness"]).text
        dict_transfer_closure["Aggressiveness"] = \
            driver.find_element_by_xpath(html_keys["xpath"]["player_aggressiveness"]).text
        dict_transfer_closure["Honesty"] = \
            driver.find_element_by_xpath(html_keys["xpath"]["player_honesty"]).text

        # Once this is done, we can parse the web page to retrieve player transfer data:
        html_doc = driver.page_source
        soup = BeautifulSoup(html_doc, "html.parser")  # the page is parsed
        # Check if the player has some transfer history
        transfer_history = soup.find("table", {"class": "htbox-table"})
        if transfer_history is None:
            empty_transfer_history = True

        # Get owner details:
        owner_table = soup.find('div', attrs={"class":"ownerAndStatusPlayerInfo"}).table.tbody
        owner_name = owner_table.find_all("tr")[0].find_all("td")[1].a.text
        owner_href = owner_table.find_all("tr")[0].find_all("td")[1].a.get("href")
        owner_id = int(owner_href.split("TeamID=")[-1])

        if not empty_transfer_history:  # there exists a transfer history for the player
            transfer_headers = transfer_history.thead.find_all("tr")[0].find_all("th")
            transfer_headers = [tag.text for tag in transfer_headers]
            transfer_rows = transfer_history.tbody.find_all("tr")  # all transfer data rows
            for j, row in enumerate(transfer_rows):  # iterating over the transfer history rows
                transfer_body = row.find_all("td")
                transfer_date = transfer_body[0].text.strip()
                if transfer_date == transfer_deadline:  # this is the transfer we need to close
                    dict_transfer_closure["Transfer_Status"] = "Completed"
                    if j == 0:
                        closing_latest_transfer = True
                    for i, col in enumerate(transfer_headers):  # iterating over the transfer history columns
                        cell_value = transfer_body[i]
                        if col == "Deadline":
                            dict_transfer_closure["Transfer_Date"] = cell_value.text.strip().replace("-", "/")
                        elif col == "Seller":
                            dict_transfer_closure["Seller_Name"] = cell_value.text.strip()
                            dict_transfer_closure["Seller_Href"] = cell_value.a.get("href")
                            dict_transfer_closure["Seller_ID"] = int(cell_value.a.get("href").split("TeamID=")[-1])
                        elif col == "Buyer":
                            if cell_value.text.strip().endswith("..."):
                                incomplete_buyer_name = True
                            if incomplete_buyer_name and closing_latest_transfer:
                                dict_transfer_closure["Buyer_Name"] = owner_name
                            else:
                                dict_transfer_closure["Buyer_Name"] = cell_value.text.strip()
                            dict_transfer_closure["Buyer_Href"] = cell_value.a.get("href")
                            dict_transfer_closure["Buyer_ID"] = int(cell_value.a.get("href").split("TeamID=")[-1])
                        elif col == "TSI":
                            dict_transfer_closure["TSI"] = int(cell_value.text.strip().replace("\xa0", ""))
                        elif col == "Age":
                            dict_transfer_closure["Age"] = int(cell_value.text.strip().split("(")[0])
                            dict_transfer_closure["Days"] = int(cell_value.text.strip().split("(")[1][:-1])
                        elif col == "Price":
                            dict_transfer_closure["Price"] = int(
                                cell_value.text.strip().replace("\xa0", "").split("€")[0]
                            )
                            transfer_closed = True
                        else:
                            pass
                elif datetime.strptime(transfer_date, "%d-%m-%Y") > datetime.strptime(transfer_deadline, "%d-%m-%Y"):
                    for i, col in enumerate(transfer_headers):  # iterating over the transfer history columns
                        cell_value = transfer_body[i]
                        if col == "Seller":
                            latest_seller_name = cell_value.text.strip()
                            latest_seller_href = cell_value.a.get("href")
                            latest_seller_id = int(cell_value.a.get("href").split("TeamID=")[-1])
                            break
                    num_more_recent_transfers += 1
                else:
                    pass

                if datetime.strptime(transfer_date, "%d-%m-%Y") < datetime.strptime(transfer_deadline, "%d-%m-%Y"):
                    """Since the transfer history is ordered chronologically, if the transfer date for the current row
                    is older than the given transfer deadline, no need to look at older transfers, the studied
                    transfer has been aborted."""
                    if j == 0:  # special case where there are only older transfers in the transfer history:
                        only_older_transfers = True
                    break

                if transfer_closed:  # the transfer has already been found, no need to search any further
                    break

            if not transfer_closed:  # this means that the transfer was not found in the transfer history
                dict_transfer_closure["Transfer_Status"] = "Aborted"

        else:  # there is no transfer history for the player
            dict_transfer_closure["Transfer_Status"] = "Aborted"

        if dict_transfer_closure["Transfer_Status"] == "Aborted":
            dict_transfer_closure["Transfer_Date"] = transfer_deadline.replace("-", "/")
            """In the case where there is no transfer history for the player, or that we only have transfer listed older
            than the one we are trying to close, we are sure that the seller of the aborted transfer is the current 
            owner of the player."""
            if empty_transfer_history or only_older_transfers:
                dict_transfer_closure["Seller_Name"] = owner_name
                dict_transfer_closure["Seller_Href"] = owner_href
                dict_transfer_closure["Seller_ID"] = owner_id
            """In the case where there are more recent transfers in the transfer history, then the seller of the aborted
            transfer can be known, it is the seller of the next most recent transfer to the one studied."""
            if num_more_recent_transfers >= 1:
                dict_transfer_closure["Seller_Name"] = latest_seller_name
                dict_transfer_closure["Seller_Href"] = latest_seller_href
                dict_transfer_closure["Seller_ID"] = latest_seller_id

    else:  # the player retired
        dict_transfer_closure["Player_ID"] = player_id
        dict_transfer_closure["Transfer_Status"] = "Retired"
        dict_transfer_closure["Transfer_Date"] = transfer_deadline.replace("-", "/")

    return pd.DataFrame([dict_transfer_closure])


procs = 4
launch_info = login_info
timeout = 2
split_index = 0
transfer_data_dir = os.path.join(hatman.__path__[0], 'output', 'transfer_data', 'playmaking_2023-06-15_20-18')
df_open_name = "playmaking_transfer_data.csv"
df_pre = pd.read_csv(os.path.join(transfer_data_dir, df_open_name), index_col=False, delimiter=";")
df_pre["Closed"] = False
csv_track_name = "track"
csv_track = "track"
csv_db_name = "db"
csv_db = "db"
split_index = 0


# df_pre, split_index, launch_info, csv_track_name, csv_db_name = closure_transfer_inputs
# csv_track = csv_track_name.split(".")[0] + "_" + str(split_index) + ".csv"
# csv_db = csv_db_name.split(".")[0] + "_" + str(split_index) + ".csv"
df_closed_transfer_data = pd.DataFrame()
break_it = False

while not df_pre["Closed"].all(axis=0):
    # 1) Get the transfer dictionary for the current transfer query and launch the query
    che.check_wifi_connection()
    driver = nav.launch_web_browser()
    try:
        read.get_hattrick_date(driver, time_ref_dict=None, transfer_deadline=None)
    except TimeoutException:
        print("\nProcess {} restarting".format(str(split_index)))
        driver.quit()
    except nav.NoInternetException:
        sys.exit(0, "Reconnect to Wifi before launching script again.")

    closed_transfer_indices = list()
    for i_row, row in df_pre.iterrows():
        if break_it:
            break_it = False
            break
        closed_transfer = row["Closed"]
        if not closed_transfer:
            player_id = row["Player_ID"]
            deadline = row["Transfer_Date"].replace("/", "-")
            dd_dt_p1 = datetime.strptime(deadline, "%d-%m-%Y") + timedelta(days=1)
            if datetime.now() > dd_dt_p1:  # the transfer has potentially already been closed
                closed_transfer_indices.append(i_row)
                che.check_wifi_connection()
                try:
                    df_row_closure = get_transfer_closure(player_id, deadline, driver)
                except TimeoutException:
                    print(f"\nProcess {str(split_index)} restarting")
                    driver.quit()
                    break
                except nav.NoInternetException:
                    sys.exit(0, "Reconnect to Wifi before launching script again.")
                df_closed_transfer_data = pd.concat([df_closed_transfer_data, df_row_closure],
                                                    sort=False, ignore_index=True)
            else:
                sys.exit(0, "Transfer has not been closed yet.")

        df_pre.at[i_row, "Closed"] = True
        #df_pre.to_csv(csv_track, index=False)
        print(f"Transfer for player ID {player_id} --> CLOSED")

df_closed_transfer_data = df_closed_transfer_data.fillna(value=np.nan)
df_db_addition = df_pre.merge(df_closed_transfer_data, on=["Player_ID", "Transfer_Date"], how='left')
if pd.Series(["TSI_x", "Age_x", "Days_x"]).isin(df_db_addition.columns).all():
    df_db_addition['Age_Years'] = np.max(df_db_addition[['Age_x', 'Age_y']], axis=1)
    df_db_addition['Age_Days'] = np.max(df_db_addition[['Days_x', 'Days_y']], axis=1)
    df_db_addition['TSI'] = np.where(
        ~df_db_addition['TSI_y'].isnull(), df_db_addition['TSI_y'], df_db_addition['TSI_x']
    )
    df_db_addition.drop(["Closed", "TSI_x", "TSI_y", "Age_x", "Age_y", "Days_x", "Days_y"], axis=1, inplace=True)
df_db_addition = df_db_addition.astype({
    'TSI': 'Int64',
    'Age_Years': 'Int64',
    'Age_Days': 'Int64',
    'Price': 'Int64',
    'Buyer_ID': 'Int64',
    'Seller_ID': 'Int64'
})
print("Hello")
df_db_addition.to_csv(os.path.join(transfer_data_dir, "df_closed_data_test.csv"), index=False)

### END OF TEST FOR CLOSING TRANSFER SEARCH ###



# ### ALL INCLUSIVE TEST FOR OPEN TRANSFER SEARCH ###
# ref_data_dir = os.path.join(hatman.__path__[0], 'reference_data')
# out_dir = os.path.join(hatman.__path__[0], 'output', 'transfer_data')
# log_dir = os.path.join(hatman.__path__[0], 'log')
# search_patterns_dir = os.path.join(hatman.__path__[0], 'reference_data', 'transfer_search_patterns')
# f = open(os.path.join(ref_data_dir, 'login_info.json'))
# launch_info = json.load(f)
# skill = "keeper"
# csv_track = skill + "_transfer_tracker.csv"
# csv_db = skill + "_transfer_data.csv"
# split_index = 0
# n_procs = 1
#
# if not os.path.isfile(os.path.join(search_patterns_dir, csv_track)):
#     df_transfer_tracker = read.get_search_pattern(skill, transfer_tracker=True)
# else:
#     df_transfer_tracker = pd.read_csv(os.path.join(search_patterns_dir, csv_track), index_col=False)
#
# # Beginning of function
# df_transfer_tracker.reset_index(drop=True, inplace=True)
# skill_cap = skill.capitalize()
# csv_name = skill + "_transfer_tracker_" + str(split_index) + ".csv"
# csv_db = skill + "_transfer_data_" + str(split_index) + ".csv"
# df_open_transfer_data = pd.DataFrame()  # the DataFrame that will group all the transfer data results for the given skill
# transfer_page_id = "ctl00_ctl00_CPContent_CPMain_ucPager_repPages_ctl0"
# timeout = 3
# nap_time = 0.1
# break_it = False
#
# # Logger:
# log_name = "open_transfer_log"
# # Now we will  configure the logger
# log_file_path = os.path.join(log_dir, f"{log_name}_{split_index}.log")
#
# while not df_transfer_tracker["researched"].all(axis=0):
#     # 1) Get the transfer dictionary for the current transfer query and launch the query
#     che.check_wifi_connection()
#     driver = nav.launch_web_browser()
#     try:
#         time_dict_ref = read.get_hattrick_date(driver, time_ref_dict=None, transfer_deadline=None)
#     except TimeoutException:
#         print("\nProcess {} restarting".format(str(split_index)))
#         with open(log_file_path, "a+") as f:
#             f.write("TimeoutException getting hattrick date. Process {} restarting\n".format(str(split_index)))
#         driver.quit()
#     except nav.NoInternetException:
#         sys.exit(0, "Reconnect to Wifi before launching script again.")
#
#     for i_row, row in df_transfer_tracker.iterrows():
#         if break_it:
#             break_it = False
#             break
#         current_query_data_collected = row["researched"]
#         if not current_query_data_collected:
#             transfer_dict = copy.deepcopy(glova.transfer_dict_init)  # intialize search dictionary
#             transfer_dict["Age"]["Years"]["Min"] = row["min_year"]
#             transfer_dict["Age"]["Years"]["Max"] = row["max_year"]
#             transfer_dict["Age"]["Days"]["Min"] = row["min_days"]
#             transfer_dict["Age"]["Days"]["Max"] = row["max_days"]
#             transfer_dict["Skills"]["Skill_1"]["Name"] = skill_cap
#             transfer_dict["Skills"]["Skill_1"]["Min"] = row["section_min"]
#             transfer_dict["Skills"]["Skill_1"]["Max"] = row["section_max"]
#             try:
#                 n_pages, n_results = rap.launch_transfer_search(driver, transfer_dict)
#             except TimeoutException:
#                 print(
#                     "\nTimeoutException launching transfer search. Process {} restarting".format(str(split_index)))
#                 with open(log_file_path, "a+") as f:
#                     f.write(
#                         "TimeoutException launching transfer search. Process {} restarting"
#                         "\n".format(str(split_index))
#                     )
#                 driver.quit()
#                 break
#
#             except nav.NoInternetException:
#                 sys.exit(0, "Reconnect to Wifi before launching script again.")
#
#             # 2) Write the number of results found in tracking csv
#             df_transfer_tracker.at[i_row, "n_results"] = n_results
#
#             # 3) Establish the next page (1, 2, 3 or 4) that needs to be scrapped
#             # A function that looks at columns page1_collected, page2_collected...
#             # in the transfer tracker needs to be created to get this page.
#             next_page_to_scrap = read.get_next_page_to_scrap(row)  # 3 for example
#
#             while not current_query_data_collected:
#                 che.check_wifi_connection()
#                 time.sleep(nap_time)
#                 # 4) Go to that page using the htlm id key
#                 try:
#                     if next_page_to_scrap > 1:
#                         xtransfer_page_id = transfer_page_id + str(next_page_to_scrap - 1) + \
#                                             "_p" + str(next_page_to_scrap - 1)
#                         nav.wait("id", xtransfer_page_id, timeout, driver)
#                         time.sleep(nap_time)
#                         driver.find_element_by_id(xtransfer_page_id).click()
#                 except TimeoutException:
#                     print("\nProcess {} restarting".format(str(split_index)))
#                     with open(log_file_path, "a+") as f:
#                         f.write(
#                             "TimeoutException finding transfer page. Process {} restarting"
#                             "\n".format(str(split_index))
#                         )
#                     break_it = True
#                     driver.quit()
#                     break
#                 except nav.NoInternetException:
#                     sys.exit(0, "Reconnect to Wifi before launching script again.")
#
#                 # 5) Collect page transfer data
#                 try:
#                     che.check_wifi_connection()
#                     time.sleep(nap_time)
#                     df_page_transfer = read.collect_1p_transfer_search_data(driver)
#                 except TimeoutException:
#                     print("\nProcess {} restarting".format(str(split_index)))
#                     with open(log_file_path, "a+") as f:
#                         f.write(
#                             "TimeoutException collecting page data transfer. Process {} restarting\n".format(
#                                 str(split_index))
#                         )
#                     break_it = True
#                     driver.quit()
#                     break
#                 except nav.NoInternetException:
#                     sys.exit(0, "Reconnect to Wifi before launching script again.")
#
#                 # 6) Add transfer ID, Hattrick Dates
#                 if not df_page_transfer.empty:
#                     df_page_transfer["Unique_Transfer_Key"] = ""
#                     df_page_transfer["Searched_Skill_Name"] = ""
#                     df_page_transfer["Searched_Age_Range"] = ""
#                     df_page_transfer["Searched_Skill_Range"] = ""
#                     df_page_transfer["Number_Search_Results"] = 0
#
#                     for i, row2 in df_page_transfer.iterrows():
#                         run_dict = row2.to_dict()
#                         keys_to_keep = ["Nationality", "Transfer_ID", "Speciality", "Transfer_Time"]
#                         run_dict2 = {k: v for k, v in run_dict.items() if k not in keys_to_keep}
#                         df_page_transfer.at[i, "Unique_Transfer_Key"] = str(
#                             comp.generate_transfer_key(run_dict2))
#                         df_page_transfer.at[i, "Search_Date"] = time_dict_ref["launch_time"]["date"]
#                         time_dict = read.get_hattrick_date(driver, time_ref_dict=time_dict_ref,
#                                                            transfer_deadline=df_page_transfer.at[
#                                                                i, "Transfer_Date"])
#                         df_page_transfer.at[i, "Transfer_Date_Day"] = time_dict["transfer_time"]["day_name"]
#                         df_page_transfer.at[i, "Transfer_Date_Week"] = time_dict["transfer_time"][
#                             "week"]  # TODO: Fix Hattrick Week
#                         df_page_transfer.at[i, "Transfer_Date_Season"] = time_dict["transfer_time"]["season"]
#
#                         # 7) Add this DF to the df_open_transfer_data DF. Keep unique transfer player ID
#                         df_page_transfer.at[i, "Searched_Skill_Name"] = skill
#                         df_page_transfer.at[i, "Searched_Age_Range"] = \
#                             str(transfer_dict["Age"]["Years"]["Min"]) + "." + \
#                             str(transfer_dict["Age"]["Days"]["Min"]).zfill(3) + "_" + \
#                             str(transfer_dict["Age"]["Years"]["Max"]) + "." + \
#                             str(transfer_dict["Age"]["Days"]["Max"]).zfill(3)
#                         df_page_transfer.at[i, "Searched_Skill_Range"] = \
#                             str(transfer_dict["Skills"]["Skill_1"]["Min"]) + "_" + \
#                             str(transfer_dict["Skills"]["Skill_1"]["Max"])
#                         df_page_transfer.at[i, "Number_Search_Results"] = n_results
#
#                 # 8) Add this DF to the df_open_transfer_data DF. Keep unique transfer player ID
#                 if not df_page_transfer.empty:
#                     df_open_transfer_data = pd.concat([df_open_transfer_data, df_page_transfer], sort=False,
#                                                       ignore_index=True)
#                 df_open_transfer_data.drop_duplicates(subset="Unique_Transfer_Key", inplace=True)
#
#                 # 9) Write the df_open_transfer_data to update the csv
#                 df_open_transfer_data.to_csv(os.path.join(out_dir, csv_db), index=False)
#
#                 # 10) Update the df_transfer_tracker to say that the page has been searched
#                 df_transfer_tracker.at[i_row, "searched_p" + str(next_page_to_scrap)] = True
#
#                 # 11) Establish if all pages have been searched for this transfer query
#                 current_query_data_collected = che.check_search_status(df_transfer_tracker, i_row, n_pages)
#                 if current_query_data_collected:
#                     df_transfer_tracker.at[i_row, "researched"] = True
#                 df_transfer_tracker.to_csv(os.path.join(out_dir, csv_name), index=False)
#
#                 # 12) Increment of the next page to search
#                 next_page_to_scrap += 1
#
#             # Print to log
#             with open(log_file_path, "a+") as f:
#                 f.write(
#                     f"Open data collection. Skill: {skill} / Index: {split_index} out of {n_procs} / Transfer "
#                     f"Search no. {str(i_row + 1).zfill(3)} out of {str(df_transfer_tracker.shape[0]).zfill(3)} "
#                     f"--> COMPLETE\n"
#                 )
#
#     driver.quit()
# ### END OF ALL INCLUSIVE TEST FOR OPEN TRANSFER SEARCH ###

# if __name__ == '__main__':
#     print(f"Launching transfer scrapping with {str(procs)} processor(s)...\n")
#     start = time.perf_counter()
#     df_open_transfer_data = rap.scrap_transfer_market(launch_info, "playmaking", n_procs=procs)
#     # df_closed_transfer_data = rap.enrich_transfer_database(launch_info, "playmaking", n_procs=procs)
#     end = time.perf_counter()
#     print(f"\nFinished in {round(end-start, 2)} second(s)")