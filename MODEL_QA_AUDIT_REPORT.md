# Model QA Report - Dutch Workbook Project

## Executive Summary
**Model**: Dutch Vocabulary Word Generation System (LLM-based) + Spaced Repetition Algorithm  
**Type**: LLM Prompt-Based Generation + Heuristic Scheduling Algorithm  
**Algorithm**: External LLM (OpenCode/OpenRouter) + Spaced Repetition (SM-2 variant)  
**QA Type**: Initial Review  
**Overall Opinion**: **Sound with Findings** ⚠️

### Key Observations
The Dutch Workbook project is a Django-based language learning application that uses:
1. **LLM-based word generation** via OpenCode CLI or OpenRouter API to generate Dutch vocabulary
2. **Spaced repetition algorithm** (box-based, similar to SM-2) for flashcard scheduling

This is **not a traditional ML project** with trained models, but rather a system that:
- Calls external LLMs via prompting (no fine-tuning)
- Uses heuristic algorithms for learning scheduling

**Critical Gap**: The system lacks validation, monitoring, and versioning that would be standard for any AI-powered feature.

---

## Findings Summary

| # | Finding | Severity | Domain | Remediation | Deadline |
|---|---------|----------|--------|-------------|----------|
| 1 | No validation of AI-generated content quality | **High** | Data Quality | Add validation layer | 30 days |
| 2 | Non-deterministic generation, no versioning | **High** | Governance | Implement prompt/model versioning | 30 days |
| 3 | Spaced Repetition algorithm not using stored ease factor | **Medium** | Model Construction | Fix interval calculation logic | 45 days |
| 4 | No monitoring of AI generation metrics | **Medium** | Performance Monitoring | Add logging & dashboards | 60 days |
| 5 | Hardcoded CEFR level prompts not validated | **Medium** | Calibration | Add level-appropriate validation | 45 days |
| 6 | No fallback strategy for LLM failures | **Medium** | Model Robustness | Implement fallback chain | 30 days |
| 7 | Flashcard box intervals not personalized | **Low** | Model Performance | Track retention metrics | 90 days |
| 8 | Missing integration tests for AI service | **Low** | Testing | Add sandbox integration tests | 60 days |
| 9 | No A/B testing framework for prompts | **Low** | Experimentation | Add feature flag system | 90 days |
| 10 | User progress tracking uses naive averaging | **Low** | Data Quality | Use proper time-series aggregation | 45 days |

---

## Detailed Analysis

### 1. Documentation & Governance - **PARTIAL FAIL** ❌

#### What Exists:
- Basic README (assumed, not reviewed)
- Code comments in Python files
- Test files with docstrings

#### What's Missing:
- **No model card** for the LLM-based word generation system
- **No prompt versioning** - prompts are embedded in code (`word_generation.py` lines 104-127)
- **No model inventory** - which LLM models are used, when they were last updated
- **No approval workflow** for prompt changes or model selection
- **No documentation** of the spaced repetition algorithm parameters

#### Evidence:
```python
# From words/services/word_generation.py lines 104-127
def _build_prompt(self, request: WordGenerationRequest) -> str:
    """Build the prompt for AI word generation."""
    source_name = SOURCE_LANGUAGE_MAP.get(request.source, "English")
    theme_str = f"Theme: {request.theme}\n" if request.theme else ""

    return f"""Generate {request.count} Dutch vocabulary words at CEFR level {request.level}.
{theme_str}Translate to {source_name}.
...
```

**Finding**: Prompts are hardcoded strings with no version tracking. If the prompt changes, there's no way to reproduce previous generations.

#### Recommendation:
Create a `MODEL_CARD.md` documenting:
- System architecture (LLM → parsing → database)
- Prompt template versions with changelog
- Model options and selection criteria
- Known limitations and failure modes

---

### 2. Data Reconstruction & Quality - **PARTIAL FAIL** ❌

#### AI-Generated Word Data Quality:

