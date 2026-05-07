"""Tests for the Storage stack."""
import aws_cdk as cdk
from aws_cdk.assertions import Template
from stacks.storage_stack import QuotaAgentStorageStack


def test_storage_stack_creates_bucket():
    app = cdk.App()
    stack = QuotaAgentStorageStack(app, "TestStorageStack")
    template = Template.from_stack(stack)

    template.resource_count_is("AWS::S3::Bucket", 2)
    template.has_resource_properties("AWS::S3::Bucket", {
        "VersioningConfiguration": {"Status": "Enabled"},
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "BlockPublicPolicy": True,
            "IgnorePublicAcls": True,
            "RestrictPublicBuckets": True,
        },
    })


def test_storage_stack_has_lifecycle_rules():
    app = cdk.App()
    stack = QuotaAgentStorageStack(app, "TestStorageStack")
    template = Template.from_stack(stack)

    template.has_resource_properties("AWS::S3::Bucket", {
        "LifecycleConfiguration": {
            "Rules": [
                {"Id": "ExpireOldVersions", "Status": "Enabled"},
                {"Id": "ArchiveRunLogs", "Status": "Enabled"},
            ],
        },
    })


def test_storage_stack_outputs():
    app = cdk.App()
    stack = QuotaAgentStorageStack(app, "TestStorageStack")
    template = Template.from_stack(stack)

    template.has_output("DataBucketName", {})
    template.has_output("FileSystemId", {})
    template.has_output("AccessPointId", {})
