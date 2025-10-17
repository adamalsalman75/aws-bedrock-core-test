"""
AWS Financial AI Agent - Main entrypoint

Bedrock AgentCore agent integrating Claude Sonnet 4.5 with
production Finance MCP server for real-time financial data and
file system operations for code generation.
"""

from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel
from strands_tools import file_read, file_write, editor

from agent import create_finance_client, load_config

# Initialize Bedrock AgentCore application
app = BedrockAgentCoreApp()

# Load configuration
config = load_config()

# Configure Claude Sonnet 4.5 via Bedrock US inference profile
# This routes requests across US regions (us-east-1, us-east-2, us-west-2)
model = BedrockModel(model_id=config.model_id)


@app.entrypoint
def invoke(payload: dict) -> dict:
    """
    AI agent invocation endpoint.

    Args:
        payload: Request payload containing 'prompt' key

    Returns:
        dict: Agent response with 'result' key
    """
    user_message = payload.get("prompt", "Hello! How can I help you today?")

    # Try to use Finance MCP tools
    try:
        finance_client = create_finance_client(config)

        # Keep MCP connection open during agent execution
        with finance_client:
            # Get tools from MCP server
            mcp_tools = finance_client.list_tools_sync()

            # Combine MCP tools with file system tools
            all_tools = mcp_tools + [file_read, file_write, editor]

            # Create agent with finance and file tools
            agent = Agent(
                model=model,
                tools=all_tools,
                system_prompt="""You are a helpful AI assistant powered by Claude Sonnet 4.5.

You have access to financial market data tools including:
- Stock prices and market data
- Earnings reports and analyst estimates
- Treasury yields and economic indicators
- Analyst upgrades and downgrades

You also have file system tools for code generation:
- file_read: Read files, list directories, search for files
- file_write: Create new files or overwrite existing files
- editor: Edit existing files using search and replace

Use these tools to provide accurate financial information and assist with code generation tasks."""
            )

            # Execute agent query while MCP connection is still open
            result = agent(user_message)
            return {"result": result.message}

    except Exception as e:
        # Fallback to agent with only file tools if MCP connection fails
        print(f"Warning: Could not connect to Finance MCP server: {e}")
        agent = Agent(
            model=model,
            tools=[file_read, file_write, editor],
            system_prompt="""You are a helpful AI assistant powered by Claude Sonnet 4.5.

You have file system tools for code generation:
- file_read: Read files, list directories, search for files
- file_write: Create new files or overwrite existing files
- editor: Edit existing files using search and replace

Use these tools to assist with code generation and file management tasks."""
        )
        result = agent(user_message)
        return {"result": result.message}


if __name__ == "__main__":
    app.run()
