# AWS Architecture Development Environment

Launch a modern multi-architecture AWS development container in seconds.

Built on **Debian 13 Trixie** with **Python 3.14**, this image provides a consistent environment for AWS architecture, Infrastructure as Code, cloud security and DevOps workflows.

## Supported architectures

The `latest` tag supports:

- `linux/amd64`
- `linux/arm64`

Docker automatically selects the appropriate image for the host architecture.

## Included tools

### AWS and CloudFormation

- AWS CLI v2
- AWS CDK
- cdk-nag
- cfn-lint

### Infrastructure as Code

- Terraform
- Terragrunt
- TFLint
- terraform-docs

### Security and compliance

- ShellCheck
- cdk-nag
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

For reproducible environments, replace `latest` with a specific `sha-*` tag or an immutable image digest.

Use SSH agent forwarding instead of mounting private SSH keys inside the container. If AWS configuration is required, mount it read-only.

## Tags

| Tag | Description | Status |
| --- | --- | --- |
| `latest` | Current multi-architecture image published automatically | Recommended for receiving updates |
| `sha-*` | Image produced from a specific source revision | Recommended for revision-based builds |
| `1.0.1` | Security-hardened multi-architecture release | Recommended stable release |
| `1.0.0` | First multi-architecture release | Available |
| `0.5` | Legacy Debian 12 image | Not recommended |

Tags can technically be moved. For strict immutability, use an image digest.

## Build and security

The image is built automatically for both supported architectures.

Published images include:

- BuildKit SBOM attestations
- BuildKit provenance attestations
- SHA-256 verification of upstream release archives when available
- Weekly automated rebuilds
- Non-root execution by default
- A CI gate that blocks releases containing fixable critical vulnerabilities

Tool versions are maintained in the image build configuration and updated through the automated release pipeline.
