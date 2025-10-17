# AWS Bedrock AgentCore Deployment Guide

## What is Bedrock AgentCore?

**AWS Bedrock AgentCore** is a serverless platform for deploying and running AI agents in production on AWS infrastructure. It eliminates the operational overhead of managing containers, scaling, and infrastructure while providing native integration with AWS Bedrock models.

**What AgentCore Provides**:
- **Serverless Runtime**: Fully managed container orchestration (no ECS/EKS/Lambda required)
- **Auto-Scaling**: Scales from zero to handle variable workloads
- **Native Bedrock Integration**: Direct access to Claude, Titan, and other foundation models
- **Built-in Observability**: CloudWatch logs, metrics, and GenAI-specific dashboards
- **IAM Security**: Automatic execution roles with least-privilege permissions
- **Container Deployment**: Packages your Python agent as a Docker image (ARM64)

**What You Build**:
- Python agent code using frameworks like Strands Agents
- `pyproject.toml` with dependencies (UV native support)
- MCP integrations or custom tools
- Configuration via environment variables and AWS Secrets Manager

## How AgentCore Works

AgentCore handles the entire deployment pipeline from source code to production runtime:

```
Your Code (my_agent.py + agent/)
         ↓
    agentcore configure    → Creates .bedrock_agentcore.yaml + Dockerfile
         ↓
    agentcore launch       → Triggers AWS deployment pipeline:
         ↓
    ┌─────────────────────────────────────────────────┐
    │  1. Source Upload:                              │
    │     • Zip source code                           │
    │     • Upload to S3 bucket                       │
    │     • Bucket: bedrock-agentcore-codebuild-...   │
    └─────────────────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────────────────┐
    │  2. CodeBuild (Docker Build):                   │
    │     • Pulls UV base image (ARM64)               │
    │     • Copies source code                        │
    │     • Runs: uv pip install . (from pyproject)   │
    │     • Builds Docker image                       │
    │     • Project: bedrock-agentcore-*-builder      │
    └─────────────────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────────────────┐
    │  3. ECR Push:                                   │
    │     • Creates ECR repository (if needed)        │
    │     • Pushes Docker image                       │
    │     • Tags with timestamp                       │
    │     • Repo: bedrock-agentcore-financial_ai...   │
    └─────────────────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────────────────┐
    │  4. IAM Role Creation:                          │
    │     • Creates execution role (if needed)        │
    │     • Attaches Bedrock permissions              │
    │     • Attaches Secrets Manager permissions      │
    │     • Role: AmazonBedrockAgentCoreSDKRuntime-*  │
    └─────────────────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────────────────┐
    │  5. AgentCore Runtime:                          │
    │     • Deploys container to serverless runtime   │
    │     • Configures environment variables          │
    │     • Exposes /invocations endpoint             │
    │     • Creates CloudWatch log group              │
    │     • Status: CREATING → READY                  │
    └─────────────────────────────────────────────────┘
                    ↓
         Production Agent (invokable via agentcore invoke)
```

**Key Infrastructure**:
- **Compute**: AWS Fargate (ARM64 containers, managed by AgentCore)
- **Storage**: ECR for Docker images, S3 for build sources
- **Build**: CodeBuild for Docker image compilation
- **Security**: IAM roles, Secrets Manager for credentials
- **Observability**: CloudWatch Logs + GenAI dashboards

## How This Example Uses AgentCore

Our financial AI agent (`my_agent.py`) demonstrates a production-ready AgentCore deployment:

**Local Development**:
```bash
# Run locally (port 8080)
uv run python my_agent.py
```

**Production Deployment**:
```bash
# Configure → Deploy → Invoke
agentcore configure --entrypoint my_agent.py --name financial_ai_agent
agentcore launch --env AUTH_SERVER_TOKEN_URL=... --env FINANCE_MCP_URL=...
agentcore invoke '{"prompt": "What is TSLA stock price?"}'
```

