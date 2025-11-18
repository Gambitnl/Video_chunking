# Implementation Plan: OOC Topic Analysis Enhancement

**Date**: 2025-11-18
**Feature**: P2 - OOC Keyword & Topic Analysis (Enhancement)
**Effort Estimate**: 2 days
**Actual Effort**: ~3 hours
**Status**: **COMPLETED**
**Owner**: Claude (Sonnet 4.5)

---

## Executive Summary

Enhance the existing OOC (Out-of-Character) analyzer from basic word frequency counting to a sophisticated topic analysis system with TF-IDF scoring, topic clustering, and discussion pattern recognition. This will help D&D groups understand their social dynamics, recurring jokes, and discussion themes.

---

## Current State

### Existing Implementation
- **File**: `src/analyzer.py`
- **Features**:
  - Basic word frequency counting
  - Dutch stop word filtering
  - Simple keyword extraction
- **UI**: `src/ui/social_insights_tab.py` with word cloud generation
- **Tests**: `tests/test_analyzer.py` (6 basic tests)

### Limitations
- No TF-IDF implementation (just raw frequency)
- No topic clustering
- No discussion pattern recognition
- No inside joke detection
- Limited to single-session analysis
- Basic Dutch stop word list (incomplete)

---

## Requirements

### Functional Requirements

#### FR-1: TF-IDF Keyword Extraction
- **Priority**: HIGH
- **Description**: Replace simple word frequency with TF-IDF scoring
- **Acceptance Criteria**:
  - Implement TF-IDF algorithm for keyword extraction
  - Support both single-session and multi-session corpus
  - Return keywords ranked by TF-IDF score
  - Filter by minimum score threshold

#### FR-2: Topic Clustering
- **Priority**: HIGH
- **Description**: Identify discussion topics using clustering algorithms
- **Acceptance Criteria**:
  - Implement LDA (Latent Dirichlet Allocation) for topic modeling
  - Extract 3-10 topics per session (configurable)
  - Label each topic with top N keywords
  - Assign confidence scores to topic assignments

#### FR-3: Multi-Session Analysis
- **Priority**: MEDIUM
- **Description**: Analyze patterns across multiple sessions
- **Acceptance Criteria**:
  - Compare topics across sessions
  - Identify recurring themes
  - Track topic evolution over time
  - Generate comparative visualizations

#### FR-4: Enhanced Insights
- **Priority**: MEDIUM
- **Description**: Generate actionable insights from analysis
- **Acceptance Criteria**:
  - Detect potential inside jokes (high-frequency unique terms)
  - Identify discussion patterns (topic transitions)
  - Calculate diversity metrics (topic distribution)
  - Generate summary statistics

### Non-Functional Requirements

#### NFR-1: Performance
- Analysis should complete within 30 seconds for 10,000-word transcript
- Memory usage should not exceed 500MB for single session
- Support batch processing of 10+ sessions

#### NFR-2: Accuracy
- TF-IDF scores should align with scikit-learn implementation
- Topic coherence score should be >0.4 for meaningful topics
- Keyword extraction should exclude 95%+ of stop words

#### NFR-3: Maintainability
- Code should follow repository style guide
- All functions should have type hints and docstrings
- Test coverage should be >85% for new code

---

## Technical Design

### Architecture

```
src/
  analyzer.py (Enhanced OOC Analyzer)
    - OOCAnalyzer (existing, enhanced)
      - get_keywords() [Enhanced with TF-IDF]
      - get_topics() [NEW]
      - get_insights() [NEW]
    - TopicModeler [NEW class]
      - extract_topics()
      - label_topics()
      - calculate_coherence()
    - MultiSessionAnalyzer [NEW class]
      - compare_sessions()
      - track_evolution()
      - identify_recurring_themes()

src/ui/
  social_insights_tab.py (Enhanced UI)
    - Add topic visualization
    - Add multi-session comparison
    - Add insights dashboard

tests/
  test_analyzer.py (Enhanced tests)
    - TF-IDF tests
    - Topic modeling tests
    - Multi-session tests
    - Edge case tests
```

### Dependencies

