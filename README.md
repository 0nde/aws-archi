# AWS Architecture development image

Dev Container multi-architecture (`linux/amd64` and `linux/arm64`) for AWS, Terraform and CDK work.

## Included tools

- Python 3.14 on Debian 13 (Trixie)
- Terraform, Terragrunt, TFLint, terraform-docs and Sentinel
- AWS CLI v2, AWS CDK and cdk-nag
- Trivy (`trivy config` replaces the legacy tfsec workflow)
- cfn-lint, cfn-nag, GitHub CLI, ShellCheck, Node.js and zsh

The version pins live at the top of `.devcontainer/Dockerfile`. Release archives are checked against upstream SHA-256 manifests when those manifests are published.

## Local use

Open this repository in VS Code and choose **Dev Containers: Reopen in Container**. The local AWS directory is mounted read-only. Authenticate on the host (`aws sso login`) and use SSH agent forwarding; private SSH keys are never mounted in the container.

Build and verify locally:

```bash
docker buildx build --load --platform linux/amd64 -f .devcontainer/Dockerfile -t aws-archi:test .
docker run --rm -v "$PWD/scripts:/tests:ro" aws-archi:test bash /tests/verify-tools.sh
```

## Publishing

GitHub Actions publishes `haonde/aws-archi` and `ghcr.io/0nde/aws-archi` for both supported architectures. Configure the repository secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`. Each published image includes BuildKit SBOM and provenance attestations and is rebuilt weekly.
