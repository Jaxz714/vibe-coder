# Vibe Coder

Quality guardrails for AI coding workflows. Automatically add code review, test generation, security scanning, and performance checks to your vibe coding sessions.

## Features

- **Code Review** — AI-powered review using Claude (find bugs, suggest improvements)
- **Test Generation** — Auto-generate unit tests for your source files
- **Security Scanning** — Pattern-based detection of hardcoded secrets, SQL injection, XSS, and dangerous functions
- **Watch Mode** — Monitor a directory for file changes, auto-run quality checks
- **Quality Reports** — Generate a full Markdown report combining all checks
- **Pre-commit Hooks** — Integrate security scanning into your git workflow

## Installation

```bash
pip install vibe-coder
```

Or install from source:

```bash
git clone https://github.com/Jaxz714/vibe-coder.git
cd vibe-coder
pip install -e .
```

## Quick Start

```bash
# AI code review
vibe review src/

# Review only git diff changes
vibe review --diff

# Generate unit tests
vibe testgen src/

# Security scan
vibe scan src/

# Full quality report
vibe report src/

# Watch mode
vibe watch src/

# Install pre-commit hook
vibe hooks install
```

## Configuration

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Or create a `vibe.yaml` in your project root:

```yaml
anthropic:
  api_key: "sk-ant-..."

review:
  model: "claude-sonnet-4-20250514"
  max_tokens: 4096

testgen:
  model: "claude-sonnet-4-20250514"
  max_tokens: 4096
```

## Security Patterns

The scanner checks for:

- Hardcoded API keys, passwords, AWS keys, private keys
- SQL injection risks (string formatting in queries)
- Dangerous functions (`eval`, `exec`, `subprocess` with `shell=True`, `pickle.load`)
- Common XSS patterns (`innerHTML`, `document.write`)

Custom patterns can be added to `patterns/security.yaml`.

## License

MIT — Copyright (c) 2026 Jaxz714