**New Dependencies** (to add to requirements.txt):
```python
scikit-learn>=1.3.0    # TF-IDF, clustering
nltk>=3.8              # Better tokenization, lemmatization
gensim>=4.3.0          # LDA topic modeling (optional, lighter than sklearn)
matplotlib>=3.7.0      # Topic visualization (already present?)
wordcloud>=1.9.0       # Word cloud (already present)
```

**Note**: Consider using gensim for LDA as it's more memory-efficient than sklearn for topic modeling.

### Data Structures

#### Keyword Result
```python
@dataclass
class Keyword:
    term: str
    score: float          # TF-IDF score
    frequency: int        # Raw count
    document_frequency: int  # Number of docs containing term
```

#### Topic Result
```python
@dataclass
class Topic:
    id: int
    label: str            # Generated from top keywords
    keywords: List[Tuple[str, float]]  # (term, weight)
    coherence_score: float
    document_proportion: float  # % of documents with this topic
```

#### Session Insights
```python
@dataclass
class SessionInsights:
    session_id: str
    keywords: List[Keyword]
    topics: List[Topic]
    inside_jokes: List[str]  # High-frequency unique terms
    discussion_patterns: Dict[str, Any]  # Topic transitions
    diversity_metrics: Dict[str, float]  # Shannon entropy, etc.
```

---

## Implementation Tasks

### Phase 1: Core Analytics Enhancement (Day 1)

#### Task 1.1: Enhance OOCAnalyzer with TF-IDF
- [ ] Status: Pending
- **Estimated Time**: 2 hours
- **Files**: `src/analyzer.py`
- **Steps**:
  1. Add scikit-learn import for TfidfVectorizer
  2. Implement `_calculate_tfidf()` method
  3. Update `get_keywords()` to use TF-IDF scoring
  4. Add `get_keywords_by_frequency()` for backward compatibility
  5. Add comprehensive Dutch stop word list (use nltk.corpus.stopwords)
  6. Support custom stop word lists

#### Task 1.2: Implement Topic Modeling
- [ ] Status: Pending
- **Estimated Time**: 3 hours
- **Files**: `src/analyzer.py`
- **Steps**:
  1. Create `TopicModeler` class
  2. Implement LDA topic extraction using gensim
  3. Implement automatic topic labeling
  4. Calculate topic coherence scores
  5. Add configurable parameters (num_topics, passes, iterations)
  6. Integrate with OOCAnalyzer via `get_topics()` method

#### Task 1.3: Add Insight Generation
- [ ] Status: Pending
- **Estimated Time**: 2 hours
- **Files**: `src/analyzer.py`
- **Steps**:
  1. Implement inside joke detection (unique high-frequency terms)
  2. Calculate topic diversity metrics
  3. Identify topic transition patterns
  4. Generate summary statistics
  5. Create `get_insights()` method returning SessionInsights

### Phase 2: Multi-Session Analysis (Day 1-2)

#### Task 2.1: Create MultiSessionAnalyzer
- [ ] Status: Pending
- **Estimated Time**: 3 hours
- **Files**: `src/analyzer.py`
- **Steps**:
  1. Create `MultiSessionAnalyzer` class
  2. Implement session loading and aggregation
  3. Build multi-session TF-IDF corpus
  4. Compare topics across sessions
  5. Track topic evolution over time
  6. Identify recurring themes
  7. Generate comparative visualizations data

### Phase 3: UI Enhancement (Day 2)

#### Task 3.1: Update Social Insights Tab
- [ ] Status: Pending
- **Estimated Time**: 2 hours
- **Files**: `src/ui/social_insights_tab.py`
- **Steps**:
  1. Add topic display section (topics with keywords)
  2. Add insights dashboard (inside jokes, patterns, metrics)
  3. Add multi-session comparison mode
  4. Update word cloud to support topic coloring
  5. Add export functionality (JSON, Markdown)
  6. Improve progress feedback and error handling

### Phase 4: Testing (Day 2)

