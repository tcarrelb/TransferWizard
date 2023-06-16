# -*- coding: utf-8 -*-
"""
Created on Thu Apr 29 09:42:49 2021

@author: Thomas
"""
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import Select

from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import copy
import socket
import sys
from tqdm import tqdm
import re
import datetime
import hashlib

import hattrick_manager.navigators as nav
import hattrick_manager.scrappers as rap

import warnings

warnings.filterwarnings("ignore", message="A value is trying to be set on a copy of a slice from a DataFrame")

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


def get_top10_scorers(df):
    now = time.time()
    days_old = 7  # top10 update frequency
    cutoff = now - (days_old * 86400)
    stat_file = os.stat("top_10_scorers.csv")
    last_mod = stat_file.st_mtime

    if last_mod > cutoff:
        df_top10_new = pd.read_csv("top_10_scorers.csv", index_col=False)
        print("Top 10 Scorer list less than {} days old. No update required\n".format(str(days_old)))

    else:
        print("Top 10 Scorer list more than {} days old. It will be updated".format(str(days_old)))
        df_top10 = df.sort_values(["Goals for the team"], ascending=[False]).reset_index(drop=True)
        df_top10 = df_top10.iloc[:10, :]
        df_top10_old = pd.read_csv("top_10_scorers.csv", index_col=False)
        scorer_filter = df_top10_old.columns.tolist()
        df_top10 = df_top10.filter(scorer_filter)
        df_top10_new = pd.concat([df_top10, df_top10_old]).drop_duplicates()
        df_top10_new = df_top10_new.sort_values(["Goals for the team"], ascending=[False]).reset_index(drop=True)

        # Keep the updated goal count
        topten_id = []
        index_to_remove = []
        for index, player in df_top10_new.iterrows():
            player_id = player["PlayerID"]
            if (len(topten_id) < 10) and (player_id not in topten_id):
                topten_id.append(player_id)
            else:
                index_to_remove.append(index)

        df_top10_new = df_top10_new.drop(index_to_remove).reset_index(drop=True)
        df_top10_new.to_csv("top_10_scorers.csv", index=False)
        print("Top 10 Scorer list has been succesfully updated\n".format(str(days_old)))

    return df_top10_new


def get_topX_scorers(df, x=20):
    max_x = 40
    if x > max_x:
        print("Not enough historical data to show all scorers.")
        x = max_x

    now = time.time()
    days_old = 0  # topx update frequency
    cutoff = now - (days_old * 86400)
    stat_file = os.stat("top_" + str(x) + "_scorers.csv")
    last_mod = stat_file.st_mtime

    if last_mod > cutoff:
        df_topx_new = pd.read_csv("top_" + str(x) + "_scorers.csv", index_col=False)
        print("Top {} Scorer list less than {} days old. No update required\n".format(str(x), str(days_old)))

    else:
        print("Top {} Scorer list more than {} days old. It will be updated".format(str(x), str(days_old)))
        df_topx = df.sort_values(["Goals for the team"], ascending=[False]).reset_index(drop=True)
        df_topx = df_topx.iloc[:x, :]
        df_topx_old = pd.read_csv("top_" + str(x) + "_scorers.csv", index_col=False)
        scorer_filter = df_topx_old.columns.tolist()
        df_topx = df_topx.filter(scorer_filter)
        df_topx_new = pd.concat([df_topx, df_topx_old]).drop_duplicates()
        df_topx_new = df_topx_new.sort_values(["Goals for the team"], ascending=[False]).reset_index(drop=True)

        # Keep the updated goal count
        topx_id = []
        index_to_remove = []
        for index, player in df_topx_new.iterrows():
            player_id = player["PlayerID"]
            if (len(topx_id) < x) and (player_id not in topx_id):
                topx_id.append(player_id)
            else:
                index_to_remove.append(index)

        df_topx_new = df_topx_new.drop(index_to_remove).reset_index(drop=True)
        df_topx_new.to_csv("top_" + str(x) + "_scorers.csv", index=False)
        print("Top {} Scorer list has been succesfully updated\n".format(str(x), str(days_old)))

    return df_topx_new


