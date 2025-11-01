# Testing Guide

## Running Tests

### Quick Test Run

Run all history trimming tests:

```bash
python test_history_trimming.py
```

Verbose output:

```bash
python test_history_trimming.py -v
```

### Performance Benchmarks

Run performance benchmarks to see improvements:

```bash
python benchmark_history.py
```

This will show:
- HTML stripping performance
- Message normalization speed
- Context preparation with caching
- Estimated token savings

## Test Coverage

The test suite includes 18 tests covering:

### 1. HTML Stripping (4 tests)
- `test_strip_html_tags` - Basic tag removal
- `test_strip_html_entities` - HTML entity decoding
- `test_normalize_whitespace` - Whitespace normalization
- `test_complex_html` - Complex nested HTML

### 2. Message Normalization (6 tests)
- `test_empty_message` - Empty payload handling
- `test_query_only` - Single query without history
- `test_history_capping` - History length enforcement
- `test_custom_history_cap` - Custom cap parameter
- `test_html_stripping_in_messages` - HTML removal in context
- `test_alternating_roles` - Correct role assignment

### 3. Agent Summarization (6 tests)
- `test_no_history_context` - First message handling
- `test_summarization_triggered` - Summary generation
- `test_summarization_disabled` - Raw history mode
- `test_summary_caching` - Cache hit verification
- `test_history_capping_in_result` - Output history size
- `test_message_cache_enabled` - Message cache functionality

### 4. End-to-End (2 tests)
- `test_large_telex_payload` - Large payload processing
- `test_process_with_trimmed_history` - Complete pipeline

## Test Environment Setup

Tests automatically handle missing API keys by using a test fallback. No additional setup required beyond:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests
python test_history_trimming.py
```

## Expected Test Output

```
....................
----------------------------------------------------------------------
Ran 18 tests in 0.094s

OK
```

Note: You may see "Summarization error" messages for tests that attempt to call Gemini without a valid API key. This is expected and handled gracefully - the tests still pass.

## Writing New Tests

### Testing Utils Functions

```python
from utils import normalize_telex_message, strip_html_and_whitespace

def test_my_feature():
    # Create test payload
    raw_message = {
        'parts': [
            {'kind': 'text', 'text': '<p>Test</p>'}
        ]
    }
    
    # Test normalization
    result = normalize_telex_message(raw_message)
    
    # Assert expectations
    assert len(result) <= HISTORY_CAP_MESSAGES
    assert '<p>' not in result[0].parts[0].text
```

### Testing Agent Methods

```python
from unittest.mock import patch
from agents.agent import StudlyAgent

def test_agent_feature():
    agent = StudlyAgent()
    
    # Mock LLM calls to avoid API calls
    with patch.object(agent, '_generate_study_plan', return_value="Test plan"):
        result = agent.process_messages(messages, context_id="test", task_id="test")
        
    # Assert expectations
    assert result.status.state == "completed"
```

### Important Mocking Notes

- Mock methods using `patch.object()`, not direct attribute assignment
- LangChain's RunnableSequence doesn't allow `invoke` attribute modification
- Always mock at the method level (e.g., `_generate_study_plan`, `_generate_summary`)

## CI/CD Integration

To integrate tests into your CI pipeline:

```yaml
# Example GitHub Actions
- name: Run Tests
  run: |
    source .venv/bin/activate
    python test_history_trimming.py
    
- name: Run Benchmarks
  run: |
    source .venv/bin/activate
    python benchmark_history.py
```

## Debugging Test Failures

### Common Issues

1. **Import Errors**
   - Ensure virtual environment is activated
   - Check all dependencies are installed: `uv sync`

2. **API Key Errors**
   - Expected in tests without `.env` file
   - Tests handle this gracefully with fallback values

3. **Mock-related Failures**
   - Use `patch.object()` for method mocking
   - Don't try to assign to chain.invoke directly

4. **Assertion Failures**
   - Check HISTORY_CAP_MESSAGES value in config.py
   - Verify test data matches expected format

### Debug Mode

Add debug output to tests:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use print statements
print(f"Debug: messages={len(messages)}, cap={HISTORY_CAP_MESSAGES}")
```

## Performance Testing

### Baseline Benchmarks

Current performance targets:
- HTML stripping: <0.02ms per message
- Normalization: <1ms per request
- Context prep (cached): <0.1ms
- Token reduction: >70%

### Running Performance Tests

```bash
# Quick benchmark
python benchmark_history.py

# Custom tests
python -c "
from utils import normalize_telex_message
import time

# Create large payload
payload = {'parts': [{'kind': 'data', 'data': [{'kind': 'text', 'text': f'msg {i}'} for i in range(100)]}]}

# Measure
start = time.perf_counter()
result = normalize_telex_message(payload)
elapsed = time.perf_counter() - start

print(f'Time: {elapsed*1000:.2f}ms, Messages: {len(result)}')
"
```

## Continuous Monitoring

Recommended metrics to track:
- Test execution time (should stay <1s)
- Cache hit rate in tests (verify caching works)
- Memory usage during large payload tests
- Token estimation accuracy

## Test Data

Test fixtures are inline in test file. To add new fixtures:

```python
# In test_history_trimming.py
class TestMyFeature(unittest.TestCase):
    def setUp(self):
        """Create reusable test data."""
        self.large_payload = create_large_telex_payload(100)
        
    def test_feature(self):
        result = normalize_telex_message(self.large_payload)
        self.assertLessEqual(len(result), HISTORY_CAP_MESSAGES)
```

## Known Limitations

1. Tests mock LLM calls - don't validate actual Gemini responses
2. Token estimation is approximate (chars ÷ 4)
3. Benchmark timing may vary based on system load
4. No integration tests with real Telex endpoints

For production validation, test with actual Telex payloads in a staging environment.
