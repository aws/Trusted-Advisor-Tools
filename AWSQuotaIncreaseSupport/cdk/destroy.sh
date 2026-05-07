#!/bin/bash
set -euo pipefail

# ==============================================================================
# AWS Quota Increase Support Agent — Destroy Script
# ==============================================================================
# CDK destroy all stacks (S3 bucket auto-deletes with DESTROY policy)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== CDK destroy ==="
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
cdk destroy --all --force

echo "=== Teardown complete ==="
