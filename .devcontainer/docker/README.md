# Docker profile

This optional configuration adds the maintainer-supported `docker-outside-of-docker` Dev Container Feature. It installs Docker CLI, Compose and Buildx and forwards the host Docker socket.

The profile is useful for CDK asset bundling, container-image projects and other workflows that need a Docker daemon. It does not run a second daemon inside the development container.

The forwarded socket grants control over the host Docker daemon and must be treated as host-level access. Do not open an untrusted workspace with this profile.

Feature reference: https://github.com/devcontainers/features/tree/main/src/docker-outside-of-docker

The base image is pinned by digest and is synchronized by the release assistant. The configuration declares the compatible Feature channel `:1`, while `devcontainer-lock.json` resolves it to an exact reviewed version and digest for this repository. Review and update the declaration and lockfile together whenever the Feature changes.
