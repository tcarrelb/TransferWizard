# -*- coding: utf-8 -*-
"""
Created on Sat Apr  3 14:42:07 2021

@author: Thomas
"""
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
import numpy as np
from os.path import isfile, join
from bs4 import BeautifulSoup
import pandas as pd
from multiprocessing import Pool
from itertools import repeat
from tqdm import tqdm
from datetime import datetime, timedelta

import hattrick_manager.navigators as nav
import hattrick_manager.computers_old as comp

# Skills: Keeper/Defending/Playmaking/Winger/Scoring/Passing/Set Pieces/Experience/Leadership
# Speciality: Technical/Quick/Powerful/Unpredictable/Head/Resilient/Support/NoFilter/NoSpeciality/AnySpeciality
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


def check_exists_by_id(elem_id, driver):
    try:
        driver.find_element_by_id(elem_id)
    except NoSuchElementException:
        return False
    return True


def reverse_date(old_d):
    delim = "-"
    old_d = old_d.split(delim)[::-1]
    new_d = ""
    for x in old_d:
        new_d += (x + delim)
    new_d = new_d[:-1]

    return new_d


def wait(element_type: str, element_name: str, timeout: float, driver):
    waiting = WebDriverWait(driver, 2)

    if element_type == "xpath":
        try:
            waiting.until(EC.presence_of_element_located((By.XPATH, element_name)))
        except:
            print("Could not find page element {}".format(str(element_name)))
    elif element_type == "id":
        try:
            waiting.until(EC.presence_of_element_located((By.ID, element_name)))
        except:
            print("Could not find page element {}".format(str(element_name)))
    else:
        pass

    return


def collect_my_team_data(driver) -> dict:
    timeout = 10
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "ctl00_ctl00_CPContent_divStartMain")))
    print("Page loaded\n")

    htmlDoc = driver.page_source
    soup = BeautifulSoup(htmlDoc, "html.parser")  # the page is parsed
    playerTable = soup.find("table", attrs={"class": "tablesorter indent"})
    playerTableHeadings = playerTable.thead.find_all("tr")  # contains 2 rows
    playerTableData = playerTable.tbody.find_all("tr")  # contains 2 rows

    # Get all the headings of Lists
    headings = []
    data = []
    for th in playerTableHeadings[0].find_all("th"):
        headings.append(th.get('title'))

    # Get all the player data (the one found in the .csv)
    for tr in playerTableData:
        t_row = {}
        for td, th in zip(tr.find_all("td"), headings):
            cellValue = td.text.replace('\n', '').strip()

            if th == "Nationality":
                t_row[th] = td.a.img.get('title')
            elif th == "Shirt number":
                t_row[th] = int(cellValue) if cellValue else None
            elif th == "Name":
                t_row[th] = td.get("data-fullname")
                # print(td.get("data-fullname"))
            elif th == "Coach":
                t_row[th] = "Yes" if cellValue else "No"
            elif th == "Specialty":
                spe = td.get("data-sortvalue")
                if not spe:
                    t_row[th] = None
                else:
                    t_row[th] = td.i.get('title')
            elif th == "Mother club bonus":
                if int(td.get("data-sortvalue")) == 1:
                    t_row[th] = "No"
                else:
                    t_row[th] = "Yes"
            elif th == "Injuries":
                injury = td.get("data-sortvalue")
                if not injury:
                    t_row[th] = "Healthy"
                elif int(injury) == 2:
                    t_row[th] = "Recovering"
                else:
                    injury_length = td.i.get("data-injury-length")
                    t_row[th] = "Injured (" + injury_length + ")"
            elif th == "Warnings":
                warning = td.get("data-sortvalue")
                if not warning:
                    t_row[th] = None
                elif int(warning) == 1:
                    t_row[th] = "1 yellow card"
                elif int(warning) == 2:
                    t_row[th] = "2 yellow cards"
                elif int(warning) == 3:
                    t_row[th] = "1 red card"
                else:
                    t_row[th] = None
            elif th == "Transfer-listed":
                if int(td.get("data-sortvalue")) == 2:
                    t_row[th] = "Yes"
                else:
                    t_row[th] = "No"
            elif th == "Transfer-listed":
                if int(td.get("data-sortvalue")) == 2:
                    t_row[th] = "Yes"
                else:
                    t_row[th] = "No"
            elif th == "Age":
                age = td.get("data-sortvalue")
                age = float(age[:2] + "." + age[2:])
                t_row[th] = age
            elif th == "TSI":
                t_row[th] = int(td.get("data-sortvalue"))
            elif th == "Wage":
                t_row[th] = int(int(td.get("data-sortvalue")) * 0.1)
            elif th == "Last match date":
                if cellValue:
                    date = td.get("data-sortvalue")
                    date = date[:4] + "/" + date[4:6] + "/" + date[6:]
                    t_row[th] = date
                else:
                    t_row[th] = None
            elif th == "Last match rating":
                t_row[th] = float(cellValue) if cellValue else None
            elif th == "Last match position":
                t_row[th] = str(cellValue) if cellValue else None
            else:
                t_row[th] = int(cellValue) if cellValue else None
        data.append(t_row)

    df_myteam = pd.DataFrame(data)

    return df_myteam


