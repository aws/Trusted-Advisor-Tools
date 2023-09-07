## Unassociated Elastic IP Addresses

### Trusted Advisor Check Description
  Checks for Elastic IP addresses (EIPs) that are not associated with a running Amazon Elastic Compute Cloud (Amazon EC2) instance.

  EIPs are static IP addresses designed for dynamic cloud computing. Unlike traditional static IP addresses, EIPs mask the failure of an instance or Availability Zone by remapping a public IP address to another instance in your account. A nominal charge is imposed for an EIP that is not associated with a running instance.


### About the Architecture
 Amazon EventBridge captures the Trusted Advisor Check Item Refresh Notification for Unassociated Elastic IPs. An AWS Lambda function is triggered via Amazon EventBridge to release the Elastic IP address. The Lambda function will ignore Elastic IP addresses that are tagged with the key "TrustedAdvisorAutomate" with a value of "false". 

![screenshot for instruction](images/Architecture.png)

### Important Note
This script has the DryRun flag set to True by default for the [ec2.release_address()](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/release_address.html) API call. When you are ready to proceed after tagging resources you intend to keep, you can change this value to False


### Installation

#### AWS SAM
If you havent already, [install AWS SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html). Ensure you are in the `UnassociatedElasticIPs` folder then `build` and `deploy` your package

```bash
cd UnassociatedElasticIPs
sam build && sam deploy -g
```

#### Cloudformation - CLI
```bash
S3BUCKET=[REPLACE_WITH_YOUR_BUCKET]
```

Ensure you are in the `UnassociatedElasticIPs` folder and use the `aws cloudformation package` utility

```bash
cd UnassociatedElasticIPs

aws cloudformation package --region us-east-1 --s3-bucket $S3BUCKET --template template.yaml --output-template-file template.output.yaml
```
Last, deploy the stack with the resulting yaml (`template.output.yaml`) through the CloudFormation Console or command line:

```bash
aws cloudformation deploy --region us-east-1 --template-file exposed_access_keys.output.yaml --stack-name unassociated-elastic-ips --capabilities CAPABILITY_NAMED_IAM
```


More information about Trusted Advisor is available here: https://aws.amazon.com/premiumsupport/trustedadvisor/

Please note that this is a just an example of how to setup automation with Trusted Advisor, Cloudwatch and Lambda. We recommend testing it and tailoring to your environment before using in your production envirnment.

