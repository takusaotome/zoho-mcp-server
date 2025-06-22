# Contributing to Zoho MCP Server

Thank you for your interest in contributing to the Zoho MCP Server project! 🎉

## 🚀 Quick Start for Contributors

### Prerequisites
- Python 3.12+
- Redis server
- Git

### Development Setup

1. **Fork and clone the repository**:
```bash
git clone https://github.com/your-username/zoho-mcp-server.git
cd zoho-mcp-server
```

2. **Set up development environment**:
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
```

3. **Set up configuration**:
```bash
# Copy environment template
cp config/env.example .env

# Edit .env with your Zoho credentials
# Follow the setup guide in README.md
```

4. **Run tests**:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=server --cov-report=html

# Run security tests
./scripts/run-security-tests.sh
```

## 🛠 Development Guidelines

### Code Style
- Follow PEP 8 standards
- Use type hints for all functions
- Maximum line length: 88 characters
- Use descriptive variable and function names

### Code Quality Tools
We use several tools to maintain code quality:

```bash
# Linting
ruff check server/
ruff check tests/

# Type checking
mypy server/

# Security scanning
bandit -r server/
safety check

# Formatting
black server/ tests/
isort server/ tests/
```

### Testing
- Write tests for all new features
- Maintain test coverage above 90%
- Include unit, integration, and security tests
- Use descriptive test names

### Security
- Never commit secrets or credentials
- Use environment variables for configuration
- Follow security best practices
- Run security tests before submitting

## 📝 Pull Request Process

1. **Create a feature branch**:
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**:
- Write clean, well-documented code
- Add tests for new functionality
- Update documentation as needed

3. **Test your changes**:
```bash
# Run full test suite
pytest

# Run security tests
./scripts/run-security-tests.sh

# Check code quality
ruff check server/ tests/
mypy server/
```

4. **Commit your changes**:
```bash
git add .
git commit -m "feat: add your feature description"
```

5. **Push and create PR**:
```bash
git push origin feature/your-feature-name
```

### Commit Message Format
Use conventional commits format:
- `feat:` new features
- `fix:` bug fixes
- `docs:` documentation changes
- `test:` adding tests
- `refactor:` code refactoring
- `security:` security improvements

## 🐛 Bug Reports

When reporting bugs, please include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs
- Configuration (with secrets redacted)

## 💡 Feature Requests

For new features:
- Describe the use case
- Explain the expected behavior
- Consider implementation complexity
- Check if similar features exist

## 🔒 Security Issues

For security vulnerabilities:
- **DO NOT** create public issues
- Email security concerns privately
- Provide detailed reproduction steps
- Allow time for fixes before disclosure

## 📚 Documentation

Help improve documentation:
- Fix typos and grammar
- Add examples and use cases
- Improve setup guides
- Translate to other languages

## 🎯 Areas for Contribution

We welcome contributions in:
- **New Zoho API integrations** (CRM, Books, etc.)
- **Performance improvements** (caching, async)
- **Security enhancements** (authentication, validation)
- **Testing** (coverage, edge cases)
- **Documentation** (guides, examples)
- **Developer tools** (scripts, utilities)

## 🤝 Code of Conduct

- Be respectful and inclusive
- Help others learn and grow
- Focus on constructive feedback
- Maintain professional communication

## 📞 Getting Help

- Create an issue for bugs/questions
- Check existing documentation
- Review closed issues for solutions
- Join community discussions

Thank you for contributing to Zoho MCP Server! 🚀 