import boto3

#iam = boto3.client('iam')

def lambda_handler(event, context):
    event_account_id = event['account']
    time_discovered = event['time']
    details = event['detail']['check-item-detail']
    username = details['User Name (IAM or Root)']
    access_key_id = details['Access Key ID']
    exposed_location = details['Location']
    current_account_id = context.invoked_function_arn.split(":")[4]
    
    print('Deactivating exposed access key pair in the current account...')
    deactivate_exposed_key_pair(event_account_id, current_account_id, username, access_key_id)
    return {
        "account_id": event_account_id,
        "time_discovered": time_discovered,
        "username": username,
        "deactivated_key": access_key_id,
        "exposed_location": exposed_location
        }

def deactivate_exposed_key_pair(event_account_id, current_account_id, username, access_key_id):
    """ Deactivates IAM access key pair identified by access key ID for specified user.
    Args:
        current_account_id (string): The ID of the current AWS account.
        event_account_id (string): The ID of the AWS account where the event occurred.
        username (string): Username of IAM user to deactivate key pair for.
        access_key_id (string): IAM access key ID to identify key pair to deactivate.
    Returns:
        (None)
    """
    if event_account_id != current_account_id:
        print("Assuming role in another account")
        sts = boto3.client("sts")
        response = sts.assume_role(
            RoleArn="arn:aws:iam::"+ event_account_id +":role/ta-12Fnkpl8Y5-crossaccount-iam-role",
            RoleSessionName="ta-12Fnkpl8Y5-cloudtraileventlookup-session"
        )
        session = boto3.Session(
            aws_access_key_id=response['Credentials']['AccessKeyId'],
            aws_secret_access_key=response['Credentials']['SecretAccessKey'],
            aws_session_token=response['Credentials']['SessionToken']
        )
    else:
        print("Using current account")
        session = boto3.Session()

    iam = session.client("iam")

    try:
        iam.update_access_key(
            UserName=username,
            Status='Inactive',
            AccessKeyId=access_key_id
        )
    except Exception as e:
        print(e)
        print('Unable to deactivate access key "{}" for user "{}".'.format(access_key_id, username))
        raise(e)