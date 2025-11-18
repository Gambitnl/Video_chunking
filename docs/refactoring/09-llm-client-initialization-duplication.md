# Refactor Candidate #9: Consolidate LLM Client Initialization

## Problem Statement

Both `OllamaClassifier` (classifier.py:72-106) and `LlmClient` (llm_client.py:9-25) have nearly identical Ollama client initialization code. This duplication creates maintenance overhead and inconsistency risk.

## Current State Analysis

### Location
- **File 1**: `src/classifier.py`
  - **Class**: `OllamaClassifier.__init__()`
  - **Lines**: 72-106

- **File 2**: `src/llm_client.py`
  - **Class**: `LlmClient.__init__()`
  - **Lines**: 9-25

### Current Code Structure

```python
# classifier.py:72-106
class OllamaClassifier(BaseClassifier):
    def __init__(
        self,
        model: str = None,
        base_url: str = None,
        fallback_model: Optional[str] = None
    ):
        import ollama

        self.model = model or Config.OLLAMA_MODEL
        self.base_url = base_url or Config.OLLAMA_BASE_URL
        self.fallback_model = fallback_model or getattr(
            Config,
            "OLLAMA_FALLBACK_MODEL",
            None
        )
        self.logger = get_logger("classifier.ollama")

        # Load prompt template (35 lines)
        prompt_path = Config.PROJECT_ROOT / "src" / "prompts" / f"classifier_prompt_{Config.WHISPER_LANGUAGE}.txt"
        # ... prompt loading logic ...

        # Initialize client
        self.client = ollama.Client(host=self.base_url)

        # Test connection
        try:
            self.client.list()
        except Exception as e:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running.\n"
                f"Install: https://ollama.ai\n"
                f"Error: {e}"
            )


# llm_client.py:9-25
class LlmClient:
    def __init__(self, model: str = None, base_url: str = None):
        import ollama

        self.model = model or Config.OLLAMA_MODEL
        self.base_url = base_url or Config.OLLAMA_BASE_URL

        self.client = ollama.Client(host=self.base_url)

        try:
            self.client.list()
        except Exception as e:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running.\n"
                f"Install: https://ollama.ai\n"
                f"Error: {e}"
            )
```

### Issues

1. **Code Duplication**: Client initialization duplicated
2. **Connection Testing**: Same test logic in both places
3. **Error Messages**: Identical error messages
4. **Import Handling**: Same import pattern
5. **Configuration**: Same config resolution logic
6. **Maintenance Burden**: Changes must be made twice
7. **Inconsistency Risk**: Could diverge over time

## Proposed Solution

### Design Overview

Create a shared `OllamaClientFactory` that handles:
- Client initialization
- Connection testing
- Error handling
- Configuration resolution
- Model management

Option A: **Factory Class** (Recommended)
Option B: **Use LlmClient in OllamaClassifier**

### Option A: Factory Class (Recommended)

