# Contributing

This is a public repository. Issues and pull requests from the community are welcome, but only repository maintainers can merge changes into the protected `main` branch.

## Before opening a pull request

- Open an issue first for substantial behavior, tooling or compatibility changes.
- Never include credentials, private infrastructure details or unpatched vulnerability information.
- Report security issues privately as described in `SECURITY.md`.
- Keep changes focused and update the relevant documentation and tests.
- Avoid adding a tool to the core image when an optional Dev Container Feature or profile is sufficient.

## Validation

For Docker image changes, run the checks on the host's native architecture when practical:

```bash
docker buildx build --load -f .devcontainer/Dockerfile -t aws-archi:test .
docker run --rm -v "$PWD/scripts:/tests:ro" aws-archi:test bash /tests/verify-tools.sh
```

Run the updater tests independently:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p "test_*.py"
```

GitHub Actions validates `linux/amd64` and `linux/arm64` on native runners. Workflows from external forks require maintainer approval before they can access runner resources. Local cross-architecture builds may use emulation and are not required from contributors.

## Pull requests

- Explain what changed, why it changed and how it was verified.
- Link the related issue when one exists.
- Allow maintainers to edit the branch when appropriate.
- Resolve review conversations and keep required checks green.
- By contributing, you agree that your contribution is licensed under Apache-2.0.

Automated dependency pull requests follow the same validation and manual-merge policy as human contributions. See `.github/MAINTENANCE.md` for the division between maintenance and releases.
