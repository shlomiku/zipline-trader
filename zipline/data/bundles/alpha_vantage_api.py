"""
Data-Bundle for Aplhavantage
Usage: set api-key with 'export ALPHAVANTAGE_API_KEY=yourkey'
Limitations: free-accounts can have 5 calls per minute and 500 calls a day.
  tolerance is used to wait some small additional time, otherwise sometimes
  we will still hit the limit if we want to squeeze out as much calls as
  possible.
  In case you have a premium-subscription, you can tune these values by
  setting the env-vars AV_FREQ_SEC, AV_CALLS_PER_FREQ, and AV_TOLERANCE_SEC
  AV_FREQ_SEC - sets the base-frequency
  AV_CALLS_PER_FREQ - sets the amount of calls per base-frequency
  AV_TOLERANCE_SEC - the amount of seconds to add to the interval in case
      we're getting exceptions because of calling api too often
Adjustments: to enable a bigger precision on our backtests, i decided to
  go for unadjusted-prices and implemented an adjustment-writer to account
  for dividends and splits. However, only daily-data contains this information
  so it's really IMPORTANT that you never only request minute-data alone.
"""

import numpy as np
import pandas as pd

from alpha_vantage.timeseries import TimeSeries

from datetime import date, timedelta
from trading_calendars import TradingCalendar

from ratelimit import limits, sleep_and_retry

import config
from zipline.data.bundles import core as bundles
from zipline.data.bundles.universe import Universe, get_sp500, get_sp100, get_nasdaq100, all_alpaca_assets

from zipline.data import bundles as bundles_module
import trading_calendars
import os
import time

from zipline.errors import SymbolNotFound, SidsNotFound

av_config = config.bundle.AlphaVantage()
AV_FREQ_SEC = av_config.sample_frequency
AV_CALLS_PER_FREQ = av_config.max_calls_per_freq
AV_TOLERANCE_SEC = av_config.breathing_space
os.environ["ALPHAVANTAGE_API_KEY"] = av_config.api_key  # make sure it's set in env variable

UNIVERSE = Universe.NASDAQ100

ASSETS = None
def list_assets():
    global ASSETS
    if not ASSETS:
        custom_asset_list = av_config.av.get("custom_asset_list")
        if custom_asset_list:
            custom_asset_list = custom_asset_list.strip().replace(" ", "").split(",")
            ASSETS = list(set(custom_asset_list))
        else:
            try:
                universe = Universe[av_config.av["universe"]]
            except:
                universe = Universe.ALL
            if universe == Universe.ALL:
                # alpha vantage doesn't define a universe. we could try using alpaca's universe if the
                # user defined credentials. if not, we will raise an exception.
                try:
                    import zipline.data.bundles.alpaca_api as alpaca
                    alpaca.initialize_client()
                    ASSETS = all_alpaca_assets(alpaca.CLIENT)
                except:
                    raise Exception("You tried to use Universe.ALL but you didn't define the alpaca credentials.")
            elif universe == Universe.SP100:
                ASSETS = get_sp100()
            elif universe == Universe.SP500:
                ASSETS = get_sp500()
            elif universe == Universe.NASDAQ100:
                ASSETS = get_nasdaq100()
            ASSETS = list(set(ASSETS))
    return ASSETS


def fill_daily_gaps(df):
    """
    filling missing data. logic:
    1. get start date and end date from df. (caveat: if the missing dates are at the edges this will not work)
    2. use trading calendars to get all session dates between start and end
    3. use difference() to get only missing dates.
    4. add those dates to the original df with NaN
    5. dividends get 0 and split gets 1 (meaning no split happened)
    6. all the rest get ffill of the close value.
    7. volume get 0
    :param df:
    :return:
    """
    cal: TradingCalendar = trading_calendars.get_calendar('NYSE')
    sessions = cal.sessions_in_range(df.index[0], df.index[-1])

    if len(df.index) == len(sessions):
        return df

    to_fill = sessions.difference(df.index)
    df = df.append(pd.DataFrame(index=to_fill)).sort_index()

    # forward-fill these values regularly
    df.close.fillna(method='ffill', inplace=True)
    df.dividend.fillna(0, inplace=True)
    df.split.fillna(1, inplace=True)
    df.volume.fillna(0, inplace=True)
    df.open.fillna(df.close, inplace=True)
    df.high.fillna(df.close, inplace=True)
    df.low.fillna(df.close, inplace=True)
    df.adj_close.fillna(df.close, inplace=True)

    filled = len(to_fill)
    print(f'\nWarning! Filled {filled} empty values!')

    return df


@sleep_and_retry
@limits(calls=AV_CALLS_PER_FREQ, period=AV_FREQ_SEC + AV_TOLERANCE_SEC)
def av_api_wrapper(symbol, interval, _slice=None):
    """
    purpose of this function is to encapsulate both minute- and daily-requests in one
    function to be able to properly do rate-limiting.
    """
    if interval == '1m':
        ts = TimeSeries(output_format='csv')
        data_slice, meta_data = ts.get_intraday_extended(symbol, interval='1min', slice=_slice, adjusted='false')
        return data_slice

    else:
        ts = TimeSeries()
        data, meta_data = ts.get_daily_adjusted(symbol, outputsize='full')
        return data