```python
# src/llm/ollama_client_factory.py - New file

from typing import Optional
import ollama
from src.config import Config
from src.logger import get_logger


class OllamaClientConfig:
    """Configuration for Ollama client"""

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        fallback_model: Optional[str] = None,
    ):
        self.model = model or Config.OLLAMA_MODEL
        self.base_url = base_url or Config.OLLAMA_BASE_URL
        self.fallback_model = fallback_model or getattr(
            Config,
            "OLLAMA_FALLBACK_MODEL",
            None
        )

    def __repr__(self) -> str:
        return (
            f"OllamaClientConfig(model={self.model}, "
            f"base_url={self.base_url}, "
            f"fallback_model={self.fallback_model})"
        )


class OllamaClientFactory:
    """
    Factory for creating and testing Ollama clients.

    Handles:
    - Client initialization
    - Connection testing
    - Error handling
    - Configuration resolution
    """

    def __init__(self):
        self.logger = get_logger("ollama_factory")

    def create_client(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        fallback_model: Optional[str] = None,
        test_connection: bool = True,
    ) -> tuple[ollama.Client, OllamaClientConfig]:
        """
        Create and configure an Ollama client.

        Args:
            model: Model name (defaults to Config.OLLAMA_MODEL)
            base_url: Ollama server URL (defaults to Config.OLLAMA_BASE_URL)
            fallback_model: Fallback model for errors
            test_connection: Whether to test connection on creation

        Returns:
            Tuple of (client, config)

        Raises:
            RuntimeError: If connection test fails
            ImportError: If ollama package not installed
        """
        # Create config
        config = OllamaClientConfig(
            model=model,
            base_url=base_url,
            fallback_model=fallback_model,
        )

        self.logger.debug(
            "Creating Ollama client with config: %s", config
        )

        # Import ollama
        try:
            import ollama
        except ImportError as exc:
            raise ImportError(
                "ollama package not installed. "
                "Install with: pip install ollama"
            ) from exc

        # Create client
        client = ollama.Client(host=config.base_url)

        # Test connection if requested
        if test_connection:
            self._test_connection(client, config.base_url)

        self.logger.info(
            "Ollama client created successfully (model=%s, url=%s)",
            config.model,
            config.base_url,
        )

        return client, config

    def _test_connection(self, client: ollama.Client, base_url: str):
        """
        Test connection to Ollama server.

        Args:
            client: Ollama client to test
            base_url: Server URL for error messages

        Raises:
            RuntimeError: If connection fails
        """
        try:
            models = client.list()
            self.logger.debug(
                "Connection test successful. Available models: %d",
                len(models.get('models', []))
            )
        except Exception as exc:
            error_msg = (
                f"Could not connect to Ollama at {base_url}. "
                f"Make sure Ollama is running.\n"
                f"Install: https://ollama.ai\n"
                f"Error: {exc}"
            )
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from exc

    def test_model_available(
        self,
        client: ollama.Client,
        model_name: str
    ) -> bool:
        """
        Test if a specific model is available.

        Args:
            client: Ollama client
            model_name: Model name to check

        Returns:
            True if model is available, False otherwise
        """
        try:
            models_response = client.list()
            available_models = [
                m['name'] for m in models_response.get('models', [])
            ]
            return model_name in available_models
        except Exception as exc:
            self.logger.warning(
                "Could not check model availability: %s", exc
            )
            return False

    def ensure_model_pulled(
        self,
        client: ollama.Client,
        model_name: str
    ):
        """
        Ensure a model is downloaded.

        Args:
            client: Ollama client
            model_name: Model to pull if not available

        Raises:
            RuntimeError: If model pull fails
        """
        if self.test_model_available(client, model_name):
            self.logger.debug("Model %s is already available", model_name)
            return

        self.logger.info("Pulling model %s...", model_name)
        try:
            client.pull(model_name)
            self.logger.info("Model %s pulled successfully", model_name)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to pull model {model_name}: {exc}"
            ) from exc


# Update OllamaClassifier to use factory
class OllamaClassifier(BaseClassifier):
    """IC/OOC classifier using local Ollama LLM."""

    def __init__(
        self,
        model: str = None,
        base_url: str = None,
        fallback_model: Optional[str] = None
    ):
        super().__init__()  # Initialize base (prompt loading, etc.)

        # Create Ollama client using factory
        factory = OllamaClientFactory()
        self.client, config = factory.create_client(
            model=model,
            base_url=base_url,
            fallback_model=fallback_model,
            test_connection=True,
        )

        self.model = config.model
        self.base_url = config.base_url
        self.fallback_model = config.fallback_model
        self.logger = get_logger("classifier.ollama")

        self.logger.info(
            "OllamaClassifier initialized with model %s", self.model
        )

    # ... rest of methods unchanged


# Update LlmClient to use factory
class LlmClient:
    """Client for interacting with an LLM."""

    def __init__(self, model: str = None, base_url: str = None):
        factory = OllamaClientFactory()
        self.client, config = factory.create_client(
            model=model,
            base_url=base_url,
            test_connection=True,
        )

        self.model = config.model
        self.base_url = config.base_url

    def generate(self, prompt: str, options: dict = None) -> dict:
        """Generate text from the LLM."""
        return self.client.generate(
            model=self.model,
            prompt=prompt,
            options=options or {},
        )
```

### Option B: Use LlmClient in OllamaClassifier

