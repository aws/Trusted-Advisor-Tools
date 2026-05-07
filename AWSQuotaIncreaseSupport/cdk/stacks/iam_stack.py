"""IAM stack for the AWS Quota Increase Support Agent.

Creates least-privilege IAM roles for Lambda execution and EventBridge Scheduler.
The Lambda role includes permissions for Amazon Bedrock (LLM inference via the
deepagents SDK), Service Quotas (read + request increases), CloudWatch,
and Amazon S3 Files mount/write.

Accepts a ``support_tier`` parameter ("basic" or "business") to control
whether Support API and Trusted Advisor permissions are included.

Security Responsibilities (AWS Shared Responsibility Model):
    AWS manages the IAM service infrastructure, API availability, and credential
    vending for Lambda execution roles.

    Customers are responsible for:
    (1) Defining least-privilege policies — implemented here with service-specific
        actions, resource-scoped ARNs, and condition keys.
    (2) Managing role trust relationships — restricted to lambda.amazonaws.com
        and scheduler.amazonaws.com service principals only.
    (3) Auditing policy usage — CloudTrail captures all IAM and STS API calls.
    (4) Reviewing and updating policies when agent capabilities change.

    This stack implements least-privilege policies for Lambda execution and
    EventBridge Scheduler invocation. See SECURITY.md for the complete key
    management strategy and THREAT_MODEL.md for the risk assessment.
"""
import aws_cdk as cdk
from aws_cdk import (
    aws_iam as iam,
    aws_s3 as s3,
)
from constructs import Construct


class QuotaAgentIAMStack(cdk.Stack):
    """IAM roles for Lambda and EventBridge Scheduler.

    Creates:
    - Lambda execution role with policies for Amazon S3 Files, Service Quotas,
      S3, CloudWatch Logs, CloudWatch Metrics, Amazon Bedrock, and VPC networking.
      Conditionally adds Support + TrustedAdvisor on business tier.
    - EventBridge Scheduler role (invoke grants added by Lambda stack)

    Exports: lambda_role, scheduler_role
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        data_bucket: s3.IBucket = None,
        support_tier: str = "basic",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._data_bucket = data_bucket

        # ── Build IAM statements ──────────────────────────────────────
        statements = [
            # Amazon S3 Files — mount, write, and root access
            # Scoped to Amazon S3 Files filesystem ARNs in this account/region
            iam.PolicyStatement(
                sid="S3FilesAccess",
                actions=[
                    "s3files:ClientMount",
                    "s3files:ClientWrite",
                    "s3files:ClientRootAccess",
                ],
                resources=[
                    f"arn:aws:s3files:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:file-system/*",
                ],
            ),
            # S3 direct read (Amazon S3 Files optimizes reads via S3)
            # Scoped to the specific data bucket ARN
            iam.PolicyStatement(
                sid="S3DirectRead",
                actions=[
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                ],
                resources=[
                    data_bucket.arn_for_objects("*") if data_bucket
                    else f"arn:aws:s3:::quota-agent-data-{cdk.Aws.ACCOUNT_ID}-{cdk.Aws.REGION}/*"
                ],
            ),
            # Service Quotas — full read access
            # Note: Service Quotas read actions do not support resource-level
            # permissions per AWS documentation. Resource: "*" is required.
            iam.PolicyStatement(
                sid="ServiceQuotasRead",
                actions=[
                    "servicequotas:ListServices",
                    "servicequotas:ListServiceQuotas",
                    "servicequotas:ListAWSDefaultServiceQuotas",
                    "servicequotas:GetServiceQuota",
                    "servicequotas:GetAWSDefaultServiceQuota",
                    "servicequotas:ListRequestedServiceQuotaChangeHistory",
                    "servicequotas:ListRequestedServiceQuotaChangeHistoryByQuota",
                    "servicequotas:GetRequestedServiceQuotaChange",
                    "servicequotas:ListTagsForResource",
                ],
                resources=["*"],
            ),
            # Service Quotas — write (submit increase requests)
            # Restricted to services monitored by the agent (per CUSTOMER_CONTEXT.md)
            iam.PolicyStatement(
                sid="ServiceQuotasWrite",
                actions=[
                    "servicequotas:RequestServiceQuotaIncrease",
                ],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "servicequotas:service": [
                            "ec2",
                            "elasticloadbalancing",
                            "vpc",
                            "ecs",
                            "lambda",
                            "s3",
                            "sns",
                            "sqs",
                            "lightsail",
                            "cloudformation",
                        ],
                    },
                },
            ),
            # CloudWatch Metrics
            # Note: cloudwatch:GetMetricStatistics does not support resource-level
            # permissions per AWS documentation. Resource: "*" is required.
            iam.PolicyStatement(
                sid="CloudWatchMetricsRead",
                actions=[
                    "cloudwatch:GetMetricStatistics",
                ],
                resources=["*"],
            ),
            # Amazon Bedrock — LLM inference via cross-region inference profile
            # The us.amazon.nova-2-lite-v1:0 inference profile routes to foundation
            # models in us-east-1, us-east-2, and us-west-2. IAM must allow access
            # to both the inference profile AND the underlying foundation models.
            iam.PolicyStatement(
                sid="BedrockInvoke",
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    f"arn:aws:bedrock:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:inference-profile/us.amazon.nova-2-lite-v1:0",
                    "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-2-lite-v1:0",
                    "arn:aws:bedrock:us-east-2::foundation-model/amazon.nova-2-lite-v1:0",
                    "arn:aws:bedrock:us-west-2::foundation-model/amazon.nova-2-lite-v1:0",
                ],
            ),
        ]

        # Business/Enterprise support: add Support API + Trusted Advisor
        # Note: Support API and Trusted Advisor actions do not support
        # resource-level permissions per AWS documentation. Resource: "*" is required.
        if support_tier == "business":
            statements.append(
                iam.PolicyStatement(
                    sid="SupportAPIAccess",
                    actions=[
                        "support:DescribeSeverityLevels",
                        "support:DescribeTrustedAdvisorCheckResult",
                        "support:DescribeTrustedAdvisorChecks",
                        "support:RefreshTrustedAdvisorCheck",
                        "support:DescribeCases",
                        "support:DescribeCommunications",
                        "support:AddCommunicationToCase",
                    ],
                    resources=["*"],
                ),
            )
            statements.append(
                iam.PolicyStatement(
                    sid="TrustedAdvisorAccess",
                    actions=[
                        "trustedadvisor:ListChecks",
                        "trustedadvisor:GetCheckResult",
                        "trustedadvisor:ListCheckSummaries",
                    ],
                    resources=["*"],
                ),
            )

        self.lambda_role = iam.Role(
            self, "AgentLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                ),
            ],
            inline_policies={
                "AgentPermissions": iam.PolicyDocument(statements=statements),
            },
        )

        # S3 — read/write agent state bucket
        if self._data_bucket:
            self._data_bucket.grant_read_write(self.lambda_role)

        # EventBridge Scheduler role
        self.scheduler_role = iam.Role(
            self, "SchedulerRole",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
        )
