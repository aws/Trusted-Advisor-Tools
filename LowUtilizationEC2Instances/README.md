## Low Utilization Amazon EC2 Instances 

### Trusted Advisor Check Description
Checks the Amazon Elastic Compute Cloud (Amazon EC2) instances that were running at any time during the last 14 days and alerts you if the daily CPU utilization was 10% or less and network I/O was 5 MB or less on 4 or more days.

### Setup and Usage
You can automatically stop EC2 instances that have low utilization recommended by Trusted Advisor using Amazon Cloudwatch events and AWS Lambda to reduce cost using the following instructions:

1. Create an Amazon IAM role for the Lambda function to use. Attach the [IAM policy](IAMPolicy) to the role in the IAM console.
Documentation on how to create an IAM policy is available here: http://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_create.html
Documentation on how to create an IAM role for Lambda is available here: http://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-service.html#roles-creatingrole-service-console

2. Create a Lambda javascript function using the [sample](LambdaFunction.js) provided and choose the IAM role created in step 1. Make sure to set the appropriate tags and region per your requirements in configuration section of the Lambda function. 
More information about Lambda is available here: http://docs.aws.amazon.com/lambda/latest/dg/getting-started.html

3. Create a Cloudwatch event rule to trigger the Lambda function created in step 2 matching the WARN status and the Low Utilization EC2 Instances Trusted Advisor check. An example of this is highlighted in the sample [Cloudwatch Event Pattern](CloudwatchEventPattern).
Documentation on to create a Trusted Advisor Cloudwatch events rule is available here: http://docs.aws.amazon.com/awssupport/latest/user/cloudwatch-events-ta.html


![Architecture](images/LowUtilizationEC2InstancesArchitecture.jpg)

More information about Trusted Advisor is available here: https://aws.amazon.com/premiumsupport/trustedadvisor/

Please note that this is a just an example of how to setup automation with Trusted Advisor, Cloudwatch and Lambda. We recommend testing it and tailoring to your envirnment before using in your production envirnment. 