#### Task 4.1: Add Comprehensive Tests
- [ ] Status: Pending
- **Estimated Time**: 2 hours
- **Files**: `tests/test_analyzer.py`
- **Steps**:
  1. Test TF-IDF calculation accuracy
  2. Test topic extraction with known corpus
  3. Test multi-session analysis
  4. Test insight generation
  5. Test edge cases (empty files, single word, etc.)
  6. Test performance with large transcripts
  7. Add integration tests for UI workflow
  8. Target: >85% test coverage

### Phase 5: Documentation & Review (Day 2)

#### Task 5.1: Update Documentation
- [ ] Status: Pending
- **Estimated Time**: 1 hour
- **Files**: `ROADMAP.md`, `docs/USAGE.md`, `README.md`
- **Steps**:
  1. Mark P2 OOC Analysis as COMPLETED in ROADMAP.md
  2. Document new analyzer features in USAGE.md
  3. Add examples of topic analysis output
  4. Update requirements.txt with new dependencies
  5. Add troubleshooting section for common issues

#### Task 5.2: Critical Review
- [ ] Status: Pending
- **Estimated Time**: 1 hour
- **Steps**:
  1. Review implementation for security issues
  2. Check performance with large datasets
  3. Validate test coverage
  4. Identify at least 3 improvements
  5. Document findings in this plan

---

## Testing Strategy

### Unit Tests

```python
# Test TF-IDF calculation
def test_tfidf_calculation():
    # Verify TF-IDF scores match expected values
    # Test with known corpus
    pass

# Test topic extraction
def test_topic_extraction():
    # Verify topics are coherent
    # Test with known document set
    pass

# Test multi-session analysis
def test_multi_session_comparison():
    # Verify cross-session topic matching
    pass

# Test insight generation
def test_inside_joke_detection():
    # Verify high-frequency unique terms are detected
    pass
```

### Integration Tests

```python
# Test full workflow
def test_full_analysis_workflow():
    # Load OOC transcript -> Extract keywords -> Extract topics -> Generate insights
    pass
```

### Performance Tests

```python
# Test large transcript
def test_large_transcript_performance():
    # 10,000 word transcript should complete in <30s
    pass
```

---

## Configuration

### Environment Variables (Optional)

```bash
# Topic modeling configuration
TOPIC_MODEL_NUM_TOPICS=5        # Default number of topics
TOPIC_MODEL_PASSES=10           # LDA training passes
TOPIC_MODEL_MIN_COHERENCE=0.4   # Minimum coherence threshold

# Keyword extraction
TFIDF_MAX_FEATURES=100          # Maximum keywords to extract
TFIDF_MIN_DF=2                  # Minimum document frequency
TFIDF_MAX_DF=0.8                # Maximum document frequency (filter common terms)
```

---

## Success Metrics

### Quantitative
- [ ] TF-IDF implementation matches scikit-learn within 1% error
- [ ] Topic coherence score >0.4 for 80%+ of extracted topics
- [ ] Test coverage >85% for new code
- [ ] Performance: <30s for 10,000-word transcript
- [ ] Memory: <500MB for single session analysis

### Qualitative
- [ ] Topics are interpretable and meaningful
- [ ] Inside jokes are correctly identified
- [ ] UI is intuitive and responsive
- [ ] Documentation is clear and comprehensive

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Topic quality varies by session length | MEDIUM | HIGH | Require minimum word count (500 words) |
| Dutch language nuances affect topic modeling | MEDIUM | MEDIUM | Use comprehensive Dutch stop words, test with real data |
| gensim dependency size | LOW | LOW | Make gensim optional, fallback to sklearn |
| Performance issues with large corpora | MEDIUM | LOW | Implement batching, add progress tracking |
| UI becomes cluttered with too much info | LOW | MEDIUM | Use progressive disclosure (accordions) |

---

## Implementation Notes & Reasoning

### Design Decisions

#### 1. Why TF-IDF over simple frequency?
**Decision**: Use TF-IDF (Term Frequency-Inverse Document Frequency) scoring
**Reasoning**: TF-IDF identifies terms that are important within a document but not common across all documents. This is crucial for OOC analysis because:
- Filters out session-specific common words
- Highlights unique discussion topics
- Enables better cross-session comparison
**Alternatives Considered**:
- Simple frequency counting (current) - too noisy
- BM25 - more complex, minimal benefit for our use case

