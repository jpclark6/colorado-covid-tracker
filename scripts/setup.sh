#!/bin/sh

read -p 'Database Credentials "postgres://<user>:<password>@host/<database>: ' dbcreds


python scripts/migrations.py $dbcreds

echo 'Successfully ran migrations'
