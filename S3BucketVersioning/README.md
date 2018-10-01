## Amazon S3 Bucket Versioning

### Trusted Advisor Check Description
Checks for Amazon Simple Storage Service buckets that do not have versioning enabled, or have versioning suspended. When versioning is enabled, you can easily recover from both unintended user actions and application failures. Versioning allows you to preserve, retrieve, and restore any version of any object stored in a bucket. You can use lifecycle rules to manage all versions of your objects as well as their associated costs by automatically archiving objects to the Glacier storage class or removing them after a specified time period. You can also choose to require multi-factor authentication (MFA) for any object deletions or configuration changes to your buckets. 

### Setup and Usage
You can automatically enable S3 bucket versioning when recommended by Trusted Advisor using Amazon Cloudwatch events and AWS Lambda for fault tolerance using the following instructions:

Choose **Launch Stack** to launch the CloudFormation template in the US East (N. Virginia) Region in your account:

[![Launch Stop Low Utilization EC2 Instances](../images/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=TAS3BucketVersioning&templateURL=https://s3-us-west-2.amazonaws.com/aws-trusted-advisor-open-source/cloudformation-templates/TAS3BucketVersioning.json)

More information about Trusted Advisor is available here: https://aws.amazon.com/premiumsupport/trustedadvisor/

Please note that this is a just an example of how to setup automation with Trusted Advisor, Cloudwatch and Lambda. We recommend testing it and tailoring to your environment before using in your production envirnment.

