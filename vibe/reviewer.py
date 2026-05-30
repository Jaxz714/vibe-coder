"""AI-powered code review using Claude."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from anthropic import Anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .config import Config

console = Console()

_SYSTEM_PROMPT = """\
You are an expert code reviewer.  When presented with source code, you:
1. Identify bugs, logic errors, and potential runtime issues.
2. Suggest improvements for readability, maintainability, and performance.
3. Flag any security concerns.
4. Be concise — use bullet points.  Prefix each finding with a severity tag: [BUG], [IMPROVEMENT], [SECURITY], [PERF].
"""


def _read_files(directory: Path) -> dict[str, str]:
    """Read source files from *directory* (skipping hidden dirs & __pycache__)."""
    skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache", ".ruff_cache"}
    extensions = {
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".go", ".rs", ".java", ".rb", ".php",
        ".c", ".cpp", ".h", ".hpp",
    }
    contents: dict[str, str] = {}
    for dirpath, dirnames, filenames in directory.resolve().walk():
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            p = Path(dirpath) / fname
            if p.suffix in extensions:
                try:
                    contents[str(p.relative_to(directory.resolve()))] = p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    pass
    return contents


def _git_diff() -> str:
    """Return the current ``git diff`` (unstaged + staged)."""
    try:
        unstaged = subprocess.check_output(["git", "diff"], text=True, stderr=subprocess.DEVNULL)
        staged = subprocess.check_output(["git", "diff", "--cached"], text=True, stderr=subprocess.DEVNULL)
        return (staged + "\n" + unstaged).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _build_prompt(file_map: dict[str, str]) -> str:
    parts: list[str] = []
    for relpath, content in file_map.items():
        ext = Path(relpath).suffix.lstrip(".")
        lang = ext if ext else "text"
        parts.append(f"### `{relpath}`\n```{lang}\n{content}\n```")
    return "\n\n".join(parts)


def review_files(directory: Path, cfg: Config) -> str:
    """Send all source files in *directory* to Claude for review. Returns the raw response text."""
    file_map = _read_files(directory)
    if not file_map:
        console.print("[yellow]No source files found to review.[/yellow]")
        return ""

    prompt_body = _build_prompt(file_map)
    user_prompt = (
        "Please review the following source files.  "
        "Focus on bugs, security issues, performance problems, and readability.\n\n"
        + prompt_body
    )
    return _call_claude(user_prompt, cfg)


def review_diff(cfg: Config) -> str:
    """Review only the current git diff."""
    diff = _git_diff()
    if not diff:
        console.print("[yellow]No git diff found (clean working tree?).[/yellow]")
        return ""
    user_prompt = (
        "Please review the following git diff.  "
        "Focus on bugs, security issues, performance problems, and readability.\n\n"
        f"```diff\n{diff}\n```"
    )
    return _call_claude(user_prompt, cfg)


def _call_claude(user_prompt: str, cfg: Config) -> str:
    """Call the Anthropic API and return the text response."""
    api_key = cfg.anthropic_api_key
    if not api_key:
        console.print("[bold red]Error:[/bold red] No Anthropic API key found. Set ANTHROPIC_API_KEY or configure it in vibe.yaml.")
        sys.exit(1)

    model = cfg.get("review.model", "claude-sonnet-4-6")
    max_tokens = cfg.get("review.max_tokens", 4096)

    client = Anthropic(api_key=api_key)
    with console.status("[bold cyan]Sending code to Claude for review..."):
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    # Extract text from the response content blocks.
    text_parts = [block.text for block in message.content if hasattr(block, "text")]
    return "\n".join(text_parts)


def display_review(text: str) -> None:
    """Render the review text as rich Markdown inside a panel."""
    if not text:
        return
    console.print()
    console.print(Panel(Markdown(text), title="Code Review", border_style="cyan", expand=False))
