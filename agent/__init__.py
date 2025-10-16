"""
AWS Financial AI Agent

A Bedrock AgentCore agent integrating Claude Sonnet 4.5 with
production Finance MCP server.
"""

from .auth import OAuth2TokenProvider
from .mcp_client import create_finance_client
from .config import load_config

__all__ = [
    'OAuth2TokenProvider',
    'create_finance_client',
    'load_config',
]
