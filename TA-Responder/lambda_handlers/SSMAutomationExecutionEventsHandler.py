"""SSMAutomationExecutionEventsHandler - Lambda function for handling events sourced from the EventBridge rule related to SSM Automation Execution completions"""

import logging

import boto3

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger()

dynamodb_client = boto3.resource("dynamodb")
ssm_client = boto3.client("ssm")

table_name = "AutomationExecutionTrackerTable"


def lambda_handler(event, context):
    # Get the detail from the event
    detail = event["detail"]
    execution_id = detail["ExecutionId"]
    automation_execution_document_name = detail["Definition"]
    automation_execution_status = detail["Status"]

    # Get the item from the DynamoDB table
    table = dynamodb_client.Table(table_name)
    response = table.get_item(Key={"automationExecutionId": execution_id})
    item = response.get("Item")

    if item:
        ops_item_id = item["opsItemId"]
        region = item["region"]

        if automation_execution_status == "Success":
            # Update the OpsItem with Resolved status
            ssm_client.update_ops_item(
                OpsItemId=ops_item_id,
                Status="Resolved",
                OperationalData={
                    "trustedAdvisorCheckAutoRemediation": {
                        "Type": "String",
                        "Value": f"DocumentName: {automation_execution_document_name}, ExecutionId: {execution_id}, Status: {automation_execution_status}, Region: {region}",
                    }
                },
            )
        else:
            # Update the OpsItem with the execution status
            ssm_client.update_ops_item(
                OpsItemId=ops_item_id,
                OperationalData={
                    "trustedAdvisorCheckAutoRemediation": {
                        "Type": "String",
                        "Value": f"DocumentName: {automation_execution_document_name}, ExecutionId: {execution_id}, Status: {automation_execution_status}, Region: {region}",
                    }
                },
            )
        # Delete the item from the DynamoDB table
        table.delete_item(Key={"automationExecutionId": execution_id})
        logger.info(
            f"Deleted item with automationExecutionId {execution_id} from DynamoDB table"
        )

    return
