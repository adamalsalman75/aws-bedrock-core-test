# Running Agent on GitLab Runner (Alternative to Bedrock AgentCore)

## Overview

This document describes how to run the financial AI agent directly on GitLab CI/CD runners instead of deploying to AWS Bedrock AgentCore. This approach is ideal when:

- **Data must stay within your organization** (compliance requirement)
- **Files must be written to GitLab runner filesystem** (for committing to repos)
- **You want to avoid AWS container execution** (but still use AWS Bedrock models)

**Key Difference from AgentCore**:
- **AgentCore**: Agent runs in AWS Fargate containers, files written to ephemeral container filesystem
- **GitLab**: Agent runs on GitLab runners (in your infrastructure), files written to runner filesystem

**What Still Uses AWS**:
- Amazon Bedrock API for Claude Sonnet 4.5 model (API calls from GitLab → AWS)
- AWS Secrets Manager for OAuth2 credentials (API calls from GitLab → AWS)

## Architecture

```
GitLab Runner (your infrastructure)
         ↓
   my_agent.py executes
         ↓
    ┌─────────────────────────────────────────┐
    │  1. Load config from env vars           │
    │  2. boto3 → AWS Secrets Manager (HTTPS) │
    │  3. OAuth2 → Finance MCP Server         │
    │  4. boto3 → AWS Bedrock Claude (HTTPS)  │
    │  5. Execute tools (MCP + Strands)       │
    │  6. Write files → GitLab runner FS      │
    └─────────────────────────────────────────┘
         ↓
   Files stay in GitLab infrastructure
```

## Prerequisites

1. **GitLab Project**: Your agent code repository
2. **GitLab Runner**: Configured for your project (self-hosted or GitLab.com shared runners)
3. **AWS Account**: For Bedrock API and Secrets Manager access
4. **IAM Permissions**:
   - `bedrock:InvokeModel` (Claude Sonnet 4.5)
   - `secretsmanager:GetSecretValue` (finance-mcp-oauth2 secret)

## Option 1: GitLab OIDC with AWS (Recommended)

### Why OIDC?

✅ **No long-lived AWS credentials** stored in GitLab
✅ **Temporary credentials** generated per job (expire in 1 hour)
✅ **Scoped by project/branch** using OIDC claims
✅ **Auditable** via AWS CloudTrail

### Step 1: Configure AWS OIDC Provider

```bash
# Add GitLab as trusted identity provider in AWS
aws iam create-open-id-connect-provider \
  --url https://gitlab.com \
  --client-id-list https://gitlab.com \
  --thumbprint-list 7e04de896a3e666ef402c23c2e65ffc448f8e0ec \
  --region us-east-1
```

**For self-hosted GitLab**: Replace `https://gitlab.com` with your GitLab instance URL.

### Step 2: Create IAM Role for GitLab Runner

```bash
# 1. Create trust policy
cat > gitlab-trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::090719695391:oidc-provider/gitlab.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "gitlab.com:sub": "project_path:YOUR_GITLAB_USERNAME/YOUR_PROJECT_NAME:ref_type:branch:ref:main"
        }
      }
    }
  ]
}
EOF

# Replace YOUR_GITLAB_USERNAME and YOUR_PROJECT_NAME with actual values
# Example: "project_path:acme-corp/ai-agents:ref_type:branch:ref:main"

# 2. Create IAM role
aws iam create-role \
  --role-name GitLabAIAgentRunner \
  --assume-role-policy-document file://gitlab-trust-policy.json \
  --description "Role for GitLab CI/CD to run AI agent with Bedrock access" \
  --region us-east-1

# 3. Attach Bedrock permissions
aws iam attach-role-policy \
  --role-name GitLabAIAgentRunner \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# 4. Add Secrets Manager permissions
aws iam put-role-policy \
  --role-name GitLabAIAgentRunner \
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
  }'
```

**Trust Policy Condition Explained**:
- `gitlab.com:sub`: OIDC claim that identifies the GitLab project and branch
- Restricts role assumption to specific project/branch combination
- Prevents other GitLab projects from using this role

### Step 3: Configure GitLab CI/CD Pipeline