**Current State** (from `words/models.py`):
- Words stored with: `dutch`, `translation`, `source`, `part_of_speech`, `context`, `example`
- Basic duplicate detection via `UniqueConstraint(fields=["dutch", "translation", "source"])`

**Critical Gaps**:
1. **No validation that generated Dutch words are grammatically correct**
2. **No validation that examples are actually correct Dutch sentences**
3. **No verification that CEFR level claims are accurate** (an "A1" word might actually be B2)
4. **No detection of LLM hallucinations** (non-existent Dutch words)

#### Evidence:
From `word_generation.py` lines 129-149, the `_parse_response` method only checks JSON structure:
```python
def _parse_response(self, response: str) -> list[dict]:
    """Parse JSON response from AI."""
    response_clean = self._clean_response(response)
    
    json_match = re.search(r"\[.*\]", response_clean, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            if isinstance(data, list):
                return data  # ← Only validates JSON structure!
        except json.JSONDecodeError:
            pass
    return []
```

**No semantic validation** of the generated content.

#### Recommendation:
Implement a validation layer:
```python
def validate_generated_word(word: GeneratedWord, level: str) -> ValidationResult:
    """Validate AI-generated word quality."""
    issues = []
    
    # Check Dutch article agreement (de/het with nouns)
    if word.part_of_speech == "noun":
        if not word.dutch.startswith(("de ", "het ")):
            issues.append("Missing article for noun")
    
    # Validate CEFR level (optional: use a separate LLM call or rules)
    # Check example sentence ends with period
    if word.example and not word.example.endswith((".", "!", "?")):
        issues.append("Example sentence missing terminal punctuation")
    
    return ValidationResult(is_valid=len(issues) == 0, issues=issues)
```

---

### 3. Target / Label Analysis - **N/A** ⚪

This is not a supervised learning system, so there are no "labels" in the traditional sense.

However, the **CEFR level is treated as a target**:
- Prompt specifies: "Generate Dutch vocabulary words at CEFR level {level}"
- **No validation** that the generated words actually match the requested level
- **Risk**: LLMs may not accurately calibrate vocabulary difficulty

**Severity**: Medium - Users expecting A1 words may receive B1 words, undermining learning.

---

### 4. Segmentation & Cohort Assessment - **PASS** ✅

The system implements reasonable segmentation:

1. **CEFR Levels**: A1, A2, B1, B2, C1 (from `word_generation.py` line 23)
2. **Source Languages**: English, Russian, Ukrainian (from `word_generation.py` lines 17-21)
3. **Categories**: User-defined categories via `Category` model
4. **Flashcard Boxes**: 1-5 for spaced repetition

**Assessment**: Segmentation is well-implemented and material.

---

### 5. Feature Analysis & Engineering - **N/A** ⚪

No feature engineering in the traditional ML sense. Words have attributes:
- `dutch`, `translation`, `part_of_speech`, `context`, `example`, `example_translation`

These are **raw fields** from LLM generation, not engineered features.

---

### 6. Model Replication & Construction - **FAIL** ❌

#### LLM Generation Non-Determinism:

**Issue**: LLM calls are non-deterministic by default.
- `opencode-auto` CLI: No documented seed or temperature parameters
- OpenRouter API: Default temperature used (likely 1.0 or undefined)

From `opencode.py` lines 42-45:
```python
def chat(self, prompt: str, model: Optional[str] = None, timeout: int = 120):
    cmd = [str(opencode_auto_path), "run"]
    if model:
        cmd.extend(["-m", model])
    cmd.append(prompt)
    # ← No seed, temperature, or other reproducibility parameters!
```

**Impact**: 
- Cannot reproduce exact generations
- Cannot A/B test prompt changes cleanly
- Debugging generation issues is difficult

#### Spaced Repetition Algorithm Issue:

