from __future__ import annotations

from .config import parse_args
from .loop import AgentLoop
from .openrouter import OpenRouterClient
from .tools import create_tool_registry


def main(argv: list[str] | None = None) -> int:
    """
    Main program entry point. Arguments are passed in via argv, and parse_args() separates them into config and an optional prompt
    If no configs are passed in the command line the defaults are used aside from OPENROUTER_API_KEY

    Runtime Object Setup:
        First, parse runtime inputs into:
        - config: model, workspace, Docker, bash, session, approval settings, etc. 
        - prompt: optional one-shot prompt from the command line
        - Makes sure the workspace folder exists, if not creates it

        Then create the core runtime objects:
        - client: OpenRouter connection that talks to the models
        - registry: stores the ToolRegistry object that executes local tools using settings from config. The tool definitions live in tools.py
        - loop: stores the AgentLoop object with the client, registry, and config settings
        - Note: the reason we use config.attributes in registry and loop is because some settings affect tools and others affect agent orchestration

    Runtime Actions:
        - Prints the workspace, the model, if bash is enabled and its docker settings, then a blank line
        - If prompt was passed in then it passes the prompt to the loop object and immediately exits the program
        - If no prompt was passed in, interactive mode starts and reads user_input in a loop until the user interrupts with the keyboard or exits with special keywords
        - In both cases the AgentLoop object uses its method run_prompt to run the prompt or user_input
    """
    ########################
    # Runtime Object Setup #
    ########################
    config, prompt = parse_args(argv)
    # prompt is only used later if the program runs in one-shot mode.
    config.workspace.mkdir(parents=True, exist_ok=True)

    client = OpenRouterClient(api_key=config.api_key, model=config.model)
    registry = create_tool_registry(
        workspace=config.workspace,
        allow_bash=config.allow_bash,
        docker_image=config.docker_image,
        docker_network=config.docker_network,
        auto_yes=config.auto_yes,
    )
    loop = AgentLoop(
        client=client,
        registry=registry,
        workspace=config.workspace,
        max_steps=config.max_steps,
        session_file=config.session_file,
        allow_bash=config.allow_bash,
    )

    ###################
    # Runtime Actions #
    ###################
    print(f"workspace: {config.workspace}")
    print(f"model: {config.model}")
    print(f"bash: {'enabled' if config.allow_bash else 'disabled'}")
    if config.allow_bash:
        print(f"docker image: {config.docker_image}")
        print(f"docker network: {'enabled' if config.docker_network else 'disabled'}")
    print()

    # One-shot mode
    if prompt:
        print(loop.run_prompt(prompt))
        return 0

    # Interactive mode
    print("Enter prompts. Use :quit to exit.")
    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not user_input:
            continue
        if user_input in {":q", ":quit", "exit"}:
            return 0
        print(loop.run_prompt(user_input))
