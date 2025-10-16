"""
Configuration management for the agent.
"""

import os
from typing import NamedTuple
from dotenv import load_dotenv


class AgentConfig(NamedTuple):
    """Configuration for the AI agent."""
    model_id: str
    finance_mcp_url: str
    auth_server_token_url: str
    mcp_client_id: str
    mcp_client_secret: str


def load_config() -> AgentConfig:
    """
    Load configuration from environment variables.

    Automatically loads from .env file if present.

    Returns:
        AgentConfig: Loaded configuration

    Raises:
        ValueError: If required environment variables are missing
    """
    # Load .env file (no-op if already loaded or file doesn't exist)
    load_dotenv()

    # Get required environment variables
    config = AgentConfig(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        finance_mcp_url=os.getenv("FINANCE_MCP_URL", "https://finance.macrospire.com/mcp"),
        auth_server_token_url=os.getenv("AUTH_SERVER_TOKEN_URL"),
        mcp_client_id=os.getenv("MCP_CLIENT_ID"),
        mcp_client_secret=os.getenv("MCP_CLIENT_SECRET"),
    )

    # Validate required fields
    if not config.auth_server_token_url:
        raise ValueError("AUTH_SERVER_TOKEN_URL environment variable is required")
    if not config.mcp_client_id:
        raise ValueError("MCP_CLIENT_ID environment variable is required")
    if not config.mcp_client_secret:
        raise ValueError("MCP_CLIENT_SECRET environment variable is required")

    return config
