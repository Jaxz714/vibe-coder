"""Automatic unit-test generation using Claude."""

from __future__ import annotations

import sys
from pathlib import Path

from anthropic import Anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .config import Config

console = Console()

_SYSTEM_PROMPT = """\
You are an expert test engineer.  Given a source file, generate comprehensive unit tests.

Rules:
1. Use pytest as the test framework.
2. Cover happy paths, edge cases, and error conditions.
3. Use descriptive test names that explain the scenario.
4. Keep tests isolated — mock external dependencies.
5. Output ONLY the test code inside a single ```python``` code fence.  No extra commentary.
"""


def _read_source_files(directory: Path) -> dict[str, str]:
    """Read source files, skipping tests, hidden dirs, caches."""
    skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", "tests", "test", ".mypy_cache", ".ruff_cache"}
    extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"}
    contents: dict[str, str] = {}
    for dirpath, dirnames, filenames in directory.resolve().walk():
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            p = Path(dirpath) / fname
            if p.suffix in extensions and "test" not in fname.lower():
                try:
                    contents[str(p.relative_to(directory.resolve()))] = p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    pass
    return contents


def _build_prompt(file_map: dict[str, str]) -> str:
    parts: list[str] = []
    for relpath, content in file_map.items():
        ext = Path(relpath).suffix.lstrip(".")
        lang = ext if ext else "text"
        parts.append(f"### `{relpath}`\n```{lang}\n{content}\n```")
    return "\n\n".join(parts)


def generate_tests(directory: Path, cfg: Config, *, output_dir: Path | None = None) -> dict[str, str]:
    """Generate tests for source files in *directory*.

    Returns a mapping ``{original_relpath: generated_test_code}``.
    If *output_dir* is given, test files are also written to disk.
    """
    file_map = _read_source_files(directory)
    if not file_map:
        console.print("[yellow]No source files found to generate tests for.[/yellow]")
        return {}

    results: dict[str, str] = {}
    api_key = cfg.anthropic_api_key
    if not api_key:
        console.print("[bold red]Error:[/bold red] No Anthropic API key found. Set ANTHROPIC_API_KEY or configure it in vibe.yaml.")
        sys.exit(1)

    model = cfg.get("testgen.model", "claude-sonnet-4-6")
    max_tokens = cfg.get("testgen.max_tokens", 4096)
    client = Anthropic(api_key=api_key)

    for relpath, content in file_map.items():
        user_prompt = (
            f"Generate unit tests for the following file (`{relpath}`).\n\n"
            f"```{Path(relpath).suffix.lstrip('.')}\n{content}\n```"
        )
        with console.status(f"[bold cyan]Generating tests for {relpath}..."):
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
        text_parts = [block.text for block in message.content if hasattr(block, "text")]
        test_code = "\n".join(text_parts)
        results[relpath] = test_code

        if output_dir:
            test_filename = f"test_{Path(relpath).stem}.py"
            test_path = output_dir / test_filename
            test_path.parent.mkdir(parents=True, exist_ok=True)
            # Strip markdown fences if present.
            cleaned = test_code.strip()
            if cleaned.startswith("```"):
                # Remove opening fence (possibly with language tag) and closing fence.
                lines = cleaned.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = "\n".join(lines)
            test_path.write_text(cleaned, encoding="utf-8")
            console.print(f"  [green]Written:[/green] {test_path}")

    return results


def display_testgen(results: dict[str, str]) -> None:
    """Render generated tests as rich Markdown panels."""
    for relpath, code in results.items():
        console.print()
        console.print(Panel(Markdown(code), title=f"Tests for {relpath}", border_style="green", expand=False))
