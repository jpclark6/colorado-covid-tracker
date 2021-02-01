import logging
import os
import io
from datetime import datetime, timedelta
import json
import sys

import requests
import boto3

from src.etl.utils import yesterday_formatted, get_data, save_data


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

BUCKET = os.getenv("S3_BUCKET", sys.argv[1])


def handler(event=None, context=None, date=None):
    transform_case_data(date)
    transform_vaccine_data(date)
    return "Success"


def transform_case_data(date):
    date = date or yesterday_formatted()  # yyyymmdd

    raw_data = get_raw_case_data(date)
    cleaned_data = clean_cases_data(raw_data)
    save_cleaned_case_data(date, cleaned_data)


def transform_vaccine_data(date):
    date = date or yesterday_formatted()  # yyyymmdd

    raw_data = get_raw_vaccine_data(date)
    cleaned_data = clean_vaccine_data(raw_data)
    save_cleaned_vaccine_data(date, cleaned_data)


def get_raw_case_data(date):
    s3_filename = f"raw_cases_data/{date}.json"
    return get_data(s3_filename, BUCKET)


def get_raw_vaccine_data(date):
    s3_filename = f"raw_vaccine_data/{date}.html"
    return get_data(s3_filename, BUCKET)


def save_cleaned_case_data(date, cleaned_data):
    s3_filename = f"cleaned_cases_data/{date}.json"
    save_data(s3_filename, cleaned_data, BUCKET)


def save_cleaned_vaccine_data(date, cleaned_data):
    s3_filename = f"cleaned_vaccine_data/{date}.json"
    save_data(s3_filename, cleaned_data, BUCKET)


def clean_cases_data(raw_data):
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


def clean_vaccine_data(dom):
    '''
    With data only available as html doc the parsing
    gets messy. This finds a known value in a table,
    then grabs additional values based on the order
    of the values and the offset from original value
    '''
    cells = dom.split('<td')
    results = {}
    cell_location_offsets = [
        {'loc': 1, 'type': 'people_immunized_one_dose'},
        {'loc': 3, 'type': 'people_immunized_two_doses'},
        {'loc': 5, 'type': 'moderna_doses'},
        {'loc': 7, 'type': 'pfizer_doses'},
    ]

    def html_to_number(sentence):
        return int((sentence.split('>'))[1].split('<')[0].replace(',', '')) # "123,456" => 123456

    for i, text in enumerate(cells):
        if 'People immunized with one dose' in text:
            for cell_location in cell_location_offsets:
                text_with_value = cells[i + cell_location['loc']]
                value = html_to_number(text_with_value)
                results[cell_location['type']] = value

    return results


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
