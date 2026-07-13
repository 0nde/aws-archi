# Hardened AWS Architecture Development Image

[![Build and publish image](https://github.com/0nde/aws-archi/actions/workflows/image.yml/badge.svg?branch=main)](https://github.com/0nde/aws-archi/actions/workflows/image.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/haonde/aws-archi?logo=docker)](https://hub.docker.com/r/haonde/aws-archi)
[![Docker Image Version](https://img.shields.io/docker/v/haonde/aws-archi?sort=semver&logo=docker&label=image)](https://hub.docker.com/r/haonde/aws-archi/tags)
[![License](https://img.shields.io/github/license/0nde/aws-archi)](https://github.com/0nde/aws-archi/blob/main/LICENSE)

![Platforms](https://img.shields.io/badge/platforms-linux%2Famd64%20%7C%20linux%2Farm64-blue)
![SBOM](https://img.shields.io/badge/SBOM-BuildKit-informational)
![Provenance](https://img.shields.io/badge/provenance-mode%3Dmax-informational)
![Signed](https://img.shields.io/badge/signed-Cosign%20%2B%20GitHub%20OIDC-success)

A hardened, multi-architecture development image for AWS, Terraform and CDK, published with a verifiable supply chain: pinned project-managed inputs, SBOM and provenance attestations, and keyless Cosign signatures.

## Included tools

- Python on Debian
- Terraform, Terragrunt, TFLint and terraform-docs
- AWS CLI and AWS CDK
- cfn-lint, GitHub CLI, ShellCheck, Node.js and Zsh

The exact project-managed pins live in `.devcontainer/Dockerfile` and the lock files under `tooling/`. Release archives are checked against reviewed SHA-256 values where available, Python packages require hashes, and AWS CDK is installed from an npm lockfile. Debian packages deliberately follow the patched Trixie repositories so regular rebuilds can apply operating-system security updates.

## Use the image

GHCR is the canonical registry. Docker Hub is a public mirror:

```bash
docker pull ghcr.io/0nde/aws-archi:latest
docker pull haonde/aws-archi:latest
```

`latest` is the rolling channel. Use a numbered `X.Y.Z` tag for a release checkpoint and an image digest for a strictly immutable environment.

Open this repository in VS Code and choose **Dev Containers: Reopen in Container**. AWS configuration is stored in the isolated Docker volume `aws-archi-aws-config`; host AWS and SSH directories are never mounted automatically. Authenticate inside the container with `aws sso login --no-browser` and use SSH agent forwarding when required.

Build and verify on the host's native architecture:

```bash
docker buildx build --load -f .devcontainer/Dockerfile -t aws-archi:test .
docker run --rm -v "$PWD/scripts:/tests:ro" aws-archi:test bash /tests/verify-tools.sh
```

The CI builds and tests both supported architectures on native runners. A local cross-architecture build may use emulation and is therefore slower.

## Verify a release

Install Docker Buildx, `jq` and Cosign, then start from the version and immutable index digest published in the GitHub release notes:

```bash
VERSION=X.Y.Z
DIGEST=sha256:REPLACE_WITH_RELEASE_INDEX_DIGEST
IMAGE="ghcr.io/0nde/aws-archi@${DIGEST}"

cosign verify "$IMAGE" \
  --certificate-identity "https://github.com/0nde/aws-archi/.github/workflows/image.yml@refs/tags/v${VERSION}" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"

docker buildx imagetools inspect "$IMAGE" --format '{{json .Manifest}}' |
  jq -e '[.manifests[].platform | select(.os != "unknown") | "\(.os)/\(.architecture)"] | sort == ["linux/amd64", "linux/arm64"]'

for platform in linux/amd64 linux/arm64; do
  docker buildx imagetools inspect "$IMAGE" \
    --format "{{json (index .SBOM \"$platform\")}}" |
    jq -e '.SPDX.spdxVersion and (.SPDX.packages | length > 0)'
  docker buildx imagetools inspect "$IMAGE" \
    --format "{{json (index .Provenance \"$platform\")}}" |
    jq -e '.SLSA.buildDefinition.buildType and .SLSA.runDetails.builder.id'
done
```

The same digest can be checked through the Docker Hub mirror by changing the repository in `IMAGE` to `haonde/aws-archi`. A successful verification proves the published signature and attestations for that digest; it does not replace vulnerability assessment for a specific use case.

## Optional Dev Container profiles

The repository provides one Docker-enabled profile that can be selected when creating a Codespace or copied into a consuming repository. Guidance for AWS application tooling is maintained separately so projects can apply their own reviewed installation and update policy:

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
