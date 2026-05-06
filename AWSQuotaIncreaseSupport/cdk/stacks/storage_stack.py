"""Storage stack for the AWS Quota Increase Support Agent.

Creates the S3 bucket, Amazon S3 Files filesystem, mount targets, and access point
for agent state persistence (memory, logs, todos).

Security Responsibilities (AWS Shared Responsibility Model):
    AWS secures the underlying S3 storage infrastructure, replication,
    durability, and Amazon S3 Files service availability.

    Customers are responsible for:
    (1) Configuring encryption at rest — implemented: AWS-managed SSE-S3 encryption
        
    (2) Blocking public access — implemented: BlockPublicAccess.BLOCK_ALL.
    (3) Enforcing TLS for data in transit — implemented: bucket policy with
        aws:SecureTransport condition denying non-HTTPS requests.
    (4) Defining bucket policies and lifecycle rules — implemented: 90-day
        version expiration, 30-day Glacier transition for run logs.
    (5) Enabling versioning for data protection — implemented: versioned=True.
    (6) Monitoring access via CloudTrail and S3 access logs — implemented:
        server access logging to dedicated logging bucket.

    Note on Amazon S3 Files NFS traffic: NFS traffic between Lambda and mount targets
    (port 2049) is not encrypted in transit. Compensating controls: VPC isolation
    (private isolated subnets), security group restriction (NFS from Lambda SG
    only), and AWS VPC tenant isolation. See SECURITY.md for full assessment.
"""
import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3files as s3files,
    Duration,
    RemovalPolicy,
)
from constructs import Construct