def av_get_data_for_symbol(symbol, start, end, interval):
    if interval == '1m':
        data = []
        for i in range(1, 3):
            for j in range(1, 13):
                _slice = 'year' + str(i) + 'month' + str(j)
                # print('requesting slice ' + _slice + ' for ' + symbol)
                data_slice = av_api_wrapper(symbol, interval=interval, slice=_slice)

                # dont know better way to convert _csv.reader to list or DataFrame
                table = []
                for line in data_slice:
                    table.append(line)

                # strip header-row from csv
                table = table[1:]
                data = data + table

        df = pd.DataFrame(data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])

        df.index = pd.to_datetime(df['date'])
        df.index = df.index.tz_localize('UTC')
        df.drop(columns=['date'], inplace=True)

    else:
        data = av_api_wrapper(symbol, interval)

        df = pd.DataFrame.from_dict(data, orient='index')
        df.index = pd.to_datetime(df.index).tz_localize('UTC')

        df.rename(columns={
            '1. open': 'open',
            '2. high': 'high',
            '3. low': 'low',
            '4. close': 'close',
            '5. volume': 'volume',
            '5. adjusted close': 'adj_close',
            '6. volume': 'volume',
            '7. dividend amount': 'dividend',
            '8. split coefficient': 'split'
        }, inplace=True)

        # fill potential gaps in data
        df = fill_daily_gaps(df)

    df.sort_index(inplace=True)

    # data comes as strings
    df['open'] = pd.to_numeric(df['open'], downcast='float')
    df['high'] = pd.to_numeric(df['high'], downcast='float')
    df['low'] = pd.to_numeric(df['low'], downcast='float')
    df['close'] = pd.to_numeric(df['close'], downcast='float')
    df['volume'] = pd.to_numeric(df['volume'], downcast='unsigned')

    if 'adj_close' in df.columns:
        df['adj_close'] = pd.to_numeric(df['adj_close'], downcast='float')

    if 'dividend' in df.columns:
        df['dividend'] = pd.to_numeric(df['dividend'], downcast='float')

    if 'split' in df.columns:
        df['split'] = pd.to_numeric(df['split'], downcast='float')

    return df


def calc_split(sid, df):
    """
    collect all days where there were splits and calculate split-ratio
     by 1 / split-factor. save them together with effective-date.
    """
    # filter only dates where splits occur
    tmp = 1. / df[df['split'] != 1.0]['split']
    split = pd.DataFrame(data=tmp.index.tolist(),
                         columns=['effective_date'])
    split['ratio'] = tmp.tolist()
    split['sid'] = np.int(sid)

    split['effective_date'] = split['effective_date'].apply(lambda x: x.timestamp())

    return split


def calc_dividend(sid, df, sessions):
    """
    collect all dividends and the dates when they were issued,
    fill stuff we don't know with empty-values
    """
    tmp = df[df['dividend'] != 0.0]['dividend']
    div = pd.DataFrame(data=tmp.index.tolist(), columns=['ex_date'])

    # as we do not know these values, set something as done in csvdir
    # there it writes nats but in case of writing to postgres,
    # pd.NaT will exceed BigInt for some reason
    natValue = pd.to_datetime('1800-1-1')
    div['record_date'] = natValue
    div['declared_date'] = natValue

    # "guess" a dividend-pay-date 10 trading-days in the future
    div['pay_date'] = [sessions[sessions.get_loc(ex_date) + 10] for ex_date in div['ex_date']]

    div['amount'] = tmp.tolist()
    div['sid'] = np.int(sid)

    # convert to string and then back to datetime, otherwise pd.concat will fail
    div['ex_date'] = div['ex_date'].apply(lambda x: x.strftime('%Y-%m-%d 00:00:00'))
    div['pay_date'] = div['pay_date'].apply(lambda x: x.strftime('%Y-%m-%d 00:00:00'))

    return div


def df_generator(interval, start, end, divs_splits, assets_to_sids={}):
    exchange = 'NYSE'

    # get calendar and extend it to 20 days to the future to be able
    # to set dividend-pay-date to a valid session
    cal: TradingCalendar = trading_calendars.get_calendar('NYSE')
    sessions = cal.sessions_in_range(start, end + timedelta(days=20))

    asset_list = list_assets()

    for symbol in asset_list:
        try:
            df = av_get_data_for_symbol(symbol, start, end, interval)

            sid = assets_to_sids[symbol]

            first_traded = df.index[0]
            auto_close_date = df.index[-1] + pd.Timedelta(days=1)

            if 'split' in df.columns:
                split = calc_split(sid, df)
                divs_splits['splits'] = divs_splits['splits'].append(split)

            if 'dividend' in df.columns:
                div = calc_dividend(sid, df, sessions)
                divs_splits['divs'] = pd.concat([divs_splits['divs'], div])

            yield (sid, df), symbol, symbol, start, end, first_traded, auto_close_date, exchange

        except KeyboardInterrupt:
            exit()

        except Exception as e:
            # somehow rate-limiting does not work with exceptions, throttle manually
            if 'Thank you for using Alpha Vantage! Our standard API call frequency is' in str(e):
                print(f'\nGot rate-limit on remote-side, retrying symbol {symbol} later')
                asset_list.append(symbol)
            else:
                print(f'\nException for symbol {symbol}')
                print(e)