**What Gets Deployed**:
1. **Agent Code**: `my_agent.py` + `agent/` package (auth, config, MCP client)
2. **Dependencies**: From `pyproject.toml` (strands-agents, mcp, httpx, etc.)
3. **Secrets**: OAuth2 credentials in AWS Secrets Manager (`finance-mcp-oauth2`)
4. **Environment**: MCP URLs, token endpoints (non-sensitive config)
5. **Runtime**: Claude Sonnet 4.5 model (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)

**Runtime Flow**:
```
User → agentcore invoke → AgentCore Runtime → Docker Container
                                                      ↓
                                            my_agent.py starts
                                                      ↓
                                    Load config (Secrets Manager)
                                                      ↓
                                    OAuth2 token from auth server
                                                      ↓
                                    Connect to Finance MCP server
                                                      ↓
                                    List tools (stocks, yields, etc.)
                                                      ↓
                                    Create Strands Agent + tools
                                                      ↓
                                    Process user prompt
                                                      ↓
                                    Call Claude Sonnet 4.5 (Bedrock)
                                                      ↓
                                    Execute MCP tools (stock prices)
                                                      ↓
                                    Return response → User
```

**Why This Architecture**:
- **Serverless**: No server management, scales automatically
- **Secure**: OAuth2 credentials never in code, IAM for AWS access
- **Observable**: CloudWatch logs show OAuth flow, MCP connections, tool calls
- **Reproducible**: `pyproject.toml` ensures consistent dependencies
- **Cross-Region**: Claude model uses US cross-region inference for availability

## Prerequisites

1. **AWS Credentials**: Valid AWS credentials configured (see `aws-cli-authentication.md`)
2. **IAM Permissions**:
   - `BedrockAgentCoreFullAccess` managed policy
   - `AmazonBedrockFullAccess` managed policy
3. **Bedrock Model Access**: Enable Anthropic Claude models in AWS Bedrock console
4. **UV Package Manager**: Installed and configured
5. **Project Dependencies**: `uv sync` completed

## Deployment Modes

AgentCore supports three deployment modes:

### 1. CodeBuild (Default - Recommended)

✅ **Pros**: No local Docker needed, builds ARM64 in cloud, faster
❌ **Cons**: Requires CodeBuild permissions

```bash
uv run agentcore launch
```

### 2. Local Build + Cloud Runtime

✅ **Pros**: Build control, works without CodeBuild
❌ **Cons**: Requires Docker/Finch/Podman locally

```bash
uv run agentcore launch --local-build
```

### 3. Local Everything

✅ **Pros**: Full local testing
❌ **Cons**: Requires Docker, not production

```bash
uv run agentcore launch --local
```

## Step-by-Step Deployment


### Step 1: Configure AgentCore

```bash
uv run agentcore configure \
  --entrypoint my_agent.py \
  --name financial_ai_agent \
  --region us-east-1
```

**Parameters**:
- `--entrypoint`: Python file with `BedrockAgentCoreApp` (our `my_agent.py`)
- `--name`: Agent name (used for CloudWatch logs, ECR repo, etc.) - use underscores, not hyphens
- `--region`: AWS region for deployment

**What this command does**:

1. **Detects project structure**: Scans for `pyproject.toml` (no `requirements.txt` needed)
2. **Creates `.bedrock_agentcore.yaml`**: Configuration file with agent settings
3. **Generates `.bedrock_agentcore/financial_ai_agent/Dockerfile`**: Uses `ghcr.io/astral-sh/uv:python3.13-bookworm-slim`
4. **Creates `.dockerignore`**: Excludes unnecessary files from Docker build

**Files created**:

`.bedrock_agentcore.yaml`:
```yaml
default_agent: financial_ai_agent
agents:
  financial_ai_agent:
    name: financial_ai_agent
    entrypoint: /path/to/my_agent.py
    platform: linux/arm64
    container_runtime: docker
    aws:
      execution_role_auto_create: true
      region: us-east-1
      ecr_auto_create: true
```

`.bedrock_agentcore/financial_ai_agent/Dockerfile`:
```dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app
ENV UV_SYSTEM_PYTHON=1 UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1
COPY . .
RUN cd . && uv pip install .  # Reads pyproject.toml
CMD ["opentelemetry-instrument", "python", "-m", "my_agent"]
```

