import logging
import os
import io
from datetime import datetime, timedelta
import json
import sys

import requests
import boto3

from src.etl.utils import yesterday_formatted, save_data


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

BUCKET = os.getenv("S3_BUCKET", sys.argv[1])


def handler(event=None, context=None, date=None):
    extract_case_data(date)
    extract_vaccine_data(date)
    return "Success"


def extract_case_data(date):
    date = date or yesterday_formatted()  # yyyymmdd

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
    raw_data = get_raw_vaccine_data()
    save_raw_vaccine_data(date, raw_data)


def get_raw_vaccine_data():
    res = requests.get("https://covid19.colorado.gov/vaccine-data-dashboard")
    return res.content


def save_raw_vaccine_data(date, data):
    raw_data = io.BytesIO(data)
    s3_filename = f"raw_vaccine_data/{yesterday_formatted()}.html"
    s3.upload_fileobj(raw_data, BUCKET, s3_filename)


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