def metadata_df(assets_to_sids={}):
    metadata = []

    sids = [sid for _, sid in assets_to_sids.items()]

    metadata_dtype = [
        ('symbol', 'object'),
        ('asset_name', 'object'),
        ('start_date', 'datetime64[ns]'),
        ('end_date', 'datetime64[ns]'),
        ('first_traded', 'datetime64[ns]'),
        ('auto_close_date', 'datetime64[ns]'),
        ('exchange', 'object'), ]

    metadata_df = pd.DataFrame(
        np.empty(len(list_assets()), dtype=metadata_dtype))

    metadata_df.index = sids

    return metadata_df


@bundles.register('alpha_vantage', calendar_name="NYSE", minutes_per_day=390)
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

        divs_splits = {'divs': pd.DataFrame(columns=['sid', 'amount',
                                                     'ex_date', 'record_date',
                                                     'declared_date', 'pay_date']),
                       'splits': pd.DataFrame(columns=['sid', 'ratio',
                                                       'effective_date'])}

        assets_to_sids = asset_to_sid_map(asset_db_writer.asset_finder, list_assets())

        def minute_data_generator():
            return (sid_df for (sid_df, *metadata.iloc[sid_df[0]]) in
                    df_generator(
                        interval='1m',
                        start=start_session,
                        end=end_session,
                        assets_to_sids=assets_to_sids,
                        divs_splits=divs_splits))

        def daily_data_generator():
            return (sid_df for (sid_df, *metadata.loc[sid_df[0]])
                    in df_generator(
                interval='1d',
                start=start_session,
                end=end_session,
                assets_to_sids=assets_to_sids,
                divs_splits=divs_splits))

        metadata = metadata_df(assets_to_sids)

        assets = list_assets()
        for _interval in interval:
            if _interval == '1d':
                daily_bar_writer.write(daily_data_generator(), assets=assets_to_sids.values(), show_progress=True,
                                       invalid_data_behavior='raise')
            elif _interval == '1m':
                minute_bar_writer.write(minute_data_generator(), show_progress=True)

        metadata.dropna(inplace=True)
        asset_db_writer.write(equities=metadata)

        # convert back wrong datatypes after pd.concat
        divs_splits['splits']['sid'] = divs_splits['splits']['sid'].astype(np.int)
        divs_splits['divs']['sid'] = divs_splits['divs']['sid'].astype(np.int)
        divs_splits['divs']['ex_date'] = pd.to_datetime(divs_splits['divs']['ex_date'], utc=True)
        divs_splits['divs']['pay_date'] = pd.to_datetime(divs_splits['divs']['pay_date'], utc=True)

        adjustment_writer.write(splits=divs_splits['splits'], dividends=divs_splits['divs'])

        # Drop the ticker rows which have missing sessions in their data sets

        print(metadata)

    return ingest


def asset_to_sid_map(asset_finder, symbols):
    assets_to_sids = {}

    if asset_finder:
        next_free_sid = asset_finder.get_max_sid() + 1
        for symbol in symbols:
            try:
                asset = asset_finder.lookup_symbol(symbol, pd.Timestamp(date.today(), tz='UTC'))
                assets_to_sids[symbol] = int(asset)
            except (SymbolNotFound, SidsNotFound) as e:
                assets_to_sids[symbol] = next_free_sid
                next_free_sid = next_free_sid + 1

        return assets_to_sids

    for i in range(len(symbols)):
        assets_to_sids[symbols[i]] = i

    return assets_to_sids


if __name__ == '__main__':
    from zipline.data.bundles import register

    cal: TradingCalendar = trading_calendars.get_calendar('NYSE')

    # alpha-vantage has a fixed time-window, no point in changing these
    start_date = pd.Timestamp('1999-11-1', tz='utc')
    end_date = pd.Timestamp(date.today() - timedelta(days=1), tz='utc')

    while not cal.is_session(end_date):
        end_date -= timedelta(days=1)

    print('ingesting alpha_vantage-data from: ' + str(start_date) + ' to: ' + str(end_date))

    start_time = time.time()

    register(
        'alpha_vantage',
        # api_to_bundle(interval=['1d', '1m']),
        # api_to_bundle(interval=['1m']),
        api_to_bundle(interval=['1d']),
        calendar_name='NYSE',
        start_session=start_date,
        end_session=end_date
    )

    assets_version = ((),)[0]  # just a weird way to create an empty tuple
    bundles_module.ingest(
        "alpha_vantage",
        os.environ,
        assets_versions=assets_version,
        show_progress=True,
    )

    print("--- %s seconds ---" % (time.time() - start_time))
