# Copyright 2015 Quantopian, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from functools import partial

import psycopg2
import sqlalchemy as sa

import config.data_backend
from zipline.utils.db_utils import check_and_create_engine
import pandas as pd

import logbook
import numpy as np
from numpy import (
    iinfo,
    nan,
)
from pandas import (
    NaT,
    read_csv,
    to_datetime,
    Timestamp,
)
from six import iteritems, viewkeys
from trading_calendars import get_calendar

from zipline.data.session_bars import CurrencyAwareSessionBarReader
from zipline.data.bar_reader import (
    NoDataAfterDate,
    NoDataBeforeDate,
    NoDataOnDate,
)
from zipline.utils.functional import apply
from zipline.utils.input_validation import expect_element
from zipline.utils.numpy_utils import iNaT, float64_dtype, uint32_dtype
from zipline.utils.memoize import lazyval
from zipline.utils.cli import maybe_show_progress
from ._equities import _compute_row_slices, _read_tape_data

logger = logbook.Logger('PSqlDailyBars')

OHLC = frozenset(['open', 'high', 'low', 'close'])
US_EQUITY_PRICING_COLUMNS = (
    'open', 'high', 'low', 'close', 'volume', 'day', 'id'
)

UINT32_MAX = iinfo(np.uint32).max

TABLE = 'ohlcv_daily'


