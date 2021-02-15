import os
import decimal

from flask_lambda import FlaskLambda
from flask import jsonify
import psycopg2
import boto3
from flask_cors import CORS, cross_origin


app = FlaskLambda(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"

client = boto3.client("ssm")

DB_CREDENTIALS = client.get_parameter(Name="/colorado-covid/db_creds")["Parameter"][
    "Value"
]


@app.route("/cases_history/")
@cross_origin()
def daily_cases():
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
    ]
    formatted_data = get_formatted_daily_data(table, values)

    return jsonify(formatted_data)


@app.route("/cases_average/")
@cross_origin()
def daily_averaged_cases():
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

    return jsonify(formatted_data)


@app.route("/vaccines_history/")
@cross_origin()
def daily_vaccines():
    table = "vaccines"
    values = [
        "reporting_date",
        "daily_qty",
        "daily_cumulative",
        "one_dose_increase",
        "one_dose_total",
        "two_doses_increase",
        "two_doses_total",
    ]
    formatted_data = get_formatted_daily_data(table, values)

    return jsonify(formatted_data)


@app.route("/vaccines_average/")
@cross_origin()
def daily_averaged_vaccines():
    """
    Weekly rolling average
    """
    table = "vaccines"
    values = ["reporting_date", "daily_qty", "one_dose_increase", "two_doses_increase"]
    formatted_data = get_formatted_averaged_data(table, values)

    return jsonify(formatted_data)


def get_formatted_daily_data(table, values):
    try:
        sql = f'SELECT {", ".join(values)} FROM {table} ORDER BY reporting_date ASC;'
        data = fetch_data(sql)
        formatted_data = format_data(data, values)
    except Exception as e:
        print("Encountered an error", e)

    return formatted_data


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


@app.route("/data/")
@cross_origin()
def get_all_data():
    daily_cases = get_daily_cases()
    daily_vaccines = get_daily_vaccines()
    ave_cases = get_ave_cases()
    ave_vaccines = get_ave_vaccines()
    return {
        "data": {
            "daily_cases": daily_cases,
            "daily_vaccines": daily_vaccines,
            "ave_cases": ave_cases,
            "ave_vaccines": ave_vaccines,
        }
    }


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
    ]
    formatted_data = get_formatted_daily_data(table, values)
    return formatted_data


def get_ave_vaccines():
    """
    Weekly rolling average
    """
    table = "vaccines"
    values = ["reporting_date", "daily_qty", "one_dose_increase", "two_doses_increase"]
    formatted_data = get_formatted_averaged_data(table, values)
    return formatted_data