def collect_player_extra_data(p_type: str, p_coach: str, driver) -> dict:
    timeout = 10
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "content")))
    print("Player page loaded")

    htmlDoc = driver.page_source
    soup = BeautifulSoup(htmlDoc, "html.parser")  # the page is parsed
    player_extra_data = {}

    if p_type == "senior":
        skill_elem = soup.find_all("a", attrs={"class": "skill"})
        print("Got skills")
        player_id = driver.find_elements_by_class_name("idNumber")
        if p_coach == "Yes":
            index = 1
        else:
            index = 0

        player_extra_data["PlayerID"] = int(player_id[0].text.strip("(").strip(")"))
        player_extra_data["Friendliness"] = skill_elem[index].text
        player_extra_data["Aggressiveness"] = skill_elem[index + 1].text
        player_extra_data["Honesty"] = skill_elem[index + 2].text

        tables = soup.find_all("table")  # locate all the tables in the page
        print("Got all tables")
        for table in tables:
            if "Career goals" in table.text:
                goalTable = table
                print("Got goal table")
                break

        goalTableData = goalTable.tbody.find_all("tr")  # contains 2 rows

        for i in range(len(goalTableData)):  # iterate over the table rows to get all the goal data
            data = goalTableData[i].text.split("\n")
            data_text = []

            for row in data:
                data_text.append(row.strip())
            data_text = list(filter(None, data_text))

            player_extra_data[data_text[0]] = int(data_text[1])


    elif p_type == "youth":
        pass
    elif p_type == "transfer":
        pass
    else:
        print("Unknow player type")

    return player_extra_data


def collect_myteam_extra_data(df_team, driver):
    df = copy.deepcopy(df_team)
    extra_data = []
    break_it = False

    if isfile(join(os.getcwd(), "partial_team_extra_data.csv")):
        df_partial_etd_old = pd.read_csv("partial_team_extra_data.csv", index_col=False)
        print("Partial team extra data collected from work directory\n")
        scanned_ids = df_partial_etd_old["PlayerID"].tolist()
        restart_pos = None

        for index, player in df.iterrows():
            player_id = player["PlayerID"]
            if player_id not in scanned_ids:
                restart_at_id = player_id
                restart_index = index
                restart_pos = (restart_at_id, restart_index)
                break
        if restart_pos is not None:
            df = df.iloc[restart_pos[1]:, :].reset_index(drop=True)
    else:
        restart_pos = (1, 1)
        df_partial_etd_old = pd.DataFrame()

    if restart_pos is not None:
        for index, player in df.iterrows():
            player_id = player["PlayerID"]
            player_is_coach = player["Coach"]
            wait = WebDriverWait(driver, 2)

            if index == 0:
                player_url = "/Club/Players/Player.aspx?playerId=" + str(player_id)
                try:
                    wait.until(EC.element_to_be_clickable((By.XPATH, '//h3/a[contains(@href,"%s")]' % player_url)))
                    driver.find_element_by_xpath('//h3/a[contains(@href,"%s")]' % player_url).click()
                except:
                    break_it = True
                    print("Could not find page element, extra data collection will terminate at Player {}.".format(
                        str(player_id)))

            else:
                player_url = "/Players/player.aspx?PlayerId=" + str(player_id)
                try:
                    wait.until(EC.element_to_be_clickable((By.XPATH, '//span/a[contains(@href,"%s")]' % player_url)))
                    driver.find_element_by_xpath('//span/a[contains(@href,"%s")]' % player_url).click()
                except:
                    break_it = True
                    print("Could not find page element, extra data collection will terminate at Player {}.".format(
                        str(player_id)))

            if break_it:
                break
            else:
                player_extra_data = collect_player_extra_data("senior", player_is_coach, driver)
                extra_data.append(player_extra_data)
                print("{} extra data collected.\n".format(player["Name"]))

        df_partial_etd_new = pd.DataFrame(extra_data)
        df_concat = pd.concat([df_partial_etd_old, df_partial_etd_new]).reset_index(drop=True)
    else:
        df_concat = df_partial_etd_old.reset_index(drop=True)

    return df_concat


