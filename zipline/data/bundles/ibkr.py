import collections

from datetime import datetime, timedelta, time as dtime
import numpy as np
import pandas as pd
import pickle
import pytz
from dateutil import tz
from trading_calendars import TradingCalendar
from zipline.data.bundles import core as bundles
from dateutil.parser import parse as date_parse
from ib_insync import *

CLIENT: IB = None

def initialize_client():
    global CLIENT
    CLIENT = IB()
    CLIENT.connect('172.17.0.1', 4002, clientId=1)

def list_assets():
    #return ["AAPL","AXP","BA","CAT","CSCO","CVX","DD","DIS","GE","GS","HD","IBM","INTC","JNJ","JPM","KO","MCD","MMM","MRK","MSFT","NKE","PFE","PG","TRV","UNH","V","VZ","WMT","XOM"]
    return ['AAPL']

def ib_get_data_for_symbol(symbol, start, end, interval):
    cal = trading_calendars.get_calendar('NYSE')
    sessions = cal.sessions_in_range(start, end)
    
    duration_days = str(len(sessions))
    bar_size = '1 day' if interval == '1d' else '1 min'

    contract = Stock(symbol='AAPL', exchange='SMART', currency='USD')
    
    # https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_request
    # TRADES data is adjusted for splits, but not dividends (does not support end-date)
    # ADJUSTED_LAST data is adjusted for splits and dividends. Requires TWS 967+
    bars = CLIENT.reqHistoricalData(contract, endDateTime=end.strftime('%Y%m%d 23:59:59'), durationStr=duration_days + ' D',
              barSizeSetting=bar_size, whatToShow='TRADES', useRTH=False)

    df = util.df(bars)
    df.index = pd.to_datetime(df['date'])
    df.index = df.index.tz_localize('UTC')
    df.drop(['date', 'average', 'barCount'], axis=1, inplace=True)
    
    return df.sort_index()
         
def df_generator(interval, start, end):
    exchange = 'NYSE'
    asset_list = list_assets()
    sid = 0

    for symbol in asset_list:
      df = ib_get_data_for_symbol(symbol, start, end, interval)

      first_traded = df.index[0]
      auto_close_date = df.index[-1:][0] + pd.Timedelta(days=1)

      yield (sid, df), symbol, start, end, first_traded, auto_close_date, exchange
      sid = sid + 1

def metadata_df():
    metadata_dtype = [
        ('symbol', 'object'),
        # ('asset_name', 'object'),
        ('start_date', 'datetime64[ns]'),
        ('end_date', 'datetime64[ns]'),
        ('first_traded', 'datetime64[ns]'),
        ('auto_close_date', 'datetime64[ns]'),
        ('exchange', 'object'), ]
    metadata_df = pd.DataFrame(
        np.empty(len(list_assets()), dtype=metadata_dtype))

    return metadata_df


@bundles.register('ibkr', calendar_name="NYSE", minutes_per_day=390)
def api_to_bundle(interval=['1m']):
    def ingest(environ,
               asset_db_writer,
               minute_bar_writer,
               daily_bar_writer,
               adjustment_writer,
               calendar,
               start_session,
               end_session,
               cache,
               show_progress,
               output_dir
               ):


        def minute_data_generator():
            return (sid_df for (sid_df, *metadata.iloc[sid_df[0]]) in df_generator(interval='1m',
                                                                                   start=start_session,
                                                                                   end=end_session))

        def daily_data_generator():
            return (sid_df for (sid_df, *metadata.iloc[sid_df[0]]) in df_generator(interval='1d',
                                                                                   start=start_session,
                                                                                   end=end_session))
        for _interval in interval:
            metadata = metadata_df()
            if _interval == '1d':
                daily_bar_writer.write(daily_data_generator(), show_progress=True)
            elif _interval == '1m':
                minute_bar_writer.write(minute_data_generator(), show_progress=True)

            # Drop the ticker rows which have missing sessions in their data sets
            metadata.dropna(inplace=True)

            asset_db_writer.write(equities=metadata)
            print(metadata)
            adjustment_writer.write()

    return ingest


if __name__ == '__main__':
    from zipline.data.bundles import register
    from zipline.data import bundles as bundles_module
    import trading_calendars
    import os
    import time

    cal: TradingCalendar = trading_calendars.get_calendar('NYSE')

    end_date = pd.Timestamp('now', tz='utc').date() - timedelta(days=1)
    while not cal.is_session(end_date):
        end_date -= timedelta(days=1)
    end_date = pd.Timestamp(end_date, tz='utc')

    start_date = end_date - timedelta(days=30)
    while not cal.is_session(start_date):
        start_date -= timedelta(days=1)

    print('ingesting ibkr-data from: ' + str(start_date) + ' to: ' + str(end_date))

    initialize_client()

    start_time = time.time()

    register(
        'ibkr',
        #api_to_bundle(interval=['1d', '1m']),
        api_to_bundle(interval=['1m']),
        #api_to_bundle(interval=['1d']),
        calendar_name='NYSE',
        start_session=start_date,
        end_session=end_date
    )

    assets_version = ((),)[0]  # just a weird way to create an empty tuple
    bundles_module.ingest(
        "ibkr",
        os.environ,
        assets_versions=assets_version,
        show_progress=True,
    )

    print("--- %s seconds ---" % (time.time() - start_time))
