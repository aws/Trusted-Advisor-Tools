# AWS Quota Increase Support Agent

A **serverless, autonomous agent** that acts as a persistent "quota butler" for an AWS customer account. It runs on a 24-hour cadence via Amazon EventBridge Scheduler, proactively monitoring service quota utilization, requesting increases before limits become blocking, and shepherding requests through to completion — all without waiting for the customer to ask.

## Architecture

```
EventBridge Scheduler (24h)
        │
        ▼
  Lambda Function (Python 3.11+, deepagents SDK)
        │
        ├── Amazon S3 Files Mount (/mnt/agent) ─── persistent memory & state
        ├── Service Quotas API ──────────── request/track increases
        ├── Trusted Advisor API ─────────── monitor limit utilization
        ├── AWS Support API ─────────────── manage support cases
        └── Amazon Bedrock ──────────────── LLM reasoning (IAM auth)
```

The agent uses the [deepagents](https://github.com/langchain-ai/deepagents/) SDK — an agent harness built with LangChain and LangGraph, equipped with a planning tool, filesystem backend, and the ability to spawn subagents — with `LocalShellBackend` and the AWS CLI as its primary tool. Persistent state (memory, run logs, dossiers) is stored via **Amazon S3 Files** mounted as a POSIX filesystem on the Lambda function. The Lambda runs inside a **VPC with private isolated subnets** and VPC endpoints (no NAT Gateway required).

| Property | Value |
|----------|-------|
| **Trigger** | EventBridge Scheduler, `rate(24 hours)` |
| **Runtime** | Python 3.11+ on Lambda |
| **Agent Framework** | deepagents SDK (`create_deep_agent()`) |
| **LLM Provider** | Amazon Bedrock (Claude via IAM auth) |
| **Persistent Storage** | Amazon S3 Files mounted at `/mnt/agent` |
| **Max Execution** | 15 minutes (Lambda max) |
| **Memory** | 2048 MB |
| **IaC** | AWS CDK (Python) |

## What It Does

1. **Monitors** — Checks Trusted Advisor for service limit warnings (Yellow ≥ 80%, Red = 100%)
2. **Identifies** — Prioritizes quotas approaching limits (Red first, then Yellow)
3. **Gathers Context** — Builds a use-case dossier with business justification before requesting
4. **Requests** — Submits quota increase requests via Service Quotas API
5. **Tracks** — Monitors open support cases for follow-up questions
6. **Responds** — Answers follow-ups using gathered context or escalates to the customer
7. **Verifies** — Confirms new quota values after approval
8. **Remembers** — Persists all state to Amazon S3 Files for the next invocation cycle

## Project Structure

```
AWSQuotaIncreaseSupport/
├── README.md                  # This file
├── LICENSE                    # MIT-0 License
├── SECURITY.md                # Service security guidelines
├── THREAT_MODEL.md            # STRIDE threat analysis
├── THIRD_PARTY_LICENSES.md    # Third-party license info
├── cdk/                       # CDK infrastructure
│   ├── app.py                 # CDK app entry point (stack wiring)
│   ├── deploy.sh              # Full deploy: venv → layers → CDK → seed S3
│   ├── destroy.sh             # Teardown all stacks
│   ├── requirements.txt       # CDK Python dependencies
│   ├── cdk.json               # CDK configuration
│   ├── stacks/
│   │   ├── network_stack.py   # VPC, security groups, VPC endpoints
│   │   ├── storage_stack.py   # S3 bucket, Amazon S3 Files filesystem, mount targets
│   │   ├── iam_stack.py       # Lambda role, Scheduler role (least-privilege)
│   │   ├── lambda_stack.py    # Lambda function, EventBridge scheduler, DLQ, alarms
│   │   └── bedrock_logging_stack.py  # Bedrock invocation logging
│   ├── layers/
│   │   ├── deepagents/        # Lambda layer: deepagents SDK + dependencies
│   │   │   ├── build.sh
│   │   │   └── requirements.txt
│   │   └── skill_assets/      # Skill files and bootstrap script
│   └── tests/
│       ├── test_lambda_handler.py
│       ├── test_lambda_stack.py
│       ├── test_iam_stack.py
│       ├── test_storage_stack.py
│       └── test_integration.py
```

## Prerequisites

- **AWS CLI v2** configured with appropriate credentials
- **Python 3.11+**
- **AWS CDK CLI** (`npm install -g aws-cdk`)
- **AWS Account** with Business or Enterprise Support plan (recommended for full functionality)
  - Basic/Developer plans can still submit quota requests via Service Quotas API but cannot access Trusted Advisor or Support case communications via CLI

## Quick Start

### Deploy

```bash
cd aws-quota-increase-support/cdk
bash deploy.sh
```

The deploy script handles everything:
1. Creates a Python virtual environment and installs CDK dependencies
2. Builds the deepagents Lambda layer
3. Deploys all four CDK stacks (Network → Storage → IAM → Lambda)
4. Seeds initial files to S3 (`SKILL.md`, `AGENTS.md`, directory placeholders)

### Run Tests

```bash
cd aws-quota-increase-support/cdk
source .venv/bin/activate
pytest tests/ -v
```

### Destroy

```bash
cd aws-quota-increase-support/cdk
bash destroy.sh
```

## CDK Stacks

The infrastructure is split into four stacks deployed in dependency order:

| Stack | Resources |
|-------|-----------|
| **QuotaAgentNetworkStack** | VPC with private isolated subnets, security groups, VPC endpoints (S3, Amazon Bedrock, Service Quotas, Support, Trusted Advisor, STS, CloudWatch) |
| **QuotaAgentStorageStack** | S3 general-purpose bucket, Amazon S3 Files filesystem, mount targets, access point |
| **QuotaAgentIAMStack** | Lambda execution role (least-privilege), EventBridge Scheduler role |
| **QuotaAgentLambdaStack** | Lambda function, deepagents layer, EventBridge Scheduler (24h), DLQ, CloudWatch alarms |

## Documentation

For security documentation, see:

- **[SECURITY.md](SECURITY.md)** — Service security guidelines, data classification, key management, AI security controls
- **[THREAT_MODEL.md](THREAT_MODEL.md)** — STRIDE threat analysis, risk assessment, and security controls

## Cost

This agent is designed for near-zero idle cost:

- **Lambda**: ~30 invocations/month at up to 15 min each = ~7.5 compute hours/month
- **Amazon S3 Files**: Storage for small markdown files (KB-range)
- **VPC Endpoints**: Interface endpoints have hourly charges; S3 gateway endpoint is free
- **No NAT Gateway**: Private subnets use VPC endpoints exclusively
- **Amazon Bedrock**: Pay-per-token for LLM inference during agent runs

## Security

This project follows security-by-design principles. For comprehensive security documentation, see:

- **[SECURITY.md](SECURITY.md)** — Service security guidelines, data classification, key management, AI security controls
- **[THREAT_MODEL.md](THREAT_MODEL.md)** — STRIDE threat analysis, risk assessment, and security controls

### Security Considerations

1. **Least-privilege IAM policies** — Lambda execution role uses service-specific actions with resource-scoped ARNs and condition keys (see `cdk/stacks/iam_stack.py`)
2. **VPC network isolation** — Private isolated subnets with no NAT Gateway; all AWS service access via VPC endpoints (see `cdk/stacks/network_stack.py`)
3. **Encryption at rest and in transit** — AWS-managed encryption at rest for S3, Lambda env vars, and CloudWatch Logs; TLS enforced via bucket policy (see `cdk/stacks/storage_stack.py`)
4. **AI security** — No external prompt injection surface; IAM as enforcement boundary; Amazon Bedrock invocation logging for audit (see `SECURITY.md`)
5. **Security monitoring** — CloudWatch alarms on failures, duration, and DLQ depth; CloudTrail for API audit trail

### Security Responsibilities

This solution follows the [AWS Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/):

**AWS Responsibilities (Security OF the Cloud):**
- Physical infrastructure security for Lambda, S3, VPC, and Amazon Bedrock services
- Service availability and patch management for managed services
- Network infrastructure and virtualization layer security

**Customer Responsibilities (Security IN the Cloud):**
- IAM policy configuration and least-privilege enforcement (see `cdk/stacks/iam_stack.py`)
- S3 bucket encryption and access controls (see `cdk/stacks/storage_stack.py`)
- VPC security group rules and network isolation (see `cdk/stacks/network_stack.py`)
- Lambda function code security and dependency management
- Amazon Bedrock model invocation logging and monitoring (see `cdk/stacks/bedrock_logging_stack.py`)
- CloudWatch alarm response and incident management

- Reviewing quota increase requests in AGENTS.md before approval

For detailed security guidance, see [SECURITY.md](SECURITY.md).

## License

This project is licensed under the MIT-0 License (MIT No Attribution). See the [LICENSE](LICENSE) file for details.

## Disclaimer

This sample code is provided "as is" without warranty of any kind, either express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. Use at your own risk.

This code is intended for demonstration and sample purposes. It should be reviewed, tested, and validated thoroughly before use in production environments. The authors and Amazon Web Services assume no responsibility or liability for any errors, omissions, or damages arising from the use of this software.

## Third-Party Libraries

This project uses open-source libraries. See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for license compatibility verification, security review status, and approval records.
