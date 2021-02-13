import sys

import psycopg2


"""
This script creates the tables in the database
Run with command line argument for database credentials 
in the form 'postgres://<user>:<pw>@host/database'
  Ex. python scripts/migrations.py postgres://<user>:<pw>@host/database
"""


db_creds = sys.argv[1]

conn = psycopg2.connect(db_creds)
cur = conn.cursor()

sql = "CREATE TABLE IF NOT EXISTS cases (reporting_date date PRIMARY KEY, positive integer, hospitalized_currently integer, death_confirmed integer, positive_increase integer, death_increase integer, hospitalized_increase integer, tested integer, tested_increase integer);"
cur.execute(sql)

sql = "CREATE TABLE IF NOT EXISTS vaccines (reporting_date date PRIMARY KEY, daily_qty integer, daily_cumulative integer, one_dose_increase, one_dose_total integer, two_doses_increase, two_doses_total integer);"
cur.execute(sql)

conn.commit()
conn.close()

print("Successfully ran migrations")
