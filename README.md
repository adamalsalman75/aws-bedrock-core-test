# AWS Financial AI Agent

**AI-powered financial assistant** using Amazon Bedrock AgentCore with Claude Sonnet 4.5 and production Finance MCP tools.

## What This Agent Does

This agent combines AWS Bedrock's Claude Sonnet 4.5 with your production Finance MCP server to provide:

- 📈 **Real-time stock prices** and market data
- 💰 **Earnings reports** and analyst estimates
- 📊 **Treasury yields** and economic indicators
- 🎯 **Analyst upgrades/downgrades** and recommendations

The agent autonomously decides which financial tools to use based on your question.

## Architecture

```
User → Bedrock AgentCore Runtime → Claude Sonnet 4.5 → Finance MCP Server (OAuth2)
                                          ↓
                                    Financial Tools
```

**Key Components:**
- **Claude Sonnet 4.5** - Latest Anthropic model via AWS Bedrock cross-region inference
- **Strands Agents** - Agentic framework for tool orchestration
- **Finance MCP Server** - Production HTTP MCP server with OAuth2 authentication
- **Bedrock AgentCore** - Serverless runtime for deployment

## Prerequisites

- **AWS Account**: `090719695391` (configured)
- **Python 3.13** with UV package manager
- **Docker Desktop** (running)
- **Finance MCP Server** access with OAuth2 credentials

## Environment Setup

Your `.env` file contains:

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_DEFAULT_REGION=us-east-1

# OAuth2 credentials for Finance MCP Server
AUTH_SERVER_TOKEN_URL=https://auth.macrospire.com/oauth2/token
MCP_CLIENT_ID=content-engine-client
MCP_CLIENT_SECRET=your-oauth-secret

# Finance MCP Server
FINANCE_MCP_URL=https://finance.macrospire.com/mcp
```

## Running the Agent Locally

### Start the Agent

```bash
# The agent automatically loads .env file
uv run python my_agent.py
```

The agent will:
1. Load configuration from `.env` file
2. Authenticate with your OAuth2 server
3. Connect to your Finance MCP server
4. Load all available financial tools
5. Start listening on port 8080

**Note**: Environment variables are automatically loaded via `python-dotenv`. No need to manually source `.env`!

### Test the Agent

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the current stock price of TSLA?"}'
```

The agent will:
- Receive your question
- Determine which finance tools to use
- Fetch real-time data from your MCP server
- Generate a comprehensive response with Claude Sonnet 4.5

## Project Structure

```
aws-agent-core/
├── agent/                      # Core agent package
│   ├── __init__.py            # Package initialization
│   ├── auth.py                # OAuth2TokenProvider class
│   ├── config.py              # Configuration management
│   └── mcp_client.py          # MCP client creation
├── my_agent.py                # Main entrypoint (78 lines)
├── pyproject.toml             # UV project configuration
├── .env                       # Credentials (gitignored)
├── .gitignore                 # Security exclusions
├── PLAN.md                    # Deployment plan
└── README.md                  # This file
```

### Code Organization

The project follows Python best practices with clear separation of concerns:

- **`agent/auth.py`** - OAuth2 authentication logic for MCP server
- **`agent/config.py`** - Environment-based configuration loading
- **`agent/mcp_client.py`** - Finance MCP client factory
- **`my_agent.py`** - Bedrock AgentCore entrypoint (thin, delegates to package)

## Key Technologies

- **AWS Bedrock** - Managed AI service with Claude Sonnet 4.5
- **Strands Agents** - Python agentic framework
- **MCP (Model Context Protocol)** - Standard for connecting AI to tools
- **OAuth2** - Secure authentication with Spring Authorization Server
- **Bedrock AgentCore** - Serverless runtime for production deployment

## Dependencies

Installed via `uv`:

```toml
bedrock-agentcore = ">=1.0.3"
strands-agents = ">=1.12.0"
bedrock-agentcore-starter-toolkit = ">=0.1.25"
mcp = ">=1.17.0"
strands-agents-tools = ">=0.2.11"  # Built-in tools
```

## Built-in Tools with Strands

Strands provides out-of-the-box tools via the `strands-agents-tools` package (similar to Claude Code):

