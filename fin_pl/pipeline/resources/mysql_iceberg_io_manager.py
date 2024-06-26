from contextlib import contextmanager
import pandas as pd
from dagster import IOManager, OutputContext, InputContext
from trino.dbapi import connect

@contextmanager
def connect_trino(config):
    conn =  connect(
        host='localhost',  # The hostname should match the service name in docker-compose
        port=8060,     # The Trino coordinator 
        user='trino'
    )
    try:
        yield conn
    except Exception:
        raise

class MySQLIcebergIOManager(IOManager):
    def __init__(self, config):
        self._config = config


    def handle_output(self, context: OutputContext):
        schema, table = context.asset_key.path[-2], context.asset_key.path[-1]
        with connect_trino(self._config) as conn:
            cur = conn.cursor()
            create_schema_query = f"CREATE SCHEMA IF NOT EXISTS iceberg.bronze"
            cur.execute(create_schema_query)
            remove_table_query = f"DROP TABLE IF EXISTS iceberg.bronze.{table}"
            cur.execute(remove_table_query)
            create_table_as_query = f"""
            CREATE TABLE iceberg.bronze.{table} AS 
            SELECT * FROM mysql.{schema}.{table}
            """
            cur.execute(create_table_as_query)
            print(f"Table {table} created in Iceberg")
        # Get the number of rows in the input table
        count_query = f"SELECT COUNT(*) FROM mysql.{schema}.{table}"
        cur.execute(count_query)
        row_count = cur.fetchone()[0]

        context.log.info("row_count: " + str(row_count))

    def load_input(self, context: InputContext) -> pd.DataFrame:
        pass

from contextlib import contextmanager
import pandas as pd
from dagster import IOManager, OutputContext, InputContext
from trino.dbapi import connect

@contextmanager
def connect_trino(config):
    conn = connect(
        host='localhost',  # The hostname should match the service name in docker-compose
        port=8060,     # The Trino coordinator 
        user='trino'
    )
    try:
        yield conn
    except Exception:
        raise

class IcebergIOManager(IOManager):
    def __init__(self, config):
        self._config = config

    def handle_output(self, context: OutputContext, transform_query: str):
        schema, table = context.asset_key.path[-3], context.asset_key.path[-1]
        with connect_trino(self._config) as conn:
            cur = conn.cursor()

            create_schema_query = f"CREATE SCHEMA IF NOT EXISTS iceberg.{schema}"
            cur.execute(create_schema_query)

            remove_table_query = f"DROP TABLE IF EXISTS iceberg.{schema}.{table}"
            cur.execute(remove_table_query)

            ddl_query = f"CREATE TABLE iceberg.{schema}.{table} AS {transform_query}"
            context.log.info(f"DDL: {ddl_query}")

            cur.execute(ddl_query)
            context.log.info(f"Table {table} created in Iceberg")

        count_query = f"SELECT COUNT(*) FROM iceberg.{schema}.{table}"
        cur.execute(count_query)
        row_count = cur.fetchone()[0]

        context.log.info("row_count: " + str(row_count))
        describe_query = f"DESCRIBE iceberg.{schema}.{table}"
        cur.execute(describe_query)
        schema_info = cur.fetchall()

        for column_info in schema_info:
            context.log.info(f"Column: {column_info[0]}, Type: {column_info[1]}")

    def load_input(self, context: InputContext) -> str:
        schema, table = context.asset_key.path[-3], context.asset_key.path[-1]
        context.log.info(f"Loading data from Iceberg table: {table}")
        table_name = f"iceberg.{schema}.{table}"
        return table_name
