# Contributing to Civis

Thank you for your interest in contributing to Civis! This document outlines the guidelines for contributing to the project.

---

## 📋 Code of Conduct

By participating in this project, you agree to:
- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Follow the project's coding standards

---

## 🛠 Development Setup

### Prerequisites
- Python 3.10+
- Git
- Telegram Bot Token (for bot development)
- OpenAI API Key (for AI matching features)

### Setup
```bash
# Fork and clone the repository
git clone https://github.com/your-username/civis.git
cd civis

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp civis_bot/.env.example civis_bot/.env

# Edit .env with your tokens
nano civis_bot/.env
```

---

## 🏗 Project Structure

```
civis/
├── civis_bot/                 # Telegram Bot
│   ├── bot.py                 # Entry point
│   ├── config.py              # Configuration
│   ├── database.py            # SQLite operations
│   ├── handlers/              # Command handlers (modular)
│   │   ├── commands.py        # All bot commands
│   │   ├── survey.py          # Registration flow
│   │   └── language.py        # Language selection
│   ├── keyboards.py           # Reply keyboards
│   ├── locales.py             # i18n (EN/RU)
│   └── utils.py               # Helpers
├── mcp_server/                # MCP Server
│   ├── app.py                 # Flask app
│   └── tools/                 # Auto-discovered tools
├── CHANGELOG.md               # Version history
├── CONTRIBUTING.md            # This file
└── README.md                  # Project overview
```

---

## 💻 Development Workflow

### 1. Fork & Clone
1. Fork the repository on GitHub
2. Clone your fork locally
3. Add upstream remote: `git remote add upstream https://github.com/LeonidYasin/civis.git`

### 2. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 3. Make Changes
- Follow the project's coding style
- Write clear, documented code
- Add tests when possible
- Update documentation as needed

### 4. Commit Guidelines
Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new feature
fix: correct a bug
docs: update documentation
style: format code
refactor: restructure code
perf: improve performance
test: add tests
chore: update dependencies
```

### 5. Push and Create PR
```bash
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub.

---

## 🧪 Testing

### Running the Bot
```bash
cd civis_bot
python bot.py
```

### Testing Commands
Use the Telegram bot interface to test commands:
1. Send `/start` to start the registration flow
2. Test individual commands: `/profile`, `/citizens`, `/offer`, etc.
3. Verify edge cases and error handling

### Testing MCP Server
```bash
cd mcp_server
python app.py
```

---

## 📝 Documentation

### Updating README
- Keep the README up-to-date with new features
- Ensure command lists and setup instructions are accurate

### Updating CHANGELOG
- Add entries under the appropriate version
- Follow the format: `### Added`, `### Changed`, `### Fixed`

### Code Documentation
- Use docstrings for all public functions and classes
- Explain non-obvious logic with comments
- Keep docstrings concise but informative

---

## 🎨 Coding Style

### Python
- Follow [PEP 8](https://pep8.org/)
- Use 4 spaces for indentation
- Use descriptive variable names
- Maximum line length: 100 characters

### Example
```python
def get_user(tg_id: int) -> dict:
    """
    Get user data by Telegram ID.

    Args:
        tg_id (int): Telegram user ID

    Returns:
        dict: User data or None if not found
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        columns = ['tg_id', 'username', 'name', ...]
        return dict(zip(columns, row))
    return None
```

---

## 🐛 Reporting Issues

### Bug Reports
- Use the GitHub Issues tracker
- Include steps to reproduce
- Include logs and error messages
- Specify your environment (OS, Python version)

### Feature Requests
- Describe the feature and its use case
- Explain why it would benefit the project
- If possible, suggest implementation details

---

## 🤝 Review Process

1. **Pull Request** — Submit PR with clear description
2. **Review** — Maintainers review code and provide feedback
3. **Changes** — Address review feedback
4. **Approval** — PR is approved and merged
5. **Release** — Changes are released with version bump

---

## 📦 Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality
- **PATCH** version for backwards-compatible bug fixes

---

## 🔗 Useful Links

- [Project Repository](https://github.com/LeonidYasin/civis)
- [Issue Tracker](https://github.com/LeonidYasin/civis/issues)
- [Documentation](https://github.com/LeonidYasin/civis#readme)

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the project's MIT License.

---

Thank you for contributing to Civis! 🚀
