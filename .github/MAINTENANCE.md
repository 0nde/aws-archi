# Semi-automated maintenance

Scheduled maintenance and Dependabot propose narrowly scoped pull requests for dependencies and reviewed build pins. They never push to `main`, enable auto-merge, create a release, move a release tag or silently change the Dev Container's pinned digest.

Maintenance and releases are intentionally separate:

- maintenance keeps the source and rolling image current;
- merging a maintenance PR publishes a new rolling image after validation;
- publishing a numbered release is an explicit maintainer decision documented in `RELEASING.md`.

## Credential setup

The pinned-tool workflow uses the protected `maintenance` environment, which only permits deployments from `main`. Store a fine-grained personal access token dedicated to this repository as the `MAINTENANCE_TOKEN` environment secret, not as a general repository secret.

Configure the token with:

- repository access: only `0nde/aws-archi`;
- Contents: read and write;
- Pull requests: read and write;
- Metadata: read-only;
- an explicit expiration and an external reminder to rotate it.

Store the token without printing it:

```bash
gh secret set MAINTENANCE_TOKEN --repo 0nde/aws-archi --env maintenance
```

No Actions, Administration, Secrets, Packages or Workflows permission is required. A separate token is necessary because GitHub intentionally suppresses most workflow events caused by its built-in `GITHUB_TOKEN`; normal pull-request validation must still run on an updater-created PR.

Token rotation is the one intentionally manual infrastructure task. If the token expires, the maintenance workflow must fail visibly rather than bypassing branch protection.

## Responsibilities

Dependabot manages supported GitHub Actions, npm and Python dependencies. The custom updater manages build inputs that cannot be represented safely in those package ecosystems, including multi-stage Docker digests, paired release versions and checksums, source commits, selected Go dependencies, the Cosign and `go-licenses` tool pins, and bundled license notices.

The updater must change only values it can validate together. New pin formats require updater tests before they are treated as automated. Runtime-generation changes—such as a new Debian release or a new Python, Go or Node.js major line—remain deliberate design decisions.

## Reviewing an automated update

Before merging:

1. Read the generated summary and upstream release notes.
2. Confirm that versions, checksums, source commits and license notices changed together.
3. Wait for the Actions analysis and both native architecture image validations.
4. Inspect the critical-vulnerability gate for each architecture.
5. Merge manually using squash only.

The repository does not require the solo maintainer to approve their own pull request. If another person receives write access, enable at least one independent approval and CODEOWNERS enforcement before relying on collaborative auto-merge.

## Rebuilds and publication

Periodic and manually dispatched image builds refresh rolling operating-system packages even when the source commit has not changed. They update `latest` but deliberately do not retarget `sha-*` or numbered release tags. A source-triggered workflow rerun can still rebuild a `sha-*` alias, so only an image digest is an immutable reference.

The publication workflow builds on native `amd64` and `arm64` runners, publishes GHCR as the canonical registry, mirrors the result to Docker Hub, and verifies the final public artifacts. Build caches are an optimization only: forced refreshes must not export redundant full caches, and cache growth should be reviewed periodically.
