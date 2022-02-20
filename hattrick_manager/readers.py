import hattrick_manager as hatman
import hattrick_manager.reference_data.global_vars as glova
import hattrick_manager.navigators as nav

import os
import sys
import pandas as pd
from copy import deepcopy
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as ec


def collect_main_team_data(_driver) -> pd.DataFrame:
    timeout = 10
    tt_ref = glova.team_table_ref
    WebDriverWait(_driver, timeout).until(ec.presence_of_element_located((By.ID, glova.htmlk['id']['team_page'])))
    html_doc = _driver.page_source
    soup = BeautifulSoup(html_doc, 'html.parser')  # the page is parsed
    player_table = soup.find('table', attrs={'class': str(tt_ref['table_id'])})
    player_table_headings = player_table.thead.find_all('tr')  # contains 2 rows
    player_table_data = player_table.tbody.find_all('tr')  # contains 2 rows

    # Get all the headings:
    headings = []
    data = []
    for th in player_table_headings[0].find_all('th'):
        headings.append(th.get('title'))

    # Get all the player data (the one found in the .csv):
    for tr in player_table_data:
        t_row = {}

        for td, th in zip(tr.find_all('td'), headings):
            cell_value = td.text.replace('\n', '').strip()
            if th == tt_ref['nationality']:
                t_row[th] = td.a.img.get('title')
            elif th == tt_ref['shirt_number']:
                t_row[th] = int(cell_value) if cell_value else None
            elif th == tt_ref['player_name']:
                t_row[th] = td.get('data-fullname')
            elif th == tt_ref['head_coach']:
                t_row[th] = 'Yes' if cell_value else 'No'
            elif th == tt_ref['specialty']:
                spe = td.get('data-sortvalue')
                if not spe:
                    t_row[th] = None
                else:
                    t_row[th] = td.i.get('title')
            elif th == tt_ref['mother_club']:
                if int(td.get('data-sortvalue')) == 1:
                    t_row[th] = 'No'
                else:
                    t_row[th] = 'Yes'
            elif th == tt_ref['injury']:
                injury = td.get('data-sortvalue')
                if not injury:
                    t_row[th] = 'Healthy'
                elif int(injury) == 2:
                    t_row[th] = 'Recovering'
                else:
                    injury_length = td.i.get('data-injury-length')
                    t_row[th] = 'Injured (' + injury_length + ')'
            elif th == tt_ref['injury']:
                warning = td.get('data-sortvalue')
                if not warning:
                    t_row[th] = None
                elif int(warning) == 1:
                    t_row[th] = '1 yellow card'
                elif int(warning) == 2:
                    t_row[th] = '2 yellow cards'
                elif int(warning) == 3:
                    t_row[th] = '1 red card'
                else:
                    t_row[th] = None
            elif th == tt_ref['injury']:
                if int(td.get('data-sortvalue')) == 2:
                    t_row[th] = 'Yes'
                else:
                    t_row[th] = 'No'
            elif th == tt_ref['transfer_listed']:
                if int(td.get('data-sortvalue')) == 2:
                    t_row[th] = 'Yes'
                else:
                    t_row[th] = 'No'
            elif th == tt_ref['age']:
                age = td.get('data-sortvalue')
                age = float(age[:2] + '.' + age[2:])
                t_row[th] = age
            elif th == tt_ref['tsi']:
                t_row[th] = int(td.get('data-sortvalue'))
            elif th == tt_ref['week_wage']:
                t_row[th] = int(int(td.get('data-sortvalue')) * 0.1)
            elif th == tt_ref['last_match_date']:
                if cell_value:
                    date = td.get('data-sortvalue')
                    date = date[:4] + '/' + date[4:6] + '/' + date[6:]
                    t_row[th] = date
                else:
                    t_row[th] = None
            elif th == tt_ref['last_match_rating']:
                t_row[th] = float(cell_value) if cell_value else None
            elif th == tt_ref['last_match_position']:
                t_row[th] = str(cell_value) if cell_value else None
            else:
                t_row[th] = int(cell_value) if cell_value else None
        data.append(t_row)

    _df_team_data = pd.DataFrame(data)
    # Renaming the dataframe columns:
    tt_ref_inv = deepcopy(tt_ref)
    del tt_ref_inv['table_id']
    tt_ref_inv = {v: k for k, v in tt_ref_inv.items()}
    _df_team_data.rename(columns=tt_ref_inv, inplace=True)

    return _df_team_data


def collect_player_extra_data(p_type: str, p_coach: str, __driver) -> dict:
    timeout = 5
    WebDriverWait(__driver, timeout).until(ec.presence_of_element_located((By.ID, 'content')))
    html_page = __driver.page_source
    soup = BeautifulSoup(html_page, 'html.parser')  # the page is parsed
    player_extra_data = {}

    if p_type == 'pro':
        skill_elem = soup.find_all('a', attrs={'class': 'skill'})
        player_id = __driver.find_elements_by_class_name('idNumber')
        index = 1 if p_coach == 'Yes' else 0

        # Retrieve personality data:
        player_extra_data['player_id'] = int(player_id[0].text.strip('(').strip(')'))
        player_extra_data['friendliness'] = skill_elem[index].text
        player_extra_data['aggressiveness'] = skill_elem[index + 1].text
        player_extra_data['honesty'] = skill_elem[index + 2].text

        # Retrieve goal table data:
        tables = soup.find_all('table')  # locate all the tables in the page
        goal_table = None
        for table in tables:
            if 'Career goals' in table.text:
                goal_table = table
                break
        goal_table_data = goal_table.tbody.find_all('tr')  # contains 2 rows

        # Iterate over the table rows to get all the goal data:
        for i in range(len(goal_table_data)):
            data = goal_table_data[i].text.split('\n')
            data_text = []
            for row in data:
                data_text.append(row.strip())
            data_text = list(filter(None, data_text))
            player_extra_data[data_text[0]] = int(data_text[1])

    elif p_type == 'youth':  # to be developed, to collect youth player extra data
        pass

    else:
        print(f'Unknown player type: {p_type}.')

    return player_extra_data


