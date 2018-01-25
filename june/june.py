"""
API Docs:
https://documenter.getpostman.com/view/2978056/june-api-doc/71FUpcH
"""

import requests
from functools import wraps
import datetime as dt
import pytz
import dateutil.parser

__title__ = "june"
__version__ = "0.1.0"
__author__ = "EnergieID.be"
__license__ = "MIT"

URL = 'https://api-portal.june.energy/'


class NotAuthenticatedError(Exception):
    pass


def authenticated(func):
    """
    Decorator to check if your access token is set.
    If it isn't, throw an error
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
        """
        Parameters
        ----------
        access_token : str
        """
        self.access_token = access_token

    def authenticate(self, username, password):
        """
        Parameters
        ----------
        username : str
        password : str
        """
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
        """
        Request contracts from API

        Returns
        -------
        dict
        """
        contract_url = URL + 'contracts'
        headers = {"Authorization": "Bearer {}".format(self.access_token)}
        r = requests.get(contract_url, headers=headers)
        r.raise_for_status()
        return r.json()

    def get_contract_ids(self):
        """
        Get a list of all contract ids

        Returns
        -------
        [int]
        """
        contracts = self.get_contracts()
        ids = [contract['id'] for contract in contracts['data']]
        return ids

    @authenticated
    def get_devices(self, contract_id):
        """
        Request devices from API

        Parameters
        ----------
        contract_id : int

        Returns
        -------
        dict
        """
        devices_url = URL + 'contracts/{}/devices'.format(contract_id)
        headers = {"Authorization": "Bearer {}".format(self.access_token)}
        r = requests.get(devices_url, headers=headers)
        r.raise_for_status()
        return r.json()

    @authenticated
    def get_measurements(self, device_id, period, start, end):
        """
        Request measurements from API

        Parameters
        ----------
        device_id : int
        period : int
            PERIOD_DAILY = 0
            PERIOD_WEEKLY = 1
            PERIOD_MONTHLY = 2
            PERIOD_YEARLY = 3
        start : str | dt.date | dt.datetime
        end : str | dt.date | dt.datetime

        Returns
        -------
        dict
        """
        measurements_url = URL + 'devices/{}/measures'.format(device_id)
        params = {
            'filter[period]': period,
            'filter[start]': self._to_date(start),
            'filter[end]': self._to_date(end)
        }
        headers = {"Authorization": "Bearer {}".format(self.access_token)}
        r = requests.get(measurements_url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()

    def get_measurements_dataframe(self, device_id, period, start, end):
        """
        Get measurements as a Pandas DataFrame

        Parameters
        ----------
        device_id : int
        period : int
            PERIOD_DAILY = 0
            PERIOD_WEEKLY = 1
            PERIOD_MONTHLY = 2
            PERIOD_YEARLY = 3
        start : str | dt.date | dt.datetime
        end : str | dt.date | dt.datetime

        Returns
        -------
        pd.DataFrame
        """
        import pandas as pd
        measurements = self.get_measurements(device_id=device_id, period=period, start=start, end=end)
        datapoints = [point['attributes'] for point in measurements['data']]
        df = pd.DataFrame.from_records(datapoints)
        df.start = pd.DatetimeIndex(df.start)
        df = df.set_index('start')
        return df

    @staticmethod
    def _to_date(date_obj):
        """
        Convert any input to a valid datestring of form yyyy-mm-dd
        If you pass a localized datetime, it is converted to UTC first

        Parameters
        ----------
        date_obj : str | dt.date | dt.datetime

        Returns
        -------
        str
        """
        fmt = '%Y-%m-%d'
        if isinstance(date_obj, str):
            try:
                dt.datetime.strptime(date_obj, fmt)
            except ValueError as e:
                raise e
            else:
                return date_obj
        elif hasattr(date_obj, 'tzinfo') and date_obj.tzinfo is not None:
            date_obj = date_obj.astimezone(pytz.UTC)

        return date_obj.strftime(fmt)

    def get_start_end(self, contract_id, device_id):
        """
        Get the start and end time of the available data for a device

        Parameters
        ----------
        contract_id : int
        device_id : int

        Returns
        -------
        dt.datetime, dt.datetime
        """
        devices = self.get_devices(contract_id=contract_id)
        for device in devices['data']:
            if device['id'] == device_id:
                start = dateutil.parser.parse(device['attributes']['created_at'])
                end = dateutil.parser.parse(device['attributes']['last_image_date'])
                return start, end
        else:
            return None, None