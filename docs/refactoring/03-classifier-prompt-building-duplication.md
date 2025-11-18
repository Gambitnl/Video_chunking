# Refactor Candidate #3: Eliminate Duplicate Prompt Building in Classifiers

## Problem Statement

Both `OllamaClassifier` and `GroqClassifier` have identical `_build_prompt()` methods (lines 180-199 and 496-514), resulting in duplicated prompt construction logic. This is tightly coupled with Refactor Candidate #2 and should be addressed together or sequentially.

## Current State Analysis

### Location
- **File**: `src/classifier.py`
- **Duplicate Methods**:
  - `OllamaClassifier._build_prompt()` (lines 180-199)
  - `GroqClassifier._build_prompt()` (lines 496-514)
- **Lines of Duplication**: ~20 lines per method = 40 total lines

### Current Code Structure

```python
class OllamaClassifier(BaseClassifier):
    def _build_prompt(
        self,
        prev_text: str,
        current_text: str,
        next_text: str,
        character_names: List[str],
        player_names: List[str]
    ) -> str:
        """Build classification prompt from the template."""
        char_list = ", ".join(character_names) if character_names else "Unknown"
        player_list = ", ".join(player_names) if player_names else "Unknown"

        return self.prompt_template.format(
            char_list=char_list,
            player_list=player_list,
            prev_text=prev_text,
            current_text=current_text,
            next_text=next_text
        )

# GroqClassifier has IDENTICAL implementation at lines 496-514
```

### Issues

1. **Code Duplication**: Identical logic implemented twice
2. **Prompt Template Loading Duplication**: Both classes load prompts identically
3. **Maintenance Burden**: Changes must be applied in two places
4. **Testing Redundancy**: Same logic tested multiple times
5. **Inconsistency Risk**: Implementations could diverge
6. **Violates DRY**: Don't Repeat Yourself principle violated
7. **Limited Flexibility**: Hard to add new context or modify prompt structure

## Proposed Solution

### Design Overview

Move prompt building and template management to the `BaseClassifier` abstract class. Create a more sophisticated prompt management system that supports:
- Multiple languages
- Template versioning
- Context extension
- Prompt caching

### New Architecture

