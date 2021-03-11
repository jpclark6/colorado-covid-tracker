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
    "https://opendata.arcgis.com/datasets/a681d9e9f61144b2977badb89149198c_0.geojson"
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
        raw_data = get_raw_vaccine_data()

        if new_day_formatted() in str(raw_data):
            s3_filename = raw_s3_filename()
            logger.info(f"New data found. Saving to s3://{BUCKET}/{s3_filename}")
            save_to_s3(raw_data, s3_filename)

            logger.info("Saved to S3. Cleaning data")
            clean_data = clean_vaccine_data(raw_data)

            s3_filename = clean_s3_filename()
            logger.info(f"Saving cleaned data to s3://{BUCKET}/{s3_filename}")
            save_to_s3(clean_data, s3_filename)

            logger.info("Saving cleaned data to database")
            save_vaccine_data_to_db(clean_data)
            log_update_time(new_data=True)

            logger.info("Success")
            invalidate_cache()
        else:
            logger.info("Data not updated yet")
            log_update_time(new_data=False)
    except Exception as e:
        message = f"Encountered an error during Vaccine data fetching: {f}"
        topic = "ColoradoCovidData Error - Vaccines"
        sns_client.publish(
            TopicArn=EMAIL_TOPIC,
            Message=message,
            Subject=subject,
        )
        logger.error(message)


def invalidate_cache():
    headers = {"invalidate-cache-key": INVALIDATE_CACHE_KEY}

    response = requests.post(API_GATEWAY_URL + "/invalidate_cache/", headers=headers)
    if response.status_code == 200:
        logger.info("Successfully invalidated cache")
    else:
        logger.info("Failed to invalidate cache")


def log_update_time(new_data=False):
    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO invokes (function_name, invoke_time, new_data) VALUES (%s, now(), %s)",
        ("vaccines", new_data),
    )
    conn.commit()
    conn.close()


def save_vaccine_data_to_db(clean_data):
    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()
    i = 0
    for day in clean_data:
        i += 1

        sql_date = reporting_date_to_formatted(day.get("date"))
        sql_data = (
            sql_date,
            day.get("daily_increase"),
            day.get("daily_cumulative"),
            day.get("one_dose_increase"),
            day.get("one_dose_cumulative"),
            day.get("fully_immunized_increase"),
            day.get("fully_immunized_cumulative"),
            day.get("pfizer_daily"),
            day.get("moderna_daily"),
            day.get("pfizer_cumulative"),
            day.get("moderna_cumulative"),
            day.get("distributed_increase"),
            day.get("distributed_cumulative"),
            day.get("total_vaccine_providers"),
            day.get("jandj_daily"),
            day.get("jandj_cumulative"),
        )

        sql_vars = sql_data + sql_data + (sql_date,)

        sql = """
            INSERT INTO vaccines (reporting_date, daily_qty, daily_cumulative, one_dose_increase, 
            one_dose_total, fully_immunized_increase, fully_immunized_total, daily_pfizer, daily_moderna,
            pfizer_total, moderna_total, distributed_increase, distrubuted_total, total_vaccine_providers,
            daily_jandj, jandj_total)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (reporting_date) DO UPDATE SET
            reporting_date = %s, daily_qty = %s, daily_cumulative = %s, one_dose_increase = %s,
            one_dose_total = %s, fully_immunized_increase = %s, fully_immunized_total = %s, daily_pfizer = %s, daily_moderna = %s,
            pfizer_total = %s, moderna_total = %s, distributed_increase = %s, distrubuted_total = %s, total_vaccine_providers = %s,
            daily_jandj = %s, jandj_total = %s
            WHERE vaccines.reporting_date = %s;
        """

        cur.execute(sql, sql_vars)
        if i % 25 == 0:
            conn.commit()

    conn.commit()
    conn.close()


def fetch_latest_day_data():
    sql = "SELECT * FROM vaccines ORDER BY reporting_date DESC LIMIT 1;"
    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()
    cur.execute(sql)
    response = cur.fetchone()
    conn.close()
    if response:
        return {
            "reporting_date": response[0],
            "daily": response[2],
            "one_dose": response[4],
            "fully_immunized": response[6],
        }
    else:
        return {
            "reporting_date": yesterday(),
        }


def format_day(date):
    return date.strftime("%m/%d/%Y")


def new_day_formatted():
    new_day = fetch_latest_day_data()["reporting_date"] + timedelta(days=1)
    return format_day(new_day)


def yesterday():
    return datetime.utcnow() - timedelta(days=2, hours=7)


def update_day(days, reporting_date, key, value):
    if days.get(reporting_date):
        days[reporting_date][key] = value
    else:
        days[reporting_date] = {key: value}


def clean_vaccine_data(raw_data):
    daily_data = extract_vaccine_data(raw_data)
    administration_counts, state_counts = filter_latest_vaccine_data(daily_data)
    flattened_data = flatten_data(administration_counts)
    combined_data = combine_counts(flattened_data, state_counts)
    sorted_data = sort_data(combined_data)
    standardized_data = standardize_metric_names(sorted_data)
    cleaned_data = add_metric_increases(standardized_data)

    return cleaned_data


def extract_vaccine_data(raw_data):
    daily_data = raw_data["features"]
    return [day["properties"] for day in daily_data]


def filter_latest_vaccine_data(daily_data):
    administration_counts = []
    state_counts = []
    new_day = new_day_formatted()
    for cat in daily_data:
        if (
            cat["publish_date"] == new_day
            and cat["category"] == "Administration"
            and cat["metric"] != "Weekly"
            and cat["type"] != "Unspecified COVID Vaccine"
        ):
            administration_counts.append(cat)
        if (
            cat["category"] == "Cumulative counts to date"
            and cat["section"] == "State Data"
        ):
            state_counts.append(cat)
            state_counts[-1]["date"] = state_counts[-1]["publish_date"]
    return administration_counts, state_counts