#### 2. Why gensim for LDA?
**Decision**: Use gensim for topic modeling
**Reasoning**:
- More memory-efficient than sklearn for LDA
- Better suited for large text corpora
- Provides topic coherence metrics out-of-the-box
- Active community and good documentation
**Alternatives Considered**:
- sklearn LDA - higher memory usage
- Custom LDA implementation - unnecessary complexity

#### 3. Inside Joke Detection Strategy
**Decision**: Use uniqueness + frequency heuristic
**Reasoning**:
- Inside jokes are typically:
  - Unique to the group (low document frequency across all sessions)
  - Repeated frequently within sessions (high term frequency)
- TF-IDF naturally captures this pattern
**Algorithm**:
1. Extract terms with high TF-IDF in single session
2. Filter terms that appear in <20% of all sessions
3. Rank by frequency within session

#### 4. Multi-Session Architecture
**Decision**: Separate `MultiSessionAnalyzer` class
**Reasoning**:
- Single responsibility principle
- OOCAnalyzer focuses on single-session analysis
- MultiSessionAnalyzer handles aggregation and comparison
- Easier to test and maintain
- Optional feature - doesn't complicate single-session use case

---

## Dependencies and Prerequisites

### Python Package Dependencies
```bash
pip install scikit-learn>=1.3.0
pip install nltk>=3.8
pip install gensim>=4.3.0
pip install wordcloud>=1.9.0  # Already present
pip install matplotlib>=3.7.0  # Already present
```

### NLTK Data
```python
# Download required NLTK data
import nltk
nltk.download('stopwords')
nltk.download('punkt')
nltk.download('wordnet')
```

### File Requirements
- OOC transcripts must exist: `output/<session_id>_ooc_only.txt`
- Minimum word count: 100 words (warn if below 500)
- UTF-8 encoding

---

## Rollout Plan

### Phase 1: Core Feature (Week 1)
1. Implement TF-IDF keyword extraction
2. Add basic topic modeling
3. Update UI to display results
4. Write core tests
5. **Validation**: Test with 3 real sessions, verify topics make sense

### Phase 2: Enhancement (Week 2)
1. Add multi-session analysis
2. Implement insight generation
3. Add comparative visualizations
4. Complete test coverage
5. **Validation**: Test with full campaign (10+ sessions)

### Phase 3: Polish (Week 3)
1. Performance optimization
2. Documentation completion
3. User feedback incorporation
4. Critical review and fixes
5. **Validation**: External user testing

---

## Code Review Findings

**Status**: To be completed after implementation

### Issues Identified
<!-- To be filled during critical review -->

### Positive Findings
<!-- To be filled during critical review -->

### Recommendations
<!-- To be filled during critical review -->

### Merge Recommendation
<!-- [ ] Approved / [ ] Issues Found / [ ] Revisions Requested -->

---

## Changelog

### 2025-11-18 15:00 UTC
- Created implementation plan
- Defined architecture and data structures
- Outlined 5-phase implementation approach
- Identified dependencies and risks

---

## Open Questions

1. **Q**: Should we support languages other than Dutch?
   **A**: Start with Dutch + English, make language configurable

2. **Q**: How to handle very short transcripts (<100 words)?
   **A**: Show warning, suggest combining sessions, disable topic modeling

3. **Q**: Should topic modeling be optional (for performance)?
   **A**: Yes, add configuration toggle, default to enabled

4. **Q**: How many topics should we extract by default?
   **A**: Auto-detect based on transcript length (3-10 topics), allow manual override

---

## References

- [TF-IDF Explanation](https://en.wikipedia.org/wiki/Tf%E2%80%93idf)
- [Gensim LDA Tutorial](https://radimrehurek.com/gensim/models/ldamodel.html)
- [Topic Coherence Metrics](https://rare-technologies.com/what-is-topic-coherence/)
- [NLTK Dutch Resources](https://www.nltk.org/)

---

**Next Steps**: Begin Phase 1 - Core Analytics Enhancement
