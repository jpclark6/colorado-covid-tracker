import logging
import os
import io
from datetime import datetime, timedelta
import json
import sys

import requests
import boto3


logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    backup_bucket = sys.argv[1]
except IndexError:
    backup_bucket = None

BUCKET = os.getenv("S3_BUCKET", backup_bucket)

s3_client = boto3.client("s3")


def handler(event=None, context=None, date=None):
    extract_case_data(date)
    extract_vaccine_data(date)
    start_next_function()
    return "Success"


def extract_case_data(date):
    date = date or today_formatted()  # yyyymmdd

    raw_data = get_raw_case_data(date)
    save_raw_case_data(date, raw_data)


def get_raw_case_data(date):
    url = f"https://api.covidtracking.com/v1/states/co/{date}.json"
    response = requests.get(url)
    return response.json()


def save_raw_case_data(date, data):
    s3_filename = f"raw_cases_data/{date}.json"
    save_data(s3_filename, data, BUCKET)


def extract_vaccine_data(date):
    date = date or today_formatted()  # yyyymmdd

    raw_data = get_raw_vaccine_data()
    save_raw_vaccine_data(date, raw_data)


def get_raw_vaccine_data():
    res = requests.get("https://covid19.colorado.gov/vaccine-data-dashboard")
    return res.content


def save_raw_vaccine_data(date, data):
    raw_data = io.BytesIO(data)
    s3_filename = f"raw_vaccine_data/{date}.html"
    s3_client.upload_fileobj(raw_data, BUCKET, s3_filename)


### Take out eventually, make module
def today_formatted():
    today = datetime.today() - timedelta(hours=7)
    return today.strftime("%Y%m%d")  # yyyymmdd


def yesterday_formatted():
    today = datetime.today() - timedelta(days=1, hours=7)
    return today.strftime("%Y%m%d")  # yyyymmdd


def save_data(s3_filename, data, bucket):
    s3_data = io.BytesIO(json.dumps(data).encode("utf-8"))
    s3_client.upload_fileobj(s3_data, bucket, s3_filename)


###


def start_next_function():
    lambda_client = boto3.client("lambda")
    print("Getting function name")
    function_name = os.getenv("NEXT_FUNCTION")
    print("Function name:", function_name)
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="Event",
    )


if __name__ == "__main__":
    """
    Call file with bucket name and optional date
    python src/etl/extract.py <bucket> <yyyymmdd>
    """
    try:
        date = sys.argv[2]
    except IndexError:
        date = None
    handler(date=date)
