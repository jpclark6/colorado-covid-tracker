import logging
import os
import io
from datetime import datetime, timedelta

import requests
import boto3


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

BUCKET = os.getenv('S3_BUCKET', None)

def handler(event=None, context=None, date=None):
    upload_case_data(date)

    # get raw vaccine data
    # save raw vaccine data to s3 bucket

    # call transform lambda function

    # return status 200
    pass

def upload_case_data(date):
    yesterday = datetime.today() - timedelta(days=1)
    date = date or yesterday.strftime('%Y%m%d') # yyyymmdd

    url = f'https://api.covidtracking.com/v1/states/co/{date}.json'
    response = requests.get(url)

    raw_data = io.BytesIO(response.content)
    s3_filename = f'raw_cases_data/{date}.json'
    s3.upload_fileobj(raw_data, BUCKET, s3_filename)

if __name__ == "__main__":
    """
    Call file with bucket name and optional date
    python src/etl/extract_raw_data.py <bucket> <yyyymmdd>
    """
    import sys
    BUCKET = sys.argv[1]
    try:
        date = sys.argv[2]
    except IndexError:
        date = None
    handler(date=date)