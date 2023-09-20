## IAM Password Policy

### Trusted Advisor Check Description


Checks the password policy for your account and warns when a password policy is not enabled, or if password content requirements have not been enabled.

Password content requirements increase the overall security of your AWS environment by enforcing the creation of strong user passwords. When you create or change a password policy, the change is enforced immediately for new users but does not require existing users to change their passwords.

### Alert Criteria

  * Yellow/Warning: A password policy is enabled, but at least one content requirement is not enabled.

  * Red/Error: No password policy is enabled.

---

### About the Architecture
 Amazon EventBridge captures the Trusted Advisor Check Item Refresh Notification for IAM Password Policy. An AWS Lambda function is triggered via Amazon EventBridge to update the required fields flagged by Trusted Advisor or create a password policy if one doesn't exist.


### Installation

#### AWS SAM
If you havent already, [install AWS SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html). Ensure you are in the `IAMPasswordPolicy` folder then `build` and `deploy` your package

```bash
cd IAMPasswordPolicy
sam build && sam deploy -g
```

#### Cloudformation - CLI
```bash
S3BUCKET=[REPLACE_WITH_YOUR_BUCKET]
```

Ensure you are in the `IAMPasswordPolicy` folder and use the `aws cloudformation package` utility

```bash
cd IAMPasswordPolicy

aws cloudformation package --region us-east-1 --s3-bucket $S3BUCKET --template template.yaml --output-template-file template.output.yaml
```
Last, deploy the stack with the resulting yaml (`template.output.yaml`) through the CloudFormation Console or command line:

```bash
aws cloudformation deploy --region us-east-1 --template-file template.output.yaml --stack-name iam-password-policy --capabilities CAPABILITY_NAMED_IAM
```


More information about Trusted Advisor is available here: https://aws.amazon.com/premiumsupport/trustedadvisor/

Please note that this is a just an example of how to setup automation with Trusted Advisor, Cloudwatch and Lambda. We recommend testing it and tailoring to your environment before using in your production envirnment.

