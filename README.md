# AWS Architecture development image

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
