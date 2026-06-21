# Contributing to Phoenix Backup

Thank you for your interest in contributing to **Phoenix Backup**! We welcome contributions from developers, security researchers, UX designers, and testers.

---

## 1. Developer Setup

Phoenix Backup is structured as a monorepo containing:
*   `desktop/`: Electron main process and React/TypeScript frontend.
*   `shared/`: Common Python modules (device discovery, repositories, scoring engines, exporters).
*   `tests/`: Integration and acceptance test suites.

### Pre-requisites
*   Node.js v20+
*   NPM v10+
*   Python v3.10+
*   Android SDK (for companion app development)

### Setup Instructions
1.  Clone the repository:
    ```bash
    git clone https://github.com/google/phoenix-backup.git
    cd phoenix-backup
    ```
2.  Install Node dependencies:
    ```bash
    npm run bootstrap
    ```
3.  Set up the Python environment (optional but recommended):
    ```bash
    python -m venv venv
    # Windows:
    .\venv\Scripts\activate
    # macOS/Linux:
    source venv/bin/activate
    ```

---

## 2. Code Style & Standards

### TypeScript / Frontend
*   We use ESLint and Prettier to format frontend code.
*   Run linting checks:
    ```bash
    npm run lint
    ```
*   Format code automatically:
    ```bash
    npm run format
    ```

### Python / Intelligence Engine
*   Enforce PEP 8 conventions.
*   Document classes and methods with descriptive docstrings.
*   Keep functions focused and modular (following SOLID principles).

---

## 3. Testing Requirements

We enforce high test coverage. Any new feature must be accompanied by corresponding unit or integration tests.

*   Run the Python test suite:
    ```bash
    python -m unittest discover -s shared -p "test_*.py"
    python -m unittest discover -s tests -p "test_*.py"
    ```
*   Ensure all tests pass cleanly before submitting a pull request.

---

## 4. Pull Request Process

1.  Create a feature branch from the `main` branch:
    ```bash
    git checkout -b feature/your-feature-name
    ```
2.  Commit your changes with clear, descriptive commit messages.
3.  Ensure the test suite passes successfully.
4.  Push to your branch and open a Pull Request (PR) targeting the `main` branch.
5.  All PRs require review and approval from at least one core maintainer before merging.
