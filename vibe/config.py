"""Configuration management for Vibe Coder."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "default.yaml"


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* (returns a new dict)."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class Config:
    """Hierarchical configuration backed by YAML files."""

    def __init__(self, overrides: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = {}
        self._load_defaults()
        self._load_project_config()
        if overrides:
            self._data = _deep_merge(self._data, overrides)

    # ------------------------------------------------------------------
    # Loading helpers
    # ------------------------------------------------------------------

    def _load_defaults(self) -> None:
        if _DEFAULT_CONFIG_PATH.exists():
            with open(_DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as fh:
                self._data = yaml.safe_load(fh) or {}

    def _load_project_config(self) -> None:
        """Look for ``vibe.yaml`` / ``.vibe.yaml`` in the cwd and parents."""
        for name in ("vibe.yaml", ".vibe.yaml"):
            cfg_path = self._find_upwards(Path.cwd(), name)
            if cfg_path:
                with open(cfg_path, "r", encoding="utf-8") as fh:
                    project_cfg = yaml.safe_load(fh) or {}
                self._data = _deep_merge(self._data, project_cfg)
                break

    @staticmethod
    def _find_upwards(start: Path, filename: str) -> Path | None:
        current = start.resolve()
        while True:
            candidate = current / filename
            if candidate.exists():
                return candidate
            parent = current.parent
            if parent == current:
                return None
            current = parent

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Retrieve a value using dot-notation (e.g. ``review.model``)."""
        keys = dotted_key.split(".")
        node: Any = self._data
        for k in keys:
            if isinstance(node, dict):
                node = node.get(k)
            else:
                return default
            if node is None:
                return default
        return node

    @property
    def anthropic_api_key(self) -> str | None:
        """Return the Anthropic API key from config *or* environment."""
        key = self.get("anthropic.api_key")
        if key:
            return key
        return os.environ.get("ANTHROPIC_API_KEY")

    @property
    def raw(self) -> dict[str, Any]:
        return self._data