def search_transfer(driver, t_search):
    timeout = 2
    transfer_icon = '//*[@id="shortcutsNoSupporter"]/div/a[4]/img'
    years_min_menu = 'ctl00_ctl00_CPContent_CPMain_ddlAgeMin'
    years_max_menu = 'ctl00_ctl00_CPContent_CPMain_ddlAgeMax'
    days_min_menu = 'ctl00_ctl00_CPContent_CPMain_ddlAgeDaysMin'
    days_max_menu = 'ctl00_ctl00_CPContent_CPMain_ddlAgeDaysMax'
    skill_root = 'ctl00_ctl00_CPContent_CPMain_ddlSkill'
    search_icon = 'ctl00_ctl00_CPContent_CPMain_butSearch'
    clear_icon = '//*[@id="mainBody"]/table[1]/tbody/tr[7]/td[2]/a[2]'
    no_transfer_id = 'ctl00_ctl00_CPContent_CPMain_lblNoTransfers'
    main_wrapper = 'ctl00_ctl00_CPContent_mainWrapper'

    time.sleep(3)
    try:
        nav.check_connected()
        rap.wait("xpath", transfer_icon, timeout, driver)
        driver.find_element_by_xpath(transfer_icon).click()
        rap.wait("id", years_min_menu, timeout, driver)
    except TimeoutException:
        driver.quit()
    except nav.NoInternetException:
        sys.exit(0, "Reconnect to Wifi before launching script again.")
    time.sleep(3)

    drop = Select(driver.find_element_by_id(years_min_menu))
    drop.select_by_value(str(t_search["Age"]["Years"]["Min"]))
    drop = Select(driver.find_element_by_id(years_max_menu))
    drop.select_by_value(str(t_search["Age"]["Years"]["Max"]))
    drop = Select(driver.find_element_by_id(days_min_menu))
    drop.select_by_value(str(t_search["Age"]["Days"]["Min"]))
    drop = Select(driver.find_element_by_id(days_max_menu))
    drop.select_by_value(str(t_search["Age"]["Days"]["Max"]))

    for i, skill_val in enumerate(t_search["Skills"].values()):
        skill_name_id = skill_root + str(i + 1)
        skill_min_id = skill_root + str(i + 1) + "Min"
        skill_max_id = skill_root + str(i + 1) + "Max"
        if skill_val["Name"] is not None:
            drop = Select(driver.find_element_by_id(skill_name_id))
            drop.select_by_visible_text(skill_val["Name"])
            drop = Select(driver.find_element_by_id(skill_min_id))
            drop.select_by_value(str(skill_val["Min"]))
            drop = Select(driver.find_element_by_id(skill_max_id))
            drop.select_by_value(str(skill_val["Max"]))
        else:
            drop = Select(driver.find_element_by_id(skill_name_id))
            drop.select_by_value("-1")

    driver.find_element_by_xpath(clear_icon).click()
    driver.find_element_by_id(search_icon).click()
    time.sleep(3)

    # Checking number of players filtered
    rap.wait("id", main_wrapper, timeout, driver)
    time.sleep(3)
    no_transfer_found = rap.check_exists_by_id(no_transfer_id, driver)

    if no_transfer_found:
        # print("No transfer results found")
        page_number = 0
        transfer_number = 0
    else:
        number_transfers = driver.find_element_by_class_name('PagerRight_Default')
        split_list = number_transfers.text.split('of')
        page_number = int(split_list[1].split(',')[0].strip())
        transfer_number = split_list[-1].strip()
        if transfer_number != "many":
            transfer_number = int(split_list[-1].strip())
        else:
            transfer_number = 101

    # print("A total of {} transfers were found, on {} page(s).".format(transfer_number, page_number))
    return page_number, transfer_number


def clean_name(param_name):
    p1 = param_name.split(" ")
    p2 = [x.capitalize() for x in p1]
    clean_p = ""
    for p in p2:
        clean_p = clean_p + p + "_"
    final_p = clean_p[:-1]
    return final_p


