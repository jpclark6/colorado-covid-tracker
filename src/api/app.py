import os

from flask_lambda import FlaskLambda
from flask import jsonify
import psycopg2
import boto3

app = FlaskLambda(__name__)

DB_CREDENTIALS = os.getenv("DB_CREDENTIALS", None)
client = boto3.client('ssm')
# param = client.get_parameter(Name='CovidDatabaseURL')
# DB_CREDENTIALS = param['Parameter']['Value']


@app.route("/covid-data")
def daily_cases():
    conn = None
    print("DB", DB_CREDENTIALS)
    try:
        conn = psycopg2.connect(DB_CREDENTIALS)
        cur = conn.cursor()
        cases_values = ['reporting_date', 'positive', 'hospitalized_currently', 'death_confirmed', 'positive_increase', 'death_increase', 'hospitalized_increase']
        sql = f'SELECT {", ".join(cases_values)} FROM cases ORDER BY reporting_date DESC;'
        cur.execute(sql)
        data = cur.fetchall()
        formatted_data = format_data(data, cases_values)
    except Exception as e:
        print("Encountered an error", e)
    finally:
        conn.close()

    return jsonify(formatted_data)


def format_data(data, cases_values):
    formatted_data = []
    for entry in data:
        new_data = {}
        for i, value in enumerate(cases_values):
            new_data[value] = entry[i]
            if value == 'reporting_date':
                # hacky way to get date format to not 
                # fail when creating json later on
                new_data[value] = str(entry[i])
        formatted_data.append(new_data)
    return formatted_data


# 7 Day moving average
# SELECT reporting_date,
#        AVG(positive_increase)
#             OVER(ORDER BY reporting_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS avg_positive_increase
# FROM cases;

# 7 Day moving average
# SELECT reporting_date,
#        AVG(daily_qty)
#             OVER(ORDER BY reporting_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS avg_daily_vaccines
# FROM vaccines;
