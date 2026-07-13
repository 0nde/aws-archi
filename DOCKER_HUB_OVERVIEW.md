# Hardened AWS Architecture Development Image

A hardened, multi-architecture development image for AWS, Terraform and CDK, published with a verifiable supply chain: pinned project-managed inputs, SBOM and provenance attestations, and keyless Cosign signatures.

## Supported architectures

The `latest` tag supports:

- `linux/amd64`
- `linux/arm64`

Docker automatically selects the appropriate image for the host architecture.

## Included tools

### AWS and CloudFormation

- AWS CLI
- AWS CDK
- cfn-lint

### Infrastructure as Code

- Terraform
- Terragrunt
- TFLint
- terraform-docs

### Linting and quality

- ShellCheck
- cfn-lint
- pylint

### Development environment

- Python and pip
- Node.js and npm
- Git and GitHub CLI
- OpenSSH client
- curl and jq
- Zsh and Oh My Zsh
- Zsh autosuggestions and syntax highlighting

The container runs as the non-root `devuser` account with passwordless sudo available for development tasks. Passwordless sudo is a convenience and is not a security boundary.

## Usage

Pull from Docker Hub:

    docker pull haonde/aws-archi:latest

Or pull the canonical image from GHCR:

    docker pull ghcr.io/0nde/aws-archi:latest

`latest` is the rolling channel. Use a numbered `X.Y.Z` tag for a release checkpoint or `repository@sha256:...` for a strictly immutable environment.

Start an interactive Zsh session:

    docker run --rm -it haonde/aws-archi:latest zsh

Check the installed tools:

    docker run --rm haonde/aws-archi:latest terraform version
    docker run --rm haonde/aws-archi:latest terragrunt --version
    docker run --rm haonde/aws-archi:latest aws --version
    docker run --rm haonde/aws-archi:latest cdk --version
    docker run --rm haonde/aws-archi:latest python --version

## VS Code Dev Container

Rolling configuration:

    {
      "name": "AWS Architecture Development",
      "image": "ghcr.io/0nde/aws-archi:latest",
      "remoteUser": "devuser",
      "init": true
    }

For a reproducible Dev Container, replace the rolling image with the index digest published in the selected GitHub release, using `ghcr.io/0nde/aws-archi@sha256:...`.

The public source repository also provides a Docker-enabled Dev Container profile and project-specific guidance for adding SAM CLI and Session Manager with reviewed installer and update policies.

Use SSH agent forwarding instead of mounting private SSH keys inside the container. Keep AWS credentials in a dedicated Docker volume or another explicitly configured credential provider rather than automatically exposing the host AWS directory.

## Tags and immutability

| Reference | Meaning | Mutability |
| --- | --- | --- |
| `latest` | Current rolling multi-architecture image | Moves after publication and maintenance rebuilds |
| `X.Y.Z` | Published release | Intended to remain stable |
| `sha-*` | Image built from a source commit | Not changed by scheduled refreshes; still a mutable registry alias |
| `@sha256:...` | Exact OCI image index or manifest | Immutable |

A `sha-*` tag identifies source code, not a byte-for-byte reproducible build. Scheduled refreshes update only `latest`, but a source-triggered workflow can still rebuild the alias. Use a digest whenever strict immutability is required.

## Build, provenance and maintenance

The image is built automatically for both supported architectures. GHCR is the canonical registry and Docker Hub is maintained as a public mirror.

Published images include:

- BuildKit SBOM attestations
- BuildKit provenance attestations
- keyless Cosign signatures backed by GitHub OIDC
- SHA-256 verification of upstream release archives where available
- regular rebuilds that refresh operating-system security packages
- non-root execution by default
- a pre-publication gate that rejects fixable critical vulnerabilities

Tool versions are intentionally omitted from this description. Dependency maintenance proposes reviewed source changes, while releases remain a separate maintainer decision. The public source, build workflow and support policy are available at https://github.com/0nde/aws-archi.

Copyable Cosign, SBOM and provenance verification commands are maintained in the public repository README.

Source authored for this repository is licensed under Apache-2.0. Bundled third-party components remain under their respective licenses; notices are installed in `/usr/share/licenses/aws-archi/` inside the image.
