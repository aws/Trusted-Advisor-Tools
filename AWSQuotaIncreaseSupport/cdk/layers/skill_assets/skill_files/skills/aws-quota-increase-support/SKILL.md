---
name: aws-quota-increase-support
description: Proactively manage AWS service quota increases for the customer's account. Monitor quota utilization via Service Quotas, request increases, track pending requests, and verify applied changes. This skill enables the agent to act as a persistent butler — continuously monitoring limits, pre-emptively requesting increases before quotas become blocking, and shepherding requests through to completion.
---

# AWS Service Quota Increase Support

Proactively monitor, request, and manage AWS service quota increases across the customer's account.

## Runtime Environment — Read First

| Property | Value |
|----------|-------|
| AWS CLI | v1 at `/opt/awscli/aws` — on PATH, callable as `aws` |
| Credentials | Lambda execution role (IAM) — no `--profile` needed |
| Default region | `us-east-1` **for AWS API calls** (Amazon Bedrock inference may route to other regions via inference profiles — unrelated to quota calls) |
| Default output | `json` (set via `AWS_DEFAULT_OUTPUT` env var) |
| Support plan | **Basic** — `aws support` and `aws trustedadvisor` commands will fail |
| Persistent storage | `/mnt/agent/` is an Amazon S3 Files mount (S3-backed filesystem) shared across Lambda invocations. Files written here survive between runs. |

**⚠️ MANDATORY: Use `aws` CLI via the `execute` tool for ALL AWS API calls.** Do NOT use boto3 or the Python SDK. If `aws` fails, the environment is broken — stop and report the error. Do not try workarounds.

Since region and output are defaulted, you do NOT need `--region us-east-1` or `--output json` flags on commands (unless targeting a different region).

### File Tool Behaviors (deepagents SDK)

| Tool | Behavior | Workaround |
|------|----------|------------|
| `write_file` | **Creates new files only** — refuses to overwrite existing files | Use `edit_file` to modify existing files |
| `edit_file` | Requires both `old_string` and `new_string` parameters, even for deletions | To delete content, pass the content to remove as `old_string` and `""` as `new_string` |
| `edit_file` | Matches `old_string` exactly (including whitespace) | Copy the exact text from the file when constructing `old_string` |

### AWS CLI Gotchas

| Issue | Correct Usage |
|-------|---------------|
| Listing pending quota change requests | `list-requested-service-quota-change-history` (NOT `list-requested-service-quota-changes`) |
| Service Quotas pagination | Use `--max-items` and `--starting-token` (NOT `--page-size`) |
| Large output from list-service-quotas | Always use `--query` to filter (see examples below) |
| `get-service-quota` response shape | Fields are nested under `Quota` — projections must use `Quota.QuotaName`, `Quota.Value`, `Quota.Adjustable`. Plain `{Value: Value}` returns null. |
| `list-service-quotas` response shape | Fields are nested under `Quotas[]` — use `Quotas[?...].[QuotaName,Value]` |
| `list-requested-service-quota-change-history` response shape | Fields are under `RequestedQuotas[]` |
| Request `Created` / `LastUpdated` fields | Unix epoch seconds (float). Convert with `date -d @<epoch>` or `python3 -c 'import datetime; ...'` when needed. |

## Support Plan: Basic — What Works and What Doesn't

This account has **Basic** support. This is permanent for this account.

### ✅ Available (use these)

All `aws service-quotas` commands work:
- `list-services` — discover service codes
- `list-service-quotas` — list quotas for a service
- `get-service-quota` — get current applied value
- `get-aws-default-service-quota` — get AWS default value
- `list-requested-service-quota-change-history` — list pending/past requests
- `request-service-quota-increase` — submit a new increase request
- `get-requested-service-quota-change` — check a specific request by ID

### ❌ Not Available (do NOT attempt)

These commands will fail with `SubscriptionRequiredException`. Do not waste turns re-discovering this:
- `aws support describe-severity-levels`
- `aws support describe-cases`
- `aws support add-communication-to-case`
- `aws trustedadvisor list-checks`
- Any other `aws support` or `aws trustedadvisor` command

If the customer needs Trusted Advisor checks or Support Case management via CLI, recommend upgrading to a Business Support plan.

