import logging
import os
import io
from datetime import datetime, timedelta
import json
import sys

import requests
import boto3
import psycopg2


BUCKET = os.getenv("S3_BUCKET")
DB_CREDENTIALS = os.getenv("DB_CREDENTIALS")
API_URL = (
    "https://opendata.arcgis.com/datasets/566216cf203e400f8cbf2e6b4354bc57_0.geojson"
)

s3_client = boto3.client("s3")


def handler(event=None, context=None):
    raw_data = get_raw_case_data()
    if today_formatted() in str(raw_data):
        save_to_s3(raw_data, raw_s3_filename())

        clean_data = clean_cases_data(raw_data)
        save_to_s3(clean_data, clean_s3_filename())

        save_case_data_to_db(clean_data)
    else:
        print("Data not updated yet")


def save_case_data_to_db(clean_data):
    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()

    for day in clean_data:
        sql_data = (
            day["reportingDate"],
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
            INSERT INTO cases (reporting_date, positive, total_hospitalized, death_confirmed, 
            positive_increase, death_increase, hospitalized_increase, tested, tested_increase)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (reporting_date) DO UPDATE SET
            reporting_date = %s, positive = %s, total_hospitalized = %s, death_confirmed = %s,
            positive_increase = %s, death_increase = %s, hospitalized_increase = %s, tested = %s,
            tested_increase = %s;
        """

        cur.execute(sql, sql_data + sql_data)
    conn.commit()
    conn.close()


def clean_cases_data(raw_data):
    daily_data = raw_data["features"]
    days = []
    for day in daily_data:
        properties = day["properties"]
        if not properties["Date"]:
            continue
        data = {
            "reportingDate": reporting_date_to_formatted(properties["Date"]),
            "positive": properties["Cases"],
            "tested": properties["Tested"],
            "deathConfirmed": properties["Deaths"],
            "hospitalizations": properties["Hosp"],
        }
        days.append(data)
    days = sorted(days, key=lambda i: i["reportingDate"])
    total_days = len(days)
    for i in range(total_days):
        if i == 0:
            days[i]["positiveIncrease"] = days[i]["positive"]
            days[i]["deathIncrease"] = days[i]["deathConfirmed"]
            days[i]["hospitalizedIncrease"] = days[i]["hospitalizations"]
            days[i]["testedIncrease"] = days[i]["tested"]
        else:
            days[i]["positiveIncrease"] = days[i]["positive"] - days[i - 1]["positive"]
            days[i]["deathIncrease"] = (
                days[i]["deathConfirmed"] - days[i - 1]["deathConfirmed"]
            )
            days[i]["hospitalizedIncrease"] = (
                days[i]["hospitalizations"] - days[i - 1]["hospitalizations"]
            )
            days[i]["testedIncrease"] = days[i]["tested"] - days[i - 1]["tested"]
    return days


def reporting_date_to_formatted(date):
    date_time = datetime.strptime(date, "%m/%d/%Y")
    return date_time.strftime("%Y-%m-%d")


def get_raw_case_data():
    res = requests.get(API_URL)
    return res.json()


def save_to_s3(json_data, s3_filename):
    data = json.dumps(json_data).encode('utf-8')
    raw_data = io.BytesIO(data)
    s3_client.upload_fileobj(raw_data, BUCKET, s3_filename)


def today_formatted():
    today = datetime.today() - timedelta(hours=7)
    return today.strftime("%m/%d/%Y")


def raw_s3_filename():
    today = datetime.today() - timedelta(hours=7)
    return f"data/raw_case_data/{today.strftime('%Y%m%d')}.json"


def clean_s3_filename():
    today = datetime.today() - timedelta(hours=7)
    return f"data/clean_case_data/{today.strftime('%Y%m%d')}.json"
