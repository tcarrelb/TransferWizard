from reference_data import global_vars as glova

import socket
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as ec


class NoInternetException(Exception):
    """Exception raised when there is no Internet Connection."""
    pass


def check_connection():
    """
    Checking the internet connection.

    Returns
    -------
    Returns NoInternetException if not connected to Wifi.
    """
    ip_address = socket.gethostbyname(socket.gethostname())
    if ip_address == '127.0.0.1':
        raise NoInternetException('You have been disconnected from the internet.')

    return


def wait(element_type: str, element_name: str, timeout: float, driver: object):
    """
    Functions that waits for an HTML element to be located.

    Parameters
    ----------
    element_type: str
        The type of element looked for, id, xpath or other.
    element_name: str
        Name of the element looked for.
    timeout: float
        Timeout limit for the search of the element.
    driver: object
        The web driver object.

    Returns
    -------
    Returns TimeoutException if element not found on time.
    """
    waiting = WebDriverWait(driver, timeout)
    if element_type == 'xpath':
        try:
            waiting.until(ec.presence_of_element_located((By.XPATH, element_name)))
        except TimeoutException:
            print(f'Could not find page element {element_name}')
    elif element_type == 'id':
        try:
            waiting.until(ec.presence_of_element_located((By.ID, element_name)))
        except TimeoutException:
            print(f'Could not find page element {element_name}')

    return


def goto_id(id_link: str, driver: object):
    """
    Click a lind identified by its HTML ID.

    Parameters
    ----------
    id_link: str
        Name of the HTML ID link.
    driver: object
        The web driver object.

    Returns
    -------
    Returns TimeoutException if element ID not found on time.
    """
    timeout = 5
    try:
        WebDriverWait(driver, timeout).until(ec.presence_of_element_located((By.ID, id_link)))
        usr_link = driver.find_element_by_id(id_link)
    except TimeoutException:
        print(f'Could not find page element {id_link}')
    else:
        usr_link.send_keys(Keys.RETURN)

    return


def launch_web_browser():
    """
    Launching the web browser.

    Returns
    -------
    driver: object
        Returns the driver object that will then be passed on other to
        other functions.
    """
    timeout = 30
    sleep_duration = 2
    options = webdriver.ChromeOptions()

    options.add_argument(glova.driver_info['options'])
    driver = webdriver.Chrome(glova.driver_info['driver_type']['chrome'], options=options)
    driver.get(glova.login_info['url'])
    driver.set_page_load_timeout(timeout)

    user_name = driver.find_element_by_name(glova.htmlk['name']['username'])
    user_name.send_keys(glova.login_info['username'])
    user_pwd = driver.find_element_by_name(glova.htmlk['name']['password'])
    user_pwd.send_keys(glova.login_info['pwd'])
    user_name.send_keys(Keys.RETURN)
    time.sleep(sleep_duration)

    return driver


def goto_team_webpage(driver: object):
    """
    Checking the internet connection.

    Parameters
    ----------
    driver: object
        The web driver object.
    """
    timeout = 2
    sleep_duration = 2
    club_link = glova.htmlk['id']['club_link']
    team_link = glova.htmlk['id']['team_link']

    wait('id', club_link, timeout, driver)
    goto_id(club_link, driver)
    wait('id', team_link, timeout, driver)
    goto_id(team_link, driver)
    time.sleep(sleep_duration)

    return
