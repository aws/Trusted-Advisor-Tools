import datetime
import collections
import boto3

def lambda_handler(event, context):
    event_account_id = event['account_id']
    time_discovered = event['time_discovered']
    username = event['username']
    deactivated_key = event['deactivated_key']
    exposed_location = event['exposed_location']
    endtime = datetime.datetime.now()  # Create start and end time for CloudTrail lookup
    interval = datetime.timedelta(hours=24)
    starttime = endtime - interval
    current_account_id = context.invoked_function_arn.split(":")[4]

    print('Retrieving events...')
    events = get_events(current_account_id, event_account_id, username, starttime, endtime)
    print('Summarizing events...')
    event_names, resource_names, resource_types = get_events_summaries(events)
    return {
        "account_id": event_account_id,
        "time_discovered": time_discovered,
        "username": username,
        "deactivated_key": deactivated_key,
        "exposed_location": exposed_location,
        "event_names": event_names,
        "resource_names": resource_names,
        "resource_types": resource_types
    }

def get_events(current_account_id, event_account_id, username, starttime, endtime):
    """ Retrieves detailed list of CloudTrail events that occurred between the specified time interval.
    Args:
        current_account_id (string): The ID of the current AWS account.
        event_account_id (string): The ID of the AWS account where the event occurred.
        username (string): Username to lookup CloudTrail events for.
        starttime(datetime): Start of interval to lookup CloudTrail events between.
        endtime(datetime): End of interval to lookup CloudTrail events between.
    Returns:
        (dict)
        Dictionary containing list of CloudTrail events occurring between the start and end time with detailed information for each event.
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

    cloudtrail = session.client("cloudtrail")

    try:
        response = cloudtrail.lookup_events(
            LookupAttributes=[
                {
                    'AttributeKey': 'Username',
                    'AttributeValue': username
                },
            ],
            StartTime=starttime,
            EndTime=endtime,
            MaxResults=50
        )
    except Exception as e:
        print(e)
        print('Unable to retrieve CloudTrail events for user "{}"'.format(username))
        raise(e)
    return response

def get_events_summaries(events):
    """ Summarizes CloudTrail events list by reducing into counters of occurrences for each event, resource name, and resource type in list.
    Args:
        events (dict): Dictionary containing list of CloudTrail events to be summarized.
    Returns:
        (list, list, list)
        Lists containing name:count tuples of most common occurrences of events, resource names, and resource types in events list.
    """
    event_name_counter = collections.Counter()
    resource_name_counter = collections.Counter()
    resource_type_counter = collections.Counter()
    for event in events['Events']:
        resources = event.get("Resources")
        event_name_counter.update([event.get('EventName')])
        if resources is not None:
            resource_name_counter.update([resource.get("ResourceName") for resource in resources])
            resource_type_counter.update([resource.get("ResourceType") for resource in resources])
    return event_name_counter.most_common(10), resource_name_counter.most_common(10), resource_type_counter.most_common(10)