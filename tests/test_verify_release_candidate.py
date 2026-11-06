import os
import unittest
from unittest.mock import patch

from scripts.verify_release_candidate import (
    EXPECTED_DESCRIPTION,
    VerificationError,
    main,
    parse_args,
    resolve_tag_metadata,
    validate_attestations,
    validate_image_metadata,
    validate_manifest,
    validate_version,
    verify_signed_release_tag,
)


COMMIT = "a" * 40
DIGEST = "sha256:" + "b" * 64


class ReleaseCandidateValidationTests(unittest.TestCase):
    def test_verifies_the_signed_tag_on_main(self):
        ref = {"object": {"type": "tag", "sha": "c" * 40}}
        tag = {
            "tag": "v1.2.3",
            "verification": {"verified": True},
            "object": {"type": "commit", "sha": COMMIT},
        }
        with (
            patch("scripts.verify_release_candidate.run_json", side_effect=[ref, tag]),
            patch("scripts.verify_release_candidate.run") as run,
        ):
            self.assertEqual(verify_signed_release_tag("1.2.3", "owner/repo"), ("v1.2.3", COMMIT))
            run.assert_called_once_with(["git", "merge-base", "--is-ancestor", COMMIT, "origin/main"])

    def test_source_only_binds_the_signed_tag_to_the_push(self):
        argv = ["--source-only", "--version", "1.2.3", "--repository", "owner/repo", "--expected-commit", COMMIT]
        for ref, event_sha, tag_commit, status in (
            ("refs/tags/v1.2.3", COMMIT, COMMIT, 0),
            ("refs/heads/v1.2.3", COMMIT, COMMIT, 1),
            ("refs/tags/v1.2.4", COMMIT, COMMIT, 1),
            ("refs/tags/v1.2.3", "b" * 40, COMMIT, 1),
            ("refs/tags/v1.2.3", COMMIT, "b" * 40, 1),
        ):
            with (
                self.subTest(ref=ref, event_sha=event_sha, tag_commit=tag_commit),
                patch.dict(os.environ, {"GH_TOKEN": "test", "GITHUB_REF": ref, "GITHUB_SHA": event_sha}),
                patch("scripts.verify_release_candidate.sys.argv", ["verify-release", *argv]),
                patch("scripts.verify_release_candidate.verify_signed_release_tag", return_value=("v1.2.3", tag_commit)),
                patch("scripts.verify_release_candidate.verify_release_candidate") as verify_image,
                patch("builtins.print"),
            ):
                self.assertEqual(main(), status)
                verify_image.assert_not_called()

    def test_source_only_requires_a_commit_and_rejects_image_options(self):
        argv = ["--source-only", "--version", "1.2.3", "--repository", "owner/repo"]
        for extras in ([], ["--expected-commit", "main"], ["--expected-commit", COMMIT, "--github-env", "env"]):
            with self.subTest(extras=extras), patch("argparse.ArgumentParser.error", side_effect=SystemExit(2)):
                with self.assertRaises(SystemExit):
                    parse_args(argv + extras)

    def test_accepts_a_signed_annotated_tag(self):
        ref = {"object": {"type": "tag", "sha": "c" * 40}}
        tag = {
            "tag": "v1.2.3",
            "verification": {"verified": True},
            "object": {"type": "commit", "sha": COMMIT},
        }
        self.assertEqual(resolve_tag_metadata(ref, tag, "v1.2.3"), COMMIT)

    def test_rejects_a_lightweight_or_unsigned_tag(self):
        with self.assertRaisesRegex(VerificationError, "annotated, signed"):
            resolve_tag_metadata({"object": {"type": "commit", "sha": COMMIT}}, {}, "v1.2.3")

        ref = {"object": {"type": "tag", "sha": "c" * 40}}
        tag = {
            "tag": "v1.2.3",
            "verification": {"verified": False},
            "object": {"type": "commit", "sha": COMMIT},
        }
        with self.assertRaisesRegex(VerificationError, "signature verified"):
            resolve_tag_metadata(ref, tag, "v1.2.3")

    def test_requires_a_stable_semantic_version(self):
        self.assertEqual(validate_version("1.2.3"), "v1.2.3")
        for invalid in ("01.2.3", "1.2.3-rc.1", "1.2.3.foo", "v1.2.3"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(VerificationError):
                    validate_version(invalid)

    def test_requires_exactly_the_two_supported_platforms(self):
        manifest = {
            "digest": DIGEST,
            "annotations": {
                "org.opencontainers.image.description": EXPECTED_DESCRIPTION,
            },
            "manifests": [
                {"platform": {"os": "linux", "architecture": "amd64"}},
                {"platform": {"os": "linux", "architecture": "arm64"}},
                {"platform": {"os": "unknown", "architecture": "unknown"}},
            ],
        }
        self.assertEqual(validate_manifest(manifest), DIGEST)
        manifest["manifests"].pop(1)
        with self.assertRaisesRegex(VerificationError, "exactly"):
            validate_manifest(manifest)

        manifest["manifests"].append(
            {"platform": {"os": "linux", "architecture": "arm64"}}
        )
        manifest["manifests"].append(
            {"platform": {"os": "windows", "architecture": "amd64"}}
        )
        with self.assertRaisesRegex(VerificationError, "exactly"):
            validate_manifest(manifest)

    def test_rejects_a_registry_digest_mismatch(self):
        manifest = {
            "digest": DIGEST,
            "annotations": {
                "org.opencontainers.image.description": EXPECTED_DESCRIPTION,
            },
            "manifests": [
                {"platform": {"os": "linux", "architecture": "amd64"}},
                {"platform": {"os": "linux", "architecture": "arm64"}},
            ],
        }
        with self.assertRaisesRegex(VerificationError, "canonical digest"):
            validate_manifest(manifest, "sha256:" + "d" * 64)

    def test_requires_the_multi_architecture_description(self):
        manifest = {
            "digest": DIGEST,
            "manifests": [
                {"platform": {"os": "linux", "architecture": "amd64"}},
                {"platform": {"os": "linux", "architecture": "arm64"}},
            ],
        }
        with self.assertRaisesRegex(VerificationError, "description"):
            validate_manifest(manifest)

    def test_binds_image_labels_to_the_tag_commit(self):
        image = {
            "config": {
                "Labels": {
                    "org.opencontainers.image.revision": COMMIT,
                    "org.opencontainers.image.version": "1.2.3",
                    "org.opencontainers.image.source": "https://github.com/0nde/aws-archi",
                }
            }
        }
        validate_image_metadata(image, COMMIT, "1.2.3")
        image["config"]["Labels"]["org.opencontainers.image.revision"] = "e" * 40
        with self.assertRaisesRegex(VerificationError, "revision"):
            validate_image_metadata(image, COMMIT, "1.2.3")

    def test_requires_non_empty_sbom_and_slsa_provenance(self):
        sbom = {"SPDX": {"spdxVersion": "SPDX-2.3", "packages": [{"name": "image"}]}}
        provenance = {
            "SLSA": {
                "buildDefinition": {"buildType": "https://mobyproject.org/buildkit@v1"},
                "runDetails": {"builder": {"id": "https://github.com/0nde/aws-archi"}},
            }
        }
        validate_attestations(sbom, provenance)
        with self.assertRaisesRegex(VerificationError, "SBOM"):
            validate_attestations({"SPDX": {"packages": []}}, provenance)
        with self.assertRaisesRegex(VerificationError, "provenance"):
            validate_attestations(sbom, {"SLSA": {}})


if __name__ == "__main__":
    unittest.main()
