import logging
import os
import io
from datetime import datetime, timedelta
import json

import requests
import boto3


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

BUCKET = os.getenv("S3_BUCKET", None)


def handler(event=None, context=None, date=None, bucket=None):
    bucket = BUCKET or bucket
    transform_case_data(date, bucket)

    # get raw vaccine data
    # save raw vaccine data to s3 bucket

    # call transform lambda function

    # return status 200
    pass


def transform_case_data(date, bucket):
    yesterday = datetime.today() - timedelta(days=1)
    date = date or yesterday.strftime("%Y%m%d")  # yyyymmdd

    s3_filename = f"raw_cases_data/{date}.json"
    response = s3.get_object(
        Bucket=bucket,
        Key=s3_filename,
    )

    raw_data = json.loads(response["Body"].read())
    cleaned_data = clean_data(raw_data)
    cleaned_data_s3_obj = io.BytesIO(json.dumps(cleaned_data).encode("utf-8"))

    s3_filename = f"cleaned_cases_data/{date}.json"
    s3.upload_fileobj(cleaned_data_s3_obj, bucket, s3_filename)


def clean_data(raw_data):
    fields_to_keep = [
        "deathConfirmed",
        "deathIncrease",
        "hospitalizedCurrently",
        "hospitalizedIncrease",
        "positive",
        "positiveIncrease",
    ]
    cleaned = {}
    for k in raw_data:
        if k in fields_to_keep:
            cleaned[k] = raw_data[k]
    return cleaned


if __name__ == "__main__":
    """
    Call file with bucket name and optional date
    python src/etl/extract_raw_data.py <bucket> <yyyymmdd>
    """
    import sys

    bucket = sys.argv[1]
    try:
        date = sys.argv[2]
    except IndexError:
        date = None
    handler(date=date, bucket=bucket)
