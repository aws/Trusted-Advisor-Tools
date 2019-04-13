"""
Copyright 2019. Amazon Web Services, Inc. All Rights Reserved.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

# Sample Lambda Function to get Trusted Advisor Underutilized EBS volumes
# check details from Cloudwatch events. For each volume that has not been
# attached within the threshold period it will snapshot the volume and
# delete it.

import os
import json
import re
import time
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

client = {} # dict to save client object for future invocations

def getLambdaEnv(parmname, defaultval=None):
    """
    Cleanly get the value of a Lambda environmental. Return if found or default
    """
    try:
        myval = os.environ[parmname]
        if isinstance(defaultval, int):
            return int(myval)
        else:
            return myval
    except:
        if defaultval:
            print('Environmental variable \'' + parmname + '\' not found. Using default [' + str(defaultval) + ']')
            return defaultval
        else:
            print('ERROR: Environmental variable \'' + parmname + '\' not found. Exiting')
            raise

IDLETHRESH = getLambdaEnv('IdleThresh', 90) # number of days unattached allowed
EXCEPTTAG = getLambdaEnv('IgnoreTag', 'ignoreEBSidle')       # ignore volumes with this tag
EXCEPTTAGVAL = getLambdaEnv('IgnoreTagVal', 'False') # value to ignore if present
MAILTOOWNER = getLambdaEnv('MailtoOwnerTag', 'Owner') # name of the tag containing owner email
MAILTO = getLambdaEnv('MailTo', 'miobrien@amazon.com')             # email to notify (with or without MAILTOOWNER)
GOLIVE = getLambdaEnv('EnableActions', 'False') # Do not enable actions unless explicitely set
FROM_EMAIL = getLambdaEnv('FromEmail', 'miobrien@amazon.com') # Email address to send from
MYREGION = os.environ['AWS_REGION']
sts = boto3.client('sts')
MYACCOUNT = sts.get_caller_identity()['Account']    # Account ID
REGION_SETUP = {} # Cache for regionSetup func

#======================================================================
#
def connect(service, region=MYREGION):
    """
    Return client object for an AWS service. Connect if not already. This method
    uses a persistent connection over the life of the lambda.
    """
    if not region in client:
        client[region] = {}

    if service not in client[region]:
        try:
            client[region][service] = boto3.client(service,region_name=region)
        except Exception as e:
            print(e)
            print(f'could not connect to {service} in {region}')
            raise e

    return client[region][service]

def notify_owner(contactEmailAddress, volinfo, accountId=MYACCOUNT):
    """
    Create email from a template
    volinfo = { idlethresh: "", volid:"", snapshotid: "", region: "" }
    """
    template = [
        "The following EBS volume in region {} has been unattached for more than {} days. The volume has been snapshotted and deleted. Please use the instructions below to recover the volume if the data is needed in the future: <br> <br>",
        "",
        "<b>Account ID:</b> {}<br>",
        "<b>Region: </b> {}<br>",
        "<b>Volume ID:</b> {}<br>",
        "<b>Snapshot ID:</b> {}",
        "<br>",
        "<p>To recover this volume, create a new volume from the snapshot. See <a href='https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-restoring-volume.html'>AWS Documentation</a> for more information.</p>"
        "<p>Note: idle (unattached) EBS volumes are billed based on the allocated volume size. Volumes that have been idle for more than {} days will be snapshotted and deleted per corporate Cloud governance policy."
    ]
    tempout = '\n'
    tempout = tempout.join(template)
    emailBody = tempout.format(volinfo['region'], IDLETHRESH, accountId, volinfo['region'], volinfo['volid'], volinfo['snapshotid'], IDLETHRESH)

    sendSesEmail(contactEmailAddress, emailBody)

# ---------------------------------------------------------------------
def sendSesEmail(toEmailAddress, emailBody, fromEmailAddress=FROM_EMAIL):
    """
    Send an email using Simple Email Service
    """
    ses = connect('ses')

    response = ses.send_email(
        Source=FROM_EMAIL,
        Destination={
            'ToAddresses': [toEmailAddress],
        },
        Message={
            'Subject': {
                'Data': 'Idle EBS Volume Deleted',
                'Charset': 'UTF-8',
            },
            'Body': {
                'Text': {
                    'Data': emailBody,
                    'Charset': 'UTF-8',
                },
                'Html': {
                    'Data': emailBody,
                    'Charset': 'UTF-8',
                }
            }
        },
        ReplyToAddresses=[fromEmailAddress]
    )

# ---------------------------------------------------------------------
def date_handler(obj):
    if not hasattr(obj, 'isoformat'):
        raise TypeError
    return obj.isoformat()

# ---------------------------------------------------------------------
def get_volume_info(volid, region):
    """
    get volume info
    return response (json)
    """
    ec2 = connect('ec2', region)
    mystatus = ec2.describe_volumes(
        VolumeIds=[volid],
    )
    return mystatus['Volumes'][0]

# ---------------------------------------------------------------------
def get_volume_status(volid, region):
    """
    get volume status
    return response (json)
    """
    ec2 = connect('ec2', region)
    mystatus = ec2.describe_volume_status(
        VolumeIds=[volid],
    )
    return mystatus['VolumeStatuses']

# ---------------------------------------------------------------------
def get_tags(ec2id, ec2type, region):
    """
    get tags
    return tags (json)
    """
    mytags = []
    ec2 = connect('ec2', region)
    if ec2type == 'volume':
        response = ec2.describe_volumes(VolumeIds=[ec2id])
        if 'Tags' in response['Volumes'][0]:
            mytags = response['Volumes'][0]['Tags']
    elif ec2type == 'snapshot':
        response = ec2.describe_snapshots(SnapshotIds=[ec2id])
        if 'Tags' in response['Snapshots'][0]:
            mytags = response['Snapshots'][0]['Tags']

    return mytags

# ---------------------------------------------------------------------
def get_tag(ec2id, ec2type, region, tagname):
    """
    Get a specific tag and return the value
    """
    tags = get_tags(ec2id, ec2type, region)
    for tag in tags:
        if tag['Key'] == tagname:
            return tag['Value']

    return None

# ---------------------------------------------------------------------
def has_tag(ec2id, ec2type, region, tagname, tagvalue=False):
    """
    Determine if a volume has a specific tag
    Returns boolean
    """
    tags = get_tags(ec2id, ec2type, region)
    for tag in tags:
        if tag['Key'] == tagname:
            if tagvalue:
                if tag['Value'] == tagvalue:
                    return True
                else:
                    break
            else:
                return True

    return False

# ---------------------------------------------------------------------
def snapshot_volume(volid, region):
    """
    Create a snapshot. Do dry run if not GOLIVE. Tag the snapshot with
    DeleteEBSVolOnCompletion. A CloudWatch rule will trigger the volume
    deletion process.
    """

    ec2 = connect('ec2', region)

    response = ec2.create_snapshot(
        Description='Snapshot of idle volume before deletion',
        VolumeId=volid,
        TagSpecifications=[
            {
                'ResourceType': 'snapshot',
                'Tags': [
                    {
                        'Key': 'SnapshotReason',
                        'Value': 'Idle Volume'
                    },
                    {
                        'Key': 'SnapshotDate',
                        'Value': str(datetime.today())
                    },
                    {

                        'Key': 'DeleteEBSVolOnCompletion',
                        'Value': GOLIVE
                    }
                ]
            },
        ]
    )

    return

# ---------------------------------------------------------------------
def delete_volume(volid, region):
    """
    Delete a volume
    """
    Dryrun = True
    if GOLIVE.lower() == 'true':
        Dryrun = False
    else:
        print('Running in Dryrun mode')

    ec2 = connect('ec2', region)

    response = ec2.delete_volume(
        VolumeId=volid,
        DryRun=Dryrun
    )
    return

# ---------------------------------------------------------------------
def hasowner(volid, region, tagname):
    """
    Retrieves owner email from the tag configured with this info
    """
    tags = get_tags(volid, 'volume', region)
    for tag in tags:
        if tag['Key'] == tagname:
            if tag['Value']:
                if tag['Value']:
                    return tag['Value']
                else:
                    break

    return False

# ---------------------------------------------------------------------
def recentlyAttached(volid, region, thresholddays):
    """
    Return bool indicating whether last volume attachment was within the
    threshold period
    """
    ct = connect('cloudtrail', region)
    most_recent = ''
    mount_found = False
    lastmounteddays = 999
    today = datetime.today()

    token = 'start'
    events = []
    todate = datetime.today()
    response = ct.lookup_events(
        MaxResults=50,
        LookupAttributes=[
            {
                'AttributeKey': 'ResourceName',
                'AttributeValue': volid
            }
        ],
        StartTime=todate - timedelta(days=thresholddays),
        EndTime=todate
    )

    events = response['Events']

    while 'NextToken' in response:

        time.sleep(1)
        response = ct.lookup_events(
            NextToken=response['NextToken'],
            MaxResults=50,
            LookupAttributes=[
                {
                    'AttributeKey': 'ResourceName',
                    'AttributeValue': volid
                }
            ],
            StartTime=todate - timedelta(days=thresholddays),
            EndTime=todate
        )

        events = events + response['Events']

    # Loop through Events looking for a mount
    for event in events:

        if event['EventName'] == 'DetachVolume' or event['EventName'] == 'AttachVolume':
            # Get duration since detached
            mount_found = True
            eventTS = event['EventTime']
            eventTS = eventTS.replace(tzinfo=None)

            eventEt = today - eventTS
            if eventEt.days < lastmounteddays:
                lastmounteddays = eventEt.days

    print(f'Volume {volid} was last attached {lastmounteddays} days ago')

    return lastmounteddays < thresholddays

# ---------------------------------------------------------------------
def topicExists(region, snstopic):
    sns = connect('sns', region)
    try:
        response = sns.get_topic_attributes(
            TopicArn='arn:aws:sns:' + region + ':' + MYACCOUNT + ':' + snstopic
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'NotFound':
            return False
        else:
            print(e)
            print('Encountered an unexpected error')
            return False
    except Exception as e:
        print(e)
        print('Encountered an unexpected error')
        return False

    return True
# ---------------------------------------------------------------------
def regionSetup(region, funcname):
    '''
    Add a rule in the region to detect when the snapshot is complete
    Return True on success
    '''
    def createRule():
        ### Create the snapcomplete rule
        try:
            cwe.put_rule(
                Description='Snapshot complete Notification',
                Name='EBSSnapshotComplete',
                EventPattern="{ \"detail-type\": [ \"EBS Snapshot Notification\" ], \"detail\": { \"event\": [ \"createSnapshot\" ], \"result\": [ \"succeeded\" ] } }",
                State='ENABLED'
            )
            cwe.put_targets(
                Rule='EBSSnapshotComplete',
                Targets=[
                    {
                        'Id': 'TAEBSVolSnapDelTopic',
                        'Arn': topicarn
                    }
                ]
            )
        except ClientError as e:
            print(e)
            print(f'AddPermission: client error adding topic permission to SNS topic {topicarn}')
            raise e
        except Exception as e:
            print(e)
            print('PutRule: Error creating CW Event rule')
            raise e

    # Check the cache
    if region in REGION_SETUP:
        return True

    sns = connect('sns', region)

    # Create the topic
    topicarn = ''
    try:
        response = sns.create_topic(
            Name='TAEBSVolSnapDelTopic'
        )
        topicarn = response['TopicArn']
        print(f'SNS Topic created: {topicarn}')
    except Exception as e:
        print(e)
        print('CreateTopic: Encountered an unexpected error')
        return False

    # Add permission in the Lambda to SNS
    lam = connect('lambda', MYREGION)

    try:
        response = lam.add_permission(
            FunctionName=funcname,
            StatementId=region,
            Action='lambda:InvokeFunction',
            Principal='sns.amazonaws.com',
            SourceArn=topicarn
        )
        print(f'Lambda {funcname} permission added for {topicarn}')
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            pass
        else:
            print(e)
            print('Encountered an unexpected error')
            return False
    except Exception as e:
        print(e)
        print('AddPermission: Encountered an unexpected error')
        return False

    # Subscribe the Lambda to the topic
    try:
        sns.subscribe(
            TopicArn=topicarn,
            Protocol='Lambda',
            Endpoint='arn:aws:lambda:us-east-1:' + MYACCOUNT + ':function:TAEBSVolumeSnapDelete'
        )
        print(f'SNS Subscription created for {MYACCOUNT} to {topicarn}')
    except Exception as e:
        print(e)
        print('Subscribe: Encountered an unexpected error')
        return False

    # Does the snapcomplete rule already exist?
    cwe = connect('events', region)
    try:
        response = cwe.describe_rule(
            Name='EBSSnapshotComplete'
        )
        print('EBSSnapshotComplete rule already exists')
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            try:
                createRule()
            except:
                return False
        else:
            print(e)
            print('DescribeRule: Encountered an unexpected error')
    except Exception as e:
        print(e)
        print('Encountered an unexpected error')
        return False

    ### Add SNS Topic Policy
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
              "Sid": "TrustCloudWatchRules",
              "Effect": "Allow",
              "Principal": {
                "Service": "events.amazonaws.com"
              },
              "Action": "sns:Publish",
              "Resource": topicarn
            }
          ]
        }
    try:
        sns.set_topic_attributes(
            TopicArn=topicarn,
            AttributeName='Policy',
            AttributeValue=json.dumps(policy)
        )
        print(f'SNS Topic Policy updated for {topicarn}')
    except ClientError as e:
        print(e)
        print(f'AddPermission: client error adding topic permission to SNS topic {topicarn}')
    except Exception as e:
        print(e)
        print('AddPermission: Encountered an unexpected error')
        return False

    REGION_SETUP[region] = True
    return True

# ---------------------------------------------------------------------
def lambda_handler(event, context):

    # Translate if from SNS
    if 'Records' in event:
        event = json.loads(event['Records'][0]['Sns']['Message'])

    if event['source'] == 'aws.trustedadvisor':
        volid = event['detail']['check-item-detail']['Volume ID']
        region = event['detail']['check-item-detail']['Region']

        cost = event['detail']['check-item-detail']['Monthly Storage Cost']
        status = get_volume_status(volid, region)
        volinfo = get_volume_info(volid, region)

        # 1) Ignore if volume has attachments
        if len(volinfo['Attachments']) > 0:
            print(f'Volume {volid} in region {region} has attachments and is ignored.')
            return

        # 2) Ignore if volume is < IDLETHRESH days old
        cdate = volinfo['CreateTime']
        cdate = cdate.replace(tzinfo=None)
        age = datetime.today() - cdate
        if age.days < IDLETHRESH:
            print(f'Volume {volid} in region {region} is {age.days} days old and is ignored. ( < IdleThresh )')
            return

        # 3) Get tags - ignore if EXCEPTTAG tag present
        if EXCEPTTAG and has_tag(volid, 'volume', region, EXCEPTTAG, EXCEPTTAGVAL):
            print(f'Volume {volid} in region {region} has exception tag {EXCEPTTAG} and is ignored.')
            return

        # 4) Get last mount and calculate idle days - ignore if below IDLETHRESH
        if recentlyAttached(volid, region, IDLETHRESH):
            print(f'volume {volid} in region {region} was recently attached to an instance and is ignored.')
            return

        # 5) Snapshot and end. Snapshot event will redrive lambda
        # but first...make sure the region is set up
        if region != MYREGION:
            if not regionSetup(region, context.function_name):
                print(f'ERROR: Could not set up cross-region support to {region}')
                return

        snapshot_volume(volid, region)
        print(f'snapshot initiated for {volid} in region {region}. Volume will be deleted when snapshot completes successfully.')
        # Processing ends here and will resume off of the successful snapshot

    elif event['source'] == 'aws.ec2':
        region = event['region']
        volarn = event['detail']['source']
        snaparn = event['detail']['snapshot_id']

        volsearch = re.match(".*:volume/(vol-.*)", volarn)
        volid = ''
        if volsearch:
            volid = volsearch.group(1)
        else:
            print(f'ERROR: could not find volume id from {volarn} in region {region}')
            return

        snapsearch = re.match(".*:snapshot/(snap-.*)", snaparn)
        snapshotid = ''
        if snapsearch:
            snapshotid = snapsearch.group(1)
        else:
            print(f'ERROR: could not find volume id from {snaparn} in region {region}')
            return

        snapresult = event['detail']['result']

        print(f'region {region} volid {volid} snapshotid {snapshotid}')

        # 1) is this one of ours?
        if not has_tag(snapshotid, 'snapshot', region, 'SnapshotReason', 'Idle Volume'):
            return # quietly disregard - this is not one of our snapshots

        # 2) Validate successful snapshot
        if snapresult != 'succeeded':
            print(f'ERROR: snapshot {snapshotid} status is {snapresult} in region {region} - ignored.')
            return

        # 3) Is this a volume we care about? Get tags to make sure
        if has_tag(snapshotid, 'snapshot', region, 'DeleteEBSVolOnCompletion'):
            if bool(get_tag(snapshotid, 'snapshot', region, 'DeleteEBSVolOnCompletion')):
                print(f'Deleting idle EBS volume {volid} in region {region}')
                delete_volume(volid, region)
            else:
                print(f'Snapshot {snapshotid} did not specify deletion for this volume {volid} in region {region}')

        # 5) email the owner snapshot id and rehydration instructions
        if MAILTOOWNER and hasowner(volid, region, MAILTOOWNER):
            notify_owner(
                hasowner(volid, region, MAILTOOWNER),
                { 'volid': volid, 'snapshotid': snapshotid, 'region': region }
            )
        if MAILTO:
            notify_owner(
                MAILTO,
                { 'volid': volid, 'snapshotid': snapshotid, 'region': region  }
            )

    return
