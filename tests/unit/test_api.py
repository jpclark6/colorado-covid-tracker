import json
from unittest.mock import MagicMock

import pytest
import boto3
import psycopg2


def test_data_endpoint(monkeypatch, apigw_event, mocker, local_api, freeze_datetime):
    def daily_cases():
        return {"mock": "daily_cases"}

    def daily_vaccines():
        return {"mock": "daily_vaccines"}

    def ave_cases():
        return {"mock": "ave_cases"}

    def ave_vaccines():
        return {"mock": "ave_vaccines"}

    monkeypatch.setattr(local_api, "get_daily_cases", daily_cases)
    monkeypatch.setattr(local_api, "get_daily_vaccines", daily_vaccines)
    monkeypatch.setattr(local_api, "get_ave_cases", ave_cases)
    monkeypatch.setattr(local_api, "get_ave_vaccines", ave_vaccines)

    ret = local_api.app(apigw_event, "")
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert data['data']['daily_cases'] == daily_cases()
    assert data['data']['daily_vaccines'] == daily_vaccines()
    assert data['data']['ave_cases'] == ave_cases()
    assert data['data']['ave_vaccines'] == ave_vaccines()
    assert data['last_updated'] == '2021-10-05 03:02:01.142314'


def test_valid_cached_response(monkeypatch, apigw_event, mocker, local_api, freeze_datetime):
    mock_passing_date = {"data": "mock", "last_updated": '2021-10-05 03:12:01.142314'}
    local_api.todays_data = mock_passing_date

    ret = local_api.app(apigw_event, "")
    data = json.loads(ret["body"])

    assert data == mock_passing_date


def test_expired_data(monkeypatch, apigw_event, local_api, freeze_datetime):
    invalid_datetime = '2021-10-05 02:45:01.142314'
    still_valid = local_api.data_still_valid(invalid_datetime)

    assert still_valid == False


def test_valid_data(monkeypatch, apigw_event, local_api, freeze_datetime):
    invalid_datetime = '2021-10-05 02:50:01.142314'
    still_valid = local_api.data_still_valid(invalid_datetime)

    assert still_valid == True


def test_get_formatted_daily_data(monkeypatch, local_api):
    actual = local_api.format_data([['11', '12'], ['21', '22'], ['31', '32']], ['first', 'second'])
    expected = [{'first': '11', 'second': '12'}, {'first': '21', 'second': '22'}, {'first': '31', 'second': '32'}]

    assert actual == expected
