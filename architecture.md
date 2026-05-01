# Simple Agent Architecture

## Import Dependency View

This view starts with `loop.py` because it is the easiest way to understand the
agent's behavior. `main.py` is shown as the wiring layer around it.

```mermaid
flowchart TB
    Agent["agent.py"] --> Main["main.py"]

    subgraph Top[" "]
        direction LR
        Config["config.py"]
        OpenRouter["openrouter.py"]
        Sessions["sessions.py"]
        Safety["safety.py"]
    end

    Loop["loop.py"]

    subgraph Bottom[" "]
        direction LR
        Tools["tools.py"]
        DockerBash["docker_bash.py"]
    end

    Main --> Config
    Main --> OpenRouter
    Main --> Loop
    Main --> Tools

    Loop --> Sessions
    Loop --> Tools

    Tools --> Safety
    Tools --> DockerBash
    DockerBash --> Safety
```

## Layered View

```mermaid
flowchart TB
    subgraph MainLayer["main.py wires concrete objects together"]
        direction TB
        Main2["main.py"]
    end

    subgraph TopHalf["modules with no local imports"]
        direction LR
        Config2["config.py"]
        OpenRouter2["openrouter.py"]
        Sessions2["sessions.py"]
        Safety2["safety.py"]
    end

    Loop2["loop.py"]

    subgraph BottomHalf["modules that import other local modules"]
        direction LR
        Tools2["tools.py"]
        DockerBash2["docker_bash.py"]
    end

    Main2 --> Config2
    Main2 --> OpenRouter2
    Main2 --> Loop2
    Main2 --> Tools2

    Loop2 --> Sessions2
    Loop2 --> Tools2
    Tools2 --> DockerBash2
    Tools2 --> Safety2
    DockerBash2 --> Safety2
```

## Runtime Loop View

This is what happens after you type a prompt.

```mermaid
sequenceDiagram
    participant User
    participant Main as main.py
    participant Loop as loop.py
    participant OR as ChatClient
    participant Tools as tools.py
    participant Bash as docker_bash.py

    User->>Main: prompt
    Main->>Loop: run_prompt(prompt)
    Loop->>OR: messages + tool schemas
    OR-->>Loop: final text or tool calls

    alt model requested tools
        Loop->>Tools: execute(tool_name, arguments)
        alt bash tool
            Tools->>Bash: run command in Docker
            Bash-->>Tools: exit code + stdout + stderr
        else file tool
            Tools-->>Loop: file result
        end
        Tools-->>Loop: tool result
        Loop->>OR: messages + tool result
    else final answer
        Loop-->>Main: answer
        Main-->>User: print answer
    end
```
