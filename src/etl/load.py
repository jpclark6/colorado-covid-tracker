import logging
import os
import io
from datetime import datetime, timedelta
import json
import sys

import requests
import boto3
import psycopg2

from src.etl.utils import yesterday_formatted, get_data, date_to_sql_date


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

BUCKET = os.getenv("S3_BUCKET", sys.argv[1])
DB_CREDENTIALS = os.getenv("DB_CREDENTIALS", sys.argv[2])


def handler(event=None, context=None, date=None):
    load_case_data(date, BUCKET)
    load_vaccine_data(date, BUCKET)


def load_case_data(date):
    date = date or yesterday_formatted()  # yyyymmdd

    s3_filename = f"cleaned_cases_data/{date}.json"
    clean_data = get_data(s3_filename, BUCKET)
    save_case_data_to_db(date, clean_data)


def load_vaccine_data(date):
    date = date or yesterday_formatted()  # yyyymmdd

    s3_filename = f"cleaned_vaccine_data/{date}.json"
    clean_data = get_data(s3_filename, BUCKET)
    save_vaccine_data_to_db(date, clean_data)

def save_case_data_to_db(date, clean_data):
    sql_date = date_to_sql_date(date)

    sql_data = (
        sql_date,
        clean_data["positive"],
        clean_data["hospitalizedCurrently"],
        clean_data["deathConfirmed"],
        clean_data["positiveIncrease"],
        clean_data["deathIncrease"],
        clean_data["hospitalizedIncrease"],
    )

    sql = """
        INSERT INTO cases (reporting_date, positive, hospitalized_currently, death_confirmed, 
        positive_increase, death_increase, hospitalized_increase)
        VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;
    """

    save_to_db(sql, sql_data)


def save_vaccine_data_to_db(date, clean_data):
    sql_date = date_to_sql_date(date)

    sql_data = (
        sql_date,
        clean_data["daily_qty"],
        clean_data["daily_cumulative"],
    )

    sql = """
        INSERT INTO vaccines (reporting_date, daily_qty, daily_cumulative)
        VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;
    """

    save_to_db(sql, sql_data)


def save_to_db(sql, sql_data):
    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()

    cur.execute(sql, sql_data)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    """
    Call file with bucket name and optional date
    python src/etl/extract.py <bucket> <yyyymmdd>
    """
    try:
        date = sys.argv[3]
    except IndexError:
        date = None
    handler(date=date)
