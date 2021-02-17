from unittest.mock import MagicMock
from datetime import datetime

import pytest
import boto3
import psycopg2


FROZEN_TIME_AFTER_6PM = datetime(2021, 10, 5, 3, 2, 1, 142314)
FROZEN_TIME_BEFORE_6PM = datetime(2021, 10, 5, 0, 2, 1, 142314)


@pytest.fixture
def mock_return(*args, **kwargs):
    return MagicMock()


@pytest.fixture(scope="function", autouse=True)
def local_api(monkeypatch, mock_return):
    monkeypatch.setattr(boto3, "client", mock_return)
    monkeypatch.setattr(psycopg2, "connect", mock_return)
    from src.api import app

    return app


@pytest.fixture
def freeze_datetime_after_6pm(monkeypatch):
    class ftdatetime:
        @classmethod
        def utcnow(cls):
            return FROZEN_TIME_AFTER_6PM
        
        @classmethod
        def strptime(cls, date, formatting):
            return datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')

    monkeypatch.setattr("src.api.app.datetime", ftdatetime)


@pytest.fixture
def freeze_datetime_before_6pm(monkeypatch):
    class ftdatetime:
        @classmethod
        def utcnow(cls):
            return FROZEN_TIME_BEFORE_6PM
        
        @classmethod
        def strptime(cls, date, formatting):
            return datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')

    monkeypatch.setattr("src.api.app.datetime", ftdatetime)


@pytest.fixture()
def apigw_event():
    """ Generates API GW Event"""

    return {
        "body": "",
        "resource": "/{proxy+}",
        "requestContext": {
            "resourceId": "123456",
            "apiId": "1234567890",
            "resourcePath": "/{proxy+}",
            "httpMethod": "GET",
            "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef",
            "accountId": "123456789012",
            "identity": {
                "apiKey": "",
                "userArn": "",
                "cognitoAuthenticationType": "",
                "caller": "",
                "userAgent": "Custom User Agent String",
                "user": "",
                "cognitoIdentityPoolId": "",
                "cognitoIdentityId": "",
                "cognitoAuthenticationProvider": "",
                "sourceIp": "127.0.0.1",
                "accountId": "",
            },
            "stage": "prod",
        },
        "queryStringParameters": {},
        "headers": {
            "Via": "1.1 08f323deadbeefa7af34d5feb414ce27.cloudfront.net (CloudFront)",
            "Accept-Language": "en-US,en;q=0.8",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Mobile-Viewer": "false",
            "X-Forwarded-For": "127.0.0.1, 127.0.0.2",
            "CloudFront-Viewer-Country": "US",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "X-Forwarded-Port": "443",
            "Host": "1234567890.execute-api.us-east-1.amazonaws.com",
            "X-Forwarded-Proto": "https",
            "X-Amz-Cf-Id": "aaaaaaaaaae3VYQb9jd-nvCd-de396Uhbp027Y2JvkCPNLmGJHqlaA==",
            "CloudFront-Is-Tablet-Viewer": "false",
            "Cache-Control": "max-age=0",
            "User-Agent": "Custom User Agent String",
            "CloudFront-Forwarded-Proto": "https",
            "Accept-Encoding": "gzip, deflate, sdch",
        },
        "pathParameters": {"proxy": "/data/"},
        "httpMethod": "GET",
        "path": "/data/",
    }
