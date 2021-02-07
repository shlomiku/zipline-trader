import os

import yaml

CONFIG_PATH = os.environ.get("ZIPLINE_TRADER_CONFIG")
if CONFIG_PATH:
    with open(CONFIG_PATH, mode='r') as f:
        ZIPLINE_CONFIG = yaml.safe_load(f)


class AlpacaConfig:
    if CONFIG_PATH:
        al = ZIPLINE_CONFIG["alpaca"]

    @property
    def key(self):
        if CONFIG_PATH:
            return self.al["key_id"]
        else:
            return os.environ.get('APCA_API_KEY_ID')

    @property
    def secret(self):
        if CONFIG_PATH:
            return self.al["secret"]
        else:
            return os.environ.get('APCA_API_SECRET_KEY')

    @property
    def base_url(self):
        if CONFIG_PATH:
            return self.al["base_url"]
        else:
            return os.environ.get('APCA_API_BASE_URL')

    @property
    def universe(self):
        if CONFIG_PATH:
            return self.al["universe"]
        else:
            return os.environ.get('ZT_UNIVERSE')

    @property
    def custom_asset_list(self):
        if CONFIG_PATH:
            return self.al["custom_asset_list"]
        else:
            return os.environ.get('ZT_CUSTOM_ASSET_LIST')



class AlphaVantage:
    if CONFIG_PATH:
        av = ZIPLINE_CONFIG["alpha-vantage"]

    @property
    def sample_frequency(self):
        """
        how long to wait between samples. default for free accounts - 1 min.
        so we could do 5 sample per minute.
        you could define it in the config file or override it with env variable
        :return:
        """
        val = 60
        if os.environ.get('AV_FREQ_SEC'):
            val = int(os.environ.get('AV_FREQ_SEC'))
        elif CONFIG_PATH and self.av.get('AV_FREQ_SEC'):
            val = int(self.av.get('AV_FREQ_SEC'))
        return val

    @property
    def max_calls_per_freq(self):
        """
        max api calls you could do per frequency period.
        free account can do 5 calls per minute
        you could define it in the config file or override it with env variable
        :return:
        """
        val = 5
        if os.environ.get('AV_CALLS_PER_FREQ'):
            val = int(os.environ.get('AV_CALLS_PER_FREQ'))
        elif CONFIG_PATH and self.av.get('AV_CALLS_PER_FREQ'):
            val = int(self.av.get('AV_CALLS_PER_FREQ'))
        return val

    @property
    def breathing_space(self):
        """
        to make sure we don't pass the limit we take some breathing room for sampling error.
        you could define it in the config file or override it with env variable
        :return:
        """
        val = 1
        if os.environ.get('AV_TOLERANCE_SEC'):
            val = int(os.environ.get('AV_TOLERANCE_SEC'))
        elif CONFIG_PATH and self.av.get('AV_TOLERANCE_SEC'):
            val = int(self.av.get('AV_TOLERANCE_SEC'))
        return val

    @property
    def api_key(self):
        """
        api key for alpha vantage
        you could define it in the config file or override it with env variable
        :return:
        """
        val = ''
        if os.environ.get('ALPHAVANTAGE_API_KEY'):
            val = os.environ.get('ALPHAVANTAGE_API_KEY')
        elif CONFIG_PATH and self.av.get('ALPHAVANTAGE_API_KEY'):
            val = self.av.get('ALPHAVANTAGE_API_KEY')
        return val


def get_binance_config():
    if CONFIG_PATH:
        return ZIPLINE_CONFIG["binance"]


if __name__ == '__main__':
    print(ZIPLINE_CONFIG)
    print(AlpacaConfig().key)
    av_conf = AlphaVantage()
    print(av_conf.sample_frequency)
    print(av_conf.max_calls_per_freq)
    print(get_binance_config())
