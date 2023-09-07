############################################################
# This script is used to release an Elastic IP address
# if the ElasticIP address does not have a
# TrustedAdvisorAutomate tag set to "false". After testing,
# modify the script to remove the DryRun=True parameter.
############################################################

import boto3

DRY_RUN = True


def lambda_handler(event, context):
    region = event["detail"]["check-item-detail"]["Region"]
    eip = event["detail"]["check-item-detail"]["IP Address"]

    ec2 = boto3.client("ec2", region_name=region)
    allocation_id = ec2.describe_addresses(PublicIps=[eip])["Addresses"][0][
        "AllocationId"
    ]
    # Grab tags for Elastic IP
    tags = ec2.describe_tags(
        Filters=[{"Name": "resource-id", "Values": [allocation_id]}]
    )["Tags"]

    # Release the Elastic IP if the TrustedAdvisorAutomate tag is set to True
    if tags:
        for tag in tags:
            if tag["Key"] == "TrustedAdvisorAutomate":
                if tag["Value"].lower() == "false":
                    return {
                        "statusCode": 200,
                        "body": f"Elastic IP {eip} has not been released.",
                    }

    # DryRun=True will not actually release the Elastic IP
    # but will return the result of the dry run
    try:
        result = ec2.release_address(DryRun=DRY_RUN, AllocationId=allocation_id)
        return {
            "statusCode": 200,
            "body": f"Elastic IP {eip} has been released. {result}",
        }
    except Exception as e:
        print(e)
        raise (e)