## Operating Model

Act as a persistent quota butler. On each run:

1. **Read AGENTS.md and CUSTOMER_CONTEXT.md** — recall previous state, known commands, pending requests AND business context for decision-making
2. **Check pending requests** — have any been approved, denied, or need follow-up?
3. **Survey monitored quotas** — check current values vs defaults for quotas in `## Monitored Quota Summary`
4. **Identify quotas approaching limits** — flag any that hit alert thresholds
5. **Take action** — submit increases per the Autonomous Action Policy, or log recommendations
6. **Update AGENTS.md** — record findings, new commands, and state changes
7. **Before returning** — run the closing checklist (see below)

### Before Returning

- [ ] AGENTS.md `## Monitored Quota Summary` timestamp updated to current run
- [ ] Any new request IDs added to `## Historical Quota Requests`
- [ ] Any new `## Recommended Actions` logged for customer
- [ ] At least 60s of Lambda time remaining

### Prefer Memorized Commands

Check AGENTS.md for "Known CLI Commands" before constructing new commands. The exact, tested invocations are stored there to avoid rediscovery on every run.

## AI Disclosure Policy

This agent must clearly identify itself as an automated AI system in all outputs
that humans will read.

### AGENTS.md Identity

The `## Identity` section in AGENTS.md must state that this is an AI agent,
not a human operator. Example:

> **I am an automated AI agent** managing AWS service quotas for this account.
> I run on a schedule as a Lambda function. All actions I take are logged here.
> My decisions are guided by SKILL.md policy and CUSTOMER_CONTEXT.md business context.

### Recommended Actions

Every entry in AGENTS.md `## Recommended Actions` must be prefixed with
`[AI Agent]` so the customer/TAM knows it was generated by automation, not a person.

Example:
> `[AI Agent] Fargate On-Demand vCPU quota (L-3032A538) is at 85% utilization (544/640). Recommend increasing to 960 based on Q3 growth plan. Requires manual approval — exceeds 2× current value.`

### Quota Increase Requests

Quota increase requests submitted via the Service Quotas API are attributed to the
Lambda execution role. The resulting support cases will show the IAM role as the
requester. No additional disclosure is needed on the API call itself (there is no
free-text field), but the agent should log in AGENTS.md that the request was
submitted autonomously so the customer/TAM has an audit trail.

## AGENTS.md Schema

AGENTS.md must contain these sections (in order). Use `edit_file` with the exact section header as the anchor:

1. `## Identity` — **must include AI agent disclosure** (see AI Disclosure Policy)
2. `## Account Context`
3. `## Known CLI Commands`
4. `## Known Quota Codes`
5. `## Monitored Quota Summary` — update timestamp on every run
6. `## Pending Quota Requests` — update on every run
7. `## Historical Quota Requests` — append-only log of all request IDs
8. `## Recommended Actions` — things needing customer input
9. `## Learnings`

## Monitored Quotas

The canonical list of quotas to survey on every run lives in AGENTS.md under `## Monitored Quota Summary`. To add a new quota to monitoring:

1. Discover its code: `aws service-quotas list-services` → `list-service-quotas`
2. Add it to AGENTS.md with: service-code, quota-code, quota-name, default, threshold
3. Add the exact `get-service-quota` command to "Known CLI Commands"

### Alert Thresholds

Flag a quota for attention when:
- Applied value is within 20% of a known usage ceiling (if usage data available)
- A pending request has been `PENDING` or `CASE_OPENED` for > 7 days
- Applied value is at or below AWS default (never raised)

## Autonomous Action Policy

Submit a quota increase WITHOUT customer confirmation only when ALL are true:
- Quota is `Adjustable: true`
- No identical request is `PENDING` or recently `CASE_CLOSED`
- Requested value is ≤ 2× current applied value
- The quota's service has a matching workload in `CUSTOMER_CONTEXT.md` (agent can size the request appropriately)
- The quota is NOT listed under "Sensitive quotas" in CUSTOMER_CONTEXT.md `## Constraints and Preferences`

Otherwise, record the recommendation in AGENTS.md under `## Recommended Actions` and wait for customer direction.

## CLI Patterns with --query Filters

