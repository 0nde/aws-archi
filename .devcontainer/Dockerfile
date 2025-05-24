# Dockerfile for the Universal Dev Environment
# Base image: Python 3.11 on Debian Bullseye Slim
FROM python:3-slim-bookworm

# Arguments for user creation, can be overridden in devcontainer.json
ARG USERNAME=devuser
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

# Versions for Terraform tools - can be overridden in devcontainer.json build args
ARG TERRAFORM_VERSION="1.12.1" # Specify a recent default version
ARG TFLINT_VERSION="v0.57.0"    # Check GitHub for latest TFLint release
ARG TERRAGRUNT_VERSION="v0.80.2" # Check GitHub for latest Terragrunt release
ARG TFSEC_VERSION="v1.28.14"     # Check GitHub for latest TFsec release
ARG TERRAFORM_DOCS_VERSION="v0.20.0" # Check GitHub for latest terraform-docs release
ARG SENTINEL_VERSION="0.40.0" # Check GitHub for latest Sentinel CLI release

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PATH="/home/${USERNAME}/.local/bin:${PATH}" \
    PYTHONUNBUFFERED=1

# Install system dependencies, create user, and set up sudo
# Using --mount=type=cache for apt lists
RUN --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    sudo \
    git \
    curl \
    gnupg \
    lsb-release \
    software-properties-common \
    ca-certificates \
    unzip \
    procps \
    zsh \
    ruby \
    ruby-dev \
    # For Node.js native modules & other builds
    build-essential \
    # Create the non-root user with sudo access
    && groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} --shell /bin/bash \
    && echo ${USERNAME} ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME} \
    # Clean up apt cache (already cached by buildkit, but good practice)
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Tool Installation (as root) ---

# Install Node.js (LTS) and Yarn
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g yarn aws-cdk cdk-nag \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y gh \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Terraform (specific version)
RUN curl -Ls "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" -o /tmp/terraform.zip \
    && unzip /tmp/terraform.zip -d /usr/local/bin \
    && chmod +x /usr/local/bin/terraform \
    && rm /tmp/terraform.zip

# Install TFLint (specific version)
RUN curl -Ls "https://github.com/terraform-linters/tflint/releases/download/${TFLINT_VERSION}/tflint_linux_amd64.zip" -o /tmp/tflint.zip \
    && unzip /tmp/tflint.zip -d /usr/local/bin \
    && chmod +x /usr/local/bin/tflint \
    && rm /tmp/tflint.zip

# Install Terragrunt (specific version)
RUN curl -Ls "https://github.com/gruntwork-io/terragrunt/releases/download/${TERRAGRUNT_VERSION}/terragrunt_linux_amd64" -o /usr/local/bin/terragrunt \
    && chmod +x /usr/local/bin/terragrunt

# Install TFsec (specific version)
RUN curl -Ls "https://github.com/aquasecurity/tfsec/releases/download/${TFSEC_VERSION}/tfsec-linux-amd64" -o /usr/local/bin/tfsec \
    && chmod +x /usr/local/bin/tfsec

# Install Terraform-docs (specific version)
RUN curl -Ls "https://github.com/terraform-docs/terraform-docs/releases/download/${TERRAFORM_DOCS_VERSION}/terraform-docs-${TERRAFORM_DOCS_VERSION}-linux-amd64.tar.gz" -o /tmp/terraform-docs.tar.gz \
    && tar -xzf /tmp/terraform-docs.tar.gz -C /usr/local/bin terraform-docs \
    && chmod +x /usr/local/bin/terraform-docs \
    && rm /tmp/terraform-docs.tar.gz

# Install Sentinel CLI (specific version)
RUN curl -Ls "https://releases.hashicorp.com/sentinel/${SENTINEL_VERSION}/sentinel_${SENTINEL_VERSION}_linux_amd64.zip" -o /tmp/sentinel.zip \
    && unzip /tmp/sentinel.zip -d /usr/local/bin \
    && chmod +x /usr/local/bin/sentinel \
    && rm /tmp/sentinel.zip

# Install Python tools (e.g., pylint) using pip
# Using --mount=type=cache for pip cache
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m pip install --no-cache-dir --upgrade pip \
    && python3 -m pip install --no-cache-dir pylint cfn-lint

# Install cfn-nag using gem
RUN gem install cfn-nag

# --- Switch to non-root user ---
USER ${USERNAME}
WORKDIR /home/${USERNAME}

# Install Oh My Zsh for the devuser and common plugins
# This section needs to run as the USERNAME, so we ensure USER ${USERNAME} is active.
# If any prior step switched to root, this would implicitly switch back if USER ${USERNAME} was the last USER command.
# However, for clarity and safety, explicitly setting USER ${USERNAME} before user-specific setup is good practice.
# Since USER ${USERNAME} is already set just before WORKDIR, we can proceed.
RUN curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh -o install_omz.sh \
    && sh install_omz.sh --unattended \
    && rm install_omz.sh \
    # Install zsh plugins: zsh-autosuggestions and zsh-syntax-highlighting
    && git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions \
    && git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting \
    # Activate plugins in .zshrc - assumes default plugins=(git)
    && sed -i 's/^plugins=(git)$/plugins=(git zsh-autosuggestions zsh-syntax-highlighting aws terraform node python zsh-completions pip npm yarn)/' /home/${USERNAME}/.zshrc

# Switch back to root to set default shell for devuser and ensure zsh is in /etc/shells
USER root
RUN if ! grep -q "$(which zsh)" /etc/shells; then echo "$(which zsh)" >> /etc/shells; fi \
    && chsh --shell $(which zsh) ${USERNAME}

# Switch back to non-root user for the remainder of the build and runtime
USER ${USERNAME}

# Default command to keep container running for IDEs
CMD ["sleep", "infinity"]
