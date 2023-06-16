import socket
from selenium.common.exceptions import NoSuchElementException


class NoInternetException(Exception):
    """Exception raised when there is no Internet Connection."""
    pass


def check_wifi_connection():
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


def check_exists_by_id(elem_id, driver):
    try:
        driver.find_element_by_id(elem_id)
    except NoSuchElementException:
        return False

    return True


def check_search_status(df_transfer_tracker, i_row, n_pages):
    search_complete = True
    for i in range(n_pages):
        if not df_transfer_tracker.at[i_row, "searched_p" + str(i + 1)]:
            search_complete = False

    return search_complete