### Listing Quotas (scoped output — ALWAYS use --query)

```bash
# List adjustable quotas for a service (compact table view)
aws service-quotas list-service-quotas \
  --service-code ec2 \
  --query "Quotas[?Adjustable==\`true\`].[QuotaCode,QuotaName,Value]" \
  --output table

# Check if a quota's applied value differs from the AWS default
aws service-quotas list-service-quotas \
  --service-code ec2 \
  --query "Quotas[?Value!=DefaultValue].[QuotaCode,QuotaName,Value,DefaultValue]" \
  --output table

# List quotas for a service, max 10 results
aws service-quotas list-service-quotas \
  --service-code ec2 \
  --max-items 10
```

### Checking Specific Quotas

```bash
# Get current Lightsail Instances quota
aws service-quotas get-service-quota \
  --service-code lightsail \
  --quota-code L-4259AF9B

# Get current EC2 Running On-Demand Standard Instances quota
aws service-quotas get-service-quota \
  --service-code ec2 \
  --quota-code L-1216C47A

# Compare applied vs default
aws service-quotas get-aws-default-service-quota \
  --service-code lightsail \
  --quota-code L-4259AF9B
```

### Checking Request Status

```bash
# List ALL pending/recent quota change requests
aws service-quotas list-requested-service-quota-change-history

# Filter to pending only
aws service-quotas list-requested-service-quota-change-history \
  --query "RequestedQuotas[?Status==\`PENDING\`]"

# Filter to a specific service's pending requests
aws service-quotas list-requested-service-quota-change-history \
  --service-code ec2 \
  --query "RequestedQuotas[?Status==\`PENDING\`].[Id,QuotaName,DesiredValue,Status]" \
  --output table

# Check a specific request by ID
aws service-quotas get-requested-service-quota-change \
  --request-id REQUEST_ID
```

Status values: `PENDING` → `CASE_OPENED` → `APPROVED` | `DENIED` | `NOT_APPROVED` | `CASE_CLOSED`

### Interpreting Terminal Statuses

- **`APPROVED`** — increase granted; applied value should reflect DesiredValue
- **`DENIED`** / **`NOT_APPROVED`** — AWS refused; do NOT auto-resubmit
- **`CASE_CLOSED`** — **ambiguous**: could mean granted, denied, or closed without action. To disambiguate, compare `DesiredValue` against the current `get-service-quota` applied value:
  - applied ≥ desired → effectively approved
  - applied < desired → closed without increase; treat as denied
- Do NOT auto-resubmit a quota that AWS has denied/closed repeatedly without new business justification. Flag it for customer follow-up in `## Recommended Actions` instead.

### Submitting Quota Increase Requests

```bash
# Find a service code (projects ServiceCode and ServiceName for readability)
aws service-quotas list-services \
  --query "Services[?contains(ServiceName, \`SEARCH_TERM\`)].[ServiceCode,ServiceName]" \
  --output table

# Check if the quota is adjustable before requesting
# ⚠️ Response wraps fields under Quota — must prefix with Quota.
aws service-quotas get-service-quota \
  --service-code SERVICE_CODE \
  --quota-code QUOTA_CODE \
  --query "Quota.{Adjustable: Adjustable, CurrentValue: Value, QuotaName: QuotaName}"

# Submit the increase request
aws service-quotas request-service-quota-increase \
  --service-code SERVICE_CODE \
  --quota-code QUOTA_CODE \
  --desired-value NEW_VALUE
```

The response includes a request `Id` and `Status: PENDING`. A linked support case is created automatically (visible in the AWS Console even on Basic plan).

### Verifying Applied Quotas

After approval, confirm the new value:
```bash
# ⚠️ Response wraps fields under Quota — must prefix with Quota.
aws service-quotas get-service-quota \
  --service-code SERVICE_CODE \
  --quota-code QUOTA_CODE \
  --query "Quota.{QuotaName: QuotaName, AppliedValue: Value}"
```

### Resource-Level Quotas

Some quotas apply per-resource rather than per-account. These require the resource ARN when requesting increases.

#### Discovering Resource-Level Quotas

