# Testing Guide - Burmese PC Chatbot

Complete guide for testing the Burmese PC Troubleshooting Chatbot application.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Coverage](#test-coverage)
5. [CI/CD Integration](#cicd-integration)
6. [Troubleshooting](#troubleshooting)

## Quick Start

### Install Test Dependencies
```bash
pip install -r requirements-test.txt
```

### Run All Tests
```bash
pytest
```

### Run with Coverage Report
```bash
pytest --cov=backend --cov-report=html
```

## Test Structure

### Test Organization

```
tests/
├── __init__.py
├── test_api.py              # API endpoint tests
├── test_admin.py            # Admin dashboard auth, metrics, config tests
├── test_database.py         # Database operation tests
├── test_language.py         # Language detection tests
├── test_engine.py           # Chat engine logic tests
├── test_gemini.py           # Gemini integration tests
├── test_frontend.py         # Frontend asset tests
└── test_integration.py      # End-to-end integration tests

conftest.py                 # Pytest fixtures and configuration
pytest.ini                  # Pytest configuration
requirements-test.txt       # Test dependencies
```

### Test Classes

#### test_api.py
- `TestHealthEndpoint` - Health check endpoint tests
- `TestChatEndpoint` - Main chat API tests
- `TestCategoriesEndpoint` - Categories endpoint tests
- `TestTranslateEndpoint` - Translation endpoint tests
- `TestSecurityHeaders` - Security header validation
- `TestRateLimiting` - Rate limiting tests

#### test_database.py
- `TestDatabaseInitialization` - Schema and table creation
- `TestChatSessions` - Session management
- `TestChatMessages` - Message logging and retrieval
- `TestTroubleshootingDatabase` - Knowledge base tests
- `TestCachedResponses` - Response caching
- `TestAdminConfig` - Configuration management
- `TestDatabaseIntegrity` - Data integrity checks

#### test_admin.py
- `TestAdminLogin` - Login endpoint (success, failure, session)
- `TestAdminLogout` - Logout and session clearing
- `TestAdminAuthRequired` - Auth guard on protected routes
- `TestAdminMetrics` - Metrics snapshot retrieval
- `TestAdminConfig` - Config get/set, including validation errors

#### test_language.py
- `TestLanguageDetection` - Language detection for Burmese and English

#### test_engine.py
- `TestKeywordExtraction` - Keyword extraction from queries
- `TestQueryProcessing` - Query processing and matching
- `TestResponseFormatting` - Response formatting
- `TestQueryRouting` - Query routing logic
- `TestBurmeseNgramMatching` - Burmese n-gram overlap matching

#### test_gemini.py
- `TestOffTopicRejection` - Off-topic query rejection via Gemini
- `TestIsConfigured` / `TestNoApiKeyFallback` - API key presence handling
- `TestDailyCapExceeded` - Daily Gemini call cap enforcement
- `TestGenerateContentException` / `TestTranslateText` - Error handling and translation
- `TestFallbackMessages` / `TestPlaceholderHooks` - Static fallback text, TTS/STT stubs

#### test_frontend.py
- `TestFrontendAssets` - Asset file existence
- `TestIndexHtml` - HTML structure and content
- `TestStyleCss` - CSS stylesheet validation
- `TestChatJs` - JavaScript file validation
- `TestFrontendIntegration` - Asset integration

#### test_integration.py
- `TestEndToEndChatFlow` - Complete chat flow tests
- `TestResponseQuality` - Response quality checks
- `TestCrossOriginRequests` - CORS testing
- `TestErrorHandling` - Error handling flows
- `TestPerformance` - Performance and response time tests
- `TestSessionManagement` - Session management
- `TestDataConsistency` - Data consistency checks

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api.py

# Run specific test class
pytest tests/test_api.py::TestHealthEndpoint

# Run specific test function
pytest tests/test_api.py::TestHealthEndpoint::test_health_check_returns_200
```

### Test Selection

```bash
# Run only API tests
pytest tests/test_api.py -v

# Run tests matching a pattern
pytest -k "test_chat" -v

# Run tests by marker
pytest -m "api" -v
pytest -m "security" -v
pytest -m "integration" -v

# Run all except slow tests
pytest -m "not slow" -v
```

### Coverage Reports

```bash
# Run with coverage
pytest --cov=backend --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov\index.html  # Windows

# Coverage with terminal report
pytest --cov=backend --cov-report=term-missing

# Set minimum coverage threshold (pytest.ini sets 70%)
pytest --cov=backend --cov-fail-under=70
```

### Output Options

```bash
# Short traceback format
pytest --tb=short

# Long traceback
pytest --tb=long

# No traceback
pytest --tb=no

# Verbose output
pytest -vv

# Quiet mode
pytest -q
```

### Parallel Testing

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest -n 4

# Auto-detect CPU count
pytest -n auto
```

## Test Coverage

### Current Coverage

169 tests passing, 92% overall backend coverage (`pytest --cov=backend --cov-report=term-missing`).

### Coverage Targets

- **Critical paths:** 100% (auth, API, database)
- **Important features:** 90%+ (chat, language detection)
- **Utilities:** 80%+ (helpers, formatting)
- **Overall:** 70%+ minimum

### Improving Coverage

1. Identify uncovered code
```bash
pytest --cov=backend --cov-report=term-missing
```

2. Add tests for uncovered lines
3. Re-run coverage to verify

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests & Security

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements-test.txt
        pip install -r backend/requirements.txt
    
    - name: Lint with flake8
      run: flake8 backend/ --count --select=E9,F63,F7,F82 --show-source --statistics
    
    - name: Check formatting with black
      run: black --check backend/
    
    - name: Run tests
      run: pytest tests/ --cov=backend --cov-fail-under=70
    
    - name: Security audit
      run: safety check -r backend/requirements.txt
```

### GitLab CI Example

```yaml
stages:
  - test
  - security

test:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements-test.txt
    - pip install -r backend/requirements.txt
    - pytest tests/ --cov=backend
  coverage: '/TOTAL.*\s+(\d+%)$/'

security:
  stage: security
  image: python:3.11
  script:
    - pip install safety
    - safety check -r backend/requirements.txt
```

## Test Data

### Fixtures

The `conftest.py` file provides reusable fixtures:

```python
# Test database with seeded data
@pytest.fixture
def test_db:
    """Temporary test database"""
    
# Flask test client
@pytest.fixture
def client(test_db):
    """Flask test client with test database"""
    
# Authenticated admin session
@pytest.fixture
def auth_session(client):
    """Admin session for protected routes"""
    
# Sample test messages
@pytest.fixture
def sample_messages():
    """Test data: English, Burmese, mixed language"""
```

### Using Fixtures

```python
def test_example(client, sample_messages):
    response = client.post('/api/chat', json={
        'message': sample_messages['english']
    })
    assert response.status_code == 200
```

## Troubleshooting

### Common Issues

#### ImportError: No module named 'backend'

**Solution:** Add backend to Python path
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
pytest
```

#### Database Lock Error

**Solution:** Clean up test databases
```bash
rm -f /tmp/*.db
pytest
```

#### Timeout in Tests

**Solution:** Increase timeout in pytest.ini
```ini
timeout = 60
```

#### CORS Errors in Tests

**Solution:** Set test environment variables
```bash
export ALLOWED_ORIGINS="http://localhost"
pytest
```

### Debug Mode

```bash
# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest --pdbcls=IPython.terminal.debugger:TerminalPdb

# Show local variables on failure
pytest -l
```

### Verbose Output

```bash
# Show all test names
pytest --collect-only

# Show test execution time
pytest --durations=10

# Show fixture usage
pytest --fixtures
```

## Performance Testing

### Response Time Tests

The integration tests include performance checks:

```python
def test_health_check_is_fast(client):
    """Health check should be fast (< 100ms)"""
    import time
    start = time.time()
    client.get('/health')
    elapsed = time.time() - start
    assert elapsed < 1.0
```

### Load Testing

For load testing, use Apache Bench or wrk:

```bash
# Apache Bench
ab -n 1000 -c 10 http://localhost:5000/health

# wrk (more powerful)
wrk -t 4 -c 100 -d 30s http://localhost:5000/health
```

## Security Testing

### OWASP Testing

Run security-specific tests:

```bash
pytest tests/ -m security -v
```

### Manual Security Testing

Use OWASP ZAP for comprehensive security scanning:

```bash
# Docker-based scanning
docker run -t owasp/zap2docker-stable zap-baseline.py -t http://localhost

# Or GUI version
owasp-zap
```

### Dependency Audit

```bash
# Check for known vulnerabilities
safety check -r backend/requirements.txt

# Or use pip-audit
pip install pip-audit
pip-audit
```

## Code Quality

### Linting

```bash
# Flake8
flake8 backend/ --max-line-length=100

# Pylint
pylint backend/
```

### Formatting

```bash
# Black (auto-format)
black backend/

# Check formatting without changes
black --check backend/
```

### Type Checking

```bash
# MyPy (if type hints added)
mypy backend/
```

## Continuous Improvement

### Test Maintenance

1. **Review tests monthly** for:
   - Deprecated assertions
   - Broken dependencies
   - Outdated test data

2. **Update tests when**:
   - Code changes
   - New features added
   - Bugs fixed

3. **Monitor coverage**:
   - Check coverage reports
   - Identify gaps
   - Add missing tests

### Test Metrics

Track these metrics:

- **Pass Rate:** Should be 100%
- **Coverage:** Target 70%+
- **Execution Time:** < 5 minutes total
- **Flakiness:** < 1% (tests shouldn't randomly fail)

## Best Practices

### Writing Good Tests

**Do:**
- Test one thing per test
- Use descriptive test names
- Use fixtures for setup
- Keep tests independent
- Mock external dependencies

**Don't:**
- Test multiple things in one test
- Use generic test names
- Depend on test execution order
- Make tests interdependent
- Make real API calls in tests

### Test Organization

```python
# Good: Clear structure
class TestFeature:
    def test_feature_works(self, client):
        """Feature should do X"""
        # Arrange
        data = {'input': 'value'}
        
        # Act
        response = client.post('/endpoint', json=data)
        
        # Assert
        assert response.status_code == 200
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/en/latest/testing/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Testing Best Practices](https://testingjavascript.com/)

## Support

For questions about testing:
- Check test examples in each test file
- Review conftest.py fixtures
- Consult pytest documentation

Python version: 3.11+
