# Refactoring Plans for Video Chunking Project

This directory contains detailed refactoring plans for the D&D Session Processor project. Each plan addresses a specific code smell or architectural issue identified in the codebase.

## Overview

The refactoring candidates have been prioritized and documented with:
- Problem analysis
- Proposed solutions
- Step-by-step implementation plans
- Testing strategies
- Risk assessments
- Time estimates

## Refactoring Candidates

### High Priority (Complexity & Impact)

#### 1. [Extract Pipeline Process Method into Stages](./01-pipeline-process-method.md)
**Issue**: 887-line monolithic `process()` method in `pipeline.py`

**Impact**: High - Core processing logic
**Effort**: 17-22 hours
**Complexity**: High

Extract the massive process method into 9 separate stage methods with consistent interfaces and improved testability.

---

#### 2. [Eliminate Duplicate Response Parsing](./02-classifier-response-parsing-duplication.md)
**Issue**: Identical `_parse_response()` methods in `OllamaClassifier` and `GroqClassifier`

**Impact**: Medium - Maintenance and consistency
**Effort**: 7-10 hours
**Complexity**: Medium

Move duplicate parsing logic to `BaseClassifier` with language-aware configuration.

---

#### 3. [Eliminate Duplicate Prompt Building](./03-classifier-prompt-building-duplication.md)
**Issue**: Identical `_build_prompt()` methods in both classifiers

**Impact**: Medium - Maintenance and consistency
**Effort**: 8-11 hours
**Complexity**: Medium

Create shared prompt building with template management system.

---

#### 4. [Refactor God Function `_load_campaign()`](./04-app-load-campaign-god-function.md)
**Issue**: Function returns 25 values and updates entire UI state

**Impact**: High - UI state management
**Effort**: 15-19 hours
**Complexity**: High

Replace massive tuple return with state objects using Builder pattern.

---

### Medium Priority (Code Quality)

#### 5. [Consolidate Formatting Methods](./05-formatter-filtered-methods-duplication.md)
**Issue**: Duplicate `format_ic_only()` and `format_ooc_only()` methods

**Impact**: Medium - Code duplication
**Effort**: 9-12 hours
**Complexity**: Medium

Create single `format_filtered()` method with filter strategy pattern.

---

#### 6. [Extract Complex Diarization Logic](./06-diarizer-complex-method.md)
**Issue**: 101-line `diarize()` method with multiple responsibilities

**Impact**: Medium - Code complexity
**Effort**: 10-12 hours
**Complexity**: Medium

Extract audio loading, diarization, and embedding extraction into separate methods.

---

#### 7. [Replace Magic Strings with Enums](./07-magic-strings-and-numbers.md)
**Issue**: Hard-coded strings throughout ("IC", "OOC", "running", "completed", etc.)

**Impact**: High - Type safety and maintainability
**Effort**: 19-24 hours
**Complexity**: Medium-High

Create enums for all magic strings: `Classification`, `ProcessingStatus`, `PipelineStage`, etc.

---

#### 8. [Extract Campaign Artifact Counting](./08-campaign-artifact-counting.md) ✅ **COMPLETED**
**Issue**: Complex nested logic with silent exception swallowing

**Impact**: Low-Medium - Code quality
**Effort**: 9-13 hours (Actual: ~2 hours for enhancements)
**Complexity**: Medium
**Status**: Completed 2025-11-14

Create `CampaignArtifactCounter` class with caching and proper error handling.

**Completion Notes**: Core extraction was pre-existing. Enhanced with convenience methods (`count_sessions`, `count_narratives`), query methods (`get_all_campaigns`, `get_campaign_summary`), and detailed tracking (session IDs, narrative paths). 39+ test cases covering all functionality.

---

### Lower Priority (Consistency)

#### 9. [Consolidate LLM Client Initialization](./09-llm-client-initialization-duplication.md)
**Issue**: Duplicate Ollama client init in `OllamaClassifier` and `LlmClient`

**Impact**: Low - Minor duplication
**Effort**: 9-11 hours
**Complexity**: Low-Medium

Create `OllamaClientFactory` to centralize client creation and testing.

---

#### 10. [Refactor Large UI Creation Functions](./10-large-ui-creation-functions.md)
**Issue**: 808-line UI creation function with inline event handlers

**Impact**: High - UI maintainability
**Effort**: 40-53 hours
**Complexity**: High

