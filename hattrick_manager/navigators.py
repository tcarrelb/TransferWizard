import socket


class NoInternetException(Exception):
    """Exception raised when there is no Internet Connection."""
    pass


def check_connection():
    """
    Checking that the connection is working and available.
    :return:
    """
    ip_address = socket.gethostbyname(socket.gethostname())
    if ip_address == '127.0.0.1':
        raise NoInternetException('You have been disconnected from the internet.')
    return