def get_transfer_closure(player_id: int, transfer_deadline, driver):
    timeout = 2
    transfer_aborted = False
    player_exists = True
    dict_transfer_closure = {}

    search_icon = '//*[@id="shortcutsNoSupporter"]/div/a[1]/img'
    search_drop_menu = 'ctl00_ctl00_CPContent_CPMain_ddlCategory'
    player_id_box = 'ctl00_ctl00_CPContent_CPMain_txtSearchPlayerID'
    search_player_button = '//*[@id="ctl00_ctl00_CPContent_CPMain_btnSearchPlayers"]'
    search_res_table = 'ctl00_ctl00_CPContent_CPMain_grdPlayers_ctl00'
    player_link = 'ctl00_ctl00_CPContent_CPMain_grdPlayers_ctl00_ctl04_lnkPlayer'
    owner_table = '//*[@id="mainBody"]/div[3]/table/tbody/tr/td[1]'

    wait("xpath", search_icon, timeout, driver)
    driver.find_element_by_xpath(search_icon).click()

    wait("id", search_drop_menu, timeout, driver)
    drop = Select(driver.find_element_by_id(search_drop_menu))
    drop.select_by_value("5")  # drop.select_by_value("Players")

    wait("id", player_id_box, timeout, driver)
    id_input = driver.find_element_by_id(player_id_box)
    id_input.send_keys(str(player_id))

    wait("xpath", search_player_button, timeout, driver)
    driver.find_element_by_xpath(search_player_button).click()

    wait("id", search_res_table, timeout, driver)
    try:
        driver.find_element_by_id(player_link).click()
    except:
        player_exists = False
        print("Player with ID {} retired".format(str(player_id)))
    # wait("id", player_link, timeout, driver)

    if player_exists:
        wait("xpath", owner_table, timeout, driver)
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
            transfer_body = transfer_table.tbody.find_all("tr")[0].find_all("td")  # only the last transfer data

            for i, col in enumerate(transfer_head):
                cell_value = transfer_body[i].text.strip()

                if str(col.text) == "Deadline":
                    dict_transfer_closure["Player_ID"] = player_id
                    if str(cell_value) != transfer_deadline:
                        transfer_aborted = True
                        dict_transfer_closure["Transfer_Status"] = "Aborted"
                    else:
                        dict_transfer_closure["Transfer_Status"] = "Completed"
                elif str(col.text) == "Seller":
                    if not transfer_aborted:
                        seller_href = transfer_body[i].div.a.get("href")
                        dict_transfer_closure["Buyer_Name"] = owner_name
                        dict_transfer_closure["Buyer_ID"] = owner_id
                        dict_transfer_closure["Buyer_Href"] = owner_href
                        dict_transfer_closure["Seller_Name"] = str(cell_value)
                        dict_transfer_closure["Seller_ID"] = int(seller_href.split("=")[1])
                        dict_transfer_closure["Seller_Href"] = str(seller_href)
                    else:
                        dict_transfer_closure["Buyer_Name"] = None
                        dict_transfer_closure["Buyer_ID"] = None
                        dict_transfer_closure["Buyer_Href"] = None
                        dict_transfer_closure["Seller_Name"] = owner_name
                        dict_transfer_closure["Seller_ID"] = owner_id
                        dict_transfer_closure["Seller_Href"] = owner_href
                # elif str(col.text) == "Season":
                #     if not transfer_aborted:
                #         n_season = int(cell_value.split(" ")[0])
                #         n_week = int(cell_value.split(" ")[1][1:-1])
                #         dict_transfer_closure["Hattrick_Season"] = n_season
                #         dict_transfer_closure["Hattrick_Week"] = n_week
                #     else:
                #         dict_transfer_closure["Hattrick_Season"] = None  # TODO find a way to get it
                #         dict_transfer_closure["Hattrick_Week"] = None  # TODO find a way to get it
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
                        dict_transfer_closure["Price_€"] = int(cell_value.replace("\xa0", ""))
                    else:
                        dict_transfer_closure["Price_€"] = None
                else:
                    pass
        else:
            dict_transfer_closure["Player_ID"] = player_id
            dict_transfer_closure["Transfer_Status"] = "Aborted"
            dict_transfer_closure["Buyer_Name"] = None
            dict_transfer_closure["Buyer_ID"] = None
            dict_transfer_closure["Buyer_Href"] = None
            dict_transfer_closure["Seller_Name"] = owner_name
            dict_transfer_closure["Seller_ID"] = owner_id
            dict_transfer_closure["Seller_Href"] = owner_href
            # dict_transfer_closure["Hattrick_Season"] = None #TODO find a way to get it
            # dict_transfer_closure["Hattrick_Week"] = None #TODO find a way to get it
            dict_transfer_closure["Price_€"] = None

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
        # dict_transfer_closure["Hattrick_Season"] = None  # TODO find a way to get it
        # dict_transfer_closure["Hattrick_Week"] = None  # TODO find a way to get it
        dict_transfer_closure["Price_€"] = None
        dict_transfer_closure["Friendliness"] = None
        dict_transfer_closure["Aggressiveness"] = None
        dict_transfer_closure["Honesty"] = None

    return pd.DataFrame([dict_transfer_closure])


