# Deployment Plan for AWS Bedrock AgentCore

## Overview
Deploy the Financial AI Agent to AWS Bedrock AgentCore Runtime with secure credential management using AWS Secrets Manager.

## Prerequisites

✅ **Already Completed**:
- OAuth2 credentials stored in AWS Secrets Manager
  - Secret name: `finance-mcp-oauth2`
  - Secret ARN: `arn:aws:secretsmanager:us-east-1:090719695391:secret:finance-mcp-oauth2-pzQgfe`
  - Contains: `MCP_CLIENT_ID` and `MCP_CLIENT_SECRET`
- `agent/config.py` updated to support both local (.env) and AWS (Secrets Manager)
- `boto3` added to dependencies

## Deployment Steps

### 1. Configure AgentCore

```bash
uv run agentcore configure \
  --entrypoint my_agent.py \
  --name financial_ai_agent \
  --region us-east-1
```

**Note**: AgentCore auto-detects `pyproject.toml` and uses UV natively - no `requirements.txt` needed!

### 2. Deploy to AWS

Deploy using CodeBuild (default - no local Docker needed):

```bash
uv run agentcore launch \
  --env AUTH_SERVER_TOKEN_URL=https://auth.macrospire.com/oauth2/token \
  --env FINANCE_MCP_URL=https://finance.macrospire.com/mcp \
  --env SECRET_NAME=finance-mcp-oauth2 \
  --env AWS_DEFAULT_REGION=us-east-1
```

This will:
- Build ARM64 container in AWS CodeBuild (no local Docker required)
- Push to ECR
- Create IAM execution role with Bedrock + Secrets Manager permissions
- Deploy to AgentCore Runtime
- Return agent ARN

**Alternative**: Use `--local-build` if you prefer building locally with Docker.

### 3. Test Deployed Agent

```bash
# Check status
uv run agentcore status

# Test invocation
uv run agentcore invoke '{"prompt": "What is the current stock price of TSLA?"}'
```

## Configuration Summary

### Local Development (.env file)
```bash
# OAuth2 credentials (local only)
MCP_CLIENT_ID=content-engine-client
MCP_CLIENT_SECRET=content-engine-secret-2024

# URLs (same for local and AWS)
AUTH_SERVER_TOKEN_URL=https://auth.macrospire.com/oauth2/token
FINANCE_MCP_URL=https://finance.macrospire.com/mcp

# AWS credentials (local only - not needed in AWS)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
```

### AWS Deployment Environment Variables
Pass these via `agentcore launch --env`:
- `AUTH_SERVER_TOKEN_URL=https://auth.macrospire.com/oauth2/token`
- `FINANCE_MCP_URL=https://finance.macrospire.com/mcp`
- `SECRET_NAME=finance-mcp-oauth2` (tells config.py to use Secrets Manager)
- `AWS_DEFAULT_REGION=us-east-1`

**OAuth2 credentials** come from Secrets Manager (no need to pass as env vars).

## How It Works

### Local Development
```
.env file → load_dotenv() → Environment variables → config.py
```

### AWS Deployment
```
Secrets Manager → boto3 → config.py (when SECRET_NAME is set)
Environment vars → config.py (for URLs)
```

The `agent/config.py:43-97` logic:
1. Check if `SECRET_NAME` environment variable exists
2. If yes: Load OAuth2 creds from Secrets Manager
3. If no: Load OAuth2 creds from environment variables (.env)
4. URLs always come from environment variables

## Project Uses UV (Not pip)

Dependencies managed via `pyproject.toml`:
- Add dependency: `uv add <package>`
- Sync: `uv sync`
- **No need for requirements.txt**: AgentCore uses UV natively and reads `pyproject.toml` directly

## IAM Permissions

AgentCore automatically creates an execution role with:
- **Bedrock permissions**: Call Claude Sonnet 4.5
- **Secrets Manager permissions**: Read `finance-mcp-oauth2` secret
- **CloudWatch Logs**: Write logs

## Monitoring

After deployment:
- **CloudWatch Logs**: `/aws/bedrock/agentcore/financial-ai-agent`
- Check for OAuth2 authentication success
- Verify MCP tool discovery
- Monitor Claude Sonnet 4.5 usage

## Cost Estimate

- **Bedrock Claude Sonnet 4.5**: ~$3 per 1M input tokens, ~$15 per 1M output tokens
- **AgentCore Runtime**: Pay per hour runtime is active
- **Secrets Manager**: ~$0.40/month per secret
- **ECR Storage**: Minimal (< $0.10/month)
- **CodeBuild**: ~$0.005 per build minute (only during deployment)

## Cleanup (When Needed)

```bash
# Destroy AgentCore resources
uv run agentcore destroy --agent financial-ai-agent

# Delete secret
aws secretsmanager delete-secret \
  --secret-id finance-mcp-oauth2 \
  --force-delete-without-recovery \
  --region us-east-1
```

## Troubleshooting

**Issue**: OAuth2 authentication fails in AWS
- Check CloudWatch logs for error details
- Verify `SECRET_NAME=finance-mcp-oauth2` is set in environment variables
- Confirm IAM execution role has `secretsmanager:GetSecretValue` permission

**Issue**: MCP tools not loading
- Verify `FINANCE_MCP_URL` and `AUTH_SERVER_TOKEN_URL` environment variables
- Check Finance MCP server is accessible from AWS
- Review `my_agent.py:39-64` for MCP connection logic

**Issue**: Build fails
- Ensure `requirements.txt` is up to date: `uv export --format requirements.txt --no-dev > requirements.txt`
- Check `pyproject.toml` dependencies are compatible with ARM64

## Next Steps

1. Run `agentcore configure` (auto-detects pyproject.toml)
2. Run `agentcore launch` with environment variables
3. Test with sample queries
4. Monitor CloudWatch logs
5. Integrate into applications via boto3 SDK