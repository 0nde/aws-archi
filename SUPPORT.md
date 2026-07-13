# Support and compatibility

## Supported platforms

Published images support `linux/amd64` and `linux/arm64`. Both are built and tested on native GitHub-hosted runners. Other operating systems and architectures are outside the support scope, even when a container runtime can emulate them.

The supported interface is the set of tools and runtime defaults checked by `scripts/verify-tools.sh`. Exact tool versions follow the repository's reviewed pins and lock files rather than this document.

## Image channels

| Reference | Intended use | Update policy |
| --- | --- | --- |
| `latest` | Current development environment | Rolling; rebuilt and updated regularly |
| `X.Y.Z` | Stable release checkpoint | Never intentionally moved after publication |
| `sha-*` | Traceability to a source commit | Not changed by scheduled refreshes; still mutable on a source-triggered rebuild |
| `@sha256:...` | Reproducible deployment or development environment | Immutable OCI reference |

GHCR (`ghcr.io/0nde/aws-archi`) is canonical and is required for every successful publication. Docker Hub (`haonde/aws-archi`) is a public mirror: normal rolling publication verifies it when available and reports a warning when it is temporarily unavailable, while a numbered release is not finalized until both registries expose the same verified digest. Consumers that need a single source of truth should prefer GHCR.

Release tags are checkpoints, not maintained branches. Security and dependency fixes reach `latest` after merge; a release user must adopt a newer patch release or digest to receive them.

## Getting help

- Use a GitHub issue for reproducible bugs, documentation errors and feature requests.
- Use GitHub Discussions only if the repository enables them in the future.
- Use private vulnerability reporting for security-sensitive reports.
- Consult upstream support for behavior that reproduces in an individual included tool outside this image.

This community project provides support on a best-effort basis and has no response-time or availability SLA.

## Compatibility changes

Routine dependency updates may change tool behavior while preserving the documented command-line surface. Breaking changes to the image contract, default user, supported architectures or major runtime generations require a documented release decision. Heavy or specialized tools should be delivered through optional profiles when possible rather than permanently expanding the core image.
