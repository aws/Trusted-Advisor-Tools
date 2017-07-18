import boto3

iam = boto3.client('iam')


def lambda_handler(event, context):
    account_id = event['account']
    time_discovered = event['time']
    details = event['detail']['check-item-detail']
    username = details['User Name (IAM or Root)']
    access_key_id = details['Access Key ID']
    exposed_location = details['Location']
    print('Deleting exposed access key pair...')
    delete_exposed_key_pair(username, access_key_id)
    return {
        "account_id": account_id,
        "time_discovered": time_discovered,
        "username": username,
        "deleted_key": access_key_id,
        "exposed_location": exposed_location
    }


def delete_exposed_key_pair(username, access_key_id):
    """ Deletes IAM access key pair identified by access key ID for specified user.

    Args:
        username (string): Username of IAM user to delete key pair for.
        access_key_id (string): IAM access key ID to identify key pair to delete.

    Returns:
        (None)

    """
    try:
        iam.delete_access_key(
            UserName=username,
            AccessKeyId=access_key_id
        )
    except Exception as e:
        print(e)
        print('Unable to delete access key "{}" for user "{}".'.format(access_key_id, username))
        raise(e)
