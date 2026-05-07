#!/bin/bash
set -euo pipefail

# ==============================================================================
# AWS Quota Increase Support Agent — Deploy Script
# ==============================================================================
# Phase 1: Python environment + CDK dependencies
# Phase 2: Build Lambda layers (deepagents SDK)
# Phase 3: CDK deploy all stacks
#
# NOTE: SKILL.md and AGENTS.md are NOT seeded via S3 API. The Lambda handler
# bootstraps them from its deployment package (skill_assets layer) on first run.
# This ensures files are created as uid 1000 via the Amazon S3 Files access point,
# avoiding POSIX permission issues with root-owned objects.
#
# OPTIONS:
#   --support-tier TIER  Set support plan tier: "basic" (default) or "business".
#                        Controls VPC endpoints and IAM policies.
#                        basic:    Skip Support + TrustedAdvisor (saves ~$29/month)
#                        business: Include Support + TrustedAdvisor endpoints + IAM
#   --bedrock-logging    Enable Bedrock model invocation logging to CloudWatch.
#                        Logs full request/response data for all Amazon Bedrock API calls.
#                        Disabled by default. Opt-in for debugging/auditing.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Initialize pyenv if available (ensures we use the correct Python version)
if command -v pyenv &>/dev/null; then
    eval "$(pyenv init -)"
elif [ -d "$HOME/.pyenv" ]; then
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
fi

# Help text
show_help() {
    cat <<'EOF'
Usage: deploy.sh [OPTIONS]

Deploy the AWS Quota Increase Support Agent via CDK.

Phases:
  1    Python virtual environment + CDK dependencies
  1.5  CUSTOMER_CONTEXT.md review prompt (interactive)
  2    Build Lambda layers (deepagents SDK)
  3    CDK deploy all stacks

Options:
  --support-tier TIER   Set support plan tier (default: basic)
                          basic    — Skip Support + TrustedAdvisor VPC endpoints
                                     and IAM policies (saves ~$29/month)
                          business — Include Support + TrustedAdvisor endpoints + IAM

  --bedrock-logging     Enable Bedrock model invocation logging to CloudWatch.
                        Logs full request/response data for all Amazon Bedrock API calls.
                        Disabled by default.

  --skip-context-check  Skip the interactive CUSTOMER_CONTEXT.md review prompt.
                        Useful for CI/CD pipelines.

  -h, --help            Show this help message and exit.

Examples:
  ./deploy.sh                                  # Basic tier, no logging
  ./deploy.sh --support-tier business          # Business tier
  ./deploy.sh --bedrock-logging                # Basic tier + Bedrock logging
  ./deploy.sh --skip-context-check             # Non-interactive (CI)
EOF
    exit 0
}

# Parse arguments
BEDROCK_LOGGING="false"
SUPPORT_TIER="basic"
SKIP_CONTEXT_CHECK="false"
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        --bedrock-logging)
            BEDROCK_LOGGING="true"
            shift
            ;;
        --support-tier)
            SUPPORT_TIER="${2:-basic}"
            shift 2
            ;;
        --skip-context-check)
            SKIP_CONTEXT_CHECK="true"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Validate support tier
if [[ "$SUPPORT_TIER" != "basic" && "$SUPPORT_TIER" != "business" ]]; then
    echo "ERROR: --support-tier must be 'basic' or 'business', got '${SUPPORT_TIER}'"
    exit 1
fi

echo "=== Phase 1: Python environment ==="
# Verify Python >= 3.10 (required by boto3/aws-cdk-lib)
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "ERROR: Python >= 3.10 required, but found Python ${PYTHON_VERSION}"
    echo "       Install Python 3.14 via pyenv: pyenv install 3.14 && pyenv local 3.14"
    exit 1
fi
echo "    Using Python ${PYTHON_VERSION} ($(which python3))"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

echo "=== Phase 1.5: Customer Context check ==="
CUSTOMER_CONTEXT="layers/skill_assets/skill_files/skills/aws-quota-increase-support/CUSTOMER_CONTEXT.md"
if [ "$SKIP_CONTEXT_CHECK" = "true" ]; then
    echo "Skipping CUSTOMER_CONTEXT.md check (--skip-context-check)"
