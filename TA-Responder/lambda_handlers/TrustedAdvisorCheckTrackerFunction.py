"""TrustedAdvisorCheckTrackerFunction - Logic for tracking the most recent status of TA checks in a DDB table"""

import hashlib
import logging
import time

import boto3
import dateutil.parser

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger()

DDB_TABLE_NAME = "TrustedAdvisorCheckTrackerTable"


def convert_to_epoch(datetime_str):
    return int(time.mktime(dateutil.parser.parse(datetime_str).timetuple()))


def lambda_handler(event, context):
    # Parse the Trusted Advisor event data
    detail = event.get("detail", {})
    check_name = detail.get("check-name")
    check_item_detail = detail.get("check-item-detail", {})
    status = check_item_detail.get("Status")
    last_updated_time_str = check_item_detail.get("Last Updated Time")
    last_updated_time_epoch = convert_to_epoch(last_updated_time_str)
    resource = check_item_detail.get("Resource")
    region = check_item_detail.get("Region")

    # Create a hash key from check_name, resource and region
    hash_key = hashlib.sha256(
        (check_name + resource + region).encode("utf-8")
    ).hexdigest()

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(DDB_TABLE_NAME)

    # Check if the item already exists in the table
    existing_item = table.get_item(Key={"hashKey": hash_key, "resource": resource}).get(
        "Item"
    )

    if existing_item:
        existing_time_epoch = existing_item.get("lastUpdatedTimeEpoch")

        # Update the existing item with new values. Only if the check update is more recent than
        # what is recorded in the DDB TrustedAdvisorCheckTrackerTable
        if last_updated_time_epoch > existing_time_epoch:
            table.put_item(
                Item={
                    "hashKey": hash_key,
                    "checkName": check_name,
                    "resourceStatus": status,
                    "lastUpdatedTime": last_updated_time_str,
                    "lastUpdatedTimeEpoch": last_updated_time_epoch,
                    "resource": resource,
                    "region": region,
                }
            )
        else:
            logger.info(
                f"Skipping update for {hash_key}/{check_name} as the existing time is more recent."
            )
    else:
        # Create a new item in the table
        table.put_item(
            Item={
                "hashKey": hash_key,
                "checkName": check_name,
                "resourceStatus": status,
                "lastUpdatedTime": last_updated_time_str,
                "lastUpdatedTimeEpoch": last_updated_time_epoch,
                "resource": resource,
                "region": region,
            }
        )

    return