def collect_transfer_data(driver) -> dict:
    no_transfer_id = 'ctl00_ctl00_CPContent_CPMain_lblNoTransfers'
    timeout = 3
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "ctl00_ctl00_CPContent_divStartMain")))
    # print("Page loaded\n")
    time.sleep(0.5)
    no_transfer_found = check_exists_by_id(no_transfer_id, driver)

    if no_transfer_found:
        df_transfers = pd.DataFrame()
    else:
        htmlDoc = driver.page_source
        soup = BeautifulSoup(htmlDoc, "html.parser")  # the page is parsed
        playerTable = soup.find("table", attrs={"class": "tablesorter indent"})
        playerTableHeadings = playerTable.thead.find_all("tr")  # contains 2 rows
        playerTableData = playerTable.tbody.find_all("tr")  # contains 2 rows

        # Get all the headings of Lists
        headings = []
        data = []
        for th in playerTableHeadings[0].find_all("th"):
            heading = str(th.get('title'))
            headings.append(heading.strip())
        headings = headings[:-1]

        # Get all the player data (the one found in the .csv)
        for tr in playerTableData:
            t_row = {}
            for td, th in zip(tr.find_all("td"), headings):
                cellValue = td.text.replace('\n', '').strip()
                if th == "Nationality":
                    t_row[th] = td.a.img.get('title')
                elif th == "Name":
                    player_href = td.a.get("href")
                    player_id = player_href.split("=")[1].split("&")[0].strip()
                    t_row["Player_ID"] = int(player_id)
                    t_row[th] = td.get("data-fullname")
                elif th == "Coach":
                    t_row[th] = "Yes" if cellValue else "No"
                elif th == "Specialty":
                    spe = td.get("data-sortvalue")
                    if not spe:
                        t_row[th] = None
                    else:
                        t_row[th] = td.i.get('title')
                elif th == "Highest bid":
                    clean_th = comp.clean_name(th)
                    if int(td.get("data-sortvalue")) == 1:
                        t_row[clean_th] = "No"
                    else:
                        t_row[clean_th] = "Yes"
                elif th == "Injuries":
                    injury = td.get("data-sortvalue")
                    if not injury:
                        t_row[th] = "Healthy"
                    elif int(injury) == 2:
                        t_row[th] = "Recovering"
                    elif int(injury) == 3:
                        t_row[th] = "Injured (1)"
                    elif int(injury) == 4:
                        t_row[th] = "Injured (2)"
                    elif int(injury) == 5:
                        t_row[th] = "Injured (3)"
                    elif int(injury) == 6:
                        t_row[th] = "Injured (4)"
                    else:
                        t_row[th] = "Healthy"
                        # injury_length = td.i.get("data-injury-length")
                        # t_row[th] = "Injured (" + injury_length + ")"
                elif th == "Warnings":
                    warning = td.get("data-sortvalue")
                    if not warning:
                        t_row[th] = None
                    elif int(warning) == 1:
                        t_row[th] = "1 yellow card"
                    elif int(warning) == 2:
                        t_row[th] = "2 yellow cards"
                    elif int(warning) == 3:
                        t_row[th] = "1 red card"
                    else:
                        t_row[th] = None
                elif th == "Age":  # TODO change age format
                    age = td.get("data-sortvalue")
                    # age = float(age[:2] + "." + age[2:])
                    age = int(age[:2])
                    t_row[th] = age
                elif th == "TSI":
                    t_row[th] = int(td.get("data-sortvalue"))
                elif th == "Wage":
                    t_row[th] = int(int(td.get("data-sortvalue")) * 0.1)
                elif th == "Bid":
                    bid = int(td.get("data-sortvalue"))
                    if bid == 1:
                        bid = 0
                    else:
                        bid = int(bid * 0.1)
                    t_row[th] = bid
                elif th == "Deadline":
                    datetime = cellValue.split(" ")
                    date = str(datetime[0])
                    timez = str(datetime[1])
                    t_row["Transfer_Date"] = date
                    t_row["Transfer_Time"] = timez
                    t_row["Transfer_Date_Day"] = ""
                    t_row["Transfer_Date_Week"] = 0
                    t_row["Transfer_Date_Season"] = 0
                    t_row["Search_Date"] = ""
                    t_row["Transfer_ID"] = player_id + "_" + date  # unique transfer ID
                elif th == "Weeks in club" or th == "Set Pieces":
                    clean_th = comp.clean_name(th)
                    t_row[clean_th] = int(cellValue) if cellValue else None
                else:
                    t_row[th] = int(cellValue) if cellValue else None
            data.append(t_row)

        df_transfers = pd.DataFrame(data)

    return df_transfers


