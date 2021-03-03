import os
import decimal
from datetime import datetime, timedelta
import logging

from flask_lambda import FlaskLambda
from flask import jsonify, request
import psycopg2
import boto3
from flask_cors import CORS, cross_origin

logger = logging.getLogger()
logger.setLevel(logging.INFO)


app = FlaskLambda(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"

DB_CREDENTIALS = os.getenv("DB_CREDENTIALS")
if not DB_CREDENTIALS:
    logger.error({"error": "no DB credentials found"})

INVALIDATE_CACHE_KEY = os.getenv("INVALIDATE_CACHE_KEY")
if not INVALIDATE_CACHE_KEY:
    logger.error({"error": "no invalidate cache key found"})

todays_data = {} # stores full data set; global var to cache data with Lambda


@app.route("/data/")
@cross_origin()
def get_all_data():
    global todays_data

    if todays_data and data_still_valid(todays_data["last_updated"]):
        logger.info({"status": "using cached data"})
        return todays_data
    else:
        logger.info({"status": "getting new data"})
        daily_cases = get_daily_cases()
        daily_vaccines = get_daily_vaccines()
        ave_cases = get_ave_cases()
        ave_vaccines = get_ave_vaccines()
        todays_data = {
            "data": {
                "daily_cases": daily_cases,
                "daily_vaccines": daily_vaccines,
                "ave_cases": ave_cases,
                "ave_vaccines": ave_vaccines,
            },
            "last_updated": str(datetime.utcnow()),
        }
        logger.info({"status": "successfully retrieved data"})
        return todays_data


@app.route("/invalidate_cache/", methods=["POST"])
def invalidate_cache():
    key = request.headers.get("invalidate-cache-key")
    if key == INVALIDATE_CACHE_KEY:
        global todays_data
        todays_data = None
        return jsonify({"status": "success"})
    else:
        logger.info({"status": "unauthorized request to invalidate cache"})
        return jsonify({"status": "unauthorized"}), 403


@app.route("/health/")
@cross_origin()
def get_health():
    logger.info({"status": "health check ok"})
    return jsonify({"status": "ok"})


# used to check alarm status, eventually remove
@app.route("/throwerror/")
@cross_origin()
def get_error():
    raise Exception("Testing")


def data_still_valid(date):
    """
    Checks if the last updated time is cached, and if it is
    checks whether it is valid. A time is valid for 15 minutes
    or until it is cleared
    """
    current_time = datetime.utcnow()
    last_updated = datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")
    if current_time - last_updated < timedelta(minutes=15):
        return True
    return False


def get_formatted_daily_data(table, values):
    try:
        sql = f'SELECT {", ".join(values)} FROM {table} ORDER BY reporting_date ASC;'
        data = fetch_data(sql)
        formatted_data = format_data(data, values)
        return formatted_data
    except Exception as e:
        print("Encountered an error", e)


def get_formatted_averaged_data(table, values):
    try:
        ave_sql = []
        for value in values[1:]:  # don't average reporting_date
            ave_sql.append(
                f"ROUND(AVG({value}) OVER(ORDER BY reporting_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)) AS avg_{value}"
            )
        sql = f'SELECT reporting_date, {", ".join(ave_sql)} FROM {table} ORDER BY reporting_date ASC;'
        data = fetch_data(sql)
        formatted_data = format_data(data, values)
    except Exception as e:
        print("Encountered an error", e)
    return formatted_data


def fetch_data(sql):
    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()
    cur.execute(sql)
    data = cur.fetchall()
    conn.close()
    return data


def format_data(data, values):
    formatted_data = []
    for entry in data:
        new_data = {}
        for i, value in enumerate(values):
            new_data[value] = entry[i]
            if value == "reporting_date":
                # hacky way to get date format to not
                # fail when creating json later on
                new_data[value] = str(entry[i])
            if isinstance(entry[i], decimal.Decimal):
                new_data[value] = round(
                    float(entry[i]), 2
                )  # psycopg2 returns Decimal, which fails at json.dumps
        formatted_data.append(new_data)
    return formatted_data


def get_daily_cases():
    table = "cases"
    values = [
        "reporting_date",
        "positive",
        "hospitalized_currently",
        "death_confirmed",
        "positive_increase",
        "death_increase",
        "hospitalized_increase",
        "tested",
        "tested_increase",
        "total_hospitalized",
        "created_at",
        "updated_at",
    ]
    formatted_data = get_formatted_daily_data(table, values)
    return formatted_data


def get_ave_cases():
    """
    Weekly rolling average
    """
    table = "cases"
    values = [
        "reporting_date",
        "hospitalized_currently",
        "positive_increase",
        "death_increase",
        "hospitalized_increase",
        "tested_increase",
    ]
    formatted_data = get_formatted_averaged_data(table, values)
    return formatted_data


def get_daily_vaccines():
    table = "vaccines"
    values = [
        "reporting_date",
        "daily_qty",
        "daily_cumulative",
        "one_dose_increase",
        "one_dose_total",
        "two_doses_increase",
        "two_doses_total",
        "daily_pfizer",
        "daily_moderna",
        "pfizer_total",
        "moderna_total",
        "distributed_increase",
        "distrubuted_total",
        "total_vaccine_providers",
        "created_at",
        "updated_at",
    ]

    formatted_data = get_formatted_daily_data(table, values)
    return formatted_data


def get_ave_vaccines():
    """
    Weekly rolling average
    """
    table = "vaccines"
    values = [
        "reporting_date",
        "daily_qty",
        "one_dose_increase",
        "two_doses_increase",
        "daily_pfizer",
        "daily_moderna",
        "distributed_increase",
    ]
    formatted_data = get_formatted_averaged_data(table, values)
    return formatted_data
