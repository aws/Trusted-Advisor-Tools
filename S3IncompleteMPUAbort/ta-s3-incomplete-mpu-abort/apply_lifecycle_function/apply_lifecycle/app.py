import boto3
from botocore.exceptions import ClientError
from model.aws.ta import Marshaller
from model.aws.ta import AWSEvent
from model.aws.ta import TAStateChangeNotification

def lambda_handler(event, context):
    """Lambda function reacting to Trusted Advisor state change notifications

    Parameters
    ----------
    event: dict, required
        EventBridge Trusted Advisor State Change Event Format

    context: object, required
        Lambda Context runtime methods and attributes

    Returns
    ------
        The same input event with updated detail_type
    """

    # Deserialize event into strongly typed object
    aws_event: AWSEvent = Marshaller.unmarshall(event, AWSEvent)
    ta_state_change_notification: TAStateChangeNotification = aws_event.detail

    # Execute business logic
    process_ta_notification(ta_state_change_notification, aws_event)

    # Make updates to event payload
    aws_event.detail_type = "TALifecyclePolicyFunction processed event of " + aws_event.detail_type

    # Return event for further processing
    return Marshaller.marshall(aws_event)

def process_ta_notification(notification: TAStateChangeNotification, aws_event: AWSEvent):
    if notification.check_name != "Amazon S3 Bucket Lifecycle Configuration":
        print(f"Ignoring notification for check: {notification.check_name}")
        return

    bucket_name = notification.check_item_detail.get("Bucket Name")
    account_id = aws_event.account  # Assuming the account ID is in the main event object

    if notification.status == "WARN":
        apply_lifecycle_policy(account_id, bucket_name)
    else:
        print(f"Bucket {bucket_name} in account {account_id} is compliant")

def apply_lifecycle_policy(account_id, bucket_name):
    # Assume role in the target account
    sts_client = boto3.client('sts')
    assumed_role_object = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/CrossAccountS3AccessRole",
        RoleSessionName="AssumeRoleSession"
    )
    
    # Create an S3 client using the assumed role credentials
    s3_client = boto3.client(
        's3',
        aws_access_key_id=assumed_role_object['Credentials']['AccessKeyId'],
        aws_secret_access_key=assumed_role_object['Credentials']['SecretAccessKey'],
        aws_session_token=assumed_role_object['Credentials']['SessionToken']
    )
    
    # Check if a lifecycle policy already exists
    try:
        existing_policy = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
        rules = existing_policy.get('Rules', [])
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
            rules = []
        else:
            print(f"Error getting lifecycle policy for bucket {bucket_name} in account {account_id}: {e}")
            return
    
    # Check if the required rule already exists
    required_rule_exists = any(
        rule.get('AbortIncompleteMultipartUpload', {}).get('DaysAfterInitiation') == 7
        for rule in rules
    )
    
    if not required_rule_exists:
        # Add the new rule
        new_rule = {
            'ID': 'AbortIncompleteMultipartUploads',
            'Status': 'Enabled',
            'Filter': {}, 
            'AbortIncompleteMultipartUpload': {
                'DaysAfterInitiation': 7
            }
        }
        rules.append(new_rule)
        
        # Apply the updated lifecycle configuration
        try:
            s3_client.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration={'Rules': rules}
            )
            print(f"Applied lifecycle policy to bucket {bucket_name} in account {account_id}")
        except ClientError as e:
            print(f"Error applying lifecycle policy to bucket {bucket_name} in account {account_id}: {e}")
    else:
        print(f"Required rule already exists for bucket {bucket_name} in account {account_id}")