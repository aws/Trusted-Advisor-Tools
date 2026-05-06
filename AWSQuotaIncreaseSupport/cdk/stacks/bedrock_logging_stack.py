"""Amazon Bedrock Model Invocation Logging stack.

Enables Amazon Bedrock model invocation logging to CloudWatch Logs so you can
inspect the full request/response data for every Converse, InvokeModel, and
InvokeModelWithResponseStream call made by the agent.

This is an account-level setting managed via an AwsCustomResource that calls the
PutModelInvocationLoggingConfiguration / DeleteModelInvocationLoggingConfiguration
Amazon Bedrock APIs on create/update and delete respectively.

IMPORTANT: This stack is deployed by default for security monitoring and compliance.
    Amazon Bedrock invocation logs capture all LLM prompts and responses, enabling:
    - Detection of prompt injection attempts
    - Monitoring for unexpected agent behavior
    - Post-incident investigation and forensics
    - Compliance audit trails

    To opt out (not recommended): cdk deploy -c bedrock_invocation_logging=false

Usage:
    Enabled by default. Opt out with CDK context variable
    ``bedrock_invocation_logging=false``.
"""
import aws_cdk as cdk
from aws_cdk import (
    RemovalPolicy,
    aws_iam as iam,
    aws_logs as logs,
    custom_resources as cr,
    CfnOutput,
)
from constructs import Construct


class BedrockLoggingStack(cdk.Stack):
    """Amazon Bedrock Model Invocation Logging (opt-in).

    Creates:
    - CloudWatch Logs log group for Amazon Bedrock invocation logs
    - IAM role trusted by bedrock.amazonaws.com for log delivery
    - AwsCustomResource that calls PutModelInvocationLoggingConfiguration
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── CloudWatch Log Group for Amazon Bedrock Invocation Logs ───────────
        # Uses AWS-managed encryption (default for CloudWatch Logs)
        self.invocation_log_group = logs.LogGroup(
            self, "BedrockInvocationLogGroup",
            log_group_name="/aws/bedrock/invocation-logs",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ── IAM Role for Amazon Bedrock to write logs ────────────────────────
        bedrock_logging_role = iam.Role(
            self, "BedrockLoggingRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )
        self.invocation_log_group.grant_write(bedrock_logging_role)

        # ── AwsCustomResource to enable Amazon Bedrock invocation logging ────
        # Uses the AWS SDK directly — no Lambda handler code needed.
        logging_config_params = {
            "loggingConfig": {
                "cloudWatchConfig": {
                    "logGroupName": self.invocation_log_group.log_group_name,
                    "roleArn": bedrock_logging_role.role_arn,
                },
                "textDataDeliveryEnabled": True,
                "imageDataDeliveryEnabled": False,
                "embeddingDataDeliveryEnabled": False,
            },
        }

        self.logging_cr = cr.AwsCustomResource(
            self, "EnableBedrockInvocationLogging",
            on_create=cr.AwsSdkCall(
                service="Bedrock",
                action="PutModelInvocationLoggingConfiguration",
                parameters=logging_config_params,
                physical_resource_id=cr.PhysicalResourceId.of(
                    "bedrock-invocation-logging"
                ),
            ),
            on_update=cr.AwsSdkCall(
                service="Bedrock",
                action="PutModelInvocationLoggingConfiguration",
                parameters=logging_config_params,
                physical_resource_id=cr.PhysicalResourceId.of(
                    "bedrock-invocation-logging"
                ),
            ),
            on_delete=cr.AwsSdkCall(
                service="Bedrock",
                action="DeleteModelInvocationLoggingConfiguration",
                parameters={},
            ),
            install_latest_aws_sdk=False,
            policy=cr.AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(
                    actions=[
                        "bedrock:PutModelInvocationLoggingConfiguration",
                        "bedrock:GetModelInvocationLoggingConfiguration",
                        "bedrock:DeleteModelInvocationLoggingConfiguration",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    actions=["iam:PassRole"],
                    resources=[bedrock_logging_role.role_arn],
                ),
            ]),
        )

        # Ensure role exists before we try to configure logging
        self.logging_cr.node.add_dependency(bedrock_logging_role)

        # ── Outputs ───────────────────────────────────────────────────
        CfnOutput(
            self, "LogGroupName",
            value=self.invocation_log_group.log_group_name,
            description="CloudWatch log group for Amazon Bedrock model invocation logs",
        )

        CfnOutput(
            self, "LoggingRoleArn",
            value=bedrock_logging_role.role_arn,
            description="IAM role ARN used by Amazon Bedrock for log delivery",
        )
