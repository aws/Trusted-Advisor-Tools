# Threat Model — AWS Quota Increase Support Agent

## System Overview

The AWS Quota Increase Support Agent is an autonomous, serverless agent that monitors AWS service quota utilization and requests increases proactively. It operates without human interaction on a 24-hour cycle.

**Architecture:**
- Lambda function (Python 3.11+) triggered by EventBridge Scheduler
- Amazon Bedrock LLM for reasoning (via IAM authentication)
- Amazon S3 Files mount for persistent state
- VPC with private isolated subnets (no internet egress)
- AWS CLI for Service Quotas, Support, and Trusted Advisor API calls

## Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│ AWS Account (Customer)                                           │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ VPC (Private Isolated Subnets)                              │ │
│  │                                                             │ │
│  │  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐  │ │
│  │  │   Lambda    │───▶│ S3 Files     │    │ VPC Endpoints│  │ │
│  │  │   (Agent)   │    │ Mount Target │    │ (Bedrock,    │  │ │
│  │  │             │───▶│              │    │  STS, Logs,  │  │ │
│  │  │ IAM Role    │    └──────────────┘    │  S3, SQ)     │  │ │
│  │  └─────────────┘                        └──────────────┘  │ │
│  │         │                                      │           │ │
│  └─────────│──────────────────────────────────────│───────────┘ │
│            │                                      │              │
│  ┌─────────▼──────────────────────────────────────▼───────────┐ │
│  │ AWS Services (via VPC Endpoints)                            │ │
│  │  • Amazon Bedrock (LLM inference)                           │ │
│  │  • Service Quotas (read/write)                              │ │
│  │  • S3 (bucket data)                                         │ │
│  │  • CloudWatch Logs                                          │ │
│  │  • Support API (business tier only)                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Control Plane                                               │ │
│  │  • EventBridge Scheduler (trigger)                          │ │
│  │  • CloudFormation/CDK (deployment)                          │ │
│  │  • IAM (access control)                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Threat Identification (STRIDE)

### 1. Spoofing

| Threat | Description | Likelihood | Impact | Mitigation |
|--------|-------------|-----------|--------|------------|
| T-S1: Compromised Lambda execution role | Attacker obtains temporary credentials from the Lambda role | Low | High | VPC isolation (no internet egress), short-lived credentials (1hr max), no external trigger surface |
| T-S2: Unauthorized scheduler invocation | Attacker triggers the Lambda outside normal schedule | Low | Low | Scheduler role scoped to specific Lambda ARN; no public invocation URL |
| T-S3: IAM role assumption by unauthorized entity | Another service/user assumes the Lambda role | Low | High | Trust policy restricts to `lambda.amazonaws.com` service principal only |

### 2. Tampering

| Threat | Description | Likelihood | Impact | Mitigation |
|--------|-------------|-----------|--------|------------|
| T-T1: Modification of agent memory (AGENTS.md) | Attacker modifies Amazon S3 Files to inject malicious instructions | Low | High | S3 versioning enabled; bucket access restricted to Lambda role + Amazon S3 Files sync role; access point scoped to /Lambda prefix |
| T-T2: Modification of skill file (SKILL.md) | Attacker modifies the agent's operational instructions | Low | Critical | Skill files deployed via CDK Lambda layer (immutable); S3 copy is seeded from known-good source |
| T-T3: Unauthorized quota modifications | Agent or attacker submits unwanted quota increase requests | Medium | Medium | IAM condition restricts to specific services; agent follows Autonomous Action Policy with documented thresholds |
| T-T4: S3 bucket data manipulation | Direct S3 API calls to modify agent state | Low | High | Bucket policy restricts access; KMS encryption; access logging enabled |

### 3. Repudiation

| Threat | Description | Likelihood | Impact | Mitigation |
|--------|-------------|-----------|--------|------------|
| T-R1: Untracked quota increase requests | Agent makes requests without audit trail | Low | Medium | CloudTrail captures all Service Quotas API calls; agent logs decisions to AGENTS.md; Amazon Bedrock invocation logging captures LLM reasoning |
| T-R2: Untracked file modifications | Changes to persistent state without attribution | Low | Low | S3 versioning + CloudTrail data events; S3 access logging to separate bucket |

### 4. Information Disclosure

