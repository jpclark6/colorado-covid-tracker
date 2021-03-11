import os
import io
from datetime import datetime, timedelta
import json
import logging

import requests
import boto3
import psycopg2

logger = logging.getLogger()
logger.setLevel(logging.INFO)


BUCKET = os.getenv("S3_BUCKET")
if not BUCKET:
    logger.error({"error": "no bucket env var found"})
DB_CREDENTIALS = os.getenv("DB_CREDENTIALS")
if not DB_CREDENTIALS:
    logger.error({"error": "no DB credentials env var found"})
API_URL = (
    "https://opendata.arcgis.com/datasets/566216cf203e400f8cbf2e6b4354bc57_0.geojson"
)
# following two keys aren't required to function, but if not included then the function
# won't invalidate the cache as soon as new data is available, but it still
# will every 15 minutes per the normal schedule
INVALIDATE_CACHE_KEY = os.getenv("INVALIDATE_CACHE_KEY")
API_GATEWAY_URL = os.getenv("API_URL")
EMAIL_TOPIC = os.getenv("EMAIL_TOPIC")

s3_client = boto3.client("s3")
sns_client = boto3.client("sns")


def handler(event=None, context=None):
    try:
        logger.info("Requesting raw data")
        raw_data = get_raw_case_data()

        if next_day() in str(raw_data):
            s3_filename = raw_s3_filename()
            logger.info(f"New data found. Saving to s3://{BUCKET}/{s3_filename}")
            save_to_s3(raw_data, s3_filename)

            logger.info("Cleaning data")
            clean_data = clean_cases_data(raw_data)

            s3_filename = clean_s3_filename()
            logger.info(f"Saving cleaned data to s3://{BUCKET}/{s3_filename}")
            save_to_s3(clean_data, s3_filename)

            logger.info("Saving to database")
            save_case_data_to_db(clean_data)
            log_update_time(new_data=True)

            update_currently_hospitalized()

            logger.info("Success")
            invalidate_cache()
        else:
            logger.info("Data not updated yet")
            log_update_time(new_data=False)
        return "Success"
    except Exception as e:
        message = f"Encountered an error during Cases data fetching: {f}"
        topic = "ColoradoCovidData Error - Cases"
        sns_client.publish(
            TopicArn=EMAIL_TOPIC,
            Message=message,
            Subject=subject,
        )
        logger.error(message)
        return "Failed"


def invalidate_cache():
    logger.info("Invalidating cache")
    headers = {"invalidate-cache-key": INVALIDATE_CACHE_KEY}
    response = requests.post(API_GATEWAY_URL + "/invalidate_cache/", headers=headers)
    if response.status_code == 200:
        logger.info("Successfully invalidated cache")
    else:
        logger.info("Failed to invalidate cache")


def log_update_time(new_data=False):
    """Update DB with times we checked for new data along with status of if we found new data"""
    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO invokes (function_name, invoke_time, new_data) VALUES (%s, now(), %s)",
        ("cases", new_data),
    )
    conn.commit()
    conn.close()


def save_case_data_to_db(clean_data):
    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()

    i = 0
    for day in clean_data:
        i += 1
        sql_data = (
            day["reporting_date"],
            day["positive"],
            day["hospitalizations"],
            day["death_confirmed"],
            day["positive_increase"],
            day["death_increase"],
            day["hospitalized_increase"],
            day["tested"],
            day["tested_increase"],
        )

        sql_vars = sql_data + sql_data + (day["reporting_date"],)

        sql = """
            INSERT INTO cases (reporting_date, positive, total_hospitalized, death_confirmed, 
            positive_increase, death_increase, hospitalized_increase, tested, tested_increase)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (reporting_date) DO UPDATE SET
            reporting_date = %s, positive = %s, total_hospitalized = %s, death_confirmed = %s,
            positive_increase = %s, death_increase = %s, hospitalized_increase = %s, tested = %s,
            tested_increase = %s WHERE cases.reporting_date = %s;
        """

        cur.execute(sql, sql_vars)
        if i % 25 == 0:
            conn.commit()
    conn.commit()
    conn.close()


def clean_cases_data(raw_data):
    daily_data = raw_data["features"]
    data = extract_relevant_data(daily_data)
    sorted_data = sorted(data, key=lambda day: day["reporting_date"])
    cleaned_data = add_metric_increases(sorted_data)
    return cleaned_data


def extract_relevant_data(daily_data):
    relevant_data = []
    for day in daily_data:
        properties = day["properties"]
        if not properties["Date"]:
            continue
        data = {
            "reporting_date": reporting_date_to_formatted(properties["Date"]),
            "positive": properties["Cases"],
            "tested": properties["Tested"],
            "death_confirmed": properties["Deaths"],
            "hospitalizations": properties["Hosp"],
        }
        relevant_data.append(data)
    return relevant_data


