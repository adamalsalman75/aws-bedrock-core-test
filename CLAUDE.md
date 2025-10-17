# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AWS Financial AI Agent using Amazon Bedrock AgentCore with Claude Sonnet 4.5 and a production Finance MCP (Model Context Protocol) server. The agent provides real-time stock prices, earnings reports, treasury yields, and analyst recommendations through OAuth2-secured MCP tools.

## Architecture

**Core Flow**: User → Bedrock AgentCore Runtime → Claude Sonnet 4.5 → Finance MCP Server (OAuth2) → Financial Tools

**Key Technologies**:
- **Bedrock AgentCore**: Serverless runtime for deploying AI agents on AWS
- **Strands Agents**: Agentic framework for tool orchestration
- **MCP Protocol**: Standard for connecting AI models to external tools
- **OAuth2**: Client credentials flow with Spring Authorization Server

**Authentication Flow**:
1. OAuth2TokenProvider requests token from AUTH_SERVER_TOKEN_URL with client credentials
2. Token includes scopes: `mcp:read mcp:write mcp:tools`
3. Token is cached with 60-second expiration buffer and auto-refreshed
4. MCP client includes `Authorization: Bearer {token}` header for all requests

**Important**: The MCP client must be kept open (using context manager) during agent execution. Closing the client prematurely will cause tool calls to fail.

## Project Structure

```
agent/                    # Core agent package
├── __init__.py          # Public API exports
├── auth.py              # OAuth2TokenProvider class
├── config.py            # Configuration loading with AgentConfig NamedTuple
└── mcp_client.py        # create_finance_client() factory

my_agent.py              # Bedrock AgentCore entrypoint (78 lines)
```

**Design Pattern**: Thin entrypoint delegates to well-organized package modules.

## Development Commands

### Running Locally

```bash
# Start the agent (auto-loads .env file)
uv run python my_agent.py

# The agent listens on port 8080
```

### Testing the Agent

```bash
# Test local agent
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the current stock price of TSLA?"}'
```

### Package Management

```bash
# Add dependency
uv add <package-name>

# Sync dependencies
uv sync

# Generate requirements.txt for deployment
uv pip freeze > requirements.txt
```

### AWS Commands

```bash
# Verify AWS credentials
aws sts get-caller-identity

# List available Claude models
aws bedrock list-foundation-models --region us-east-1 --by-provider anthropic

# Check model availability
aws bedrock get-foundation-model-availability \
  --region us-east-1 \
  --model-id anthropic.claude-sonnet-4-5-20250929-v1:0
```

## Deployment to AWS

### Configure and Deploy

```bash
# Configure the agent (auto-detects pyproject.toml)
agentcore configure -e my_agent.py --name financial_ai_agent

# Deploy (creates ECR, IAM role, AgentCore runtime)
agentcore launch \
  --env SECRET_NAME=finance-mcp-oauth2 \
  --env AUTH_SERVER_TOKEN_URL=https://auth.macrospire.com/oauth2/token \
  --env FINANCE_MCP_URL=https://finance.macrospire.com/mcp

# Test deployed agent
agentcore invoke '{"prompt": "What is the current stock price of TSLA?"}'
```

### Deployment Requirements

**Before deploying**, ensure:
1. OAuth2 credentials stored in AWS Secrets Manager (see docs/secrets-management.md)
2. Dependencies in `pyproject.toml` are up to date (AgentCore uses UV natively)
3. Docker Desktop is running (only if using `--local-build` mode)

**Required AWS Permissions**:
- `BedrockAgentCoreFullAccess` managed policy
- `AmazonBedrockFullAccess` managed policy
- Anthropic Claude Sonnet 4.5 enabled in Bedrock console

**What Gets Deployed**:
- OAuth2 credentials → AWS Secrets Manager
- Non-sensitive config (URLs) → Environment variables
- Agent code + dependencies (from `pyproject.toml`) → Docker container (UV) → ECR
- IAM execution role (auto-created) → Bedrock + Secrets Manager permissions

