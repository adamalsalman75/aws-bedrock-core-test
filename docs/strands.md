# Strands Agents Framework

## Overview

[Strands](https://strandsagents.com/) is a Python agentic framework for building AI agents that use AWS Bedrock models. It provides:

- **Model abstractions**: Unified interface for Bedrock models
- **Tool orchestration**: Automatic tool calling and result handling
- **Built-in tools**: Pre-built tools for files, math, thinking, and data
- **MCP integration**: Connect to Model Context Protocol servers
- **Event loop**: Manages agent execution and tool calls

Strands is designed specifically for AWS Bedrock and AgentCore deployments.

## Why Strands?

Unlike general-purpose agent frameworks (LangChain, etc.), Strands:

✅ **Bedrock-native**: Built specifically for AWS Bedrock models
✅ **AgentCore-ready**: Seamlessly deploys to Bedrock AgentCore
✅ **MCP-first**: Native support for Model Context Protocol
✅ **Minimal overhead**: Lightweight, focused on AWS ecosystem
✅ **Production-ready**: Used by AWS internally

## Core Concepts

### Agent

The main class for creating AI agents:

```python
from strands import Agent
from strands.models import BedrockModel

model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0")

agent = Agent(
    model=model,
    tools=[],  # List of tools
    system_prompt="You are a helpful assistant."
)

result = agent("What is 2+2?")
print(result.message)  # "2+2 equals 4."
```

### BedrockModel

Wrapper for AWS Bedrock models with cross-region inference:

```python
from strands.models import BedrockModel

# Claude Sonnet 4.5 with US cross-region inference
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region="us-east-1"  # Optional, defaults to AWS_DEFAULT_REGION
)
```

**Inference Profiles**:
- `us.anthropic.claude-sonnet-4-5-*` - Routes across us-east-1, us-east-2, us-west-2
- `anthropic.claude-sonnet-4-5-*` - Single region (us-east-1)

**Available models**:
- Claude Sonnet 4.5, Opus 4.1, Haiku 4.5
- Claude 3.5 Sonnet, Opus, Haiku
- Claude 3.0 Sonnet, Opus, Haiku

### Tools

Tools are Python functions with type hints and docstrings:

```python
from strands import Agent

def get_weather(city: str) -> str:
    """Get current weather for a city.

    Args:
        city: Name of the city

    Returns:
        Weather description
    """
    # Implementation
    return f"Weather in {city}: Sunny, 72°F"

agent = Agent(
    model=model,
    tools=[get_weather],
    system_prompt="You are a weather assistant."
)

result = agent("What's the weather in San Francisco?")
# Agent automatically calls get_weather("San Francisco") and uses result
```

### MCP Integration

Connect to MCP servers for external tools:

```python
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

# Create MCP client
mcp_client = MCPClient(
    lambda: streamablehttp_client(
        "https://finance.macrospire.com/mcp",
        headers={"Authorization": f"Bearer {token}"}
    )
)

# Use as context manager
with mcp_client:
    # Get tools from MCP server
    tools = mcp_client.list_tools_sync()

    # Create agent with MCP tools
    agent = Agent(model=model, tools=tools)
    result = agent("What is TSLA stock price?")
```

**Important**: Keep MCP client open during agent execution using `with` statement.

## Built-in Tools (strands-agents-tools)

The `strands-agents-tools` package provides pre-built tools similar to Claude Code.

### Installation

```bash
uv add strands-agents-tools
```

Already included in our `pyproject.toml`.

### File System Tools

#### file_read

Advanced file reading with multiple modes:

```python
from strands_tools import file_read

agent = Agent(model=model, tools=[file_read])

# Mode: view (full content)
agent("Show me the contents of config.py")

# Mode: lines (specific range)
agent("Read lines 10-20 of my_agent.py")

# Mode: search (pattern with context)
agent("Find all TODO comments in the codebase")

# Mode: find (file/directory patterns)
agent("Find all .py files in the agent/ directory")

# Mode: diff (compare files)
agent("Show differences between old_config.py and new_config.py")

# Mode: time_machine (git history)
agent("Show me how auth.py looked 3 commits ago")
```

**Modes**:
- `view` - Full content with syntax highlighting
- `lines` - Read specific line ranges
- `search` - Pattern searching with context
- `find` - File/directory pattern matching
- `diff` - Compare files or directories
- `time_machine` - View Git version history
- `document` - Generate Bedrock document blocks

#### file_write

Secure file writing with user confirmation:

```python
from strands_tools import file_write

agent = Agent(model=model, tools=[file_write])
agent("Create a new file called notes.txt with 'Hello World'")
```

**Features**:
- User confirmation required (unless `BYPASS_TOOL_CONSENT=true`)
- Syntax highlighting for code files
- Backup creation before overwriting

#### editor

Multi-file editing with undo support:

```python
from strands_tools import editor

agent = Agent(model=model, tools=[editor])

# Commands available:
# - view: Display file contents
# - create: Create new file
# - str_replace: Replace string in file
# - insert: Insert text at line
# - undo_edit: Revert last change

agent("Replace 'old_value' with 'new_value' in config.py")
```

**Features**:
- Automatic backups before edits
- Content caching for performance
- Smart line finding for replacements
- Undo support

### Computation Tools

#### calculator

SymPy-powered mathematical engine:

```python
from strands_tools import calculator

agent = Agent(model=model, tools=[calculator])

# Basic arithmetic
agent("Calculate 123 * 456 + 789")

# Algebra
agent("Solve the equation 2x + 5 = 15 for x")

# Calculus
agent("Find the derivative of x^3 + 2x^2 + 1")

# Matrices
agent("Multiply matrices [[1,2],[3,4]] and [[5,6],[7,8]]")
```

**Capabilities**:
- Arithmetic, trigonometry, logarithms
- Equation solving (single and systems)
- Calculus: derivatives, integrals, limits
- Linear algebra: matrices, vectors
- Complex numbers
- Series expansions

### Agent Control Tools

#### think

Recursive thinking for deep analysis:

```python
from strands_tools import think

agent = Agent(model=model, tools=[think])

agent("Think deeply about the implications of quantum computing on cryptography")
# Agent enters recursive thinking mode with multiple reasoning cycles
```

**Use cases**:
- Complex problem-solving
- Multi-step reasoning
- Deep analysis requiring reflection

#### stop

Gracefully terminate event loop:

```python
from strands_tools import stop

agent = Agent(model=model, tools=[stop])
agent("Stop execution when you're done")
```

#### handoff_to_user

Pause execution for human input:

```python
from strands_tools import handoff_to_user

agent = Agent(model=model, tools=[handoff_to_user])
agent("Ask the user for confirmation before proceeding")
```

### Data Tools

#### retrieve

Amazon Bedrock Knowledge Base semantic search:

```python
from strands_tools import retrieve

agent = Agent(model=model, tools=[retrieve])

# Requires KNOWLEDGE_BASE_ID environment variable
agent("Find information about AWS pricing in our knowledge base")
```

**Setup**:
```bash
export KNOWLEDGE_BASE_ID=your-kb-id
export AWS_DEFAULT_REGION=us-east-1
```

#### current_time

Get current timestamp:

```python
from strands_tools import current_time

agent = Agent(model=model, tools=[current_time])
agent("What time is it?")
```

## Tool Consent

By default, file tools require user confirmation for safety.

### Development Mode (Bypass Consent)

```python
import os
os.environ["BYPASS_TOOL_CONSENT"] = "true"

from strands_tools import file_write
agent = Agent(model=model, tools=[file_write])
# No user confirmation required
```

### Production Mode (Require Consent)

```python
# Default behavior - user confirmation required
from strands_tools import file_write
agent = Agent(model=model, tools=[file_write])
# Will prompt user before writing files
```

## Agent Configuration

### System Prompts

Customize agent behavior with system prompts:

```python
agent = Agent(
    model=model,
    tools=[calculator],
    system_prompt="""You are a math tutor for high school students.

    Guidelines:
    - Explain concepts clearly with examples
    - Use the calculator tool for complex calculations
    - Show step-by-step solutions
    - Encourage students to try problems themselves
    """
)
```

### Tool Selection

Agents automatically choose which tools to use:

```python
from strands_tools import calculator, file_read, current_time

agent = Agent(
    model=model,
    tools=[calculator, file_read, current_time],
    system_prompt="You are a helpful assistant with math and file access."
)

# Agent decides which tool(s) to use based on query
result = agent("Calculate 2+2 and read README.md")
# Uses both calculator and file_read
```

### Temperature and Sampling

Control model creativity:

```python
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    temperature=0.7,  # Higher = more creative (0.0-1.0)
    max_tokens=2048   # Maximum response length
)

agent = Agent(model=model, tools=[])
```

### Multiple Agents

Create specialized agents:

```python
# Math specialist
math_agent = Agent(
    model=model,
    tools=[calculator],
    system_prompt="You are a mathematics expert."
)

# Code specialist
code_agent = Agent(
    model=model,
    tools=[file_read, file_write, editor],
    system_prompt="You are a senior software engineer."
)

# Route queries to appropriate agent
query = "Calculate the derivative of x^2"
result = math_agent(query)  # Use math_agent for math queries
```

## Our Project Implementation

### my_agent.py Architecture

```python
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel
from agent import create_finance_client, load_config

app = BedrockAgentCoreApp()
config = load_config()
model = BedrockModel(model_id=config.model_id)

@app.entrypoint
def invoke(payload: dict) -> dict:
    user_message = payload.get("prompt", "Hello!")

    try:
        finance_client = create_finance_client(config)

        # Keep MCP connection open during execution
        with finance_client:
            # Get finance tools from MCP server
            tools = finance_client.list_tools_sync()

            # Create agent with finance tools
            agent = Agent(
                model=model,
                tools=tools,
                system_prompt="You are a financial assistant..."
            )

            result = agent(user_message)
            return {"result": result.message}

    except Exception as e:
        # Fallback to agent without tools
        agent = Agent(model=model, system_prompt="You are a helpful AI assistant.")
        result = agent(user_message)
        return {"result": result.message}
```

**Key patterns**:
1. **Context manager**: Keep MCP client open with `with` statement
2. **Graceful fallback**: Return agent without tools if MCP connection fails
3. **Tool discovery**: Fetch tools dynamically from MCP server
4. **Clean separation**: Configuration, auth, and MCP logic in `agent/` package

## Advanced Topics

### Custom Tools

Create domain-specific tools:

```python
def analyze_sentiment(text: str) -> dict:
    """Analyze sentiment of text.

    Args:
        text: Text to analyze

    Returns:
        dict with sentiment (positive/negative/neutral) and confidence
    """
    # Implementation
    return {"sentiment": "positive", "confidence": 0.95}

agent = Agent(
    model=model,
    tools=[analyze_sentiment],
    system_prompt="You are a sentiment analysis assistant."
)
```

### Tool Composition

Combine multiple tools for complex workflows:

```python
from strands_tools import file_read, calculator

def analyze_csv(file_path: str) -> dict:
    """Analyze CSV file and calculate statistics.

    Args:
        file_path: Path to CSV file

    Returns:
        Statistical summary
    """
    # Read file using file_read internally
    # Calculate stats using calculator internally
    pass

agent = Agent(
    model=model,
    tools=[analyze_csv, file_read, calculator]
)
```

### Error Handling

Handle tool execution errors:

```python
try:
    result = agent("Process the data")
except Exception as e:
    print(f"Agent error: {e}")
    # Fallback logic
```

### Streaming Responses

For real-time output (not yet in our implementation):

```python
# Future feature in Strands
for chunk in agent.stream("Tell me a long story"):
    print(chunk, end="", flush=True)
```

## Performance Tips

1. **Reuse model instances**: Create `BedrockModel` once, use for multiple agents
2. **Cache MCP connections**: Keep MCP clients open for multiple requests
3. **Minimize tool count**: Only include tools needed for the task
4. **Use inference profiles**: `us.anthropic.*` models for better availability
5. **Set max_tokens**: Limit response length to control costs

## Debugging

### Enable verbose logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Strands will log:
# - Model API calls
# - Tool invocations
# - Agent reasoning steps
```

### Inspect tool calls

```python
result = agent("What is 2+2?")

# Access tool calls (if available in result object)
print(result.tool_calls)  # List of tools used
print(result.message)     # Final response
```

## Cost Optimization

### Choose the right model

| Model | Speed | Cost | Use Case |
|-------|-------|------|----------|
| Haiku 4.5 | Fastest | Lowest | Simple queries, high volume |
| Sonnet 4.5 | Medium | Medium | Agents, tool use, complex reasoning |
| Opus 4.1 | Slowest | Highest | Maximum intelligence, research |

### Monitor token usage

```python
# Log API calls to track costs
import boto3
cloudwatch = boto3.client('cloudwatch')

# After agent execution, log metrics
cloudwatch.put_metric_data(
    Namespace='FinancialAgent',
    MetricData=[{
        'MetricName': 'InputTokens',
        'Value': input_token_count,
        'Unit': 'Count'
    }]
)
```

## Resources

- **Official Documentation**: [strandsagents.com](https://strandsagents.com/)
- **GitHub Examples**: [amazon-bedrock-agentcore-samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- **Bedrock Pricing**: [aws.amazon.com/bedrock/pricing](https://aws.amazon.com/bedrock/pricing/)
- **MCP Protocol**: [modelcontextprotocol.io](https://modelcontextprotocol.io/)

## Troubleshooting

### Issue: "Tool not found"

**Cause**: Tool not in agent's tool list

**Solution**: Add tool to `tools=[]` parameter:
```python
agent = Agent(model=model, tools=[calculator, file_read])
```

### Issue: "Access denied" for file operations

**Cause**: File consent required

**Solution**: Set `BYPASS_TOOL_CONSENT=true` or approve when prompted

### Issue: MCP tools not discovered

**Cause**: MCP client closed before tool use

**Solution**: Use context manager:
```python
with mcp_client:
    tools = mcp_client.list_tools_sync()
    agent = Agent(model=model, tools=tools)
    result = agent(query)  # Must be inside context
```

### Issue: "Model not found"

**Cause**: Model not enabled in Bedrock console

**Solution**:
1. Go to AWS Bedrock console
2. Navigate to Model access
3. Request access for Anthropic Claude models
4. Wait for approval (instant for most accounts)