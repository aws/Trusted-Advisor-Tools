/* Copyright 2016. Amazon Web Services, Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License. */

// Sample Lambda Function to get Trusted Advisor Amazon EBS Snapshots check details from Cloudwatch events and execute the EBS create Snapshot recommendation
var AWS = require('aws-sdk');

// define configuration
const tagKey ='environment';
const tagValue ='prod';
const regionSpecification = 'eu-west-1'; //Specify a region to restrict the EBS create Snapshot action to. Use 'all' for all regions

//main function which gets Trusted Advisor data from Cloudwatch event
exports.handler = (event, context, callback) => {
    //extract details from Cloudwatch event
    checkName = event.detail["check-name"];
    volumeId = event.detail["check-item-detail"]["Volume ID"];
    region = event.detail["check-item-detail"]["Region"];
    const trustedAdvisorSuccessMessage = `Successfully got details from Trusted Advisor check, ${checkName} and executed automated action.`;
    
    //check if the volume is in the right region
    if (region == regionSpecification || regionSpecification == 'all') { createSnapshot (volumeId, region); }
    else { console.log ("No EBS volume found in specifed region"); }
    callback(null, trustedAdvisorSuccessMessage); //return success
};

//Sample function which creates snapshots for volumes that have no backup after checking their tags
function createSnapshot (volumeId, region) {
    AWS.config.update({region: region});
    var ec2 = new AWS.EC2();
    
    //get tags for the volumes highlighted by Trusted Advisor
    var describeTagsparams = {
        Filters: [
        {
            Name: "resource-id", 
            Values: [volumeId]
        },
        {
            Name: "key",
            Values: [tagKey]
        }
        ]
    };
    ec2.describeTags(describeTagsparams, function(err, data) {
        if (err) console.log(err, err.stack); // an error occurred
        else {
            if (data.Tags == "") {data = {Tags: [{value: "empty"}]} };
            
            //if the tag value matches what's configured, then create snapshot for the volume
            if (data.Tags[0].Value == tagValue)
            {
                const snapshotDescription = `Snapshot for volume, ${volumeId}`;
                var createSnapshotParams = {
                    Description: snapshotDescription,
                    VolumeId: volumeId
                };
                ec2.createSnapshot(createSnapshotParams, function(err, data) {
                    if (err) console.log(volumeId, region, err, err.stack); // an error occurred
                    else console.log("Started creation for volume: ", volumeId, region, data); // successful response
                });
            }
            else console.log ("Volume did not match tag: ", volumeId, region);
        }
    });
}
