import csv
import sys

import psycopg2


if __name__ == "__main__":
    '''
    The CSV file for this data is in a strange format
    so this is just a "brute force" approach to loading
    in the DB.
    '''
    csv_file = sys.argv[1]
    db_credentials = sys.argv[2]

    lines = []
    with open(csv_file, newline='') as csvfile:
        vaccinereader = csv.reader(csvfile, delimiter=',')
        for row in vaccinereader:
            lines.append(row)
    daily = []
    daily_cumulative = []
    data = {}
    for line in lines:
        if 'All COVID Vaccines' in line and 'Vaccine Administration' in line:
            if line[2] == 'Daily':
                if data.get(line[4]):
                    data[line[4]]['daily'] = int(line[5])
                else:
                    data[line[4]] = {'daily': int(line[5])}
            elif line[2] == 'Cumulative Daily':
                if data.get(line[4]):
                    data[line[4]]['daily_cumulative'] = int(line[5])
                else:
                    data[line[4]] = {'daily_cumulative': int(line[5])}

    conn = psycopg2.connect(db_credentials)
    cur = conn.cursor()

    for day in data:
        sql_data = (
            day,
            data[day]['daily'],
            data[day]['daily_cumulative'],
        )
        cur.execute(
            """
                INSERT INTO vaccines (reporting_date, daily_qty, daily_cumulative)
                VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;
                """,
            sql_data,
        )
        conn.commit()

    conn.close()

