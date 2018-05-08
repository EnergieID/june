"""
API Docs:
https://documenter.getpostman.com/view/2978056/june-api-doc/71FUpcH
"""

import requests
import functools
import datetime as dt
import pytz
import dateutil.parser

__title__ = "june"
__version__ = "0.1.5"
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
    @functools.wraps(func)
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

    @functools.lru_cache(maxsize=128, typed=False)
    @authenticated
    def get_clients(self):
        """
        Request cllients from API

        Returns
        -------
        dict
        """
        client_url = URL + 'clients'
        headers = {"Authorization": "Bearer {}".format(self.access_token)}
        r = requests.get(client_url, headers=headers)
        r.raise_for_status()
        return r.json()

    def get_client_ids(self):
        """
        Get a list of all client ids

        Returns
        -------
        [int]
        """
        clients = self.get_clients()
        ids = [client['id'] for client in clients['data']]
        return ids

    @functools.lru_cache(maxsize=128, typed=False)
    @authenticated
    def get_devices(self, client_id):
        """
        Request devices from API

        Parameters
        ----------
        client_id : int

        Returns
        -------
        dict
        """
        devices_url = URL + 'contracts/{}/devices'.format(client_id)
        headers = {"Authorization": "Bearer {}".format(self.access_token)}
        r = requests.get(devices_url, headers=headers)
        r.raise_for_status()
        return r.json()

    @functools.lru_cache(maxsize=128, typed=False)
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
        if len(datapoints) == 0:
            return pd.DataFrame()
        df = pd.DataFrame.from_records(datapoints)
        df['start'] = pd.DatetimeIndex(df['start'])
        df = df.set_index('start')
        df = df.tz_localize('UTC')
        # cast the numerical columns to float
        for column in df.columns ^ {'filled', 'last_image', 'period'}:
            df[column] = df[column].astype(float)
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

    def get_start_end(self, client_id, device_id):
        """
        Get the start and end time of the available data for a device

        Parameters
        ----------
        client_id : int
        device_id : int

        Returns
        -------
        dt.datetime, dt.datetime
        """
        devices = self.get_devices(client_id=client_id)
        for device in devices['data']:
            if device['id'] == device_id:
                start = dateutil.parser.parse(device['attributes']['created_at'])
                end = dateutil.parser.parse(device['attributes']['last_image_date'])
                return start, end
        else:
            return None, None
