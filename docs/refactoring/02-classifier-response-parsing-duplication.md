# Refactor Candidate #2: Eliminate Duplicate Response Parsing in Classifiers

## Problem Statement

Both `OllamaClassifier` and `GroqClassifier` have nearly identical `_parse_response()` methods (lines 397-435 and 516-554), resulting in approximately 40 lines of duplicated code. This violates the DRY (Don't Repeat Yourself) principle and creates a maintenance burden.

## Current State Analysis

### Location
- **File**: `src/classifier.py`
- **Duplicate Methods**:
  - `OllamaClassifier._parse_response()` (lines 397-435)
  - `GroqClassifier._parse_response()` (lines 516-554)
- **Lines of Duplication**: ~40 lines per method = 80 total lines

### Current Code Structure

```python
class OllamaClassifier(BaseClassifier):
    def _parse_response(self, response: str, index: int) -> ClassificationResult:
        """Parse LLM response into ClassificationResult."""
        classification = "IC"
        confidence = 0.5
        reasoning = "Could not parse response"
        character = None

        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("Classificatie:"):
                class_text = line.split(":", 1)[1].strip().upper()
                if class_text in ["IC", "OOC", "MIXED"]:
                    classification = class_text
            elif line.startswith("Reden:"):
                reasoning = line.split(":", 1)[1].strip()
            elif line.startswith("Vertrouwen:"):
                try:
                    conf_text = line.split(":", 1)[1].strip()
                    confidence = float(conf_text)
                    confidence = max(0.0, min(1.0, confidence))
                except ValueError:
                    pass
            elif line.startswith("Personage:"):
                char_text = line.split(":", 1)[1].strip()
                if char_text.upper() != "N/A":
                    character = char_text

        return ClassificationResult(
            segment_index=index,
            classification=classification,
            confidence=confidence,
            reasoning=reasoning,
            character=character
        )

# GroqClassifier has IDENTICAL implementation at lines 516-554
```

### Issues

1. **Code Duplication**: Same logic implemented twice
2. **Maintenance Burden**: Bug fixes must be applied to both places
3. **Inconsistency Risk**: Methods could diverge over time
4. **Testing Overhead**: Same logic tested multiple times
5. **Violates DRY Principle**: Don't Repeat Yourself
6. **Hard-coded Strings**: "Classificatie:", "Reden:", etc. repeated in both
7. **Language Coupling**: Dutch field names hard-coded in parser

## Proposed Solution

### Design Overview

Move the parsing logic to the `BaseClassifier` abstract class, making it available to all classifier implementations. Additionally, create a configuration system for field names to support multiple languages.

### New Architecture

```python
@dataclass
class ResponseParsingConfig:
    """Configuration for parsing LLM responses in different languages"""
    classification_field: str = "Classificatie"
    reasoning_field: str = "Reden"
    confidence_field: str = "Vertrouwen"
    character_field: str = "Personage"
    not_applicable: str = "N/A"

    @classmethod
    def from_language(cls, language: str) -> 'ResponseParsingConfig':
        """Factory method for language-specific configs"""
        configs = {
            'nl': cls(),  # Dutch (default)
            'en': cls(
                classification_field="Classification",
                reasoning_field="Reason",
                confidence_field="Confidence",
                character_field="Character",
                not_applicable="N/A"
            ),
        }
        return configs.get(language, configs['en'])


class BaseClassifier(ABC):
    """Abstract base for IC/OOC classifiers"""

    def __init__(self):
        self.parsing_config = ResponseParsingConfig.from_language(
            Config.WHISPER_LANGUAGE
        )

    @abstractmethod
    def classify_segments(
        self,
        segments: List[Dict],
        character_names: List[str],
        player_names: List[str]
    ) -> List[ClassificationResult]:
        """Classify segments as IC or OOC"""
        pass

    def parse_response(
        self,
        response: str,
        index: int
    ) -> ClassificationResult:
        """
        Parse LLM response into ClassificationResult.

        This method is shared by all classifier implementations.
        """
        classification = "IC"
        confidence = 0.5
        reasoning = "Could not parse response"
        character = None

        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()

            # Extract classification
            if line.startswith(f"{self.parsing_config.classification_field}:"):
                class_text = line.split(":", 1)[1].strip().upper()
                if class_text in ["IC", "OOC", "MIXED"]:
                    classification = class_text

            # Extract reasoning
            elif line.startswith(f"{self.parsing_config.reasoning_field}:"):
                reasoning = line.split(":", 1)[1].strip()

            # Extract confidence
            elif line.startswith(f"{self.parsing_config.confidence_field}:"):
                try:
                    conf_text = line.split(":", 1)[1].strip()
                    confidence = float(conf_text)
                    confidence = max(0.0, min(1.0, confidence))
                except ValueError:
                    pass

            # Extract character
            elif line.startswith(f"{self.parsing_config.character_field}:"):
                char_text = line.split(":", 1)[1].strip()
                if char_text.upper() != self.parsing_config.not_applicable:
                    character = char_text

        return ClassificationResult(
            segment_index=index,
            classification=classification,
            confidence=confidence,
            reasoning=reasoning,
            character=character
        )

    def preflight_check(self):
        """Return an iterable of PreflightIssue objects."""
        return []


class OllamaClassifier(BaseClassifier):
    """IC/OOC classifier using local Ollama LLM."""

    def __init__(self, model: str = None, base_url: str = None, fallback_model: Optional[str] = None):
        super().__init__()  # Initialize parsing config
        # ... rest of initialization

    # Remove _parse_response() - now inherited from BaseClassifier
    # Update _classify_with_context to use self.parse_response()


class GroqClassifier(BaseClassifier):
    """IC/OOC classifier using the Groq API."""

    def __init__(self, api_key: str = None, model: str = "llama3-8b-8192"):
        super().__init__()  # Initialize parsing config
        # ... rest of initialization

    # Remove _parse_response() - now inherited from BaseClassifier
    # Update classify_segments to use self.parse_response()
```

## Implementation Plan

### Phase 1: Create Base Infrastructure (Low Risk)
**Duration**: 1-2 hours

1. **Create `ResponseParsingConfig` dataclass**
   ```python
   # At top of classifier.py
   @dataclass
   class ResponseParsingConfig:
       """Configuration for parsing LLM responses"""
       # ... implementation
   ```

2. **Add unit tests for config**
   ```python
   def test_response_parsing_config_dutch():
       config = ResponseParsingConfig.from_language('nl')
       assert config.classification_field == "Classificatie"

   def test_response_parsing_config_english():
       config = ResponseParsingConfig.from_language('en')
       assert config.classification_field == "Classification"
   ```

3. **Verify no regressions**
   - Run existing tests
   - Ensure new code doesn't affect behavior yet

### Phase 2: Extract to Base Class (Medium Risk)
**Duration**: 2-3 hours

1. **Add `parse_response()` to `BaseClassifier`**
   - Copy implementation from `OllamaClassifier`
   - Use `self.parsing_config` for field names
   - Add comprehensive docstring
   - Add type hints

2. **Update `BaseClassifier.__init__()`**
   ```python
   def __init__(self):
       self.parsing_config = ResponseParsingConfig.from_language(
           Config.WHISPER_LANGUAGE
       )
   ```

3. **Create extensive unit tests**
   ```python
   class TestBaseClassifierParsing(unittest.TestCase):
       def setUp(self):
           self.classifier = MockClassifier()  # Test implementation

       def test_parse_valid_response(self):
           response = """
           Classificatie: IC
           Reden: Character dialogue
           Vertrouwen: 0.95
           Personage: Gandalf
           """
           result = self.classifier.parse_response(response, 0)
           assert result.classification == "IC"
           assert result.confidence == 0.95
           assert result.character == "Gandalf"

       def test_parse_missing_fields(self):
           response = "Classificatie: OOC"
           result = self.classifier.parse_response(response, 0)
           assert result.classification == "OOC"
           assert result.confidence == 0.5  # default

       def test_parse_invalid_confidence(self):
           response = """
           Classificatie: IC
           Vertrouwen: invalid
           """
           result = self.classifier.parse_response(response, 0)
           assert result.confidence == 0.5  # default

       def test_parse_na_character(self):
           response = """
           Classificatie: OOC
           Personage: N/A
           """
           result = self.classifier.parse_response(response, 0)
           assert result.character is None
   ```

### Phase 3: Update Subclasses (Low Risk)
**Duration**: 1 hour

1. **Update `OllamaClassifier`**
   - Add `super().__init__()` call
   - Remove `_parse_response()` method
   - Update `_classify_with_context()` to use `self.parse_response()`
   ```python
   def _classify_with_context(self, ...):
       # ... existing code ...
       return self.parse_response(response_text, index)  # Use inherited method
   ```

2. **Update `GroqClassifier`**
   - Add `super().__init__()` call
   - Remove `_parse_response()` method
   - Update `classify_segments()` to use `self.parse_response()`
   ```python
   def classify_segments(self, ...):
       for i, segment in enumerate(segments):
           # ... existing code ...
           response_text = self._make_api_call(prompt)
           results.append(self.parse_response(response_text, i))
   ```

### Phase 4: Testing (High Priority)
**Duration**: 2-3 hours

1. **Unit tests for parsing**
   - Test all field combinations
   - Test malformed responses
   - Test empty responses
   - Test Unicode characters
   - Test different languages

2. **Integration tests**
   - Test `OllamaClassifier` with new base method
   - Test `GroqClassifier` with new base method
   - Verify identical behavior to old implementation

3. **Regression tests**
   ```python
   def test_ollama_classifier_parsing_regression():
       """Ensure new parsing produces same results as old"""
       classifier = OllamaClassifier()
       test_responses = load_test_responses()  # Historical data

       for response, expected in test_responses:
           result = classifier.parse_response(response, 0)
           assert result.classification == expected.classification
           assert result.confidence == expected.confidence
   ```

### Phase 5: Documentation (Low Risk)
**Duration**: 1 hour

1. **Update docstrings**
   - Document `parse_response()` in base class
   - Document `ResponseParsingConfig`
   - Add examples of response formats

2. **Update architecture docs**
   - Document parsing strategy
   - Add language support documentation
   - Update class hierarchy diagrams

## Testing Strategy

### Unit Tests

```python
class TestResponseParsing(unittest.TestCase):
    """Test suite for response parsing logic"""

    def test_parse_full_response(self):
        """Test parsing a complete response with all fields"""
        config = ResponseParsingConfig()
        classifier = BaseClassifier()
        classifier.parsing_config = config

        response = """
        Classificatie: IC
        Reden: The character is speaking in first person
        Vertrouwen: 0.92
        Personage: Thorin Oakenshield
        """

        result = classifier.parse_response(response, 5)

        assert result.segment_index == 5
        assert result.classification == "IC"
        assert result.reasoning == "The character is speaking in first person"
        assert abs(result.confidence - 0.92) < 0.001
        assert result.character == "Thorin Oakenshield"

    def test_parse_multiline_reasoning(self):
        """Test parsing reasoning that spans multiple lines"""
        # Only first line after "Reden:" should be captured

    def test_parse_extra_whitespace(self):
        """Test robustness to extra whitespace"""

    def test_parse_case_insensitivity(self):
        """Test that classification values are case-insensitive"""

    def test_parse_invalid_classification(self):
        """Test handling of invalid classification values"""

    def test_parse_confidence_out_of_range(self):
        """Test clamping confidence to [0.0, 1.0]"""
        # Test values < 0 and > 1

    def test_parse_empty_response(self):
        """Test handling of empty or whitespace-only response"""

    def test_parse_missing_all_fields(self):
        """Test defaults when no fields are present"""
```

### Integration Tests

```python
class TestClassifierIntegration(unittest.TestCase):
    """Integration tests with actual classifiers"""

    @pytest.mark.integration
    def test_ollama_classifier_uses_base_parsing(self):
        """Test that OllamaClassifier correctly uses inherited parsing"""
        classifier = OllamaClassifier()

        # Mock the LLM response
        with patch.object(classifier, '_generate_with_retry') as mock_gen:
            mock_gen.return_value = "Classificatie: IC\nVertrouwen: 0.8"

            segments = [{'text': 'Test', 'speaker': 'S1', 'start_time': 0, 'end_time': 1}]
            results = classifier.classify_segments(segments, ['Char1'], ['Player1'])

            assert len(results) == 1
            assert results[0].classification == "IC"
            assert results[0].confidence == 0.8

    @pytest.mark.integration
    def test_groq_classifier_uses_base_parsing(self):
        """Test that GroqClassifier correctly uses inherited parsing"""
        # Similar test for GroqClassifier
```

### Edge Case Tests

```python
def test_parse_unicode_characters():
    """Test handling of Unicode in character names and reasoning"""
    response = """
    Classificatie: IC
    Personage: Elrønd Halfelven
    Reden: Spricht über die Vergangenheit
    """
    # Should handle non-ASCII characters correctly

def test_parse_special_characters():
    """Test handling of special characters in reasoning"""
    response = """
    Classificatie: IC
    Reden: Character says "Hello, world!" with emotion.
    """
    # Should preserve quotes and punctuation
```

## Risks and Mitigation

### Risk 1: Breaking Existing Behavior
**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Comprehensive regression tests
- Copy exact implementation initially
- Use feature flag for gradual rollout
- Test with production data samples

### Risk 2: Language Configuration Errors
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Default to Dutch (current behavior)
- Log warnings when fields not found
- Provide clear error messages
- Document all supported languages

### Risk 3: Subclass Constructor Issues
**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Ensure `super().__init__()` called first
- Add tests for initialization order
- Document initialization requirements
- Use linters to catch missing super calls

### Risk 4: Performance Overhead
**Likelihood**: Low
**Impact**: Low
**Mitigation**:
- Config created once at initialization
- No additional method calls in hot path
- Benchmark parsing performance
- Profile memory usage

## Expected Benefits

### Immediate Benefits
1. **Reduced Code**: Remove ~40 lines of duplicated code
2. **Single Source of Truth**: One implementation to maintain
3. **Easier Bug Fixes**: Fix once, fixes everywhere
4. **Better Testing**: Test parsing logic once, thoroughly
5. **Consistency**: Guaranteed identical behavior across classifiers

### Long-term Benefits
1. **Extensibility**: Easy to add new classifier backends
2. **Internationalization**: Support for multiple languages
3. **Maintainability**: Changes to parsing format easier
4. **Documentation**: Centralized parsing documentation
5. **Testability**: Mock parsing for classifier tests

### Metrics
- **Lines of Code**: Reduce by ~40 lines (5% of classifier.py)
- **Code Duplication**: Eliminate 100% of parsing duplication
- **Test Coverage**: Increase parsing coverage to 100%
- **Maintenance Cost**: Reduce by 50% for parsing changes

## Migration Path

### Backward Compatibility
- Parsing behavior remains identical
- No API changes for classifier users
- Existing tests should pass without modification

### Deprecation (None Required)
This is an internal refactoring with no external API changes.

## Success Criteria

1. ✅ All existing classifier tests pass
2. ✅ New unit tests for `BaseClassifier.parse_response()` (100% coverage)
3. ✅ Regression tests verify identical behavior
4. ✅ Both `OllamaClassifier` and `GroqClassifier` use inherited method
5. ✅ No performance degradation (within 1%)
6. ✅ Code review approved
7. ✅ Documentation updated

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Create Infrastructure | 1-2 hours | None |
| Phase 2: Extract to Base | 2-3 hours | Phase 1 |
| Phase 3: Update Subclasses | 1 hour | Phase 2 |
| Phase 4: Testing | 2-3 hours | Phase 3 |
| Phase 5: Documentation | 1 hour | Phase 4 |
| **Total** | **7-10 hours** | |

## References

- Current implementation: `src/classifier.py:397-435, 516-554`
- Base class: `src/classifier.py:45-61`
- Related refactoring: Candidate #3 (prompt building duplication)
- Design pattern: Template Method Pattern
