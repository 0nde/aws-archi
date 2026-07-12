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
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / ".devcontainer" / "Dockerfile"
NOTICES = ROOT / "THIRD_PARTY_NOTICES.md"
LICENSES = ROOT / "third_party_licenses"
USER_AGENT = "aws-archi-maintenance/1.0"


def request(url: str) -> bytes:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as response:
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


def arg(content: str, name: str) -> str:
    match = re.search(rf"^ARG {re.escape(name)}=(.+)$", content, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Missing Dockerfile ARG {name}")
    return match.group(1).strip()


def set_arg(content: str, name: str, value: str) -> str:
    return replace_one(content, rf"^ARG {re.escape(name)}=.+$", f"ARG {name}={value}", name)


def github_release(repository: str) -> tuple[str, str, dict[str, str]]:
    release = api(f"https://api.github.com/repos/{repository}/releases/latest")
    tag = release["tag_name"]
    commit = api(f"https://api.github.com/repos/{repository}/commits/{tag}")["sha"]
    assets = {asset["name"]: asset["browser_download_url"] for asset in release.get("assets", [])}
    return tag, commit, assets


def github_head(repository: str) -> str:
    repo = api(f"https://api.github.com/repos/{repository}")
    return api(f"https://api.github.com/repos/{repository}/commits/{repo['default_branch']}")["sha"]


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
    tags = api("https://api.github.com/repos/aws/aws-cli/tags?per_page=100")
    versions = [item["name"] for item in tags if item["name"].startswith("2.")]
    return max(versions, key=version_tuple)


def write_license_dir(prefix: str, suffix: str, files: dict[str, bytes]) -> None:
    matches = list(LICENSES.glob(f"{prefix}-*"))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one {prefix} license directory, found {len(matches)}")
    destination = LICENSES / f"{prefix}-{suffix}"
    if matches[0] != destination:
        shutil.rmtree(matches[0])
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (destination / name).write_bytes(data)


def update() -> list[str]:
    original_dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    original_notices = NOTICES.read_text(encoding="utf-8")
    dockerfile = original_dockerfile
    notices = original_notices
    changes: list[str] = []

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
            "terraform",
            terraform_version,
            {"LICENSE": request(f"https://raw.githubusercontent.com/hashicorp/terraform/v{terraform_version}/LICENSE")},
        )
        notices = notices.replace(f"terraform-{old}/LICENSE", f"terraform-{terraform_version}/LICENSE")
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
            "tflint",
            tflint_version,
            {
                "LICENSE": request(f"https://raw.githubusercontent.com/terraform-linters/tflint/{tflint_tag}/LICENSE"),
                "LICENSE-BUSL": request(f"https://raw.githubusercontent.com/terraform-linters/tflint/{tflint_tag}/terraform/LICENSE"),
            },
        )
        notices = notices.replace(f"tflint-{old}/", f"tflint-{tflint_version}/")
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
            "github-cli",
            gh_version,
            {"LICENSE": request(f"https://raw.githubusercontent.com/cli/cli/{gh_tag}/LICENSE")},
        )
        notices = notices.replace(f"github-cli-{old}/LICENSE", f"github-cli-{gh_version}/LICENSE")
        changes.append(f"GitHub CLI {old} -> {gh_version}")

    terragrunt_tag, terragrunt_commit, _ = github_release("gruntwork-io/terragrunt")
    terragrunt_version = terragrunt_tag.removeprefix("v")
    if arg(dockerfile, "TERRAGRUNT_COMMIT") != terragrunt_commit:
        old = arg(dockerfile, "TERRAGRUNT_VERSION")
        dockerfile = set_arg(dockerfile, "TERRAGRUNT_VERSION", terragrunt_version)
        dockerfile = set_arg(dockerfile, "TERRAGRUNT_COMMIT", terragrunt_commit)
        write_license_dir(
            "terragrunt",
            terragrunt_version,
            {"LICENSE.txt": request(f"https://raw.githubusercontent.com/gruntwork-io/terragrunt/{terragrunt_tag}/LICENSE.txt")},
        )
        notices = notices.replace(f"terragrunt-{old}/LICENSE.txt", f"terragrunt-{terragrunt_version}/LICENSE.txt")
        changes.append(f"Terragrunt {old} -> {terragrunt_version}")

    docs_tag, docs_commit, _ = github_release("terraform-docs/terraform-docs")
    if arg(dockerfile, "TERRAFORM_DOCS_COMMIT") != docs_commit:
        old_short = arg(dockerfile, "TERRAFORM_DOCS_COMMIT")[:8]
        new_short = docs_commit[:8]
        dockerfile = set_arg(dockerfile, "TERRAFORM_DOCS_COMMIT", docs_commit)
        write_license_dir(
            "terraform-docs",
            new_short,
            {"LICENSE": request(f"https://raw.githubusercontent.com/terraform-docs/terraform-docs/{docs_tag}/LICENSE")},
        )
        notices = notices.replace(f"terraform-docs-{old_short}/LICENSE", f"terraform-docs-{new_short}/LICENSE")
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
                    "APACHE-2.0.txt": (next(LICENSES.glob("aws-cli-*/APACHE-2.0.txt"))).read_bytes(),
                }
        write_license_dir("aws-cli", aws_version, license_files)
        notices = notices.replace(f"aws-cli-{old}/", f"aws-cli-{aws_version}/")
        changes.append(f"AWS CLI {old} -> {aws_version}")

    npm_version = api("https://registry.npmjs.org/npm/latest")["version"]
    if arg(dockerfile, "NPM_VERSION") != npm_version:
        old = arg(dockerfile, "NPM_VERSION")
        dockerfile = set_arg(dockerfile, "NPM_VERSION", npm_version)
        changes.append(f"npm {old} -> {npm_version}")

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

    if dockerfile != original_dockerfile:
        DOCKERFILE.write_text(dockerfile, encoding="utf-8", newline="\n")
    if notices != original_notices:
        NOTICES.write_text(notices, encoding="utf-8", newline="\n")
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
