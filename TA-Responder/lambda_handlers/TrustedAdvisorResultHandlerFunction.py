"""TrustedAdvisorResultHandler - Lambda function ingesting events from the DDB TrustedAdvisorCheckTrackerTable event stream. This function has the logic for creating OpsItems and executing SSM Automation Documents (if mapping configuration is in place)"""

import json
import logging
import os
import re

import boto3
from botocore.exceptions import ClientError

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger()

AUTOMATION_MAPPING_DDB_TABLE_NAME = "AutomationMappingTable"
AUTOMATION_EXECUTION_TRACKER_DDB_TABLE_NAME = "AutomationExecutionTrackerTable"
AUTOMATION_DOCUMENT_INVOKE_MODEL = "taResponderAutomationDocumentInvokeModel"
AUTOMATION_DOCUMENT_INVOKE_MODEL_ROLE = os.environ[
    "AUTOMATION_DOCUMENT_INVOKE_MODEL_ROLE"
]
GEN_AI_RECOMMENDATIONS_ENABLED = (
    os.environ["GEN_AI_RECOMMENDATIONS_ENABLED"].lower() == "true"
)


def _replace_resource_id(automation_parameters, resource_id):
    """
    Replace any instance of '$resourceId' in the 'automation_parameters' object with the value of 'resource_id'

    :param automation_parameters: The automation parameters object with instances of the '$resourceId' variable
    :param resource_id: The resource ID to include in the automation parameters object
    :return: The modified automation parameters object
    """
    if isinstance(automation_parameters, dict):
        for key, value in automation_parameters.items():
            if isinstance(value, str):
                automation_parameters[key] = value.replace("$resourceId", resource_id)
            elif isinstance(value, (dict, list)):
                automation_parameters[key] = _replace_resource_id(value, resource_id)
    elif isinstance(automation_parameters, list):
        for i, item in enumerate(automation_parameters):
            if isinstance(item, str):
                automation_parameters[i] = item.replace("$resourceId", resource_id)
            elif isinstance(item, (dict, list)):
                automation_parameters[i] = _replace_resource_id(item, resource_id)
    return automation_parameters


def _create_ops_item(check_name, resource_arn, operational_data):
    """
    Create an OpsItem in SSM with the provided check name, resource ARN, and operational data.

    :param check_name: Name of the Trusted Advisor check
    :param resource_arn: ARN of the resource
    :param operational_data: Operational data for the OpsItem
    :return: OpsItem ID if successful, None otherwise
    """
    try:
        ssm_ops_item_client = boto3.client("ssm")
        ops_item = ssm_ops_item_client.create_ops_item(
            Description=f"{check_name}: {resource_arn}",
            OperationalData=operational_data,
            Source="Trusted Advisor",
            Title=f"[TA] [{check_name}] [{resource_arn}]",
        )
        ops_item_id = ops_item["OpsItemId"]
        logger.info(f"OpsItem {ops_item_id} created for resource {resource_arn}")

    except Exception as e:
        # Check if the error is OpsItemAlreadyExistsException
        if e.response["Error"]["Code"] == "OpsItemAlreadyExistsException":
            ops_item_id = e.response["OpsItemId"]
            logger.info(f"OpsItem {ops_item_id} already exists for {resource_arn}")
        else:
            logger.error(f"Error creating OpsItem for resource {resource_arn}: {e}")
            return None

    return ops_item_id


def _put_item_in_automation_execution_ddb(automation_execution_id, ops_item_id, region):
    """
    Create item in AutomationExecutionTrackerTable DDB table with the OpsItem Id and SSM Automation Document execution Id.
    This allows SSMAutomationExecutionEventsHandler Lambda function to track the execution of the SSM Automation Document and update the corresponding OpsItem.

    :param automation_execution_id: SSM Automation Document execution Id
    :param ops_item_id: OpsItem Id
    :param region: AWS region
    :return: None
    """
    try:
        dynamodb = boto3.resource("dynamodb")
        automation_execution_table = dynamodb.Table(
            AUTOMATION_EXECUTION_TRACKER_DDB_TABLE_NAME
        )
        automation_execution_table.put_item(
            Item={
                "automationExecutionId": automation_execution_id,
                "opsItemId": ops_item_id,
                "region": region,
            }
        )

    except ClientError as e:
        logger.error(
            f"Error adding item to DDB AutomationExecutionTrackerTable for execution {automation_execution_id} and OpsItem {ops_item_id}: {e}"
        )