## Checking main team data
def scan_my_team(launch_info, top10_update=False, topx_update=False):
    try:
        nav.check_connected()
        driver = nav.launch_webbrowser(launch_info, nav_followup=True)
        df_main_team_data = collect_my_team_data(driver)
    except TimeoutException:
        driver.quit()
    except nav.NoInternetException:
        sys.exit(0, "Reconnect to Wifi before launching script again.")
    df_top10 = pd.DataFrame()
    df_topx = pd.DataFrame()
    print("Main team data collected\n")

    # Checking if the team has been modified since the last data collection
    df_team_data_old = pd.read_csv("complete_team_data.csv", index_col=False)
    old_ids = set(df_team_data_old["PlayerID"])
    new_ids = set(df_main_team_data["PlayerID"])
    i = 0

    if not old_ids == new_ids:  # case where team data has been modified
        df_partial_etd_new = collect_myteam_extra_data(df_main_team_data, driver)
        df_partial_etd_new.to_csv("partial_team_extra_data.csv", index=False)

        print("Complementary team data needs to be updated\n")
        while not df_partial_etd_new.shape[0] == df_main_team_data.shape[
            0]:  # complementary data has been collected for the entire team
            try:
                if i > 0:
                    driver.quit()
                    nav.check_connected()
                    driver = nav.launch_webbrowser(launch_info, nav_followup=True)
                    df_partial_etd_new = collect_myteam_extra_data(df_main_team_data, driver)
                    df_partial_etd_new.to_csv("partial_team_extra_data.csv", index=False)
                i += 1
            except TimeoutException:
                driver.quit()
            except nav.NoInternetException:
                sys.exit(0, "Reconnect to Wifi before launching script again.")
            finally:
                pass

        df_team_extra_data = df_partial_etd_new
        print("Complementary team data completely collected\n")
        os.remove("partial_team_extra_data.csv")
        df_team_data = pd.merge(df_main_team_data, df_team_extra_data, on="PlayerID", how="outer")
        df_team_data.to_csv("complete_team_data.csv", index=False)
        if top10_update:
            df_top10 = comp.get_top10_scorers(df_team_data)
        if topx_update:
            df_topx = comp.get_topX_scorers(df_team_data, x=40)

    else:
        print("Team data up to date\n")
        df_team_data = df_team_data_old
        if top10_update:
            df_top10 = comp.get_top10_scorers(df_team_data)
        if topx_update:
            df_topx = comp.get_topX_scorers(df_team_data, x=40)

    return df_team_data, df_top10, df_topx


