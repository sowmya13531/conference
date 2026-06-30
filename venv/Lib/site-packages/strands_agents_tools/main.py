"""Main module for strands-agents-tools."""

from strands_agents import main as agents_main

def get_agent_greeting():
    """Return the greeting from strands-agents."""
    return agents_main.hello()

def tools_hello():
    """Return a greeting message from tools."""
    return "Hello from strands-agents-tools!"

def main():
    """Run the main function."""
    print(tools_hello())
    print(f"Agent says: {get_agent_greeting()}")

if __name__ == "__main__":
    main()
