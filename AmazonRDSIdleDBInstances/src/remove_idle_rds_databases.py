import boto3
import json
import os


def lambda_handler(event, context):
    # Get Trusted Advisor event details
    region = event["detail"]["check-item-detail"]["Region"]
    last_connection = int(
        str(event["detail"]["check-item-detail"]["Days Since Last Connection"]).strip(
            "+"
        )
    )
    min_age = int(os.environ["MIN_AGE"])
    termination_method = os.environ["TERMINATION_METHOD"]
    db_instance_name = event["detail"]["check-item-detail"]["DB Instance Name"]

    if last_connection < min_age:
        print(
            f"Database instance {db_instance_name} does not meet the minimum threshold for termination. Skipping."
        )
        return

    if termination_method == "delete":
        return delete_db_instance(
            db_instance_name, boto3.client("rds", region_name=region)
        )
    elif termination_method == "stop":
        return stop_db_instance(
            db_instance_name, boto3.client("rds", region_name=region)
        )


def send_sns_message(message):
    sns_topic = os.environ["SNS_TOPIC_ARN"]
    if sns_topic == "":
        print("SNS topic not set. Skipping SNS message.")
        return
    try:
        sns = boto3.client("sns")
        sns.publish(
            TopicArn=sns_topic,
            Subject=f"RDS Idle Database Termination Notification ({os.environ['ACCOUNT_ID']})",
            Message=message,
            MessageStructure="string",
        )

    except Exception as e:
        print(f"Error sending SNS message - {e}")


def delete_db_instance(db_instance_name, rds_client) -> dict:
    final_snapshot_identifier = db_instance_name + "-final-snapshot"
    try:
        rds_client.delete_db_instance(
            DBInstanceIdentifier=db_instance_name,
            FinalDBSnapshotIdentifier=final_snapshot_identifier,
        )
        print(f"Database instance deleted - {db_instance_name}")
        message = f"Database instance {db_instance_name} has been deleted.\nFinal snapshot: {final_snapshot_identifier}"
        send_sns_message(message)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Database instance deleted"}),
        }
    except Exception as e:
        print(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error deleting database instance"}),
        }


def stop_db_instance(db_instance_name, rds_client) -> dict:
    try:
        rds_client.stop_db_instance(DBInstanceIdentifier=db_instance_name)
        print(f"Database instance stopped - {db_instance_name}")
        message = f"Database instance {db_instance_name} has been stopped."
        send_sns_message(message)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Database instance stopped"}),
        }
    except Exception as e:
        print(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error stopping database instance"}),
        }
