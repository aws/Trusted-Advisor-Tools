"""Bootstrap helper for the Quota Agent Lambda.

Copies skill files from the deployment package (Lambda layer) to the Amazon S3 Files
mount on first run, and creates required directories. Since the Lambda connects
as uid 1000 via the Amazon S3 Files access point, all files/dirs created here will be
owned by uid 1000 and remain writable on subsequent runs.
"""
import os
import shutil

BOOTSTRAP_AGENTS_MD = """# Agent Memory

## Identity
I am the AWS Quota Increase Support Agent for account {account_id}.

## Account Context
- Support plan: **Basic** (confirmed — do NOT re-run `aws support describe-severity-levels`)
- Region: us-east-1 (set automatically by Lambda runtime — AWS_DEFAULT_REGION is reserved)
- Output: json (set via AWS_DEFAULT_OUTPUT env var)

## Known CLI Commands

Use these exact, tested invocations. Do not rediscover.

```bash
# List all pending/recent quota change requests
aws service-quotas list-requested-service-quota-change-history

# Filter to pending only
aws service-quotas list-requested-service-quota-change-history \\
  --query "RequestedQuotas[?Status==\\`PENDING\\`]"

# Get current Lightsail Instances quota (code: L-4259AF9B)
aws service-quotas get-service-quota \\
  --service-code lightsail --quota-code L-4259AF9B

# Get current EC2 Running On-Demand Standard Instances quota (code: L-1216C47A)
aws service-quotas get-service-quota \\
  --service-code ec2 --quota-code L-1216C47A

# Check quota with --query (⚠️ fields nested under Quota.)
aws service-quotas get-service-quota \\
  --service-code lightsail --quota-code L-4259AF9B \\
  --query "Quota.{{QuotaName: QuotaName, Value: Value, Adjustable: Adjustable}}"

# List adjustable quotas for a service (scoped)
aws service-quotas list-service-quotas \\
  --service-code ec2 \\
  --query "Quotas[?Adjustable==\\`true\\`].[QuotaCode,QuotaName,Value]" \\
  --output table

# Find a service code by name
aws service-quotas list-services \\
  --query "Services[?contains(ServiceName, \\`SEARCH_TERM\\`)]"

# Submit a quota increase request
aws service-quotas request-service-quota-increase \\
  --service-code SERVICE_CODE --quota-code QUOTA_CODE --desired-value NEW_VALUE

# Check a specific request by ID
aws service-quotas get-requested-service-quota-change --request-id REQUEST_ID
```

## Known Quota Codes
- Lightsail Instances: `lightsail` / `L-4259AF9B`
- EC2 Running On-Demand Standard Instances: `ec2` / `L-1216C47A`

## Monitored Quota Summary
_Last updated: (not yet run)_

| Service | Quota | Code | Default | Applied | Health |
|---------|-------|------|---------|---------|--------|
| Lightsail | Instances | L-4259AF9B | 20 | — | — |
| EC2 | On-Demand Standard | L-1216C47A | 5 | — | — |

## Pending Quota Requests
None yet.

## Historical Quota Requests
None yet.

## Recommended Actions
None yet.

## Learnings

### Environment
- AWS CLI v1 is at `/opt/awscli/aws`. PATH is pre-configured — use `aws` directly.
- ALWAYS use AWS CLI via `execute` tool. Do NOT fall back to boto3/Python SDK.
- Region and output are defaulted — no need for `--region` or `--output` flags.
- `/mnt/agent/` is persistent EFS — files survive across runs.

### AWS CLI Response Shapes
- `get-service-quota`: fields under `Quota` — use `Quota.QuotaName`, `Quota.Value`, etc.
- `list-service-quotas`: fields under `Quotas[]`
- `list-requested-service-quota-change-history`: fields under `RequestedQuotas[]`
- `Created` / `LastUpdated` are Unix epoch floats.

### Support Plan Limitations
- Basic plan: `aws support` and `aws trustedadvisor` fail with SubscriptionRequiredException.
- Use only `aws service-quotas` commands for all quota monitoring.
"""

# Skill files are bundled in the layer at /opt/skill_files/
SKILL_FILES_SRC = "/opt/skill_files"


def bootstrap_mount(mount_path):
    """Ensure all required files and directories exist on the mount.

    Creates:
    - skills/aws-quota-increase-support/SKILL.md (from layer)
    - AGENTS.md (template if missing)
    - run-log/ directory
    - dossiers/ directory
    """
    # 1. Bootstrap SKILL.md from layer
    _copy_skill_files(mount_path)

    # 2. Bootstrap AGENTS.md
    _ensure_agents_md(mount_path)

    # 3. Create required directories
    for dirname in ("run-log", "dossiers"):
        dirpath = os.path.join(mount_path, dirname)
        os.makedirs(dirpath, exist_ok=True)


def _copy_skill_files(mount_path):
    """Copy skill files from layer to mount if not present."""
    if not os.path.isdir(SKILL_FILES_SRC):
        return
    for root, dirs, files in os.walk(SKILL_FILES_SRC):
        rel = os.path.relpath(root, SKILL_FILES_SRC)
        dest_dir = os.path.join(mount_path, rel)
        os.makedirs(dest_dir, exist_ok=True)
        for fname in files:
            dest_file = os.path.join(dest_dir, fname)
            if not os.path.isfile(dest_file):
                src_file = os.path.join(root, fname)
                shutil.copy2(src_file, dest_file)


def _ensure_agents_md(mount_path):
    """Create AGENTS.md from template if it doesn't exist."""
    agents_md = os.path.join(mount_path, "AGENTS.md")
    if not os.path.isfile(agents_md):
        account_id = os.environ.get("AWS_ACCOUNT_ID", "unknown")
        with open(agents_md, "w") as f:
            f.write(BOOTSTRAP_AGENTS_MD.format(account_id=account_id))
