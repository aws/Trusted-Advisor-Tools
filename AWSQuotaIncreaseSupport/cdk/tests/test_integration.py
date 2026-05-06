"""Integration tests — full CDK synth validation."""
import aws_cdk as cdk
from aws_cdk.assertions import Template
from stacks.storage_stack import QuotaAgentStorageStack
from stacks.iam_stack import QuotaAgentIAMStack
from stacks.lambda_stack import QuotaAgentLambdaStack


def test_full_synth():
    """Test that all stacks synthesize without errors."""
    app = cdk.App()

    storage = QuotaAgentStorageStack(app, "TestStorageStack")
    iam = QuotaAgentIAMStack(app, "TestIAMStack", data_bucket=storage.data_bucket)
    lambda_stack = QuotaAgentLambdaStack(app, "TestLambdaStack",
        lambda_role=iam.lambda_role,
        scheduler_role=iam.scheduler_role,
        bucket_name=storage.data_bucket.bucket_name)

    # Synthesize all stacks
    assembly = app.synth()
    assert len(assembly.stacks) == 3


def test_cross_stack_references():
    """Test that cross-stack references are wired correctly."""
    app = cdk.App()

    storage = QuotaAgentStorageStack(app, "TestStorageStack")
    iam = QuotaAgentIAMStack(app, "TestIAMStack", data_bucket=storage.data_bucket)
    lambda_stack = QuotaAgentLambdaStack(app, "TestLambdaStack",
        lambda_role=iam.lambda_role,
        scheduler_role=iam.scheduler_role,
        bucket_name=storage.data_bucket.bucket_name)

    # Verify Lambda stack has the function
    lambda_template = Template.from_stack(lambda_stack)
    lambda_template.resource_count_is("AWS::Lambda::Function", 1)

    # Verify IAM stack has both roles
    iam_template = Template.from_stack(iam)
    iam_template.resource_count_is("AWS::IAM::Role", 2)

    # Verify Storage stack has the bucket
    storage_template = Template.from_stack(storage)
    storage_template.resource_count_is("AWS::S3::Bucket", 1)
