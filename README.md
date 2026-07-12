# AWS Architecture development image


[![Build and publish image](https://github.com/0nde/aws-archi/actions/workflows/image.yml/badge.svg?branch=main)](https://github.com/0nde/aws-archi/actions/workflows/image.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/haonde/aws-archi?logo=docker)](https://hub.docker.com/r/haonde/aws-archi)
[![Docker Image Version](https://img.shields.io/docker/v/haonde/aws-archi?sort=semver&logo=docker&label=image)](https://hub.docker.com/r/haonde/aws-archi/tags)
[![License](https://img.shields.io/github/license/0nde/aws-archi)](https://github.com/0nde/aws-archi/blob/main/LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/0nde/aws-archi/main)](https://github.com/0nde/aws-archi/commits/main)

![Platforms](https://img.shields.io/badge/platforms-linux%2Famd64%20%7C%20linux%2Farm64-blue)
![SBOM](https://img.shields.io/badge/SBOM-BuildKit-informational)
![Provenance](https://img.shields.io/badge/provenance-mode%3Dmax-informational)
![Signed](https://img.shields.io/badge/signed-Cosign%20%2B%20GitHub%20OIDC-success)

Dev Container multi-architecture (`linux/amd64` and `linux/arm64`) for AWS, Terraform and CDK work.

## Included tools

- Python on Debian Trixie
- Terraform, Terragrunt, TFLint and terraform-docs
- AWS CLI and AWS CDK
- cfn-lint, GitHub CLI, ShellCheck, Node.js and zsh

Version pins live in `.devcontainer/Dockerfile` and the lock files under `tooling/`. Release archives are checked against reviewed SHA-256 values, Python packages require hashes, and AWS CDK is installed from an npm lockfile.

## Local use

Open this repository in VS Code and choose **Dev Containers: Reopen in Container**. AWS configuration is stored in the isolated Docker volume `aws-archi-aws-config`; host AWS and SSH directories are never mounted automatically. Authenticate inside the container with `aws sso login --no-browser` and use SSH agent forwarding when required.

Build and verify locally:

```bash
docker buildx build --load --platform linux/amd64 -f .devcontainer/Dockerfile -t aws-archi:test .
docker run --rm -v "$PWD/scripts:/tests:ro" aws-archi:test bash /tests/verify-tools.sh
```

## Publishing

GitHub Actions publishes `haonde/aws-archi` and `ghcr.io/0nde/aws-archi` for both supported architectures. Configure the repository secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`. Each published image includes BuildKit SBOM and provenance attestations and is rebuilt weekly.

Validation runs before publication. Published manifests are additionally signed keylessly with GitHub OIDC and Cosign.

## Security and licensing

Report vulnerabilities through GitHub private vulnerability reporting as described in `SECURITY.md`.

Source authored for this repository is licensed under Apache-2.0. The image contains third-party software under separate terms, including BUSL-1.1, MPL-2.0 and GPL-family licenses. See `THIRD_PARTY_NOTICES.md` and `SOURCE_OFFER.md`; the same notices are installed under `/usr/share/licenses/aws-archi/` in the image.
