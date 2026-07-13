# AWS Architecture development image

[![Build and publish image](https://github.com/0nde/aws-archi/actions/workflows/image.yml/badge.svg?branch=main)](https://github.com/0nde/aws-archi/actions/workflows/image.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/haonde/aws-archi?logo=docker)](https://hub.docker.com/r/haonde/aws-archi)
[![Docker Image Version](https://img.shields.io/docker/v/haonde/aws-archi?sort=semver&logo=docker&label=image)](https://hub.docker.com/r/haonde/aws-archi/tags)
[![License](https://img.shields.io/github/license/0nde/aws-archi)](https://github.com/0nde/aws-archi/blob/main/LICENSE)

![Platforms](https://img.shields.io/badge/platforms-linux%2Famd64%20%7C%20linux%2Farm64-blue)
![SBOM](https://img.shields.io/badge/SBOM-BuildKit-informational)
![Provenance](https://img.shields.io/badge/provenance-mode%3Dmax-informational)
![Signed](https://img.shields.io/badge/signed-Cosign%20%2B%20GitHub%20OIDC-success)

A multi-architecture Dev Container for AWS, Terraform and CDK work. The core image deliberately stays focused; optional Docker and AWS application extensions add heavier tools only when a project needs them.

## Included tools

- Python on Debian
- Terraform, Terragrunt, TFLint and terraform-docs
- AWS CLI and AWS CDK
- cfn-lint, GitHub CLI, ShellCheck, Node.js and Zsh

The exact pins live in `.devcontainer/Dockerfile` and the lock files under `tooling/`. Release archives are checked against reviewed SHA-256 values where available, Python packages require hashes, and AWS CDK is installed from an npm lockfile.

## Use the image

GHCR is the canonical registry. Docker Hub is a public mirror:

```bash
docker pull ghcr.io/0nde/aws-archi:latest
docker pull haonde/aws-archi:latest
```

Open this repository in VS Code and choose **Dev Containers: Reopen in Container**. AWS configuration is stored in the isolated Docker volume `aws-archi-aws-config`; host AWS and SSH directories are never mounted automatically. Authenticate inside the container with `aws sso login --no-browser` and use SSH agent forwarding when required.

Build and verify on the host's native architecture:

```bash
docker buildx build --load -f .devcontainer/Dockerfile -t aws-archi:test .
docker run --rm -v "$PWD/scripts:/tests:ro" aws-archi:test bash /tests/verify-tools.sh
```

The CI builds and tests both supported architectures on native runners. A local cross-architecture build may use emulation and is therefore slower.

## Optional Dev Container profiles

The default configuration uses the lean core image. One alternative configuration is available when creating a Codespace or can be copied into a consuming repository. AWS application tooling remains documented as a project-specific extension rather than an unpinned installation:

| Profile | Added capabilities |
| --- | --- |
| `.devcontainer/docker/devcontainer.json` | Docker CLI, Compose and Buildx connected to the host Docker socket |
| `.devcontainer/aws-app/README.md` | Verified upstream guidance for adding SAM CLI and Session Manager to a project-specific image |

The Docker profile can control the host Docker daemon. Use it only for trusted workspaces. SAM's container-based build and local-test commands require a working Docker daemon.

## Image references

- `latest` is a rolling tag and is rebuilt regularly.
- `X.Y.Z` identifies a published release and is intended to remain stable.
- `sha-*` identifies source code, but remains a mutable alias if a source-triggered build is rerun; scheduled refreshes update only `latest`.
- `repository@sha256:...` is the only strictly immutable reference.

See [SUPPORT.md](SUPPORT.md) for the compatibility policy and [RELEASING.md](RELEASING.md) for the release process.

## Publishing and maintenance

GitHub Actions validates both architectures, publishes the canonical GHCR image, mirrors it to Docker Hub, generates BuildKit SBOM and provenance attestations, and signs the published manifests keylessly with GitHub OIDC and Cosign.

Dependency maintenance proposes pull requests; it does not create releases or merge changes. See [.github/MAINTENANCE.md](.github/MAINTENANCE.md).

## Security and licensing

Report vulnerabilities through GitHub private vulnerability reporting as described in [SECURITY.md](SECURITY.md).

Source authored for this repository is licensed under Apache-2.0. The image contains third-party software under separate terms, including BUSL-1.1, MPL-2.0 and GPL-family licenses. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [SOURCE_OFFER.md](SOURCE_OFFER.md); the same notices are installed under `/usr/share/licenses/aws-archi/` in the image.
