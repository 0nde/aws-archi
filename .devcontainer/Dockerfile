# syntax=docker/dockerfile:1.24@sha256:87999aa3d42bdc6bea60565083ee17e86d1f3339802f543c0d03998580f9cb89
FROM node:26-trixie-slim@sha256:ffc78385a788964bb3cbab5e434ff79a10bdc25b8ae6db03fe5fe6cb14053c09 AS node

FROM golang:1.26-trixie@sha256:116489021a0d8ca3facf79f84ee69052cff88733547150a644d45c5eaa91dc43 AS go-tools-builder
ARG TERRAFORM_DOCS_COMMIT=9d4455198941806aa02ec14369de030cda2c2b59
ARG TERRAGRUNT_VERSION=1.1.0
ARG TERRAGRUNT_COMMIT=aad3397a3552a9d5fab90c587e6027d31f2b6ee1
RUN GOBIN=/usr/local/bin go install github.com/google/go-licenses/v2@v2.0.1
WORKDIR /src/terraform-docs
RUN git init . \
    && git remote add origin https://github.com/terraform-docs/terraform-docs.git \
    && git fetch --depth 1 origin "${TERRAFORM_DOCS_COMMIT}" \
    && git checkout --detach FETCH_HEAD \
    && go get golang.org/x/crypto@v0.53.0 golang.org/x/net@v0.56.0 \
    && go mod verify \
    && CGO_ENABLED=0 go build -trimpath \
      -ldflags="-s -w -X github.com/terraform-docs/terraform-docs/internal/version.commit=${TERRAFORM_DOCS_COMMIT}" \
      -o /terraform-docs . \
    && go-licenses report . > /terraform-docs-go-licenses.csv

WORKDIR /src/terragrunt
RUN git init . \
    && git remote add origin https://github.com/gruntwork-io/terragrunt.git \
    && git fetch --depth 1 origin "${TERRAGRUNT_COMMIT}" \
    && git checkout --detach FETCH_HEAD \
    && go mod verify \
    && CGO_ENABLED=0 go build -trimpath \
      -ldflags="-s -w -X github.com/gruntwork-io/terragrunt/internal/version.Version=v${TERRAGRUNT_VERSION}" \
      -o /terragrunt . \
    && go-licenses report . > /terragrunt-go-licenses.csv

FROM python:3.14-slim-trixie@sha256:b877e50bd90de10af8d82c57a022fc2e0dc731c5320d762a27986facfc3355c1

ARG TARGETARCH
ARG USERNAME=devuser
ARG USER_UID=1000
ARG USER_GID=1000
ARG TERRAFORM_VERSION=1.15.8
ARG TFLINT_VERSION=0.63.1
ARG GH_VERSION=2.96.0
ARG AWS_CLI_VERSION=2.35.21
ARG NPM_VERSION=12.0.1
ARG TERRAFORM_SHA256_AMD64=d25ce7b6902013ad905db3d2eab0be4cd905887fe88b81a6171b8d5503c31f3d
ARG TERRAFORM_SHA256_ARM64=8891e9dcedc9e3b8950bc6af9d4d8af1f4cfade3062f53b9dc403a89f6ce8c9c
ARG TFLINT_SHA256_AMD64=8441a7d97df20431f19c9b9d27ff4c63e308c964e86660bc7cc0cf7bbe0725e8
ARG TFLINT_SHA256_ARM64=6d858ca7f11858c3fe3c5e29cc746823abccb55e2d2e2da130fa7ad7ea4eecb8
ARG GH_SHA256_AMD64=83d5c2ccad5498f58bf6368acb1ab32588cf43ab3a4b1c301bf36328b1c8bd60
ARG GH_SHA256_ARM64=06f86ec7103d41993b76cd78072f43595c34aaa56506d971d9860e67140bf909
ARG AWS_CLI_SHA256_AMD64=1fe665267a6149dfb8551cec52b419fa6e82533fab6dd7678939209246e792ee
ARG AWS_CLI_SHA256_ARM64=1d7a1f26a1bd9f0610663b7a4b571def6990692c8c66223ebe09ac2445787bcc
ARG OH_MY_ZSH_COMMIT=677a4592b18c08ddea737f8aca70bac0e9fc9313
ARG ZSH_AUTOSUGGESTIONS_COMMIT=85919cd1ffa7d2d5412f6d3fe437ebdbeeec4fc5
ARG ZSH_SYNTAX_HIGHLIGHTING_COMMIT=1d85c692615a25fe2293bdd44b34c217d5d2bf04

ARG DEBIAN_FRONTEND=noninteractive

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

