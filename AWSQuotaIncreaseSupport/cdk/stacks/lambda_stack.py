"""Lambda stack for the AWS Quota Increase Support Agent.

Creates the Lambda function with inline handler code, Lambda layers (AWS CLI,
deepagents, and skill assets), EventBridge Scheduler for 24-hour cadence, DLQ
for failed invocations, and CloudWatch alarms.

The handler bootstraps a deepagents agent with ``create_deep_agent()`` and a
``LocalShellBackend`` rooted at the Amazon S3 Files mount point, then invokes the
agent with a continuation prompt that drives the quota monitoring loop.
"""
import textwrap

import aws_cdk as cdk
from aws_cdk import (
    Duration,
    RemovalPolicy,
    Size,
    aws_cloudwatch as cw,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_scheduler as scheduler,
    aws_sqs as sqs,
)

try:
    from aws_cdk import aws_s3files as s3files
except ImportError:
    # aws_s3files requires aws-cdk-lib >= 2.200 (now pinned to 2.252.0). Provide a stub so
    # the LAMBDA_HANDLER_CODE constant and non-S3Files tests can still
    # import this module on older CDK installations.
    s3files = None  # type: ignore[assignment]

from aws_cdk.lambda_layer_awscli import AwsCliLayer
from constructs import Construct

# ---------------------------------------------------------------------------
# Lambda handler code — inline Python executed inside the Lambda function.
# Must stay under 4096 bytes. Heavy logic lives in the bootstrap layer.
#
# AwsCliLayer installs the AWS CLI v1 at /opt/awscli/aws.
# The handler prepends /opt/awscli: to PATH so `aws` is available.
# AWS_DEFAULT_REGION is set by Lambda runtime. AWS_DEFAULT_OUTPUT is set as env var.
#
# TODO: Enable Anthropic prompt caching once deepagents supports it.
#   The ~16K tokens of tool definitions + system prompt are re-sent on every
#   turn (~100K redundant tokens across a 6-turn run). Marking the system
#   prompt and tool block with `cache_control: {"type": "ephemeral"}` would
#   reduce per-turn input tokens by ~90%.
#   Tracked: https://github.com/langchain-ai/deepagents/issues/917
#
# NOTE: max_tokens fix (2026-04-30)
#   ChatBedrockConverse.max_tokens defaults to None, which causes _drop_none
#   to omit maxTokens from the Converse API inferenceConfig. The Amazon Bedrock
#   Converse API then applies its own model-specific default (~1024 for Claude
#   Sonnet 4), which truncates long edit_file tool calls. We now construct the
#   model explicitly with max_tokens=4096 instead of passing a string spec.
#   The AGENT_MAX_TOKENS env var makes this configurable without a redeploy.
# ---------------------------------------------------------------------------
LAMBDA_HANDLER_CODE = textwrap.dedent('''\
import json, os, datetime

def handler(event, context):
    os.environ["PATH"] = "/opt/awscli:" + os.environ.get("PATH", "")
    mount = os.environ.get("AGENT_MOUNT_PATH", "/mnt/agent")
    model_id = os.environ.get("AGENT_MODEL_ID", "us.amazon.nova-2-lite-v1:0")
    max_tok = int(os.environ.get("AGENT_MAX_TOKENS", "4096"))

    from bootstrap import bootstrap_mount
    bootstrap_mount(mount)

    from langchain_aws import ChatBedrockConverse
    from deepagents import create_deep_agent
    from deepagents.backends.local_shell import LocalShellBackend

    model = ChatBedrockConverse(model=model_id, max_tokens=max_tok)

    backend = LocalShellBackend(
        root_dir=mount, virtual_mode=False, timeout=120, inherit_env=True,
    )
    skills_dir = os.path.join(mount, "skills")
    memory_file = os.path.join(mount, "AGENTS.md")
    context_file = os.path.join(mount, "skills", "aws-quota-increase-support",
                                "CUSTOMER_CONTEXT.md")
    skills = [skills_dir] if os.path.isdir(skills_dir) else []
    memory = [p for p in [memory_file, context_file] if os.path.isfile(p)]

    agent = create_deep_agent(
        model=model, backend=backend, skills=skills, memory=memory,
    )

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    remaining = context.get_remaining_time_in_millis() // 1000
    prompt = f"""## Quota Monitoring Run — {now}

You are the AWS Quota Increase Support Agent. Resume your monitoring loop.

1. Read your memory (AGENTS.md) and customer context (CUSTOMER_CONTEXT.md) to recall previous state and business context.
2. Read your skill file (SKILL.md) for the full workflow.
3. Survey monitored quotas and check pending requests.
4. Run the Before Returning checklist and update AGENTS.md.

Current UTC time: {now}
Remaining Lambda time: {remaining}s

IMPORTANT: You have at most 14 minutes. Be efficient:
- Use AWS CLI via execute tool for ALL AWS calls — do NOT use boto3
- Read CUSTOMER_CONTEXT.md for business context needed by the Autonomous Action Policy
- Prefer memorized commands from AGENTS.md over rediscovery
- get-service-quota wraps fields under Quota — use Quota.QuotaName, Quota.Value etc.
- CASE_CLOSED is ambiguous — compare DesiredValue vs applied to disambiguate
- Follow the Autonomous Action Policy before submitting any increase
- Use edit_file (not write_file) to update AGENTS.md
- Stop with at least 60s remaining to run the Before Returning checklist"""

    result = agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]},
    )
    last_msg = result["messages"][-1].content if result.get("messages") else "No output"
    return {
        "statusCode": 200,
        "body": json.dumps({"run_time": now, "result": last_msg[:1000]}),
    }
''')


