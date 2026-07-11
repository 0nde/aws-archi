#!/usr/bin/env bash
set -euo pipefail

commands=(aws cdk cfn-lint gh node npm python shellcheck terraform terraform-docs terragrunt tflint zsh)
for command in "${commands[@]}"; do
  command -v "$command" >/dev/null || { echo "missing: $command" >&2; exit 1; }
done

# These tools were intentionally removed because their current distributions
# carry critical vulnerabilities or obsolete dependency trees.
removed_commands=(cdk-nag cfn_nag_scan sentinel trivy)
for command in "${removed_commands[@]}"; do
  ! command -v "$command" >/dev/null || { echo "unexpected vulnerable tool: $command" >&2; exit 1; }
done

terraform version
terragrunt --version
tflint --version
terraform-docs --version
aws --version
cdk --version
python --version

test "$(id -un)" = "devuser"
sudo -n true
! npm list --global --depth=0 cdk-nag >/dev/null 2>&1
test -f /usr/share/licenses/aws-archi/LICENSE
test -f /usr/share/licenses/aws-archi/third_party/terraform-1.15.8/LICENSE
