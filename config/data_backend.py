import os

import yaml

CONFIG_PATH = os.environ.get("ZIPLINE_TRADER_CONFIG")
if CONFIG_PATH:
    with open(CONFIG_PATH, mode='r') as f:
        ZIPLINE_CONFIG = yaml.safe_load(f)


def db_backend_configured():
    if CONFIG_PATH:
        return ZIPLINE_CONFIG["backend"].get("type", False)
    else:
        return os.environ.get('ZIPLINE_DATA_BACKEND')


class PostgresDB:
    if CONFIG_PATH:
        pg = ZIPLINE_CONFIG["backend"]["postgres"]

    @property
    def host(self):
        """
        you could define it in the zipline-trader config file or
        override it with this env variable: ZIPLINE_DATA_BACKEND_HOST
        :return:
        """
        val = None
        if os.environ.get('ZIPLINE_DATA_BACKEND_HOST'):
            val = os.environ.get('ZIPLINE_DATA_BACKEND_HOST')
        elif CONFIG_PATH and self.pg.get('host'):
            val = self.pg.get('host')
        if not val:
            raise Exception("Postgres host not defined by user")
        return val

    @property
    def port(self):
        """
        you could define it in the zipline-trader config file or
        override it with this env variable: ZIPLINE_DATA_BACKEND_PORT
        :return:
        """
        val = None
        if os.environ.get('ZIPLINE_DATA_BACKEND_PORT'):
            val = os.environ.get('ZIPLINE_DATA_BACKEND_PORT')
        elif CONFIG_PATH and self.pg.get('port'):
            val = self.pg.get('port')
        if not val:
            raise Exception("Postgres port not defined by user")
        return int(val)

    @property
    def user(self):
        """
        you could define it in the zipline-trader config file or
        override it with this env variable: ZIPLINE_DATA_BACKEND_USER
        :return:
        """
        val = None
        if os.environ.get('ZIPLINE_DATA_BACKEND_USER'):
            val = os.environ.get('ZIPLINE_DATA_BACKEND_USER')
        elif CONFIG_PATH and self.pg.get('user'):
            val = self.pg.get('user')
        if not val:
            raise Exception("Postgres user not defined by user")
        return val

    @property
    def password(self):
        """
        you could define it in the zipline-trader config file or
        override it with this env variable: ZIPLINE_DATA_BACKEND_PASSWORD
        :return:
        """
        val = None
        if os.environ.get('ZIPLINE_DATA_BACKEND_PASSWORD'):
            val = os.environ.get('ZIPLINE_DATA_BACKEND_PASSWORD')
        elif CONFIG_PATH and self.pg.get('password'):
            val = self.pg.get('password')
        if not val:
            raise Exception("Postgres password not defined by user")
        return val


if __name__ == '__main__':
    print(ZIPLINE_CONFIG)
    db = PostgresDB()
    print(db.host)
    os.environ["ZIPLINE_DATA_BACKEND_HOST"] = "localhost"
    print(db.host)
    del db.pg["host"]
    del os.environ["ZIPLINE_DATA_BACKEND_HOST"]
    try:
        print(db.host)
    except Exception as e:
        print(e)

    print(db.port)
    os.environ["ZIPLINE_DATA_BACKEND_PORT"] = "5433"
    assert 5433 == db.port

    print(db.user)
    os.environ["ZIPLINE_DATA_BACKEND_USER"] = "userrr"
    assert "userrr" == db.user

    print(db.password)
    os.environ["ZIPLINE_DATA_BACKEND_PASSWORD"] = "passdd"
    assert "passdd" == db.password



