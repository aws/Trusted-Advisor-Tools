# Third-Party Licenses and Approvals

This document records the third-party open-source libraries used in this project, their licenses, and approval status.

## Runtime Dependencies (Lambda Layer)

| Library | Version | License | Purpose | Approval Status |
|---------|---------|---------|---------|-----------------|
| deepagents | 0.5.5 | MIT | Agent framework (planning, filesystem tools, shell execution, skills, memory) | ✅ Approved — MIT license, compatible with Apache 2.0 project license |
| langchain-aws | 1.4.5 | MIT | Amazon Bedrock LLM integration for LangChain | ✅ Approved — MIT license, compatible with Apache 2.0 project license |

## Transitive Dependencies

The above libraries bring in the following notable transitive dependencies:

| Library | License | Purpose |
|---------|---------|---------|
| langchain-core | MIT | Core LangChain abstractions |
| langgraph | MIT | Agent orchestration graph |
| pydantic | MIT | Data validation |
| boto3 / botocore | Apache 2.0 | AWS SDK (used by langchain-aws for Amazon Bedrock) |

## CDK Dependencies (Build-time Only)

| Library | Version | License | Purpose |
|---------|---------|---------|---------|
| aws-cdk-lib | >=2.252.0 | Apache 2.0 | AWS CDK infrastructure definitions |
| constructs | >=10.0.0 | Apache 2.0 | CDK construct base library |

## License Compatibility

All dependencies use MIT or Apache 2.0 licenses, which are fully compatible with this project's Apache 2.0 license for:
- ✅ Use in production AWS environments
- ✅ Distribution as part of AWS sample code
- ✅ Modification and redistribution

## Security Review

| Library | Security Review | Notes |
|---------|----------------|-------|
| deepagents | ✅ Reviewed | Open-source on GitHub; provides agent harness with shell execution capabilities. Security boundary is managed via IAM role scoping (see SECURITY.md). |
| langchain-aws | ✅ Reviewed | Official LangChain integration for AWS services. Authenticates via IAM — no API keys stored. |

## Maintenance and Support

| Library | Maintainer | Activity | Risk |
|---------|-----------|----------|------|
| deepagents | LangChain AI | Active development | Low — actively maintained OSS |
| langchain-aws | LangChain AI + AWS | Active development | Low — joint AWS/community maintenance |

## Approval Record

- **Reviewer:** Security review completed as part of Holmes Content Security Review
- **Date:** 2026-05-05
- **Decision:** Approved for use in AWS sample code distribution
- **Conditions:** Pin to specific versions (deepagents==0.5.5, langchain-aws==1.4.5); monitor for CVEs via dependabot/safety
- **Verification:**
  1. MIT license compatibility with Apache 2.0 project license — confirmed compatible
  2. No known security vulnerabilities in pinned versions — verified via `pip-audit`
  3. Libraries sourced from trusted repositories (LangChain AI official GitHub)
  4. No backdoor or supply chain risks identified — open-source with active community review
