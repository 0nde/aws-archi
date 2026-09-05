# Semi-automated maintenance

Scheduled maintenance and Dependabot propose narrowly scoped pull requests for dependencies and reviewed build pins. They never push to `main`, enable auto-merge, create a release, move a release tag or silently change the Dev Container's pinned digest.

The pinned-tool workflow creates its commits through GitHub's `createCommitOnBranch` API and verifies their signatures before opening or refreshing a pull request. This satisfies the signed-commit requirement on `main`. The signed commit is prepared on a temporary branch, then the bot branch is updated with an explicit lease so a concurrent branch update is not overwritten. The temporary branch is removed afterward; the open pull request keeps its review history throughout the refresh.

Maintenance and releases are intentionally separate:

- maintenance keeps the source and rolling image current;
- merging a maintenance PR publishes a new rolling image after validation;
- publishing a numbered release is an explicit maintainer decision documented in `RELEASING.md`.

## Credential setup

The pinned-tool workflow and release assistant use the protected `maintenance` environment, which only permits deployments from `main`. Store a fine-grained personal access token dedicated to this repository as the `MAINTENANCE_TOKEN` environment secret, not as a general repository secret.

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

Dependabot manages supported GitHub Actions, npm and Python dependencies. The custom updater manages build inputs that cannot be represented safely in those package ecosystems, including multi-stage Docker digests, paired release versions, source commits and checksums, the Rekor override used by source-built TFLint, selected Go dependencies, the Cosign and `go-licenses` tool pins, and bundled license notices.

The updater must change only values it can validate together. New pin formats require updater tests before they are treated as automated. Runtime-generation changes—such as a new Debian release or a new Python, Go or Node.js major line—remain deliberate design decisions.

The Go builder currently follows Go 1.27 because Terragrunt 1.1.4 requires it. This compiler is used only in build stages; the runtime remains Python 3.14 and Node.js 24 on Debian Trixie. When an upstream tool raises its minimum Go version, review its `go.mod`, then update the Dockerfile builder reference, its minimum-version check and `DOCKER_PINS` in `scripts/update-pins.py` together. Keep `GOTOOLCHAIN=local` so builds cannot silently download an unreviewed compiler.

## Reviewing an automated update

Before merging:

1. Read the generated summary and upstream release notes.
2. Confirm that versions, checksums, source commits and license notices changed together.
3. Wait for the required CodeQL Actions and Python analyses and both native architecture image validations. The `Protect main` ruleset also requires CodeQL results, with errors and high-or-higher security alerts blocking merge.
4. Inspect the critical-vulnerability gate and the complete vulnerability report for each architecture.
5. Merge manually using squash only.

The repository does not require the solo maintainer to approve their own pull request. If another person receives write access, enable at least one independent approval and CODEOWNERS enforcement before relying on collaborative auto-merge.

### Dependency and security labels

Dependabot and the pinned-tool updater apply `dependencies` to routine updates. The `security` label is reserved for a reviewed correction linked to a vulnerability alert, advisory or upstream security release. Maintainers apply it after checking that link; a new version alone does not establish a security fix. Dependabot security updates remain enabled independently of these labels. Labels do not authorize a merge or bypass any check.

### Vulnerability reports

Each native image validation and publication records every Trivy vulnerability severity, including findings without a reported fix. The job summary counts package findings by severity and whether a fixed version is available. The same vulnerability in two packages or targets counts twice.

Download the full `trivy.json`, readable `trivy.txt` and `summary.md` from the job summary link or the workflow's artifacts. Artifacts are named `vulnerabilities-pr-amd64` / `vulnerabilities-pr-arm64` for pull requests and `vulnerabilities-published-amd64` / `vulnerabilities-published-arm64` for publication. They are retained for 30 days and uploaded before the blocking check, so a rejected image still has a report to inspect. Publication reports describe the exact staged image digest that is tested before promotion.

The blocking policy remains fixable **CRITICAL** vulnerabilities. Other severities and findings without a fix remain visible for review; they are not silently accepted as harmless. A scanner or reporting failure fails validation instead of appearing as a clean report.

## Rebuilds and publication

Periodic and manually dispatched image builds refresh rolling operating-system packages even when the source commit has not changed. They update `latest` but deliberately do not retarget `sha-*` or numbered release tags. A source-triggered workflow rerun can still rebuild a `sha-*` alias, so only an image digest is an immutable reference.

The publication workflow builds on native `amd64` and `arm64` runners, publishes GHCR as the canonical registry, mirrors the result to Docker Hub, and verifies the final public artifacts. Build caches are an optimization only: forced refreshes must not export redundant full caches, and cache growth should be reviewed periodically.