```bash
# List resource-level quotas for a service
aws service-quotas list-service-quotas \
  --service-code SERVICE_CODE \
  --quota-applied-at-level RESOURCE \
  --query "Quotas[].[QuotaCode,QuotaName,Value]" \
  --output table

# Account-level quotas (the default scope for most quotas)
aws service-quotas list-service-quotas \
  --service-code SERVICE_CODE \
  --quota-applied-at-level ACCOUNT \
  --query "Quotas[].[QuotaCode,QuotaName,Value]" \
  --output table
```

#### Requesting a Resource-Level Increase

```bash
# Specify the resource ARN via --context-id
aws service-quotas request-service-quota-increase \
  --service-code SERVICE_CODE \
  --quota-code QUOTA_CODE \
  --desired-value NEW_VALUE \
  --context-id RESOURCE_ARN
```

Key response fields:
- `QuotaRequestedAtLevel` — confirms `RESOURCE` scope
- `QuotaContext.ContextId` — the ARN the increase applies to

#### Identifying Resource-Level Quotas in Responses

When `get-service-quota` returns `QuotaAppliedAtLevel: RESOURCE`, check the
`QuotaContext.ContextId` field for the specific resource ARN the value applies to.

## Using Customer Context for Decisions

The agent cannot ask the customer questions at runtime. `CUSTOMER_CONTEXT.md` provides
pre-loaded business context that the agent uses for **decision-making** — not for
composing prose to attach to requests.

### What CUSTOMER_CONTEXT.md Is For

The `request-service-quota-increase` API takes only service-code, quota-code, and
desired-value. **There is no justification field.** The customer context helps the agent:

1. **Decide whether to act** — is this quota associated with a known workload?
   If the service doesn't appear in CUSTOMER_CONTEXT.md, the agent should log a
   recommendation rather than blindly requesting an increase.
2. **Size the request** — growth trajectory and constraints tell the agent what
   desired-value to target (e.g., 50% headroom above current usage, or a specific
   number from the growth plan).
3. **Respect sensitive quotas** — some quotas are flagged as "never auto-increase"
   in CUSTOMER_CONTEXT.md `## Constraints and Preferences`.
4. **Write useful recommendations** — when the agent logs to AGENTS.md
   `## Recommended Actions`, it can include relevant context (workload name,
   growth trajectory, why the increase matters) so the customer/TAM can act on it.

### Decision Flow

When a quota approaches its threshold:

1. **Match the service** — find the quota's service in CUSTOMER_CONTEXT.md workload descriptions
2. **Check constraints** — is this a sensitive quota? Does the desired value exceed 2× current?
3. **Size the value** — use growth trajectory and preferred headroom from CUSTOMER_CONTEXT.md
4. **Act or recommend:**
   - All Autonomous Action Policy conditions met → submit the increase (just the API call — no extra prose)
   - Any condition not met → log to `## Recommended Actions` with context for the customer

### When Context Is Missing

If the quota's service doesn't appear in CUSTOMER_CONTEXT.md:

1. Do NOT submit an autonomous increase for an unknown workload
2. Log to AGENTS.md → `## Recommended Actions`:
   - Which quota is approaching its limit and current utilization
   - That no matching workload was found in CUSTOMER_CONTEXT.md
   - Suggest the customer/TAM add workload details for this service
3. The agent can act on the next run after context is updated

## End-to-End Workflow Playbook

### Generic Quota Increase Lifecycle

```bash
# 1. Find the service code
aws service-quotas list-services \
  --query "Services[?contains(ServiceName, 'SERVICE_NAME')].[ServiceCode,ServiceName]" \
  --output table

# 2. Find the quota code
aws service-quotas list-service-quotas \
  --service-code SERVICE_CODE \
  --query "Quotas[?contains(QuotaName, 'QUOTA_NAME')].[QuotaCode,QuotaName,Value,Adjustable]" \
  --output table

# 3. Check current value and adjustability
aws service-quotas get-service-quota \
  --service-code SERVICE_CODE \
  --quota-code QUOTA_CODE \
  --query "Quota.{Name: QuotaName, Value: Value, Adjustable: Adjustable}"

# 4. Consult CUSTOMER_CONTEXT.md to size the desired value (see Using Customer Context for Decisions)

# 5. Submit increase
aws service-quotas request-service-quota-increase \
  --service-code SERVICE_CODE \
  --quota-code QUOTA_CODE \
  --desired-value NEW_VALUE

# 6. Record request ID in AGENTS.md, then track
aws service-quotas get-requested-service-quota-change \
  --request-id REQUEST_ID

# 7. After approval, verify the new value
aws service-quotas get-service-quota \
  --service-code SERVICE_CODE \
  --quota-code QUOTA_CODE \
  --query "Quota.{Name: QuotaName, AppliedValue: Value}"
```