From `views.py` lines 229-242:
```python
intervals = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}

if rating == "again":
    card.box = 1
    card.next_review = timezone.now() + timedelta(days=1)
elif rating == "hard":
    card.box = max(card.box, 2)
    card.next_review = timezone.now() + timedelta(days=intervals.get(card.box, 1))
# ...
```

**Bug**: The `ease_factor` field (line 96 in models.py) is **never used** in interval calculation!

From `models.py` line 96:
```python
ease_factor = models.FloatField(default=2.5)
```

But `ease_factor` is never read or updated in `views.py`. This is a **dead field** - the SM-2 algorithm is not fully implemented.

#### Recommendation:
1. **For LLM generation**: Document temperature settings, or add seed parameter
2. **For Spaced Repetition**: Implement proper SM-2:
```python
def calculate_next_review(card, rating):
    """Full SM-2 algorithm implementation."""
    if rating == "again":
        card.repetitions = 0
        card.ease_factor = max(1.3, card.ease_factor - 0.2)
        interval = 1
    else:
        # Update ease factor based on rating
        # Calculate interval using ease_factor and repetitions
        pass
    return timezone.now() + timedelta(days=interval)
```

---

### 7. Calibration - **FAIL** ❌

#### LLM Calibration (CEFR Level Accuracy):

**No calibration testing** has been performed:
- Are "A1" words actually A1 difficulty?
- Does the model systematically generate words that are too easy/hard?

**Recommended Test**:
```python
def test_cefr_calibration():
    """Test if generated words match claimed CEFR level."""
    # Generate 100 words at each level
    # Have Dutch native speakers or language experts rate them
    # Compare distribution of rated levels vs. requested levels
    # Compute calibration curve (requested level vs. actual level)
    pass
```

#### Spaced Repetition Calibration:

The hardcoded intervals (1, 3, 7, 14, 30) are **not calibrated** to user performance:
- No tracking of whether users actually remember words at these intervals
- No adjustment based on individual user retention rates

**Severity**: Medium - Miscalibrated intervals reduce learning efficiency.

---

### 8. Performance & Monitoring - **FAIL** ❌

#### What's Not Monitored:

1. **AI Generation Success Rate**:
   - How often does the LLM return valid JSON?
   - How often are generations empty or malformed?
   - From `word_generation.py`: Failures silently return empty lists (line 63, 149)

2. **Generation Latency**:
   - No timing logs for LLM API calls
   - OpenCode CLI has 120s timeout (`ai_settings.py` line 11) but no monitoring

3. **Cost Tracking** (if using OpenRouter):
   - No token usage tracking
   - No cost attribution per user or per generation batch

4. **Spaced Repetition Effectiveness**:
   - No tracking of card retention (do users get cards right when reviewed?)
   - No monitoring of box distribution over time
   - No measurement of learning velocity

#### Evidence of Missing Monitoring:

From `word_generation.py` lines 356-371 (view layer):
```python
try:
    service = WordGenerationService()
    used_model, generated_words = service.generate_words(request_data)
    
    if not generated_words:
        context["error"] = "Could not parse AI response. Please try again."
        return render(request, "words/generate_words.html", context)
    # ← No logging of failure rate!
```

#### Recommendation:
Add structured logging:
```python
import structlog

logger = structlog.get_logger()

def generate_words(self, request):
    with logger.bind(model=request.model, level=request.level, count=request.count):
        start = time.time()
        try:
            model, words = self.client.chat(prompt, model=request.model)
            logger.info("generation_success", word_count=len(words), 
                       latency_ms=(time.time()-start)*1000)
        except Exception as e:
            logger.error("generation_failed", error=str(e))
            raise
```

---

### 9. Interpretability & Fairness - **NOT APPLICABLE** ⚪

Not a traditional ML system, but relevant considerations:

#### LLM Bias:
- **Dutch cultural bias**: LLM may generate words more relevant to certain cultures
- **Translation bias**: Translations may carry source-language cultural assumptions
- **Gender bias**: Example sentences may use stereotypical gender roles

