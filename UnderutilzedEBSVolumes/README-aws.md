## Underutilized Amazon EBS Volumes

### Trusted Advisor Check Description
Checks Amazon Elastic Block Store (Amazon EBS) volume configurations and warns when volumes appear to be underused. Charges begin when a volume is created. If a volume remains unattached or has very low write activity (excluding boot volumes) for a period of time, the volume is probably not being used. Trusted Advisor alerts if a volume is unattached or had less than 1 IOPS per day for the past 7 days.

### Setup and Usage
You can automatically create a snapshot and delete EBS volumes that are flagged by Trusted Advisor as underutilized and have not been attached to an instance recently using Amazon Cloudwatch events, Simple Email Service, and AWS Lambda to reduce cost using the following instructions:

Choose **Launch Stack** to launch the CloudFormation template in the US East (N. Virginia) Region in your account:

[![Launch Stop Low Utilization EC2 Instances](../images/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=StopLowUtilizationEC2Instances&templateURL=https://s3-us-west-2.amazonaws.com/aws-trusted-advisor-open-source/cloudformation-templates/TASnapandDeleteEBS.yaml)

Enter your configuration parameters:

[Mailfrom] Email address that notifications will come from. Must be validated in SES

[Mailto] Email address to send notifications to

Make sure to set the appropriate tags and region per your requirements in configuration section of the Lambda function. We recommend running in EnableAction = False mode until you have tested the results.

More information about Trusted Advisor is available here: https://aws.amazon.com/premiumsupport/trustedadvisor/

Please note that this is a just an example of how to setup automation with Trusted Advisor, Cloudwatch and Lambda. We recommend testing it and tailoring to your environment before using in your production environment.
