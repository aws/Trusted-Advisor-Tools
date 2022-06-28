# Trusted_Advisor-3rd-Paty-Integrations
# Authors: Manas Satpathi and Sandeep Mohanty
# Description/Use-case: Use these solutions to integrate AWS Trusted Advisor with 3rd party tools, for example Slack. This is a sample project, we expect our customers to review and test it before using for production use.

Use any of these automated solution to get notified for AWS Trusted Advisor findings with status red/error (actions required). High priority Trusted Advisor checks require further investigation as they help you secure and optimize your account to align with AWS best practices. Notifications are classified by risk category (Security, Fault Tolerance, Performance, Cost and Service Limits) and sent to your preferred monitoring or DevOps tools at a preconfigured interval.  Configure the notification interval as a scheduled event rule in Amazon EventBridge. Modify the included python script to customize the solution further to meet your requirements.

## Solution Overview
Deploying this solution automates the process of checking, and delivery of specific alerts from Trusted Advisor to with your preferred 3rd paty tools.

The following diagram illustrates how the solution works,

![image](./TA-Slack-Arch.PNG)

## How it works

Review the README files specific to the solution in the solutions folder.

## Deploy the solution

Review the README files specific to the solution in the solutions folder.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

