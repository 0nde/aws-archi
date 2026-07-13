from __future__ import annotations

import importlib.util
import unittest
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


if __name__ == "__main__":
    unittest.main()