class QuotaAgentStorageStack(cdk.Stack):
    """S3 bucket + Amazon S3 Files filesystem for the Quota Agent.

    Creates:
    - S3 bucket (versioned, encrypted, DESTROY on delete for sample)
    - IAM role for Amazon S3 Files sync (assumed by elasticfilesystem.amazonaws.com)
    - Amazon S3 Files filesystem linked to the bucket
    - Mount targets in each isolated subnet
    - Access point scoped to /Lambda prefix with POSIX uid/gid 1000

    Exports: data_bucket, access_point, file_system
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc = None,
        mount_target_sg: ec2.ISecurityGroup = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── S3 Access Logging Bucket ──────────────────────────────────
        self.logs_bucket = s3.Bucket(
            self, "AccessLogsBucket",
            bucket_name=f"quota-agent-access-logs-{cdk.Aws.ACCOUNT_ID}-{cdk.Aws.REGION}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ExpireAccessLogs",
                    expiration=Duration.days(90),
                ),
            ],
        )

        # TLS enforcement for access logs bucket
        self.logs_bucket.add_to_resource_policy(iam.PolicyStatement(
            sid="DenyInsecureTransport",
            effect=iam.Effect.DENY,
            principals=[iam.AnyPrincipal()],
            actions=["s3:*"],
            resources=[
                self.logs_bucket.bucket_arn,
                self.logs_bucket.arn_for_objects("*"),
            ],
            conditions={
                "Bool": {"aws:SecureTransport": "false"},
            },
        ))

        # ── S3 Bucket ─────────────────────────────────────────────────
        self.data_bucket = s3.Bucket(
            self, "AgentDataBucket",
            bucket_name=f"quota-agent-data-{cdk.Aws.ACCOUNT_ID}-{cdk.Aws.REGION}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            event_bridge_enabled=True,  # Required for Amazon S3 Files sync
            server_access_logs_bucket=self.logs_bucket,
            server_access_logs_prefix="access-logs/",
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ExpireOldVersions",
                    noncurrent_version_expiration=Duration.days(90),
                ),
                s3.LifecycleRule(
                    id="ArchiveRunLogs",
                    prefix="Lambda/run-log/",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(30),
                        ),
                    ],
                ),
            ],
        )

        # ── TLS Enforcement ───────────────────────────────────────────
        # Deny any requests that do not use HTTPS (aws:SecureTransport)
        self.data_bucket.add_to_resource_policy(iam.PolicyStatement(
            sid="DenyInsecureTransport",
            effect=iam.Effect.DENY,
            principals=[iam.AnyPrincipal()],
            actions=["s3:*"],
            resources=[
                self.data_bucket.bucket_arn,
                self.data_bucket.arn_for_objects("*"),
            ],
            conditions={
                "Bool": {"aws:SecureTransport": "false"},
            },
        ))

        # ── Amazon S3 Files Sync Role ────────────────────────────────────────
        # Amazon S3 Files assumes this role to sync data between S3 and the filesystem
        self.s3files_role = iam.Role(
            self, "S3FilesSyncRole",
            assumed_by=iam.ServicePrincipal("elasticfilesystem.amazonaws.com"),
        )

        # S3 permissions for sync
        self.s3files_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:ListBucket*"],
            resources=[self.data_bucket.bucket_arn],
        ))
        self.s3files_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "s3:AbortMultipartUpload",
                "s3:DeleteObject",
                "s3:GetObject*",
                "s3:List*",
                "s3:PutObject*",
            ],
            resources=[self.data_bucket.arn_for_objects("*")],
        ))

        # EventBridge permissions for Amazon S3 Files sync rules
        self.s3files_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "events:DeleteRule",
                "events:DisableRule",
                "events:EnableRule",
                "events:PutRule",
                "events:PutTargets",
                "events:RemoveTargets",
            ],
            resources=[
                f"arn:{cdk.Aws.PARTITION}:events:*:*:rule/DO-NOT-DELETE-S3-Files*"
            ],
            conditions={
                "StringEquals": {
                    "events:ManagedBy": "elasticfilesystem.amazonaws.com"
                }
            },
        ))
        self.s3files_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "events:DescribeRule",
                "events:ListRuleNamesByTarget",
                "events:ListRules",
                "events:ListTargetsByRule",
            ],
            resources=[f"arn:{cdk.Aws.PARTITION}:events:*:*:rule/*"],
        ))

        # ── Amazon S3 Files Filesystem ───────────────────────────────────────
        self.file_system = s3files.CfnFileSystem(
            self, "AgentFileSystem",
            bucket=self.data_bucket.bucket_arn,
            role_arn=self.s3files_role.role_arn,
            accept_bucket_warning=True,
        )
        self.file_system.apply_removal_policy(RemovalPolicy.DESTROY)

        # ── Mount Targets ─────────────────────────────────────────────
        if vpc and mount_target_sg:
            for i, subnet in enumerate(vpc.isolated_subnets):
                mt = s3files.CfnMountTarget(
                    self, f"MountTarget{i}",
                    file_system_id=self.file_system.attr_file_system_id,
                    subnet_id=subnet.subnet_id,
                    security_groups=[mount_target_sg.security_group_id],
                )
                mt.add_dependency(self.file_system)

        # ── Access Point ──────────────────────────────────────────────
        # Scoped to /Lambda prefix, POSIX uid/gid 1000 (Lambda default)
        self.access_point = s3files.CfnAccessPoint(
            self, "AgentAccessPoint",
            file_system_id=self.file_system.attr_file_system_id,
            root_directory=s3files.CfnAccessPoint.RootDirectoryProperty(
                path="/Lambda",
                creation_permissions=s3files.CfnAccessPoint.CreationPermissionsProperty(
                    owner_uid="1000",
                    owner_gid="1000",
                    permissions="777",
                ),
            ),
            posix_user=s3files.CfnAccessPoint.PosixUserProperty(
                uid="1000",
                gid="1000",
            ),
        )
        self.access_point.add_dependency(self.file_system)

        # ── Outputs ───────────────────────────────────────────────────
        cdk.CfnOutput(self, "DataBucketName",
            value=self.data_bucket.bucket_name,
            description="S3 bucket name for agent data",
        )
        cdk.CfnOutput(self, "FileSystemId",
            value=self.file_system.attr_file_system_id,
            description="Amazon S3 Files filesystem ID",
        )
        cdk.CfnOutput(self, "AccessPointId",
            value=self.access_point.attr_access_point_id,
            description="Amazon S3 Files access point ID",
        )
