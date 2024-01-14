import os
import boto3


TOPIC_ARN = os.environ['TOPIC_ARN']  # ARN for SNS topic to post message to

TEMPLATE = '''At {} public read and/or write permissions were detected on the S3 bucket {} of account {}, and have subsequently been removed.

Please ensure your AWS account remains secure by logging in and further reviewing the ACLs and recently created objects for the bucket.'''

s3 = boto3.client('s3')
sns = boto3.client('sns')


def lambda_handler(event, context):
    time_discovered = event['time']
    account_id = event['account']
    bucket_name = event['detail']['resource_id'].split(':')[-1].strip()  # Munge bucket name from resource id and strip whitespace
    print('Retrieving bucket acls...')
    bucket_acls = get_bucket_acls(bucket_name)
    print('Pruning public ACLs...')
    pruned_acls = prune_public_acls(bucket_acls)
    print('Applying pruned ACLs to bucket...')
    put_bucket_acls(bucket_name, pruned_acls)
    print("Publishing message...")
    subject = 'Security Alert: Public ACLs Detected for Bucket {} On Account {}'.format(bucket_name, account_id)
    message = TEMPLATE.format(time_discovered, bucket_name, account_id)
    publish_msg(subject, message)


def get_bucket_acls(bucket_name):
    """ Retrieves list of configured bucket ACLs from target S3 bucket

    Args:
        bucket_name (string): Name of S3 bucket to retrieve ACLs for.

    Returns:
        (dict)
        Dictionary containing details about owner of bucket and configured ACL grants

    """
    try:
        bucket_acls = s3.get_bucket_acl(Bucket=bucket_name)
    except Exception as e:
        print(e)
        print('Unable to retrieve bucket ACLs for bucket "{}".'.format(bucket_name))
        raise(e)
    bucket_acls.pop('ResponseMetadata')  # Remove unneeded key-value pair from response
    return bucket_acls


def prune_public_acls(acl_dict):
    """ Prunes ACLs granted to the public (AllUsers) group from the target ACL dictionary

    Args:
        acl_dict (dict): Dictionary containing details about owner of bucket and configured ACL grants

    Returns:
        (dict)
        Dictionary containing details about owner of bucket and configured ACL grants with ACLs granted to AllUsers pruned out

    """
    grants = acl_dict['Grants'][:]
    acl_dict['Grants'] = [grant for grant in grants if not grant['Grantee'].get('URI') == "http://acs.amazonaws.com/groups/global/AllUsers"]  # List comp to remove public permission grants
    return acl_dict


def put_bucket_acls(bucket_name, acl_dict):
    """ Removes public permissions from target S3 bucket

    Args:
        bucket_name (string): Username of IAM user to delete key pair for.

    Returns:
        (None)

    """
    try:
        s3.put_bucket_acl(
            Bucket=bucket_name,
            AccessControlPolicy=acl_dict
        )
    except Exception as e:
        print(e)
        print('Unable to put bucket ACLs to bucket "{}".'.format(bucket_name))
        raise(e)


def publish_msg(subject, message):
    """ Publishes message to SNS topic.

    Args:
        subject (string): Subject of message to be published to topic.
        message (string): Content of message to be published to topic.

    Returns:
        (None)

    """
    try:
        sns.publish(
            TopicArn=TOPIC_ARN,
            Message=message,
            Subject=subject,
            MessageStructure='string'
        )
    except Exception as e:
        print(e)
        print('Could not publish message to SNS topic "{}"'.format(TOPIC_ARN))
        raise e
