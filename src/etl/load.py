import logging
import os
import io
from datetime import datetime, timedelta
import json
import sys

import requests
import boto3
import psycopg2


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
ssm = boto3.client("ssm")

try:
    backup_bucket = sys.argv[1]
except IndexError:
    backup_bucket = None

BUCKET = os.getenv("S3_BUCKET", backup_bucket)
DB_CREDENTIALS = ssm.get_parameter(Name="/colorado-covid/db_creds")["Parameter"][
    "Value"
]  # make env var


def handler(event=None, context=None, date=None):
    load_case_data(date)
    load_vaccine_data(date)


def load_case_data(date):
    date = date or today_formatted()  # yyyymmdd

    s3_filename = f"cleaned_cases_data/{date}.json"
    clean_data = get_data(s3_filename, BUCKET)
    save_case_data_to_db(date, clean_data)


def load_vaccine_data(date):
    date = date or yesterday_formatted()  # yyyymmdd

    s3_filename = f"cleaned_vaccine_data/{date}.json"
    clean_data = get_data(s3_filename, BUCKET)
    save_vaccine_data_to_db(date, clean_data)


def save_case_data_to_db(date, clean_data):
    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()

    for day in clean_data:
        sql_date = date_to_sql_date(date)

        sql_data = (
            date_to_sql_date(day["reportingDate"]),
            day["positive"],
            day["hospitalizations"],
            day["deathConfirmed"],
            day["positiveIncrease"],
            day["deathIncrease"],
            day["hospitalizedIncrease"],
            day["tested"],
            day["testedIncrease"],
        )

        sql = """
            INSERT INTO cases (reporting_date, positive, hospitalized_currently, death_confirmed, 
            positive_increase, death_increase, hospitalized_increase, tested, tested_increase)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;
        """

        cur.execute(sql, sql_data)
    conn.commit()
    conn.close()


def save_vaccine_data_to_db(date, clean_data):
    sql_date = date_to_sql_date(date)

    try:
        backup_bucket = sys.argv[1]
        sql_data = (
            sql_date,
            clean_data["daily_qty"],
            clean_data["daily_cumulative"],
        )
    except IndexError:  # if running automatically with different formatted data
        total_cumulative = (
            clean_data["people_immunized_one_dose"]
            + clean_data["people_immunized_two_doses"]
        )
        (
            yesterday_cases,
            one_dose_daily,
            two_doses_daily,
        ) = fetch_prev_days_vaccine_cumulative()
        daily = total_cumulative - yesterday_cases
        one_dose_increase = clean_data["people_immunized_one_dose"] - one_dose_daily
        two_doses_increase = clean_data["people_immunized_two_doses"] - two_doses_daily

        sql_data = (
            sql_date,
            daily,
            total_cumulative,
            one_dose_increase,
            clean_data["people_immunized_one_dose"],
            two_doses_increase,
            clean_data["people_immunized_two_doses"],
        )

    sql = """
        INSERT INTO vaccines (reporting_date, daily_qty, daily_cumulative, one_dose_increase, 
        one_dose_total, two_doses_increase, two_doses_total)
        VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;
    """

    save_to_db(sql, sql_data)


def save_to_db(sql, sql_data):
    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()

    cur.execute(sql, sql_data)

    conn.commit()
    conn.close()


def run_raw_sql(sql):
    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()

    cur.execute(sql)

    conn.commit()
    conn.close()


def fetch_prev_days_vaccine_cumulative():
    sql = "SELECT * FROM vaccines ORDER BY reporting_date DESC LIMIT 1;"
    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()
    cur.execute(sql)
    data = cur.fetchone()
    conn.close()
    daily = data[2]
    one_dose = data[4]
    two_doses = data[6]
    return daily, one_dose, two_doses


### Take out eventually, make module
def today_formatted():
    today = datetime.today() - timedelta(hours=7)
    return today.strftime("%Y%m%d")  # yyyymmdd


def yesterday_formatted():
    today = datetime.today() - timedelta(days=1, hours=7)
    return today.strftime("%Y%m%d")  # yyyymmdd


def get_data(s3_filename, bucket):
    response = s3.get_object(
        Bucket=bucket,
        Key=s3_filename,
    )
    return json.loads(response["Body"].read())


def date_to_sql_date(date):
    date_time = datetime.strptime(date, "%Y%m%d")
    return date_time.strftime("%Y-%m-%d")


###

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
