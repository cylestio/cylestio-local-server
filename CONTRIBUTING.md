# Contributing to Cylestio Local Server

We love your input! We want to make contributing to Cylestio Local Server as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

### Pull Requests

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Pull Request Guidelines

- Update the README.md with details of changes to the interface, if applicable.
- Update documentation in the `/docs` directory as needed.
- The PR should work for Python 3.9 and above.
- Make sure your code is properly formatted and passes linting.
- Make sure all tests pass.

## Development Setup

Follow these steps to set up the project for development:

1. Clone the repository
   ```bash
   git clone https://github.com/cylestio/cylestio-local-server.git
   cd cylestio-local-server
   ```

2. Create a virtual environment and activate it
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r src/requirements.txt
   pip install -e .  # Install in development mode
   ```

4. Run tests to verify your setup
   ```bash
   python -m pytest
   ```

## Code Style

We use the following tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting

Please ensure your code adheres to these standards before submitting a PR.

## Testing

We use pytest for testing. All new features should include tests. To run tests:

```bash
# Run all tests
python -m pytest

# Run with coverage report
python -m pytest --cov=src
```

## Issue Reporting

When reporting issues, please include:

- A clear description of the issue
- Steps to reproduce
- Expected behavior
- Actual behavior
- Code samples or test cases if applicable
- Your environment (Python version, OS, etc.)

## License

By contributing, you agree that your contributions will be licensed under the project's Apache 2.0 License.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) in all your interactions with the project. 