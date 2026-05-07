"""Network stack for the AWS Quota Increase Support Agent.

Creates a VPC with private isolated subnets (no NAT Gateway) and VPC
endpoints so the Lambda function can reach AWS services from inside the VPC.

Accepts a ``support_tier`` parameter ("basic" or "business") to control
whether Support and Trusted Advisor VPC endpoints are created. Each
interface endpoint costs ~$14.40/month per AZ — skipping them on basic
saves ~$29/month.

Security Responsibilities (AWS Shared Responsibility Model):
    AWS secures the physical network infrastructure, virtualization layer,
    and VPC service availability.

    Customers are responsible for:
    (1) Configuring security group rules — implemented: Lambda SG allows
        outbound only; mount target SG restricts NFS (port 2049) ingress
        to the Lambda security group exclusively.
    (2) Subnet isolation strategy — implemented: PRIVATE_ISOLATED subnets
        with no NAT Gateway, eliminating all internet egress paths.
    (3) VPC endpoint policies — default (full access) used; restrict if
        required by organizational policy.
    (4) Network traffic monitoring — recommend enabling VPC Flow Logs for
        audit and anomaly detection (not included in sample to minimize cost).

    Amazon S3 Files (aws_s3files CDK module) provides S3-backed file system
    access using NFS mount targets within the VPC. "Amazon S3 Files" is the
    official AWS service name (announced April 2026, CDK module aws-cdk-lib/aws-s3files).
"""
import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
)
from constructs import Construct


class QuotaAgentNetworkStack(cdk.Stack):
    """VPC, subnets, security groups, and VPC endpoints.

    Creates:
    - VPC with private isolated subnets in 2 AZs (no NAT — cost zero)
    - Security group for Amazon S3 Files mount targets (NFS port 2049)
    - Security group for Lambda function
    - VPC endpoints for: S3 (gateway), Amazon Bedrock, STS, CloudWatch Logs,
      Service Quotas, and conditionally Support + TrustedAdvisor

    Exports: vpc, lambda_sg, mount_target_sg
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        support_tier: str = "basic",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC with only ISOLATED subnets — no NAT Gateway ($0/month)
        self.vpc = ec2.Vpc(
            self, "AgentVpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        # Security group for Lambda
        self.lambda_sg = ec2.SecurityGroup(
            self, "LambdaSG",
            vpc=self.vpc,
            description="Security group for QuotaAgent Lambda",
            allow_all_outbound=True,
        )

        # Security group for Amazon S3 Files mount targets
        self.mount_target_sg = ec2.SecurityGroup(
            self, "MountTargetSG",
            vpc=self.vpc,
            description="Security group for Amazon S3 Files mount targets",
        )

        # Allow NFS (port 2049) from Lambda SG to mount target SG
        self.mount_target_sg.add_ingress_rule(
            peer=self.lambda_sg,
            connection=ec2.Port.tcp(2049),
            description="NFS from Lambda",
        )

        # ── VPC Endpoints ─────────────────────────────────────────────
        # S3 Gateway endpoint (free, needed for Amazon S3 Files data path)
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        # Interface endpoints for AWS services the agent calls.
        # Each costs ~$0.01/hr/AZ = ~$14.40/month for 2 AZs.
        interface_services = {
            "Bedrock": ec2.InterfaceVpcEndpointAwsService("bedrock-runtime"),
            "STS": ec2.InterfaceVpcEndpointAwsService.STS,
            "Logs": ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            "ServiceQuotas": ec2.InterfaceVpcEndpointAwsService("servicequotas"),
        }

        # Business/Enterprise support: add Support + TrustedAdvisor endpoints
        if support_tier == "business":
            interface_services["Support"] = ec2.InterfaceVpcEndpointAwsService(
                "support"
            )
            interface_services["TrustedAdvisor"] = (
                ec2.InterfaceVpcEndpointAwsService("trustedadvisor")
            )

        for name, service in interface_services.items():
            self.vpc.add_interface_endpoint(
                f"{name}Endpoint",
                service=service,
                private_dns_enabled=True,
            )