class QuotaAgentLambdaStack(cdk.Stack):
    """Lambda function, EventBridge Scheduler, DLQ, and CloudWatch alarms.

    Creates:
    - Lambda function (Python 3.14, 15-min timeout, 2048 MB, inline handler)
    - Lambda layers: AWS CLI + deepagents SDK + skill assets (SKILL.md + bootstrap)
    - Amazon S3 Files mount at /mnt/agent
    - EventBridge Scheduler (rate: 24 hours, 60-min flexible window)
    - SQS dead-letter queue (14-day retention for failed invocations)
    - CloudWatch alarms: failures, duration warning, DLQ depth
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        lambda_role: iam.IRole = None,
        scheduler_role: iam.IRole = None,
        bucket_name: str = None,
        vpc: ec2.IVpc = None,
        lambda_sg: ec2.ISecurityGroup = None,
        access_point=None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── Lambda Layers ─────────────────────────────────────────────
        # AwsCliLayer: CDK-managed layer that installs AWS CLI v1 at
        # /opt/awscli/aws. No Docker or custom build required.
        aws_cli_layer = AwsCliLayer(self, "AwsCliLayer")

        deepagents_layer = lambda_.LayerVersion(
            self, "DeepagentsLayer",
            code=lambda_.Code.from_asset("layers/deepagents"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_14],
            description="deepagents SDK + langchain-aws (Amazon Bedrock) dependencies",
        )

        skill_assets_layer = lambda_.LayerVersion(
            self, "SkillAssetsLayer",
            code=lambda_.Code.from_asset("layers/skill_assets"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_14],
            description="Bootstrap helper + SKILL.md for agent initialization",
        )

        # ── Amazon S3 Files Mount ────────────────────────────────────────────
        filesystem = None
        if access_point:
            filesystem = lambda_.FileSystem.from_s3_files_access_point(
                access_point, "/mnt/agent"
            )

        # ── Lambda Function ───────────────────────────────────────────
        agent_function = lambda_.Function(
            self, "QuotaAgent",
            function_name="QuotaAgent",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="index.handler",
            code=lambda_.Code.from_inline(LAMBDA_HANDLER_CODE),
            timeout=Duration.minutes(15),
            memory_size=2048,
            ephemeral_storage_size=Size.mebibytes(1024),
            role=lambda_role,
            reserved_concurrent_executions=1,
            layers=[aws_cli_layer, deepagents_layer, skill_assets_layer],
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            ) if vpc else None,
            security_groups=[lambda_sg] if lambda_sg else None,
            filesystem=filesystem,
            # Lambda encrypts env vars with AWS-managed key by default
            environment={
                "AGENT_MOUNT_PATH": "/mnt/agent",
                "AGENT_MODEL_ID": "us.amazon.nova-2-lite-v1:0",
                "AGENT_MAX_TOKENS": "4096",
                "AWS_ACCOUNT_ID": cdk.Aws.ACCOUNT_ID,
                # AWS_DEFAULT_REGION is set automatically by Lambda runtime
                # to the function's region — do NOT set it manually (reserved).
                # AWS_DEFAULT_OUTPUT is not reserved, so we set it here.
                "AWS_DEFAULT_OUTPUT": "json",
            },
        )

        # SQS Dead-Letter Queue
        dlq = sqs.Queue(
            self, "AgentDLQ",
            queue_name="QuotaAgent-DLQ",
            retention_period=Duration.days(14),
        )

        # Grant Scheduler role permission to invoke Lambda and send to DLQ
        if scheduler_role:
            iam.Policy(
                self, "SchedulerInvokePolicy",
                roles=[scheduler_role],
                statements=[
                    iam.PolicyStatement(
                        actions=["lambda:InvokeFunction"],
                        resources=[agent_function.function_arn],
                    ),
                    iam.PolicyStatement(
                        actions=["sqs:SendMessage"],
                        resources=[dlq.queue_arn],
                    ),
                ],
            )

        # EventBridge Scheduler — 24-hour cadence
        scheduler.CfnSchedule(
            self, "DailySchedule",
            schedule_expression="rate(24 hours)",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(
                mode="FLEXIBLE",
                maximum_window_in_minutes=60,
            ),
            target=scheduler.CfnSchedule.TargetProperty(
                arn=agent_function.function_arn,
                role_arn=scheduler_role.role_arn if scheduler_role else "",
                retry_policy=scheduler.CfnSchedule.RetryPolicyProperty(
                    maximum_event_age_in_seconds=3600,
                    maximum_retry_attempts=2,
                ),
                dead_letter_config=scheduler.CfnSchedule.DeadLetterConfigProperty(
                    arn=dlq.queue_arn,
                ),
            ),
        )

        # CloudWatch Alarms
        cw.Alarm(
            self, "AgentFailureAlarm",
            alarm_name="QuotaAgent-Failures",
            metric=agent_function.metric_errors(period=Duration.hours(24)),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )

        cw.Alarm(
            self, "AgentDurationAlarm",
            alarm_name="QuotaAgent-Duration-Warning",
            metric=agent_function.metric_duration(period=Duration.hours(24)),
            threshold=840_000,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        cw.Alarm(
            self, "DLQAlarm",
            alarm_name="QuotaAgent-DLQ",
            metric=dlq.metric_approximate_number_of_messages_visible(),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        )

        self.function_name = agent_function.function_name

        cdk.CfnOutput(
            self, "FunctionName",
            value=agent_function.function_name,
            description="Lambda function name",
        )
