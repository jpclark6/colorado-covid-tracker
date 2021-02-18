#!/bin/sh

read -p 'S3 bucket created by SAM: ' bucket
read -p 'Start date in format yyyymmdd (earliest value is 20200304): ' startdate
read -p 'End date in format yyyymmdd (latest date is yesterday): ' enddate
read -p 'Database Credentials "postgres://<user>:<password>@host/<database>: ' dbcreds
read -p 'COVID vaccine data file name (Ex. covid19_vaccine_2021-01-31.csv): ' vaccinefile
echo

python scripts/migrations.py $dbcreds

## Cases no longer needed, they will fill in on the first Lambda run
# python -m scripts.backfill_cases $bucket $startdate $enddate $dbcreds

## Vaccine data comes from a Google Doc object for the history, but from 
## the website for daily new data so you have to backfill it manually
python scripts/backfill_vaccines.py scripts/data_files/$vaccinefile $dbcreds

echo 'Successfully ran migrations and backfilled data'