**Recommendation**: Document known limitations in model card. Consider auditing generated examples for biased language.

---

### 10. Business Impact & Communication - **PARTIAL FAIL** ❌

#### What's Missing:

1. **No documented success metrics**:
   - What does "good" look like for word generation?
   - User satisfaction with AI-generated words?
   - Learning outcomes (vocabulary retention)?

2. **No feedback loop**:
   - Users cannot report low-quality generations
   - No mechanism to correct or flag bad examples
   - From `models.py`: No fields for user ratings or flags

3. **No communication of limitations**:
   - Users aren't told that words are AI-generated
   - No disclaimer about potential inaccuracies

#### Evidence:

The `Word` model has no fields for:
- User rating / feedback
- Flagged for review
- Validation status
- Source model version

#### Recommendation:
Add to `Word` model:
```python
class Word(models.Model):
    # ... existing fields ...
    
    # New fields for quality tracking
    generated_by = models.CharField(max_length=100, blank=True, 
                                    help_text="Model used for generation")
    prompt_version = models.CharField(max_length=50, blank=True)
    user_rating = models.FloatField(null=True, blank=True)
    flagged = models.BooleanField(default=False)
    validation_status = models.CharField(max_length=20, default="unvalidated",
                                         choices=[("unvalidated", "Unvalidated"),
                                                  ("validated", "Validated"),
                                                  ("flagged", "Flagged")])
```

---

## Appendices

### A: Replication Scripts and Environment

**Environment** (from `pyproject.toml`):
- Python >= 3.11
- Django >= 5.0
- openai >= 1.0.0 (for OpenRouter client)
- No ML frameworks (PyTorch, scikit-learn, etc.)

**Model Dependencies**:
- External: OpenCode CLI (`opencode-auto` binary)
- External: OpenRouter API (cloud-based LLMs)

**Reproducibility Concern**: LLM outputs are non-deterministic without seed control.

---

### B: Statistical Test Outputs

**Not Applicable** - No statistical models in the traditional sense.

However, recommended tests for this system:
1. **CEFR Calibration Test**: Generate 100 words at each level, have experts rate them
2. **Spaced Repetition Retention Test**: Track what % of cards are answered correctly at each review
3. **LLM Reliability Test**: Measure JSON parsing success rate across 100 generations

---

### C: Feature Stability Analysis

**Not Applicable** - No engineered features.

For LLM generation, "feature stability" would mean:
- Do prompts consistently generate words at the requested CEFR level?
- Is the JSON structure stable across different LLM models?

---

### D: Algorithm Analysis - Spaced Repetition

**Current Implementation** (from `views.py` lines 226-248):

```python
intervals = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}

if rating == "again":
    card.box = 1
    card.next_review = timezone.now() + timedelta(days=1)
elif rating == "hard":
    card.box = max(card.box, 2)
    card.next_review = timezone.now() + timedelta(days=intervals.get(card.box, 1))
# ...
```

**Issues Identified**:
1. ❌ `ease_factor` field is never used (dead code)
2. ⚠️ "Easy" rating jumps box by 2 (line 241), which may be too aggressive
3. ⚠️ Intervals are hardcoded, not personalized
4. ⚠️ No tracking of repetition count (SM-2 uses this)

**SM-2 Reference Implementation**:
```
EF := EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
I(1) := 1
I(2) := 6
I(n) := I(n-1) * EF
```

Current implementation does not match SM-2.

---

### E: LLM Integration Analysis

**Two Integration Paths**:

1. **OpenCode CLI** (`utils/opencode.py`):
   - Calls local LLM via `opencode-auto run -m <model> <prompt>`
   - Returns JSON with `{"success": true, "output": "...", "model": "..."}`
   - **Risk**: CLI output format may change; no schema validation

