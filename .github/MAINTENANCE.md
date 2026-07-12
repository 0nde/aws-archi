# Semi-automated pinned tool maintenance

The `Maintain pinned tools` workflow runs every Saturday and can also be started manually. It updates the pins that Dependabot cannot safely maintain, including paired release versions and SHA-256 values, exact source commits, Go security overrides and bundled license notices.

The workflow only creates or refreshes the `bot/pinned-tool-updates` pull request. It never pushes to `main`, enables auto-merge, publishes a release or changes the pinned devcontainer digest.

## One-time credential setup

Create a fine-grained personal access token dedicated to this repository and store it as the Actions repository secret `MAINTENANCE_TOKEN`.

Configure the token with:

- repository access: only `0nde/aws-archi`;
- Contents: read and write;
- Pull requests: read and write;
- Metadata: read-only;
- an explicit expiration and a calendar reminder to rotate it.

No Actions, Administration, Secrets, Packages or Workflows permission is required. The separate identity is necessary because GitHub intentionally suppresses workflow events caused by its built-in `GITHUB_TOKEN`; a pull request created with that token would not receive the normal pull-request validation runs.

## Review policy

Before merging an automated update:

1. Review upstream release notes and the version/checksum pairs in the Dockerfile.
2. Confirm that bundled third-party notices match the new versions.
3. Wait for `Analyze (actions)`, `Validate image (amd64)` and `Validate image (arm64)`.
4. Inspect the Trivy result inside both architecture validation jobs.
5. Merge manually using squash only.

Dependabot continues to manage Docker base image digests, GitHub Actions, npm dependencies and Python dependencies independently.
