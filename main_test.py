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

import hattrick_manager as hatman
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


def get_transfer_closure(player_id, transfer_deadline, driver):
    timeout = 2
    transfer_aborted = False
    closing_latest_transfer = False
    incomplete_buyer_name = False
    transfer_closed = False
    player_exists = True
    dict_transfer_closure = {}

    search_icon = '//*[@id="shortcutsNoSupporter"]/div/a[1]/img'
    search_drop_menu = 'ctl00_ctl00_CPContent_CPMain_ddlCategory'
    player_id_box = 'ctl00_ctl00_CPContent_CPMain_txtSearchPlayerID'
    search_player_button = '//*[@id="ctl00_ctl00_CPContent_CPMain_btnSearchPlayers"]'
    search_res_table = 'ctl00_ctl00_CPContent_CPMain_grdPlayers_ctl00'
    player_link = 'ctl00_ctl00_CPContent_CPMain_grdPlayers_ctl00_ctl04_lnkPlayer'
    transfer_history_tab_id = '//*[@id="ctl00_ctl00_CPContent_CPMain_btnViewTransferHistory"]'
    player_gentleness_xpath = '//*[@id="mainBody"]/p/a[1]'
    player_aggressiveness_xpath = '//*[@id="mainBody"]/p/a[2]'
    player_honesty_xpath = '//*[@id="mainBody"]/p/a[3]'

    # Click on the hattrick search icon:
    nav.wait("xpath", search_icon, timeout, driver)
    driver.find_element_by_xpath(search_icon).click()

    # Select the "player" category:
    nav.wait("id", search_drop_menu, timeout, driver)
    drop = Select(driver.find_element_by_id(search_drop_menu))
    drop.select_by_value("5")  # drop.select_by_value("Players")

    # Enter the player ID:
    nav.wait("id", player_id_box, timeout, driver)
    id_input = driver.find_element_by_id(player_id_box)
    id_input.send_keys(str(player_id))

    # Click on the "Search" button:
    nav.wait("xpath", search_player_button, timeout, driver)
    driver.find_element_by_xpath(search_player_button).click()

    # Click on the search result link:
    nav.wait("id", search_res_table, timeout, driver)
    try:
        driver.find_element_by_id(player_link).click()
    except:  # TODO: find the specific exception
        player_exists = False
        print("Player with ID {} retired".format(str(player_id)))

    if player_exists:
        dict_transfer_closure["Player_ID"] = player_id
        time.sleep(0.1)
        """Having to deal with a dynamic table (https://www.tutorialspoint.com/
        how-to-click-on-a-button-with-javascript-executor-in-selenium-with-python) we locate the transfer history tab
        and we activate it to retrieve the right table."""
        transfer_history_tab = driver.find_element_by_xpath(transfer_history_tab_id)
        driver.execute_script("arguments[0].click();", transfer_history_tab)

        # Get player personality:
        dict_transfer_closure["Gentleness"] = driver.find_element_by_xpath(player_gentleness_xpath).text
        dict_transfer_closure["Aggressiveness"] = driver.find_element_by_xpath(player_aggressiveness_xpath).text
        dict_transfer_closure["Honesty"] = driver.find_element_by_xpath(player_honesty_xpath).text

        # Once this is done, we can parse the web page to retrieve transfer data:
        html_doc = driver.page_source
        soup = BeautifulSoup(html_doc, "html.parser")  # the page is parsed
        try:  # Check if the player has some transfer history
            transfer_history = soup.find("table", {"class":"htbox-table"})
        except:  # TODO: find the specific error
            transfer_aborted = True

        # Get owner details:
        owner_table = soup.find('div', attrs={"class":"ownerAndStatusPlayerInfo"}).table.tbody
        owner_name = owner_table.find_all("tr")[0].find_all("td")[1].a.text
        owner_href = owner_table.find_all("tr")[0].find_all("td")[1].a.get("href")
        owner_id = int(owner_href.split("TeamID=")[-1])

        if not transfer_aborted:  # there exists a transfer history for the player
            transfer_headers = transfer_history.thead.find_all("tr")[0].find_all("th")
            transfer_headers = [tag.text for tag in transfer_headers]
            transfer_rows = transfer_history.tbody.find_all("tr")  # all transfer data rows
            for j, row in enumerate(transfer_rows):
                transfer_body = row.find_all("td")
                transfer_date = transfer_body[0].text.strip()
                if transfer_date == transfer_deadline:  # this is the transfer we need to close
                    dict_transfer_closure["Transfer_Status"] = "Completed"
                    if j == 0:
                        closing_latest_transfer = True
                    for i, col in enumerate(transfer_headers):
                        cell_value = transfer_body[i]
                        if col == "Deadline":
                            dict_transfer_closure["Transfer_Date"] = cell_value.text.strip()
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
                            break
                        else:
                            pass
            if not transfer_closed:  # this means that the transfer was not found in the transfer history
                dict_transfer_closure["Transfer_Status"] = "Aborted"
        else:  # there is no transfer history for the player
            dict_transfer_closure["Transfer_Status"] = "Aborted"

        if dict_transfer_closure["Transfer_Status"] == "Aborted":
            dict_transfer_closure["Transfer_Date"] = transfer_deadline
            dict_transfer_closure["Seller_Name"] = owner_name
            dict_transfer_closure["Seller_Href"] = owner_href
            dict_transfer_closure["Seller_ID"] = owner_id
            dict_transfer_closure["Buyer_Name"] = None
            dict_transfer_closure["Buyer_Href"] = None
            dict_transfer_closure["Buyer_ID"] = None
            dict_transfer_closure["TSI"] = None
            dict_transfer_closure["Age"] = None
            dict_transfer_closure["Days"] = None
            dict_transfer_closure["Price"] = None

    else:  # the player retired
        dict_transfer_closure["Player_ID"] = player_id
        dict_transfer_closure["Gentleness"] = None
        dict_transfer_closure["Aggressiveness"] = None
        dict_transfer_closure["Honesty"] = None
        dict_transfer_closure["Transfer_Status"] = "Retired"
        dict_transfer_closure["Transfer_Date"] = transfer_deadline
        dict_transfer_closure["Seller_Name"] = None
        dict_transfer_closure["Seller_Href"] = None
        dict_transfer_closure["Seller_ID"] = None
        dict_transfer_closure["Buyer_Name"] = None
        dict_transfer_closure["Buyer_Href"] = None
        dict_transfer_closure["Buyer_ID"] = None
        dict_transfer_closure["TSI"] = None
        dict_transfer_closure["Age"] = None
        dict_transfer_closure["Days"] = None
        dict_transfer_closure["Price"] = None

    return pd.DataFrame([dict_transfer_closure])


