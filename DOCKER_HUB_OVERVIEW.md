# AWS Architecture Development Environment

Launch a modern multi-architecture AWS development container in seconds.

Built on Debian with Python, this image provides a consistent environment for AWS architecture, Infrastructure as Code, cloud security and DevOps workflows.

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

### Security and compliance

- ShellCheck
- cfn-lint

### Development environment

- Python, pip and pylint
- Node.js and npm
- Git and GitHub CLI
- OpenSSH client
- curl and jq
- Zsh and Oh My Zsh
- Zsh autosuggestions and syntax highlighting

The container runs as the non-root `devuser` account with passwordless sudo available for development tasks.

## Usage

Pull the current multi-architecture image:

    docker pull haonde/aws-archi:latest

Start an interactive Zsh session:

    docker run --rm -it haonde/aws-archi:latest zsh

Check the installed tools:

    docker run --rm haonde/aws-archi:latest terraform version
    docker run --rm haonde/aws-archi:latest terragrunt --version
    docker run --rm haonde/aws-archi:latest aws --version
    docker run --rm haonde/aws-archi:latest cdk --version
    docker run --rm haonde/aws-archi:latest python --version

## VS Code Dev Container

Basic configuration:

    {
      "name": "AWS Architecture Development",
      "image": "haonde/aws-archi:latest",
      "remoteUser": "devuser",
      "init": true
    }

For strict reproducibility, use a specific `sha-*` tag or, preferably, an immutable image digest.

Use SSH agent forwarding instead of mounting private SSH keys inside the container. Keep AWS credentials in a dedicated Docker volume or another explicitly configured credential provider rather than automatically exposing the host AWS directory.

## Tags

| Tag | Description | Status |
| --- | --- | --- |
| `latest` | Current multi-architecture image published automatically | Recommended for receiving updates |
| `X.Y.Z` | Images associated with published releases | Recommended for stable environments |
| `sha-*` | Images associated with specific source revisions | Recommended for revision-based builds |

Tags can technically be moved. For strict immutability, use an image digest.

## Build and security

The image is built automatically for both supported architectures.

Published images include:

- BuildKit SBOM attestations
- BuildKit provenance attestations
- Keyless Cosign signatures backed by GitHub OIDC
- SHA-256 verification of upstream release archives when available
- Weekly automated rebuilds
- Non-root execution by default
- A pre-publication gate that rejects images containing fixable critical vulnerabilities

Tool versions are maintained in the image build configuration and updated through the automated release pipeline.

Source authored for this repository is licensed under Apache-2.0. Bundled third-party components remain under their respective licenses; notices are installed in `/usr/share/licenses/aws-archi/` inside the image.
