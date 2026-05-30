"""Click CLI for Vibe Coder."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from .config import Config
from .hooks import install_hook, uninstall_hook
from .reporter import generate_report, save_report
from .reviewer import display_review, review_diff, review_files
from .security import display_scan_result, scan_directory
from .testgen import display_testgen, generate_tests
from .watcher import FileWatcher

console = Console()


def _resolve_directory(path: str) -> Path:
    """Resolve and validate a directory argument."""
    p = Path(path).resolve()
    if not p.is_dir():
        console.print(f"[bold red]Error:[/bold red] '{p}' is not a directory.")
        raise SystemExit(1)
    return p


# -----------------------------------------------------------------------
# Root group
# -----------------------------------------------------------------------

@click.group()
@click.version_option(package_name="vibe-coder")
def cli() -> None:
    """Vibe Coder — quality guardrails for AI coding workflows."""


# -----------------------------------------------------------------------
# review
# -----------------------------------------------------------------------

@cli.command()
@click.argument("directory", required=False, default=".")
@click.option("--diff", is_flag=True, help="Review only the current git diff.")
def review(directory: str, diff: bool) -> None:
    """AI-powered code review using Claude."""
    cfg = Config()
    if diff:
        text = review_diff(cfg)
    else:
        text = review_files(_resolve_directory(directory), cfg)
    display_review(text)


# -----------------------------------------------------------------------
# testgen
# -----------------------------------------------------------------------

@cli.command()
@click.argument("directory", required=False, default=".")
@click.option("--output-dir", "-o", type=click.Path(), default=None, help="Directory to write generated test files.")
def testgen(directory: str, output_dir: str | None) -> None:
    """Auto-generate unit tests for source files."""
    cfg = Config()
    out = Path(output_dir).resolve() if output_dir else None
    results = generate_tests(_resolve_directory(directory), cfg, output_dir=out)
    display_testgen(results)


# -----------------------------------------------------------------------
# scan
# -----------------------------------------------------------------------

@cli.command()
@click.argument("directory", required=False, default=".")
@click.option("--quiet", is_flag=True, help="Suppress table output (exit code only).")
def scan(directory: str, quiet: bool) -> None:
    """Run a security scan (pattern-based)."""
    result = scan_directory(_resolve_directory(directory))
    if not quiet:
        display_scan_result(result, _resolve_directory(directory))
    if result.high_count > 0:
        raise SystemExit(1)


# -----------------------------------------------------------------------
# watch
# -----------------------------------------------------------------------

@cli.command()
@click.argument("directory", required=False, default=".")
def watch(directory: str) -> None:
    """Watch a directory for changes and auto-run quality checks."""
    cfg = Config()
    target = _resolve_directory(directory)

    def on_change(changed_files: list[Path]) -> None:
        console.print(f"\n[bold]Running checks on {len(changed_files)} changed file(s)...[/bold]")
        # Security scan on changed files.
        from .security import Finding, ScanResult, scan_file, _load_patterns

        patterns = _load_patterns()
        findings: list[Finding] = []
        for f in changed_files:
            findings.extend(scan_file(f, patterns))
        if findings:
            tmp_result = ScanResult(findings=findings)
            display_scan_result(tmp_result, target)
        else:
            console.print("[green]No security issues in changed files.[/green]")

        # AI review if key is available.
        if cfg.anthropic_api_key:
            text = review_files(target, cfg)
            display_review(text)

    watcher = FileWatcher(target, on_change=on_change)
    watcher.run()


# -----------------------------------------------------------------------
# report
# -----------------------------------------------------------------------

@cli.command()
@click.argument("directory", required=False, default=".")
@click.option("--output", "-o", type=click.Path(), default="vibe-report.md", help="Path for the Markdown report.")
def report(directory: str, output: str) -> None:
    """Generate a full quality report (review + tests + security)."""
    cfg = Config()
    report_text = generate_report(_resolve_directory(directory), cfg)
    save_report(report_text, Path(output).resolve())


# -----------------------------------------------------------------------
# hooks
# -----------------------------------------------------------------------

@cli.group()
def hooks() -> None:
    """Manage git pre-commit hooks."""


@hooks.command("install")
def hooks_install() -> None:
    """Install the Vibe Coder pre-commit hook."""
    install_hook()


@hooks.command("uninstall")
def hooks_uninstall() -> None:
    """Uninstall the Vibe Coder pre-commit hook."""
    uninstall_hook()