2. **OpenRouter API** (`utils/openrouter.py`):
   - Uses OpenAI Python client to call OpenRouter
   - Model: Configurable, default `anthropic/claude-3.5-sonnet`
   - **Risk**: API may fail; no retry logic (line 47-50 just calls create())

**Timeout Handling** (from `opencode.py` lines 48-55):
```python
try:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,  # 120 seconds
    )
except subprocess.TimeoutExpired:
    return None, "Timeout"  # ← Just returns error string, no retry
```

**Missing**:
- No retry with exponential backoff
- No circuit breaker for API failures
- No fallback model if primary fails

---

## Priority Recommendations

### Immediate (0-30 days):

1. **Add word validation layer** - Validate AI-generated content before saving to DB
2. **Implement model/prompt versioning** - Log which model + prompt generated each word
3. **Add fallback strategy** - If primary LLM fails, try backup model
4. **Fix dead code** - Either implement `ease_factor` or remove the field

### Short-term (30-60 days):

5. **Add monitoring & logging** - Track generation success rates, latency, costs
6. **Implement user feedback** - Let users flag bad generations
7. **Add integration tests** - Test against sandbox LLM environment
8. **Fix progress tracking** - Use proper time-series for average_score

### Medium-term (60-90 days):

9. **Calibrate CEFR levels** - Validate that generated words match difficulty claims
10. **Improve spaced repetition** - Full SM-2 implementation with personalization
11. **Add A/B testing** - Experiment with different prompts and models
12. **Create model card** - Document system limitations and known issues

---

## Severity-Rated Findings Summary

### High Severity (2 findings):
- **Finding #1**: No validation of AI-generated content → Risk of bad data in DB
- **Finding #2**: Non-deterministic generation, no versioning → Cannot reproduce results

### Medium Severity (4 findings):
- **Finding #3**: Spaced repetition not using ease_factor → Algorithm not working as intended
- **Finding #4**: No monitoring of AI generation → Blind to failures and costs
- **Finding #5**: CEFR level prompts not validated → Users may get wrong difficulty
- **Finding #6**: No fallback strategy → System fragile to LLM failures

### Low Severity (4 findings):
- **Finding #7**: Flashcard intervals not personalized → Suboptimal learning
- **Finding #8**: Missing integration tests → Deployment risk
- **Finding #9**: No A/B testing → Cannot optimize prompts
- **Finding #10**: Naive progress averaging → Mathematical inaccuracy

---

## Conclusion

The Dutch Workbook project demonstrates **good software engineering practices** (Django best practices, tests, etc.) but **lacks ML/AI-specific quality assurance**. 

The AI-powered word generation feature is essentially a **prompt → LLM → JSON parse → DB** pipeline with:
- ❌ No output validation
- ❌ No quality monitoring  
- ❌ No versioning or reproducibility
- ❌ No fallback mechanisms

The Spaced Repetition algorithm has a **bug** (ease_factor not used) and is **not calibrated** to user performance.

**Overall Assessment**: The system is **functional but not robust**. It works in ideal conditions but lacks the safeguards, monitoring, and validation needed for a production AI-powered feature.

**Recommended Action**: Address High and Medium severity findings before scaling up AI generation usage.

---

**QA Analyst**: Model QA Specialist (big-pickle)  
**QA Date**: April 28, 2026  
**Next Scheduled Review**: After remediation of High severity findings (est. 30-60 days)

---

## Audit Methodology Notes

This audit was conducted by:
1. **Code review** of all Python files in the project (excluding .venv)
2. **Architecture analysis** of LLM integration points
3. **Algorithm review** of spaced repetition implementation
4. **Gap analysis** against ML/AI QA best practices

**Limitations of this audit**:
- No access to production data or logs
- No ability to test LLM generation quality empirically
- No user feedback data analyzed
- Static code analysis only (no runtime testing)

A **Phase 2 audit** should include:
- Runtime testing of LLM generation quality
- Analysis of production monitoring data
- User satisfaction surveys on AI-generated content
- A/B test results for prompt optimization