```python
@dataclass
class PromptContext:
    """Context information for building classification prompts"""
    prev_text: str
    current_text: str
    next_text: str
    character_names: List[str]
    player_names: List[str]
    additional_context: Optional[Dict[str, str]] = None

    def format_character_list(self) -> str:
        """Format character names for prompt"""
        return ", ".join(self.character_names) if self.character_names else "Unknown"

    def format_player_list(self) -> str:
        """Format player names for prompt"""
        return ", ".join(self.player_names) if self.player_names else "Unknown"


class PromptTemplateManager:
    """
    Manages prompt templates for classification.

    Handles:
    - Loading templates from files
    - Language-specific templates
    - Template caching
    - Version management
    """

    def __init__(self, language: str = "en"):
        self.language = language
        self.logger = get_logger("classifier.prompts")
        self._template_cache: Dict[str, str] = {}

    def load_template(self, template_name: str = "classifier_prompt") -> str:
        """
        Load a prompt template for the configured language.

        Args:
            template_name: Name of the template (without extension)

        Returns:
            Template string

        Raises:
            RuntimeError: If template file not found
        """
        cache_key = f"{template_name}_{self.language}"

        # Check cache first
        if cache_key in self._template_cache:
            return self._template_cache[cache_key]

        # Build path
        template_path = (
            Config.PROJECT_ROOT
            / "src"
            / "prompts"
            / f"{template_name}_{self.language}.txt"
        )

        # Fallback to English if language template not found
        if not template_path.exists():
            self.logger.warning(
                f"Prompt file for language '{self.language}' not found. "
                f"Falling back to English."
            )
            template_path = (
                Config.PROJECT_ROOT
                / "src"
                / "prompts"
                / f"{template_name}_en.txt"
            )

        # Load template
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
                self._template_cache[cache_key] = template
                return template
        except FileNotFoundError:
            raise RuntimeError(f"Prompt file not found at: {template_path}")

    def clear_cache(self):
        """Clear the template cache (useful for testing or hot-reload)"""
        self._template_cache.clear()


class BaseClassifier(ABC):
    """Abstract base for IC/OOC classifiers"""

    def __init__(self, language: str = None):
        self.language = language or Config.WHISPER_LANGUAGE
        self.parsing_config = ResponseParsingConfig.from_language(self.language)
        self.prompt_manager = PromptTemplateManager(self.language)
        self.prompt_template = self.prompt_manager.load_template()

    def build_prompt(self, context: PromptContext) -> str:
        """
        Build classification prompt from context.

        This method is shared by all classifier implementations.

        Args:
            context: Prompt context with all necessary information

        Returns:
            Formatted prompt string ready for LLM
        """
        # Prepare template variables
        template_vars = {
            'char_list': context.format_character_list(),
            'player_list': context.format_player_list(),
            'prev_text': context.prev_text,
            'current_text': context.current_text,
            'next_text': context.next_text,
        }

        # Add any additional context
        if context.additional_context:
            template_vars.update(context.additional_context)

        # Format template
        try:
            return self.prompt_template.format(**template_vars)
        except KeyError as e:
            self.logger.error(
                f"Template formatting error: missing variable {e}. "
                f"Check prompt template for required variables."
            )
            raise

    @abstractmethod
    def classify_segments(
        self,
        segments: List[Dict],
        character_names: List[str],
        player_names: List[str]
    ) -> List[ClassificationResult]:
        """Classify segments as IC or OOC"""
        pass


class OllamaClassifier(BaseClassifier):
    """IC/OOC classifier using local Ollama LLM."""

    def __init__(
        self,
        model: str = None,
        base_url: str = None,
        fallback_model: Optional[str] = None
    ):
        # Initialize base (loads prompt template)
        super().__init__()

        # Ollama-specific initialization
        import ollama
        self.model = model or Config.OLLAMA_MODEL
        self.base_url = base_url or Config.OLLAMA_BASE_URL
        self.fallback_model = fallback_model or getattr(
            Config, "OLLAMA_FALLBACK_MODEL", None
        )
        self.logger = get_logger("classifier.ollama")
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

    def _classify_with_context(
        self,
        prev_text: str,
        current_text: str,
        next_text: str,
        character_names: List[str],
        player_names: List[str],
        index: int
    ) -> ClassificationResult:
        """Classify a single segment with context."""
        # Build prompt using inherited method
        context = PromptContext(
            prev_text=prev_text,
            current_text=current_text,
            next_text=next_text,
            character_names=character_names,
            player_names=player_names
        )
        prompt = self.build_prompt(context)

        # Generate response
        response_text = self._generate_with_retry(prompt, index)
        if response_text is None:
            return ClassificationResult(
                segment_index=index,
                classification="IC",
                confidence=0.5,
                reasoning="Classification failed, defaulted to IC"
            )

        # Parse response using inherited method
        return self.parse_response(response_text, index)


class GroqClassifier(BaseClassifier):
    """IC/OOC classifier using the Groq API."""

    def __init__(self, api_key: str = None, model: str = "llama3-8b-8192"):
        # Initialize base (loads prompt template)
        super().__init__()

        # Groq-specific initialization
        from groq import Groq
        self.api_key = api_key or Config.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("Groq API key required. Set GROQ_API_KEY in .env")

        self.client = Groq(api_key=self.api_key)
        self.model = model
        self.logger = get_logger("classifier.groq")

    def classify_segments(
        self,
        segments: List[Dict],
        character_names: List[str],
        player_names: List[str]
    ) -> List[ClassificationResult]:
        """Classify each segment using the Groq API."""
        results = []
        for i, segment in enumerate(segments):
            prev_text = segments[i-1]['text'] if i > 0 else ""
            current_text = segment['text']
            next_text = segments[i+1]['text'] if i < len(segments) - 1 else ""

            # Build prompt using inherited method
            context = PromptContext(
                prev_text=prev_text,
                current_text=current_text,
                next_text=next_text,
                character_names=character_names,
                player_names=player_names
            )
            prompt = self.build_prompt(context)

            try:
                response_text = self._make_api_call(prompt)
                # Parse response using inherited method
                results.append(self.parse_response(response_text, i))
            except Exception as e:
                self.logger.error(f"Error classifying segment {i} with Groq: {e}")
                results.append(ClassificationResult(
                    segment_index=i,
                    classification="IC",
                    confidence=0.5,
                    reasoning="Classification failed, defaulted to IC"
                ))
        return results
```

## Implementation Plan

### Phase 1: Create Supporting Infrastructure (Low Risk)
**Duration**: 2-3 hours

1. **Create `PromptContext` dataclass**
   ```python
   @dataclass
   class PromptContext:
       """Context information for building classification prompts"""
       prev_text: str
       current_text: str
       next_text: str
       character_names: List[str]
       player_names: List[str]
       additional_context: Optional[Dict[str, str]] = None
   ```

2. **Create `PromptTemplateManager` class**
   - Implement template loading logic
   - Add caching mechanism
   - Handle language fallbacks
   - Add comprehensive logging

