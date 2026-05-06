# Security Documentation

This document provides comprehensive security guidelines, data classification, key management strategy, and AI security controls for the AWS Quota Increase Support Agent.

## Table of Contents

- [AWS Service Security Guidelines](#aws-service-security-guidelines)
- [Data Classification and Handling](#data-classification-and-handling)
- [Key Management Strategy](#key-management-strategy)
- [AI Security Controls](#ai-security-controls)
- [Compensating Controls](#compensating-controls)

---

## AWS Service Security Guidelines

Security guidelines for each AWS service used by this solution:

### AWS Lambda

| Guideline | Implementation | Reference |
|-----------|---------------|-----------|
| Use least-privilege execution roles | Custom inline policy with service-specific actions only | `cdk/stacks/iam_stack.py` |
| Enable VPC isolation | Lambda deployed in private isolated subnets with no internet egress | `cdk/stacks/network_stack.py` |
| Encrypt environment variables with AWS KMS | AWS-managed encryption (default Lambda behavior) | `cdk/stacks/lambda_stack.py` |
| Set reserved concurrency | `reserved_concurrent_executions=1` prevents parallel execution | `cdk/stacks/lambda_stack.py` |
| Monitor failures | CloudWatch alarms on errors, duration, and DLQ depth | `cdk/stacks/lambda_stack.py` |

### Amazon S3

| Guideline | Implementation | Reference |
|-----------|---------------|-----------|
| Enable encryption at rest with AWS KMS | AWS-managed SSE-S3 encryption | `cdk/stacks/storage_stack.py` |
| Block all public access | `block_public_access=BlockPublicAccess.BLOCK_ALL` | `cdk/stacks/storage_stack.py` |
| Enforce HTTPS-only access | Bucket policy with `aws:SecureTransport` condition | `cdk/stacks/storage_stack.py` |
| Enable versioning | `versioned=True` for data protection | `cdk/stacks/storage_stack.py` |
| Enable access logging | Server access logs to dedicated logging bucket | `cdk/stacks/storage_stack.py` |
| Configure lifecycle rules | Old versions expire after 90 days; run logs archived to Glacier | `cdk/stacks/storage_stack.py` |

### Amazon S3 Files (aws_s3files)

| Guideline | Implementation | Reference |
|-----------|---------------|-----------|
| Scope access points | Access point restricted to `/Lambda` prefix with POSIX uid/gid 1000 | `cdk/stacks/storage_stack.py` |
| Restrict mount target access | Security group limits NFS (port 2049) to Lambda SG only | `cdk/stacks/network_stack.py` |
| Use VPC isolation | Mount targets in private isolated subnets | `cdk/stacks/storage_stack.py` |
| Document NFS encryption limitation | NFS traffic within VPC is unencrypted; VPC isolation is compensating control | This document |

### AWS IAM

| Guideline | Implementation | Reference |
|-----------|---------------|-----------|
| Follow least-privilege principle | Service-specific policies with scoped resources | `cdk/stacks/iam_stack.py` |
| Scope Amazon Bedrock permissions to specific models | Resource ARN limited to the configured model | `cdk/stacks/iam_stack.py` |
| Use service-specific condition keys | Service Quotas write limited to known services | `cdk/stacks/iam_stack.py` |
| Separate roles per function | Distinct roles for Lambda, Scheduler, and Amazon S3 Files sync | `cdk/stacks/iam_stack.py` |

### Amazon Bedrock

| Guideline | Implementation | Reference |
|-----------|---------------|-----------|
| Use IAM authentication (no API keys) | Lambda role assumes Amazon Bedrock permissions via IAM | `cdk/stacks/iam_stack.py` |
| Enable model invocation logging | CloudWatch Logs with AWS KMS encryption (enabled by default) | `cdk/stacks/bedrock_logging_stack.py` |
| Scope to specific model ARNs | InvokeModel restricted to configured model ID | `cdk/stacks/iam_stack.py` |
| Use VPC endpoints | Amazon Bedrock Runtime VPC endpoint (no internet egress) | `cdk/stacks/network_stack.py` |

### Amazon VPC

| Guideline | Implementation | Reference |
|-----------|---------------|-----------|
| Use private isolated subnets (no NAT) | `PRIVATE_ISOLATED` subnet type with no internet path | `cdk/stacks/network_stack.py` |
| Restrict security group rules | Lambda SG: outbound only; Mount SG: NFS from Lambda SG only | `cdk/stacks/network_stack.py` |
| Use VPC endpoints for AWS services | Gateway (S3) + Interface (Amazon Bedrock, STS, Logs, ServiceQuotas) endpoints | `cdk/stacks/network_stack.py` |
| Enable private DNS on endpoints | `private_dns_enabled=True` for transparent access | `cdk/stacks/network_stack.py` |

### Amazon EventBridge Scheduler

| Guideline | Implementation | Reference |
|-----------|---------------|-----------|
| Use dedicated scheduler role | Separate IAM role with only `lambda:InvokeFunction` on target | `cdk/stacks/iam_stack.py` |
| Configure DLQ for failures | SQS DLQ with 14-day retention for failed invocations | `cdk/stacks/lambda_stack.py` |
| Limit retry attempts | Maximum 2 retries with 1-hour event age | `cdk/stacks/lambda_stack.py` |

### Amazon SQS (DLQ)

| Guideline | Implementation | Reference |
|-----------|---------------|-----------|
| Use server-side encryption | SQS managed encryption (default) | `cdk/stacks/lambda_stack.py` |
| Set retention policy | 14-day message retention for investigation | `cdk/stacks/lambda_stack.py` |
| Monitor queue depth | CloudWatch alarm on messages visible | `cdk/stacks/lambda_stack.py` |

### Amazon CloudWatch

| Guideline | Implementation | Reference |
|-----------|---------------|-----------|
| Encrypt log groups with AWS KMS | Customer-managed AWS KMS key for Amazon Bedrock logs | `cdk/stacks/bedrock_logging_stack.py` |
| Set log retention policies | 1-month retention for invocation logs | `cdk/stacks/bedrock_logging_stack.py` |
| Configure actionable alarms | Failure, duration, and DLQ alarms | `cdk/stacks/lambda_stack.py` |

### AWS Service Quotas

| Guideline | Implementation | Reference |
|-----------|---------------|-----------|
| Limit write actions to known services | Condition key restricts `RequestServiceQuotaIncrease` to monitored services | `cdk/stacks/iam_stack.py` |
| Separate read and write permissions | Read (List/Get) and Write (Request) in separate policy statements | `cdk/stacks/iam_stack.py` |

---

## Data Classification and Handling

### Data Types and Sensitivity

| Data Type | Classification | Examples | Retention |
|-----------|---------------|----------|-----------|
| Quota values | Internal | Current/applied quota numbers | Indefinite (in AGENTS.md) |
| AWS Account IDs | Confidential | 12-digit account identifiers | Indefinite (in config) |
| Business context | Confidential | Growth projections, service usage patterns | Indefinite (in CUSTOMER_CONTEXT.md) |
| Agent memory | Internal | Run summaries, decision history | Indefinite (in AGENTS.md) |
| Run logs | Internal | Full agent execution transcripts | 30 days active, then Glacier |
| LLM prompts/responses | Confidential | Full request/response payloads | 1 month (CloudWatch Logs) |
| Support case content | Confidential | Case communications, justifications | Duration of case lifecycle |

### Handling Procedures

| Classification | Encryption at Rest | Encryption in Transit | Access Control | Logging |
|---------------|-------------------|----------------------|----------------|---------|
| **Confidential** | AWS-managed encryption | TLS 1.2+ (enforced) | IAM role-based, least-privilege | CloudTrail + S3 access logs |
| **Internal** | AWS-managed encryption | TLS 1.2+ (enforced) | IAM role-based | CloudTrail |

### Data Lifecycle

1. **Creation:** Data generated during Lambda execution (agent runs, API responses)
2. **Storage:** Persisted to S3 via Amazon S3 Files mount (KMS-encrypted at rest)
3. **Transmission:** All API calls via VPC endpoints (TLS 1.2+); NFS within private VPC
4. **Retention:** Governed by S3 lifecycle rules (90-day version expiration, 30-day Glacier transition for logs)
5. **Deletion:** `RemovalPolicy.DESTROY` on stack teardown; S3 `auto_delete_objects=True`

---

## Key Management Strategy

This solution uses **AWS-managed encryption keys** for all data at rest. This is the recommended approach for sample/demonstration code as it provides strong encryption with zero operational overhead.

### Encryption Implementation

| Resource | Encryption Type | Details |
|----------|----------------|---------|
| S3 Data Bucket | SSE-S3 (AWS-managed) | Amazon S3 manages keys, rotation, and access transparently |
| Lambda Environment Variables | AWS-managed | Lambda service encrypts env vars at rest by default |
| CloudWatch Logs | AWS-managed | CloudWatch Logs service encrypts log data at rest by default |
| SQS DLQ | AWS-managed | SQS encrypts messages at rest by default |

### Why AWS-Managed Keys

- **Zero operational overhead:** No key rotation, access policies, or lifecycle management required
- **Automatic rotation:** AWS rotates keys transparently without customer intervention
- **No dependency cycles:** Eliminates cross-stack CDK references that customer-managed keys introduce
- **Cost:** No additional KMS charges for AWS-managed keys
- **Security:** Data is encrypted at rest with AES-256; AWS manages the full key lifecycle

### Upgrading to Customer-Managed Keys

If your security policy requires customer-managed AWS KMS keys (CMKs), you can upgrade by:
1. Creating KMS keys in the appropriate stacks
2. Setting `encryption=s3.BucketEncryption.KMS` with a custom key for S3
3. Adding `encryption_key=` parameter to CloudWatch Log Groups
4. Adding `environment_encryption=` parameter to Lambda functions

Note: Customer-managed keys add operational responsibilities including key rotation monitoring, access policy management, and disaster recovery planning.

---

## AI Security Controls

### Threat Vectors for LLM-based Agents

| Threat | Risk Level | Mitigation |
|--------|-----------|------------|
| Prompt injection via memory files | Low | No external user input; fixed continuation prompt; memory files written only by the agent itself |
| Prompt injection via AWS API responses | Low | API responses are structured JSON; no user-controlled free text in quota/support responses |
| Model hallucination (incorrect AWS actions) | Medium | IAM policy limits blast radius; agent skill file provides explicit instructions |
| Unauthorized API calls | Low | IAM role restricts available actions; no EC2/network modification permissions |
| Data exfiltration | Low | No internet egress; VPC endpoints only; Amazon S3 Files access scoped to /Lambda prefix |

### Implemented Controls

1. **No external prompt injection surface:** The Lambda is triggered by EventBridge Scheduler with a fixed continuation prompt. There is no HTTP endpoint, API Gateway, or user-facing interface that could inject malicious prompts.

2. **IAM as security boundary:** Even if the LLM generates unexpected commands, the Lambda execution role limits what succeeds. The role cannot: terminate instances, modify VPCs, access other accounts, create IAM users, or escalate privileges.

3. **No internet egress:** The Lambda function communicates exclusively through VPC endpoints. It cannot exfiltrate data to external endpoints.

4. **Amazon Bedrock model invocation logging:** All LLM interactions (prompts and responses) are logged to CloudWatch Logs with AWS KMS encryption, enabling post-hoc security analysis and incident investigation.

5. **Single concurrency:** `reserved_concurrent_executions=1` prevents parallel agent runs that could cause race conditions in state management.

6. **Shell execution via LocalShellBackend:** The agent executes commands via `LocalShellBackend` with `inherit_env=True`. This is intentional — the agent needs AWS CLI access. The security boundary is the IAM role, not the shell.

### Future Enhancements (Recommended)

- **Amazon Bedrock Guardrails:** Configure content filters and denied topic policies to add defense-in-depth. Associate guardrail with the model via `guardrailIdentifier` and `guardrailVersion` parameters.
- **Output validation:** Add post-processing to validate agent responses before returning from Lambda handler.
- **Rate limiting:** CloudWatch alarms already monitor invocation patterns; consider adding throttling for quota increase requests.

---

## Compensating Controls

### exec() Usage (Bandit B102)

**Location:** `cdk/stacks/lambda_stack.py`, line 54

**Context:** The `exec()` call executes the `LAMBDA_HANDLER_CODE` constant to define the Lambda handler function. This is a CDK pattern for inline Lambda code that exceeds the complexity of a simple one-liner.

**Why exec() is used:** AWS CDK's `Code.from_inline()` requires the handler code as a string. The `LAMBDA_HANDLER_CODE` constant is defined as a multi-line string in the same file. At CDK synthesis time, `exec()` is used in tests to validate the handler code can parse correctly.

**Compensating controls:**
1. **Code is a constant, not user input:** `LAMBDA_HANDLER_CODE` is a hardcoded string literal defined in the same source file — there is no user-controlled input path to `exec()`.
2. **Build-time only:** The `exec()` runs during CDK synthesis/testing, not at Lambda runtime. The Lambda runtime receives the code string via CloudFormation.
3. **Code review:** The handler code is visible and reviewable as a string constant in the same file.
4. **Static analysis:** The `# noqa: S102` comment acknowledges the Bandit finding with documented justification.
5. **Alternative considered:** Extracting to a separate .py file was rejected because the handler must stay under 4096 bytes for `Code.from_inline()` and co-locating it aids readability.

### NFS Traffic Encryption (Amazon S3 Files) — Accepted Risk

> **⚠️ SECURITY ADVISORY:** NFS traffic between Lambda and Amazon S3 Files mount targets is
> NOT encrypted in transit. This solution should only be deployed in environments where
> VPC network isolation is sufficient for the data sensitivity level being handled.

**Context:** This solution uses direct NFS mounts to Amazon S3 Files mount targets without the Amazon S3 Files mount helper. The mount helper provides TLS 1.2 encryption for NFS traffic, but is not compatible with Lambda's `FileSystem.from_s3_files_access_point()` CDK construct which uses kernel NFS mounts. NFS traffic between Lambda and mount targets (port 2049) is therefore not encrypted in transit.

**Risk Classification:** Known security gap — does not meet encryption-in-transit requirements.

**Formal Risk Acceptance:**
- **Risk:** Unencrypted NFS traffic within VPC private isolated subnets
- **Data exposed:** Agent memory files (AGENTS.md), skill files, run logs — classified as Internal/Confidential
- **Likelihood of exploitation:** Very Low (requires compromise of AWS VPC infrastructure)
- **Impact if exploited:** Medium (quota information and account IDs exposed)
- **Decision:** ACCEPTED with compensating controls — VPC isolation provides sufficient protection for this data classification
- **Review date:** To be reviewed if data classification changes or if Lambda adds mount helper support
- **Accepted by:** [Security reviewer name and date]

**Compensating controls:**
1. **VPC isolation:** NFS traffic only traverses private isolated subnets with no internet connectivity
2. **Security group restriction:** Mount target SG only accepts NFS from the Lambda security group
3. **No cross-AZ traffic sniffing:** AWS VPC infrastructure provides network isolation between tenants
4. **Data at rest is encrypted:** The underlying S3 bucket uses AWS KMS encryption; only the NFS transport layer is unencrypted
5. **Threat model assessment:** For this use case (small markdown files with quota information), VPC isolation provides sufficient protection

**Remediation path:** If encryption in transit becomes required:
1. **Preferred:** Investigate using the Amazon S3 Files mount helper in Lambda's bootstrap script if Lambda supports custom mount commands, which would enable TLS encryption without changing the storage backend.
2. **Alternative:** Migrate from Amazon S3 Files to Amazon EFS with `transit_encryption=efs.TransitEncryption.ENABLED`. This adds TLS 1.2 for NFS connections but requires EFS-compatible configuration changes and loses S3-native data access.
