import logging
import os

import requests
import boto3


logger = logging.getLogger()
logger.setLevel(logging.INFO)

API_GATEWAY_URL = os.getenv("API_URL")
if not API_GATEWAY_URL:
    logger.error({"error": "no API Gateway URL credentials env var found"})
EMAIL_TOPIC = os.getenv("EMAIL_TOPIC")
if not EMAIL_TOPIC:
    logger.error({"error": "no SNS Topic credentials env var found"})
FRONTEND_URL = "https://coloradocoviddata.com"
sns_client = boto3.client("sns")


def handler(event=None, context=None):
    return_message = ""
    response = requests.get(API_GATEWAY_URL + "/data/")
    if response.status_code != 200 or len(response.text) < 100000:
        message = "API endpoint acting weird"
        topic = "ColoradoCovidData Error - API"
        sns_client.publish(
            TopicArn=EMAIL_TOPIC,
            Message=message,
            Subject=subject,
        )
        logger.error(message)
    else:
        logger.info("Data looks good")

    response = requests.get(FRONTEND_URL)
    if response.status_code != 200 or len(response.text) < 1000:
        message = "Front end unreachable"
        topic = "ColoradoCovidData Error - Frontend"
        sns_client.publish(
            TopicArn=EMAIL_TOPIC,
            Message=message,
            Subject=subject,
        )
        logger.error(message)
    else:
        logger.info("Front end looks good")
    return "Success"