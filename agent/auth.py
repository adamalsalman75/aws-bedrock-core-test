"""
OAuth2 authentication for MCP server access.
"""

import requests
from datetime import datetime, timedelta
from typing import Optional


class OAuth2TokenProvider:
    """
    Obtains and caches OAuth2 tokens from Spring Authorization Server.

    Automatically refreshes tokens before expiration.
    """

    def __init__(self, token_url: str, client_id: str, client_secret: str):
        """
        Initialize OAuth2 token provider.

        Args:
            token_url: OAuth2 token endpoint URL
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
        """
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._expires_at: Optional[datetime] = None

    def get_token(self) -> str:
        """
        Get a valid access token, refreshing if needed.

        Returns:
            str: Valid OAuth2 access token

        Raises:
            requests.HTTPError: If token request fails
        """
        # Return cached token if still valid
        if self._token and self._expires_at and datetime.now() < self._expires_at:
            return self._token

        # Request new token
        response = requests.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "scope": "mcp:read mcp:write mcp:tools"
            },
            auth=(self.client_id, self.client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()

        # Cache token with expiration (60 seconds buffer)
        token_data = response.json()
        self._token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        self._expires_at = datetime.now() + timedelta(seconds=expires_in - 60)

        return self._token
