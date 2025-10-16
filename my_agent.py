"""
AWS Financial AI Agent - Main entrypoint

Bedrock AgentCore agent integrating Claude Sonnet 4.5 with
production Finance MCP server for real-time financial data.
"""

from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel

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
            tools = finance_client.list_tools_sync()

            # Create agent with finance tools
            agent = Agent(
                model=model,
                tools=tools,
                system_prompt="""You are a helpful AI assistant powered by Claude Sonnet 4.5.

You have access to financial market data tools including:
- Stock prices and market data
- Earnings reports and analyst estimates
- Treasury yields and economic indicators
- Analyst upgrades and downgrades

Use these tools to provide accurate, up-to-date financial information."""
            )

            # Execute agent query while MCP connection is still open
            result = agent(user_message)
            return {"result": result.message}

    except Exception as e:
        # Fallback to agent without MCP tools if connection fails
        print(f"Warning: Could not connect to Finance MCP server: {e}")
        agent = Agent(
            model=model,
            system_prompt="You are a helpful AI assistant powered by Claude Sonnet 4.5."
        )
        result = agent(user_message)
        return {"result": result.message}


if __name__ == "__main__":
    app.run()
