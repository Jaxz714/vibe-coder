[English](README.md) | [中文](README_CN.md)

# Vibe Coder

为 AI 编码工作流提供质量保障。自动为你的 Vibe Coding 会话添加代码审查、测试生成、安全扫描和性能检查。

## 功能特性

- **代码审查** — 基于 Claude 的 AI 代码审查（发现 bug、提出改进建议）
- **测试生成** — 为源文件自动生成单元测试
- **安全扫描** — 基于模式检测硬编码密钥、SQL 注入、XSS 和危险函数
- **监听模式** — 监控目录文件变更，自动运行质量检查
- **质量报告** — 生成整合所有检查项的完整 Markdown 报告
- **Pre-commit 钩子** — 将安全扫描集成到 Git 工作流中

## 安装

```bash
pip install vibe-coder
```

或从源码安装：

```bash
git clone https://github.com/Jaxz714/vibe-coder.git
cd vibe-coder
pip install -e .
```

## 快速开始

```bash
# AI 代码审查
vibe review src/

# 仅审查 git diff 变更
vibe review --diff

# 生成单元测试
vibe testgen src/

# 安全扫描
vibe scan src/

# 完整质量报告
vibe report src/

# 监听模式
vibe watch src/

# 安装 pre-commit 钩子
vibe hooks install
```

## 配置

设置你的 Anthropic API key：

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

或在项目根目录创建 `vibe.yaml` 文件：

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

## 安全模式

扫描器会检测以下内容：

- 硬编码的 API key、密码、AWS 密钥、私钥
- SQL 注入风险（查询中的字符串拼接）
- 危险函数（`eval`、`exec`、`subprocess` 配合 `shell=True`、`pickle.load`）
- 常见 XSS 模式（`innerHTML`、`document.write`）

可在 `patterns/security.yaml` 中添加自定义模式。

## 许可证

MIT — Copyright (c) 2026 Jaxz714
