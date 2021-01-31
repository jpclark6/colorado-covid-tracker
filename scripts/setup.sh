#!/bin/sh

read -p 'S3 bucket created by SAM: ' bucket
read -p 'Start date in format yyyymmdd (earliest value is 20200304): ' startdate
read -p 'End date in format yyyymmdd (latest date is yesterday): ' enddate
read -p 'Database Credentials "postgres://<user>:<password>@host/<database>: ' dbcreds
echo

python scripts/migrations.py $dbcreds

python -m scripts.backfill_cases $bucket $startdate $enddate $dbcreds

echo 'Successfully ran migrations and backfilled data'
