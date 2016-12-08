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

// Sample Lambda Function to get Trusted Advisor Low Utilization Amazon EC2 Instances check details from Cloudwatch events and execute the EC2 stop instance recommendation
var AWS = require('aws-sdk');

// define configuration
const tagKey ='environment';
const tagValue ='dev';
const regionSpecification = 'us-east-2'; //Specify a region to restrict the EC2 Stop Instances action to. Use 'all' for all regions

//main function which gets Trusted Advisor data from Cloudwatch event
exports.handler = (event, context, callback) => {
    //extract details from Cloudwatch event
    checkName = event.detail["check-name"];
    instanceId = event.detail["check-item-detail"]["Instance ID"];
    region = event.detail["check-item-detail"]["Region/AZ"].slice(0, -1);
    const trustedAdvisorSuccessMessage = `Successfully got details from Trusted Advisor check, ${checkName} and executed automated action.`;
    
    //check if the EC2 instance is in the right region
    if (region == regionSpecification || regionSpecification == 'all') { stopInstances(instanceId, region); }
    else { console.log ("No EC2 instance found in specifed region"); }
    callback(null, trustedAdvisorSuccessMessage); //return success
};

//Sample function which stops EC2 Instances after checking their tags
function stopInstances (instanceId, region) {
    AWS.config.update({region: region});
    var ec2 = new AWS.EC2();
    
    //get tags for the instances highlighted by Trusted Advisor
    var describeTagsparams = {
        Filters: [
        {
            Name: "resource-id", 
            Values: [instanceId]
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
            
            //if the tag value matches what's configured, then stop the instance
            if (data.Tags[0].Value == tagValue)
            {
                var stopInstancesParams = {
                    InstanceIds: [instanceId],
                    DryRun: true //set to true for testing
                };
                ec2.stopInstances(stopInstancesParams, function(err, data) {
                    if (err) console.log(instanceId, region, err, err.stack); // an error occurred
                    else console.log("Instance stopped: ", instanceId, region);           // successful response
                });
            }
            else console.log ("Instance did not match tag: ", instanceId, region);
        }
    });
}

