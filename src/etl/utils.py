from datetime import datetime, timedelta


def yesterday_formatted():
    yesterday = datetime.today() - timedelta(days=1)
    return yesterday.strftime("%Y%m%d")  # yyyymmdd


def get_data(s3_filename, bucket):
    response = s3.get_object(
        Bucket=bucket,
        Key=s3_filename,
    )
    return json.loads(response["Body"].read())


def save_data(s3_filename, data, bucket):
    s3_data = io.BytesIO(json.dumps(data).encode("utf-8"))
    s3.upload_fileobj(s3_data, bucket, s3_filename)


def date_to_sql_date(date):
    date_time = datetime.strptime(date, "%Y%m%d")
    return date_time.strftime("%Y-%m-%d")
