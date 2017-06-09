# Trusted Advisor Exposed Keys CloudWatch Event Monitor

The Trusted Advisor Exposed Keys CloudWatch Event Monitor demonstrates how to use [AWS Step Functions](https://aws.amazon.com/step-functions/) to orchestrate a serverless workflow using [AWS Lambda](http://aws.amazon.com/lambda/) in response to a [CloudWatch](https://aws.amazon.com/cloudwatch/) Event. On detection of a Trusted Advisor Exposed Access Key CloudWatch Event this workflow deletes the exposed IAM Access Key, summarizes the recent API activity for the exposed key, and sends the summary message to an SNS Topic to notify the subscribers.

This repository contains sample code for all the Lambda functions depicted in the diagram below as well as an AWS CloudFormation template for creating the functions and related resources.

![screenshot for instruction](images/Architecture.png)

### Walkthrough of the architecture
1. An IAM Access Key is inadvertently uploaded to one of the popular code repositories monitored by Trusted Advisor (ex: github)
2. Trusted Advisor detects the key, triggering a Trusted Advisor Exposed Access Keys CloudWatch Event. AWS also temporarily restricts the API calls the key is able to make.
3. A configured CloudWatch Events rule matches this event, triggering an execution of the `ExposedKey` state machine, which has the following sub-steps:
  * Delete the exposed IAM Access Key Pair
  * Summarize recent API activity for the user
  * Send security notification message containing summary to `SecurityNotificationTopic` SNS Topic.

## Running the Example
 
#### Option 1: Launch the CloudFormation Template in US East - N. Virginia (us-east-1) 
The backend infrastructure can be deployed in US East - N. Virginia (us-east-1) using the provided CloudFormation template.
Click **Launch Stack** to launch the template in the US East - N. Virginia (us-east-1) region in your account:

[![Launch Trusted Advisor Exposed Keys CloudWatch Event Monitor into N. Virginia with CloudFormation](http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/images/cloudformation-launch-stack-button.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=ExposedAccessKeysMonitor&templateURL=https://s3.amazonaws.com/exposed-keys-project/delete_exposed_keys.packaged.yaml)

(In the last page of the wizard, make sure to:

1. Click the checkboxes to give AWS CloudFormation permission to **"create IAM resources"** and **"create IAM resources with custom names"**
2. Follow the instructions to **"Create Change Set"** 
3. Click **"Execute"**
)

#### Option 2: Launch the CloudFormation Template manually 

If you would like to deploy the template manually, you need a S3 bucket in the target region, and then package the Lambda functions into that S3 bucket by using the `aws cloudformation package` utility.

** Note that this template may only be launched into US East - N. Virginia (us-east-1) as that is the only region where Trusted Advisor CloudWatch Event rules are configurable. **


Set environment variables for later commands to use:

```bash
S3BUCKET=[REPLACE_WITH_YOUR_BUCKET]
```

Then go to the `cloudformation` folder and use the `aws cloudformation package` utility

```bash
cd cloudformation

aws cloudformation package --region us-east-1 --s3-bucket $S3BUCKET --template exposed_access_keys.serverless.yaml --output-template-file exposed_access_keys.output.yaml
```
Last, deploy the stack with the resulting yaml (`exposed_access_keys.output.yaml`) through the CloudFormation Console or command line:

```bash
aws cloudformation deploy --region us-east-1 --template-file exposed_access_keys.output.yaml --stack-name ExposedAccessKeysMonitor --capabilities CAPABILITY_NAMED_IAM
```

## Testing the Example
To test the example without exposing an IAM Access Key to a public repository you can simulate the workflow by executing the `ExposedKey` state machine with a set of test json for the event. To do this follow the steps detailed below.

Ensure you have at least one E-mail address [subscribed](http://docs.aws.amazon.com/sns/latest/dg/SubscribeTopic.html) to the `SecurityNotificationTopic` created by the template to receive the notification.

1. Go to the [Identity & Access Management](https://console.aws.amazon.com/iam/home) console
2. Go to `Users`
3. Click `Add User` and create a user with programmatic access
  * For the `User name` put `test-user`
  * For `Access type` select `Programmatic access`
  * **Do not set any permissions for the user**
  * Note the `Access key ID` from the Review page for later use in the test json
4. Go to the [Step Functions](https://console.aws.amazon.com/states/home?region=us-east-1#/) console
5. Select the `ExposedKey` state machine
6. Click `New execution` to create the test execution of the state machine
  * Copy and paste the json below to the execution json field
  * Replace `ACCESS_KEY_ID_HERE` with the `Access key ID` noted from the earlier creation of `test-user`
  * You do not need to enter an execution id as one will be randomly generated by default
```json
{
  "check-name": "Exposed Access Keys",
  "check-item-detail": {
    "Case ID": "02648f3b-e18f-4019-8d68-ce25efe080ff",
    "Usage (USD per Day)": "0",
    "User Name (IAM or Root)": "test-user",
    "Deadline": "1440453299248",
    "Access Key ID": "ACCESS_KEY_ID_HERE",
    "Time Updated": "1440021299248",
    "Fraud Type": "Exposed",
    "Location": "www.github.com"
  },
  "status": "ERROR",
  "resource_id": "",
  "uuid": "cce6d28f-e44b-4e61-aba1-5b4af96a0f59"
}
```

You can follow the state machine's progress in the Step Functions console. The summary message for `test-user` will be sent to the e-mail address(es) subscribed to the `SecurityNotificationTopic` SNS Topic.
 * **Note that the summary for this user will likely be empty as it will not have logged any API calls to CloudTrail**


## Cleaning Up the Stack Resources

To remove all resources created by this example, do the following:

1. Delete the CloudFormation stack.
1. Delete the CloudWatch log groups associated with each Lambda function created by the CloudFormation stack.

## CloudFormation template resources

The following sections explain all of the resources created by the CloudFormation template provided with this example.

### CloudWatch
- **TrustedAdvisorExposedKeyRule** - A CloudWatch Events Rule to detect Trusted Advisor Exposed Key events and send them to the Step Functions state machine target

### Step Functions
- **ExposedKeysStepFunction** - A Step Functions state machine that orchestrates the access key deletion, API call summary, and notification of security

### Lambda
- **DeleteAccessKeyPair** - Lambda function that deletes the exposed IAM Access Key Pair associated with username provided by event.
- **LookupCloudTrailEvents** - Lambda function that looks up and summarizes recent API activity for the exposed access key provided by the event.
- **NotifySecurity** - Lambda function that constructs and sends security notification message containing API activity summary to SNS Topic created by this CloudFormation template.

### SNS
- **NotificationTopic** - SNS Topic that API activity security message is sent to.

### IAM
- **ExecuteStateMachineRole** - IAM Role with policy that allows CloudWatch Events rule to invoke executions of Step Functions state machines
- **LambdaDeleteAccessKeyPairRole** - IAM Role with policy that allows Lambda function to invoke "iam:DeleteAccessKey" API call and write log messages to CloudWatch Logs.
- **LambdaLookupCloudTrailEventsRole** - IAM Role with policy that allows Lambda function to invoke "cloudtrail:LookupEvents" API call and write log messages to CloudWatch Logs.
- **LambdaSnsPublishRole** - IAM Role with policy that allows Lambda function to invoke "sns:Publish" API call and write log messages to CloudWatch Logs.


## License

This reference architecture sample is licensed under Apache 2.0.