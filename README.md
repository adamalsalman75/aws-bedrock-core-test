# AWS Financial AI Agent

**AI-powered financial assistant** using Amazon Bedrock AgentCore with Claude Sonnet 4.5 and production Finance MCP tools.

## What This Agent Does

This agent combines AWS Bedrock's Claude Sonnet 4.5 with a production Finance MCP server to provide:

- 📈 **Real-time stock prices** and market data
- 💰 **Earnings reports** and analyst estimates
- 📊 **Treasury yields** and economic indicators
- 🎯 **Analyst upgrades/downgrades** and recommendations

The agent autonomously decides which financial tools to use based on your question.

## Quick Start

### Prerequisites

- Python 3.13 with [UV package manager](https://github.com/astral-sh/uv)
- Docker Desktop (for local development)
- AWS Account with Bedrock access
- Finance MCP Server credentials

### Local Setup

1. **Clone and install dependencies**:
   ```bash
   git clone <repo-url>
   cd aws-agent-core
   uv sync
   ```

2. **Configure environment** (see [docs/secrets-management.md](docs/secrets-management.md)):
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Run locally**:
   ```bash
   uv run python my_agent.py
   ```

4. **Test the agent**:
   ```bash
   curl -X POST http://localhost:8080/invocations \
     -H "Content-Type: application/json" \
     -d '{"prompt": "What is the current stock price of TSLA?"}'
   ```

## Architecture

```
User → Bedrock AgentCore Runtime → Claude Sonnet 4.5 → Finance MCP Server (OAuth2)
                                          ↓
                                    Financial Tools
```

**Key Components:**
- **Claude Sonnet 4.5**: Latest Anthropic model via AWS Bedrock cross-region inference
- **Strands Agents**: Agentic framework for tool orchestration ([docs/strands.md](docs/strands.md))
- **Finance MCP Server**: Production HTTP MCP server with OAuth2 authentication
- **Bedrock AgentCore**: Serverless runtime for AWS deployment

## Project Structure

```
aws-agent-core/
├── agent/              # Core agent package
│   ├── auth.py        # OAuth2 token management
│   ├── config.py      # Dual-mode config (local .env + AWS Secrets Manager)
│   └── mcp_client.py  # Finance MCP client factory
├── docs/              # Documentation
│   ├── agentcore-deployment.md    # AWS deployment guide
│   ├── aws-cli-authentication.md  # AWS credential setup
│   ├── secrets-management.md      # Local vs AWS secrets
│   └── strands.md                 # Strands framework guide
├── my_agent.py        # Main entrypoint
└── pyproject.toml     # UV dependencies
```

**Code Organization:**
- `agent/auth.py`: OAuth2 token provider with caching and auto-refresh
- `agent/config.py`: Loads secrets from `.env` (local) or AWS Secrets Manager (production)
- `agent/mcp_client.py`: Creates authenticated MCP client for Finance tools
- `my_agent.py`: Bedrock AgentCore entrypoint with graceful fallback

## Key Technologies

- **[AWS Bedrock](https://aws.amazon.com/bedrock/)**: Managed AI service with Claude models
- **[Strands Agents](https://strandsagents.com/)**: AWS-native agentic framework ([docs/strands.md](docs/strands.md))
- **[MCP](https://modelcontextprotocol.io/)**: Model Context Protocol for tool integration
- **[Bedrock AgentCore](https://github.com/awslabs/amazon-bedrock-agentcore-samples)**: Serverless agent runtime

## Documentation

Comprehensive guides in `/docs`:

- **[agentcore-deployment.md](docs/agentcore-deployment.md)**: Complete AWS deployment guide
  - Deployment modes (CodeBuild, local-build, local)
  - Configuration and environment variables
  - Monitoring, debugging, and cost optimization

- **[aws-cli-authentication.md](docs/aws-cli-authentication.md)**: AWS credential setup
  - Diagnosing invalid credentials
  - Using .env credentials vs ~/.aws/credentials
  - Profiles and AWS SSO

- **[secrets-management.md](docs/secrets-management.md)**: Local vs AWS secrets
  - .env file for local development
  - AWS Secrets Manager for production
  - How agent/config.py detects environment

- **[strands.md](docs/strands.md)**: Strands framework deep dive
  - Agent and model concepts
  - Built-in tools (file_read, calculator, etc.)
  - MCP integration
  - Advanced configuration

## Development Workflow

**Local Development:**
```bash
# Add dependency
uv add <package-name>

# Run locally
uv run python my_agent.py

# Test local endpoint
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is TSLA stock price?"}'
```

### Deploy to AWS

See [docs/agentcore-deployment.md](docs/agentcore-deployment.md) for complete deployment guide.

```bash
# 1. Configure AgentCore (auto-detects pyproject.toml)
uv run agentcore configure --entrypoint my_agent.py --name financial_ai_agent --region us-east-1

# 2. Deploy to AWS
uv run agentcore launch \
  --env SECRET_NAME=finance-mcp-oauth2 \
  --env AUTH_SERVER_TOKEN_URL=https://auth.macrospire.com/oauth2/token \
  --env FINANCE_MCP_URL=https://finance.macrospire.com/mcp

# 3. Test deployed agent
uv run agentcore invoke '{"prompt": "What is the current stock price of TSLA?"}'
```

## Resources

- [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [Strands Agents Documentation](https://strandsagents.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)

## Configuration

**AWS Account**: `090719695391`
**Region**: `us-east-1`
**Model**: Claude Sonnet 4.5 (cross-region inference profile)
**Secrets**: AWS Secrets Manager (`finance-mcp-oauth2`)

## License

[Your License Here]