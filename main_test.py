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
    transfer_completed = False
    more_recent_transfer = False
    next_transfer_after_deadline = False
    player_exists = True
    dict_transfer_closure = {}

    search_icon = '//*[@id="shortcutsNoSupporter"]/div/a[1]/img'
    search_drop_menu = 'ctl00_ctl00_CPContent_CPMain_ddlCategory'
    player_id_box = 'ctl00_ctl00_CPContent_CPMain_txtSearchPlayerID'
    search_player_button = '//*[@id="ctl00_ctl00_CPContent_CPMain_btnSearchPlayers"]'
    search_res_table = 'ctl00_ctl00_CPContent_CPMain_grdPlayers_ctl00'
    player_link = 'ctl00_ctl00_CPContent_CPMain_grdPlayers_ctl00_ctl04_lnkPlayer'
    owner_table = '//*[@id="mainBody"]/div[3]/table/tbody/tr/td[1]'

    nav.wait("xpath", search_icon, timeout, driver)
    driver.find_element_by_xpath(search_icon).click()

    nav.wait("id", search_drop_menu, timeout, driver)
    drop = Select(driver.find_element_by_id(search_drop_menu))
    drop.select_by_value("5")  # drop.select_by_value("Players")

    nav.wait("id", player_id_box, timeout, driver)
    id_input = driver.find_element_by_id(player_id_box)
    id_input.send_keys(str(player_id))

    nav.wait("xpath", search_player_button, timeout, driver)
    driver.find_element_by_xpath(search_player_button).click()

    nav.wait("id", search_res_table, timeout, driver)
    try:
        driver.find_element_by_id(player_link).click()
    except:
        player_exists = False
        # print("Player with ID {} retired".format(str(player_id)))
    # wait("id", player_link, timeout, driver)

    if player_exists:
        time.sleep(0.1)
        nav.wait("xpath", owner_table, timeout, driver)
        owner = driver.find_element_by_class_name("ownerAndStatusPlayerInfo")
        owner_html = owner.get_attribute("innerHTML").split("<a")[1].split("</a>")[0]
        owner_content = owner_html.split('"')
        owner_id = None
        owner_href = None
        owner_name = None

        for i, val in enumerate(owner_content):
            if "TeamID" in str(val):
                owner_id = int(val.split("=")[1])
                owner_href = str(val)
            if "title" in str(val):
                owner_name = str(owner_content[i + 1].strip())

        html_doc = driver.page_source
        soup = BeautifulSoup(html_doc, "html.parser")  # the page is parsed
        transfer_history = soup.find_all(id="transferHistory")[0]
        try:
            transfer_table = transfer_history.find_all("table")[0]
        except IndexError:
            transfer_aborted = True

        if not transfer_aborted:
            transfer_head = transfer_table.thead.find_all("tr")[0].find_all("th")
            transfer_rows = transfer_table.tbody.find_all("tr")  # all transfer data rows
            j = 0
            old_seller_name = None
            old_seller_id = None
            old_seller_href = None

            for row in transfer_rows:
                transfer_body = row.find_all("td")

                for i, col in enumerate(transfer_head):
                    cell_value = transfer_body[i].text.strip()
                    if str(col.text) == "Deadline":
                        dict_transfer_closure["Player_ID"] = player_id
                        if str(cell_value) != transfer_deadline:
                            date_transfer_x = comp.reverse_date(str(cell_value))
                            date_transfer_dl = comp.reverse_date(transfer_deadline)
                            if date_transfer_x > date_transfer_dl:
                                more_recent_transfer = True
                                next_transfer_after_deadline = True
                            else:
                                next_transfer_after_deadline = False
                            if j + 1 == len(transfer_rows):
                                transfer_aborted = True  # last transfer, not matching date, transfer was aborted
                                dict_transfer_closure["Transfer_Status"] = "Aborted"
                        else:
                            transfer_completed = True
                            dict_transfer_closure["Transfer_Status"] = "Completed"
                    elif str(col.text) == "Seller":
                        seller_href = transfer_body[i].div.a.get("href")
                        new_seller_name = str(cell_value)
                        new_seller_id = int(seller_href.split("=")[1])
                        new_seller_href = str(seller_href)
                        if not transfer_aborted:
                            if next_transfer_after_deadline:
                                dict_transfer_closure["Buyer_Name"] = old_seller_name
                                dict_transfer_closure["Buyer_ID"] = old_seller_id
                                dict_transfer_closure["Buyer_Href"] = old_seller_href
                            else:
                                dict_transfer_closure["Buyer_Name"] = owner_name
                                dict_transfer_closure["Buyer_ID"] = owner_id
                                dict_transfer_closure["Buyer_Href"] = owner_href
                            dict_transfer_closure["Seller_Name"] = new_seller_name
                            dict_transfer_closure["Seller_ID"] = new_seller_id
                            dict_transfer_closure["Seller_Href"] = new_seller_href
                        else:
                            dict_transfer_closure["Buyer_Name"] = None
                            dict_transfer_closure["Buyer_ID"] = None
                            dict_transfer_closure["Buyer_Href"] = None
                            if more_recent_transfer:
                                if next_transfer_after_deadline:
                                    dict_transfer_closure["Seller_Name"] = new_seller_name
                                    dict_transfer_closure["Seller_ID"] = new_seller_id
                                    dict_transfer_closure["Seller_Href"] = new_seller_href
                            else:
                                dict_transfer_closure["Seller_Name"] = owner_name
                                dict_transfer_closure["Seller_ID"] = owner_id
                                dict_transfer_closure["Seller_Href"] = owner_href

                    elif str(col.text) == "TSI":
                        if not transfer_aborted:
                            dict_transfer_closure[str(col.text)] = int(cell_value.replace("\xa0", ""))
                    elif str(col.text) == "Age":
                        if not transfer_aborted:
                            age_str = cell_value.split("(")[0]
                            days_str = cell_value.split("(")[1].split(")")[0]
                            dict_transfer_closure[str(col.text)] = int(age_str)
                            dict_transfer_closure["Days"] = int(days_str)
                    elif str(col.text) == "Price":
                        if not transfer_aborted:
                            cell_value = cell_value.split("€")[0]
                            dict_transfer_closure["Price_Euros"] = int(cell_value.replace("\xa0", ""))
                        else:
                            dict_transfer_closure["Price_Euros"] = None
                    else:
                        pass

                old_seller_name = new_seller_name
                old_seller_id = new_seller_id
                old_seller_href = new_seller_href

                if transfer_completed:
                    break

                j += 1
        else:
            dict_transfer_closure["Player_ID"] = player_id
            dict_transfer_closure["Transfer_Status"] = "Aborted"
            dict_transfer_closure["Buyer_Name"] = None
            dict_transfer_closure["Buyer_ID"] = None
            dict_transfer_closure["Buyer_Href"] = None
            dict_transfer_closure["Seller_Name"] = owner_name
            dict_transfer_closure["Seller_ID"] = owner_id
            dict_transfer_closure["Seller_Href"] = owner_href
            dict_transfer_closure["TSI"] = None
            dict_transfer_closure["Age"] = None
            dict_transfer_closure["Days"] = None
            dict_transfer_closure["Price_Euros"] = None

        skill_elem = soup.find_all("a", attrs={"class": "skill"})
        dict_transfer_closure["Friendliness"] = str(skill_elem[0].text)
        dict_transfer_closure["Aggressiveness"] = str(skill_elem[1].text)
        dict_transfer_closure["Honesty"] = str(skill_elem[2].text)
    else:
        dict_transfer_closure["Player_ID"] = player_id
        dict_transfer_closure["Transfer_Status"] = "Retired"
        dict_transfer_closure["Buyer_Name"] = None
        dict_transfer_closure["Buyer_ID"] = None
        dict_transfer_closure["Buyer_Href"] = None
        dict_transfer_closure["Seller_Name"] = None
        dict_transfer_closure["Seller_ID"] = None
        dict_transfer_closure["Seller_Href"] = None
        dict_transfer_closure["Price_Euros"] = None
        dict_transfer_closure["Friendliness"] = None
        dict_transfer_closure["Aggressiveness"] = None
        dict_transfer_closure["Honesty"] = None

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