3. **Add unit tests**
   ```python
   def test_prompt_context_format_character_list():
       context = PromptContext(
           prev_text="", current_text="", next_text="",
           character_names=["Gandalf", "Frodo"],
           player_names=["Alice", "Bob"]
       )
       assert context.format_character_list() == "Gandalf, Frodo"

   def test_prompt_template_manager_caching():
       manager = PromptTemplateManager("en")
       template1 = manager.load_template()
       template2 = manager.load_template()
       assert template1 is template2  # Same object from cache

   def test_prompt_template_manager_fallback():
       manager = PromptTemplateManager("nonexistent")
       template = manager.load_template()  # Should fallback to English
       assert template is not None
   ```

### Phase 2: Add to Base Class (Medium Risk)
**Duration**: 2 hours

1. **Update `BaseClassifier.__init__()`**
   - Initialize prompt manager
   - Load template at initialization
   - Handle errors gracefully

2. **Add `build_prompt()` method**
   - Copy implementation from existing methods
   - Use `PromptContext` for parameters
   - Add comprehensive docstring
   - Add error handling

3. **Create unit tests**
   ```python
   class TestBaseClassifierPromptBuilding(unittest.TestCase):
       def setUp(self):
           self.classifier = MockClassifier()

       def test_build_prompt_basic(self):
           context = PromptContext(
               prev_text="Previous segment",
               current_text="Current segment",
               next_text="Next segment",
               character_names=["Hero"],
               player_names=["Player"]
           )
           prompt = self.classifier.build_prompt(context)
           assert "Hero" in prompt
           assert "Player" in prompt
           assert "Current segment" in prompt

       def test_build_prompt_no_characters(self):
           context = PromptContext(
               prev_text="", current_text="test",
               next_text="", character_names=[],
               player_names=[]
           )
           prompt = self.classifier.build_prompt(context)
           assert "Unknown" in prompt  # Default value

       def test_build_prompt_additional_context(self):
           context = PromptContext(
               prev_text="", current_text="test",
               next_text="", character_names=[],
               player_names=[],
               additional_context={"campaign": "Lost Mines"}
           )
           prompt = self.classifier.build_prompt(context)
           # If template supports it, should include campaign
   ```

### Phase 3: Update Subclasses (Low Risk)
**Duration**: 1-2 hours

1. **Update `OllamaClassifier`**
   - Remove `_build_prompt()` method
   - Remove template loading code from `__init__`
   - Update `_classify_with_context()` to use `PromptContext` and `self.build_prompt()`

2. **Update `GroqClassifier`**
   - Remove `_build_prompt()` method
   - Remove template loading code from `__init__`
   - Update `classify_segments()` to use `PromptContext` and `self.build_prompt()`

3. **Ensure `super().__init__()` is called**
   - Verify initialization order
   - Test that templates are loaded correctly

### Phase 4: Testing (High Priority)
**Duration**: 2-3 hours

1. **Unit tests for prompt building**
   - Test various context combinations
   - Test empty/None values
   - Test special characters
   - Test Unicode
   - Test very long text

2. **Integration tests**
   ```python
   @pytest.mark.integration
   def test_ollama_classifier_prompt_building():
       classifier = OllamaClassifier()

       with patch.object(classifier.client, 'generate') as mock_gen:
           mock_gen.return_value = {
               'response': 'Classificatie: IC\nVertrouwen: 0.9'
           }

           segments = [
               {'text': 'Test 1', 'speaker': 'S1', 'start_time': 0, 'end_time': 1},
               {'text': 'Test 2', 'speaker': 'S2', 'start_time': 1, 'end_time': 2},
           ]

           results = classifier.classify_segments(
               segments,
               character_names=['Hero'],
               player_names=['Player']
           )

           # Verify prompt was built correctly
           call_args = mock_gen.call_args_list[0]
           prompt = call_args[1]['prompt']
           assert 'Hero' in prompt
           assert 'Player' in prompt
           assert 'Test 1' in prompt

   @pytest.mark.integration
   def test_groq_classifier_prompt_building():
       # Similar test for Groq
   ```

3. **Regression tests**
   - Verify prompts are identical to old implementation
   - Test with historical data
   - Compare outputs

### Phase 5: Documentation (Low Risk)
**Duration**: 1 hour

1. **Update docstrings**
   - Document `PromptContext`
   - Document `PromptTemplateManager`
   - Document `build_prompt()` method
   - Add usage examples

2. **Update architecture docs**
   - Document prompt management strategy
   - Add template creation guide
   - Document language support

3. **Create migration guide** (if API changes)

## Testing Strategy

### Unit Tests

