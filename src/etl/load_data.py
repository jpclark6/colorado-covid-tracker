import logging
import os
import io
from datetime import datetime, timedelta
import json

import requests
import boto3
import psycopg2


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

BUCKET = os.getenv("S3_BUCKET", None)
DB_CREDENTIALS = os.getenv("DB_CREDENTIALS", None)


def handler(event=None, context=None, date=None, bucket=None, db_credentials=None):
    bucket = BUCKET or bucket
    db_credentials = DB_CREDENTIALS or db_credentials

    load_case_data(date, bucket, db_credentials)


def load_case_data(date, bucket, db_credentials):
    yesterday = datetime.today() - timedelta(days=1)
    date = date or yesterday.strftime("%Y%m%d")  # yyyymmdd

    s3_filename = f"cleaned_cases_data/{date}.json"
    response = s3.get_object(
        Bucket=bucket,
        Key=s3_filename,
    )

    clean_data = json.loads(response["Body"].read())

    date_time = datetime.strptime(date, "%Y%m%d")
    sql_date = date_time.strftime("%Y-%m-%d")
    sql_data = (
        sql_date,
        clean_data["positive"],
        clean_data["hospitalizedCurrently"],
        clean_data["deathConfirmed"],
        clean_data["positiveIncrease"],
        clean_data["deathIncrease"],
        clean_data["hospitalizedIncrease"],
    )

    conn = psycopg2.connect(db_credentials)
    cur = conn.cursor()

    cur.execute(
        """
            INSERT INTO cases (reporting_date, positive, hospitalized_currently, death_confirmed, 
            positive_increase, death_increase, hospitalized_increase)
            VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;
            """,
        sql_data,
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    """
    Call file with bucket name and optional date
    python src/etl/extract_raw_data.py <bucket> <yyyymmdd>
    """
    import sys

    bucket = sys.argv[1]
    db_credentials = sys.argv[2]
    try:
        date = sys.argv[3]
    except IndexError:
        date = None
    handler(date=date, bucket=bucket, db_credentials=db_credentials)