**Key Point**: AgentCore uses UV natively - dependencies are installed from `pyproject.toml` during Docker build.

### Step 2: Deploy to AWS

```bash
uv run agentcore launch \
  --env AUTH_SERVER_TOKEN_URL=https://auth.macrospire.com/oauth2/token \
  --env FINANCE_MCP_URL=https://finance.macrospire.com/mcp \
  --env SECRET_NAME=finance-mcp-oauth2 \
  --env AWS_DEFAULT_REGION=us-east-1
```

**Environment Variables**:
- `AUTH_SERVER_TOKEN_URL`: OAuth2 token endpoint (public, not secret)
- `FINANCE_MCP_URL`: MCP server URL (public, not secret)
- `SECRET_NAME`: Name of secret in Secrets Manager (tells `agent/config.py` to load credentials)
- `AWS_DEFAULT_REGION`: Region for boto3 Secrets Manager client

**What this command does** (see "How AgentCore Works" diagram for full pipeline):

**Phase 1: Source Upload to S3**
1. Zips your project directory (`my_agent.py`, `agent/`, `pyproject.toml`, etc.)
2. Creates S3 bucket: `bedrock-agentcore-codebuild-sources-090719695391-us-east-1` (if needed)
3. Uploads source zip to S3 for CodeBuild access

**Phase 2: Docker Image Build (CodeBuild)**
4. Creates CodeBuild project: `bedrock-agentcore-financial_ai_agent-builder` (if needed)
5. Creates IAM build role: `AmazonBedrockAgentCoreSDKCodeBuild-us-east-1-*` (if needed)
6. Triggers CodeBuild job:
   - Pulls `ghcr.io/astral-sh/uv:python3.13-bookworm-slim` base image
   - Downloads source zip from S3
   - Runs `uv pip install .` (reads `pyproject.toml` for dependencies)
   - Builds ARM64 Docker image
   - Tags image with timestamp

**Phase 3: Push to ECR**
7. Creates ECR repository: `bedrock-agentcore-financial_ai_agent` (if needed)
8. Pushes built Docker image to ECR
9. Image URI: `090719695391.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-financial_ai_agent:latest`

**Phase 4: IAM Role Setup**
10. Creates IAM execution role: `AmazonBedrockAgentCoreSDKRuntime-us-east-1-a7e5687419` (if needed)
11. Attaches policies:
    - `bedrock:InvokeModel` for Claude Sonnet 4.5
    - `secretsmanager:GetSecretValue` for AgentCore identity secrets
    - `logs:*` for CloudWatch logging
12. **Note**: Custom policy needed for `finance-mcp-oauth2` secret (see Step 3)

**Phase 5: AgentCore Runtime Deployment**
13. Creates AgentCore runtime: `financial_ai_agent-ZhY4bUBFJX`
14. Configures:
    - Container image from ECR
    - Environment variables (AUTH_SERVER_TOKEN_URL, FINANCE_MCP_URL, SECRET_NAME, etc.)
    - IAM execution role
    - CloudWatch log group: `/aws/bedrock-agentcore/runtimes/financial_ai_agent-ZhY4bUBFJX-DEFAULT`
15. Deploys to AWS Fargate (ARM64, serverless)
16. Exposes `/invocations` endpoint
17. Status transitions: `CREATING` → `READY` (2-5 minutes)

**Expected output**:
```
✓ Uploading source to S3...
✓ Starting CodeBuild job...
✓ Building Docker image (ARM64)...
✓ Pushing to ECR...
✓ Creating execution role...
✓ Deploying to AgentCore runtime...

Agent Runtime ARN: arn:aws:bedrock:us-east-1:090719695391:agent-runtime/financial-ai-agent
Status: CREATING
```

**Build Time**: ~3-5 minutes (CodeBuild + ECR push + runtime provisioning)

### Step 3: Add Secrets Manager Permissions

