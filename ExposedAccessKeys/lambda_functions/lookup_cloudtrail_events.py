import datetime
import collections
import boto3

cloudtrail = boto3.client('cloudtrail')


def lambda_handler(event, context):
    username = event['username']
    deleted_key = event['deleted_key']
    exposed_location = event['exposed_location']
    endtime = datetime.datetime.now()
    endtime_str = '{} {}'.format(str(endtime), 'UTC')
    interval = datetime.timedelta(hours=24)
    starttime = endtime - interval
    print('Retrieving events...')
    events_pages = get_events_pages(username, starttime, endtime)
    print('Summarizing events...')
    event_names, resource_names, resource_types = get_events_summaries(events_pages)
    return {
        "username": username,
        "deleted_key": deleted_key,
        "exposed_location": exposed_location,
        "time_discovered": endtime_str,
        "event_names": event_names,
        "resource_names": resource_names,
        "resource_types": resource_types
    }


def get_events_pages(username, starttime, endtime):
    try:
        paginator = cloudtrail.get_paginator('lookup_events')
        lookup_events_iterator = paginator.paginate(
            LookupAttributes=[
                {
                    'AttributeKey': 'Username',
                    'AttributeValue': username
                },
            ],
            StartTime=starttime,
            EndTime=endtime,
            PaginationConfig={'PageSize': 50}
        )
    except Exception as e:
        print(e)
        print('Unable to retrieve CloudTrail events for user "{}"'.format(username))
        raise(e)
    return lookup_events_iterator


def get_events_summaries(events_pages):
    event_name_counter = collections.Counter()
    resource_name_counter = collections.Counter()
    resource_type_counter = collections.Counter()
    for events in events_pages:
        for event in events['Events']:
            resources = event.get("Resources")
            event_name_counter.update([event.get('EventName')])
            if resources is not None:
                resource_name_counter.update([resource.get("ResourceName") for resource in resources])
                resource_type_counter.update([resource.get("ResourceType") for resource in resources])
    return event_name_counter.most_common(10), resource_name_counter.most_common(10), resource_type_counter.most_common(10)
