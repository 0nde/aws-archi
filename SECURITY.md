# Security policy

## Supported versions

Security maintenance targets the rolling `latest` image first. A released `X.Y.Z` image is not modified in place; when a release needs a fix, the maintainer publishes a new patch release. Older tags and digests do not receive backports unless explicitly announced.

Use `latest` to receive ongoing rebuilds and dependency updates, or follow new releases while pinning a digest when strict immutability is required. See `SUPPORT.md` for the complete tag and compatibility policy.

No scanner result guarantees that an image is free of vulnerabilities. Reports should distinguish exploitable findings from packages that are present only as transitive or build-time dependencies.

## Reporting a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/0nde/aws-archi/security/advisories/new) for suspected vulnerabilities. Do not open a public issue for an unpatched vulnerability or include credentials, tokens, private infrastructure details or exploit data in public discussions.

Include the affected registry reference and image digest, architecture, reproduction steps, expected impact and relevant scanner output. Reports will be acknowledged as soon as practical; no fixed response-time SLA is offered. Coordinated disclosure is preferred.

Never submit real AWS, GitHub or registry credentials as test data.