**IMPORTANT**: AgentCore's auto-created IAM role only has permissions for secrets matching the pattern `bedrock-agentcore-identity!default/oauth2/*`. Since our secret `finance-mcp-oauth2` doesn't match this pattern, we must manually add permissions.

```bash
aws iam put-role-policy \
  --role-name AmazonBedrockAgentCoreSDKRuntime-us-east-1-a7e5687419 \
  --policy-name FinanceMCPSecretsAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "secretsmanager:GetSecretValue",
        "Resource": "arn:aws:secretsmanager:us-east-1:090719695391:secret:finance-mcp-oauth2-*"
      }
    ]
  }' \
  --region us-east-1
```

**Why this is needed**:
- The execution role created by AgentCore has limited Secrets Manager permissions
- By default, it can only read secrets for AgentCore's built-in identity management
- Custom application secrets (like our OAuth2 credentials) require explicit permissions
- The wildcard `*` at the end handles AWS's automatic suffix on secret ARNs

**Note**: If you skip this step, the agent will fail at startup with:
```
ValueError: MCP_CLIENT_ID is required (from SECRET_NAME or environment)
```

### Step 4: Wait for READY Status

```bash
# Check status
uv run agentcore status
```

Expected output:
```
Agent: financial-ai-agent
Status: READY
Runtime ARN: arn:aws:bedrock:us-east-1:090719695391:agent-runtime/financial-ai-agent
ECR Repository: 090719695391.dkr.ecr.us-east-1.amazonaws.com/financial-ai-agent
Execution Role: arn:aws:iam::090719695391:role/agentcore-execution-role-financial-ai-agent
```

Status transitions: `CREATING` → `READY` (takes 2-5 minutes)

### Step 5: Test the Agent

```bash
# Simple test
uv run agentcore invoke '{"prompt": "What is the current stock price of TSLA?"}'

# Test with different queries
uv run agentcore invoke '{"prompt": "Show me treasury yields"}'
uv run agentcore invoke '{"prompt": "What are recent analyst upgrades?"}'
```

## Configuration Files

### .bedrock_agentcore.yaml

Created by `agentcore configure`:

```yaml
default_agent: financial_ai_agent
agents:
  financial_ai_agent:
    name: financial_ai_agent
    entrypoint: /path/to/my_agent.py
    platform: linux/arm64
    container_runtime: docker
    aws:
      execution_role_auto_create: true
      region: us-east-1
      ecr_auto_create: true
```

### .bedrock_agentcore/financial_ai_agent/Dockerfile

Auto-generated Dockerfile using UV:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app

ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY . .
# Installs from pyproject.toml automatically
RUN cd . && uv pip install .

