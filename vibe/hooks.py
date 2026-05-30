"""Git pre-commit hook integration."""

from __future__ import annotations

import stat
import subprocess
import sys
from pathlib import Path

from rich.console import Console

console = Console()

_HOOK_SCRIPT = """\
#!/usr/bin/env bash
# Vibe Coder pre-commit hook
# Installed by: vibe hooks install

set -e

echo ">>> Vibe Coder: running security scan on staged files..."

# Collect staged source files.
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\\.(py|js|ts|jsx|tsx|go|rs|java|rb|php|c|cpp|h|hpp)$' || true)

if [ -z "$STAGED_FILES" ]; then
    echo "    No source files staged — skipping."
    exit 0
fi

# Run vibe scan on the repo root (it will scan all files, but this is fast).
vibe scan . --quiet || {
    echo ""
    echo "!!! Vibe Coder security scan found issues. Commit aborted."
    echo "    Fix the findings above, or use 'git commit --no-verify' to bypass."
    exit 1
}

echo ">>> Vibe Coder: security scan passed."
"""


def _find_git_root() -> Path | None:
    """Return the root of the current git repo, or *None*."""
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return Path(root)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def install_hook() -> None:
    """Install the vibe-coder pre-commit hook."""
    git_root = _find_git_root()
    if git_root is None:
        console.print("[bold red]Error:[/bold red] Not inside a git repository.")
        sys.exit(1)

    hooks_dir = git_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-commit"

    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8")
        if "Vibe Coder pre-commit hook" in existing:
            console.print("[yellow]Hook already installed. Overwriting...[/yellow]")
        else:
            console.print("[yellow]A pre-commit hook already exists. Backing it up.[/yellow]")
            backup = hook_path.with_suffix(".bak")
            backup.write_text(existing, encoding="utf-8")
            console.print(f"  Backup saved to {backup}")

    hook_path.write_text(_HOOK_SCRIPT, encoding="utf-8")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    console.print(f"[bold green]Hook installed at[/bold green] {hook_path}")


def uninstall_hook() -> None:
    """Remove the vibe-coder pre-commit hook (if it was installed by us)."""
    git_root = _find_git_root()
    if git_root is None:
        console.print("[bold red]Error:[/bold red] Not inside a git repository.")
        sys.exit(1)

    hook_path = git_root / ".git" / "hooks" / "pre-commit"
    if not hook_path.exists():
        console.print("[yellow]No pre-commit hook found.[/yellow]")
        return

    content = hook_path.read_text(encoding="utf-8")
    if "Vibe Coder pre-commit hook" not in content:
        console.print("[yellow]The existing hook was not installed by Vibe Coder. Leaving it untouched.[/yellow]")
        return

    hook_path.unlink()
    console.print("[bold green]Hook removed.[/bold green]")