def _start_automation_execution(document_name, automation_parameters, region):
    """
    Start an SSM automation execution based on the provided document name and parameters.

    :param document_name: Name of the SSM automation document
    :param automation_parameters: Parameters for the SSM automation execution
    :param region: AWS region
    :return: Automation execution ID, or None if an error occurred
    """
    try:
        ssm_document_execution_client = boto3.client("ssm", region_name=region)
        automation_execution = ssm_document_execution_client.start_automation_execution(
            DocumentName=document_name, Parameters=automation_parameters
        )

        automation_execution_id = automation_execution["AutomationExecutionId"]

        logger.info(f"Automation execution started: {automation_execution_id}")

    except ClientError as e:
        logger.error(f"Error starting the automation execution: {e}")
        return None

    return automation_execution_id


def _get_ddb_mapping_item(check_name):
    """
    Retrieve the mapping item from the AutomationMappingTable DDB table based on the check name.
    Example of mapping item:
    {
        "checkName": {
            "S": "Security groups should not allow unrestricted access to ports with high risk"
        },
        "ssmAutomationDocument": {
            "S": "AWS-DisablePublicAccessForSecurityGroup"
        },
        "regexPattern": {
            "S": "(sg-\\w+)"
        },
        "automationParameters": {
            "S": "{\"GroupId\": [\"$resourceId\"], \"AutomationAssumeRole\": [\"arn:aws:iam::0123456789012:role/TA-ControlPlane-Test-AutomationRole\"]}"
        },
        "automationStatus": {
            "BOOL": true
        }
    }

    :param check_name: Name of the Trusted Advisor check
    :return: Mapping item from the DDB table, or None if not found
    """
    try:
        dynamodb = boto3.resource("dynamodb")
        automation_mapping_table = dynamodb.Table(AUTOMATION_MAPPING_DDB_TABLE_NAME)
        get_item_response = automation_mapping_table.get_item(
            Key={"checkName": check_name}
        )
        mapping_item = (
            get_item_response["Item"] if "Item" in get_item_response else None
        )

    except ClientError as e:
        logger.warning(
            f"Error retrieving mapping item from DDB AutomationMappingTable for check {check_name}: {e}"
        )
        return None

    return mapping_item


def _build_execution_automation_parameters(mapping_item, resource_arn):
    """
    Based on the mapping item from the AutomationMappingTable DDB table and resource ARN, construct the automation parameters needed for the SSM automation execution.

    :param mapping_item: Mapping item from the DDB table
    :param resource_arn: ARN of the resource
    :return: Automation parameters in the required format
    """
    regex_pattern = mapping_item.get("regexPattern", "")
    match = re.search(regex_pattern, resource_arn)
    resource_id = match.group()

    if len(resource_id) > 0:
        automation_parameters = _replace_resource_id(
            json.loads(mapping_item["automationParameters"]), resource_id
        )
    else:
        raise Exception(
            f"Regex pattern [{regex_pattern}] is not properly defined in ddb mapping table for check [{mapping_item['checkName']}]"
        )

    return automation_parameters


def _get_resource_tags(resource_arn, resource_region):
    """
    Get list of tags associated with the resource

    :param resource_arn: ARN of the resource
    :param resource_region: Region of the resource
    :return: List of resource tags. Example: [{'Key': 'automaticRemediation', 'Value': 'True'}]
    """
    try:
        tag_client = boto3.client(
            "resourcegroupstaggingapi", region_name=resource_region
        )
        resources_paginator = tag_client.get_paginator("get_resources")
        resource_tag_mapping_lists = resources_paginator.paginate(
            ResourceARNList=[resource_arn]
        ).build_full_result()["ResourceTagMappingList"]
    except ClientError as e:
        logger.warning(
            f"Failed to retrieve resource tags for resource {resource_arn}. {e}"
        )
        return []

    if len(resource_tag_mapping_lists) == 0:
        return []
    else:
        # Example return: [{'Key': 'automaticRemediation', 'Value': 'True'}]
        return resource_tag_mapping_lists[0]["Tags"]


