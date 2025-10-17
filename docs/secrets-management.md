# Secrets Management: Local vs AWS

## Overview

This project uses **dual-mode secrets management**:
- **Local development**: `.env` file
- **AWS deployment**: AWS Secrets Manager

The `agent/config.py` module automatically detects which environment it's running in and loads secrets accordingly.

## Local Development: .env File

### Setup

Create `.env` file in project root:

```bash
# OAuth2 credentials for MCP servers
AUTH_SERVER_TOKEN_URL=https://auth.macrospire.com/oauth2/token
MCP_CLIENT_ID=content-engine-client
MCP_CLIENT_SECRET=content-engine-secret-2024

# Finance MCP Server
FINANCE_MCP_URL=https://finance.macrospire.com/mcp

# AWS credentials (for local development only)
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
AWS_DEFAULT_REGION=us-east-1
```

### How It Works

1. **python-dotenv** loads `.env` file
2. Variables become environment variables
3. `agent/config.py` reads from `os.getenv()`

### Security

✅ **Do**:
- Add `.env` to `.gitignore` (already done)
- Never commit `.env` to version control
- Keep `.env` file permissions restricted: `chmod 600 .env`

❌ **Don't**:
- Share `.env` file via email/Slack
- Store `.env` in cloud storage (Dropbox, Google Drive)
- Include `.env` in Docker images

### Testing Local Config

```bash
# Test config loads correctly
uv run python -c "from agent import load_config; config = load_config(); print(f'✓ Client ID: {config.mcp_client_id}')"

# Run agent locally
uv run python my_agent.py
```

## AWS Deployment: Secrets Manager

### Why Secrets Manager?

- **Automatic rotation**: Schedule credential rotation
- **Audit trail**: CloudTrail logs all access
- **IAM permissions**: Fine-grained access control
- **Encryption**: Encrypted at rest with KMS
- **No filesystem**: Secrets not stored in Docker image

### Creating a Secret

```bash
# Set AWS credentials first
export AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
export AWS_DEFAULT_REGION=us-east-1

# Create secret
aws secretsmanager create-secret \
  --name finance-mcp-oauth2 \
  --description "OAuth2 credentials for Finance MCP Server" \
  --secret-string '{"MCP_CLIENT_ID":"content-engine-client","MCP_CLIENT_SECRET":"content-engine-secret-2024"}' \
  --region us-east-1
```

**Output**:
```json
{
    "ARN": "arn:aws:secretsmanager:us-east-1:090719695391:secret:finance-mcp-oauth2-pzQgfe",
    "Name": "finance-mcp-oauth2",
    "VersionId": "5cfb8790-dc7d-4b9d-ba02-905bb68f87e0"
}
```

### Secret Structure

Secrets Manager stores JSON:

```json
{
  "MCP_CLIENT_ID": "content-engine-client",
  "MCP_CLIENT_SECRET": "content-engine-secret-2024"
}
```

**Important**: Use exact key names (`MCP_CLIENT_ID`, not `mcp_client_id`) to match `agent/config.py`.

### Retrieving a Secret

```bash
# Get secret value
aws secretsmanager get-secret-value \
  --secret-id finance-mcp-oauth2 \
  --region us-east-1

# Extract just the secret string
aws secretsmanager get-secret-value \
  --secret-id finance-mcp-oauth2 \
  --query SecretString \
  --output text \
  --region us-east-1
```

### Updating a Secret

```bash
# Update secret value
aws secretsmanager update-secret \
  --secret-id finance-mcp-oauth2 \
  --secret-string '{"MCP_CLIENT_ID":"new-client","MCP_CLIENT_SECRET":"new-secret"}' \
  --region us-east-1

# Note: Agent needs restart to pick up new values
uv run agentcore launch --auto-update-on-conflict
```

### Deleting a Secret

