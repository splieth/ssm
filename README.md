# ssm

> Python CLI that leverages SSM's capability to provide an SSH access to EC2 instances.

## Prerequisites
* [python](https://www.python.org/) >= 3.10
* [uv](https://docs.astral.sh/uv/)
* [session-manager-plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)

## Usage
Run

```bash
uv sync
source .venv/bin/activate
```

to have the virtualenv activated for some profit.

In order to connect to a running EC2 instance, you must provide valid AWS credentials, e.g. by specifying the profile:

```bash
AWS_PROFILE=some-profile "./ssm.py login"
```

## Development
Install dev dependencies and the pre-commit hook:

```bash
uv sync
uv run pre-commit install
```

Run linters, type checks and tests:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy ssm.py tests
uv run pytest
```
