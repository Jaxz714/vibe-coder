"""Quality report generation in Markdown."""

from __future__ import annotations

import datetime
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown

from .config import Config
from .reviewer import review_files
from .security import ScanResult, scan_directory
from .testgen import generate_tests

console = Console()


def _header(directory: Path) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "# Vibe Coder — Quality Report\n\n"
        f"- **Directory:** `{directory.resolve()}`\n"
        f"- **Generated:** {now}\n\n"
        "---\n"
    )


def _security_section(scan_result: ScanResult) -> str:
    lines = ["## Security Scan\n"]
    if scan_result.total == 0:
        lines.append("No security issues found.\n")
    else:
        lines.append(f"**Total findings:** {scan_result.total} ")
        lines.append(f"({scan_result.high_count} high, {scan_result.medium_count} medium, {scan_result.low_count} low)\n")
        lines.append("| Severity | File | Line | Pattern | Description |")
        lines.append("|----------|------|------|---------|-------------|")
        for f in sorted(scan_result.findings, key=lambda x: ("high", "medium", "low").index(x.severity)):
            lines.append(f"| {f.severity} | `{f.filepath}` | {f.line_number} | {f.pattern_name} | {f.description} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def _review_section(review_text: str) -> str:
    lines = ["## AI Code Review\n"]
    if not review_text:
        lines.append("_Skipped — no Anthropic API key configured._\n")
    else:
        lines.append(review_text + "\n")
    return "\n".join(lines) + "\n"


def _testgen_section(test_results: dict[str, str]) -> str:
    lines = ["## Test Generation\n"]
    if not test_results:
        lines.append("_Skipped — no source files found or no API key configured._\n")
    else:
        for relpath, code in test_results.items():
            lines.append(f"### Tests for `{relpath}`\n")
            # Strip markdown fences for embedding.
            cleaned = code.strip()
            if cleaned.startswith("```"):
                fence_lines = cleaned.splitlines()
                if fence_lines[0].startswith("```"):
                    fence_lines = fence_lines[1:]
                if fence_lines and fence_lines[-1].strip() == "```":
                    fence_lines = fence_lines[:-1]
                cleaned = "\n".join(fence_lines)
            lines.append(f"```python\n{cleaned}\n```\n")
    return "\n".join(lines) + "\n"


def generate_report(directory: Path, cfg: Config) -> str:
    """Run all checks and produce a full Markdown report."""
    console.print("[bold cyan]Generating quality report...[/bold cyan]\n")

    # 1. Security scan (always runs — no API key needed).
    console.print("  [cyan]1/3[/cyan] Running security scan...")
    scan_result = scan_directory(directory)

    # 2. AI code review.
    console.print("  [cyan]2/3[/cyan] Running AI code review...")
    review_text = ""
    if cfg.anthropic_api_key:
        review_text = review_files(directory, cfg)
    else:
        console.print("    [dim](skipped — no API key)[/dim]")

    # 3. Test generation.
    console.print("  [cyan]3/3[/cyan] Generating tests...")
    test_results: dict[str, str] = {}
    if cfg.anthropic_api_key:
        test_results = generate_tests(directory, cfg)
    else:
        console.print("    [dim](skipped — no API key)[/dim]")

    # Assemble report.
    report = _header(directory)
    report += _security_section(scan_result)
    report += _review_section(review_text)
    report += _testgen_section(test_results)
    return report


def save_report(report: str, output_path: Path) -> None:
    """Write the report to *output_path* and print it to the console."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    console.print(f"\n[bold green]Report saved to[/bold green] {output_path}\n")
    console.print(Markdown(report))
