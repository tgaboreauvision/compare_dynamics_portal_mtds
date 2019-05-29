import pyodbc
import pandas as pd
from sqlalchemy import create_engine
from crm_class import Odata
import settings
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT  # <-- ADD THIS LINE


class db_builder():

    def __init__(self, target_dbname, password, host='', user='postgres', dbname='postgres'):
        self.host = host
        self.user = user
        self.password = password
        self.dbname = dbname
        self.target_dbname = target_dbname
        self.initial_target_conn = psycopg2.connect(dbname=self.dbname,
                                                    user=self.user,
                                                    host=self.host,
                                                    password=self.password)
        self.built_target_conn = psycopg2.connect(dbname=self.target_dbname,
                                                  user=self.user,
                                                  host=self.host,
                                                  password=self.password)
        self.source_conns = {}
        self.dynamics = Odata(sandbox=False, odata_username=settings.odata_username,
                              odata_password=settings.odata_userpassword)

    def create_target_db(self, drop_existing=False):
        self.initial_target_conn.set_isolation_level(
            ISOLATION_LEVEL_AUTOCOMMIT)  # <-- ADD THIS LINE
        cur = self.initial_target_conn.cursor()
        if drop_existing:
            cur.execute(f'DROP DATABASE IF EXISTS {self.target_dbname}')
            print(cur.statusmessage)
        try:
            cur.execute(f"CREATE DATABASE {self.target_dbname};")
        except psycopg2.ProgrammingError:
            print('DB already exists - Skipping creation')
        print(cur.statusmessage)

    def add_source_conn(self, conn_name, flavour, host=None, user=None, dsn=None, dbname=None,
                        password=None):
        if flavour == 'postgres':
            engine_string = f'postgresql://{user}:{password}@{host}:5432/{dbname}'
            conn = create_engine(engine_string)
        elif flavour == 'mssql':
            conn = pyodbc.connect(f'DSN={dsn};DATABASE={dbname};UID={user};PWD={password}')
        self.source_conns[conn_name] = conn

    def get_odata_df(self, entity, top=None, select=None, fltr=None):
        self.dynamics.get_access_token()
        dynamics_data = self.dynamics.get_req(entity, top=top, select=select, fltr=fltr)
        df = pd.DataFrame(dynamics_data)
        return df

    def get_sql_df(self, conn_name, query):
        conn = self.source_conns[conn_name]
        df = pd.read_sql_query(query, con=conn)
        return df

    def get_csv_df(self, filename, select):
        df = pd.read_csv(filename, usecols=select)
        return df

    def check_target_table_exists(self, table_name):
        conn = self.built_target_conn

        exist_query = f"""SELECT
            EXISTS(
                SELECT
                    1
                FROM
                    information_schema.tables
                WHERE
                        table_catalog = '{self.target_dbname}'
                    AND
                        table_schema = 'public'
                    AND
                        table_name = '{table_name}');"""
        cur = conn.cursor()
        cur.execute(exist_query)
        return cur.fetchone()[0]

    def add_table(self, target_table, source, conn_name=None, query=None, entity=None, select=None,
                  fltr=None, top=None, filename=None, replace=False):

        if self.check_target_table_exists(target_table):
            if not replace:
                print(f'table {target_table} already exists, skipping.')
                return None
            else:
                print(f'dropping table {target_table}')
                cur = self.built_target_conn.cursor()
                cur.execute(f'DROP TABLE {target_table}')
                print(cur.statusmessage)
        if source == 'odata':
            if not entity:
                raise BaseException('Source entity must be specified for oData query')
            else:
                print(f'Retrieving data from oData - {entity}')
                df = self.get_odata_df(entity, top=top, select=select, fltr=fltr)
        elif source == 'sql':
            if not conn_name:
                raise BaseException('Conn must be specified for sql query')
            elif not query:
                raise BaseException('Please specify the query to be executed')
            else:
                print(f'Retreiving {target_table} data from sql source: {conn_name}')
                df = self.get_sql_df(conn_name, query)
        elif source == 'csv':
            if not filename:
                raise BaseException('Filename must be specified for csv table')
            else:
                print(f'Retrieving {target_table} data from {filename}')
                df = self.get_csv_df(filename, select)
        else:
            print(f'Source type for {target_table} not found or not specified.')
        engine_string = f'postgresql://{self.user}:{self.password}@{self.host}:5432/{self.target_dbname}'
        engine = create_engine(engine_string)
        df.to_sql(target_table, engine)

    def add_view(self, view_name, sql):
        cur = self.built_target_conn.cursor()
        cur.execute(f'CREATE VIEW {view_name} as {sql}')
        print(cur.statusmessage)
        self.built_target_conn.commit()
