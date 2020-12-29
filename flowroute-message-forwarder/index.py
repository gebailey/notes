import base64
import json
import logging

import boto3
import requests

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def load_configuration():
    """Load configuration values from SSM Parameter Store"""

    ssm = boto3.client("ssm")

    config = {}
    for parameter_name in (
        "flowroute_messages_bucket",
        "flowroute_number_map",
        "flowroute_access_key",
        "flowroute_secret_key",
    ):
        try:
            parameter_value = ssm.get_parameter(
                Name=parameter_name, WithDecryption=True
            )["Parameter"]["Value"]
        except Exception:
            log.exception("Exception loading parameter %s:", parameter_name)

        # Attempt to decode value as JSON; but if that fails, store the value directly
        try:
            config[parameter_name] = json.loads(parameter_value)
        except Exception:
            config[parameter_name] = parameter_value

    return config


def send_message(message, config):
    """Send an SMS or MMS message to Flowroute using Messages v2.1 API"""

    log.debug("Sending message: %s", json.dumps(message))

    try:
        response = requests.post(
            "https://api.flowroute.com/v2.1/messages",
            headers={"Content-Type": "application/vnd.api+json"},
            auth=(config["flowroute_access_key"], config["flowroute_secret_key"]),
            json=message,
        )

        log.debug(
            "Response [%d]: %s", response.status_code, json.dumps(response.json())
        )

    except Exception:
        log.exception("Requests library exception:")


def copy_and_generate_urls(media_object_list, config):
    """Copies media from the specified list to S3 and returns a list of signed URLs"""

    s3_client = boto3.client("s3")

    url_list = []
    for media_object in media_object_list:
        try:
            # Retrieve the media object and store it in S3
            boto3.resource("s3").Object(
                config["flowroute_messages_bucket"], media_object["id"]
            ).put(
                Body=requests.get(media_object["attributes"]["url"]).content,
                ContentType=media_object["attributes"]["mime_type"],
            )

            # Generate a presigned URL for the media object
            url_list.append(
                s3_client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={
                        "Bucket": config["flowroute_messages_bucket"],
                        "Key": media_object["id"],
                    },
                )
            )

        except Exception:
            log.exception("Unhandled exception while parsing media object:")

    return url_list


def handler(event, context):
    """Entry point for message handler; expects API Gateway event structure"""

    # Load configuration
    try:
        config = load_configuration()
    except Exception:
        log.exception("Unhandled exception while loading configuration:")
        return {"statusCode": 500, "body": "Internal Server Error"}

    log.debug("Event: %s", json.dumps(event))

    # Parse event
    try:
        if event.get("isBase64Encoded"):
            body = json.loads(base64.b64decode(event["body"]))
        else:
            body = json.loads(event["body"])
    except Exception:
        log.exception("Unhandled exception while parsing event:")
        return {"statusCode": 400, "body": "Bad Request"}

    log.debug("Body: %s", json.dumps(body))

    # Parse body attributes
    try:
        is_mms = body["data"]["attributes"]["is_mms"]

        orig_to = body["data"]["attributes"]["to"]

        if orig_to not in config["flowroute_number_map"]:
            log.info("Unhandled phone number: %s", orig_to)
            return {"statusCode": 200, "body": "OK"}

        orig_from = body["data"]["attributes"]["from"]
        orig_body = body["data"]["attributes"]["body"]

    except Exception:
        log.exception("Unhandled exception while parsing body attributes:")
        return {"statusCode": 400, "body": "Bad Request"}

    message_text = "FWD(%s):" % orig_from
    if orig_body is not None:
        message_text += " " + orig_body

    message_json = {"is_mms": is_mms, "from": orig_to, "body": message_text}

    if is_mms:
        log.debug("Processing MMS message")

        if body["included"]:
            message_json["media_urls"] = copy_and_generate_urls(
                body["included"], config
            )

    else:
        log.debug("Processing SMS message")

    for recipient in config["flowroute_number_map"][orig_to]:
        message_json["to"] = recipient
        send_message(message_json, config)

    return {"statusCode": 200, "body": "OK"}
