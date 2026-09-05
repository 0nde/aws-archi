# Security policy

## Supported versions

Security maintenance targets the rolling `latest` image first. A released `X.Y.Z` image is not modified in place; when a release needs a fix, the maintainer publishes a new patch release. Older tags and digests do not receive backports unless explicitly announced.

Use `latest` to receive ongoing rebuilds and dependency updates, or follow new releases while pinning a digest when strict immutability is required. See `SUPPORT.md` for the complete tag and compatibility policy.

No scanner result guarantees that an image is free of vulnerabilities. Reports should distinguish exploitable findings from packages that are present only as transitive or build-time dependencies.

## Automated checks

Every pull request requires successful native AMD64 and ARM64 image validation and CodeQL analysis of the repository's Python code and GitHub Actions. CodeQL merge protection blocks errors and high-or-higher security alerts. The explicit CodeQL workflow includes Dependabot pull requests.

Trivy blocks image validation and publication when it finds a **CRITICAL** vulnerability with an available fix. A separate complete report includes every vulnerability severity and findings without a reported fix. Each architecture's job summary links to JSON and text reports retained as workflow artifacts for 30 days, including when the vulnerability gate rejects the image. A green image gate therefore does not mean there are no high-severity or unpatched vulnerabilities. See [.github/MAINTENANCE.md](.github/MAINTENANCE.md#vulnerability-reports) for report locations and interpretation.

## Reporting a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/0nde/aws-archi/security/advisories/new) for suspected vulnerabilities. Do not open a public issue for an unpatched vulnerability or include credentials, tokens, private infrastructure details or exploit data in public discussions.

Include the affected registry reference and image digest, architecture, reproduction steps, expected impact and relevant scanner output. Reports will be acknowledged as soon as practical; no fixed response-time SLA is offered. Coordinated disclosure is preferred.

Never submit real AWS, GitHub or registry credentials as test data.