def collect_extra_team_data(df_main_team_data: pd.DataFrame, _driver, partial_path: str) -> pd.DataFrame:
    df = deepcopy(df_main_team_data)
    extra_data = []
    break_it = False

    if os.path.isfile(partial_path):
        # Retrieve the data that was already scanned:
        df_partial_etd_old = pd.read_csv(partial_path, index_col=False)
        print('Partial team extra data collected from work directory\n')
        scanned_ids = df_partial_etd_old['player_id'].tolist()
        restart_pos = None

        # Get the restarting position:
        for index, player in df.iterrows():
            player_id = player['player_id']
            if player_id not in scanned_ids:
                restart_id = player_id
                restart_index = index
                restart_pos = (restart_id, restart_index)
                break
        if restart_pos is not None:
            df = df.iloc[restart_pos[1]:, :].reset_index(drop=True)

    else:  # case where there is no partial data collected
        restart_pos = (1, 1)
        df_partial_etd_old = pd.DataFrame()

    if restart_pos is not None:  # if there is a restarting position (there is more data to collect)
        for index, player in df.iterrows():
            player_id = player['player_id']
            player_is_coach = player['head_coach']
            wait = WebDriverWait(_driver, 2)

            if index == 0:  # if first player in the dataframe
                player_url = glova.htmlk['url']['club_player'] + str(player_id)
                try:
                    wait.until(ec.element_to_be_clickable((
                        By.XPATH, '//h3/a[contains(@href,"%s")]' % player_url)))
                    _driver.find_element_by_xpath('//h3/a[contains(@href,"%s")]' % player_url).click()
                except TimeoutException:
                    break_it = True
                    print(f'Could not find page element. Extra data collection interrupted at Player {player_id}.')
            else:
                player_url = glova.htmlk['url']['player'] + str(player_id)
                try:
                    wait.until(ec.element_to_be_clickable((
                        By.XPATH, '//span/a[contains(@href,"%s")]' % player_url)))
                    _driver.find_element_by_xpath('//span/a[contains(@href,"%s")]' % player_url).click()
                except TimeoutException:
                    break_it = True
                    print(f'Could not find page element. Extra data collection interrupted at Player {player_id}.')

            if break_it:  # if the data collection was interrupted
                break
            else:  # the extra data for the current player can be collected
                player_extra_data = collect_player_extra_data('pro', player_is_coach, _driver)
                extra_data.append(player_extra_data)
                print('{} --> extra data collected'.format(player['player_name']))

        # We are now at the end of the main team dataframe, we concatenate all the extra data together:
        df_partial_etd_new = pd.DataFrame(extra_data)
        df_partial_etd_new.rename(columns={
            'Goals for the team': 'goals_for_team',
            'Career goals': 'career_goals',
            'Hattricks': 'career_hattricks',
            'Season series goals': 'season_series_goals',
            'Season cup goals': 'season_cup_goals',
        }, inplace=True)
        df_concat = pd.concat([df_partial_etd_old, df_partial_etd_new]).reset_index(drop=True)

    else:  # if there is no restarting position (no extra data to collect)
        df_concat = df_partial_etd_old.reset_index(drop=True)

    return df_concat


def collect_team_data() -> pd.DataFrame:
    """
    Collecting the team main data and creating a DataFrame out of it.

    Returns
    -------
    df_team_data: pd.DataFrame
    """
    driver = None
    temp_dir = os.path.join(hatman.__path__[0], 'temp')
    out_dir = os.path.join(hatman.__path__[0], 'output')
    team_data_csv = 'complete_team_data.csv'
    partial_data_csv = 'team_extra_data_partial.csv'
    partial_csv_path = os.path.join(temp_dir, partial_data_csv)
    team_csv_path = os.path.join(out_dir, team_data_csv)
    df_team_main_data = pd.DataFrame()
    try:
        nav.check_connection()
        print('Connected to Wifi.')
        driver = nav.launch_web_browser()
        nav.goto_team_webpage(driver)
        print('Chrome Driver launched.')
        df_team_main_data = collect_main_team_data(driver)
    except TimeoutException:
        driver.quit()
    except nav.NoInternetException:
        sys.exit(0, 'Reconnect to Wifi before launching script again.')
    finally:
        print('Main team data collected.\n')

    # Start collecting extra team data:
    print('Collecting team complementary data...')
    i = 0  # index iterator
    df_partial_etd_new = collect_extra_team_data(df_team_main_data, driver, partial_csv_path)
    df_partial_etd_new.to_csv(partial_csv_path, index=False)

    # Complementary team data has to be collected for the entire team:
    while not df_partial_etd_new.shape[0] == df_team_main_data.shape[0]:
        try:
            if i > 0:
                nav.check_connection()
                df_partial_etd_new = collect_extra_team_data(df_team_main_data, driver, partial_csv_path)
                df_partial_etd_new.to_csv(partial_csv_path, index=False)
            i += 1
        except TimeoutException:
            driver.quit()
        except nav.NoInternetException:
            sys.exit(0, 'Reconnect to Wifi before launching script again.')
        finally:
            pass
    print('Complementary team data collected.\n')

    # Combine all the team data:
    df_team_extra_data = df_partial_etd_new.copy()
    os.remove(partial_csv_path)
    df_team_data = pd.merge(df_team_main_data, df_team_extra_data, on='player_id', how='outer')
    df_team_data.to_csv(team_csv_path, index=False)

    return df_team_data
