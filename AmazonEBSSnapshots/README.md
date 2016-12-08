## Amazon EBS Snapshots Fault Tolerance

### Trusted Advisor Check Description
Checks the age of the snapshots for your Amazon Elastic Block Store (Amazon EBS) volumes (available or in-use). Even though Amazon EBS volumes are replicated, failures can occur. Snapshots are persisted to Amazon Simple Storage Service (Amazon S3) for durable storage and point-in-time recovery.

### Setup and Usage
You can automatically create EBS snapshots for volumes that do not have a recent backup as recommended by Trusted Advisor using Amazon Cloudwatch events and AWS Lambda using the following instructions:

1. Create an Amazon IAM role for the Lambda function to use. Attach the [IAM policy](IAMPolicy) to the role in the IAM console.
Documentation on how to create an IAM policy is available here: http://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_create.html
Documentation on how to create an IAM role for Lambda is available here: http://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-service.html#roles-creatingrole-service-console

2. Create a Lambda Node javascript function using the [sample](LambdaFunction.js) provided and choose the IAM role created in step 1. Make sure to set the appropriate tags and region per your requirements in configuration section of the Lambda function. 
More information about Lambda is available here: http://docs.aws.amazon.com/lambda/latest/dg/getting-started.html

3. Create a Cloudwatch event rule to trigger the Lambda function created in step 2 matching the ERROR status and the Amazon EBS Snapshot Trusted Advisor check. An example of this is highlighted in the sample [Cloudwatch Event Pattern](CloudwatchEventPattern).
Documentation on to create a Trusted Advisor Cloudwatch events rule is available here: http://docs.aws.amazon.com/awssupport/latest/user/cloudwatch-events-ta.html

More information about Trusted Advisor is available here: https://aws.amazon.com/premiumsupport/trustedadvisor/

Please note that this is a just an example of how to setup automation with Trusted Advisor, Cloudwatch and Lambda. We recommend testing it and tailoring to your environment before using in your production envirnment. 