def _is_resource_level_automatic_remediation_enabled(resource_tags):
    """
    Verifies if the resource level automation remediation is enabled based on the resource tags.

    :param resource_tags: List of resource tags.
    :return: 'True', if the tag key 'automaticRemediation' is present and its value is 'True'. 'False', if the tag is not present or set to 'False'
    """
    automatic_remediation = next(
        (item for item in resource_tags if item["Key"] == "automaticRemediation"), None
    )
    if automatic_remediation and automatic_remediation["Value"] == "True":
        return True
    else:
        logger.info(f"Resource level automation remediation is not enabled.")
        return False


def lambda_handler(event, context):
    for record in event["Records"]:
        """
        Extracting values from DDB TrustedAdvisorCheckTrackerTable stream. Example event:

        {'Records': [{'eventID': 'example123id', 'eventName': 'MODIFY', 'eventVersion': '1.1', 'eventSource': 'aws:dynamodb', 'awsRegion': 'us-east-1', 'dynamodb': {'ApproximateCreationDateTime': 1715587134.0, 'Keys': {'hashKey': {'S': 'abc123xyz'}, 'resource': {'S': 'arn:aws:ec2:ap-southeast-2:012345678901:security-group/sg-example123'}}, 'NewImage': {'lastUpdatedTimeEpoch': {'N': '1715573312'}, 'hashKey': {'S': 'abc123xyz'}, 'resourceStatus': {'S': 'Red'}, 'resource': {'S': 'arn:aws:ec2:ap-southeast-2:012345678901:security-group/sg-example123'}, 'lastUpdatedTime': {'S': '2024-05-13T04:08:32.687Z'}, 'checkName': {'S': 'Security groups should not allow unrestricted access to ports with high risk'}, 'region': {'S': 'ap-southeast-2'}}, 'SequenceNumber': '10053100000000041555340248', 'SizeBytes': 498, 'StreamViewType': 'NEW_IMAGE'}, 'eventSourceARN': 'arn:aws:dynamodb:us-east-1:012345678901:table/TrustedAdvisorCheckTrackerTable/stream/2024-05-11T07:16:57.900'}]}
        """
        new_image = record["dynamodb"]["NewImage"]
        check_name = new_image.get("checkName", {}).get("S")
        resource_arn = new_image.get("resource", {}).get("S")
        region = new_image.get("region", {}).get("S")
        hash_key = new_image.get("hashKey", {}).get("S")

        # Avoid duplicate OpsItem creation.
        dedup_value = {"dedupString": hash_key}

        resource_tags = _get_resource_tags(resource_arn, region)

        mapping_item = _get_ddb_mapping_item(check_name)

        # Verifies if automation is enabled at resource tag level
        resource_level_remediation_flag = (
            _is_resource_level_automatic_remediation_enabled(resource_tags)
        )

        # Verifies if automation is enabled at global level in the DDB AutomationMappingTable
        # 'False' if either 'mapping_item' is None, or, if mapping_item.automationStatus is 'false'
        global_level_remediation_flag = (
            mapping_item.get("automationStatus", False) if mapping_item else False
        )

        # If automation mapping is not found in AutomationMappingTable DDB table, or, automation is not enabled at resource tag level,
        # create the OpsItem without any automation execution
        if not global_level_remediation_flag or not resource_level_remediation_flag:
            if GEN_AI_RECOMMENDATIONS_ENABLED:
                invoke_model_url = f"https://{os.environ['AWS_REGION']}.console.aws.amazon.com/systems-manager/automation/execute/taResponderAutomationDocumentInvokeModel?region={os.environ['AWS_REGION']}#AutomationAssumeRole={AUTOMATION_DOCUMENT_INVOKE_MODEL_ROLE}&CheckName={check_name}&AffectedResourceArn={resource_arn}"
                operational_data = {
                    "flaggedResource": {
                        "Value": resource_arn,
                        "Type": "SearchableString",
                    },
                    "/aws/automations": {
                        "Type": "SearchableString",
                        "Value": f'[{{"automationType": "AWS::SSM::Automation", "automationId": "{AUTOMATION_DOCUMENT_INVOKE_MODEL}"}}]',
                    },
                    "invokeModelParameters": {
                        "Type": "String",
                        "Value": json.dumps(
                            {
                                "AutomationAssumeRole": AUTOMATION_DOCUMENT_INVOKE_MODEL_ROLE,
                                "AffectedResourceArn": resource_arn,
                                "CheckName": check_name,
                            }
                        ),
                    },
                    "invokeModelUrl": {"Value": invoke_model_url, "Type": "String"},
                    "/aws/dedup": {
                        "Value": json.dumps(dedup_value),
                        "Type": "SearchableString",
                    },
                }
            else:
                operational_data = {
                    "flaggedResource": {
                        "Value": resource_arn,
                        "Type": "SearchableString",
                    },
                    "/aws/dedup": {
                        "Value": json.dumps(dedup_value),
                        "Type": "SearchableString",
                    },
                }

            # Create the OpsItem
            ops_item_id = _create_ops_item(check_name, resource_arn, operational_data)
            return

        # Create the OpsItem and start the automation execution only if
        # the automation is enabled at resource tag level and global (AutomationMappingTable DDB table) level
        elif global_level_remediation_flag and resource_level_remediation_flag:
            if GEN_AI_RECOMMENDATIONS_ENABLED:
                invoke_model_url = f"https://{os.environ['AWS_REGION']}.console.aws.amazon.com/systems-manager/automation/execute/taResponderAutomationDocumentInvokeModel?region={os.environ['AWS_REGION']}#AutomationAssumeRole={AUTOMATION_DOCUMENT_INVOKE_MODEL_ROLE}&CheckName={check_name}&AffectedResourceArn={resource_arn}"
                operational_data = {
                    "flaggedResource": {
                        "Value": resource_arn,
                        "Type": "SearchableString",
                    },
                    "/aws/automations": {
                        "Type": "SearchableString",
                        "Value": f"[{{\"automationType\": \"AWS::SSM::Automation\", \"automationId\": \"{mapping_item['ssmAutomationDocument']}\"}}, {{\"automationType\": \"AWS::SSM::Automation\", \"automationId\": \"{AUTOMATION_DOCUMENT_INVOKE_MODEL}\"}}]",
                    },
                    "automationParameters": {
                        "Type": "String",
                        "Value": json.dumps(mapping_item["automationParameters"]),
                    },
                    "invokeModelParameters": {
                        "Type": "String",
                        "Value": json.dumps(
                            {
                                "AutomationAssumeRole": AUTOMATION_DOCUMENT_INVOKE_MODEL_ROLE,
                                "AffectedResourceArn": resource_arn,
                                "CheckName": check_name,
                            }
                        ),
                    },
                    "invokeModelUrl": {"Value": invoke_model_url, "Type": "String"},
                    "/aws/dedup": {
                        "Value": json.dumps(dedup_value),
                        "Type": "SearchableString",
                    },
                }
            else:
                operational_data = {
                    "flaggedResource": {
                        "Value": resource_arn,
                        "Type": "SearchableString",
                    },
                    "/aws/automations": {
                        "Type": "SearchableString",
                        "Value": f"[{{\"automationType\": \"AWS::SSM::Automation\", \"automationId\": \"{mapping_item['ssmAutomationDocument']}\"}}]",
                    },
                    "automationParameters": {
                        "Type": "String",
                        "Value": json.dumps(mapping_item["automationParameters"]),
                    },
                    "/aws/dedup": {
                        "Value": json.dumps(dedup_value),
                        "Type": "SearchableString",
                    },
                }

            automation_parameters = _build_execution_automation_parameters(
                mapping_item, resource_arn
            )

            operational_data["automationParameters"]["Value"] = json.dumps(
                automation_parameters
            )

            # Start automation execution
            automation_execution_id = _start_automation_execution(
                mapping_item["ssmAutomationDocument"], automation_parameters, region
            )

            # Create the OpsItem
            ops_item_id = _create_ops_item(check_name, resource_arn, operational_data)

            # Create item in AutomationExecutionTrackerTable DDB table with OpsItem and Execution Ids
            if automation_execution_id and ops_item_id:
                _put_item_in_automation_execution_ddb(
                    automation_execution_id, ops_item_id, region
                )

    return
