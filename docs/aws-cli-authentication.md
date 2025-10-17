# AWS CLI Authentication Guide

## Problem: Invalid AWS Credentials

When running AWS CLI commands, you may encounter:

```bash
$ aws sts get-caller-identity
An error occurred (InvalidClientTokenId) when calling the GetCallerIdentity operation:
The security token included in the request is invalid.
```

This indicates your AWS credentials are invalid or expired.

## Understanding AWS Credential Sources

The AWS CLI checks credentials in this order:

1. **Environment variables** (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. **Shared credentials file** (`~/.aws/credentials`)
3. **Shared config file** (`~/.aws/config`)
4. **IAM role** (when running on EC2/ECS/Lambda)

## Diagnosing the Issue

### Check Which Credentials Are Being Used

```bash
aws configure list
```

Example output:
```
NAME       : VALUE                    : TYPE             : LOCATION
profile    : <not set>                : None             : None
access_key : ****************PDVF     : shared-credentials-file :
secret_key : ****************mUrh     : shared-credentials-file :
region     : eu-west-2                : config-file      : ~/.aws/config
```

This shows:
- **Credentials source**: `~/.aws/credentials` (default profile)
- **Region source**: `~/.aws/config`
- **Last 4 characters** of access key for identification

### Check Available Profiles

```bash
# List profiles in credentials file
cat ~/.aws/credentials | grep -E '^\['

# List profiles in config file
cat ~/.aws/config | grep -E '^\['
```

## Solution 1: Use .env File Credentials (Temporary)

If you have valid credentials in your `.env` file:

```bash
# Export credentials from .env
export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
export AWS_DEFAULT_REGION=us-east-1

# Verify it works
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "090719695391",
    "Account": "090719695391",
    "Arn": "arn:aws:iam::090719695391:root"
}
```

### Run Multiple Commands

```bash
# Chain commands with && to keep environment variables
export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID && \
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY && \
export AWS_DEFAULT_REGION=us-east-1 && \
aws secretsmanager create-secret --name my-secret --secret-string '{"key":"value"}'
```

## Solution 2: Update ~/.aws/credentials (Permanent)

Edit `~/.aws/credentials`:

```bash
vim ~/.aws/credentials
```

Update the `[default]` profile:

```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
```

Update `~/.aws/config` for region:

```bash
vim ~/.aws/config
```

```ini
[default]
region = us-east-1
output = json
```

Now all AWS CLI commands will use these credentials automatically.

## Solution 3: Use AWS Profiles

If you have multiple AWS accounts:

### Create a Named Profile

Edit `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = OLD_KEY
aws_secret_access_key = OLD_SECRET

[bedrock-project]
aws_access_key_id = YOUR_BEDROCK_ACCESS_KEY_ID
aws_secret_access_key = YOUR_BEDROCK_SECRET_ACCESS_KEY
```

Edit `~/.aws/config`:

```ini
[default]
region = eu-west-2

[profile bedrock-project]
region = us-east-1
output = json
```

### Use the Profile

```bash
# Option 1: Use --profile flag
aws sts get-caller-identity --profile bedrock-project

# Option 2: Set environment variable
export AWS_PROFILE=bedrock-project
aws sts get-caller-identity
```

## Solution 4: AWS SSO (Recommended for Enterprise)

If your organization uses AWS SSO:

```bash
# Configure SSO
aws configure sso

# Login
aws sso login

# Use SSO profile
aws sts get-caller-identity --profile your-sso-profile
```

## Common Issues

### Issue: Credentials work in .env but not in AWS CLI

**Cause**: AWS CLI doesn't automatically load `.env` files.

**Solution**: Either export environment variables manually or update `~/.aws/credentials`.

### Issue: "Region not set" error

```bash
# Temporary fix
export AWS_DEFAULT_REGION=us-east-1

# Permanent fix
aws configure set region us-east-1
```

### Issue: Credentials expired

**For temporary credentials** (IAM roles, SSO):
- Credentials typically expire after 1-12 hours
- Re-login: `aws sso login` or refresh your session

**For long-term credentials** (IAM user access keys):
- Keys don't expire unless manually rotated
- If getting errors, the key may have been deactivated
- Generate new access key in AWS Console → IAM → Users → Security credentials

## Security Best Practices

1. **Never commit credentials to git**
   - Add `.env` to `.gitignore`
   - Never commit `~/.aws/credentials`

2. **Rotate credentials regularly**
   - Generate new access keys every 90 days
   - Delete old access keys after rotation

3. **Use IAM roles when possible**
   - For EC2, Lambda, ECS: Use IAM roles instead of access keys
   - For local development: Use AWS SSO

4. **Use least privilege**
   - Only grant permissions needed for the task
   - Avoid using root account credentials

5. **Monitor credential usage**
   - Check CloudTrail for unexpected API calls
   - Set up alerts for suspicious activity

## Verifying Your Setup

Run these commands to verify everything works:

```bash
# Check identity
aws sts get-caller-identity

# Check S3 access
aws s3 ls

# Check Bedrock access
aws bedrock list-foundation-models --region us-east-1 --by-provider anthropic

# Check Secrets Manager access
aws secretsmanager list-secrets --region us-east-1
```

## Our Project Setup

For the AWS Financial AI Agent project:

- **Account ID**: `090719695391`
- **Region**: `us-east-1`
- **Credentials**: Root account access keys
- **Usage**: Bedrock AgentCore deployment, Secrets Manager

**Local development**: Use `.env` file
**AWS CLI operations**: Export environment variables or update `~/.aws/credentials`