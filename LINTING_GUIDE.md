# 🔍 Linting Guide for ArthaNethra

## Overview

ArthaNethra uses industry-standard linting tools to maintain code quality:
- **Backend (Python):** Ruff + Black + MyPy
- **Frontend (TypeScript):** ESLint + Prettier

---

## Backend Linting (Python)

### Tools

1. **Ruff** — Fast Python linter and formatter
2. **Black** — Code formatter
3. **MyPy** — Static type checker

### Installation

```bash
cd backend
pip install ruff black mypy
```

### Usage

#### Check for issues
```bash
# Run ruff linter
ruff check .

# Run mypy type checker
mypy .
```

#### Auto-fix issues
```bash
# Format code with ruff
ruff format .

# Auto-fix linting issues
ruff check --fix .

# Format with black (alternative)
black .
```

### Configuration

Ruff is configured in:
- `backend/pyproject.toml`
- `backend/.ruff.toml`

Settings:
- Line length: 100 characters
- Python version: 3.11+
- Enabled rules: pycodestyle, pyflakes, isort, bugbear, comprehensions

### Common Issues and Fixes

#### Unused imports
```python
# Bad
from typing import Optional, List
import unused_module

# Good
from typing import Optional, List
# Only import what you use
```

#### Line too long
```python
# Bad
def very_long_function_name_with_many_parameters(param1, param2, param3, param4, param5, param6):

# Good
def very_long_function_name_with_many_parameters(
    param1, param2, param3, 
    param4, param5, param6
):
```

#### Import order
```python
# Good order (ruff/isort will fix this)
# 1. Standard library
import os
import sys
from datetime import datetime

# 2. Third-party
from fastapi import FastAPI
import pandas as pd

# 3. Local
from models.entity import Entity
from services.extraction import ExtractionService
```

---

## Frontend Linting (TypeScript/Angular)

### Tools

1. **ESLint** — TypeScript linter
2. **Prettier** — Code formatter
3. **Angular CLI** — Built-in linter

### Installation

```bash
cd frontend
npm install --save-dev eslint prettier @angular-eslint/schematics
```

### Usage

#### Check for issues
```bash
# Run ESLint
npm run lint

# Or with ng
ng lint
```

#### Auto-fix issues
```bash
# Fix ESLint issues
npm run lint -- --fix

# Format with Prettier
npx prettier --write "src/**/*.{ts,html,scss}"
```

### Configuration

ESLint is configured in:
- `frontend/.eslintrc.json`

Prettier is configured in:
- `frontend/.prettierrc`

### Common Issues and Fixes

#### Unused variables
```typescript
// Bad
function processData(data: any, unusedParam: string) {
  return data;
}

// Good
function processData(data: any) {
  return data;
}

// Or use underscore for intentionally unused
function processData(data: any, _unusedParam: string) {
  return data;
}
```

#### Any type usage
```typescript
// Bad
function process(data: any) {
  return data;
}

// Good
interface DataType {
  id: string;
  name: string;
}

function process(data: DataType) {
  return data;
}
```

#### Console statements
```typescript
// Bad (in production code)
console.log('Debug info');

// Good (only for debugging, remove before commit)
// Or use allowed methods
console.error('Error occurred');
console.warn('Warning');
```

---

## Using the Makefile

For convenience, use the provided Makefile:

```bash
# Lint everything
make lint

# Format everything
make format

# Lint backend only
make lint-backend

# Lint frontend only
make lint-frontend

# Format backend
make format-backend

# Format frontend
make format-frontend
```

---

## Pre-commit Hooks (Optional)

### Install pre-commit

```bash
pip install pre-commit
```

### Create `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier
        files: \.(ts|html|scss)$
```

### Install hooks

```bash
pre-commit install
```

Now linting runs automatically on every commit!

---

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/lint.yml`:

```yaml
name: Lint

on: [push, pull_request]

jobs:
  lint-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install ruff
      - run: cd backend && ruff check .

  lint-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint
```

---

## VS Code Integration

### Recommended Extensions

Add to `.vscode/extensions.json`:

```json
{
  "recommendations": [
    "charliermarsh.ruff",
    "ms-python.python",
    "angular.ng-template",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode"
  ]
}
```

### Settings

Add to `.vscode/settings.json`:

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    }
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.eslint": true
    }
  },
  "[html]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  }
}
```

---

## Quick Reference

### Backend Commands
```bash
# Check
ruff check .
mypy .

# Fix
ruff format .
ruff check --fix .
```

### Frontend Commands
```bash
# Check
npm run lint

# Fix
npm run lint -- --fix
npx prettier --write "src/**/*.{ts,html,scss}"
```

### All at Once
```bash
make lint    # Check everything
make format  # Fix everything
```

---

## Current Status

✅ **Backend:** No linting errors (all Python files are clean)  
⚠️ **Frontend:** Expected errors due to missing node_modules  

To resolve frontend errors:
```bash
cd frontend
npm install
npm run lint
```

---

## Before Committing

Always run:
```bash
# 1. Format code
make format

# 2. Check for issues
make lint

# 3. Run tests
make test

# 4. Commit if all pass
git add .
git commit -m "your message"
```

---

## Troubleshooting

### Ruff not found
```bash
pip install ruff
```

### ESLint errors after npm install
```bash
cd frontend
npm install --save-dev @angular-eslint/schematics
ng add @angular-eslint/schematics
```

### Prettier not formatting
```bash
cd frontend
npm install --save-dev prettier
```

---

**Keep your code clean! 🧹**

