import boto3

iam = boto3.client('iam')

def lambda_handler(event, context):
    details = event['check-item-detail']
    username = details['User Name (IAM or Root)']
    access_key_id = details['Access Key ID']
    exposed_location = details['Location']
    print('Deleting exposed access key pair...')
    delete_exposed_key_pair(username, access_key_id)
    return {
        "username": username,
        "deleted_key": access_key_id,
        "exposed_location": exposed_location
    }

def delete_exposed_key_pair(username, access_key_id):
    try:
        iam.delete_access_key(
            UserName=username,
            AccessKeyId=access_key_id
        )
    except Exception as e:
        print(e)
        print('Unable to delete access key "{}" for user "{}".'.format(access_key_id, username))
        raise(e)
