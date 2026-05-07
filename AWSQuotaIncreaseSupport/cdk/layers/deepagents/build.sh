#!/bin/bash
set -euo pipefail
# ==============================================================================
# Build the deepagents Lambda layer.
#
# Installs deepagents + langchain-aws (for Amazon Bedrock) into the Lambda-standard
# python/ directory structure.  The resulting directory is consumed by CDK's
# Code.from_asset("layers/deepagents") which zips it into a Lambda layer.
#
# Usage:
#   cd aws-quota-increase-support/cdk/layers/deepagents
#   ./build.sh
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Initialize pyenv if available (for standalone execution outside deploy.sh)
if command -v pyenv &>/dev/null; then
    eval "$(pyenv init -)"
elif [ -d "$HOME/.pyenv" ]; then
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
fi

# Use python3 -m pip for reliability (works with venv or pyenv)
PIP="python3 -m pip"

LAYER_DIR="python"

echo "=== Cleaning previous build ==="
rm -rf "$LAYER_DIR"

echo "=== Installing dependencies into ${LAYER_DIR}/ ==="
# Cross-compile for Lambda (Amazon Linux 2023, glibc 2.34, x86_64).
# Multiple --platform flags ensure we find wheels regardless of manylinux tag generation.
# AL2023 supports manylinux_2_28 and below. PEP 600 names (manylinux_2_NN) are preferred.
$PIP install \
    --target "$LAYER_DIR" \
    --python-version 3.14 \
    --platform manylinux_2_28_x86_64 \
    --platform manylinux_2_17_x86_64 \
    --platform manylinux2014_x86_64 \
    --platform linux_x86_64 \
    --implementation cp \
    --only-binary=:all: \
    --upgrade \
    -r requirements.txt

echo "=== Layer contents ==="
du -sh "$LAYER_DIR"
echo "=== Done — layer ready at ${SCRIPT_DIR}/${LAYER_DIR}/ ==="