```yaml
# .gitlab-ci.yml
variables:
  AWS_DEFAULT_REGION: us-east-1
  AWS_ROLE_ARN: arn:aws:iam::090719695391:role/GitLabAIAgentRunner
  AUTH_SERVER_TOKEN_URL: https://auth.macrospire.com/oauth2/token
  FINANCE_MCP_URL: https://finance.macrospire.com/mcp
  SECRET_NAME: finance-mcp-oauth2

stages:
  - run_agent

run_ai_agent:
  stage: run_agent
  image: python:3.12-slim

  # Request OIDC token from GitLab
  id_tokens:
    GITLAB_OIDC_TOKEN:
      aud: https://gitlab.com

  before_script:
    # Install AWS CLI
    - apt-get update && apt-get install -y awscli

    # Assume AWS role using OIDC token
    - |
      export $(printf "AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s AWS_SESSION_TOKEN=%s" \
      $(aws sts assume-role-with-web-identity \
      --role-arn ${AWS_ROLE_ARN} \
      --role-session-name "gitlab-job-${CI_JOB_ID}" \
      --web-identity-token "${GITLAB_OIDC_TOKEN}" \
      --duration-seconds 3600 \
      --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' \
      --output text))

    # Verify AWS credentials
    - aws sts get-caller-identity

    # Install UV and project dependencies
    - pip install uv
    - uv sync

  script:
    # Run the agent (same command as local development!)
    - uv run python my_agent.py

  artifacts:
    paths:
      - output/           # Files written by agent
      - "*.txt"           # Any text files created
    expire_in: 1 week

  only:
    - main                # Only run on main branch
```

### Step 4: Test the Pipeline

```bash
# Push to GitLab to trigger pipeline
git add .gitlab-ci.yml
git commit -m "Add GitLab CI/CD pipeline with OIDC"
git push origin main

# Monitor pipeline in GitLab UI:
# Project → CI/CD → Pipelines
```

**Expected Output** in job logs:
```
✓ Installing AWS CLI
✓ Assuming role: arn:aws:iam::090719695391:role/GitLabAIAgentRunner
✓ AWS credentials configured (temporary, expires in 1 hour)
✓ Installing UV and dependencies
✓ Running agent: uv run python my_agent.py
✓ Agent execution complete
✓ Uploading artifacts: output/
```

## Option 2: Static AWS Credentials (Not Recommended)

If OIDC setup is not feasible, you can use static AWS credentials as GitLab CI/CD variables.

### Step 1: Create GitLab CI/CD Variables

Go to: **GitLab Project → Settings → CI/CD → Variables**

Add the following variables:
- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key (mark as **Masked** and **Protected**)
- `AWS_DEFAULT_REGION`: `us-east-1`
- `AUTH_SERVER_TOKEN_URL`: `https://auth.macrospire.com/oauth2/token`
- `FINANCE_MCP_URL`: `https://finance.macrospire.com/mcp`
- `SECRET_NAME`: `finance-mcp-oauth2`

### Step 2: Configure GitLab CI/CD Pipeline

```yaml
# .gitlab-ci.yml (simplified version without OIDC)
run_ai_agent:
  stage: run_agent
  image: python:3.12-slim

  before_script:
    - pip install uv
    - uv sync

  script:
    - uv run python my_agent.py

  artifacts:
    paths:
      - output/
    expire_in: 1 week

  only:
    - main
```

**Note**: All environment variables are automatically inherited from GitLab CI/CD settings.

## File Handling

### Files Written by Agent

When the agent uses strands-agents file tools, files are written to the **GitLab runner filesystem**:

```python
# In agent execution
agent.run("Create a file called report.txt with stock analysis")

# File created at: /builds/YOUR_USERNAME/YOUR_PROJECT/report.txt
# (GitLab runner working directory)
```

### Accessing Files in Subsequent Jobs

```yaml
# .gitlab-ci.yml
stages:
  - run_agent
  - process_output

run_ai_agent:
  stage: run_agent
  script:
    - uv run python my_agent.py
  artifacts:
    paths:
      - output/

commit_changes:
  stage: process_output
  script:
    - git config user.email "ai-agent@example.com"
    - git config user.name "AI Agent"
    - git add output/
    - git commit -m "AI-generated files from job ${CI_JOB_ID}" || true
    - git push https://oauth2:${GITLAB_ACCESS_TOKEN}@gitlab.com/YOUR_USERNAME/YOUR_PROJECT.git HEAD:main
  dependencies:
    - run_ai_agent
```

**Required**: Create a GitLab access token with `write_repository` scope and add as `GITLAB_ACCESS_TOKEN` CI/CD variable.

## Environment Variables Reference

### Required Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `AWS_ACCESS_KEY_ID` | OIDC or CI/CD variable | AWS access key (or temp creds from OIDC) |
| `AWS_SECRET_ACCESS_KEY` | OIDC or CI/CD variable | AWS secret key (or temp creds from OIDC) |
| `AWS_SESSION_TOKEN` | OIDC only | Temporary session token from STS |
| `AWS_DEFAULT_REGION` | CI/CD variable | AWS region (`us-east-1`) |
| `AUTH_SERVER_TOKEN_URL` | CI/CD variable | OAuth2 token endpoint |
| `FINANCE_MCP_URL` | CI/CD variable | Finance MCP server URL |
| `SECRET_NAME` | CI/CD variable | Secrets Manager secret name |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_CLIENT_ID` | From Secrets Manager | OAuth2 client ID (if not using `SECRET_NAME`) |
| `MCP_CLIENT_SECRET` | From Secrets Manager | OAuth2 client secret (if not using `SECRET_NAME`) |
| `BYPASS_TOOL_CONSENT` | `false` | Skip tool consent prompts (set to `true` for CI/CD) |

## Code Changes (None Required!)

Your existing `my_agent.py` already works on GitLab runner:

```python
# my_agent.py (no changes needed)
from bedrock_agentcore import BedrockAgentCoreApp
from strands_agents import Agent, BedrockClient
from agent.config import load_config
from agent.mcp_client import create_finance_client