### File System Tools

- **`file_read`** - Advanced file reading with multiple modes:
  - `view` - Full content with syntax highlighting
  - `find` - Pattern matching with directory tree visualization
  - `lines` - Read specific line ranges
  - `search` - Pattern searching with context
  - `diff` - Compare files or directories
  - `time_machine` - View Git version history
  - `document` - Generate Bedrock document blocks

- **`file_write`** - Secure file writing with user confirmation and syntax highlighting

- **`editor`** - Iterative multi-file editing:
  - Commands: `view`, `create`, `str_replace`, `insert`, `undo_edit`
  - Automatic backups and content caching
  - Syntax highlighting and smart line finding

### Computation Tools

- **`calculator`** - SymPy-powered math engine:
  - Basic arithmetic, trigonometry, logarithms
  - Equation solving (single and systems)
  - Derivatives, integrals, limits, series expansions
  - Matrix operations, complex numbers

### Agent Control Tools

- **`think`** - Recursive thinking/reasoning cycles for deep analysis
- **`stop`** - Gracefully terminate event loop
- **`handoff_to_user`** - Pause execution for human input/approval

### Data Tools

- **`retrieve`** - Amazon Bedrock Knowledge Base semantic search
- **`current_time`** - Get current timestamp

### Usage Example

```python
from strands import Agent
from strands.models import BedrockModel
from strands_tools import calculator, file_read, current_time

model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0")

agent = Agent(
    model=model,
    tools=[calculator, file_read, current_time],
    system_prompt="You are a helpful assistant with file and math capabilities."
)

result = agent("Calculate the square root of 144 and read config.txt")
```

**Note**: File tools require user consent by default. Set `os.environ["BYPASS_TOOL_CONSENT"]="true"` for development.

## Deploying to AWS

### Configure and Deploy

```bash
# Configure the agent for deployment
agentcore configure -e my_agent.py

# Deploy to AWS (auto-creates all required resources)
agentcore launch

# Test the deployed agent
agentcore invoke '{"prompt": "What is the current stock price of TSLA?"}'
```

### Required AWS Permissions

Your AWS account needs:
- `BedrockAgentCoreFullAccess` managed policy
- `AmazonBedrockFullAccess` managed policy
- Model Access: Anthropic Claude Sonnet 4.5 enabled in Amazon Bedrock console

## Available Claude Models

You have access to 24 Claude models including:
- **Claude Sonnet 4.5** (current) - Best for agents and complex reasoning
- **Claude Opus 4.1** - Maximum intelligence
- **Claude Haiku 4.5** - Fast and cost-effective
- **Claude 3.x series** - Various versions for different use cases

## How It Works

1. **OAuth2 Authentication**: Agent requests token from your Spring Authorization Server with `mcp:read mcp:write mcp:tools` scopes

2. **MCP Connection**: Agent connects to Finance MCP server using bearer token

3. **Tool Discovery**: Agent fetches all available finance tools from MCP server

4. **Query Processing**: Claude Sonnet 4.5 analyzes your question and decides which tools to use

5. **Tool Execution**: Agent calls finance tools via MCP protocol

6. **Response Generation**: Claude synthesizes tool results into natural language response

## Useful Commands

### UV Commands

```bash
# Add a package
uv add <package-name>

# Run Python script
uv run python my_agent.py

# Sync dependencies
uv sync
```

### AWS CLI Commands

```bash
# Verify AWS credentials
aws sts get-caller-identity

# List available Claude models
aws bedrock list-foundation-models --region us-east-1 --by-provider anthropic

# Check Claude Sonnet 4.5 availability
aws bedrock get-foundation-model-availability \
  --region us-east-1 \
  --model-id anthropic.claude-sonnet-4-5-20250929-v1:0
```

## Resources

- [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [Strands Agents Documentation](https://strandsagents.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- AWS Account: `090719695391`
- Default Region: `us-east-1`

## Notes

- This project demonstrates AWS Bedrock AgentCore with production MCP integration
- Docker must be running for local agent development
- All credentials stored in `.env` are gitignored
- Agent uses inference profiles for cross-region availability
- OAuth2 tokens are cached and auto-refreshed