def add_metric_increases(sorted_data):
    total_days = len(sorted_data)
    for i in range(total_days):
        if i == 0:
            sorted_data[i]["positive_increase"] = sorted_data[i]["positive"]
            sorted_data[i]["death_increase"] = sorted_data[i]["death_confirmed"]
            sorted_data[i]["hospitalized_increase"] = sorted_data[i]["hospitalizations"]
            sorted_data[i]["tested_increase"] = sorted_data[i]["tested"]
        else:
            sorted_data[i]["positive_increase"] = (
                sorted_data[i]["positive"] - sorted_data[i - 1]["positive"]
            )
            sorted_data[i]["death_increase"] = (
                sorted_data[i]["death_confirmed"]
                - sorted_data[i - 1]["death_confirmed"]
            )
            sorted_data[i]["hospitalized_increase"] = (
                sorted_data[i]["hospitalizations"]
                - sorted_data[i - 1]["hospitalizations"]
            )
            sorted_data[i]["tested_increase"] = (
                sorted_data[i]["tested"] - sorted_data[i - 1]["tested"]
            )
    return sorted_data


def reporting_date_to_formatted(date):
    date_time = datetime.strptime(date, "%m/%d/%Y")
    return date_time.strftime("%Y-%m-%d")


def get_raw_case_data():
    res = requests.get(API_URL)
    return res.json()


def save_to_s3(json_data, s3_filename):
    data = json.dumps(json_data).encode("utf-8")
    raw_data = io.BytesIO(data)
    s3_client.upload_fileobj(raw_data, BUCKET, s3_filename)


def format_day(date):
    return date.strftime("%m/%d/%Y")


def next_day():
    new_day = fetch_latest_day_data()["reporting_date"] + timedelta(days=1)
    return format_day(new_day)


def week_before():
    return datetime.utcnow() - timedelta(days=7, hours=7)


def fetch_latest_day_data():
    sql = "SELECT * FROM cases ORDER BY reporting_date DESC LIMIT 1;"
    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()
    cur.execute(sql)
    data = cur.fetchone()
    conn.close()

    if data:
        return {
            "reporting_date": data[0],
        }
    else:
        return {
            "reporting_date": week_before,
        }


def raw_s3_filename():
    today = datetime.today() - timedelta(hours=7)
    return f"data/raw_case_data/{today.strftime('%Y%m%d')}.json"


def clean_s3_filename():
    today = datetime.today() - timedelta(hours=7)
    return f"data/clean_case_data/{today.strftime('%Y%m%d')}.json"


def update_currently_hospitalized():
    # for some reason this stat isn't included in the API
    # and I can only find it on the website, so need to scrape
    # only check and write data if during automated hours
    # to avoid accidental overwrite of good data during
    # debugging or off hours update
    try:
        if datetime.utcnow().hour not in [0, 1, 2, 3, 23]:
            return
        value = get_currently_hospitalized()
        save_currently_hospitalized(value)
    except Exception as e:
        message = f"Unable to successfully fetch currently hospitalized data: {f}"
        topic = "ColoradoCovidData Error - Currently Hospitalized"
        sns_client.publish(
            TopicArn=EMAIL_TOPIC,
            Message=message,
            Subject=subject,
        )
        logger.error(message)


def get_currently_hospitalized():
    website = requests.get("https://covid19.colorado.gov/data").text
    # good luck!
    snippet = website.split(
        "Number of patients currently hospitalized for confirmed COVID-19"
    )[1].split(
        "Patients currently hospitalized as COVID-19 persons under investigation"
    )[
        0
    ]
    data = int(snippet.split('">')[1].split("<")[0])
    return data


def save_currently_hospitalized(value):
    last_day = fetch_latest_day_data()["reporting_date"]

    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()

    sql = "UPDATE cases SET hospitalized_currently = %s WHERE reporting_date = %s;"
    cur.execute(sql, (value, last_day))
    conn.commit()
    conn.close()

    # https://covid19.colorado.gov/data
    # <table border="2" cellpadding="2" cellspacing="1" style="width: 100%;"><thead></thead><tbody><tr><td style="width: 944px;">Percent of facilities updating (within 24 hours)</td>
    #     <td style="width: 240px;">90%</td>
    # </tr><tr><td style="width: 944px;">Number of patients currently hospitalized for confirmed COVID-19
    #
    # </td>
    #     <td style="width: 240px;">
    # 299</td>
    # </tr><tr><td style="width: 944px;">
    #
    # Patients currently hospitalized as COVID-19 persons under investigation</td>
    #     <td style="width: 240px;">54</td>
    # </tr><tr><td style="width: 944px;">Number of patients discharged/transferred within past the 24 hours</td>
    #     <td style="width: 240px;">39</td>
