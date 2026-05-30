"""File-change watcher — monitors a directory and triggers quality checks."""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.live import Live
from rich.table import Table

console = Console()

# Poll interval in seconds.
_POLL_INTERVAL = 1.5

# File extensions to watch.
_WATCH_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".go", ".rs", ".java", ".rb", ".php",
    ".c", ".cpp", ".h", ".hpp",
}


def _file_hash(path: Path) -> str:
    """Return a sha256 hex digest of *path*'s contents."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _collect_files(root: Path) -> dict[Path, str]:
    """Walk *root* and return ``{path: hash}`` for watched extensions."""
    files: dict[Path, str] = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in filenames:
            p = Path(dirpath) / fname
            if p.suffix in _WATCH_EXTENSIONS and ".git" not in p.parts:
                try:
                    files[p] = _file_hash(p)
                except OSError:
                    pass
    return files


def _build_status_table(changed: list[Path], added: list[Path], removed: list[Path]) -> Table:
    table = Table(title="Vibe Watcher", border_style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("File")
    for p in changed:
        table.add_row("[yellow]CHANGED[/yellow]", str(p))
    for p in added:
        table.add_row("[green]ADDED[/green]", str(p))
    for p in removed:
        table.add_row("[red]REMOVED[/red]", str(p))
    return table


class FileWatcher:
    """Simple poll-based file watcher.

    Parameters
    ----------
    root : Path
        Directory to monitor.
    on_change : Callable[[list[Path]], None]
        Callback invoked with the list of changed/added file paths.
    """

    def __init__(self, root: Path, on_change: Callable[[list[Path]], None]) -> None:
        self.root = root.resolve()
        self.on_change = on_change
        self._snapshot: dict[Path, str] = {}
        self._running = False

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self, *, poll_interval: float = _POLL_INTERVAL) -> None:
        """Start watching.  Blocks until interrupted (KeyboardInterrupt)."""
        self._snapshot = _collect_files(self.root)
        self._running = True
        console.print(f"[bold cyan]Watching[/bold cyan] {self.root}  (Ctrl-C to stop)")
        try:
            while self._running:
                time.sleep(poll_interval)
                self._tick()
        except KeyboardInterrupt:
            console.print("\n[bold]Watcher stopped.[/bold]")

    def stop(self) -> None:
        self._running = False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        current = _collect_files(self.root)

        changed: list[Path] = []
        added: list[Path] = []
        removed: list[Path] = []

        for path, h in current.items():
            if path not in self._snapshot:
                added.append(path)
            elif self._snapshot[path] != h:
                changed.append(path)

        for path in self._snapshot:
            if path not in current:
                removed.append(path)

        if not (changed or added or removed):
            return

        table = _build_status_table(changed, added, removed)
        console.print(table)

        affected = changed + added
        if affected:
            try:
                self.on_change(affected)
            except Exception as exc:
                console.print(f"[bold red]Callback error:[/bold red] {exc}")

        self._snapshot = current