def get_search_pattern(skill, transfer_tracker=False):
    if not transfer_tracker:
        csv_name = skill + "_search_cases.csv"
    else:
        csv_name = skill + "_transfer_tracker.csv"
    df = pd.read_excel('search_pattern.xlsx', sheet_name=skill)
    df_skill_pat = pd.DataFrame()
    n_sections = 3

    df[["Min", "Max"]] = df.age_range.str.split("-", expand=True)
    df_skill_pat[["min_year", "min_days"]] = df.Min.str.split(".", expand=True)
    df_skill_pat[["max_year", "max_days"]] = df.Max.str.split(".", expand=True)
    df_skill_pat[["section_1_min", "section_1_max"]] = df.section_1.str.split("&", expand=True)
    df_skill_pat[["section_2_min", "section_2_max"]] = df.section_2.str.split("&", expand=True)
    df_skill_pat[["section_3_min", "section_3_max"]] = df.section_3.str.split("&", expand=True)

    df_skill_pat["min_year"] = df_skill_pat["min_year"].astype(str).astype(int)
    df_skill_pat["max_year"] = df_skill_pat["max_year"].astype(str).astype(int)
    df_skill_pat["min_days"] = df_skill_pat["min_days"].astype(str).astype(int)
    df_skill_pat["max_days"] = df_skill_pat["max_days"].astype(str).astype(int)
    df_skill_pat["section_1_min"] = df_skill_pat["section_1_min"].astype(str).astype(int)
    df_skill_pat["section_1_max"] = df_skill_pat["section_1_max"].astype(str).astype(int)
    df_skill_pat["section_2_min"] = df_skill_pat["section_2_min"].astype(str).astype(int)
    df_skill_pat["section_2_max"] = df_skill_pat["section_2_max"].astype(str).astype(int)
    df_skill_pat["section_3_min"] = df_skill_pat["section_3_min"].astype(str).astype(int)
    df_skill_pat["section_3_max"] = df_skill_pat["section_3_max"].astype(str).astype(int)

    df_skill_search_cases = []
    i = 0
    for i_row, row in df_skill_pat.iterrows():
        for i_section in range(n_sections):
            df_skill_search_case = {}
            section_min = "section_" + str(i_section + 1) + "_min"
            section_max = "section_" + str(i_section + 1) + "_max"
            df_skill_search_case["min_year"] = row["min_year"]
            df_skill_search_case["max_year"] = row["max_year"]
            df_skill_search_case["min_days"] = row["min_days"]
            df_skill_search_case["max_days"] = row["max_days"]
            df_skill_search_case["section_min"] = row[section_min]
            df_skill_search_case["section_max"] = row[section_max]
            df_skill_search_case["researched"] = False
            if transfer_tracker:
                df_skill_search_case["searched_p1"] = False
                df_skill_search_case["searched_p2"] = False
                df_skill_search_case["searched_p3"] = False
                df_skill_search_case["searched_p4"] = False
            df_skill_search_case["n_results"] = 0
            df_skill_search_cases.append(df_skill_search_case)
            i += 1

    df_skill_search_cases = pd.DataFrame(df_skill_search_cases)
    df_skill_search_cases = df_skill_search_cases[df_skill_search_cases["section_min"] != 0].reset_index(drop=True)
    df_skill_search_cases.to_csv(csv_name, index=False)

    return df_skill_search_cases


## Loop to get search pattern distribution
def investigate_search_pattern(launch_info, skill):
    skill_cap = skill.capitalize()
    csv_name = skill + "_search_cases.csv"

    if not os.path.isfile(csv_name):
        df_search_pattern = get_search_pattern(skill)
    else:
        df_search_pattern = pd.read_csv(csv_name, index_col=False)

    while not df_search_pattern["researched"].all(axis=0):
        try:
            nav.check_connected()
            driver = nav.launch_webbrowser(launch_info, nav_followup=False)
            with tqdm(total=df_search_pattern.shape[0], desc="Search Pattern Progress") as pbar:
                for i_row, row in df_search_pattern.iterrows():
                    data_collected = row["researched"]
                    if not data_collected:
                        transfer_dict = copy.deepcopy(transfer_dict_init)  # intialize search dictionnary
                        transfer_dict["Age"]["Years"]["Min"] = row["min_year"]
                        transfer_dict["Age"]["Years"]["Max"] = row["max_year"]
                        transfer_dict["Age"]["Days"]["Min"] = row["min_days"]
                        transfer_dict["Age"]["Days"]["Max"] = row["max_days"]
                        transfer_dict["Skills"]["Skill_1"]["Name"] = skill_cap
                        transfer_dict["Skills"]["Skill_1"]["Min"] = row["section_min"]
                        transfer_dict["Skills"]["Skill_1"]["Max"] = row["section_max"]
                        _, n_results = search_transfer(driver, transfer_dict)
                        df_search_pattern.at[i_row, "researched"] = True
                        df_search_pattern.at[i_row, "n_results"] = n_results
                        # df_search_pattern["n_results"].iloc[i_row] = n_results
                        df_search_pattern.to_csv(csv_name, index=False)
                    pbar.update(1)
        except TimeoutException:
            driver.quit()
        except nav.NoInternetException:
            sys.exit(0, "Reconnect to Wifi before launching script again.")
        finally:
            pass
    return





def generate_transfer_key(run_dict):
    args = [(key, value) for key, value in run_dict.items()]
    args.sort()
    m = hashlib.md5()
    for key, value in args:
        m.update("({}, {})".format(key, value).encode('utf-8'))

    return m.hexdigest()


def split_dataframe(df, chunk_size=10000):
    chunks = list()
    num_chunks = len(df) // chunk_size + 1
    for i in range(num_chunks):
        chunks.append(df[i * chunk_size:(i + 1) * chunk_size])
    return chunks
