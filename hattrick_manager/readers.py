import hattrick_manager.reference_data.global_vars as glova
import hattrick_manager.navigators as nav

import sys
import pandas as pd
from copy import deepcopy
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as ec


def collect_team_data() -> pd.DataFrame:
    """
    Collecting the team data in creating a DataFrame out of it.

    Returns
    -------
    df_team_data: pd.DataFrame
    """
    def _collect_team_data(_driver: object) -> pd.DataFrame:
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

    driver = None
    try:
        nav.check_connection()
        driver = nav.launch_web_browser()
        nav.goto_team_webpage(driver)
        df_team_data = _collect_team_data(driver)
    except TimeoutException:
        driver.quit()
    except nav.NoInternetException:
        sys.exit(0, 'Reconnect to Wifi before launching script again.')

    return df_team_data
