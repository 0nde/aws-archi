# Third-party notices

The Apache-2.0 license in `LICENSE` applies only to the source authored for this repository. The container image bundles third-party software under its own terms; Apache-2.0 does not relicense those components.

## Standalone tools

| Component | Version source | License | Bundled notice |
| --- | --- | --- | --- |
| Terraform | `.devcontainer/Dockerfile` | BUSL-1.1 | `third_party_licenses/terraform-1.15.8/LICENSE` |
| TFLint | `.devcontainer/Dockerfile` | MPL-2.0 and BUSL-1.1 | `third_party_licenses/tflint-0.63.1/` |
| Terragrunt | `.devcontainer/Dockerfile` | MIT | `third_party_licenses/terragrunt-1.1.0/LICENSE.txt` |
| terraform-docs | pinned source commit | MIT and dependency-specific terms | `third_party_licenses/terraform-docs-9d445519/LICENSE` |
| GitHub CLI | `.devcontainer/Dockerfile` | MIT and dependency-specific terms | `third_party_licenses/github-cli-2.96.0/LICENSE` |
| AWS CLI | `.devcontainer/Dockerfile` | Apache-2.0 and bundled third-party terms | `third_party_licenses/aws-cli-2.35.21/` |

The container also preserves the license and notice files shipped with Python, pip, Node.js, npm, AWS CDK, cfn-lint, pylint, Oh My Zsh and its plugins. Dependency-level Go license reports for locally compiled tools are installed under `/usr/share/licenses/aws-archi/go-dependencies/`.

## Debian packages

Debian package copyright files remain available inside the image under `/usr/share/doc/<package>/copyright`. The generated SBOM identifies the exact binary package versions included in each published image.

## Source code

Corresponding source information and immutable upstream references are documented in `SOURCE_OFFER.md`. BuildKit SBOM and provenance attestations accompany each image.
