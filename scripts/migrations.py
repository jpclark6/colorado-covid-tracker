import sys

import psycopg2


"""
This script creates the tables in the database
Run using command line 'python scripts/migrations.py'
"""


db_creds = input('Database Credentials "postgres://<user>:<password>@host/<database>: ')

conn = psycopg2.connect(db_creds)
cur = conn.cursor()

sql = "CREATE TABLE IF NOT EXISTS cases (reporting_date date PRIMARY KEY, positive integer, hospitalized_currently integer, total_hospitalized integer, death_confirmed integer, positive_increase integer, death_increase integer, hospitalized_increase integer, tested integer, tested_increase integer);"
cur.execute(sql)

sql = """CREATE TABLE IF NOT EXISTS vaccines (reporting_date date PRIMARY KEY, 
    daily_qty integer, daily_cumulative integer, one_dose_increase integer, one_dose_total integer, 
    two_doses_increase integer, two_doses_total integer, daily_pfizer integer, daily_moderna integer,
    pfizer_total integer, moderna_total integer, distributed_increase integer, distrubuted_total integer, 
    total_vaccine_providers integer);"""

cur.execute(sql)

conn.commit()
conn.close()

print("Successfully ran migrations")
