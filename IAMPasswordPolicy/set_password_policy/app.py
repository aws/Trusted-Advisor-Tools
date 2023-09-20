import json
import boto3


def lambda_handler(event, context):
    # Connect to IAM
    iam = boto3.client("iam")

    # Get status of Trusted Advisor Check from EventBridge
    check_status = event["detail"]["status"]
    current_policy = {}
    if check_status == "WARN":
        # Get details of current password policy
        current_policy = iam.get_account_password_policy()["PasswordPolicy"]

    # Set password policy for IAM
    response = iam.update_account_password_policy(
        MinimumPasswordLength=current_policy.get("MinimumPasswordLength", 12),
        RequireSymbols=True,
        RequireNumbers=True,
        RequireUppercaseCharacters=True,
        RequireLowercaseCharacters=True,
        AllowUsersToChangePassword=current_policy.get(
            "AllowUsersToChangePassword", True
        ),
        PasswordReusePrevention=current_policy.get("PasswordReusePrevention", 12),
        MaxPasswordAge=current_policy.get("MaxPasswordAge", 90),
        HardExpiry=current_policy.get("HardExpiry", False),
    )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "response": response,
            }
        ),
    }
