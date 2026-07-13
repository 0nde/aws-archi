# Docker profile

This optional configuration adds the maintainer-supported `docker-outside-of-docker` Dev Container Feature. It installs Docker CLI, Compose and Buildx and forwards the host Docker socket.

The profile is useful for CDK asset bundling, container-image projects and other workflows that need a Docker daemon. It does not run a second daemon inside the development container.

The forwarded socket grants control over the host Docker daemon and must be treated as host-level access. Do not open an untrusted workspace with this profile.

Feature reference: https://github.com/devcontainers/features/tree/main/src/docker-outside-of-docker

The base image is pinned by digest and is synchronized by the release assistant. The Feature uses its compatible `:1` channel and can therefore update independently; consuming projects that require a byte-for-byte reproducible editor layer should pin the Feature to a reviewed digest as well.