```python
# Simpler option: Have OllamaClassifier use LlmClient internally

class OllamaClassifier(BaseClassifier):
    """IC/OOC classifier using local Ollama LLM."""

    def __init__(
        self,
        model: str = None,
        base_url: str = None,
        fallback_model: Optional[str] = None
    ):
        super().__init__()

        # Use LlmClient for connection
        self.llm_client = LlmClient(model=model, base_url=base_url)

        self.model = self.llm_client.model
        self.base_url = self.llm_client.base_url
        self.client = self.llm_client.client  # For direct access if needed
        self.fallback_model = fallback_model or getattr(
            Config, "OLLAMA_FALLBACK_MODEL", None
        )
        self.logger = get_logger("classifier.ollama")

    def _generate_with_model(self, model: str, prompt: str, *, low_vram: bool = False):
        """Generate using LlmClient"""
        options = self._default_generation_options()
        if low_vram:
            options["low_vram"] = True
            if "num_ctx" in options:
                options["num_ctx"] = min(options["num_ctx"], 1024)

        # Use the client's generate method
        return self.llm_client.generate(prompt, options)
```

## Implementation Plan

### Phase 1: Create Factory (Option A - Recommended)
**Duration**: 3-4 hours

1. **Create `OllamaClientFactory` class**
   - Implement `create_client()`
   - Implement `_test_connection()`
   - Implement `test_model_available()`
   - Implement `ensure_model_pulled()`

2. **Create `OllamaClientConfig` dataclass**
   - Implement configuration logic
   - Add repr for debugging

3. **Add unit tests**
   ```python
   class TestOllamaClientFactory(unittest.TestCase):
       def test_create_client_default_config(self):
           """Test creating client with defaults"""
           factory = OllamaClientFactory()
           client, config = factory.create_client(test_connection=False)
           assert client is not None
           assert config.model == Config.OLLAMA_MODEL
           assert config.base_url == Config.OLLAMA_BASE_URL

       def test_create_client_custom_config(self):
           """Test creating client with custom config"""
           factory = OllamaClientFactory()
           client, config = factory.create_client(
               model="custom-model",
               base_url="http://localhost:11435",
               test_connection=False
           )
           assert config.model == "custom-model"
           assert config.base_url == "http://localhost:11435"

       @patch('ollama.Client')
       def test_connection_test_success(self, mock_client):
           """Test successful connection"""
           mock_client.return_value.list.return_value = {'models': []}
           factory = OllamaClientFactory()
           client, config = factory.create_client()
           # Should not raise

       @patch('ollama.Client')
       def test_connection_test_failure(self, mock_client):
           """Test connection failure"""
           mock_client.return_value.list.side_effect = Exception("Connection failed")
           factory = OllamaClientFactory()
           with pytest.raises(RuntimeError, match="Could not connect"):
               factory.create_client()

       def test_test_model_available(self):
           """Test checking model availability"""
           # Test implementation
   ```

### Phase 2: Update OllamaClassifier (Medium Risk)
**Duration**: 2 hours

1. **Refactor `__init__()`**
   - Use `OllamaClientFactory`
   - Remove duplicate initialization
   - Keep same public interface

2. **Test changes**
   - Verify same behavior
   - Test with different configs
   - Test connection errors

### Phase 3: Update LlmClient (Low Risk)
**Duration**: 1 hour

1. **Refactor `__init__()`**
   - Use `OllamaClientFactory`
   - Remove duplicate code

2. **Test changes**

### Phase 4: Testing (High Priority)
**Duration**: 2-3 hours

1. **Integration tests**
   ```python
   @pytest.mark.integration
   def test_ollama_classifier_with_factory():
       """Test OllamaClassifier using factory"""
       classifier = OllamaClassifier()
       # Test classification works
       # Verify client is properly initialized

   @pytest.mark.integration
   def test_llm_client_with_factory():
       """Test LlmClient using factory"""
       client = LlmClient()
       # Test generation works
   ```

2. **Error handling tests**
   ```python
   def test_classifier_handles_connection_error():
       """Test classifier handles connection errors gracefully"""
       with patch('ollama.Client') as mock:
           mock.side_effect = Exception("No connection")
           with pytest.raises(RuntimeError):
               OllamaClassifier()
   ```