app = BedrockAgentCoreApp()

@app.invoke
def invoke(prompt: str) -> str:
    config = load_config()  # ✅ Reads from env vars or Secrets Manager

    with create_finance_client(config) as finance_client:
        tools = finance_client.list_tools()

        agent = Agent(
            client=BedrockClient(model_id=config.model_id),  # ✅ Uses boto3
            tools=[finance_client.create_tool(t) for t in tools]
        )

        return agent.run(prompt)

if __name__ == "__main__":
    app.run()  # ✅ Works as standalone script
```

**Why it works**:
- `load_config()` uses `os.getenv()` and boto3 - works from any environment
- `BedrockClient` uses boto3 for Bedrock API - works with OIDC temp creds
- File operations use local filesystem - writes to GitLab runner

## Comparison: AgentCore vs GitLab

| Aspect | Bedrock AgentCore | GitLab Runner |
|--------|------------------|---------------|
| **Execution Location** | AWS Fargate containers | GitLab infrastructure |
| **File Storage** | Ephemeral container FS | GitLab runner FS (persistent) |
| **Data Residency** | AWS infrastructure | Your org infrastructure |
| **AWS Credentials** | IAM execution role | OIDC or static credentials |
| **Deployment** | `agentcore launch` | Git push to trigger CI/CD |
| **Scaling** | Automatic (serverless) | GitLab runner capacity |
| **Cost** | AgentCore runtime + Bedrock | GitLab runners + Bedrock |
| **Use Case** | Production agent API | CI/CD workflows, GitLab coding agent |

## Monitoring and Debugging

### View Job Logs

GitLab UI: **Project → CI/CD → Jobs → [Select Job]**

Look for:
- AWS role assumption success/failure
- boto3 Secrets Manager calls
- OAuth2 token acquisition
- MCP connection
- Agent execution output
- File write operations

### Common Issues

**Issue**: `An error occurred (AccessDenied) when calling the AssumeRoleWithWebIdentity operation`

**Solution**: Check trust policy `Condition.StringEquals` matches your GitLab project path exactly:
```bash
# Get OIDC token claims to verify
gitlab_token=$(curl --silent --header "Job-Token: ${CI_JOB_TOKEN}" \
  "${CI_API_V4_URL}/job/token" | jq -r .token)

echo $gitlab_token | cut -d. -f2 | base64 -d | jq .
# Should show: {"sub": "project_path:username/project:ref_type:branch:ref:main", ...}
```

**Issue**: `ValueError: MCP_CLIENT_ID is required`

**Solution**: Ensure `SECRET_NAME` variable is set and IAM role has Secrets Manager permissions.

**Issue**: Files not uploaded as artifacts

**Solution**: Verify `artifacts.paths` in `.gitlab-ci.yml` matches where agent writes files:
```yaml
artifacts:
  paths:
    - output/           # Default strands-agents output directory
    - "**/*.txt"        # All text files recursively
```

## Security Best Practices

1. **Use OIDC instead of static credentials** whenever possible
2. **Restrict OIDC role trust policy** to specific projects/branches
3. **Mark sensitive variables as Protected and Masked** in GitLab
4. **Set artifact expiration** to avoid storing files indefinitely
5. **Audit AWS CloudTrail** for role assumption events
6. **Use protected branches** to prevent unauthorized pipeline runs
7. **Rotate static credentials** regularly if OIDC is not available

## Next Steps

1. **Test locally first**: `uv run python my_agent.py` with `.env` file
2. **Set up AWS OIDC provider** and IAM role
3. **Create `.gitlab-ci.yml`** with OIDC configuration
4. **Test pipeline** on a feature branch before deploying to main
5. **Configure artifact handling** for agent-generated files
6. **Set up downstream jobs** to process/commit files if needed

## References

- [GitLab CI/CD with AWS OIDC](https://docs.gitlab.com/ee/ci/cloud_services/aws/)
- [AWS STS AssumeRoleWithWebIdentity](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRoleWithWebIdentity.html)
- [GitLab CI/CD Variables](https://docs.gitlab.com/ee/ci/variables/)
- [GitLab Artifacts](https://docs.gitlab.com/ee/ci/pipelines/job_artifacts.html)