#!/usr/bin/env python3
"""Summarize a complete Trivy JSON report without changing the security gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")
PLATFORMS = ("linux/amd64", "linux/arm64")


def summarize_report(report: object, platform: str) -> str:
    """Validate report structure and render counts, never untrusted package text."""
    if platform not in PLATFORMS:
        raise ValueError("unsupported platform")
    if not isinstance(report, dict) or not isinstance(report.get("Results"), list):
        raise ValueError("report must be an object containing a Results array")
    counts = {severity: [0, 0, 0] for severity in SEVERITIES}
    for result in report["Results"]:
        if not isinstance(result, dict):
            raise ValueError("each Results entry must be an object")
        vulnerabilities = result.get("Vulnerabilities", [])
        if not isinstance(vulnerabilities, list):
            raise ValueError("Vulnerabilities must be an array when present")
        for vulnerability in vulnerabilities:
            if not isinstance(vulnerability, dict):
                raise ValueError("each vulnerability must be an object")
            severity = vulnerability.get("Severity")
            if not isinstance(severity, str) or severity not in counts:
                raise ValueError("each vulnerability must have a recognized Severity")
            fixed_version = vulnerability.get("FixedVersion", "")
            if not isinstance(fixed_version, str):
                raise ValueError("FixedVersion must be a string when present")
            counts[severity][0] += 1
            counts[severity][1 if fixed_version.strip() else 2] += 1
    lines = [
        f"### Vulnerability report: {platform}",
        "",
        "| Severity | Occurrences | Fixed version available | No fixed version reported |",
        "| --- | ---: | ---: | ---: |",
    ]
    for severity, (total, fixed, unfixed) in counts.items():
        lines.append(f"| {severity} | {total} | {fixed} | {unfixed} |")
    lines.extend([
        "",
        "Counts are package vulnerability occurrences; the same CVE can appear more than once.",
        "Only CRITICAL findings with a fixed version available block the existing Trivy gate.",
        "Other findings remain available for review; this summary does not change the gate.",
    ])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_json", type=Path)
    parser.add_argument("--platform", required=True, choices=PLATFORMS)
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report_json.read_text(encoding="utf-8"))
        summary = summarize_report(report, args.platform)
    except (OSError, ValueError) as error:
        print(f"Cannot summarize Trivy report: {error}", file=sys.stderr)
        return 1
    print(summary, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
