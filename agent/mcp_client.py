"""
MCP client creation and management for Finance tools.
"""

from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

from .auth import OAuth2TokenProvider
from .config import AgentConfig


def create_finance_client(config: AgentConfig) -> MCPClient:
    """
    Create an MCP client for Finance tools with OAuth2 authentication.

    Args:
        config: Agent configuration containing MCP server details

    Returns:
        MCPClient: Configured MCP client for Finance server
    """
    # Initialize OAuth2 token provider
    token_provider = OAuth2TokenProvider(
        token_url=config.auth_server_token_url,
        client_id=config.mcp_client_id,
        client_secret=config.mcp_client_secret
    )

    # Get OAuth2 token
    token = token_provider.get_token()

    # Create MCP client with Authorization header
    return MCPClient(
        lambda: streamablehttp_client(
            config.finance_mcp_url,
            headers={"Authorization": f"Bearer {token}"}
        )
    )
