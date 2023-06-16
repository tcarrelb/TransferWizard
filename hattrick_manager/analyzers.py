import hattrick_manager as hatman
import hattrick_manager.reference_data.global_vars as glova
import hattrick_manager.navigators as nav
import hattrick_manager.checkers as che
import hattrick_manager.readers as read

import os
import sys
import time
import tqdm
import pandas as pd
from copy import deepcopy
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException


def investigate_search_pattern(skill):
    # Loop to get search pattern distribution
    skill_cap = skill.capitalize()
    csv_name = skill + '_search_cases.csv'
    transfer_dict_init = glova.transfer_dict_init
    ref_dir = os.path.join(hatman.__path__[0], 'reference_data', 'transfer_search_patterns')
    search_pattern_skill_csv = os.path.join(ref_dir, csv_name)

    if not os.path.isfile(search_pattern_skill_csv):
        df_search_pattern = read.get_search_pattern(skill)
    else:
        df_search_pattern = pd.read_csv(csv_name, index_col=False)

    while not df_search_pattern['researched'].all(axis=0):
        try:
            che.check_connected()
            print('Connected to Wifi.')
            driver = nav.launch_web_browser()
            print('Chrome Driver launched.')
            with tqdm(total=df_search_pattern.shape[0], desc='Search Pattern Progress') as pbar:
                for i_row, row in df_search_pattern.iterrows():
                    data_collected = row['researched']
                    if not data_collected:
                        transfer_dict = deepcopy(transfer_dict_init)  # intialize search dictionnary
                        transfer_dict['Age']['Years']['Min'] = row['min_year']
                        transfer_dict['Age']['Years']['Max'] = row['max_year']
                        transfer_dict['Age']['Days']['Min'] = row['min_days']
                        transfer_dict['Age']['Days']['Max'] = row['max_days']
                        transfer_dict['Skills']['Skill_1']['Name'] = skill_cap
                        transfer_dict['Skills']['Skill_1']['Min'] = row['section_min']
                        transfer_dict['Skills']['Skill_1']['Max'] = row['section_max']
                        _, n_results = launch_transfer_search(driver, transfer_dict)  # only n of transfers is returned
                        df_search_pattern.at[i_row, 'researched'] = True
                        df_search_pattern.at[i_row, 'n_results'] = n_results
                        df_search_pattern.to_csv(search_pattern_skill_csv, index=False)
                    pbar.update(1)

        except TimeoutException:
            driver.quit()

        except nav.NoInternetException:
            sys.exit(0, 'Reconnect to Wifi before launching script again.')

        finally:
            pass

    return
