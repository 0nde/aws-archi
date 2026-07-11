#!/usr/bin/env bash
set -euo pipefail

commands=(aws cdk cfn-lint cfn_nag_scan gh node npm python sentinel shellcheck terraform terraform-docs terragrunt tflint trivy zsh)
for command in "${commands[@]}"; do
  command -v "$command" >/dev/null || { echo "missing: $command" >&2; exit 1; }
done

terraform version
terragrunt --version
tflint --version
terraform-docs --version
trivy --version
aws --version
cdk --version
python --version
