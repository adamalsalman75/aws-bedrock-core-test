# AWS Bedrock AgentCore Deployment Guide

## Overview

AWS Bedrock AgentCore provides a serverless runtime for deploying AI agents that use AWS Bedrock models. This guide covers deployment using the `agentcore` CLI.

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

**What this does**:
- Auto-detects `pyproject.toml` (no need for `requirements.txt`!)
- Creates `.bedrock_agentcore.yaml` with your settings
- Generates Dockerfile using UV's official Docker image
- Creates `.dockerignore` file

**Note**: AgentCore uses UV natively - it installs dependencies directly from `pyproject.toml` using `uv pip install .` in the Docker build.

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
- `SECRET_NAME`: Name of secret in Secrets Manager (tells config.py to use it)
- `AWS_DEFAULT_REGION`: Region for boto3 Secrets Manager client

**What this does**:
1. **Packages code**: Creates deployment package with `my_agent.py` + `agent/` package
2. **Builds Docker image**: ARM64 container with Python 3.13 + dependencies
3. **Creates ECR repository**: `financial-ai-agent` in your AWS account
4. **Pushes to ECR**: Uploads Docker image
5. **Creates IAM role**: Execution role with Bedrock + Secrets Manager permissions
6. **Deploys to AgentCore**: Creates runtime endpoint
7. **Returns ARN**: Agent runtime ARN for invocation

**Expected output**:
```
✓ Building container...
✓ Pushing to ECR...
✓ Creating execution role...
✓ Deploying to AgentCore...

Agent Runtime ARN: arn:aws:bedrock:us-east-1:090719695391:agent-runtime/financial-ai-agent
Status: CREATING
```

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

## AWS Resources Created

AgentCore automatically creates:

1. **ECR Repository**: `financial-ai-agent`
   - Stores Docker image
   - Tagged with deployment timestamp

2. **IAM Execution Role**: `agentcore-execution-role-financial-ai-agent`
   - **Trust policy**: Allows Bedrock to assume role
   - **Permissions**:
     - `bedrock:InvokeModel` (Claude Sonnet 4.5)
     - `secretsmanager:GetSecretValue` (read `finance-mcp-oauth2`)
     - `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

3. **CloudWatch Log Group**: `/aws/bedrock/agentcore/financial-ai-agent`
   - Contains agent execution logs
   - Includes OAuth2 auth, MCP connection, tool calls, Claude responses

4. **AgentCore Runtime**: Serverless endpoint
   - Scales automatically based on load
   - Runs on AWS Fargate (ARM64)
   - Billed per hour active

## Viewing Resources in AWS Console

After deployment, you can monitor and manage your agent through the AWS Console:

### Quick Links (us-east-1)

**Bedrock AgentCore Runtime** (main agent):
- Console: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agent-core/runtimes
- Look for: `financial_ai_agent-ZhY4bUBFJX`

**CloudWatch Logs** (agent execution logs):
- Console: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups
- Log group: `/aws/bedrock-agentcore/runtimes/financial_ai_agent-ZhY4bUBFJX-DEFAULT`
- Direct link: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Fbedrock-agentcore$252Fruntimes$252Ffinancial_ai_agent-ZhY4bUBFJX-DEFAULT

**GenAI Observability Dashboard** (recommended):
- Direct link: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#gen-ai-observability/agent-core
- Shows: Agent invocations, token usage, latency, errors
- **Note**: Data takes up to 10 minutes to appear after first invocation

**ECR Repository** (Docker images):
- Console: https://console.aws.amazon.com/ecr/repositories?region=us-east-1
- Repository: `bedrock-agentcore-financial_ai_agent`
- Direct link: https://console.aws.amazon.com/ecr/repositories/private/090719695391/bedrock-agentcore-financial_ai_agent?region=us-east-1

**Secrets Manager** (OAuth2 credentials):
- Console: https://console.aws.amazon.com/secretsmanager/listsecrets?region=us-east-1
- Secret: `finance-mcp-oauth2`

**IAM Roles** (permissions):
- Console: https://console.aws.amazon.com/iam/home#/roles
- Roles:
  - `AmazonBedrockAgentCoreSDKRuntime-us-east-1-a7e5687419` (agent execution)
  - `AmazonBedrockAgentCoreSDKCodeBuild-us-east-1-a7e5687419` (build)

**CodeBuild** (build history):
- Console: https://console.aws.amazon.com/codesuite/codebuild/projects?region=us-east-1
- Project: `bedrock-agentcore-financial_ai_agent-builder`

**S3 Bucket** (CodeBuild sources):
- Console: https://s3.console.aws.amazon.com/s3/buckets?region=us-east-1
- Bucket: `bedrock-agentcore-codebuild-sources-090719695391-us-east-1`

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