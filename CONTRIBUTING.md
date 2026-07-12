# Contributing

Contributions are welcome through GitHub pull requests.

## Before opening a pull request

- Open an issue first for substantial behavior, tooling or compatibility changes.
- Never include credentials, private infrastructure details or unpatched vulnerability information.
- Report security issues privately as described in `SECURITY.md`.
- Keep changes focused and update the relevant documentation.

## Validation

For Docker image changes, run the local checks when practical:

```bash
docker buildx build --load --platform linux/amd64 -f .devcontainer/Dockerfile -t aws-archi:test .
docker run --rm -v "$PWD/scripts:/tests:ro" aws-archi:test bash /tests/verify-tools.sh
```

GitHub Actions validates both `linux/amd64` and `linux/arm64`. Workflows from external forks require maintainer approval before they run.

## Pull requests

- Explain what changed, why it changed and how it was verified.
- Link the related issue when one exists.
- Allow maintainers to edit the branch when appropriate.
- By contributing, you agree that your contribution is licensed under Apache-2.0.
