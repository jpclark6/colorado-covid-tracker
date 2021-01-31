import io
from datetime import datetime, timedelta
import sys

import requests
import boto3

from src.etl.extract_raw_data import upload_case_data
from src.etl.transform_data import transform_case_data
from src.etl.load_data import load_case_data


"""
Do not call python file directly. Correct example:
    "python -m scripts.backfill_cases <bucket> 20200501 20200531 <db_credentials>"
DB Credentials in the from 'postgres://<user>:<pw>@host/database'
Script should be ran once to fill in previous COVID
data once the app can be deployed. Additional new
data will be retrieved automatically.
data will be retrieved automatically.
"""


def loop_through_dates(bucket, start_date, end_date, db_creds):
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")

    if int(start_date) < 20200304:
        print("No data at start date")
    if end >= datetime.today():
        print("No data available after yesterday's date")

    if start_date > end_date:
        print("Unable to process request. Start date is after end date")
        return

    delta = timedelta(days=1)
    while start <= end:
        print(f"Uploading data for {start}")
        date = start.strftime("%Y%m%d")
        upload_case_data(date, bucket)
        transform_case_data(date, bucket)
        load_case_data(date, bucket, db_creds)
        start += delta


if __name__ == "__main__":
    """
    Call file with bucket name, start date, and end date
    python src/etl/extract_raw_data.py <bucket> <yyyymmdd> <yyyymmdd>
    """

    bucket = sys.argv[1]
    start_date = sys.argv[2]
    end_date = sys.argv[3]
    db_creds = sys.argv[4]

    loop_through_dates(bucket, start_date, end_date, db_creds)
