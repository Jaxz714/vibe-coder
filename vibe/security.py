"""Pattern-based security scanner."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

console = Console()

_PATTERNS_FILE = Path(__file__).resolve().parent.parent / "patterns" / "security.yaml"


@dataclass
class Finding:
    """A single security finding."""

    filepath: str
    line_number: int
    line_text: str
    pattern_name: str
    severity: str  # high / medium / low
    description: str


@dataclass
class ScanResult:
    """Aggregated results of a security scan."""

    findings: list[Finding] = field(default_factory=list)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "medium")

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "low")

    @property
    def total(self) -> int:
        return len(self.findings)


def _load_patterns() -> list[dict]:
    """Load security patterns from the YAML config."""
    if not _PATTERNS_FILE.exists():
        console.print(f"[yellow]Warning:[/yellow] Patterns file not found at {_PATTERNS_FILE}. Using built-in defaults.")
        return _builtin_patterns()
    with open(_PATTERNS_FILE, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data.get("patterns", [])


def _builtin_patterns() -> list[dict]:
    """Fallback built-in patterns if the YAML file is missing."""
    return [
        {
            "name": "hardcoded_api_key",
            "regex": r"""(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?token)\s*[=:]\s*['"][A-Za-z0-9+/=_\-]{16,}['"]""",
            "severity": "high",
            "description": "Possible hardcoded API key or secret token.",
        },
        {
            "name": "hardcoded_password",
            "regex": r"""(?:password|passwd|pwd)\s*[=:]\s*['"][^'"]{4,}['"]""",
            "severity": "high",
            "description": "Possible hardcoded password.",
        },
        {
            "name": "sql_injection_format",
            "regex": r"""(?:execute|cursor\.execute|query)\s*\(\s*f['"]|\.format\(|%\s*\(.*(?:SELECT|INSERT|UPDATE|DELETE)""",
            "severity": "high",
            "description": "Possible SQL injection via string formatting.",
        },
        {
            "name": "sql_injection_concat",
            "regex": r"""(?:SELECT|INSERT|UPDATE|DELETE)\b.*['"]\s*\+\s*\w+""",
            "severity": "high",
            "description": "Possible SQL injection via string concatenation.",
        },
        {
            "name": "dangerous_eval",
            "regex": r"""\b(?:eval|exec)\s*\(""",
            "severity": "high",
            "description": "Use of eval/exec — potential code injection.",
        },
        {
            "name": "shell_true",
            "regex": r"""subprocess\.\w+\(.*shell\s*=\s*True""",
            "severity": "medium",
            "description": "subprocess call with shell=True — potential command injection.",
        },
        {
            "name": "xss_innerhtml",
            "regex": r"""\.innerHTML\s*=""",
            "severity": "medium",
            "description": "Direct innerHTML assignment — possible XSS vector.",
        },
        {
            "name": "xss_document_write",
            "regex": r"""document\.write\s*\(""",
            "severity": "medium",
            "description": "document.write usage — possible XSS vector.",
        },
        {
            "name": "debug_enabled",
            "regex": r"""DEBUG\s*=\s*True""",
            "severity": "low",
            "description": "DEBUG mode appears to be enabled.",
        },
        {
            "name": "http_url",
            "regex": r"""['"]http://[^'"]+['"]""",
            "severity": "low",
            "description": "Plain HTTP URL — consider using HTTPS.",
        },
    ]


def scan_file(filepath: Path, patterns: list[dict]) -> list[Finding]:
    """Scan a single file against all patterns."""
    findings: list[Finding] = []
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings

    for lineno, line in enumerate(text.splitlines(), start=1):
        for pat in patterns:
            try:
                if re.search(pat["regex"], line, re.IGNORECASE):
                    findings.append(
                        Finding(
                            filepath=str(filepath),
                            line_number=lineno,
                            line_text=line.rstrip(),
                            pattern_name=pat["name"],
                            severity=pat.get("severity", "medium"),
                            description=pat.get("description", ""),
                        )
                    )
            except re.error:
                pass
    return findings


def _collect_files(directory: Path) -> list[Path]:
    """Collect source files to scan."""
    skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache", ".ruff_cache"}
    extensions = {
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".go", ".rs", ".java", ".rb", ".php",
        ".c", ".cpp", ".h", ".hpp", ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini", ".env",
    }
    files: list[Path] = []
    for dirpath, dirnames, filenames in directory.resolve().walk():
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            p = Path(dirpath) / fname
            if p.suffix in extensions or fname in {".env", ".env.local", ".env.production"}:
                files.append(p)
    return files


def scan_directory(directory: Path) -> ScanResult:
    """Run the security scanner over all files in *directory*."""
    patterns = _load_patterns()
    result = ScanResult()
    for filepath in _collect_files(directory):
        result.findings.extend(scan_file(filepath, patterns))
    return result


def display_scan_result(result: ScanResult, directory: Path) -> None:
    """Render scan results as a rich table."""
    if result.total == 0:
        console.print("[bold green]No security issues found.[/bold green]")
        return

    table = Table(title=f"Security Scan — {directory}", border_style="red")
    table.add_column("Severity", style="bold", width=10)
    table.add_column("File", max_width=50)
    table.add_column("Line", width=6, justify="right")
    table.add_column("Pattern", max_width=25)
    table.add_column("Detail", max_width=60)

    severity_styles = {"high": "[bold red]HIGH[/bold red]", "medium": "[yellow]MEDIUM[/yellow]", "low": "[dim]LOW[/dim]"}

    for f in sorted(result.findings, key=lambda x: ("high", "medium", "low").index(x.severity)):
        table.add_row(
            severity_styles.get(f.severity, f.severity),
            f.filepath,
            str(f.line_number),
            f.pattern_name,
            f.description,
        )

    console.print()
    console.print(table)
    console.print(
        f"\nTotal: [bold]{result.total}[/bold] findings "
        f"([red]{result.high_count} high[/red], "
        f"[yellow]{result.medium_count} medium[/yellow], "
        f"[dim]{result.low_count} low[/dim])"
    )
