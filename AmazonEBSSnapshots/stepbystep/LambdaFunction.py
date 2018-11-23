import json
import boto3


def create_snapshot(volume_id, region):
    ec2 = boto3.client('ec2', region_name=region)
    # the function will only consider volumes with the tag 'ta-ebs'
    allowed_tag = 'ta-ebs'
    
    describe_tags_params = [
        {
            'Name' : 'resource-id',
            'Values': [volume_id],
        },
        {
            'Name': 'key',
            'Values': [allowed_tag]
        }
    ]
    
    # we check if the volume has the tag 'ta-ebs'
    print ('Checking tags for volume: %s' % volume_id)
    describe_response = ec2.describe_tags(Filters=describe_tags_params)
    print (describe_response)
    
    if len(describe_response['Tags']) >0:
    
        snapshot_description = 'Automated Snapshot by TA automation for volume %s' % volume_id
        response = ec2.create_snapshot(Description=snapshot_description, VolumeId=volume_id )
        print (response)
        
        # tag the volume with the tag used by Data Lifecycle Manager
        resources=[
            volume_id
        ]
    
        tags = [
            {
                'Key': 'ta-snapshot',
                'Value': 'true'
            }
        ]
    
        response = ec2.create_tags(Resources=resources, Tags=tags)
        print (response)
        
        print ('Snapshot initiated and volume tagged for snapshot lifecycle management')
    else:
        print ('Volume %s in region %s did not match tag, skipping.' % (volume_id, region))
    
def lambda_handler(event, context):
    
    print(json.dumps(event))
    
    check_name = event['detail']['check-name'];
    region = event['detail']["check-item-detail"]["Region"];
    volume_id = event['detail']['check-item-detail']['Volume ID']
    
    ta_success_msg = 'Successfully got details from Trusted Advisor check, %s and executed automated action.' % check_name
    print (ta_success_msg)
    create_snapshot(volume_id, region)
    
    return None