#!/usr/bin/env python3
"""CDK app entry point for the AWS Quota Increase Support Agent.

Stack wiring order:
  1. NetworkStack — VPC, security groups, VPC endpoints
  2. StorageStack — S3 bucket, Amazon S3 Files filesystem, mount targets, access point
  3. IAMStack     — Lambda role, Scheduler role (needs bucket ARN)
  4. LambdaStack  — Lambda function, scheduler, DLQ, alarms (needs roles + VPC + Amazon S3 Files)
  5. BedrockLoggingStack (opt-in) — Amazon Bedrock — Model invocation logging to CloudWatch Logs

Context variables:
  support_tier    — "basic" (default) or "business". Controls:
                    - VPC endpoints (Support + TrustedAdvisor only on business)
                    - IAM policy (support:* + trustedadvisor:* only on business)
                    Saves ~$29/month on VPC endpoints when using basic.
  bedrock_invocation_logging — "true" to enable Amazon Bedrock model invocation logging.
"""
import aws_cdk as cdk
from stacks.network_stack import QuotaAgentNetworkStack
from stacks.storage_stack import QuotaAgentStorageStack
from stacks.iam_stack import QuotaAgentIAMStack
from stacks.lambda_stack import QuotaAgentLambdaStack
from stacks.bedrock_logging_stack import BedrockLoggingStack

app = cdk.App()

# ── Support tier context ───────────────────────────────────────────────
# Default: "basic" — no Support API / Trusted Advisor endpoints or IAM.
# Set to "business" for accounts with Business or Enterprise support.
support_tier_raw = app.node.try_get_context("support_tier") or "basic"
support_tier = str(support_tier_raw).lower().strip()
if support_tier not in ("basic", "business"):
    raise ValueError(
        f"Invalid support_tier '{support_tier}'. Must be 'basic' or 'business'."
    )

network = QuotaAgentNetworkStack(
    app, "QuotaAgentNetworkStack",
    support_tier=support_tier,
)

storage = QuotaAgentStorageStack(
    app, "QuotaAgentStorageStack",
    vpc=network.vpc,
    mount_target_sg=network.mount_target_sg,
)

iam_stack = QuotaAgentIAMStack(
    app, "QuotaAgentIAMStack",
    data_bucket=storage.data_bucket,
    support_tier=support_tier,
)

lambda_stack = QuotaAgentLambdaStack(
    app, "QuotaAgentLambdaStack",
    lambda_role=iam_stack.lambda_role,
    scheduler_role=iam_stack.scheduler_role,
    bucket_name=storage.data_bucket.bucket_name,
    vpc=network.vpc,
    lambda_sg=network.lambda_sg,
    access_point=storage.access_point,
)

# ── Amazon Bedrock Model Invocation Logging (enabled by default) ─────────────
# Deployed by default for security monitoring and compliance.
# Opt out (not recommended) with: cdk deploy -c bedrock_invocation_logging=false
disable_bedrock_logging = app.node.try_get_context("bedrock_invocation_logging")
if not (disable_bedrock_logging and str(disable_bedrock_logging).lower() == "false"):
    BedrockLoggingStack(app, "QuotaAgentBedrockLoggingStack")

app.synth()
