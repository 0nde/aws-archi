from __future__ import annotations

import io
import importlib.util
import shutil
import tempfile
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update-pins.py"
SPEC = importlib.util.spec_from_file_location("update_pins", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT}")
UPDATE_PINS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UPDATE_PINS)

# Short but recognisable stand-ins for the redistributed license texts. They only
# need the markers the updater checks, not the full legal text.
LICENSE_TEXTS = {
    "Apache-2.0": b"Apache License\nVersion 2.0, January 2004\n",
    "BUSL-1.1": b'Business Source License 1.1\n\n"Business Source License" is a trademark.\n',
    "MIT": b"MIT License\n\nCopyright (c) 2026 Example\n",
    "MPL-2.0": b"Mozilla Public License, version 2.0\n\n1. Definitions\n",
}
# Upstream layout the updater is expected to read, including the neighbouring
# `terraform/LICENSE` file that carries MPL-2.0 text and must never be written
# to `LICENSE-BUSL`.
UPSTREAM_LICENSES = {
    "hashicorp/terraform": {"LICENSE": "BUSL-1.1"},
    "terraform-linters/tflint": {
        "LICENSE": "MPL-2.0",
        "LICENSE-BUSL": "BUSL-1.1",
        "terraform/LICENSE": "MPL-2.0",
        "terraform/LICENSE-BUSL": "BUSL-1.1",
    },
    "cli/cli": {"LICENSE": "MIT"},
    "gruntwork-io/terragrunt": {"LICENSE.txt": "MIT"},
    "terraform-docs/terraform-docs": {"LICENSE": "MIT"},
    "aws/aws-cli": {"LICENSE.txt": "Apache-2.0"},
}
RAW_PREFIX = "https://raw.githubusercontent.com/"