def get_next_page_to_scrap(row):
    page_found = False
    i = 1
    next_page = 1
    while not page_found:
        if not row["searched_p" + str(i)]:
            next_page = i
            page_found = True
        i += 1
    return next_page


def check_search_status(df_transfer_tracker, i_row, n_pages):
    search_complete = True
    for i in range(n_pages):
        if not df_transfer_tracker.at[i_row, "searched_p" + str(i + 1)]:
            search_complete = False

    return search_complete


def scrap_transfer_market_per_process(scrap_transfer_inputs):
    df_transfer_tracker, split_index, launch_info, skill = scrap_transfer_inputs

    skill_cap = skill.capitalize()
    csv_name = skill + "_transfer_tracker_" + str(split_index) + ".csv"
    csv_db = skill + "_transfer_data_" + str(split_index) + ".csv"
    df_open_transfer_data = pd.DataFrame()  # the DataFrame that will group all the transfer data results for the given skill
    transfer_page_id = "ctl00_ctl00_CPContent_CPMain_ucPager_repPages_ctl0"
    timeout = 3
    break_it = False

    while not df_transfer_tracker["researched"].all(axis=0):
        # 1) Get the transfer dictionary for the current transfer query and launch the query
        nav.check_connected()
        driver = nav.launch_webbrowser(launch_info, nav_followup=False)
        try:
            time_dict_ref = comp.get_hattrick_date(driver, time_ref_dict=None, transfer_deadline=None)
        except TimeoutException:
            print("\nProcess {} restarting".format(str(split_index)))
            driver.quit()
        except nav.NoInternetException:
            sys.exit(0, "Reconnect to Wifi before launching script again.")

        with tqdm(total=df_transfer_tracker.shape[0], desc="Transfer Data Collection", leave=True) as pbar:
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
                        n_pages, n_results = comp.search_transfer(driver, transfer_dict)
                    except TimeoutException:
                        print("\nProcess {} restarting".format(str(split_index)))
                        driver.quit()
                        break

                    except nav.NoInternetException:
                        sys.exit(0, "Reconnect to Wifi before launching script again.")

                    # 2) Write the number of results found in tracking csv
                    df_transfer_tracker.at[i_row, "n_results"] = n_results

                    # 3) Establish the next page (1, 2, 3 or 4) that needs to be scrapped
                    # A function that looks at columns page1_collected, page2_collected...
                    # in the transfer tracker needs to be created to get this page.
                    next_page_to_scrap = get_next_page_to_scrap(row)  # 3 for example

                    while not current_query_data_collected:
                        nav.check_connected()

                        # 4) Go to that page using the htlm id key
                        try:
                            if next_page_to_scrap > 1:
                                xtransfer_page_id = transfer_page_id + str(next_page_to_scrap - 1) + \
                                                    "_p" + str(next_page_to_scrap - 1)
                                wait("id", xtransfer_page_id, timeout, driver)
                                driver.find_element_by_id(xtransfer_page_id).click()
                        except TimeoutException:
                            print("\nProcess {} restarting".format(str(split_index)))
                            break_it = True
                            driver.quit()
                            break
                        except nav.NoInternetException:
                            sys.exit(0, "Reconnect to Wifi before launching script again.")

                        # 5) Collect page transfer data
                        try:
                            nav.check_connected()
                            df_page_transfer = collect_transfer_data(driver)
                        except TimeoutException:
                            print("\nProcess {} restarting".format(str(split_index)))
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
                                time_dict = comp.get_hattrick_date(driver, time_ref_dict=time_dict_ref,
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
                        df_open_transfer_data.to_csv(csv_db, index=False)

                        # 10) Update the df_transfer_tracker to say that the page has been searched
                        df_transfer_tracker.at[i_row, "searched_p" + str(next_page_to_scrap)] = True

                        # 11) Establish if all pages have been searched for this transfer query
                        current_query_data_collected = check_search_status(df_transfer_tracker, i_row, n_pages)
                        if current_query_data_collected:
                            df_transfer_tracker.at[i_row, "researched"] = True
                        df_transfer_tracker.to_csv(csv_name, index=False)

                        # 12) Increment of the next page to search
                        next_page_to_scrap += 1

                print("\nProcess {} progress:".format(str(split_index)))
                pbar.update()

    return df_open_transfer_data


def scrap_transfer_market(launch_info, skill, n_procs=1):
    # 0a) We start be defining or retrieving the transfer tracker for the given skill
    # This csv file is a bit different than the one used for the search pattern determination
    # It has more columns and tracks also the pages that were searched for each transfer query
    csv_track = skill + "_transfer_tracker.csv"
    csv_db = skill + "_transfer_data.csv"

    if not os.path.isfile(csv_track):
        df_transfer_tracker = comp.get_search_pattern(skill, transfer_tracker=True)
    else:
        df_transfer_tracker = pd.read_csv(csv_track, index_col=False)

    # 0b) The transfer tracker is split in X blocks depending on the number of processors required
    # Note that the script does not use multi-threading, it uses multi-processing
    # https://blog.alexoglou.com/multithreading-or-multiprocessing-selenium-with-python/
    # https://stackoverflow.com/questions/53475578/python-selenium-multiprocessing
    # https://medium.com/geekculture/introduction-to-selenium-and-python-multi-threading-module-aa5b1c4386cb
    df_split = np.array_split(df_transfer_tracker, n_procs)
    split_index = np.arange(0, n_procs, 1)

    # 0c) Launch the pool of processes, with headless drivers
    # The below will probably be part of another function as all of this has to be performed per process
    # Everything now is per processor.
    scrap_transfer_inputs = zip(df_split, split_index, repeat(launch_info), repeat(skill))
    pool = Pool(n_procs)
    df_open_transfer_data = pd.concat(pool.map(scrap_transfer_market_per_process, scrap_transfer_inputs))
    pool.close()
    pool.join()

    # Clean the folder, combine results
    df_open_transfer_data.drop_duplicates(subset="Unique_Transfer_Key", inplace=True)
    df_open_transfer_data.reset_index(drop=True, inplace=True)
    df_open_transfer_data["Closed"] = False
    df_open_transfer_data.to_csv(csv_db, index=False)

    df_transfer_tracker_final = pd.DataFrame()
    for i in split_index:
        csv_track_i = csv_track.split(".")[0] + "_" + str(i) + ".csv"
        csv_db_i = csv_db.split(".")[0] + "_" + str(i) + ".csv"
        df_csv_track_i = pd.read_csv(csv_track_i, index_col=False)
        df_transfer_tracker_final = pd.concat([df_transfer_tracker_final, df_csv_track_i],
                                              sort=False, ignore_index=True)
        os.remove(csv_db_i)
        os.remove(csv_track_i)

    df_transfer_tracker_final.reset_index(drop=True, inplace=True)
    df_transfer_tracker_final.to_csv(csv_track, index=False)

    return df_open_transfer_data


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

    wait("xpath", search_icon, timeout, driver)
    driver.find_element_by_xpath(search_icon).click()

    wait("id", search_drop_menu, timeout, driver)
    drop = Select(driver.find_element_by_id(search_drop_menu))
    drop.select_by_value("5")  # drop.select_by_value("Players")

    wait("id", player_id_box, timeout, driver)
    id_input = driver.find_element_by_id(player_id_box)
    id_input.send_keys(str(player_id))

    wait("xpath", search_player_button, timeout, driver)
    driver.find_element_by_xpath(search_player_button).click()

    wait("id", search_res_table, timeout, driver)
    try:
        driver.find_element_by_id(player_link).click()
    except:
        player_exists = False
        # print("Player with ID {} retired".format(str(player_id)))
    # wait("id", player_link, timeout, driver)

    if player_exists:
        time.sleep(0.1)
        wait("xpath", owner_table, timeout, driver)
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
                            date_transfer_x = reverse_date(str(cell_value))
                            date_transfer_dl = reverse_date(transfer_deadline)
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


def collect_transfer_closure_data(closure_transfer_inputs):
    # df_pre, split_index, launch_info = list(closure_transfer_inputs)[0]
    df_pre, split_index, launch_info, csv_track_name, csv_db_name = closure_transfer_inputs

    csv_track = csv_track_name.split(".")[0] + "_" + str(split_index) + ".csv"
    csv_db = csv_db_name.split(".")[0] + "_" + str(split_index) + ".csv"
    df_closed_transfer_data = pd.DataFrame()
    break_it = False

    while not df_pre["Closed"].all(axis=0):
        # 1) Get the transfer dictionary for the current transfer query and launch the query
        nav.check_connected()
        driver = nav.launch_webbrowser(launch_info, nav_followup=False)
        try:
            comp.get_hattrick_date(driver, time_ref_dict=None, transfer_deadline=None)
        except TimeoutException:
            print("\nProcess {} restarting".format(str(split_index)))
            driver.quit()
        except nav.NoInternetException:
            sys.exit(0, "Reconnect to Wifi before launching script again.")

        closed_transfer_indices = list()
        with tqdm(total=df_pre.shape[0], desc="Transfer Closure Data Collection", leave=True) as pbar:
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
                        nav.check_connected()
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

                df_pre.at[i_row, "Closed"] = True
                df_pre.to_csv(csv_track, index=False)

                df_db_addition = df_pre.merge(df_closed_transfer_data, on="Player_ID")
                df_db_addition.drop(["Closed"], axis=1, inplace=True)
                df_db_addition.to_csv(csv_db, index=False)

                print("\nProcess {} progress:".format(str(split_index)))
                pbar.update()

    return df_db_addition


def enrich_transfer_database(launch_info, skill, n_procs=1):
    csv_open_transfer_data = skill + "_transfer_data.csv"
    csv_track = skill + "_transfer_closure_tracking.csv"
    csv_db = skill + "_transfer_database.csv"

    df_transfer_data = pd.read_csv(csv_open_transfer_data, index_col=False)
    df_transfer_data.drop_duplicates(subset="Unique_Transfer_Key", inplace=True)
    df_transfer_data.reset_index(drop=True, inplace=True)
    df_transfer_data = df_transfer_data.astype(object).replace(np.nan, "None")
    df_transfer_data.Age = df_transfer_data.Age.astype(int)  # TODO: fix in the scrap_transfer_market function

    # 0b) The transfer tracker is split in X blocks depending on the number of processors required
    # Note that the script does not use multi-threading, it uses multi-processing
    df_split = np.array_split(df_transfer_data, n_procs)
    split_index = np.arange(0, n_procs, 1)

    # 0c) Launch the pool of processes, with headless drivers
    # The below will probably be part of another function as all of this has to be performed per process
    # Everything now is per processor.
    closure_transfer_inputs = zip(df_split, split_index, repeat(launch_info), repeat(csv_track), repeat(csv_db))
    # df_tdb = collect_transfer_closure_data(closure_transfer_inputs)
    pool = Pool(n_procs)
    df_tdb = pd.concat(pool.map(collect_transfer_closure_data, closure_transfer_inputs))
    df_tdb.reset_index(drop=True, inplace=True)
    pool.close()
    pool.join()

    # Clean the folder, combine results
    df_tdb.loc[df_tdb.Transfer_Status == "Completed", "Days_x"] = df_tdb.Days_y
    df_tdb.Days_x = df_tdb.Days_x.astype(int)
    df_tdb.loc[df_tdb.Transfer_Status == "Completed", "Age_x"] = df_tdb.Age_y
    df_tdb.Age_x = df_tdb.Age_x.astype(int)
    df_tdb.loc[df_tdb.Transfer_Status == "Completed", "TSI_x"] = df_tdb.TSI_y
    df_tdb.TSI_x = df_tdb.TSI_x.astype(int)
    new_names = {"Age_x": "Age", "Days_x": "Days", "TSI_x": "TSI"}
    df_tdb.rename(columns=new_names, inplace=True)
    df_tdb.drop(["Age_y", "Days_y", "TSI_y"], axis=1, inplace=True)

    df_tdb.drop_duplicates(subset="Unique_Transfer_Key", inplace=True)
    df_tdb.reset_index(drop=True, inplace=True)
    df_tdb.to_csv(csv_db, index=False)

    df_tdb_track = pd.DataFrame()
    for i in split_index:
        csv_track_i = csv_track.split(".")[0] + "_" + str(i) + ".csv"
        csv_db_i = csv_db.split(".")[0] + "_" + str(i) + ".csv"
        df_csv_track_i = pd.read_csv(csv_track_i, index_col=False)
        df_tdb_track = pd.concat([df_tdb_track, df_csv_track_i],
                                 sort=False, ignore_index=True)
        os.remove(csv_db_i)
        os.remove(csv_track_i)

    # Clean the folder, combine results
    df_tdb_track.drop_duplicates(subset="Unique_Transfer_Key", inplace=True)
    df_tdb_track.reset_index(drop=True, inplace=True)
    df_tdb_track.to_csv(csv_track, index=False)

    return df_tdb