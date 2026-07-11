# syntax=docker/dockerfile:1.18
FROM python:3.14-slim-trixie

ARG TARGETARCH
ARG USERNAME=devuser
ARG USER_UID=1000
ARG USER_GID=1000
ARG TERRAFORM_VERSION=1.15.8
ARG TERRAGRUNT_VERSION=1.1.0
ARG TFLINT_VERSION=0.63.1
ARG TERRAFORM_DOCS_VERSION=0.24.0
ARG TRIVY_VERSION=0.72.0
ARG SENTINEL_VERSION=0.41.0
ARG AWS_CDK_VERSION=2.1130.0
ARG CDK_NAG_VERSION=3.0.1
ARG CFN_LINT_VERSION=1.53.0
ARG CFN_NAG_VERSION=0.8.10
ARG OH_MY_ZSH_COMMIT=677a4592b18c08ddea737f8aca70bac0e9fc9313
ARG ZSH_AUTOSUGGESTIONS_COMMIT=85919cd1ffa7d2d5412f6d3fe437ebdbeeec4fc5
ARG ZSH_SYNTAX_HIGHLIGHTING_COMMIT=1d85c692615a25fe2293bdd44b34c217d5d2bf04

ENV DEBIAN_FRONTEND=noninteractive \
    PATH="/home/${USERNAME}/.local/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      bash-completion build-essential ca-certificates curl gh git gnupg jq less \
      nodejs npm openssh-client procps ruby ruby-dev shellcheck sudo unzip zsh \
    && groupadd --gid "${USER_GID}" "${USERNAME}" \
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" --create-home --shell /usr/bin/zsh "${USERNAME}" \
    && printf '%s ALL=(root) NOPASSWD:ALL\n' "${USERNAME}" > "/etc/sudoers.d/${USERNAME}" \
    && chmod 0440 "/etc/sudoers.d/${USERNAME}"

# Install release archives for the active BuildKit architecture. Every project
# providing SHA256SUMS is verified before its archive is extracted.
RUN set -eux; \
    case "${TARGETARCH}" in amd64) arch=amd64; trivy_arch=64bit ;; arm64) arch=arm64; trivy_arch=ARM64 ;; *) echo "Unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; esac; \
    install_zip() { url="$1" sums="$2" binary="$3"; file="/tmp/${url##*/}"; curl -fsSLo "$file" "$url"; curl -fsSLo /tmp/SHA256SUMS "$sums"; (cd /tmp && grep "  ${file##*/}$" SHA256SUMS | sha256sum -c -); unzip -q "$file" -d /tmp/tool; install -m 0755 "/tmp/tool/${binary}" "/usr/local/bin/${binary}"; rm -rf /tmp/tool "$file" /tmp/SHA256SUMS; }; \
    install_tar() { url="$1" sums="$2" binary="$3"; file="/tmp/${url##*/}"; curl -fsSLo "$file" "$url"; curl -fsSLo /tmp/checksums "$sums"; (cd /tmp && grep "${file##*/}$" checksums | sha256sum -c -); tar -xzf "$file" -C /tmp; install -m 0755 "/tmp/${binary}" "/usr/local/bin/${binary}"; rm -f "$file" "/tmp/${binary}" /tmp/checksums; }; \
    install_zip "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${arch}.zip" "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_SHA256SUMS" terraform; \
    install_zip "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/tflint_linux_${arch}.zip" "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/checksums.txt" tflint; \
    install_tar "https://github.com/terraform-docs/terraform-docs/releases/download/v${TERRAFORM_DOCS_VERSION}/terraform-docs-v${TERRAFORM_DOCS_VERSION}-linux-${arch}.tar.gz" "https://github.com/terraform-docs/terraform-docs/releases/download/v${TERRAFORM_DOCS_VERSION}/terraform-docs-v${TERRAFORM_DOCS_VERSION}.sha256sum" terraform-docs; \
    install_tar "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-${trivy_arch}.tar.gz" "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_checksums.txt" trivy; \
    tg="/tmp/terragrunt_linux_${arch}"; curl -fsSLo "$tg" "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/terragrunt_linux_${arch}"; curl -fsSLo /tmp/SHA256SUMS "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/SHA256SUMS"; (cd /tmp && grep "  ${tg##*/}$" SHA256SUMS | sha256sum -c -); install -m 0755 "$tg" /usr/local/bin/terragrunt; rm -f "$tg" /tmp/SHA256SUMS; \
    install_zip "https://releases.hashicorp.com/sentinel/${SENTINEL_VERSION}/sentinel_${SENTINEL_VERSION}_linux_${arch}.zip" "https://releases.hashicorp.com/sentinel/${SENTINEL_VERSION}/sentinel_${SENTINEL_VERSION}_SHA256SUMS" sentinel

# AWS CLI publishes architecture-specific signed bundles. HTTPS transport plus
# AWS's own installer is used here; the remaining standalone tools are checksummed above.
RUN set -eux; \
    case "${TARGETARCH}" in amd64) aws_arch=x86_64 ;; arm64) aws_arch=aarch64 ;; esac; \
    curl -fsSLo /tmp/awscliv2.zip "https://awscli.amazonaws.com/awscli-exe-linux-${aws_arch}.zip"; \
    unzip -q /tmp/awscliv2.zip -d /tmp; /tmp/aws/install; rm -rf /tmp/aws /tmp/awscliv2.zip

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-cache-dir "cfn-lint==${CFN_LINT_VERSION}" pylint \
    && npm install --global "aws-cdk@${AWS_CDK_VERSION}" "cdk-nag@${CDK_NAG_VERSION}" \
    && gem install cfn-nag --version "${CFN_NAG_VERSION}" --no-document \
    && npm cache clean --force \
    && rm -rf /root/.gem /tmp/*

USER ${USERNAME}
WORKDIR /home/${USERNAME}

RUN set -eux; \
    clone_at() { repo="$1" destination="$2" commit="$3"; git init "$destination"; git -C "$destination" remote add origin "$repo"; git -C "$destination" fetch --depth 1 origin "$commit"; git -C "$destination" checkout --detach FETCH_HEAD; rm -rf "$destination/.git"; }; \
    clone_at https://github.com/ohmyzsh/ohmyzsh.git .oh-my-zsh "${OH_MY_ZSH_COMMIT}"; \
    cp .oh-my-zsh/templates/zshrc.zsh-template .zshrc; \
    clone_at https://github.com/zsh-users/zsh-autosuggestions.git .oh-my-zsh/custom/plugins/zsh-autosuggestions "${ZSH_AUTOSUGGESTIONS_COMMIT}"; \
    clone_at https://github.com/zsh-users/zsh-syntax-highlighting.git .oh-my-zsh/custom/plugins/zsh-syntax-highlighting "${ZSH_SYNTAX_HIGHLIGHTING_COMMIT}"; \
    sed -i 's/^plugins=(git)$/plugins=(git aws terraform node npm python pip gh zsh-autosuggestions zsh-syntax-highlighting)/' .zshrc

CMD ["sleep", "infinity"]
