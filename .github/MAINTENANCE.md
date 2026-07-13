# Semi-automated pinned tool maintenance

The `Maintain pinned tools` workflow runs every Saturday and can also be started manually. It updates the pins that Dependabot cannot safely maintain, including every Docker base and frontend digest in the multi-stage Dockerfile, paired release versions and SHA-256 values, exact source commits, Go security overrides and bundled license notices.

The workflow only creates or refreshes the `bot/pinned-tool-updates` pull request. It never pushes to `main`, enables auto-merge, publishes a release or changes the pinned devcontainer digest.

## One-time credential setup

The workflow uses the protected `maintenance` environment, which only permits deployments from `main`. Create a fine-grained personal access token dedicated to this repository and store it as the `MAINTENANCE_TOKEN` environment secret, not as a general repository secret.

Configure the token with:

- repository access: only `0nde/aws-archi`;
- Contents: read and write;
- Pull requests: read and write;
- Metadata: read-only;
- an explicit expiration and a calendar reminder to rotate it.

Store the token without printing it:

```bash
gh secret set MAINTENANCE_TOKEN --repo 0nde/aws-archi --env maintenance
```

No Actions, Administration, Secrets, Packages or Workflows permission is required. The separate identity is necessary because GitHub intentionally suppresses workflow events caused by its built-in `GITHUB_TOKEN`; a pull request created with that token would not receive the normal pull-request validation runs.

## Review policy

Before merging an automated update:

1. Review upstream release notes and the version/checksum pairs in the Dockerfile.
2. Confirm that bundled third-party notices match the new versions.
3. Wait for `Analyze (actions)`, `Validate image (amd64)` and `Validate image (arm64)`.
4. Inspect the Trivy result inside both architecture validation jobs.
5. Merge manually using squash only.

Dependabot continues to manage GitHub Actions, npm dependencies and Python dependencies independently. The maintenance workflow manages all Docker digests because Dependabot does not support every `FROM` instruction in a multi-stage Dockerfile.

Runtime generation changes remain deliberate manual decisions. This includes moving to a new Node.js LTS line, Python or Go minor line, or Debian release. Release tags, published version numbers and the pinned devcontainer digest are also intentionally outside the maintenance workflow.

Scheduled and manually dispatched image builds bypass the BuildKit layer cache so Debian security packages are refreshed. Pull requests and source pushes continue to use the cache for fast validation.
