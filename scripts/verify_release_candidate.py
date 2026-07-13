#!/usr/bin/env python3
"""Verify that a numbered image is the signed artifact of a signed Git tag."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_PLATFORMS = [("linux", "amd64"), ("linux", "arm64")]
EXPECTED_SOURCE = "https://github.com/0nde/aws-archi"


class VerificationError(RuntimeError):
    """Raised when the release candidate violates an integrity invariant."""


def require(condition: bool, message: str) -> None:
    """Reject a violated release integrity invariant."""
    if not condition:
        raise VerificationError(message)


def run(command: Sequence[str]) -> str:
    """Run a command and return its UTF-8 output or a safe failure."""
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise VerificationError(f"{command[0]} failed: {detail or 'unknown error'}")
    return completed.stdout


def run_json(command: Sequence[str]) -> Any:
    """Run a command whose output must be valid JSON."""
    output = run(command)
    try:
        return json.loads(output)
    except json.JSONDecodeError as error:
        raise VerificationError(f"{command[0]} returned invalid JSON") from error


def validate_version(version: str) -> str:
    """Validate a stable semantic version and return its Git tag."""
    require(
        VERSION_RE.fullmatch(version) is not None,
        "Version must be a stable semantic version without the v prefix",
    )
    return f"v{version}"


def resolve_tag_metadata(ref: Any, tag_object: Any, expected_tag: str) -> str:
    """Return the commit from a matching GitHub-verified annotated tag."""
    require(isinstance(ref, dict), "Git tag reference is invalid")
    ref_object = ref.get("object")
    require(isinstance(ref_object, dict), "Git tag reference has no target")
    require(
        ref_object.get("type") == "tag",
        f"{expected_tag} must be an annotated, signed tag",
    )

    require(isinstance(tag_object, dict), "Annotated Git tag object is invalid")
    require(tag_object.get("tag") == expected_tag, "Annotated Git tag name does not match")
    verification = tag_object.get("verification")
    require(
        isinstance(verification, dict) and verification.get("verified") is True,
        f"{expected_tag} does not have a signature verified by GitHub",
    )
    target = tag_object.get("object")
    require(
        isinstance(target, dict) and target.get("type") == "commit",
        f"{expected_tag} must point directly to a commit",
    )
    commit = target.get("sha")
    require(
        isinstance(commit, str) and COMMIT_RE.fullmatch(commit) is not None,
        "Tag commit is invalid",
    )
    return commit


def validate_manifest(manifest: Any, expected_digest: str | None = None) -> str:
    """Validate an OCI index digest and its exact supported platforms."""
    require(isinstance(manifest, dict), "OCI manifest is invalid")
    digest = manifest.get("digest")
    require(
        isinstance(digest, str) and DIGEST_RE.fullmatch(digest) is not None,
        "OCI digest is invalid",
    )
    if expected_digest is not None:
        require(digest == expected_digest, "Registry digest does not match the canonical digest")

    entries = manifest.get("manifests")
    require(isinstance(entries, list), "OCI index does not contain platform manifests")
    platforms = []
    for entry in entries:
        platform = entry.get("platform") if isinstance(entry, dict) else None
        require(isinstance(platform, dict), "OCI platform metadata is invalid")
        operating_system = platform.get("os")
        architecture = platform.get("architecture")
        if (operating_system, architecture) == ("unknown", "unknown"):
            continue
        require(isinstance(operating_system, str), "OCI platform OS is invalid")
        require(isinstance(architecture, str), "OCI platform architecture is invalid")
        platforms.append((operating_system, architecture))
    platforms.sort()
    require(
        platforms == EXPECTED_PLATFORMS,
        "OCI index must contain exactly linux/amd64 and linux/arm64",
    )
    return digest


def validate_image_metadata(image: Any, commit: str, version: str) -> None:
    """Bind platform OCI labels to the requested version and tag commit."""
    require(isinstance(image, dict), "Platform image metadata is invalid")
    config = image.get("config")
    labels = config.get("Labels") if isinstance(config, dict) else None
    require(isinstance(labels, dict), "Platform image has no OCI labels")
    require(
        labels.get("org.opencontainers.image.revision") == commit,
        "Image revision does not match the Git tag commit",
    )
    require(
        labels.get("org.opencontainers.image.version") == version,
        "Image version label does not match the release",
    )
    require(
        labels.get("org.opencontainers.image.source") == EXPECTED_SOURCE,
        "Image source label is invalid",
    )


def validate_attestations(sbom: Any, provenance: Any) -> None:
    """Require a non-empty SPDX SBOM and SLSA provenance."""
    spdx = sbom.get("SPDX") if isinstance(sbom, dict) else None
    require(
        isinstance(spdx, dict)
        and bool(spdx.get("spdxVersion"))
        and isinstance(spdx.get("packages"), list)
        and bool(spdx["packages"]),
        "Platform SBOM is missing or empty",
    )

    slsa = provenance.get("SLSA") if isinstance(provenance, dict) else None
    build_definition = slsa.get("buildDefinition") if isinstance(slsa, dict) else None
    run_details = slsa.get("runDetails") if isinstance(slsa, dict) else None
    builder = run_details.get("builder") if isinstance(run_details, dict) else None
    require(
        isinstance(build_definition, dict)
        and bool(build_definition.get("buildType"))
        and isinstance(builder, dict)
        and bool(builder.get("id")),
        "Platform SLSA provenance is missing",
    )


def inspect(reference: str, template: str) -> Any:
    """Read structured registry metadata through Buildx."""
    return run_json(
        ["docker", "buildx", "imagetools", "inspect", reference, "--format", template]
    )


def verify_registry(
    repository: str,
    digest: str,
    commit: str,
    version: str,
    certificate_identity: str,
) -> None:
    """Verify one registry copy, its metadata, attestations, and signature."""
    reference = f"{repository}@{digest}"
    validate_manifest(inspect(reference, "{{json .Manifest}}"), digest)

    for platform in ("linux/amd64", "linux/arm64"):
        image = inspect(reference, f'{{{{json (index .Image "{platform}")}}}}')
        validate_image_metadata(image, commit, version)
        sbom = inspect(reference, f'{{{{json (index .SBOM "{platform}")}}}}')
        provenance = inspect(reference, f'{{{{json (index .Provenance "{platform}")}}}}')
        validate_attestations(sbom, provenance)

    run(
        [
            "cosign",
            "verify",
            reference,
            "--certificate-identity",
            certificate_identity,
            "--certificate-oidc-issuer",
            "https://token.actions.githubusercontent.com",
        ]
    )


def verify_release_candidate(
    version: str,
    repository: str,
    canonical_image: str,
    mirror_image: str,
) -> tuple[str, str, str]:
    """Verify and bind the complete release candidate across both registries."""
    tag = validate_version(version)
    ref = run_json(["gh", "api", f"repos/{repository}/git/ref/tags/{tag}"])
    tag_sha = ref.get("object", {}).get("sha") if isinstance(ref, dict) else None
    require(
        isinstance(tag_sha, str) and COMMIT_RE.fullmatch(tag_sha) is not None,
        "Annotated tag object is invalid",
    )
    tag_object = run_json(["gh", "api", f"repos/{repository}/git/tags/{tag_sha}"])
    commit = resolve_tag_metadata(ref, tag_object, tag)

    run(["git", "merge-base", "--is-ancestor", commit, "origin/main"])

    canonical_manifest = inspect(f"{canonical_image}:{version}", "{{json .Manifest}}")
    digest = validate_manifest(canonical_manifest)
    mirror_manifest = inspect(f"{mirror_image}:{version}", "{{json .Manifest}}")
    validate_manifest(mirror_manifest, digest)

    identity = (
        f"https://github.com/{repository}/.github/workflows/image.yml@refs/tags/{tag}"
    )
    verify_registry(canonical_image, digest, commit, version, identity)
    verify_registry(mirror_image, digest, commit, version, identity)
    return tag, commit, digest


def parse_args() -> argparse.Namespace:
    """Parse the workflow-facing command-line interface."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--canonical-image", required=True)
    parser.add_argument("--mirror-image", required=True)
    parser.add_argument("--github-env", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    """Verify a candidate and export its immutable release metadata."""
    args = parse_args()
    try:
        require(bool(os.environ.get("GH_TOKEN")), "MAINTENANCE_TOKEN is missing")
        tag, commit, digest = verify_release_candidate(
            args.version,
            args.repository,
            args.canonical_image,
            args.mirror_image,
        )
        with args.github_env.open("a", encoding="utf-8") as environment:
            environment.write(f"TAG={tag}\nTAG_COMMIT={commit}\nDIGEST={digest}\n")
        print(f"Verified {tag}: {digest} ({commit})")
        return 0
    except VerificationError as error:
        print(f"Release candidate verification failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
