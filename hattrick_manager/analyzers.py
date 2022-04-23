import hattrick_manager as hatman
import hattrick_manager.reference_data.global_vars as glova
import hattrick_manager.navigators as nav
import hattrick_manager.readers as read
import hattrick_manager.checkers as che

import os
import sys
import time
import tqdm
import pandas as pd
from copy import deepcopy
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException


def launch_transfer_search(driver, t_search):
    timeout = 2
    sleep_time = 3  # not needed with great internet connection
    max_disp_transfers = 101  # hard coded hattrick logic
    transfer_icon = '//*[@id="shortcutsNoSupporter"]/div/a[4]/img'
    clear_icon = '//*[@id="mainBody"]/table[1]/tbody/tr[7]/td[2]/a[2]'
    ids = glova.htmlk['id']

    time.sleep(sleep_time)
    try:
        che.check_connected()
        nav.wait('xpath', transfer_icon, timeout, driver)
        driver.find_element_by_xpath(transfer_icon).click()  # go to the transfer menu
        nav.wait('id', ids['years_min_menu'], timeout, driver)
    except TimeoutException:
        driver.quit()
    except nav.NoInternetException:
        sys.exit(0, 'Reconnect to Wifi before launching script again.')
    time.sleep(sleep_time)

    # Select age transfer options:
    drop = Select(driver.find_element_by_id(ids['years_min_menu']))
    drop.select_by_value(str(t_search['Age']['Years']['Min']))
    drop = Select(driver.find_element_by_id(ids['years_max_menu']))
    drop.select_by_value(str(t_search['Age']['Years']['Max']))
    drop = Select(driver.find_element_by_id(ids['days_min_menu']))
    drop.select_by_value(str(t_search['Age']['Days']['Min']))
    drop = Select(driver.find_element_by_id(ids['days_max_menu']))
    drop.select_by_value(str(t_search['Age']['Days']['Max']))

    # Select skill transfer options:
    for i, skill_val in enumerate(t_search['Skills'].values()):
        skill_name_id = ids['skill_root'] + str(i+1)
        skill_min_id = ids['skill_root'] + str(i+1) + 'Min'
        skill_max_id = ids['skill_root'] + str(i+1) + 'Max'
        if skill_val['Name'] is not None:
            drop = Select(driver.find_element_by_id(skill_name_id))
            drop.select_by_visible_text(skill_val['Name'])
            drop = Select(driver.find_element_by_id(skill_min_id))
            drop.select_by_value(str(skill_val['Min']))
            drop = Select(driver.find_element_by_id(skill_max_id))
            drop.select_by_value(str(skill_val['Max']))
        else:
            drop = Select(driver.find_element_by_id(skill_name_id))
            drop.select_by_value('-1')

    driver.find_element_by_xpath(clear_icon).click()  # clear any specialty
    driver.find_element_by_id(ids['search_icon']).click()  # launch the search
    time.sleep(sleep_time)

    # Checking number of players filtered:
    nav.wait('id', ids['main_wrapper'], timeout, driver)
    no_transfer_found = che.check_exists_by_id(ids['no_transfer_id'], driver)

    if no_transfer_found:
        # print('No transfer results found')
        page_number = 0
        transfer_number = 0
    else:
        number_transfers = driver.find_element_by_class_name('PagerRight_Default')
        split_list = number_transfers.text.split('of')
        page_number = int(split_list[1].split(',')[0].strip())
        transfer_number = split_list[-1].strip()
        if transfer_number != 'many':
            transfer_number = int(split_list[-1].strip())
        else:
            transfer_number = max_disp_transfers

    # print('A total of {} transfers were found, on {} page(s).'.format(transfer_number, page_number))
    return page_number, transfer_number


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
