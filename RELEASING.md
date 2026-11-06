# Releasing

Numbered releases are deliberate checkpoints. Scheduled maintenance and merged dependency pull requests update the rolling image, but never choose a release number automatically.

The project uses two related naming conventions:

- Git tag and GitHub release: `vX.Y.Z`;
- container image tag: `X.Y.Z`.

Keeping the `v` on the Git object distinguishes source releases while preserving conventional container tags. Do not publish a duplicate `vX.Y.Z` container tag.

## Version policy

Use semantic versioning for the supported image contract:

- patch: compatible dependency refreshes, fixes and documentation corrections;
- minor: backward-compatible tools or capabilities added to the supported core;
- major: breaking changes to the default user, supported command surface, base runtime generations or compatibility policy.

The size of an upstream dependency update alone does not determine the project version. Review the effect on users.

## Release checklist

1. Start from a clean, current `main` branch and review all changes since the previous release.
2. Confirm the maintenance tests and native `amd64` and `arm64` image validations are green.
3. Run or inspect the latest forced-refresh build so the release does not immediately inherit stale operating-system packages.
4. Check the generated SBOM, provenance, license notices and vulnerability-gate result.
5. Choose the next version and create the signed Git tag `vX.Y.Z` on the reviewed commit.
6. Push the tag and wait for publication and post-publication verification to succeed. The workflow verifies the signed tag and its ancestry before building. It signs the staged index before applying the final registry tags and rejects an attempt to move an existing numbered tag to a different digest.
7. Confirm GHCR and Docker Hub resolve `X.Y.Z` to the expected multi-architecture image.
8. Run the release assistant with the version without the `v` prefix. It verifies the signed tag, binds both registry images to its commit, checks the supported architectures, SBOM, provenance and Cosign signatures, creates a GitHub-signed commit that updates every repository Dev Container pin, opens a normal pull request, and creates a draft GitHub release.
9. Review and merge the pin pull request, edit the generated release notes to include compatibility information and the immutable index digest, then publish the draft release manually.

Example commands, replacing the version before use:

```bash
git switch main
git pull --ff-only
git status --short
git tag -s vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
gh workflow run release-assistant.yml --ref main -f version=X.Y.Z
```

Do not run the release assistant until the image publication workflow for the tag has completed successfully. The assistant never creates or rewrites a release tag, publishes a release, or merges its pull request. It may safely refresh its own `release/vX.Y.Z` branch with lease protection when rerun. A failed publication is fixed in source and released with a new version; an already published release tag is never rewritten.

### Preproduction candidate

Dispatch the image workflow on the reviewed candidate branch with a tag such as `1.0.6-rc.1`. The workflow stages and validates both native platforms, signs the index and tags only the separate GHCR candidate package. The package may require GitHub authentication. Use the digest from the workflow summary to test the candidate.

```bash
gh workflow run image.yml --ref BRANCH -f candidate_tag=1.0.6-rc.1
docker pull ghcr.io/0nde/aws-archi-candidates@sha256:VERIFIED_INDEX_DIGEST
```

Restrict creation of `v*` Git tags to the authorized release identity in GitHub rulesets. The source check in the workflow cannot protect a run whose tagged commit replaces the workflow itself.

## Rollback

Immutable releases are not rolled back by retargeting tags. If a release is defective:

1. mark the GitHub release as affected and describe the impact;
2. fix the source through the protected pull-request path;
3. publish a new patch release;
4. advise users to move to the replacement release or its digest.

The rolling `latest` tag can advance to the repaired image after normal validation. Existing digests remain available for audit and incident analysis according to registry retention policy.

For immediate recovery, pin the consuming Dev Container or Docker configuration to the last verified digest from the preceding GitHub release and recreate the container. The named AWS configuration volume can be reused. Verify the selected digest and repeat the tool smoke tests after recreating the container.
