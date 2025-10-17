# Repository Guidelines

## Project Structure & Module Organization
- `agent/`: Core logic — `auth.py` (OAuth2), `config.py` (env + AWS Secrets Manager), `mcp_client.py` (Finance MCP).
- `my_agent.py`: Local entrypoint and AgentCore bootstrap.
- `docs/`: Deployment, secrets, and platform guides.
- `pyproject.toml`: Managed with `uv`; Python 3.13.

## Build, Test, and Development Commands
- Install deps: `uv sync`
- Run locally: `uv run python my_agent.py`
- Add dep: `uv add <package>`
- Quick invoke (local HTTP):
  `curl -X POST http://localhost:8080/invocations -H "Content-Type: application/json" -d '{"prompt":"TSLA price?"}'`
- Deploy (see docs for details):
  `uv run agentcore configure --entrypoint my_agent.py`
  `uv run agentcore launch`

## Coding Style & Naming Conventions
- Python, PEP 8, 4-space indent, max line length ~100 where practical.
- Use type hints and docstrings for public APIs.
- Naming: modules/files `lower_snake_case`; classes `PascalCase`; functions/vars `lower_snake_case`.
- Keep AWS- and MCP-specific configuration centralized in `agent/config.py`.

## Testing Guidelines
- Preferred: pytest. Place tests under `tests/` mirroring package structure.
- Name tests `test_*.py`; keep unit tests fast and isolated (mock AWS/MCP IO).
- Run tests: `uv run pytest -q` (add pytest to dev deps if not present).

## Commit & Pull Request Guidelines
- Commits: imperative mood, concise summary, optional scope. Examples:
  - `Deploy Financial AI Agent to AgentCore`
  - `Add AgentCore build artifacts to .gitignore`
- PRs: include purpose, key changes, test notes, and links to related issues/docs. Add screenshots or sample requests when UX/behavior changes.

## Security & Configuration Tips
- Never commit secrets. Store local creds in `.env`; production in AWS Secrets Manager (see `docs/secrets-management.md`).
- Validate AWS auth (profiles/SSO) per `docs/aws-cli-authentication.md`.
- Keep network calls behind small adapters (easier to mock and secure).

## Agent-Specific Notes
- Use `agent/mcp_client.py` to obtain an authenticated Finance MCP client; avoid duplicating auth flows.
- Prefer configuration via environment variables consumed by `agent/config.py` so deployments and local runs behave consistently.

