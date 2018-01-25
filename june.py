import requests
from functools import wraps

URL = 'https://api-portal.june.energy/'


class NotAuthenticatedError(Exception):
    pass


class MultipleIdError(Exception):
    pass


def authenticated(func):
    """
    Decorator to check if Smappee's access token has expired.
    If it has, use the refresh token to request a new access token
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        if not self.access_token:
            raise NotAuthenticatedError("Please authenticate first")
        return func(*args, **kwargs)
    return wrapper


class June:
    def __init__(self, access_token=None):
        self.access_token = access_token

    def authenticate(self, username, password):
        auth_url = URL + 'oauth/token'
        data = {
            "grant_type": "password",
            "username": username,
            "password": password
        }
        r = requests.post(auth_url, data)
        r.raise_for_status()
        j = r.json()
        self.access_token = j['access_token']

    @authenticated
    def get_contracts(self):
        contract_url = URL + 'contracts'
        headers = {"Authorization": "Bearer {}".format(self.access_token)}
        r = requests.get(contract_url, headers=headers)
        r.raise_for_status()
        return r.json()

    def get_ids(self):
        contracts = self.get_contracts()
        ids = [contract['id'] for contract in contracts['data']]
        return ids

    def get_id(self):
        ids = self.get_ids()
        if len(ids) == 1:
            return ids[0]
        else:
            raise MultipleIdError('0 or more than 1 ids, cannot return single Id')

    @authenticated
    def get_devices(self, id):
        devices_url = URL + 'devices/{}'.format(id)
        headers = {"Authorization": "Bearer {}".format(self.access_token)}
        r = requests.get(devices_url, headers=headers)
        r.raise_for_status()
        return r.json()
