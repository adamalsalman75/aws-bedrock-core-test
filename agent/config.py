"""
Configuration management for the agent.
"""

import json
import os
from typing import NamedTuple, Optional
from dotenv import load_dotenv


class AgentConfig(NamedTuple):
    """Configuration for the AI agent."""
    model_id: str
    finance_mcp_url: str
    auth_server_token_url: str
    mcp_client_id: str
    mcp_client_secret: str


def _get_secret_from_aws(secret_name: str, region: str = "us-east-1") -> Optional[dict]:
    """
    Retrieve secret from AWS Secrets Manager.

    Args:
        secret_name: Name of the secret in Secrets Manager
        region: AWS region (default: us-east-1)

    Returns:
        dict: Secret key-value pairs, or None if not available
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client('secretsmanager', region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except (ImportError, ClientError, KeyError):
        # boto3 not available, or secret not found, or IAM permissions missing
        return None


def load_config() -> AgentConfig:
    """
    Load configuration from environment variables or AWS Secrets Manager.

    Local Development:
    - Loads from .env file via environment variables

    AWS Deployment:
    - Loads OAuth2 credentials from Secrets Manager if SECRET_NAME is set
    - Falls back to environment variables if secret not found

    Returns:
        AgentConfig: Loaded configuration

    Raises:
        ValueError: If required environment variables are missing
    """
    # Load .env file for local development (no-op if not present)
    load_dotenv()

    # Check if running in AWS with Secrets Manager
    secret_name = os.getenv("SECRET_NAME")
    secret_data = None

    if secret_name:
        # Running in AWS - try to load from Secrets Manager
        region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        secret_data = _get_secret_from_aws(secret_name, region)

    # Get OAuth2 credentials: Secrets Manager first, then environment variables
    if secret_data:
        mcp_client_id = secret_data.get("MCP_CLIENT_ID")
        mcp_client_secret = secret_data.get("MCP_CLIENT_SECRET")
    else:
        mcp_client_id = os.getenv("MCP_CLIENT_ID")
        mcp_client_secret = os.getenv("MCP_CLIENT_SECRET")

    # Build config
    config = AgentConfig(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        finance_mcp_url=os.getenv("FINANCE_MCP_URL", "https://finance.macrospire.com/mcp"),
        auth_server_token_url=os.getenv("AUTH_SERVER_TOKEN_URL"),
        mcp_client_id=mcp_client_id,
        mcp_client_secret=mcp_client_secret,
    )

    # Validate required fields
    if not config.auth_server_token_url:
        raise ValueError("AUTH_SERVER_TOKEN_URL environment variable is required")
    if not config.mcp_client_id:
        raise ValueError("MCP_CLIENT_ID is required (from SECRET_NAME or environment)")
    if not config.mcp_client_secret:
        raise ValueError("MCP_CLIENT_SECRET is required (from SECRET_NAME or environment)")

    return config