CMD ["opentelemetry-instrument", "python", "-m", "my_agent"]
```

**Note**: AgentCore uses UV's official Docker image and installs directly from `pyproject.toml` - no `requirements.txt` needed!

## AWS Resources Created by AgentCore

When you run `agentcore launch`, the following AWS resources are automatically created and configured:

### Build Infrastructure (CodeBuild Mode)

**1. S3 Bucket** (source code storage):
- Bucket: `bedrock-agentcore-codebuild-sources-090719695391-us-east-1`
- Purpose: Stores zipped source code for CodeBuild
- Console: https://s3.console.aws.amazon.com/s3/buckets?region=us-east-1

**2. CodeBuild Project** (Docker image builder):
- Project: `bedrock-agentcore-financial_ai_agent-builder`
- Purpose: Builds ARM64 Docker image from source code
- Reads: `pyproject.toml` for dependencies
- Runs: `uv pip install .` in container
- Console: https://console.aws.amazon.com/codesuite/codebuild/projects?region=us-east-1

**3. IAM Build Role** (CodeBuild permissions):
- Role: `AmazonBedrockAgentCoreSDKCodeBuild-us-east-1-a7e5687419`
- Permissions: ECR push, S3 read, CloudWatch logs
- Console: https://console.aws.amazon.com/iam/home#/roles

### Runtime Infrastructure

**4. ECR Repository** (Docker image storage):
- Repository: `bedrock-agentcore-financial_ai_agent`
- Purpose: Stores built Docker images (tagged with timestamps)
- Platform: ARM64 containers
- Console: https://console.aws.amazon.com/ecr/repositories?region=us-east-1
- Direct link: https://console.aws.amazon.com/ecr/repositories/private/090719695391/bedrock-agentcore-financial_ai_agent?region=us-east-1

**5. IAM Execution Role** (agent runtime permissions):
- Role: `AmazonBedrockAgentCoreSDKRuntime-us-east-1-a7e5687419`
- Trust policy: Allows Bedrock to assume role
- Permissions:
  - `bedrock:InvokeModel` (Claude Sonnet 4.5)
  - `secretsmanager:GetSecretValue` (limited - requires custom policy for `finance-mcp-oauth2`)
  - `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`
- Console: https://console.aws.amazon.com/iam/home#/roles

**6. Bedrock AgentCore Runtime** (serverless agent endpoint):
- Runtime: `financial_ai_agent-ZhY4bUBFJX`
- Compute: AWS Fargate (ARM64 containers)
- Scaling: Automatic (scales to zero when idle)
- Status: `CREATING` → `READY` (2-5 minutes)
- Endpoint: `/invocations` (invoked via `agentcore invoke`)
- Console: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agent-core/runtimes

**7. CloudWatch Log Group** (agent execution logs):
- Log group: `/aws/bedrock-agentcore/runtimes/financial_ai_agent-ZhY4bUBFJX-DEFAULT`
- Contents: OAuth2 auth, MCP connections, tool calls, Claude responses, errors
- Retention: Default (never expire) - consider setting to 7-30 days
- Console: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups
- Direct link: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Fbedrock-agentcore$252Fruntimes$252Ffinancial_ai_agent-ZhY4bUBFJX-DEFAULT

### Pre-Existing Resources (Created Manually)

**8. Secrets Manager Secret** (OAuth2 credentials):
- Secret: `finance-mcp-oauth2`
- Contains: `MCP_CLIENT_ID`, `MCP_CLIENT_SECRET`
- Created: Manually (see `secrets-management.md`)
- Console: https://console.aws.amazon.com/secretsmanager/listsecrets?region=us-east-1

### Observability Dashboards

**GenAI Observability Dashboard** (recommended):
- Purpose: Agent-specific metrics (invocations, token usage, latency, errors)
- Data delay: Up to 10 minutes after first invocation
- Direct link: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#gen-ai-observability/agent-core

## Updating a Deployed Agent

### Update Code Only

```bash
# Make code changes
vim my_agent.py

# Redeploy (uses existing config)
uv run agentcore launch --auto-update-on-conflict
```

### Update Dependencies

```bash
# Add new dependency
uv add some-package

# Redeploy (AgentCore reads pyproject.toml automatically)
uv run agentcore launch --auto-update-on-conflict
```

### Update Environment Variables

```bash
uv run agentcore launch \
  --auto-update-on-conflict \
  --env AUTH_SERVER_TOKEN_URL=https://new-url.com/oauth2/token \
  --env FINANCE_MCP_URL=https://finance.macrospire.com/mcp \
  --env SECRET_NAME=finance-mcp-oauth2
```

## Monitoring and Debugging

### View CloudWatch Logs

```bash
# Via AWS Console
# Navigate to: CloudWatch → Log groups → /aws/bedrock/agentcore/financial-ai-agent

# Via AWS CLI
aws logs tail /aws/bedrock/agentcore/financial-ai-agent --follow --region us-east-1
```

**What to look for**:
- OAuth2 token request: `POST https://auth.macrospire.com/oauth2/token`
- MCP connection: `Connecting to Finance MCP server`
- Tool discovery: `Found N tools from MCP server`
- Agent queries: Claude reasoning and tool calls
- Errors: Authentication failures, MCP connection issues

### Common Log Patterns

**Successful OAuth2 authentication**:
```
INFO - OAuth2TokenProvider: Requesting token from https://auth.macrospire.com/oauth2/token
INFO - OAuth2TokenProvider: Token obtained, expires in 3600s
```

