#!/bin/sh

read -p 'Database Credentials "postgres://<user>:<password>@host/<database>: ' dbcreds


python scripts/migrations.py $dbcreds

echo 'Successfully ran migrations'
echo 'Next run "backfill_hospital.py" after you get the latest hospital data file from https://drive.google.com/drive/folders/1bjQ7LnhU8pBR3Ly63341bCULHFqc7pMw'
