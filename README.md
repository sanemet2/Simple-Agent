# Simple OpenRouter Agent

Simple agent based on Pi, but implemented as a minimal Python/OpenRouter harness.

This project is for experimenting with:

- OpenRouter chat completions
- a basic model/tool loop
- local file tools guarded to one workspace
- confirmed writes/edits
- Docker-backed `bash` with network disabled by default
- optional JSONL session logging

It is intentionally small. It is not Pi, Codex, or a full sandbox product.

## Setup

Set an OpenRouter key:

```powershell
$env:OPENROUTER_API_KEY = "sk-or-..."
```

Or create `.env.local` in this folder:

```text
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=openai/gpt-4o-mini
```

Optional model override:

```powershell
$env:OPENROUTER_MODEL = "openai/gpt-4o-mini"
```

Docker is only required when the `bash` tool is enabled and used.

Pull the default bash image once if you do not already have it:

```powershell
docker pull python:3.12-slim
```

## Run

Start an interactive session from this folder:

```powershell
python agent.py
```

Run one prompt:

```powershell
python agent.py "list the files and explain this project"
```

Use a scratch workspace instead of this folder:

```powershell
python agent.py --workspace "C:\Users\franc\Desktop\agent-scratch"
```

Disable bash entirely:

```powershell
python agent.py --no-bash
```

Enable Docker network for bash commands:

```powershell
python agent.py --network
```

Append and resume session messages from JSONL:

```powershell
python agent.py --session ".sessions\first-run.jsonl"
```

## Safety Model

File tools only resolve paths inside the configured workspace. They refuse obvious sensitive paths like `.env`, `.ssh`, `.aws`, private-key-like files, and certificate/key suffixes.

`write_file`, `edit_file`, and `bash` ask for confirmation by default. `--yes` auto-approves them and should only be used inside a disposable workspace or real sandbox.

The bash tool runs commands like this:

```powershell
docker run --rm --pull never --network none -v "<workspace>:/workspace" -w /workspace python:3.12-slim bash -lc "<command>"
```

That means commands can modify mounted workspace files, but not your whole Windows home folder unless you mount it.

## Files

```text
agent.py                   launcher
simple_agent/config.py     CLI and environment config
simple_agent/loop.py       agent/control loop
simple_agent/openrouter.py OpenRouter HTTP client
simple_agent/tools.py      file tools and tool dispatch
simple_agent/docker_bash.py Docker-backed bash runner
simple_agent/safety.py     path checks, confirmations, truncation
simple_agent/sessions.py   JSONL session append helper
```