LABEL org.opencontainers.image.source="https://github.com/0nde/aws-archi" \
      org.opencontainers.image.licenses="Apache-2.0"

# Debian package versions intentionally follow the patched Trixie repositories;
# pinning exact revisions here would prevent the weekly security rebuild from updating them.
# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      bash-completion ca-certificates curl git jq less openssh-client procps \
      shellcheck sudo unzip zsh \
    && groupadd --gid "${USER_GID}" "${USERNAME}" \
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" --create-home --shell /usr/bin/zsh "${USERNAME}" \
    && printf '%s ALL=(root) NOPASSWD:ALL\n' "${USERNAME}" > "/etc/sudoers.d/${USERNAME}" \
    && chmod 0440 "/etc/sudoers.d/${USERNAME}"

# Use the official Node.js distribution instead of Debian's npm dependency tree.
COPY --from=node /usr/local/ /usr/local/
COPY --from=go-tools-builder /terraform-docs /terragrunt /usr/local/bin/

# Install release archives for the active BuildKit architecture. Every project
# providing release hashes is checked against values reviewed in this file.
RUN set -eux; \
    case "${TARGETARCH}" in \
      amd64) arch=amd64; terraform_sha="${TERRAFORM_SHA256_AMD64}"; tflint_sha="${TFLINT_SHA256_AMD64}"; gh_sha="${GH_SHA256_AMD64}" ;; \
      arm64) arch=arm64; terraform_sha="${TERRAFORM_SHA256_ARM64}"; tflint_sha="${TFLINT_SHA256_ARM64}"; gh_sha="${GH_SHA256_ARM64}" ;; \
      *) echo "Unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    install_zip() { url="$1" expected="$2" binary="$3"; file="/tmp/${url##*/}"; rm -rf /tmp/tool; curl -fsSLo "$file" "$url"; echo "${expected}  ${file}" | sha256sum -c -; mkdir /tmp/tool; unzip -q "$file" -d /tmp/tool; install -m 0755 "/tmp/tool/${binary}" "/usr/local/bin/${binary}"; rm -rf /tmp/tool "$file"; }; \
    install_zip "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${arch}.zip" "${terraform_sha}" terraform; \
    install_zip "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/tflint_linux_${arch}.zip" "${tflint_sha}" tflint; \
    gh_archive="gh_${GH_VERSION}_linux_${arch}.tar.gz"; curl -fsSLo "/tmp/${gh_archive}" "https://github.com/cli/cli/releases/download/v${GH_VERSION}/${gh_archive}"; echo "${gh_sha}  /tmp/${gh_archive}" | sha256sum -c -; tar -xzf "/tmp/${gh_archive}" -C /tmp; install -m 0755 "/tmp/gh_${GH_VERSION}_linux_${arch}/bin/gh" /usr/local/bin/gh; rm -rf "/tmp/${gh_archive}" "/tmp/gh_${GH_VERSION}_linux_${arch}"

# AWS CLI is versioned and verified against an independently reviewed hash.
RUN set -eux; \
    case "${TARGETARCH}" in amd64) aws_arch=x86_64; aws_sha="${AWS_CLI_SHA256_AMD64}" ;; arm64) aws_arch=aarch64; aws_sha="${AWS_CLI_SHA256_ARM64}" ;; *) exit 1 ;; esac; \
    curl -fsSLo /tmp/awscliv2.zip "https://awscli.amazonaws.com/awscli-exe-linux-${aws_arch}-${AWS_CLI_VERSION}.zip"; \
    echo "${aws_sha}  /tmp/awscliv2.zip" | sha256sum -c -; \
    unzip -q /tmp/awscliv2.zip -d /tmp; /tmp/aws/install; rm -rf /tmp/aws /tmp/awscliv2.zip

COPY tooling/python/requirements-tools.txt /tmp/requirements-tools.txt
COPY tooling/node/package.json tooling/node/package-lock.json /opt/aws-cdk/

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements-tools.txt \
    && npm install --global "npm@${NPM_VERSION}" \
    && npm ci --prefix /opt/aws-cdk --omit=dev --ignore-scripts \
    && ln -s /opt/aws-cdk/node_modules/.bin/cdk /usr/local/bin/cdk \
    && npm cache clean --force \
    && rm -rf /tmp/* /root/.npm

COPY LICENSE NOTICE THIRD_PARTY_NOTICES.md SOURCE_OFFER.md /usr/share/licenses/aws-archi/
COPY third_party_licenses/ /usr/share/licenses/aws-archi/third_party/
COPY --from=go-tools-builder /terraform-docs-go-licenses.csv /terragrunt-go-licenses.csv /usr/share/licenses/aws-archi/go-dependencies/

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
