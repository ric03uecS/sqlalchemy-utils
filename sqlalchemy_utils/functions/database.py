from sqlalchemy.engine.url import make_url
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError, OperationalError
import os
from copy import copy


def database_exists(url):
    """Check if a database exists.

    :param url: A SQLAlchemy engine URL.

    Performs backend-specific testing to quickly determine if a database
    exists on the server. ::

        database_exists('postgres://postgres@localhost/name')  #=> False
        create_database('postgres://postgres@localhost/name')
        database_exists('postgres://postgres@localhost/name')  #=> True

    Supports checking against a constructed URL as well. ::

        engine = create_engine('postgres://postgres@localhost/name')
        database_exists(engine.url)  #=> False
        create_database(engine.url)
        database_exists(engine.url)  #=> True

    """

    url = copy(make_url(url))
    database = url.database
    url.database = None

    engine = sa.create_engine(url)

    if engine.dialect.name == 'postgresql':
        text = "SELECT 1 FROM pg_database WHERE datname='%s'" % database
        return bool(engine.execute(text).scalar())

    elif engine.dialect.name == 'mysql':
        text = ("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                "WHERE SCHEMA_NAME = '%s'" % database)
        return bool(engine.execute(text).scalar())

    elif engine.dialect.name == 'sqlite':
        return database == ':memory:' or os.path.exists(database)

    else:
        text = 'SELECT 1'
        try:
            url.database = database
            engine = sa.create_engine(url)
            engine.execute(text)
            return True

        except (ProgrammingError, OperationalError):
            return False


def create_database(url, encoding='utf8'):
    """Issue the appropriate CREATE DATABASE statement.

    :param url: A SQLAlchemy engine URL.
    :param encoding: The encoding to create the database as.

    To create a database, you can pass a simple URL that would have
    been passed to ``create_engine``. ::

        create_database('postgres://postgres@localhost/name')

    You may also pass the url from an existing engine. ::

        create_database(engine.url)

    Has full support for mysql, postgres, and sqlite. In theory,
    other database engines should be supported.
    """

    url = copy(make_url(url))

    database = url.database
    if not url.drivername.startswith('sqlite'):
        url.database = None

    engine = sa.create_engine(url)

    if engine.dialect.name == 'postgresql':
        if engine.driver == 'psycopg2':
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
            engine.raw_connection().set_isolation_level(
                ISOLATION_LEVEL_AUTOCOMMIT)

        text = "CREATE DATABASE %s ENCODING = '%s'" % (database, encoding)
        engine.execute(text)

    elif engine.dialect.name == 'mysql':
        text = "CREATE DATABASE %s CHARACTER SET = '%s'" % (database, encoding)
        engine.execute(text)

    elif engine.dialect.name == 'sqlite' and database != ':memory:':
        open(database, 'w').close()

    else:
        text = "CREATE DATABASE %s" % database
        engine.execute(text)


def drop_database(url):
    """Issue the appropriate DROP DATABASE statement.

    :param url: A SQLAlchemy engine URL.

    Works similar to the :ref:`create_database` method in that both url text
    and a constructed url are accepted. ::

        drop_database('postgres://postgres@localhost/name')
        drop_database(engine.url)

    """

    url = copy(make_url(url))

    database = url.database
    if not url.drivername.startswith('sqlite'):
        url.database = None

    engine = sa.create_engine(url)

    if engine.dialect.name == 'sqlite' and url.database != ':memory:':
        os.remove(url.database)

    elif engine.dialect.name == 'postgresql' and engine.driver == 'psycopg2':
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        engine.raw_connection().set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        text = "DROP DATABASE %s" % database
        engine.execute(text)

    else:
        text = "DROP DATABASE %s" % database
        engine.execute(text)
