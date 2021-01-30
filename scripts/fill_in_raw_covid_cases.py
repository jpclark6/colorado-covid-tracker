import io
from datetime import datetime, timedelta
import sys

import requests
import boto3


"""
Script should be ran once to fill in previous COVID
data once the app can be deployed. Additional new
data will be retrieved automatically.
"""

s3 = boto3.client('s3')

def upload_case_data(bucket, date):
    yesterday = datetime.today() - timedelta(days=1)
    date = date.strftime('%Y%m%d') # yyyymmdd

    url = f'https://api.covidtracking.com/v1/states/co/{date}.json'
    response = requests.get(url)

    raw_data = io.BytesIO(response.content)
    s3_filename = f'raw_cases_data/{date}.json'
    s3.upload_fileobj(raw_data, bucket, s3_filename)


def loop_through_dates(bucket, start_date, end_date):
    start = datetime.strptime(start_date,'%Y%m%d')
    end = datetime.strptime(end_date,'%Y%m%d')

    if int(start_date) < 20200304:
        print("No data at start date")
    if end >= datetime.today():
        print("No data available after yesterday's date")

    if start_date > end_date:
        print("Unable to process request. Start date is after end date")
        return
    elif start_date == end_date:
        upload_case_data(bucket, start)
        print("Success")
        return

    delta = timedelta(days=1)
    while start <= end:
        print(f'Uploading data for {start}')
        upload_case_data(bucket, start)
        start += delta


if __name__ == "__main__":
    """
    Call file with bucket name, start date, and end date
    python src/etl/extract_raw_data.py <bucket> <yyyymmdd> <yyyymmdd>
    """
    
    bucket = sys.argv[1]
    start_date = sys.argv[2]
    end_date = sys.argv[3]

    loop_through_dates(bucket, start_date, end_date)
