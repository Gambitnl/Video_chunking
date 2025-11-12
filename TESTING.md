# Testing Guide

## Overview

This project has three levels of testing:

1. **Unit Tests** - Fast, mocked tests that verify logic
2. **Integration Tests** - Tests that call real APIs
3. **System Tests** - End-to-end verification

## Running Tests

### Run All Tests (Except Integration)
```bash
pytest
```

### Run Unit Tests Only
```bash
pytest -m "not integration and not slow"
```

### Run Integration Tests
```bash
# Requires API keys to be set
pytest -m integration
```

### Run Specific Test File
```bash
pytest tests/test_classifier.py -v
```

### Run with Coverage
```bash
pytest --cov=src --cov-report=html
```

## Integration Tests

Integration tests make real API calls and require valid API keys.

### Setup

1. **Set environment variables:**
   ```bash
   # Linux/Mac
   export GROQ_API_KEY="your_groq_key_here"
   export HUGGING_FACE_API_KEY="your_hf_key_here"

   # Windows
   set GROQ_API_KEY=your_groq_key_here
   set HUGGING_FACE_API_KEY=your_hf_key_here
   ```

2. **Or use `.env` file:**
   ```bash
   echo "GROQ_API_KEY=your_key_here" >> .env
   echo "HUGGING_FACE_API_KEY=your_key_here" >> .env
   ```

### Run Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -m integration -v

# Run only API validation tests
pytest tests/integration/test_api_integration.py::TestAPIKeyValidation -v

# Run only model deprecation checks
pytest tests/integration/test_api_integration.py::TestModelDeprecation -v
```

### Skip Integration Tests

Integration tests are automatically skipped if API keys are not configured:

```bash
# This will skip integration tests if no keys found
pytest tests/integration/
```

## Test Structure

```
tests/
├── conftest.py                      # Shared fixtures
├── test_classifier.py               # OllamaClassifier + GroqClassifier unit tests
├── test_transcriber.py              # Transcriber unit tests
├── integration/
│   ├── test_api_integration.py      # Real API tests
│   └── test_sample.py               # Sample integration test
└── system/
    └── test_system.py               # System-level tests
```

## Writing Tests

### Unit Test Example

```python
@patch('src.classifier.Groq')
def test_groq_classifier_init(MockGroq):
    """Test GroqClassifier initialization with mocked API."""
    classifier = GroqClassifier(api_key='test-key')
    assert classifier.api_key == 'test-key'
```

### Integration Test Example

```python
@pytest.mark.integration
def test_groq_real_api():
    """Test GroqClassifier with real API call."""
    if not Config.GROQ_API_KEY:
        pytest.skip("GROQ_API_KEY not configured")

    classifier = GroqClassifier()
    results = classifier.classify_segments([{'text': 'Test'}], [], [])
    assert len(results) == 1
```

## Test Coverage

### Current Coverage

- **OllamaClassifier**: ✅ Full coverage (68 tests)
- **GroqClassifier**: ✅ Full coverage (13 new tests)
- **GroqTranscriber**: ✅ Partial coverage (unit tests)
- **Integration**: ✅ API validation and deprecation checks

### Generating Coverage Report

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html  # Linux/Mac
start htmlcov/index.html  # Windows
```

## CI/CD Testing

### GitHub Actions Workflows

1. **Unit Tests** (`python-app.yml`)
   - Runs on every push/PR
   - Fast, no API keys required
   - Must pass for merge

2. **API Integration Tests** (`api-integration-tests.yml`)
   - Runs on push to main/feature branches
   - Runs weekly (Sundays) to catch deprecations
   - Requires secrets: `GROQ_API_KEY`, `HUGGING_FACE_API_KEY`

3. **Model Deprecation Check**
   - Automatically creates GitHub issue if models deprecated
   - Labels: `bug`, `api`, `urgent`

### Setting Up Secrets

In GitHub repository settings:

1. Go to Settings → Secrets and variables → Actions
2. Add secrets:
   - `GROQ_API_KEY`: Your Groq API key
   - `HUGGING_FACE_API_KEY`: Your HuggingFace token

## Manual API Validation

### Quick Test Script

```bash
python test_api_keys.py
```

Output:
```
================================================================================
API Key Validation Test Suite
================================================================================

================================================================================
Testing Groq API
================================================================================
✓ API Key found: gsk_abc123...
✓ Groq client initialized
✓ API Response: API test successful
✅ Groq API is working correctly!

================================================================================
Testing Hugging Face API
================================================================================
✓ API Key found: hf_xyz789...
✓ Authenticated as: your_username
✅ Hugging Face API is working correctly!

================================================================================
Test Summary
================================================================================
Groq API:         ✅ PASS
Hugging Face API: ✅ PASS

🎉 All APIs are configured correctly!
```

## Troubleshooting

### Integration Tests Failing

1. **Check API keys are set:**
   ```bash
   echo $GROQ_API_KEY
   echo $HUGGING_FACE_API_KEY
   ```

2. **Verify keys are valid:**
   ```bash
   python test_api_keys.py
   ```

3. **Check rate limits:**
   - Groq: Free tier has rate limits
   - HuggingFace: ~1000 requests/day on free tier

### Model Deprecation Errors

If you see errors like:
```
Error code: 400 - {'error': {'message': 'The model `llama3-8b-8192` has been decommissioned...'}}
```

**Fix:**
1. Check current models at [console.groq.com/docs/models](https://console.groq.com/docs/models)
2. Update model names in:
   - `src/classifier.py` (GroqClassifier default model)
   - `src/transcriber.py` (if needed)
   - `test_api_keys.py`
3. Update `CLOUD_INFERENCE_OPTIONS.md` documentation
4. Run tests to verify

### Mocked Tests Not Working

If mocks aren't being applied:

1. **Check patch path:**
   ```python
   @patch('src.classifier.Groq')  # Correct: where it's imported
   # NOT
   @patch('groq.Groq')  # Wrong: where it's defined
   ```

2. **Verify import order:**
   ```python
   @pytest.fixture(autouse=True)
   def patched_config():
       with patch('src.classifier.Config') as MockConfig:
           yield MockConfig

   # Import AFTER patching
   from src.classifier import GroqClassifier
   ```

## Best Practices

1. **Always mock in unit tests** - Don't make real API calls
2. **Mark integration tests** - Use `@pytest.mark.integration`
3. **Skip if no keys** - Integration tests should skip gracefully
4. **Test error cases** - Verify behavior on API errors
5. **Keep tests fast** - Unit tests should run in < 1 second each
6. **Update tests with code** - New features need new tests

## Pytest Markers

```python
@pytest.mark.slow           # Test takes > 5 seconds
@pytest.mark.integration    # Requires real APIs
@pytest.mark.system         # System-level test
```

Run specific markers:
```bash
pytest -m slow              # Run only slow tests
pytest -m "not slow"        # Skip slow tests
pytest -m integration       # Run only integration tests
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Groq API Docs](https://console.groq.com/docs/)
- [HuggingFace API Docs](https://huggingface.co/docs/api-inference/)

## Quick Commands Reference

```bash
# Run all tests
pytest

# Run fast tests only
pytest -m "not integration and not slow"

# Run with coverage
pytest --cov=src

# Run specific test
pytest tests/test_classifier.py::TestGroqClassifier::test_init_with_api_key -v

# Run and stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Verbose output
pytest -vv

# Show print statements
pytest -s

# Run integration tests
pytest -m integration
```