### Phase 5: Documentation (Low Risk)
**Duration**: 1 hour

1. **Document factory**
2. **Update class docstrings**
3. **Add usage examples**

## Testing Strategy

### Unit Tests

```python
class TestOllamaClientFactory(unittest.TestCase):
    """Test Ollama client factory"""

    def test_create_client(self):
        """Test basic client creation"""
        pass

    def test_connection_test(self):
        """Test connection testing"""
        pass

    def test_model_availability(self):
        """Test model availability check"""
        pass

    def test_error_handling(self):
        """Test error handling"""
        pass


class TestOllamaClassifierWithFactory(unittest.TestCase):
    """Test OllamaClassifier using factory"""

    def test_initialization(self):
        """Test classifier initialization"""
        pass

    def test_custom_config(self):
        """Test with custom configuration"""
        pass

    def test_backward_compatibility(self):
        """Test that public API hasn't changed"""
        pass
```

### Integration Tests

```python
@pytest.mark.integration
class TestOllamaIntegration(unittest.TestCase):
    """Integration tests with real Ollama server"""

    @pytest.mark.skipif(not ollama_available(), reason="Ollama not running")
    def test_classifier_classification(self):
        """Test classification with real Ollama"""
        classifier = OllamaClassifier()
        # Perform classification
        # Verify results

    @pytest.mark.skipif(not ollama_available(), reason="Ollama not running")
    def test_llm_client_generation(self):
        """Test generation with real Ollama"""
        client = LlmClient()
        result = client.generate("Test prompt")
        assert 'response' in result
```

## Risks and Mitigation

### Risk 1: Breaking Existing Code
**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Keep same public API
- Comprehensive tests
- Gradual rollout
- Backward compatibility

### Risk 2: Connection Testing Issues
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Test with real Ollama server
- Mock connection for unit tests
- Provide option to skip test
- Clear error messages

### Risk 3: Configuration Differences
**Likelihood**: Low
**Impact**: Low
**Mitigation**:
- Use exact same config logic
- Test all config combinations
- Document behavior
- Maintain defaults

## Expected Benefits

### Immediate Benefits
1. **Reduced Code**: Eliminate ~20 lines of duplication
2. **Single Source of Truth**: One place for client initialization
3. **Consistency**: Guaranteed identical behavior
4. **Better Testing**: Test initialization once
5. **Reusability**: Factory can be used elsewhere

### Long-term Benefits
1. **Maintainability**: Changes to init logic in one place
2. **Extensibility**: Easy to add new client features
3. **Testability**: Mock factory for tests
4. **Features**: Can add connection pooling, etc.
5. **Documentation**: Centralized initialization docs

### Metrics
- **Lines of Code**: Reduce by ~20 lines
- **Code Duplication**: Eliminate 100% of init duplication
- **Test Coverage**: Increase to 100% for initialization
- **Maintenance Cost**: Reduce by 50% for init changes

## Success Criteria

1. ✅ `OllamaClientFactory` created and tested
2. ✅ `OllamaClassifier` uses factory
3. ✅ `LlmClient` uses factory
4. ✅ All existing tests pass
5. ✅ New unit tests for factory (>90% coverage)
6. ✅ Integration tests verify same behavior
7. ✅ No breaking changes to public APIs
8. ✅ Documentation updated

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Create Factory | 3-4 hours | None |
| Phase 2: Update OllamaClassifier | 2 hours | Phase 1 |
| Phase 3: Update LlmClient | 1 hour | Phase 1 |
| Phase 4: Testing | 2-3 hours | Phases 2-3 |
| Phase 5: Documentation | 1 hour | Phase 4 |
| **Total** | **9-11 hours** | |

## References

- Current implementations:
  - `src/classifier.py:72-106` (OllamaClassifier)
  - `src/llm_client.py:9-25` (LlmClient)
- Ollama Python client: https://github.com/ollama/ollama-python
- Design pattern: Factory Pattern
- Related: Refactor Candidates #2 and #3 (classifier refactorings)