```bash
# Schedule deletion (30-day recovery window)
aws secretsmanager delete-secret \
  --secret-id finance-mcp-oauth2 \
  --region us-east-1

# Force immediate deletion (cannot be recovered)
aws secretsmanager delete-secret \
  --secret-id finance-mcp-oauth2 \
  --force-delete-without-recovery \
  --region us-east-1
```

## How agent/config.py Works

### Code Flow

```python
def load_config() -> AgentConfig:
    # 1. Load .env file (local development)
    load_dotenv()

    # 2. Check if SECRET_NAME environment variable is set
    secret_name = os.getenv("SECRET_NAME")

    if secret_name:
        # 3. Running in AWS - load from Secrets Manager
        secret_data = _get_secret_from_aws(secret_name, region)
        mcp_client_id = secret_data["MCP_CLIENT_ID"]
        mcp_client_secret = secret_data["MCP_CLIENT_SECRET"]
    else:
        # 4. Running locally - load from environment variables
        mcp_client_id = os.getenv("MCP_CLIENT_ID")
        mcp_client_secret = os.getenv("MCP_CLIENT_SECRET")
```

### Decision Logic

| Environment Variable | Source | Used For |
|---------------------|--------|----------|
| `SECRET_NAME` not set | `.env` file | Local development |
| `SECRET_NAME=finance-mcp-oauth2` | AWS Secrets Manager | AWS deployment |

### Testing Both Modes

**Local mode** (default):
```bash
# No SECRET_NAME set - uses .env
uv run python my_agent.py
```

**AWS mode** (simulated locally):
```bash
# Set SECRET_NAME - fetches from AWS
export SECRET_NAME=finance-mcp-oauth2
uv run python my_agent.py
```

## IAM Permissions for Secrets Manager

### AgentCore Execution Role

AgentCore automatically grants the execution role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:090719695391:secret:finance-mcp-oauth2-*"
    }
  ]
}
```

### Manual IAM Policy (if needed)

If creating custom IAM roles:

```bash
# Create policy
aws iam create-policy \
  --policy-name FinanceMCPSecretsAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:us-east-1:090719695391:secret:finance-mcp-oauth2-*"
    }]
  }'

# Attach to role
aws iam attach-role-policy \
  --role-name my-custom-role \
  --policy-arn arn:aws:iam::090719695391:policy/FinanceMCPSecretsAccess
```

## Best Practices

### Secret Rotation

Schedule automatic rotation:

```bash
aws secretsmanager rotate-secret \
  --secret-id finance-mcp-oauth2 \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:090719695391:function:rotate-oauth2 \
  --rotation-rules AutomaticallyAfterDays=90
```

**Note**: Requires Lambda function to handle rotation logic.

### Access Auditing

Monitor secret access with CloudTrail:

```bash
# Find who accessed secret
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=finance-mcp-oauth2 \
  --region us-east-1
```

### Secret Versioning

Secrets Manager maintains version history:

```bash
# List versions
aws secretsmanager list-secret-version-ids \
  --secret-id finance-mcp-oauth2 \
  --region us-east-1

# Get specific version
aws secretsmanager get-secret-value \
  --secret-id finance-mcp-oauth2 \
  --version-id 5cfb8790-dc7d-4b9d-ba02-905bb68f87e0 \
  --region us-east-1
```

### Cost Optimization

Secrets Manager pricing:
- **$0.40/month** per secret
- **$0.05** per 10,000 API calls

**Tip**: Cache secrets in application memory instead of fetching on every request.

### KMS Encryption

By default, Secrets Manager uses AWS-managed KMS key. For custom encryption:

```bash
# Create KMS key
aws kms create-key --description "Finance MCP secrets encryption"

# Use custom key
aws secretsmanager create-secret \
  --name finance-mcp-oauth2 \
  --kms-key-id arn:aws:kms:us-east-1:090719695391:key/12345678-1234-1234-1234-123456789012 \
  --secret-string '{"MCP_CLIENT_ID":"...","MCP_CLIENT_SECRET":"..."}'
