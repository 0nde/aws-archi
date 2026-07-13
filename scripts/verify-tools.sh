#!/usr/bin/env bash
set -euo pipefail

commands=(
  aws cdk cfn-lint curl gh git jq node npm pip pylint python shellcheck
  ssh terraform terraform-docs terragrunt tflint zsh
)
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
gh --version
node --version
npm --version
python --version
python -m pip --version
python -m pylint --version
cfn-lint --version

test "$(id -un)" = "devuser"
sudo -n true
python -m pip check
npm list --prefix /opt/aws-cdk --omit=dev >/dev/null
! npm list --global --depth=0 cdk-nag >/dev/null 2>&1

mapfile -t terraform_licenses < <(
  find /usr/share/licenses/aws-archi/third_party \
    -maxdepth 2 -type f -path '*/terraform-[0-9]*/LICENSE' -print
)
test "${#terraform_licenses[@]}" -eq 1
test -f "${terraform_licenses[0]}"
test -f /usr/share/licenses/aws-archi/LICENSE
test -f /usr/share/licenses/aws-archi/NOTICE
test -f /usr/share/licenses/aws-archi/THIRD_PARTY_NOTICES.md
test -s /usr/share/licenses/aws-archi/go-dependencies/terraform-docs-go-licenses.csv
test -s /usr/share/licenses/aws-archi/go-dependencies/terragrunt-go-licenses.csv

temporary="$(mktemp -d)"
trap 'rm -rf "$temporary"' EXIT

cat >"$temporary/main.tf" <<'EOF'
terraform {
  required_version = ">= 1.0"
}

variable "example" {
  type    = string
  default = "ok"
}
EOF
terraform -chdir="$temporary" init -backend=false -input=false >/dev/null
terraform -chdir="$temporary" validate >/dev/null
terraform-docs markdown table "$temporary" >/dev/null

cat >"$temporary/template.yaml" <<'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  ExampleQueue:
    Type: AWS::SQS::Queue
EOF
cfn-lint "$temporary/template.yaml"

cat >"$temporary/check.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' ok
EOF
shellcheck "$temporary/check.sh"

python - <<'PY'
import cfnlint
import pylint

assert cfnlint.__package__ == "cfnlint"
assert pylint.__package__ == "pylint"
PY
node -e 'if (process.versions.node.split(".")[0] < 20) process.exit(1)'
git -C "$temporary" init --quiet
zsh -ic 'test -n "$ZSH_VERSION" && test -d "$ZSH"'
test -d /home/devuser/.oh-my-zsh/custom/plugins/zsh-autosuggestions
test -d /home/devuser/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting
