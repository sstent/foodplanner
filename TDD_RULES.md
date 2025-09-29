# TDD Development Rules

This document outlines the rules for Test-Driven Development (TDD) using pytest within our containerized environment.

## Principles

- **Test-First Approach**: All new features must begin with writing a failing test.
- **Debug-Driven Tests**: When a bug is identified during debugging, a new pytest must be created to reproduce the bug and validate its fix.

## Pytest Execution

Pytest should be run within the Docker Compose environment to ensure consistency and isolation.

### Running Specific Tests

To run tests for a specific file:

```bash
docker compose build
docker compose run --remove-orphans foodtracker pytest tests/<test filename>
```

### Running All Tests

To run all tests in the project:

```bash
docker compose build
docker compose run --remove-orphans foodtracker pytest