elif [ -f "$CUSTOMER_CONTEXT" ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo "║  CUSTOMER_CONTEXT.md found                                              ║"
    echo "║                                                                          ║"
    echo "║  This file provides the agent with business context for sizing quota     ║"
    echo "║  increase requests. It ships with a sample company (Voidpunch            ║"
    echo "║  Theoretical Labs) — replace it with your actual customer's info         ║"
    echo "║  before deploying to production.                                         ║"
    echo "║                                                                          ║"
    echo "║  ⚠️  SENSITIVE DATA WARNING:                                             ║"
    echo "║  Do NOT include passwords, API keys, access tokens, PII, or other        ║"
    echo "║  secrets in this file. It is bundled into the Lambda deployment           ║"
    echo "║  package, stored on Amazon S3 Files, and read by an AI agent. Include only       ║"
    echo "║  business context: workload descriptions, growth plans, service           ║"
    echo "║  architecture, and quota preferences.                                    ║"
    echo "║                                                                          ║"
    echo "║  Location: ${CUSTOMER_CONTEXT}      ║"
    echo "╚══════════════════════════════════════════════════════════════════════════╝"
    echo ""
    read -rp "Would you like to open CUSTOMER_CONTEXT.md for editing now? [y/N] " edit_choice
    if [[ "$edit_choice" =~ ^[Yy]$ ]]; then
        if command -v "${EDITOR:-}" &>/dev/null; then
            "$EDITOR" "$CUSTOMER_CONTEXT"
        elif command -v code &>/dev/null; then
            code --wait "$CUSTOMER_CONTEXT"
        elif command -v vim &>/dev/null; then
            vim "$CUSTOMER_CONTEXT"
        elif command -v nano &>/dev/null; then
            nano "$CUSTOMER_CONTEXT"
        else
            echo "No editor found. Please edit the file manually:"
            echo "  $CUSTOMER_CONTEXT"
            echo ""
            read -rp "Press Enter when done editing..."
        fi
        echo "Customer context updated. Continuing deployment..."
    else
        echo "Skipping — deploying with current CUSTOMER_CONTEXT.md content."
    fi
else
    echo "WARNING: CUSTOMER_CONTEXT.md not found at ${CUSTOMER_CONTEXT}"
    echo "The agent will not be able to compose business justifications autonomously."
    echo "Create this file before deploying to production."
    echo ""
    read -rp "Continue deployment without customer context? [y/N] " continue_choice
    if [[ ! "$continue_choice" =~ ^[Yy]$ ]]; then
        echo "Aborting deployment. Create CUSTOMER_CONTEXT.md and re-run."
        exit 1
    fi
fi

echo "=== Phase 2: Build Lambda layers ==="
echo "--- Building deepagents layer ---"
bash layers/deepagents/build.sh

echo "=== Phase 3: CDK deploy ==="
CDK_CONTEXT="-c support_tier=${SUPPORT_TIER} -c bedrock_invocation_logging=${BEDROCK_LOGGING}"

echo ">>> Support tier: ${SUPPORT_TIER}"
if [ "$SUPPORT_TIER" = "basic" ]; then
    echo "    Skipping Support + TrustedAdvisor VPC endpoints and IAM (saves ~\$29/month)"
else
    echo "    Including Support + TrustedAdvisor VPC endpoints and IAM"
fi

if [ "$BEDROCK_LOGGING" = "true" ]; then
    echo ">>> Amazon Bedrock model invocation logging: ENABLED"
    echo "    Logs will be written to /aws/bedrock/modelinvocations in CloudWatch"
else
    echo ">>> Bedrock model invocation logging: DISABLED (use --bedrock-logging to enable)"
fi

cdk deploy --all --require-approval never --outputs-file cdk-outputs.json ${CDK_CONTEXT}

echo "=== Deployment complete ==="
if [ -f cdk-outputs.json ]; then
    echo "Outputs:"
    cat cdk-outputs.json
fi
