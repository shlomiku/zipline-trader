import pandas as pd
from datetime import date
from zipline.errors import SymbolNotFound, SidsNotFound


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
