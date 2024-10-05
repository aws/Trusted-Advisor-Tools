# Amazon S3 Incomplete Multipart Upload Abort

## Trusted Advisor Check Description
This check identifies Amazon S3 buckets that do not have appropriate lifecycle policies to abort incomplete multipart uploads. Incomplete multipart uploads can accumulate over time and consume storage space, potentially leading to unnecessary costs. By implementing a lifecycle policy to abort incomplete multipart uploads after a specific period, you can manage your S3 storage more efficiently and reduce costs.

## Setup and Usage
You can automatically apply appropriate lifecycle policies to S3 buckets when recommended by Trusted Advisor using Amazon EventBridge and AWS Lambda for fault tolerance. This solution will add a lifecycle rule to abort incomplete multipart uploads after 7 days for buckets flagged by Trusted Advisor. Deploy using the following instructions:

### CloudFormation Launch Stack
Choose **Launch Stack** to launch the CloudFormation template in the US East (N. Virginia) Region in your account:

[![Launch S3 Incomplete Multipart upload abort Solution](../images/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=TAS3BucketVersioning&templateURL=https://aws-trusted-advisor-open-source.s3.us-west-2.amazonaws.com/cloudformation-templates/ta-s3-incomplete-mpu-abort/template.yaml)
### AWS SAM
If you haven't already, [install AWS SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html). Ensure you are in the `ta-s3-incomplete-mpu-abort` folder then `build` and `deploy` your package:

```bash
cd ta-s3-incomplete-mpu-abort
sam build && sam deploy --guided
```

Follow the prompts in the deploy process to set up your stack name, AWS Region, and other parameters.

### CloudFormation - CLI
First, set up your S3 bucket for the CloudFormation package:

```bash
S3BUCKET=[REPLACE_WITH_YOUR_BUCKET]
```

Ensure you are in the `ta-s3-incomplete-mpu-abort` folder and use the `aws cloudformation package` utility:

```bash
cd ta-s3-incomplete-mpu-abort
aws cloudformation package --region us-east-1 --s3-bucket $S3BUCKET --template template.yaml --output-template-file template.output.yaml
```

Last, deploy the stack with the resulting yaml (`template.output.yaml`) through the CloudFormation Console or command line:

```bash
aws cloudformation deploy --region us-east-1 --template-file template.output.yaml --stack-name TAS3IncompleteMPUAbort --capabilities CAPABILITY_NAMED_IAM
```

## Solution Details
This solution deploys a Lambda function that is triggered by Trusted Advisor check results via EventBridge. When a bucket is identified as non-compliant (lacking an appropriate lifecycle policy for incomplete multipart uploads), the function will:

1. Assume a role in the account where the bucket is located.
2. Check the current lifecycle configuration of the bucket.
3. Add a new rule to abort incomplete multipart uploads after 7 days if such a rule doesn't already exist.

## Testing
To run the unit tests for this project:

```bash
pip install -r tests/requirements.txt
python -m pytest tests/unit -v
```

## Cleanup
To delete the deployed resources, you can use the SAM CLI:

```bash
sam delete --stack-name TAS3IncompleteMPUAbort
```

More information about Trusted Advisor is available here: https://aws.amazon.com/premiumsupport/trustedadvisor/

Please note that this is just an example of how to set up automation with Trusted Advisor, EventBridge, and Lambda. We recommend testing it and tailoring it to your environment before using it in your production environment.