```python
class TestPromptBuilding(unittest.TestCase):
    """Comprehensive tests for prompt building"""

    def test_build_prompt_with_all_fields(self):
        """Test prompt building with complete context"""
        pass

    def test_build_prompt_with_minimal_fields(self):
        """Test prompt building with minimal context"""
        pass

    def test_build_prompt_with_empty_strings(self):
        """Test handling of empty strings"""
        pass

    def test_build_prompt_with_special_characters(self):
        """Test handling of quotes, newlines, etc."""
        pass

    def test_build_prompt_with_very_long_text(self):
        """Test handling of very long context text"""
        pass

    def test_template_formatting_error_handling(self):
        """Test graceful handling of template errors"""
        pass


class TestPromptTemplateManager(unittest.TestCase):
    """Tests for template management"""

    def test_load_existing_template(self):
        """Test loading an existing template"""
        pass

    def test_load_nonexistent_language(self):
        """Test fallback for missing language"""
        pass

    def test_cache_functionality(self):
        """Test that templates are cached"""
        pass

    def test_clear_cache(self):
        """Test cache clearing"""
        pass

    def test_custom_template_name(self):
        """Test loading templates with different names"""
        pass
```

### Integration Tests

```python
@pytest.mark.integration
class TestClassifierPromptIntegration(unittest.TestCase):
    """Test prompt building in real classifiers"""

    def test_ollama_uses_base_prompt_building(self):
        """Verify OllamaClassifier uses inherited method"""
        pass

    def test_groq_uses_base_prompt_building(self):
        """Verify GroqClassifier uses inherited method"""
        pass

    def test_prompt_reaches_llm_correctly(self):
        """Verify formatted prompt is sent to LLM"""
        pass
```

## Risks and Mitigation

### Risk 1: Template Formatting Errors
**Likelihood**: Medium
**Impact**: High
**Mitigation**:
- Validate templates at load time
- Provide clear error messages
- Add template validation tests
- Document required template variables

### Risk 2: Breaking Prompt Behavior
**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Keep exact same formatting logic
- Regression test with historical prompts
- Compare outputs character-by-character
- Feature flag for gradual rollout

### Risk 3: Initialization Order Issues
**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Ensure `super().__init__()` called first
- Document initialization requirements
- Add initialization tests
- Use linters to catch issues

### Risk 4: Performance of Template Loading
**Likelihood**: Low
**Impact**: Low
**Mitigation**:
- Cache templates after first load
- Load templates at initialization (not per-call)
- Benchmark template loading time
- Profile memory usage

## Expected Benefits

### Immediate Benefits
1. **Reduced Code**: Remove ~20 lines of duplication
2. **Single Prompt Logic**: One place to modify prompts
3. **Better Testing**: Test prompt building thoroughly once
4. **Consistency**: Guaranteed identical prompts across backends
5. **Easier Maintenance**: Change prompt logic in one place

### Long-term Benefits
1. **Extensibility**: Easy to add new classifier backends
2. **Template Management**: Better control over prompt versions
3. **A/B Testing**: Can test different prompt templates easily
4. **Internationalization**: Better language support
5. **Debugging**: Easier to log and inspect prompts

### Metrics
- **Lines of Code**: Reduce by ~40 lines (including template loading)
- **Code Duplication**: Eliminate 100% of prompt building duplication
- **Test Coverage**: Increase to 100% for prompt logic
- **Maintenance Cost**: Reduce by 50% for prompt changes

## Migration Path

### Backward Compatibility
- Prompt format remains identical
- No API changes for external users
- Internal method signatures change but are private

### Deprecation (None Required)
This is an internal refactoring with no external API changes.

## Success Criteria

1. ✅ All existing classifier tests pass
2. ✅ New unit tests for prompt building (100% coverage)
3. ✅ Regression tests verify identical prompts
4. ✅ Both classifiers use inherited `build_prompt()`
5. ✅ Template loading tested for all languages
6. ✅ No performance degradation
7. ✅ Code review approved
8. ✅ Documentation updated

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Create Infrastructure | 2-3 hours | None |
| Phase 2: Add to Base Class | 2 hours | Phase 1 |
| Phase 3: Update Subclasses | 1-2 hours | Phase 2 |
| Phase 4: Testing | 2-3 hours | Phase 3 |
| Phase 5: Documentation | 1 hour | Phase 4 |
| **Total** | **8-11 hours** | |

## Related Refactorings

This refactoring should be done in conjunction with:
- **Refactor Candidate #2**: Response parsing duplication
- Together, these eliminate most duplication in classifier implementations
- Can be done sequentially or in parallel

## References

- Current implementation: `src/classifier.py:180-199, 496-514`
- Base class: `src/classifier.py:45-61`
- Prompt templates: `src/prompts/classifier_prompt_*.txt`
- Design pattern: Template Method Pattern