class PSQLDailyBarReader(CurrencyAwareSessionBarReader):
    """
    Reader for raw pricing data written by PSQLDailyBarWriter.

    Parameters
    ----------
    table : bcolz.ctable
        The ctable contaning the pricing data, with attrs corresponding to the
        Attributes list below.
    read_all_threshold : int
        The number of equities at which; below, the data is read by reading a
        slice from the carray per asset.  above, the data is read by pulling
        all of the data for all assets into memory and then indexing into that
        array for each day and asset pair.  Used to tune performance of reads
        when using a small or large number of equities.

    Attributes
    ----------
    The table with which this loader interacts contains the following
    attributes:

    first_row : dict
        Map from asset_id -> index of first row in the dataset with that id.
    last_row : dict
        Map from asset_id -> index of last row in the dataset with that id.
    calendar_offset : dict
        Map from asset_id -> calendar index of first row.
    start_session_ns: int
        Epoch ns of the first session used in this dataset.
    end_session_ns: int
        Epoch ns of the last session used in this dataset.
    calendar_name: str
        String identifier of trading calendar used (ie, "NYSE").

    We use first_row and last_row together to quickly find ranges of rows to
    load when reading an asset's data into memory.

    We use calendar_offset and calendar to orient loaded blocks within a
    range of queried dates.

    Notes
    ------
    A Bcolz CTable is comprised of Columns and Attributes.
    The table with which this loader interacts contains the following columns:

    ['open', 'high', 'low', 'close', 'volume', 'day', 'id'].

    The data in these columns is interpreted as follows:

    - Price columns ('open', 'high', 'low', 'close') are interpreted as 1000 *
      as-traded dollar value.
    - Volume is interpreted as as-traded volume.
    - Day is interpreted as seconds since midnight UTC, Jan 1, 1970.
    - Id is the asset id of the row.

    The data in each column is grouped by asset and then sorted by day within
    each asset block.

    The table is built to represent a long time range of data, e.g. ten years
    of equity data, so the lengths of each asset block is not equal to each
    other. The blocks are clipped to the known start and end date of each asset
    to cut down on the number of empty values that would need to be included to
    make a regular/cubic dataset.

    When read across the open, high, low, close, and volume with the same
    index should represent the same asset and day.

    See Also
    --------
    zipline.data.bcolz_daily_bars.BcolzDailyBarWriter
    """

    def __init__(self, path, read_all_threshold=3000):
        self.conn = check_and_create_engine(path, False)

        # Cache of fully read np.array for the carrays in the daily bar table.
        # raw_array does not use the same cache, but it could.
        # Need to test keeping the entire array in memory for the course of a
        # process first.
        self._spot_cols = {}
        self._read_all_threshold = read_all_threshold

        # caching the calendar-sessions like this prevent problems during ingestion
        # where the reader is first initialized when there are still no bars
        self._sessions = pd.DatetimeIndex([], dtype='datetime64[ns, UTC]', freq='C')

        self._calendar_offsets_c = {}
        self._first_rows_c = {}
        self._last_rows_c = {}
        self._first_trading_day_c = {}

    @property
    def sessions(self):
        if self._sessions.empty:
            outer_dates = pd.read_sql('SELECT MIN(day) as min_day, MAX(day) as max_day FROM ohlcv_daily', self.conn)

            start_session = Timestamp(outer_dates['min_day'][0], tz='UTC')
            end_session = Timestamp(outer_dates['max_day'][0], tz='UTC')

            calendar_name = 'XNYS'  # NYSE for POC only
            cal = get_calendar(calendar_name)

            self._sessions = cal.sessions_in_range(start_session, end_session)

        return self._sessions

    @lazyval
    def first_trading_day(self):
        return Timestamp(
            self._first_trading_day,
            unit='s',
            tz='UTC'
        )

    @lazyval
    def trading_calendar(self):
        return get_calendar('XNYS')

    @property
    def last_available_dt(self):
        return self.sessions[-1]

    @property
    def _calendar_offsets(self):
        if not self._calendar_offsets_c:
            self._calendar_offsets_c = self._get_calendar_offsets()
        return self._calendar_offsets_c

    def _get_calendar_offsets(self):
        info = pd.read_sql('SELECT id, MIN(day) AS start FROM ohlcv_daily GROUP BY id ORDER BY id', self.conn)

        sessions = self.sessions
        if len(sessions) == 0:
            return {}

        offsets = {}

        for i in range(len(info['id'])):
            first_session = Timestamp(info['start'][i], tz='UTC')
            offsets[info['id'][i]] = sessions.get_loc(first_session)

        return offsets

    @property
    def _first_trading_day(self):
        if not self._first_trading_day_c:
            self._first_trading_day_c = self._get_first_trading_day()
        return self._first_trading_day_c

    @property
    def _last_rows(self):
        if not self._last_rows_c:
            self._first_rows_c, self._last_rows_c = self._get_first_and_last_rows()
        return self._last_rows_c

    @property
    def _first_rows(self):
        if not self._first_rows_c:
            self._first_rows_c, self._last_rows_c = self._get_first_and_last_rows()
        return self._first_rows_c

    def _get_first_and_last_rows(self):
        info = pd.read_sql('SELECT id, COUNT(day) AS ct FROM ohlcv_daily GROUP BY id ORDER BY id', self.conn)

        first_rows = {}
        last_rows = {}
        total = 0
        length = len(info['id'])

        for i in range(length):
            total = total + info['ct'][i]

            if i == 0:
                first_rows[info['id'][i]] = 0
            last_rows[info['id'][i]] = total - 1
            if i > 0:
                first_rows[info['id'][i]] = last_rows[last_id] + 1

            last_id = info['id'][i]

        return first_rows, last_rows

    def _get_first_trading_day(self):
        result = pd.read_sql('SELECT MIN(day) AS first_day FROM ohlcv_daily', self.conn)
        return result.first_day.iloc[0]

    def _compute_slices(self, start_idx, end_idx, assets):
        """
        Compute the raw row indices to load for each asset on a query for the
        given dates after applying a shift.

        Parameters
        ----------
        start_idx : int
            Index of first date for which we want data.
        end_idx : int
            Index of last date for which we want data.
        assets : pandas.Int64Index
            Assets for which we want to compute row indices

        Returns
        -------
        A 3-tuple of (first_rows, last_rows, offsets):
        first_rows : np.array[intp]
            Array with length == len(assets) containing the index of the first
            row to load for each asset in `assets`.
        last_rows : np.array[intp]
            Array with length == len(assets) containing the index of the last
            row to load for each asset in `assets`.
        offset : np.array[intp]
            Array with length == (len(asset) containing the index in a buffer
            of length `dates` corresponding to the first row of each asset.

            The value of offset[i] will be 0 if asset[i] existed at the start
            of a query.  Otherwise, offset[i] will be equal to the number of
            entries in `dates` for which the asset did not yet exist.
        """
        # The core implementation of the logic here is implemented in Cython
        # for efficiency.
        return _compute_row_slices(
            self._first_rows,
            self._last_rows,
            self._calendar_offsets,
            start_idx,
            end_idx,
            assets,
        )

    def _load_raw_arrays_date_to_index(self, date):
        try:
            return self.sessions.get_loc(date)
        except KeyError:
            raise NoDataOnDate(date)

    def load_raw_arrays(self, columns, start_date, end_date, assets):
        for col in columns:
            self._spot_col(col)

        start_idx = self._load_raw_arrays_date_to_index(start_date)
        end_idx = self._load_raw_arrays_date_to_index(end_date)

        first_rows, last_rows, offsets = self._compute_slices(
            start_idx,
            end_idx,
            assets,
        )

        read_all = len(assets) > self._read_all_threshold
        tape = _read_tape_data(
            self._spot_cols,
            (end_idx - start_idx + 1, len(assets)),
            list(columns),
            first_rows,
            last_rows,
            offsets,
            read_all,
        )

        return tape

    def load_raw_arrays_slow(self, columns, start_date, end_date, assets):
        result = []

        sessions = self.sessions[self.sessions.get_loc(start_date): self.sessions.get_loc(end_date) + 1]

        for column in columns:
            column_vals = []

            for session in sessions:
                row_vals = []
                for asset in assets:
                    try:
                        row_vals.append(self.get_value(int(asset), session, column))
                    except NoDataBeforeDate:
                        row_vals.append(np.nan)

                column_vals.append(row_vals)

            result.append(np.array(column_vals))

        return result

    def _spot_col(self, colname):
        """
        Get the colname from daily_bar_table and read all of it into memory,
        caching the result.

        Parameters
        ----------
        colname : string
            A name of a OHLCV carray in the daily_bar_table

        Returns
        -------
        array (uint32)
            Full read array of the carray in the daily_bar_table with the
            given colname.
        """
        try:
            col = self._spot_cols[colname]
        except KeyError:
            result = pd.read_sql(f'SELECT {colname} FROM ohlcv_daily ORDER BY id, day', self.conn)[colname].values
            col = self._spot_cols[colname] = np.array(result)
        return col

    def get_last_traded_dt(self, asset, day):
        volumes = self._spot_col('volume')

        search_day = day

        while True:
            try:
                ix = self.sid_day_index(asset, search_day)
            except NoDataBeforeDate:
                return NaT
            except NoDataAfterDate:
                prev_day_ix = self.sessions.get_loc(search_day) - 1
                if prev_day_ix > -1:
                    search_day = self.sessions[prev_day_ix]
                continue
            except NoDataOnDate:
                return NaT
            if volumes[ix] != 0:
                return search_day
            prev_day_ix = self.sessions.get_loc(search_day) - 1
            if prev_day_ix > -1:
                search_day = self.sessions[prev_day_ix]
            else:
                return NaT

    def sid_day_index(self, sid, day):
        """
        all data for all assets is stored sequentially. to get the right values we must find the index
        for this sid and this day. so we calculate the offset in this long array.
        Parameters
        ----------
        sid : int
            The asset identifier.
        day : datetime64-like
            Midnight of the day for which data is requested.

        Returns
        -------
        int
            Index into the data tape for the given sid and day.
            Raises a NoDataOnDate exception if the given day and sid is before
            or after the date range of the equity.
        """
        try:
            day_loc = self.sessions.get_loc(day)
        except Exception:
            raise NoDataOnDate("day={0} is outside of calendar={1}".format(
                day, self.sessions))
        offset = day_loc - self._calendar_offsets[sid]
        if offset < 0:
            raise NoDataBeforeDate(
                "No data on or before day={0} for sid={1}".format(
                    day, sid))
        ix = self._first_rows[sid] + offset
        if ix > self._last_rows[sid]:
            raise NoDataAfterDate(
                "No data on or after day={0} for sid={1}".format(
                    day, sid))

        return ix

    def get_value(self, sid, dt, field):
        """
        Parameters
        ----------
        sid : int
            The asset identifier.
        day : datetime64-like
            Midnight of the day for which data is requested.
        colname : string
            The price field. e.g. ('open', 'high', 'low', 'close', 'volume')

        Returns
        -------
        float
            The spot price for colname of the given sid on the given day.
            Raises a NoDataOnDate exception if the given day and sid is before
            or after the date range of the equity.
            Returns -1 if the day is within the date range, but the price is
            0.
        """
        ix = self.sid_day_index(sid, dt)

        price = self._spot_col(field)[ix]
        if field != 'volume':
            if price == 0:
                return nan
            else:
                return price
        else:
            return price

    def currency_codes(self, sids):
        # XXX: This is pretty inefficient. This reader doesn't really support
        # country codes, so we always either return USD or None if we don't
        # know about the sid at all.
        first_rows = self._first_rows
        out = []
        for sid in sids:
            if sid in first_rows:
                out.append('USD')
            else:
                out.append(None)
        return np.array(out, dtype=object)