**MCP tool discovery**:
```
INFO - MCPClient: Connected to Finance MCP server
INFO - MCPClient: Discovered tools: get_stock_price, get_treasury_yields, ...
```

**Agent reasoning**:
```
INFO - Agent: Processing query: "What is the current stock price of TSLA?"
INFO - Agent: Using tool: get_stock_price (symbol=TSLA)
INFO - Agent: Generating response with Claude Sonnet 4.5
```

### Debugging Checklist

**Issue**: Agent returns empty response

1. Check CloudWatch logs for errors
2. Verify `SECRET_NAME` environment variable is set
3. Confirm IAM role has Secrets Manager permissions
4. Test secret access: `aws secretsmanager get-secret-value --secret-id finance-mcp-oauth2`

**Issue**: OAuth2 authentication fails

1. Verify secret contains correct `MCP_CLIENT_ID` and `MCP_CLIENT_SECRET`
2. Check `AUTH_SERVER_TOKEN_URL` is correct
3. Confirm OAuth2 server is accessible from AWS (not behind firewall)
4. Test locally: `uv run python -c "from agent import load_config; print(load_config())"`

**Issue**: MCP tools not loading

1. Verify `FINANCE_MCP_URL` environment variable
2. Check Finance MCP server is accessible from AWS
3. Confirm OAuth2 token includes `mcp:read mcp:write mcp:tools` scopes
4. Review `my_agent.py:39-64` for MCP connection logic

## Cost Management

### Estimate Monthly Costs

**Assumptions**:
- 1000 queries/month
- Average 500 input tokens, 1000 output tokens per query

**Breakdown**:
- **Bedrock Claude Sonnet 4.5**:
  - Input: 1000 * 500 * $3 / 1M = $1.50
  - Output: 1000 * 1000 * $15 / 1M = $15.00
- **AgentCore Runtime**: ~$0.05/hour * 730 hours = $36.50 (if always on)
- **Secrets Manager**: $0.40/month
- **ECR Storage**: $0.10/month (per GB)
- **CloudWatch Logs**: $0.50/GB ingested

**Total**: ~$53/month (or less if runtime auto-scales down)

### Reduce Costs

1. **Use auto-scaling**: AgentCore scales to zero during inactivity
2. **Clean up old ECR images**: Delete unused Docker images
3. **Adjust log retention**: Set CloudWatch log retention to 7 days
4. **Use reserved capacity**: For high-volume production workloads

## Cleanup

### Remove All Resources

```bash
# Destroy AgentCore resources
uv run agentcore destroy --agent financial-ai-agent
```

This removes:
- AgentCore runtime
- IAM execution role
- CloudWatch log group

**Manually delete** (if needed):
```bash
# Delete ECR repository
aws ecr delete-repository \
  --repository-name financial-ai-agent \
  --force \
  --region us-east-1

# Delete secret (see secrets-management.md)
aws secretsmanager delete-secret \
  --secret-id finance-mcp-oauth2 \
  --force-delete-without-recovery \
  --region us-east-1
```

## Invoking from Code

Instead of using `agentcore invoke`, integrate directly:

```python
import boto3
import json

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = client.invoke_agent(
    agentId='financial-ai-agent',  # or use full ARN
    agentAliasId='TSTALIASID',     # or 'DRAFT'
    sessionId='test-session-123',
    inputText='What is the current stock price of TSLA?'
)

# Stream response
for event in response['completion']:
    if 'chunk' in event:
        chunk = event['chunk']
        print(chunk.get('bytes', b'').decode('utf-8'))
```

## Next Steps

1. **Set up CI/CD**: Automate deployment on git push
2. **Add monitoring**: CloudWatch alarms for errors
3. **Load testing**: Validate performance under load
4. **API Gateway**: Add REST API in front of agent
5. **Versioning**: Use agent aliases for blue-green deployments

## References

- [AgentCore Documentation](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [IAM Roles for AgentCore](https://docs.aws.amazon.com/bedrock/latest/userguide/agent-permissions.html)