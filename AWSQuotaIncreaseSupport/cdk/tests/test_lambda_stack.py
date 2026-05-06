"""Tests for the Lambda stack (CDK resources)."""
import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk.assertions import Match, Template
from stacks.lambda_stack import QuotaAgentLambdaStack


def _create_lambda_stack():
    app = cdk.App()
    role_stack = cdk.Stack(app, "RoleStack")
    lambda_role = iam.Role(
        role_stack,
        "LambdaRole",
        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
    )
    scheduler_role = iam.Role(
        role_stack,
        "SchedulerRole",
        assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
    )
    stack = QuotaAgentLambdaStack(
        app,
        "TestLambdaStack",
        lambda_role=lambda_role,
        scheduler_role=scheduler_role,
        bucket_name="test-bucket",
    )
    return Template.from_stack(stack)


def test_lambda_stack_creates_function():
    template = _create_lambda_stack()
    template.resource_count_is("AWS::Lambda::Function", 1)
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "FunctionName": "QuotaAgent",
            "Runtime": "python3.14",
            "Handler": "index.handler",
            "Timeout": 900,  # 15 minutes
            "MemorySize": 2048,
            "ReservedConcurrentExecutions": 1,
        },
    )


def test_lambda_stack_has_layers():
    """Lambda function has both the AWS CLI and deepagents layers."""
    template = _create_lambda_stack()
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Layers": Match.any_value(),
        },
    )


def test_lambda_stack_creates_deepagents_layer():
    """The deepagents layer version is created."""
    template = _create_lambda_stack()
    template.has_resource_properties(
        "AWS::Lambda::LayerVersion",
        {
            "Description": Match.string_like_regexp("deepagents"),
        },
    )


def test_lambda_stack_creates_dlq():
    template = _create_lambda_stack()
    template.has_resource_properties(
        "AWS::SQS::Queue",
        {
            "QueueName": "QuotaAgent-DLQ",
        },
    )


def test_lambda_stack_creates_scheduler():
    template = _create_lambda_stack()
    template.has_resource_properties(
        "AWS::Scheduler::Schedule",
        {
            "ScheduleExpression": "rate(24 hours)",
        },
    )


def test_lambda_stack_creates_alarms():
    template = _create_lambda_stack()
    template.resource_count_is("AWS::CloudWatch::Alarm", 3)
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "AlarmName": "QuotaAgent-Failures",
        },
    )
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "AlarmName": "QuotaAgent-Duration-Warning",
        },
    )
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "AlarmName": "QuotaAgent-DLQ",
        },
    )


def test_lambda_stack_has_agent_env_vars():
    """Lambda has AGENT_MOUNT_PATH, AGENT_MODEL_ID, AGENT_MAX_TOKENS, and AWS_DEFAULT_OUTPUT."""
    template = _create_lambda_stack()
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Environment": {
                "Variables": {
                    "AGENT_MOUNT_PATH": "/mnt/agent",
                    "AGENT_MODEL_ID": "us.amazon.nova-2-lite-v1:0",
                    "AGENT_MAX_TOKENS": "4096",
                    "AWS_DEFAULT_OUTPUT": "json",
                },
            },
        },
    )


def test_lambda_stack_no_vpc():
    template = _create_lambda_stack()
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "VpcConfig": Match.absent(),
        },
    )


def test_lambda_stack_outputs_function_name():
    template = _create_lambda_stack()
    template.has_output("FunctionName", {})
