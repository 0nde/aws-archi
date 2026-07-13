from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update-pins.py"
SPEC = importlib.util.spec_from_file_location("update_pins", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT}")
UPDATE_PINS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UPDATE_PINS)


class FakeResponse:
    def __init__(self, digest: str = "", body: bytes = b""):
        self.headers = {"Docker-Content-Digest": digest}
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class UpdatePinsTests(unittest.TestCase):
    def isolated_repository(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        dockerfile = root / ".devcontainer" / "Dockerfile"
        notices = root / "THIRD_PARTY_NOTICES.md"
        licenses = root / "third_party_licenses"
        tool_versions = root / "tooling" / "tool-versions.conf"
        for source, destination in (
            (UPDATE_PINS.DOCKERFILE, dockerfile),
            (UPDATE_PINS.NOTICES, notices),
            (UPDATE_PINS.TOOL_VERSIONS, tool_versions),
        ):
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        shutil.copytree(UPDATE_PINS.LICENSES, licenses)
        return temporary, root, dockerfile, notices, licenses, tool_versions

    @staticmethod
    def dockerfile_arg(name: str) -> str:
        return UPDATE_PINS.arg(UPDATE_PINS.DOCKERFILE.read_text(encoding="utf-8"), name)

    @classmethod
    def current_release(cls, repository: str):
        versions = UPDATE_PINS.TOOL_VERSIONS.read_text(encoding="utf-8")
        cosign = UPDATE_PINS.env_version(versions, "COSIGN_VERSION")
        releases = {
            "terraform-linters/tflint": (f"v{cls.dockerfile_arg('TFLINT_VERSION')}", "unused", {}),
            "cli/cli": (f"v{cls.dockerfile_arg('GH_VERSION')}", "unused", {}),
            "gruntwork-io/terragrunt": (
                f"v{cls.dockerfile_arg('TERRAGRUNT_VERSION')}",
                cls.dockerfile_arg("TERRAGRUNT_COMMIT"),
                {},
            ),
            "terraform-docs/terraform-docs": (
                "v-current",
                cls.dockerfile_arg("TERRAFORM_DOCS_COMMIT"),
                {},
            ),
            "google/go-licenses": (f"v{cls.dockerfile_arg('GO_LICENSES_VERSION')}", "unused", {}),
            "sigstore/cosign": (f"v{cosign}", "unused", {}),
        }
        return releases[repository]

    @classmethod
    def current_api(cls, url: str):
        dockerfile = UPDATE_PINS.DOCKERFILE.read_text(encoding="utf-8")
        if url == "https://api.releases.hashicorp.com/v1/releases/terraform/latest":
            return {"version": cls.dockerfile_arg("TERRAFORM_VERSION"), "url_shasums": "unused"}
        if url == "https://registry.npmjs.org/npm/latest":
            return {"version": cls.dockerfile_arg("NPM_VERSION")}
        if "golang.org%2Fx%2Fcrypto" in url or "golang.org/x/crypto" in url:
            return {"Version": UPDATE_PINS.re.search(r"go get golang.org/x/crypto@(v[^ ]+)", dockerfile).group(1)}
        if "golang.org%2Fx%2Fnet" in url or "golang.org/x/net" in url:
            return {"Version": UPDATE_PINS.re.search(r"golang.org/x/net@(v[^ ]+)", dockerfile).group(1)}
        raise AssertionError(f"Unexpected API URL: {url}")

    @classmethod
    def current_head(cls, repository: str):
        heads = {
            "ohmyzsh/ohmyzsh": cls.dockerfile_arg("OH_MY_ZSH_COMMIT"),
            "zsh-users/zsh-autosuggestions": cls.dockerfile_arg("ZSH_AUTOSUGGESTIONS_COMMIT"),
            "zsh-users/zsh-syntax-highlighting": cls.dockerfile_arg("ZSH_SYNTAX_HIGHLIGHTING_COMMIT"),
        }
        return heads[repository]

    def test_github_accept_header_is_not_sent_to_other_registries(self):
        response = FakeResponse(body=b"{}")
        with (
            mock.patch.dict(UPDATE_PINS.os.environ, {"GH_TOKEN": "github-token"}, clear=True),
            mock.patch.object(UPDATE_PINS.urllib.request, "urlopen", return_value=response) as urlopen,
        ):
            UPDATE_PINS.request("https://registry.npmjs.org/npm/latest")
            npm_request = urlopen.call_args.args[0]
            UPDATE_PINS.request("https://api.github.com/repos/cli/cli")
            github_request = urlopen.call_args.args[0]

        self.assertIsNone(npm_request.get_header("Accept"))
        self.assertIsNone(npm_request.get_header("Authorization"))
        self.assertEqual("application/vnd.github+json", github_request.get_header("Accept"))
        self.assertEqual("Bearer github-token", github_request.get_header("Authorization"))

    def test_request_retries_a_transient_server_failure(self):
        failure = urllib.error.HTTPError(
            "https://example.test", 503, "unavailable", {"Retry-After": "0"}, None
        )
        response = FakeResponse(body=b"recovered")
        with (
            mock.patch.object(
                UPDATE_PINS.urllib.request,
                "urlopen",
                side_effect=[failure, response],
            ) as urlopen,
            mock.patch.object(UPDATE_PINS.time, "sleep") as sleep,
        ):
            actual = UPDATE_PINS.request("https://example.test")

        self.assertEqual(b"recovered", actual)
        self.assertEqual(2, urlopen.call_count)
        sleep.assert_called_once_with(0.0)

    def test_every_configured_docker_pin_matches_the_dockerfile(self):
        dockerfile = UPDATE_PINS.DOCKERFILE.read_text(encoding="utf-8")
        replacement = "b" * 64

        with mock.patch.object(UPDATE_PINS, "docker_hub_digest", return_value=replacement):
            for label, reference, repository in UPDATE_PINS.DOCKER_PINS:
                with self.subTest(label=label):
                    updated, change = UPDATE_PINS.update_docker_pin(
                        dockerfile, label, reference, repository
                    )
                    self.assertIn(f"{reference}@sha256:{replacement}", updated)
                    self.assertIsNotNone(change)

    def test_docker_hub_digest_uses_the_registry_digest_header(self):
        digest = "sha256:" + "a" * 64
        response = FakeResponse(digest)

        with (
            mock.patch.object(UPDATE_PINS, "api", return_value={"token": "registry-token"}),
            mock.patch.object(UPDATE_PINS.urllib.request, "urlopen", return_value=response) as urlopen,
        ):
            actual = UPDATE_PINS.docker_hub_digest("library/python", "3.14-slim-trixie")

        self.assertEqual("a" * 64, actual)
        request = urlopen.call_args.args[0]
        self.assertEqual("HEAD", request.get_method())
        self.assertEqual("Bearer registry-token", request.get_header("Authorization"))
        self.assertIn("application/vnd.oci.image.index.v1+json", request.get_header("Accept"))

    def test_latest_aws_cli_tag_checks_every_page(self):
        first_page = [{"name": f"2.1.{index}"} for index in range(100)]
        second_page = [
            {"name": "2.999.0"},
            {"name": "2.1000.0dev0"},
            {"name": "1.40.0"},
        ]

        with mock.patch.object(UPDATE_PINS, "api", side_effect=[first_page, second_page]) as api:
            latest = UPDATE_PINS.latest_aws_cli_tag()

        self.assertEqual("2.999.0", latest)
        self.assertEqual(2, api.call_count)
        self.assertIn("page=2", api.call_args_list[1].args[0])

    def test_notice_replacement_requires_exactly_one_match(self):
        self.assertEqual(
            "license-new",
            UPDATE_PINS.replace_literal_once("license-old", "old", "new", "notice"),
        )
        for content in ("missing", "old old"):
            with self.subTest(content=content):
                with self.assertRaises(RuntimeError):
                    UPDATE_PINS.replace_literal_once(content, "old", "new", "notice")

    def test_full_update_with_current_pins_does_not_rewrite_repository(self):
        temporary, root, dockerfile, notices, licenses, tool_versions = self.isolated_repository()
        self.addCleanup(temporary.cleanup)
        original_files = {
            path: path.read_bytes() for path in (dockerfile, notices, tool_versions)
        }
        original_licenses = sorted(
            path.relative_to(licenses) for path in licenses.rglob("*") if path.is_file()
        )
        with (
            mock.patch.object(UPDATE_PINS, "ROOT", root),
            mock.patch.object(UPDATE_PINS, "DOCKERFILE", dockerfile),
            mock.patch.object(UPDATE_PINS, "NOTICES", notices),
            mock.patch.object(UPDATE_PINS, "LICENSES", licenses),
            mock.patch.object(UPDATE_PINS, "TOOL_VERSIONS", tool_versions),
            mock.patch.object(UPDATE_PINS, "DOCKER_PINS", ()),
            mock.patch.object(UPDATE_PINS, "api", side_effect=self.current_api),
            mock.patch.object(UPDATE_PINS, "github_release", side_effect=self.current_release),
            mock.patch.object(
                UPDATE_PINS,
                "latest_aws_cli_tag",
                return_value=self.dockerfile_arg("AWS_CLI_VERSION"),
            ),
            mock.patch.object(UPDATE_PINS, "github_head", side_effect=self.current_head),
        ):
            changes = UPDATE_PINS.update()

        self.assertEqual([], changes)
        self.assertEqual(original_files, {path: path.read_bytes() for path in original_files})
        self.assertEqual(
            original_licenses,
            sorted(path.relative_to(licenses) for path in licenses.rglob("*") if path.is_file()),
        )

    def test_full_update_stages_license_and_notice_changes_together(self):
        temporary, root, dockerfile, notices, licenses, tool_versions = self.isolated_repository()
        self.addCleanup(temporary.cleanup)

        def api(url: str):
            if url == "https://api.releases.hashicorp.com/v1/releases/terraform/latest":
                return {"version": "99.99.99", "url_shasums": "https://example.test/SHA256SUMS"}
            return self.current_api(url)

        with (
            mock.patch.object(UPDATE_PINS, "ROOT", root),
            mock.patch.object(UPDATE_PINS, "DOCKERFILE", dockerfile),
            mock.patch.object(UPDATE_PINS, "NOTICES", notices),
            mock.patch.object(UPDATE_PINS, "LICENSES", licenses),
            mock.patch.object(UPDATE_PINS, "TOOL_VERSIONS", tool_versions),
            mock.patch.object(UPDATE_PINS, "DOCKER_PINS", ()),
            mock.patch.object(UPDATE_PINS, "api", side_effect=api),
            mock.patch.object(UPDATE_PINS, "github_release", side_effect=self.current_release),
            mock.patch.object(
                UPDATE_PINS,
                "latest_aws_cli_tag",
                return_value=self.dockerfile_arg("AWS_CLI_VERSION"),
            ),
            mock.patch.object(UPDATE_PINS, "github_head", side_effect=self.current_head),
            mock.patch.object(UPDATE_PINS, "checksum_file", return_value="a" * 64),
            mock.patch.object(UPDATE_PINS, "request", return_value=b"new license"),
        ):
            changes = UPDATE_PINS.update()

        old_terraform = self.dockerfile_arg("TERRAFORM_VERSION")
        self.assertIn(f"Terraform {old_terraform} -> 99.99.99", changes)
        self.assertIn("ARG TERRAFORM_VERSION=99.99.99", dockerfile.read_text(encoding="utf-8"))
        self.assertIn("terraform-99.99.99/LICENSE", notices.read_text(encoding="utf-8"))
        self.assertFalse((licenses / f"terraform-{old_terraform}").exists())
        self.assertEqual(
            b"new license", (licenses / "terraform-99.99.99" / "LICENSE").read_bytes()
        )

    def test_commit_updates_rolls_back_files_and_licenses_on_failure(self):
        temporary, root, dockerfile, _, licenses, _ = self.isolated_repository()
        self.addCleanup(temporary.cleanup)
        staged_licenses = root / "staged-licenses"
        shutil.copytree(licenses, staged_licenses)
        marker = staged_licenses / "rollback-marker"
        marker.write_text("new", encoding="utf-8")
        original_dockerfile = dockerfile.read_bytes()
        real_replace = UPDATE_PINS.os.replace
        failed = False

        def fail_staged_license_install(source, destination):
            nonlocal failed
            if (
                not failed
                and Path(source) == staged_licenses
                and Path(destination) == licenses
            ):
                failed = True
                raise OSError("simulated license installation failure")
            return real_replace(source, destination)

        with (
            mock.patch.object(UPDATE_PINS, "LICENSES", licenses),
            mock.patch.object(
                UPDATE_PINS.os, "replace", side_effect=fail_staged_license_install
            ),
            self.assertRaises(OSError),
        ):
            UPDATE_PINS.commit_updates(
                {dockerfile: dockerfile.read_text(encoding="utf-8") + "\n# changed\n"},
                staged_licenses,
            )

        self.assertEqual(original_dockerfile, dockerfile.read_bytes())
        self.assertTrue(licenses.is_dir())
        self.assertFalse((licenses / "rollback-marker").exists())


if __name__ == "__main__":
    unittest.main()
