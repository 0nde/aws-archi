#!/usr/bin/env python3
"""Update manually pinned tools and their redistribution notices.

The script deliberately prepares reviewable source changes only. It never commits,
pushes, publishes an image, creates a release, or merges a pull request.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / ".devcontainer" / "Dockerfile"
NOTICES = ROOT / "THIRD_PARTY_NOTICES.md"
LICENSES = ROOT / "third_party_licenses"
TOOL_VERSIONS = ROOT / "tooling" / "tool-versions.conf"
USER_AGENT = "aws-archi-maintenance/1.0"
REQUEST_ATTEMPTS = 4
DOCKER_MANIFEST_ACCEPT = ", ".join(
    (
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    )
)
DOCKER_PINS = (
    ("Dockerfile frontend", "docker/dockerfile:1.24", "docker/dockerfile"),
    ("Node.js base image", "node:24-trixie-slim", "library/node"),
    ("Go builder image", "golang:1.26-trixie", "library/golang"),
    ("Python base image", "python:3.14-slim-trixie", "library/python"),
)


def urlopen_with_retry(request_or_url, *, timeout: int = 120):
    """Open an URL, retrying only transient network and server failures."""

    for attempt in range(REQUEST_ATTEMPTS):
        try:
            return urllib.request.urlopen(request_or_url, timeout=timeout)
        except urllib.error.HTTPError as error:
            if error.code not in {408, 425, 429, 500, 502, 503, 504}:
                raise
            failure = error
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            failure = error
        if attempt == REQUEST_ATTEMPTS - 1:
            raise failure
        retry_after = (getattr(failure, "headers", None) or {}).get("Retry-After")
        try:
            delay = min(float(retry_after), 30.0) if retry_after else min(2**attempt, 8)
        except ValueError:
            delay = min(2**attempt, 8)
        time.sleep(delay)
    raise AssertionError("unreachable")


def request(url: str) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if url.startswith("https://api.github.com/"):
        headers["Accept"] = "application/vnd.github+json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
    with urlopen_with_retry(urllib.request.Request(url, headers=headers)) as response:
        return response.read()


def text(url: str) -> str:
    return request(url).decode("utf-8")


def api(url: str):
    return json.loads(request(url))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_one(content: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"Could not uniquely update {label}")
    return updated


def replace_literal_once(content: str, old: str, new: str, label: str) -> str:
    if content.count(old) != 1:
        raise RuntimeError(f"Could not uniquely update {label}")
    return content.replace(old, new, 1)


def arg(content: str, name: str) -> str:
    match = re.search(rf"^ARG {re.escape(name)}=(.+)$", content, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Missing Dockerfile ARG {name}")
    return match.group(1).strip()


def set_arg(content: str, name: str, value: str) -> str:
    return replace_one(content, rf"^ARG {re.escape(name)}=.+$", f"ARG {name}={value}", name)


def env_version(content: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}=(.+)$", content, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Missing version pin {name}")
    return match.group(1)


def set_env_version(content: str, name: str, value: str) -> str:
    return replace_one(content, rf"^{re.escape(name)}=.+$", f"{name}={value}", name)


def github_release(repository: str) -> tuple[str, str, dict[str, str]]:
    release = api(f"https://api.github.com/repos/{repository}/releases/latest")
    tag = release["tag_name"]
    commit = api(f"https://api.github.com/repos/{repository}/commits/{tag}")["sha"]
    assets = {asset["name"]: asset["browser_download_url"] for asset in release.get("assets", [])}
    return tag, commit, assets


def github_head(repository: str) -> str:
    repo = api(f"https://api.github.com/repos/{repository}")
    return api(f"https://api.github.com/repos/{repository}/commits/{repo['default_branch']}")["sha"]


def docker_hub_digest(repository: str, tag: str) -> str:
    query = urllib.parse.urlencode(
        {"service": "registry.docker.io", "scope": f"repository:{repository}:pull"}
    )
    token = api(f"https://auth.docker.io/token?{query}")["token"]
    manifest_url = f"https://registry-1.docker.io/v2/{repository}/manifests/{urllib.parse.quote(tag, safe='')}"
    manifest_request = urllib.request.Request(
        manifest_url,
        headers={
            "Accept": DOCKER_MANIFEST_ACCEPT,
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
        },
        method="HEAD",
    )
    with urlopen_with_retry(manifest_request) as response:
        digest = response.headers.get("Docker-Content-Digest", "").lower()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise RuntimeError(f"Docker Hub returned an invalid digest for {repository}:{tag}")
    return digest.removeprefix("sha256:")


def update_docker_pin(content: str, label: str, reference: str, repository: str) -> tuple[str, str | None]:
    pattern = (
        rf"^(?P<prefix>(?:# syntax=|FROM ){re.escape(reference)}@sha256:)"
        rf"(?P<digest>[0-9a-f]{{64}})(?P<suffix>(?: AS [A-Za-z0-9_.-]+)?)$"
    )
    matches = list(re.finditer(pattern, content, re.MULTILINE))
    if len(matches) != 1:
        raise RuntimeError(f"Could not uniquely locate {label}")
    current = matches[0].group("digest")
    latest = docker_hub_digest(repository, reference.rsplit(":", 1)[1])
    if current == latest:
        return content, None
    updated = replace_one(content, pattern, rf"\g<prefix>{latest}\g<suffix>", label)
    return updated, f"{label} {current[:12]} -> {latest[:12]}"


def checksum_file(url: str, filename: str) -> str:
    for line in text(url).splitlines():
        fields = line.strip().split()
        if len(fields) >= 2 and fields[-1].lstrip("*") == filename:
            value = fields[0].lower()
            if re.fullmatch(r"[0-9a-f]{64}", value):
                return value
    raise RuntimeError(f"No SHA-256 for {filename} in {url}")


def version_tuple(value: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+(?:\.\d+)+", value):
        raise ValueError(value)
    return tuple(int(part) for part in value.split("."))


def latest_aws_cli_tag() -> str:
    versions: list[str] = []
    page = 1
    while True:
        tags = api(f"https://api.github.com/repos/aws/aws-cli/tags?per_page=100&page={page}")
        versions.extend(
            item["name"]
            for item in tags
            if re.fullmatch(r"2\.\d+(?:\.\d+)+", item["name"])
        )
        if len(tags) < 100:
            break
        page += 1
    if not versions:
        raise RuntimeError("No AWS CLI v2 tag found")
    return max(versions, key=version_tuple)


def write_license_dir(
    licenses: Path, prefix: str, suffix: str, files: dict[str, bytes]
) -> None:
    # A component name can prefix another one (for example, terraform and
    # terraform-docs), so require the suffix to look like a version or commit.
    matches = [
        path
        for path in licenses.glob(f"{prefix}-*")
        if re.match(r"(?:v?\d|[a-f][0-9a-f]{7,39}$)", path.name[len(prefix) + 1 :])
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one {prefix} license directory, found {len(matches)}")
    destination = licenses / f"{prefix}-{suffix}"
    if matches[0] != destination:
        shutil.rmtree(matches[0])
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (destination / name).write_bytes(data)


def atomic_write_text(path: Path, content: str) -> None:
    """Replace a text file without exposing a partially written file."""

    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.chmod(temporary, path.stat().st_mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def commit_updates(files: dict[Path, str], staged_licenses: Path) -> None:
    """Apply staged changes with rollback if a local filesystem operation fails."""

    originals = {path: path.read_bytes() for path in files}
    backup = LICENSES.with_name(f".{LICENSES.name}.backup-{os.getpid()}")
    moved_licenses = False
    try:
        for path, content in files.items():
            atomic_write_text(path, content)
        if backup.exists():
            shutil.rmtree(backup)
        os.replace(LICENSES, backup)
        moved_licenses = True
        os.replace(staged_licenses, LICENSES)
    except Exception:
        for path, content in originals.items():
            descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.rollback.", dir=path.parent)
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(content)
                os.chmod(temporary, path.stat().st_mode)
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        if moved_licenses:
            if LICENSES.exists():
                shutil.rmtree(LICENSES)
            os.replace(backup, LICENSES)
        raise
    finally:
        if backup.exists():
            shutil.rmtree(backup)


def update() -> list[str]:
    original_dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    original_notices = NOTICES.read_text(encoding="utf-8")
    original_tool_versions = TOOL_VERSIONS.read_text(encoding="utf-8")
    dockerfile = original_dockerfile
    notices = original_notices
    tool_versions = original_tool_versions
    changes: list[str] = []

    temporary = tempfile.TemporaryDirectory(prefix=".update-pins-", dir=ROOT)
    staging = Path(temporary.name)
    staged_licenses = staging / "third_party_licenses"
    shutil.copytree(LICENSES, staged_licenses)

    for label, reference, repository in DOCKER_PINS:
        dockerfile, change = update_docker_pin(dockerfile, label, reference, repository)
        if change:
            changes.append(change)

    terraform = api("https://api.releases.hashicorp.com/v1/releases/terraform/latest")
    terraform_version = terraform["version"]
    terraform_sums = terraform["url_shasums"]
    if arg(dockerfile, "TERRAFORM_VERSION") != terraform_version:
        old = arg(dockerfile, "TERRAFORM_VERSION")
        dockerfile = set_arg(dockerfile, "TERRAFORM_VERSION", terraform_version)
        for arch in ("amd64", "arm64"):
            filename = f"terraform_{terraform_version}_linux_{arch}.zip"
            dockerfile = set_arg(dockerfile, f"TERRAFORM_SHA256_{arch.upper()}", checksum_file(terraform_sums, filename))
        write_license_dir(
            staged_licenses,
            "terraform",
            terraform_version,
            {"LICENSE": request(f"https://raw.githubusercontent.com/hashicorp/terraform/v{terraform_version}/LICENSE")},
        )
        notices = replace_literal_once(
            notices,
            f"terraform-{old}/LICENSE",
            f"terraform-{terraform_version}/LICENSE",
            "Terraform notice",
        )
        changes.append(f"Terraform {old} -> {terraform_version}")

    tflint_tag, _, tflint_assets = github_release("terraform-linters/tflint")
    tflint_version = tflint_tag.removeprefix("v")
    if arg(dockerfile, "TFLINT_VERSION") != tflint_version:
        old = arg(dockerfile, "TFLINT_VERSION")
        sums = tflint_assets["checksums.txt"]
        dockerfile = set_arg(dockerfile, "TFLINT_VERSION", tflint_version)
        for arch in ("amd64", "arm64"):
            dockerfile = set_arg(
                dockerfile,
                f"TFLINT_SHA256_{arch.upper()}",
                checksum_file(sums, f"tflint_linux_{arch}.zip"),
            )
        write_license_dir(
            staged_licenses,
            "tflint",
            tflint_version,
            {
                "LICENSE": request(f"https://raw.githubusercontent.com/terraform-linters/tflint/{tflint_tag}/LICENSE"),
                "LICENSE-BUSL": request(f"https://raw.githubusercontent.com/terraform-linters/tflint/{tflint_tag}/terraform/LICENSE"),
            },
        )
        notices = replace_literal_once(
            notices,
            f"tflint-{old}/",
            f"tflint-{tflint_version}/",
            "TFLint notice",
        )
        changes.append(f"TFLint {old} -> {tflint_version}")

    gh_tag, _, gh_assets = github_release("cli/cli")
    gh_version = gh_tag.removeprefix("v")
    if arg(dockerfile, "GH_VERSION") != gh_version:
        old = arg(dockerfile, "GH_VERSION")
        sums = gh_assets[f"gh_{gh_version}_checksums.txt"]
        dockerfile = set_arg(dockerfile, "GH_VERSION", gh_version)
        for arch in ("amd64", "arm64"):
            dockerfile = set_arg(
                dockerfile,
                f"GH_SHA256_{arch.upper()}",
                checksum_file(sums, f"gh_{gh_version}_linux_{arch}.tar.gz"),
            )
        write_license_dir(
            staged_licenses,
            "github-cli",
            gh_version,
            {"LICENSE": request(f"https://raw.githubusercontent.com/cli/cli/{gh_tag}/LICENSE")},
        )
        notices = replace_literal_once(
            notices,
            f"github-cli-{old}/LICENSE",
            f"github-cli-{gh_version}/LICENSE",
            "GitHub CLI notice",
        )
        changes.append(f"GitHub CLI {old} -> {gh_version}")

    terragrunt_tag, terragrunt_commit, _ = github_release("gruntwork-io/terragrunt")
    terragrunt_version = terragrunt_tag.removeprefix("v")
    if arg(dockerfile, "TERRAGRUNT_COMMIT") != terragrunt_commit:
        old = arg(dockerfile, "TERRAGRUNT_VERSION")
        dockerfile = set_arg(dockerfile, "TERRAGRUNT_VERSION", terragrunt_version)
        dockerfile = set_arg(dockerfile, "TERRAGRUNT_COMMIT", terragrunt_commit)
        write_license_dir(
            staged_licenses,
            "terragrunt",
            terragrunt_version,
            {"LICENSE.txt": request(f"https://raw.githubusercontent.com/gruntwork-io/terragrunt/{terragrunt_tag}/LICENSE.txt")},
        )
        notices = replace_literal_once(
            notices,
            f"terragrunt-{old}/LICENSE.txt",
            f"terragrunt-{terragrunt_version}/LICENSE.txt",
            "Terragrunt notice",
        )
        changes.append(f"Terragrunt {old} -> {terragrunt_version}")

    docs_tag, docs_commit, _ = github_release("terraform-docs/terraform-docs")
    if arg(dockerfile, "TERRAFORM_DOCS_COMMIT") != docs_commit:
        old_short = arg(dockerfile, "TERRAFORM_DOCS_COMMIT")[:8]
        new_short = docs_commit[:8]
        dockerfile = set_arg(dockerfile, "TERRAFORM_DOCS_COMMIT", docs_commit)
        write_license_dir(
            staged_licenses,
            "terraform-docs",
            new_short,
            {"LICENSE": request(f"https://raw.githubusercontent.com/terraform-docs/terraform-docs/{docs_tag}/LICENSE")},
        )
        notices = replace_literal_once(
            notices,
            f"terraform-docs-{old_short}/LICENSE",
            f"terraform-docs-{new_short}/LICENSE",
            "terraform-docs notice",
        )
        changes.append(f"terraform-docs {old_short} -> {docs_tag} ({new_short})")

    aws_version = latest_aws_cli_tag()
    if arg(dockerfile, "AWS_CLI_VERSION") != aws_version:
        old = arg(dockerfile, "AWS_CLI_VERSION")
        archives: dict[str, bytes] = {}
        dockerfile = set_arg(dockerfile, "AWS_CLI_VERSION", aws_version)
        for arch, aws_arch in (("AMD64", "x86_64"), ("ARM64", "aarch64")):
            data = request(f"https://awscli.amazonaws.com/awscli-exe-linux-{aws_arch}-{aws_version}.zip")
            archives[aws_arch] = data
            dockerfile = set_arg(dockerfile, f"AWS_CLI_SHA256_{arch}", sha256(data))
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "awscliv2.zip"
            archive.write_bytes(archives["x86_64"])
            with zipfile.ZipFile(archive) as bundle:
                license_files = {
                    "LICENSE.txt": request(f"https://raw.githubusercontent.com/aws/aws-cli/{aws_version}/LICENSE.txt"),
                    "THIRD_PARTY_LICENSES": bundle.read("aws/THIRD_PARTY_LICENSES"),
                    "APACHE-2.0.txt": (
                        next(staged_licenses.glob("aws-cli-*/APACHE-2.0.txt"))
                    ).read_bytes(),
                }
        write_license_dir(staged_licenses, "aws-cli", aws_version, license_files)
        notices = replace_literal_once(
            notices,
            f"aws-cli-{old}/",
            f"aws-cli-{aws_version}/",
            "AWS CLI notice",
        )
        changes.append(f"AWS CLI {old} -> {aws_version}")

    npm_version = api("https://registry.npmjs.org/npm/latest")["version"]
    if arg(dockerfile, "NPM_VERSION") != npm_version:
        old = arg(dockerfile, "NPM_VERSION")
        dockerfile = set_arg(dockerfile, "NPM_VERSION", npm_version)
        changes.append(f"npm {old} -> {npm_version}")

    go_licenses_tag, _, _ = github_release("google/go-licenses")
    go_licenses_version = go_licenses_tag.removeprefix("v")
    if arg(dockerfile, "GO_LICENSES_VERSION") != go_licenses_version:
        old = arg(dockerfile, "GO_LICENSES_VERSION")
        dockerfile = set_arg(dockerfile, "GO_LICENSES_VERSION", go_licenses_version)
        changes.append(f"go-licenses {old} -> {go_licenses_version}")

    cosign_tag, _, _ = github_release("sigstore/cosign")
    cosign_version = cosign_tag.removeprefix("v")
    current_cosign = env_version(tool_versions, "COSIGN_VERSION")
    if current_cosign != cosign_version:
        tool_versions = set_env_version(
            tool_versions, "COSIGN_VERSION", cosign_version
        )
        changes.append(f"Cosign {current_cosign} -> {cosign_version}")

    for module, pattern in (("golang.org/x/crypto", r"go get golang.org/x/crypto@v[^ ]+"), ("golang.org/x/net", r"golang.org/x/net@v[^ ]+")):
        latest = api(f"https://proxy.golang.org/{module}/@latest")["Version"]
        current_match = re.search(pattern, dockerfile)
        if not current_match:
            raise RuntimeError(f"Missing forced Go dependency {module}")
        current = current_match.group(0).split("@", 1)[1]
        if current != latest:
            dockerfile = replace_one(dockerfile, pattern, current_match.group(0).replace(f"@{current}", f"@{latest}"), module)
            changes.append(f"{module} {current} -> {latest}")

    for repository, name in (
        ("ohmyzsh/ohmyzsh", "OH_MY_ZSH_COMMIT"),
        ("zsh-users/zsh-autosuggestions", "ZSH_AUTOSUGGESTIONS_COMMIT"),
        ("zsh-users/zsh-syntax-highlighting", "ZSH_SYNTAX_HIGHLIGHTING_COMMIT"),
    ):
        latest = github_head(repository)
        current = arg(dockerfile, name)
        if current != latest:
            dockerfile = set_arg(dockerfile, name, latest)
            changes.append(f"{repository} {current[:8]} -> {latest[:8]}")

    files: dict[Path, str] = {}
    if dockerfile != original_dockerfile:
        files[DOCKERFILE] = dockerfile
    if notices != original_notices:
        files[NOTICES] = notices
    if tool_versions != original_tool_versions:
        files[TOOL_VERSIONS] = tool_versions
    if files:
        commit_updates(files, staged_licenses)
    temporary.cleanup()
    return changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, help="write a Markdown summary")
    args = parser.parse_args()
    changes = update()
    lines = ["## Pinned tool maintenance", ""]
    if changes:
        lines.extend(f"- {change}" for change in changes)
    else:
        lines.append("All manually managed pins are current.")
    summary = "\n".join(lines) + "\n"
    print(summary, end="")
    if args.summary:
        args.summary.write_text(summary, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
