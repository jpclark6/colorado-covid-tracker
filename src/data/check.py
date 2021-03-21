"""
Checks data once per day on a cron job to make sure data is
in the database. Check late in the evening MST
"""
import os
from datetime import datetime
import logging

import boto3
import psycopg2

logger = logging.getLogger()
logger.setLevel(logging.INFO)


DB_CREDENTIALS = os.getenv("DB_CREDENTIALS")
if not DB_CREDENTIALS:
    logger.error({"error": "no DB credentials env var found"})

EMAIL_TOPIC = os.getenv("EMAIL_TOPIC")
if not EMAIL_TOPIC:
    logger.error({"error": "no SNS Topic credentials env var found"})
sns_client = boto3.client("sns")


def handler(event=None, context=None):
    """
    Check if the database is up to date
    """
    latest_day_cases = fetch_latest_day_data("cases")
    latest_day_vaccines = fetch_latest_day_data("vaccines")
    today = datetime.utcnow()

    message = "Could not find current data for the following table(s): "
    tables = []
    if latest_day_cases[0].day != today.day - 1:  # sub 1 for UTC
        tables.append("Cases")
    if not latest_day_cases[2]:  # check if web scraping for currently hospitalized worked
        tables.append("Currently Hospitalized")
    if latest_day_vaccines[0].day != today.day - 1:  # sub 1 for UTC
        tables.append("Vaccines")
    if tables:
        message += ", ".join(tables)
        message += "\nGood luck!"
        subject = "ColoradoCovidData Missing Data"
        sns_client.publish(
            TopicArn=EMAIL_TOPIC,
            Message=message,
            Subject=subject,
        )
        logger.error(message)
        return "Missing data"
    else:
        logger.info("Data looks good")
        return "Data looks good"


def fetch_latest_day_data(table):
    sql = f"SELECT * FROM {table} ORDER BY reporting_date DESC LIMIT 1;"
    conn = psycopg2.connect(DB_CREDENTIALS)
    cur = conn.cursor()
    cur.execute(sql)
    data = cur.fetchone()
    conn.close()
    return data  # latest date datetime object
