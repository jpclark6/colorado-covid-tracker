import csv
import sys

import psycopg2


if __name__ == "__main__":
    """
    The CSV file for this data is in a strange format
    so this is just a "brute force" approach to loading
    in the DB.
    """
    csv_file = sys.argv[1]
    db_credentials = sys.argv[2]

    lines = []
    with open(csv_file, newline="") as csvfile:
        vaccinereader = csv.reader(csvfile, delimiter=",")
        for row in vaccinereader:
            lines.append(row)
    hospitalized = []
    for line in lines:
        if line[5] == "Confirmed COVID-19":
            hospitalized.append({"reporting_date": line[4], "value": int(line[6])})
    
    conn = psycopg2.connect(db_credentials)
    cur = conn.cursor()
    for day in hospitalized:
        print(day)
        sql = f"UPDATE cases SET hospitalized_currently = {day['value']} WHERE reporting_date = '{day['reporting_date']}';"
        cur.execute(sql)

    conn.commit()
    conn.close()