class FakeUpstream:
    """Serve deterministic upstream payloads and record every requested URL."""

    def __init__(
        self,
        *,
        archive: bytes | None = None,
        overrides: dict[str, bytes | None] | None = None,
    ):
        self.archive = archive
        self.overrides = overrides or {}
        self.urls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.urls.append(url)
        if url.endswith(".zip") and self.archive is not None:
            return self.archive
        if not url.startswith(RAW_PREFIX):
            raise AssertionError(f"Unexpected request URL: {url}")
        owner, repository_name, _ref, path = url[len(RAW_PREFIX) :].split("/", 3)
        repository = f"{owner}/{repository_name}"
        if path in self.overrides:
            payload = self.overrides[path]
            if payload is None:
                raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
            return payload
        license_id = UPSTREAM_LICENSES.get(repository, {}).get(path)
        if license_id is None:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return LICENSE_TEXTS[license_id]

    def paths(self, repository: str) -> list[str]:
        prefix = f"{RAW_PREFIX}{repository}/"
        return [
            url[len(prefix) :].split("/", 1)[1]
            for url in self.urls
            if url.startswith(prefix)
        ]


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
            (UPDATE_PINS.ROOT / "LICENSE", root / "LICENSE"),
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
            "hashicorp/terraform": (
                f"v{cls.dockerfile_arg('TERRAFORM_VERSION')}",
                cls.dockerfile_arg("TERRAFORM_COMMIT"),
                {},
            ),
            "terraform-linters/tflint": (
                f"v{cls.dockerfile_arg('TFLINT_VERSION')}",
                cls.dockerfile_arg("TFLINT_COMMIT"),
                {},
            ),
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
        if url == "https://registry.npmjs.org/npm/latest":
            return {"version": cls.dockerfile_arg("NPM_VERSION")}
        if url == "https://proxy.golang.org/github.com/sigstore/rekor/@latest":
            return {"Version": f"v{cls.dockerfile_arg('TFLINT_REKOR_VERSION')}"}
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

    def test_license_files_have_exactly_one_terminal_newline(self):
        with tempfile.TemporaryDirectory() as temporary:
            licenses = Path(temporary)
            current = licenses / "component-1.0"
            current.mkdir()
            (current / "LICENSE").write_bytes(b"old license\n")

            UPDATE_PINS.write_license_dir(
                licenses,
                "component",
                "2.0",
                {"LICENSE": b"new license\r\n\r\n"},
            )

            self.assertFalse(current.exists())
            self.assertEqual(
                b"new license\n",
                (licenses / "component-2.0" / "LICENSE").read_bytes(),
            )

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

        def github_release(repository: str):
            if repository == "hashicorp/terraform":
                return "v99.99.99", "f" * 40, {}
            return self.current_release(repository)

        upstream = FakeUpstream()
        with (
            mock.patch.object(UPDATE_PINS, "ROOT", root),
            mock.patch.object(UPDATE_PINS, "DOCKERFILE", dockerfile),
            mock.patch.object(UPDATE_PINS, "NOTICES", notices),
            mock.patch.object(UPDATE_PINS, "LICENSES", licenses),
            mock.patch.object(UPDATE_PINS, "TOOL_VERSIONS", tool_versions),
            mock.patch.object(UPDATE_PINS, "DOCKER_PINS", ()),
            mock.patch.object(UPDATE_PINS, "api", side_effect=self.current_api),
            mock.patch.object(UPDATE_PINS, "github_release", side_effect=github_release),
            mock.patch.object(
                UPDATE_PINS,
                "latest_aws_cli_tag",
                return_value=self.dockerfile_arg("AWS_CLI_VERSION"),
            ),
            mock.patch.object(UPDATE_PINS, "github_head", side_effect=self.current_head),
            mock.patch.object(UPDATE_PINS, "request", side_effect=upstream),
        ):
            changes = UPDATE_PINS.update()

        old_terraform = self.dockerfile_arg("TERRAFORM_VERSION")
        self.assertIn(f"Terraform {old_terraform} -> 99.99.99", changes)
        self.assertIn("ARG TERRAFORM_VERSION=99.99.99", dockerfile.read_text(encoding="utf-8"))
        self.assertIn(f"ARG TERRAFORM_COMMIT={'f' * 40}", dockerfile.read_text(encoding="utf-8"))
        self.assertIn("terraform-99.99.99/LICENSE", notices.read_text(encoding="utf-8"))
        self.assertFalse((licenses / f"terraform-{old_terraform}").exists())
        self.assertEqual(
            LICENSE_TEXTS["BUSL-1.1"],
            (licenses / "terraform-99.99.99" / "LICENSE").read_bytes(),
        )

    def test_aws_cli_update_uses_repository_apache_license(self):
        temporary, root, dockerfile, notices, licenses, tool_versions = (
            self.isolated_repository()
        )
        self.addCleanup(temporary.cleanup)
        for apache_license in licenses.glob("aws-cli-*/APACHE-2.0.txt"):
            apache_license.unlink()

        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("aws/THIRD_PARTY_LICENSES", b"updated third-party licenses")

        upstream = FakeUpstream(archive=archive.getvalue())

        with (
            mock.patch.object(UPDATE_PINS, "ROOT", root),
            mock.patch.object(UPDATE_PINS, "DOCKERFILE", dockerfile),
            mock.patch.object(UPDATE_PINS, "NOTICES", notices),
            mock.patch.object(UPDATE_PINS, "LICENSES", licenses),
            mock.patch.object(UPDATE_PINS, "TOOL_VERSIONS", tool_versions),
            mock.patch.object(UPDATE_PINS, "DOCKER_PINS", ()),
            mock.patch.object(UPDATE_PINS, "api", side_effect=self.current_api),
            mock.patch.object(UPDATE_PINS, "github_release", side_effect=self.current_release),
            mock.patch.object(UPDATE_PINS, "latest_aws_cli_tag", return_value="2.99.0"),
            mock.patch.object(UPDATE_PINS, "github_head", side_effect=self.current_head),
            mock.patch.object(UPDATE_PINS, "request", side_effect=upstream),
        ):
            changes = UPDATE_PINS.update()

        destination = licenses / "aws-cli-2.99.0"
        self.assertIn(
            f"AWS CLI {self.dockerfile_arg('AWS_CLI_VERSION')} -> 2.99.0",
            changes,
        )
        self.assertEqual(
            (root / "LICENSE").read_bytes().rstrip(b"\r\n") + b"\n",
            (destination / "APACHE-2.0.txt").read_bytes(),
        )
        self.assertEqual(
            b"updated third-party licenses\n",
            (destination / "THIRD_PARTY_LICENSES").read_bytes(),
        )

    def test_source_built_go_tools_have_immutable_source_pins(self):
        dockerfile = UPDATE_PINS.DOCKERFILE.read_text(encoding="utf-8")
        for name in ("TERRAFORM_COMMIT", "TFLINT_COMMIT"):
            with self.subTest(name=name):
                self.assertRegex(UPDATE_PINS.arg(dockerfile, name), r"^[0-9a-f]{40}$")
        self.assertNotIn("TERRAFORM_SHA256_", dockerfile)
        self.assertNotIn("TFLINT_SHA256_", dockerfile)

    def test_full_update_tracks_tflint_source_and_rekor_together(self):
        temporary, root, dockerfile, notices, licenses, tool_versions = self.isolated_repository()
        self.addCleanup(temporary.cleanup)

        def github_release(repository: str):
            if repository == "terraform-linters/tflint":
                return "v99.88.77", "e" * 40, {}
            return self.current_release(repository)

        def api(url: str):
            if url == "https://proxy.golang.org/github.com/sigstore/rekor/@latest":
                return {"Version": "v1.5.99"}
            return self.current_api(url)

        upstream = FakeUpstream()
        with (
            mock.patch.object(UPDATE_PINS, "ROOT", root),
            mock.patch.object(UPDATE_PINS, "DOCKERFILE", dockerfile),
            mock.patch.object(UPDATE_PINS, "NOTICES", notices),
            mock.patch.object(UPDATE_PINS, "LICENSES", licenses),
            mock.patch.object(UPDATE_PINS, "TOOL_VERSIONS", tool_versions),
            mock.patch.object(UPDATE_PINS, "DOCKER_PINS", ()),
            mock.patch.object(UPDATE_PINS, "api", side_effect=api),
            mock.patch.object(UPDATE_PINS, "github_release", side_effect=github_release),
            mock.patch.object(
                UPDATE_PINS,
                "latest_aws_cli_tag",
                return_value=self.dockerfile_arg("AWS_CLI_VERSION"),
            ),
            mock.patch.object(UPDATE_PINS, "github_head", side_effect=self.current_head),
            mock.patch.object(UPDATE_PINS, "request", side_effect=upstream),
        ):
            changes = UPDATE_PINS.update()

        updated = dockerfile.read_text(encoding="utf-8")
        self.assertIn("TFLint", " ".join(changes))
        self.assertIn("ARG TFLINT_VERSION=99.88.77", updated)
        self.assertIn(f"ARG TFLINT_COMMIT={'e' * 40}", updated)
        self.assertIn("ARG TFLINT_REKOR_VERSION=1.5.99", updated)
        self.assertIn("tflint-99.88.77/", notices.read_text(encoding="utf-8"))
        self.assertTrue((licenses / "tflint-99.88.77" / "LICENSE").is_file())

    def tflint_update(self, upstream: FakeUpstream):
        """Run a TFLint-only pin update against a fake upstream."""

        temporary, root, dockerfile, notices, licenses, tool_versions = self.isolated_repository()
        self.addCleanup(temporary.cleanup)
        old_version = self.dockerfile_arg("TFLINT_VERSION")

        def github_release(repository: str):
            if repository == "terraform-linters/tflint":
                return "v99.88.77", "e" * 40, {}
            return self.current_release(repository)

        with (
            mock.patch.object(UPDATE_PINS, "ROOT", root),
            mock.patch.object(UPDATE_PINS, "DOCKERFILE", dockerfile),
            mock.patch.object(UPDATE_PINS, "NOTICES", notices),
            mock.patch.object(UPDATE_PINS, "LICENSES", licenses),
            mock.patch.object(UPDATE_PINS, "TOOL_VERSIONS", tool_versions),
            mock.patch.object(UPDATE_PINS, "DOCKER_PINS", ()),
            mock.patch.object(UPDATE_PINS, "api", side_effect=self.current_api),
            mock.patch.object(UPDATE_PINS, "github_release", side_effect=github_release),
            mock.patch.object(
                UPDATE_PINS,
                "latest_aws_cli_tag",
                return_value=self.dockerfile_arg("AWS_CLI_VERSION"),
            ),
            mock.patch.object(UPDATE_PINS, "github_head", side_effect=self.current_head),
            mock.patch.object(UPDATE_PINS, "request", side_effect=upstream),
        ):
            try:
                UPDATE_PINS.update()
                failure: Exception | None = None
            except Exception as error:  # noqa: BLE001 - the tests assert on the failure
                failure = error
        return licenses, notices, old_version, failure

    def test_tflint_busl_notice_comes_from_its_own_upstream_file(self):
        upstream = FakeUpstream()
        licenses, notices, old_version, failure = self.tflint_update(upstream)

        self.assertIsNone(failure)
        destination = licenses / "tflint-99.88.77"
        license_text = (destination / "LICENSE").read_bytes()
        busl_text = (destination / "LICENSE-BUSL").read_bytes()

        # Each notice file must come from its own upstream path.
        self.assertEqual(
            ["LICENSE", "terraform/LICENSE-BUSL"],
            sorted(upstream.paths("terraform-linters/tflint")),
        )
        # MPL-2.0 and BUSL-1.1 are different licenses and different files.
        self.assertNotEqual(license_text, busl_text)
        self.assertIn(b"Mozilla Public License", license_text)
        self.assertNotIn(b"Mozilla Public License", busl_text)
        self.assertIn(b"Business Source License 1.1", busl_text)
        # The superseded directory is replaced, not left behind.
        self.assertFalse((licenses / f"tflint-{old_version}").exists())
        self.assertIn("tflint-99.88.77/", notices.read_text(encoding="utf-8"))

    def test_tflint_busl_notice_rejects_the_neighbouring_mpl_file(self):
        # Regression guard: `terraform/LICENSE` holds the MPL-2.0 notice of the
        # embedded Terraform sources, so serving it as the BUSL grant must fail.
        upstream = FakeUpstream(
            overrides={"terraform/LICENSE-BUSL": LICENSE_TEXTS["MPL-2.0"]}
        )
        licenses, _notices, old_version, failure = self.tflint_update(upstream)

        self.assertIsInstance(failure, RuntimeError)
        self.assertIn("BUSL-1.1", str(failure))
        self.assertTrue((licenses / f"tflint-{old_version}").is_dir())
        self.assertFalse((licenses / "tflint-99.88.77").exists())

    def test_tflint_update_fails_when_an_upstream_license_is_missing(self):
        upstream = FakeUpstream(overrides={"terraform/LICENSE-BUSL": None})
        licenses, _notices, old_version, failure = self.tflint_update(upstream)

        self.assertIsInstance(failure, urllib.error.HTTPError)
        self.assertEqual(404, failure.code)
        self.assertTrue((licenses / f"tflint-{old_version}").is_dir())
        self.assertFalse((licenses / "tflint-99.88.77").exists())

    def test_tflint_update_fails_on_an_empty_upstream_response(self):
        upstream = FakeUpstream(overrides={"terraform/LICENSE-BUSL": b"   \n"})
        licenses, _notices, old_version, failure = self.tflint_update(upstream)

        self.assertIsInstance(failure, RuntimeError)
        self.assertTrue((licenses / f"tflint-{old_version}").is_dir())

    def test_write_license_dir_rejects_two_files_with_the_same_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            licenses = Path(temporary)
            (licenses / "component-1.0").mkdir()
            with self.assertRaises(RuntimeError) as raised:
                UPDATE_PINS.write_license_dir(
                    licenses,
                    "component",
                    "2.0",
                    {"LICENSE": b"same text\n", "LICENSE-BUSL": b"same text\n"},
                )

            self.assertIn("identical content", str(raised.exception))
            self.assertTrue((licenses / "component-1.0").is_dir())
            self.assertFalse((licenses / "component-2.0").exists())

    def test_checked_license_requires_the_expected_marker(self):
        self.assertEqual(
            LICENSE_TEXTS["BUSL-1.1"],
            UPDATE_PINS.checked_license(LICENSE_TEXTS["BUSL-1.1"], "BUSL-1.1", "test"),
        )
        for license_id, data in (
            ("BUSL-1.1", LICENSE_TEXTS["MPL-2.0"]),
            ("MPL-2.0", LICENSE_TEXTS["BUSL-1.1"]),
            ("MIT", b""),
        ):
            with self.subTest(license_id=license_id):
                with self.assertRaises(RuntimeError):
                    UPDATE_PINS.checked_license(data, license_id, "test")

    def test_committed_tflint_notices_reproduce_two_distinct_licenses(self):
        directories = sorted(UPDATE_PINS.LICENSES.glob("tflint-*"))
        self.assertEqual(1, len(directories), directories)
        license_text = (directories[0] / "LICENSE").read_bytes()
        busl_text = (directories[0] / "LICENSE-BUSL").read_bytes()

        self.assertIn(b"Mozilla Public License", license_text)
        self.assertIn(b"Business Source License 1.1", busl_text)
        self.assertNotIn(b"Mozilla Public License", busl_text)
        self.assertNotEqual(license_text, busl_text)
        self.assertIn(
            f"{directories[0].name}/",
            UPDATE_PINS.NOTICES.read_text(encoding="utf-8"),
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