**What NOT to Deploy**:
- AWS credentials (runtime uses IAM execution role)
- `.env` file (secrets moved to Secrets Manager)
- `requirements.txt` (AgentCore uses `pyproject.toml` directly via UV)

## Configuration

### Environment Variables (Local Development)

Required in `.env` file:

```bash
# OAuth2 credentials for Finance MCP Server
AUTH_SERVER_TOKEN_URL=https://auth.macrospire.com/oauth2/token
MCP_CLIENT_ID=content-engine-client
MCP_CLIENT_SECRET=your-oauth-secret

# Finance MCP Server
FINANCE_MCP_URL=https://finance.macrospire.com/mcp

# AWS credentials (local only)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_DEFAULT_REGION=us-east-1
```

**Note**: Configuration is loaded via `python-dotenv` in `agent/config.py:32`. The `load_config()` function validates all required OAuth2 fields.

### AWS Deployment Configuration

For production deployment, `agent/config.py` should be updated to:
1. Read OAuth2 credentials from AWS Secrets Manager
2. Maintain environment variable fallback for local testing

## Code Architecture Details

### my_agent.py:26-74 (Main Entrypoint)

The `invoke()` function follows a graceful fallback pattern:
1. Attempts to create Finance MCP client with OAuth2
2. Keeps MCP connection open using context manager (`with finance_client`)
3. Lists available tools from MCP server
4. Creates Strands Agent with finance tools and Claude Sonnet 4.5
5. On failure, falls back to agent without MCP tools (prints warning)

**Critical**: Tool execution happens inside the `with finance_client:` block to maintain connection.

### agent/auth.py:10-64 (OAuth2TokenProvider)

Implements token caching with automatic refresh:
- Tokens cached in `_token` and `_expires_at` instance variables
- Refresh triggered when `datetime.now() >= _expires_at`
- 60-second expiration buffer to prevent race conditions
- Uses HTTP Basic Auth for client credentials
- Requests scope: `mcp:read mcp:write mcp:tools`

### agent/mcp_client.py:12-38 (create_finance_client)

Factory function that:
1. Creates OAuth2TokenProvider
2. Obtains initial token
3. Returns MCPClient with `streamablehttp_client` configured with Bearer token

**Important**: Token is obtained once at client creation. For long-running agents, consider implementing token refresh in the client.

### agent/config.py:10-51 (Configuration Management)

Uses `NamedTuple` for immutable configuration. Validates required fields and raises `ValueError` if missing. The `model_id` is hardcoded to Claude Sonnet 4.5 US cross-region inference profile.

## Strands Built-in Tools

The agent has access to strands-agents-tools (>=0.2.11) providing:

**File System**: `file_read` (multiple modes: view, find, lines, search, diff, time_machine), `file_write`, `editor` (view, create, str_replace, insert, undo_edit)

**Computation**: `calculator` (SymPy-powered math engine)

**Agent Control**: `think` (recursive reasoning), `stop` (terminate), `handoff_to_user` (pause for input)

**Data**: `retrieve` (Bedrock Knowledge Base), `current_time`

**Note**: File tools require user consent by default. Set `BYPASS_TOOL_CONSENT=true` for development.

## AWS Account Details

- **Account ID**: `090719695391`
- **Default Region**: `us-east-1`
- **Claude Model**: Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)
- **Inference**: Cross-region profile routes across us-east-1, us-east-2, us-west-2

## Common Issues

**Docker not running**: AgentCore requires Docker for local development. Ensure Docker Desktop is running.

**MCP connection fails**: Check OAuth2 credentials and token URL. Verify Finance MCP server is accessible. Review CloudWatch logs for authentication errors.

**Token expiration**: OAuth2TokenProvider auto-refreshes tokens. If issues persist, verify token endpoint returns valid `expires_in` field.

**Missing dependencies**: Run `uv sync` to ensure all dependencies from pyproject.toml are installed.