```

## Environment-Specific Configuration

### Summary Table

| Item | Local (.env) | AWS (Secrets Manager) |
|------|-------------|----------------------|
| **OAuth2 credentials** | `.env` file | `finance-mcp-oauth2` secret |
| **URLs** | `.env` file | Environment variables (not secret) |
| **AWS credentials** | `.env` file | IAM execution role |
| **Loading mechanism** | `python-dotenv` | `boto3` |
| **Trigger** | No `SECRET_NAME` | `SECRET_NAME=finance-mcp-oauth2` |

### Non-Secret Configuration

These are **not secrets** (public URLs):
- `AUTH_SERVER_TOKEN_URL`
- `FINANCE_MCP_URL`

Store as **environment variables** in both local and AWS:

```bash
# Local: In .env file
AUTH_SERVER_TOKEN_URL=https://auth.macrospire.com/oauth2/token

# AWS: Pass to agentcore launch
uv run agentcore launch --env AUTH_SERVER_TOKEN_URL=https://auth.macrospire.com/oauth2/token
```

## Troubleshooting

### Issue: "SECRET_NAME set but secret not found"

**Symptoms**:
```
ValueError: MCP_CLIENT_ID is required (from SECRET_NAME or environment)
```

**Diagnosis**:
```bash
# Check if secret exists
aws secretsmanager describe-secret \
  --secret-id finance-mcp-oauth2 \
  --region us-east-1
```

**Solution**:
- Create secret: See "Creating a Secret" section above
- Or unset `SECRET_NAME` to use local `.env`

### Issue: "AccessDeniedException"

**Symptoms**:
```
botocore.exceptions.ClientError: An error occurred (AccessDeniedException) when calling
the GetSecretValue operation: User is not authorized to perform: secretsmanager:GetSecretValue
```

**Solution**:
- Verify IAM role has `secretsmanager:GetSecretValue` permission
- Check resource ARN matches secret name
- Confirm execution role is attached to AgentCore runtime

### Issue: "Secret returns null values"

**Symptoms**:
```
ValueError: MCP_CLIENT_SECRET is required (from SECRET_NAME or environment)
```

**Diagnosis**:
```bash
# Check secret structure
aws secretsmanager get-secret-value \
  --secret-id finance-mcp-oauth2 \
  --query SecretString \
  --output text
```

**Solution**:
- Ensure JSON uses correct key names: `MCP_CLIENT_ID`, `MCP_CLIENT_SECRET`
- Not `client_id`, `clientId`, or other variations

### Issue: "Works locally but not in AWS"

**Checklist**:
1. ✅ Secret created in correct region (us-east-1)
2. ✅ SECRET_NAME environment variable passed to `agentcore launch`
3. ✅ IAM role has Secrets Manager permissions
4. ✅ Secret contains valid JSON with correct keys
5. ✅ Agent code includes `boto3` dependency

## Migration: .env to Secrets Manager

When moving from local to AWS:

1. **Identify secrets** in `.env`:
   ```
   MCP_CLIENT_ID=content-engine-client
   MCP_CLIENT_SECRET=content-engine-secret-2024
   ```

2. **Create Secrets Manager secret** (see above)

3. **Identify non-secrets** (keep as env vars):
   ```
   AUTH_SERVER_TOKEN_URL=https://auth.macrospire.com/oauth2/token
   FINANCE_MCP_URL=https://finance.macrospire.com/mcp
   ```

4. **Deploy with SECRET_NAME**:
   ```bash
   uv run agentcore launch \
     --env SECRET_NAME=finance-mcp-oauth2 \
     --env AUTH_SERVER_TOKEN_URL=... \
     --env FINANCE_MCP_URL=...
   ```

5. **Verify** in CloudWatch logs:
   ```
   INFO - Config: Loading OAuth2 credentials from Secrets Manager (finance-mcp-oauth2)
   ```

## References

- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
- [Secrets Manager Pricing](https://aws.amazon.com/secrets-manager/pricing/)
- [Best Practices for Secrets Management](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [Python python-dotenv](https://pypi.org/project/python-dotenv/)