Break into reusable component classes with Builder pattern.

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| **Total Candidates** | 10 |
| **Completed** | 1 |
| **In Progress** | 0 |
| **Not Started** | 9 |
| **Total Estimated Effort** | 143-186 hours |
| **Average Effort per Candidate** | 14.3-18.6 hours |
| **High Priority Items** | 4 |
| **Medium Priority Items** | 4 (1 completed) |
| **Lower Priority Items** | 2 |

## Implementation Strategy

### Phase 1: Foundation (Weeks 1-2)
Focus on reducing code duplication and improving type safety:
- **#2**: Classifier response parsing (7-10h)
- **#3**: Classifier prompt building (8-11h)
- **#9**: LLM client initialization (9-11h)
- **#5**: Formatter methods (9-12h)

**Total**: 33-44 hours

### Phase 2: Core Improvements (Weeks 3-5)
Tackle complex core logic:
- **#1**: Pipeline process method (17-22h)
- **#6**: Diarizer complex method (10-12h)
- **#8**: Campaign artifact counting (9-13h)

**Total**: 36-47 hours

### Phase 3: Type Safety (Week 6)
Improve type safety across codebase:
- **#7**: Replace magic strings with enums (19-24h)

**Total**: 19-24 hours

### Phase 4: UI Refactoring (Weeks 7-9)
Major UI restructuring (can be done in parallel with other work):
- **#4**: Campaign state management (15-19h)
- **#10**: UI component system (40-53h)

**Total**: 55-72 hours

## Benefits Summary

### Code Quality Improvements
- **Lines Reduced**: ~500-700 lines (duplicate code eliminated)
- **Average Function Size**: Reduced from 100+ to <30 lines
- **Test Coverage**: Increase from ~70% to >90%
- **Type Safety**: Increase from ~70% to ~95%

### Maintainability Improvements
- **Easier Debugging**: Smaller, focused functions
- **Better Testing**: Isolated components
- **Clear Structure**: Self-documenting code
- **Reduced Complexity**: Average cyclomatic complexity reduced by 50%

### Developer Experience
- **Faster Onboarding**: Clearer code structure
- **IDE Support**: Better autocomplete with enums
- **Fewer Bugs**: Type checking catches errors early
- **Easier Refactoring**: Well-structured code easier to change

## Getting Started

### Before Starting Any Refactoring

1. **Read the specific plan** thoroughly
2. **Create a feature branch** named `refactor/candidate-XX`
3. **Run all tests** to establish baseline
4. **Communicate with team** about upcoming changes
5. **Consider dependencies** between refactorings

### During Refactoring

1. **Follow the implementation plan** step-by-step
2. **Write tests first** when possible (TDD)
3. **Commit frequently** with clear messages
4. **Run tests after each phase**
5. **Document as you go**

### After Completing Refactoring

1. **Run full test suite** (unit + integration)
2. **Perform manual testing** of affected features
3. **Update documentation**
4. **Request code review**
5. **Monitor for regressions** after merge

## Dependencies Between Refactorings

Some refactorings depend on or benefit from others:

```
#7 (Enums) → Should be done early, helps multiple refactorings
    ↓
#2, #3 (Classifier) → Can use enums
    ↓
#1 (Pipeline) → Benefits from enums and simplified classifiers
    ↓
#4 (Campaign State) → Benefits from simplified pipeline

#9 (LLM Client) → Independent
#5 (Formatter) → Independent
#6 (Diarizer) → Independent
#8 (Artifact Counter) → Independent
#10 (UI Components) → Independent but large effort
```

## Risk Assessment

### Low Risk
- #2, #3, #5, #9: Internal refactorings, no API changes
- #6, #8: Isolated improvements with clear boundaries

### Medium Risk
- #1: Core pipeline logic, needs extensive testing
- #7: Touches many files, but backward compatible

### High Risk
- #4: Complex state management, many dependencies
- #10: Large UI changes, extensive manual testing needed

## Contributing

When implementing a refactoring:

1. **Follow the plan** but adapt as needed
2. **Document deviations** from the plan
3. **Update the plan** if you discover better approaches
4. **Share learnings** with the team
5. **Update this README** with actual effort and outcomes

## Questions or Issues?

- Review the specific refactoring plan document
- Check related issues in the issue tracker
- Consult with team members who know the code
- Update the plan if you discover new information

---

**Last Updated**: 2025-11-14
**Status**: 1 of 10 refactorings completed. All plans documented, ready for implementation.