def flatten_data(days):
    new_day = new_day_formatted()
    return [
        {
            "metric": day["metric"],
            "type": day["type"],
            "date": day["date"],
            "value": day["value"],
            "publish_date": day["publish_date"],
        }
        for day in days
        if day["publish_date"] == new_day
    ]


def combine_counts(flattened_data, state_counts):
    combined_daily = {}
    for day in flattened_data:
        if not combined_daily.get(day["date"]):
            combined_daily[day["date"]] = {}
        try:
            combined_daily[day["date"]][day["type"] + " " + day["metric"]] = day[
                "value"
            ]
        except:
            combined_daily[day["date"]][day["metric"]] = day["value"]

    for day in state_counts:
        if not combined_daily.get(day["date"]):
            combined_daily[day["date"]] = {}
        combined_daily[day["date"]][day["metric"]] = day["value"]

    return [{"date": day[0], **day[1]} for day in combined_daily.items()]


def standardize_metric_names(sorted_data):
    replacements = {
        "All COVID Vaccines Cumulative Daily": "daily_cumulative",
        "Moderna Cumulative Daily": "moderna_cumulative",
        "Pfizer Cumulative Daily": "pfizer_cumulative",
        "Janssen Cumulative Daily": "jandj_cumulative",
        "All COVID Vaccines Daily": "daily",
        "Moderna Daily": "moderna_daily",
        "Pfizer Daily": "pfizer_daily",
        "Janssen Daily": "jandj_daily",
        "People Immunized with One Dose": "one_dose_cumulative",
        "People Fully Immunized": "fully_immunized_cumulative",
        "date": "date",
        "Cumulative Doses Administered": "daily_cumulative_2",
        "Cumulative Doses Distributed": "distributed_cumulative",
        "Total Vaccine Providers": "total_vaccine_providers",
    }
    updated_data = []
    for day in sorted_data:
        temp_day = {}
        for key, val in day.items():
            if "Weekly" in key:
                continue
            try:
                temp_day[replacements[key]] = val
            except KeyError:
                logger.error(f"Found unknown key: {key}")
        updated_data.append(temp_day)

    for day in updated_data:
        if day.get("daily_cumulative_2"):
            day["daily_cumulative"] = day.get("daily_cumulative_2")
            del day["daily_cumulative_2"]
        if day.get("daily"):  # confusing metric that isn't what it says
            del day["daily"]
    return updated_data


def add_metric_increases(standardized_data):
    total_days = len(standardized_data)
    for i in range(total_days):
        if i == 0:
            standardized_data[i]["daily_increase"] = standardized_data[i].get(
                "daily_cumulative"
            )
            standardized_data[i]["distributed_increase"] = standardized_data[i].get(
                "distributed_cumulative"
            )
            standardized_data[i]["one_dose_increase"] = standardized_data[i].get(
                "one_dose_cumulative"
            )
            standardized_data[i]["fully_immunized_increase"] = standardized_data[i].get(
                "fully_immunized_cumulative"
            )
        else:
            try:
                standardized_data[i]["daily_increase"] = standardized_data[i].get(
                    "daily_cumulative"
                ) - standardized_data[i - 1].get("daily_cumulative", 0)
            except TypeError:
                standardized_data[i]["daily_increase"] = None

            try:
                standardized_data[i]["distributed_increase"] = standardized_data[i].get(
                    "distributed_cumulative"
                ) - standardized_data[i - 1].get("distributed_cumulative", 0)
            except TypeError:
                standardized_data[i]["distributed_increase"] = None

            try:
                standardized_data[i]["one_dose_increase"] = standardized_data[i].get(
                    "one_dose_cumulative"
                ) - standardized_data[i - 1].get("one_dose_cumulative", 0)
            except TypeError:
                standardized_data[i]["one_dose_increase"] = None
            try:
                standardized_data[i]["fully_immunized_increase"] = standardized_data[i].get(
                    "fully_immunized_cumulative"
                ) - standardized_data[i - 1].get("fully_immunized_cumulative", 0)
            except TypeError:
                standardized_data[i]["fully_immunized_increase"] = None
    return standardized_data


def sort_data(combined_data):
    return sorted(
        combined_data, key=lambda day: datetime.strptime(day["date"], "%m/%d/%Y")
    )


def reporting_date_to_formatted(date):
    date_time = datetime.strptime(date, "%m/%d/%Y")
    return date_time.strftime("%Y-%m-%d")


def get_raw_vaccine_data():
    res = requests.get(API_URL)
    return res.json()


def save_to_s3(json_data, s3_filename):
    data = json.dumps(json_data).encode("utf-8")
    raw_data = io.BytesIO(data)
    s3_client.upload_fileobj(raw_data, BUCKET, s3_filename)


def today_formatted():
    today = datetime.today() - timedelta(hours=7)
    return today.strftime("%m/%d/%Y")


def yesterday_formatted():
    today = datetime.today() - timedelta(days=1, hours=7)
    return today.strftime("%m/%d/%Y")


def raw_s3_filename():
    today = datetime.today() - timedelta(hours=7)
    return f"data/raw_vaccine_data/{today.strftime('%Y%m%d')}.json"


def clean_s3_filename():
    today = datetime.today() - timedelta(hours=7)
    return f"data/clean_vaccine_data/{today.strftime('%Y%m%d')}.json"