| Threat | Description | Likelihood | Impact | Mitigation |
|--------|-------------|-----------|--------|------------|
| T-I1: Data exfiltration from Amazon S3 Files mount | Agent or attacker extracts account IDs, business context | Low | High | No internet egress; VPC endpoints only; Lambda reserved concurrency=1 |
| T-I2: LLM prompt/response data exposure | Amazon Bedrock invocation logs contain sensitive business context | Medium | Medium | CloudWatch Logs encrypted with KMS; access restricted to authorized roles |
| T-I3: NFS traffic interception | NFS traffic between Lambda and S3 Files mount targets | Very Low | Very Low | S3 Files mandates TLS encryption for all data in transit; traffic additionally confined to private isolated subnets; security group restricts NFS to Lambda SG only |
| T-I4: Environment variable exposure | Lambda env vars visible in console/API | Low | Low | Env vars encrypted with KMS; values are non-secret (mount path, model ID, account ID) |

### 5. Denial of Service

| Threat | Description | Likelihood | Impact | Mitigation |
|--------|-------------|-----------|--------|------------|
| T-D1: Agent execution timeout | LLM takes too long, Lambda hits 15-min timeout | Medium | Low | DLQ captures failures; CloudWatch alarm triggers; agent retries next cycle |
| T-D2: Amazon S3 Files mount unavailability | Mount targets unreachable | Low | High | Mount targets in 2 AZs; S3 data remains accessible via S3 API |
| T-D3: Amazon Bedrock API throttling | High-volume model invocations throttled | Low | Medium | Agent runs once per 24 hours; single concurrency prevents burst |
| T-D4: Service Quotas API throttling | Too many quota API calls | Low | Low | Agent optimizes calls via memory; 24-hour cadence limits total calls |

### 6. Elevation of Privilege

| Threat | Description | Likelihood | Impact | Mitigation |
|--------|-------------|-----------|--------|------------|
| T-E1: IAM policy misconfiguration | Lambda role grants more permissions than intended | Medium | Critical | IAM policies use specific actions (no wildcards on actions); resource scoping on Amazon Bedrock, S3; condition keys on Service Quotas |
| T-E2: Prompt injection causing privilege escalation | Malicious content in API responses causes agent to attempt unauthorized actions | Low | Low | IAM is the enforcement boundary — unauthorized actions fail regardless of LLM output; no user-facing input |
| T-E3: Shell command injection | Agent executes unintended commands via LocalShellBackend | Low | Medium | IAM limits what commands succeed; no package installation (no internet); fixed continuation prompt |
| T-E4: Cross-account access | Agent accesses resources in other accounts | Very Low | Critical | No cross-account role assumptions in IAM policy; VPC endpoints are account-scoped |

## Risk Assessment Matrix

| Risk Level | Threats | Action |
|-----------|---------|--------|
| **Critical** (Likelihood ≥ Medium, Impact = Critical) | T-E1 | ✅ Mitigated: Resource-scoped policies, condition keys, code review |
| **High** (Likelihood = Medium, Impact = High) | None identified | — |
| **Medium** | T-T3, T-I2, T-D1 | ✅ Mitigated: Condition keys, KMS encryption, DLQ + alarms |
| **Low** | All others | ✅ Accepted with existing controls |

## Security Controls Summary

### Preventive Controls
- IAM least-privilege policies with resource scoping and condition keys
- VPC isolation with no internet egress
- S3 Block Public Access
- KMS encryption at rest for all data stores
- TLS enforcement for S3 access (bucket policy)
- Security group restrictions (NFS limited to Lambda SG)
- Reserved concurrency = 1 (prevents parallel execution)

### Detective Controls
- CloudTrail for all API calls
- Amazon Bedrock model invocation logging (prompts + responses)
- S3 access logging
- CloudWatch alarms (failures, duration, DLQ)
- S3 versioning (tamper detection)

### Corrective Controls
- DLQ for failed invocations (investigation)
- CloudWatch alarms for operational response
- S3 versioning for rollback
- CDK re-deployment for infrastructure recovery
- KMS key disable for compromise response

## Assumptions

1. The AWS account is not already compromised
2. IAM credentials are properly managed by AWS Lambda service
3. VPC endpoint traffic is encrypted by AWS (TLS 1.2+)
4. AWS service-level security (physical, hypervisor) is maintained per AWS Shared Responsibility Model
5. CDK deployment happens from a trusted workstation with proper credentials
6. The deepagents SDK and langchain-aws libraries are not backdoored (see THIRD_PARTY_LICENSES.md for review status)

## Review Schedule

This threat model should be reviewed:
- When new AWS services are added to the solution
- When the agent's permissions or capabilities change
- When new threat intelligence relevant to LLM-based agents emerges
- At minimum annually as part of security review
