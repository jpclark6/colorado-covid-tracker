import io
from datetime import datetime, timedelta
import sys
import os

import requests
import boto3

os.setenvvar("S3_BUCKET", sys.argv[1])
os.setenvvar("DB_CREDENTIALS", sys.argv[4])

from src.etl.extract import extract_case_data
from src.etl.transform import transform_case_data
from src.etl.load import load_case_data


"""
Do not call python file directly. Correct example:
    "python -m scripts.backfill_cases <bucket> 20200501 20200531 <db_credentials>"
DB Credentials in the from 'postgres://<user>:<pw>@host/database'
Script should be ran once to fill in previous COVID
data once the app can be deployed. Additional new
data will be retrieved automatically.
data will be retrieved automatically.
"""


def loop_through_dates(start_date, end_date):
    current_day = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")

    if int(start_date) < 20200304:
        print("No data at start date")
        return
    if end >= datetime.today():
        print("No data available after yesterday's date")
        return
    if start_date > end_date:
        print("Unable to process request. Start date is after end date")
        return

    delta = timedelta(days=1)
    while current_day <= end:
        print(f"Uploading data for {current_day}")
        date = current_day.strftime("%Y%m%d")
        extract_case_data(date)
        transform_case_data(date)
        load_case_data(date)
        current_day += delta


if __name__ == "__main__":
    """
    Call file with bucket name, start date, and end date
    python src/etl/extract.py <bucket> <yyyymmdd> <yyyymmdd>
    """

    bucket = sys.argv[1]
    start_date = sys.argv[2]
    end_date = sys.argv[3]
    db_creds = sys.argv[4]

    loop_through_dates(start_date, end_date)
