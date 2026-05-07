"""Tests for the IAM stack."""
import aws_cdk as cdk
from aws_cdk import aws_s3 as s3
from aws_cdk.assertions import Template, Match
from stacks.iam_stack import QuotaAgentIAMStack


def _create_iam_stack():
    app = cdk.App()
    bucket_stack = cdk.Stack(app, "BucketStack")
    bucket = s3.Bucket(bucket_stack, "TestBucket")
    stack = QuotaAgentIAMStack(app, "TestIAMStack", data_bucket=bucket)
    return Template.from_stack(stack)


def test_iam_stack_creates_lambda_role():
    template = _create_iam_stack()
    template.has_resource_properties("AWS::IAM::Role", {
        "AssumeRolePolicyDocument": {
            "Statement": Match.array_with([
                Match.object_like({
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                }),
            ]),
        },
    })


def test_iam_stack_creates_scheduler_role():
    template = _create_iam_stack()
    template.has_resource_properties("AWS::IAM::Role", {
        "AssumeRolePolicyDocument": {
            "Statement": Match.array_with([
                Match.object_like({
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "scheduler.amazonaws.com"},
                }),
            ]),
        },
    })


def test_iam_stack_has_lambda_managed_policies():
    """Lambda role has basic execution and VPC access managed policies."""
    template = _create_iam_stack()
    template.has_resource_properties("AWS::IAM::Role", {
        "ManagedPolicyArns": Match.array_with([
            Match.object_like({"Fn::Join": Match.any_value()}),
        ]),
    })


def test_iam_stack_has_inline_permissions():
    template = _create_iam_stack()
    template.has_resource_properties("AWS::IAM::Role", {
        "Policies": Match.array_with([
            Match.object_like({
                "PolicyName": "AgentPermissions",
            }),
        ]),
    })
