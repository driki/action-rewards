# Contributing

This project is actively maintained and welcomes contributions.

## Areas where help is welcome

- **New evaluator patterns** -- if you've used action-rewards in a domain (CI/CD, alerting, chatbots, government automation), share the evaluation logic
- **Strategy evolution** -- the current rule system is condition-matching; ideas for smarter strategy learning without adding ML dependencies are welcome
- **Integrations** -- hooks for popular automation tools (GitHub Actions, Airflow, Prefect, n8n)
- **Documentation** -- real-world examples and use cases

## How to contribute

1. Fork the repo
2. Create a branch (`feat/your-feature` or `fix/your-fix`)
3. Add tests for new functionality
4. Run `python -m pytest tests/` to verify
5. Open a PR with a clear description of what and why

## Code style

- Keep it simple. No dependencies beyond stdlib.
- SQLite for storage. No ORMs.
- Tests should be fast (no network, no disk I/O beyond tmp_path).

## Context

This tool was extracted from a larger government data pipeline that automates FOIA processing, municipal portal navigation, and public record classification across hundreds of US jurisdictions. If you're interested in civic tech, government transparency, or public data infrastructure, reach out -- there's more to build.

[Matt MacDonald](https://www.linkedin.com/in/mattmacdonald2/) | [GitHub](https://github.com/driki)
