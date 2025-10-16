# Deployment Plan for AWS Bedrock AgentCore

## Overview
Deploy the Financial AI Agent to AWS Bedrock AgentCore Runtime with secure credential management.

## Tasks for Tomorrow

### 1. Update Code for AWS Deployment
- **Modify `agent/config.py`**:
  - Add support for AWS Secrets Manager for OAuth2 secrets
  - Keep environment variable fallback for local testing (already done!)
  - AWS credentials are already excluded (code uses env vars only)
- **Verify `agent/` package**:
  - Ensure all modules work in containerized environment
  - Confirm MCP connection handling is correct

### 2. Store Secrets in AWS Secrets Manager
- **Create secret** for OAuth2 MCP credentials:
  ```bash
  aws secretsmanager create-secret \
    --name finance-mcp-oauth2 \
    --secret-string '{"MCP_CLIENT_ID":"your-client-id","MCP_CLIENT_SECRET":"your-client-secret"}'
  ```
- **Grant permissions** to AgentCore execution role (auto-handled by toolkit)

### 3. Configure AgentCore Deployment
- **Use starter toolkit** to configure:
  ```python
  from bedrock_agentcore_starter_toolkit import Runtime

  runtime = Runtime()
  runtime.configure(
      entrypoint="my_agent.py",
      auto_create_execution_role=True,  # Creates IAM role automatically
      auto_create_ecr=True,             # Creates ECR repo
      requirements_file="requirements.txt",  # Generate with: uv pip freeze > requirements.txt
      region="us-east-1",
      agent_name="financial-ai-agent"
  )
  ```
- **Pass environment variables**:
  - `AUTH_SERVER_TOKEN_URL=https://auth.macrospire.com/oauth2/token`
  - `FINANCE_MCP_URL=https://finance.macrospire.com/mcp`
  - `SECRET_NAME=finance-mcp-oauth2` (for Secrets Manager)

### 4. Deploy to AgentCore Runtime
- **Launch deployment**:
  ```python
  launch_result = runtime.launch()
  ```
  - Builds Docker container with your agent
  - Pushes to ECR
  - Creates AgentCore Runtime endpoint
  - Sets up IAM execution role with Bedrock permissions

### 5. Test Deployed Agent
- **Check status**: Wait for `READY` state
- **Test invocation**:
  ```python
  runtime.invoke({"prompt": "What is the current stock price of TSLA?"})
  ```
- **Or use boto3**:
  ```python
  client = boto3.client('bedrock-agentcore', region_name='us-east-1')
  response = client.invoke_agent_runtime(
      agentRuntimeArn=launch_result.agent_arn,
      qualifier="DEFAULT",
      payload=json.dumps({"prompt": "What is TSLA stock price?"})
  )
  ```

### 6. Verify MCP Connection
- **Check CloudWatch logs** for OAuth2 authentication success
- **Test finance tools** work correctly in deployed environment
- **Verify** Claude Sonnet 4.5 is being used via Bedrock

## What Gets Uploaded

✅ **Required**:
- OAuth2 credentials → AWS Secrets Manager
- Environment variables (URLs)
- Agent code (`my_agent.py` + `agent/` package)
- Dependencies (`pyproject.toml` or generate `requirements.txt` via `uv pip freeze`)

❌ **NOT Required**:
- AWS credentials (runtime uses IAM execution role)
- `.env` file (secrets moved to Secrets Manager)

## Security Model

**Local Development**:
- `.env` file with all credentials
- Direct AWS credential usage

**AWS Deployment**:
- IAM execution role (auto-created) → Bedrock permissions
- Secrets Manager → OAuth2 credentials
- Environment variables → Non-sensitive config

## Expected Outcome

After deployment:
1. Agent runs serverlessly on AgentCore Runtime
2. Automatically authenticates to Finance MCP via OAuth2
3. Uses Claude Sonnet 4.5 via Bedrock (no API key needed)
4. Scales automatically based on load
5. Accessible via boto3 or AgentCore API

## Important Notes

### AWS Credentials
- ✅ Your agent will use an **IAM execution role** (auto-created)
- ✅ This role has permissions to call Bedrock models
- ❌ Do NOT include `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in deployment

### OAuth2 Secrets
You only need to upload these to Secrets Manager:
```bash
# From your .env file:
MCP_CLIENT_ID=<your-client-id>
MCP_CLIENT_SECRET=<your-client-secret>
```

These URLs go in environment variables (not sensitive):
```bash
AUTH_SERVER_TOKEN_URL=https://auth.macrospire.com/oauth2/token
FINANCE_MCP_URL=https://finance.macrospire.com/mcp
```

### Deployment Flow
```
Local Machine → Docker Build → ECR Push → AgentCore Runtime
     ↓              ↓              ↓              ↓
  my_agent.py → Container → Image → IAM Role + Endpoint
```

### Cost Considerations
- **Bedrock inference**: Pay per token (Claude Sonnet 4.5 pricing)
- **AgentCore Runtime**: Pay per hour runtime is active
- **ECR storage**: Minimal cost for Docker image storage
- **Secrets Manager**: ~$0.40/month per secret

### Next Steps After Deployment
1. Get the AgentCore Runtime ARN from `launch_result.agent_arn`
2. Test with curl or boto3
3. Integrate into applications using AWS SDK
4. Monitor CloudWatch logs for debugging
5. Set up CloudWatch alarms for failures

### Cleanup (when needed)
```python
# Delete the runtime
agentcore_control_client.delete_agent_runtime(
    agentRuntimeId=launch_result.agent_id
)

# Delete ECR repository
ecr_client.delete_repository(
    repositoryName=launch_result.ecr_uri.split('/')[1],
    force=True
)

# Delete Secrets Manager secret
secretsmanager_client.delete_secret(
    SecretId='finance-mcp-oauth2',
    ForceDeleteWithoutRecovery=True
)
```