procs = 4
ref_data_dir = os.path.join(hatman.__path__[0], 'reference_data')
f = open(os.path.join(ref_data_dir, 'login_info.json'))
launch_info = json.load(f)
timeout = 2
split_index = 0
transfer_data_dir = os.path.join(hatman.__path__[0], 'output', 'transfer_data', 'playmaking_2023-06-15_20-18')
df_open_name = "playmaking_transfer_data.csv"
df_pre = pd.read_csv(os.path.join(transfer_data_dir, df_open_name), index_col=False)
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
            if datetime.now() > dd_dt_p1:  # the transfer has already been closed
                closed_transfer_indices.append(i_row)
                che.check_wifi_connection()
                try:
                    df_row_closure = get_transfer_closure(player_id, deadline, driver)
                except TimeoutException:
                    print("\nProcess {} restarting".format(str(split_index)))
                    driver.quit()
                    break
                except nav.NoInternetException:
                    sys.exit(0, "Reconnect to Wifi before launching script again.")
                df_closed_transfer_data = pd.concat([df_closed_transfer_data, df_row_closure],
                                                    sort=False, ignore_index=True)
            else:
                sys.exit(0, "Transfer has not been closed yet.")


        df_pre.at[i_row, "Closed"] = True
        df_pre.to_csv(csv_track, index=False)

        df_db_addition = df_pre.merge(df_closed_transfer_data, on="Player_ID")
        df_db_addition.drop(["Closed"], axis=1, inplace=True)
        df_db_addition.to_csv(csv_db, index=False)

        print("\nProcess {} progress:".format(str(split_index)))


# if __name__ == '__main__':
#     print(f"Launching transfer scrapping with {str(procs)} processor(s)...\n")
#     start = time.perf_counter()
#     df_open_transfer_data = rap.scrap_transfer_market(launch_info, "playmaking", n_procs=procs)
#     # df_closed_transfer_data = rap.enrich_transfer_database(launch_info, "playmaking", n_procs=procs)
#     end = time.perf_counter()
#     print(f"\nFinished in {round(end-start, 2)} second(s)")