class PSQLDailyBarWriter(object):
    """
    Class capable of writing daily OHLCV data to disk in a format that can
    be read efficiently by PSQLDailyOHLCVReader.

    Parameters
    ----------
    filename : str
        The location at which we should write our output.
    calendar : zipline.utils.calendar.trading_calendar
        Calendar to use to compute asset calendar offsets.
    start_session: pd.Timestamp
        Midnight UTC session label.
    end_session: pd.Timestamp
        Midnight UTC session label.

    See Also
    --------
    zipline.data.bcolz_daily_bars.BcolzDailyBarReader
    """
    _csv_dtypes = {
        'open': float64_dtype,
        'high': float64_dtype,
        'low': float64_dtype,
        'close': float64_dtype,
        'volume': float64_dtype,
    }

    def __init__(self, db_path, calendar, start_session, end_session):
        self.conn = check_and_create_engine(db_path, False)

        if start_session != end_session:
            if not calendar.is_session(start_session):
                raise ValueError(
                    "Start session %s is invalid!" % start_session
                )
            if not calendar.is_session(end_session):
                raise ValueError(
                    "End session %s is invalid!" % end_session
                )

        self._start_session = start_session
        self._end_session = end_session
        self._calendar = calendar

        try:
            self.conn.connect()
        except sa.exc.OperationalError:
            # can't connect to db. might mean that the database is not created yey.
            # let's create it. (happens in first time usage)
            self.ensure_database(db_path)

        self.ensure_table()

    def ensure_database(self, db_path):
        """
        create the bundle database. it will have the name of the bundle
        :param db_path: expected db path (table). used to get the bundle name.
        """
        db_config = config.data_backend.PostgresDB()
        host = db_config.host
        port = db_config.port
        user = db_config.user
        password = db_config.password
        conn = psycopg2.connect(
            database="",
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.autocommit = True
        # Creating a cursor object using the cursor() method
        cursor = conn.cursor()
        bundle_name = db_path.split("/")[-1]
        sql = f'CREATE database {bundle_name}'
        # Creating a database
        cursor.execute(sql)
        print(f"Database {bundle_name} created successfully........")

    def ensure_table(self):
        metadata = sa.MetaData()

        ohlcv_daily = sa.Table(
            'ohlcv_daily',
            metadata,
            sa.Column('id', sa.Integer()),
            sa.Column('day', sa.Date()),
            sa.Column('open', sa.Float()),
            sa.Column('high', sa.Float()),
            sa.Column('low', sa.Float()),
            sa.Column('close', sa.Float()),
            sa.Column('volume', sa.BigInteger()),
        )

        sa.Index('id_day', ohlcv_daily.c.id, ohlcv_daily.c.day)

        metadata.create_all(self.conn)

    @property
    def progress_bar_message(self):
        return "Merging daily equity files:"

    def progress_bar_item_show_func(self, value):
        return value if value is None else str(value[0])

    def write(self,
              data,
              assets=None,
              show_progress=False,
              invalid_data_behavior='warn'):
        """
        Parameters
        ----------
        data : iterable[tuple[int, pandas.DataFrame or bcolz.ctable]]
            The data chunks to write. Each chunk should be a tuple of sid
            and the data for that asset.
        assets : set[int], optional
            The assets that should be in ``data``. If this is provided
            we will check ``data`` against the assets and provide better
            progress information.
        show_progress : bool, optional
            Whether or not to show a progress bar while writing.
        invalid_data_behavior : {'warn', 'raise', 'ignore'}, optional
            What to do when data is encountered that is outside the range of
            a uint32.

        Returns
        -------
        table : bcolz.ctable
            The newly-written table.
        """
        ctx = maybe_show_progress(
            (
                (sid, self._write_to_postgres(sid, df, invalid_data_behavior))
                for sid, df in data
            ),
            show_progress=show_progress,
            item_show_func=self.progress_bar_item_show_func,
            label=self.progress_bar_message,
            length=len(assets) if assets is not None else None,
        )
        with ctx as it:
            return self._write_internal(it, assets)

    def write_csvs(self,
                   asset_map,
                   show_progress=False,
                   invalid_data_behavior='warn'):
        """Read CSVs as DataFrames from our asset map.

        Parameters
        ----------
        asset_map : dict[int -> str]
            A mapping from asset id to file path with the CSV data for that
            asset
        show_progress : bool
            Whether or not to show a progress bar while writing.
        invalid_data_behavior : {'warn', 'raise', 'ignore'}
            What to do when data is encountered that is outside the range of
            a uint32.
        """
        read = partial(
            read_csv,
            parse_dates=['day'],
            index_col='day',
            dtype=self._csv_dtypes,
        )
        return self.write(
            ((asset, read(path)) for asset, path in iteritems(asset_map)),
            assets=viewkeys(asset_map),
            show_progress=show_progress,
            invalid_data_behavior=invalid_data_behavior,
        )

    def _write_internal(self, iterator, assets):
        """
        Internal implementation of write.

        `iterator` should be an iterator yielding pairs of (asset, dataframe).
        """
        if assets is not None:
            @apply
            def iterator(iterator=iterator, assets=set(assets)):
                for asset_id, table in iterator:
                    if asset_id not in assets:
                        logger.warning(f"unknown asset id {asset_id}. skipping.")
                        continue

                    yield asset_id, table

        for asset_id, table in iterator:
            # when writing to db, drop timezone, will crash otherwise
            if not table.empty:
                table.index = table.index.tz_localize(None)
                table.to_sql('ohlcv_daily', self.conn, if_exists='append')

    def _ensure_sessions_consistency(self, data_slice, invalid_data_behavior):
        """
        check that we have exactly the amount of days we expect by checking the start and end dates
        counting the active days in between using the trading calendar data
        """
        val = True

        if not data_slice.empty:

            first_day = data_slice.index[0]
            last_day = data_slice.index[-1]

            asset_sessions = self._calendar.sessions_in_range(first_day, last_day)
            if len(data_slice) != len(asset_sessions):
                err_msg = (
                    'Got {} rows for daily bars table with first day={}, last '
                    'day={}, expected {} rows.\n'
                    'Missing sessions: {}\n'
                    'Extra sessions: {}'.format(
                        len(data_slice),
                        first_day,
                        last_day,
                        len(asset_sessions),
                        asset_sessions.difference(
                            to_datetime(
                                np.array(data_slice.index),
                                unit='s',
                                utc=True,
                            )
                        ).tolist(),
                        to_datetime(
                            np.array(data_slice.index),
                            unit='s',
                            utc=True,
                        ).difference(asset_sessions).tolist(),
                    )
                )
                val = False
                logger.warning(err_msg)

        return val

    @expect_element(invalid_data_behavior={'warn', 'raise', 'ignore'})
    def _write_to_postgres(self, sid, data, invalid_data_behavior):

        result = self._format_df_columns_and_index(data, sid)
        if not result.empty:
            # set proper id
            data['id'] = sid

            edge_days = self._get_exisiting_data_dates_from_db(sid)

            if not self._data_for_sid_already_exist_in_db(edge_days):
                # this asset is still not in the DB. we write everything we got
                if self._ensure_sessions_consistency(data, invalid_data_behavior):
                    # data is not consistent. we will not write anything to db
                    result = data
                else:
                    result = pd.DataFrame(columns=data.columns)
            else:
                result = self._validate_data_consistency_on_edges(sid, data, edge_days, invalid_data_behavior)

        return result

    def _validate_data_consistency_on_edges(self, sid, data, edge_days, invalid_data_behavior):
        """
        there's already data in the db for this sid. we may append data at the beginning and/or end.
        before we do that, we must make sure that both segments are consistent.
        note: we could make a better effort by loosing up restriction and if one segment is corrupted still accept
              the other one.
        """
        first_day = edge_days['first_day'][0]
        last_day = edge_days['last_day'][0]
        before_slice = data[data.index < first_day]
        after_slice = data[data.index > last_day]
        # check if before-slice and after-slice are aligned with data in db
        # e.g. don't allow gaps in terms of sessions. should be exactly two
        # sessions (sessions on the edge of the data and the slice)
        consistent_data = True
        if not before_slice.empty:
            backward_gap = len(self._calendar.sessions_in_range(before_slice.index[-1], first_day))
            if backward_gap != 2:
                # max allowed gap for consistent data is 2
                logger.warning(f"data for {sid} contains backward gaps {backward_gap} "
                               f"and not consistent. will not be written to db.")
                consistent_data = False
        if not after_slice.empty:
            forward_gap = len(self._calendar.sessions_in_range(last_day, after_slice.index[-1]))
            if forward_gap != 2:
                logger.warning(f"data for {sid} contains forward gaps {forward_gap} "
                               f"and not consistent. will not be written to db.")
                consistent_data = False
        if not self._ensure_sessions_consistency(before_slice, invalid_data_behavior) or not \
                self._ensure_sessions_consistency(after_slice, invalid_data_behavior):
            consistent_data = False
        if consistent_data:
            result = before_slice.append(after_slice)
        else:
            result = pd.DataFrame(columns=data.columns)
        return result

    def _data_for_sid_already_exist_in_db(self, edges: pd.DataFrame) -> bool:
        """
        edges is a query performed for sid in db. if it's empty it means the db doesn't contain data for this sid yet.
        :return: bool
        """
        return not pd.isnull(edges['first_day'].iloc[0])

    def _get_exisiting_data_dates_from_db(self, sid):
        """
        using the sid- query the db and get the dates (start and end) for data stored in db
        :param sid:
        :return:
        """
        edge_days = pd.read_sql(
            f'SELECT MAX(day) as last_day, MIN(day) as first_day '
            f'FROM ohlcv_daily WHERE id = {sid}',
            self.conn,
            parse_dates=['last_day', 'first_day']
        )
        return edge_days

    def _format_df_columns_and_index(self, data, sid):
        """
        make sure that the data received is in the structure we expect columns and index wise.
        :param data: data from data bundle
        :param sid: sid as it should be stored in db
        :return: formatted data or empty df if the data is corrupted
        """
        result = pd.DataFrame(columns=data.columns)
        # rename index-column to day and convert it to datetime and utc
        if data.index[0].tzname() != 'UTC':
            data.index = [x.tz_convert('utc') for x in data.index]
        data.index.rename("day", inplace=True)
        # drop time-information, it will confuse the aligning-logic
        data.index = data.index.normalize()
        # check if we have all necessary columns
        corrupted_data = False
        for column in US_EQUITY_PRICING_COLUMNS:
            # id not necessary
            if column == 'id':
                continue

            if column not in list(data.columns) + [data.index.name]:
                msg = f"corrupted data for :{sid}. columns must contain day, open, high, low, close, volume"
                logger.warning(msg)
                corrupted_data = True
                break
        if not corrupted_data:
            # drop columns not of interest
            cols_to_drop = [column for column in data.columns if column not in US_EQUITY_PRICING_COLUMNS]
            data.drop(columns=cols_to_drop, inplace=True)
            result = data

        return result