### Check All Pending Requests

```bash
# Single command to see all pending/case-opened requests across all services
aws service-quotas list-requested-service-quota-change-history \
  --query "RequestedQuotas[?Status=='PENDING' || Status=='CASE_OPENED'].[Id,ServiceCode,QuotaName,DesiredValue,Status]" \
  --output table
```

### Post-Submission Notes

- A support case is created automatically for each request
- The case may generate follow-up questions visible in the AWS Console
- Since this account has Basic support, the agent cannot see or respond to case communications
- Log in AGENTS.md → `## Recommended Actions` that the customer should check the
  AWS Console for any follow-up prompts on their quota increase cases
- Allow time for propagation — after approval, `get-service-quota` may take minutes
  to hours to reflect the new value

## Best Practices

- **Keep analysis text brief** — reasoning is for tool calls, not prose. Minimize text output between tool invocations.
- **Use --query to scope output** — never dump full `list-service-quotas` responses into context
- **Check adjustability first** — not all quotas can be increased (`Adjustable: false`)
- **Request increases one at a time** — one quota per request for proper tracking
- **Quotas are regional** — the default region is us-east-1; specify `--region` for other regions
- **Prefer memorized commands** — don't rediscover CLI syntax; use commands from AGENTS.md
- **Allow time for propagation** — after a quota increase is approved, `get-service-quota` may take minutes to hours to reflect the new value. If the applied value hasn't changed yet, wait and re-check on the next run rather than reporting a failure.

## Appendix: Business/Enterprise Support Plans Only

The following features require Business or Enterprise support. They are documented here for reference if the account is upgraded.

### Trusted Advisor Service Limit Checks

```bash
# Requires Business+ support plan
aws trustedadvisor list-checks --pillar service_limits --language en

# Get results for a specific check (must target us-east-1)
aws support describe-trusted-advisor-check-result \
  --check-id CHECK_ID --language en --region us-east-1

# Filter to flagged resources only
aws support describe-trusted-advisor-check-result \
  --check-id CHECK_ID --language en --region us-east-1 \
  --query "result.flaggedResources[?status=='warning' || status=='error']"
```

### Support Case Management

```bash
# Requires Business+ support plan
aws support describe-cases --language en
aws support describe-communications --case-id CASE_ID
aws support add-communication-to-case --case-id CASE_ID --communication-body "RESPONSE"
```

## Security Responsibilities

This agent operates under the AWS Shared Responsibility Model:

**AWS Responsibilities:**
- Service Quotas API availability and infrastructure security
- Lambda execution environment isolation and patching
- Amazon S3 Files infrastructure security and data durability
- Amazon Bedrock model hosting and inference infrastructure
- VPC endpoint availability and TLS termination

**Customer Responsibilities:**
- IAM role policy configuration (least-privilege for Service Quotas, S3, Amazon Bedrock)
- Monitoring agent actions via CloudWatch Logs and CloudTrail
- Reviewing quota increase requests in AGENTS.md before approval
- Rotating Amazon Bedrock model access if compromised
- Auditing Amazon S3 Files mount access and file modifications
- Responding to CloudWatch alarms (failures, duration, DLQ)

**Security Controls in Effect:**
- All AWS API calls are logged to CloudTrail and auditable
- Amazon Bedrock model invocation logging captures all LLM prompts/responses
- Lambda runs in VPC with no internet egress (VPC endpoints only)
- Amazon S3 Files access point restricts filesystem to /Lambda prefix
- IAM policy restricts quota increase requests to approved services only
- Environment variables encrypted with customer-managed KMS key
- S3 bucket data encrypted with KMS and access logged
