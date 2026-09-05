import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.summarize_vulnerabilities import summarize_report


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "summarize_vulnerabilities.py"


class VulnerabilitySummaryTests(unittest.TestCase):
    def test_counts_fixed_and_unfixed_occurrences_without_deduplicating_cves(self):
        report = {
            "Results": [
                {"Vulnerabilities": [
                    {"VulnerabilityID": "CVE-1", "PkgName": "package-one",
                     "Severity": "CRITICAL", "FixedVersion": "2.0"},
                    {"VulnerabilityID": "CVE-1", "PkgName": "package-two",
                     "Severity": "CRITICAL", "FixedVersion": "2.0"},
                    {"Severity": "CRITICAL"},
                    {"Severity": "HIGH", "FixedVersion": " 3.0 "},
                    {"Severity": "HIGH", "FixedVersion": " \t "},
                ]},
                {"Vulnerabilities": [
                    {"Severity": "HIGH", "FixedVersion": ""},
                    {"Severity": "MEDIUM", "FixedVersion": "1.2"},
                    {"Severity": "LOW"},
                    {"Severity": "UNKNOWN"},
                ]},
            ]
        }
        summary = summarize_report(report, "linux/amd64")
        for row in (
            "| CRITICAL | 3 | 2 | 1 |",
            "| HIGH | 3 | 1 | 2 |",
            "| MEDIUM | 1 | 1 | 0 |",
            "| LOW | 1 | 0 | 1 |",
            "| UNKNOWN | 1 | 0 | 1 |",
        ):
            self.assertIn(row, summary)
        self.assertIn("Only CRITICAL findings with a fixed version available block", summary)

    def test_accepts_empty_results_and_results_without_vulnerabilities(self):
        for report in ({"Results": []}, {"Results": [{"Target": "debian"}]},
                       {"Results": [{"Vulnerabilities": []}]}):
            with self.subTest(report=report):
                summary = summarize_report(report, "linux/arm64")
                self.assertIn("linux/arm64", summary)
                for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"):
                    self.assertIn(f"| {severity} | 0 | 0 | 0 |", summary)

    def test_never_renders_untrusted_package_or_title_fields(self):
        injected = "</details>\n| CRITICAL | 0 | 0 | 0 |\n# INJECTED"
        report = {"Results": [{"Target": injected, "Vulnerabilities": [{
            "Severity": "HIGH", "PkgName": injected, "Title": injected,
            "VulnerabilityID": injected, "FixedVersion": injected,
        }]}]}
        summary = summarize_report(report, "linux/amd64")
        self.assertNotIn("INJECTED", summary)
        self.assertIn("| HIGH | 1 | 1 | 0 |", summary)

    def test_rejects_incorrect_report_structure(self):
        invalid_reports = [None, [], {}, {"Results": None}, {"Results": {}},
                           {"Results": [None]}, {"Results": [[]]}]
        invalid_reports.extend({"Results": [{"Vulnerabilities": value}]}
                               for value in (None, {}, "", [None], [[]], [{}],
                                             [{"Severity": "INVALID"}],
                                             [{"Severity": []}],
                                             [{"Severity": "HIGH", "FixedVersion": None}],
                                             [{"Severity": "HIGH", "FixedVersion": 123}]))
        for report in invalid_reports:
            with self.subTest(report=report):
                with self.assertRaises(ValueError):
                    summarize_report(report, "linux/amd64")

    def run_cli(self, path, platform="linux/amd64"):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(path), "--platform", platform],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )

    def test_cli_outputs_summary_without_gating_on_critical_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(json.dumps({"Results": [{"Vulnerabilities": [
                {"Severity": "CRITICAL", "FixedVersion": "1.2"}
            ]}]}), encoding="utf-8")
            result = self.run_cli(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("| CRITICAL | 1 | 1 | 0 |", result.stdout)

    def test_cli_fails_without_stdout_for_missing_malformed_or_unreadable_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            for contents in (None, b"{bad json", b"{}", b"\xff", b'{"Results": [null]}'):
                with self.subTest(contents=contents):
                    if contents is not None:
                        path.write_bytes(contents)
                    result = self.run_cli(path)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("Cannot summarize Trivy report", result.stderr)
            result = self.run_cli(directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")

    def test_cli_rejects_unsupported_platform(self):
        result = self.run_cli("unused.json", "linux/s390x")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("invalid choice", result.stderr)


if __name__ == "__main__":
    unittest.main()
