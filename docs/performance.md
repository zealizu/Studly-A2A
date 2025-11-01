# Performance Tracing and Profiling

This document describes how to enable performance tracing and run profiling tests for the `/tasks/send` endpoint.

## Overview

The application includes built-in performance instrumentation to capture precise timing data for each stage of the request handling flow. This helps identify bottlenecks and optimize the most critical paths.

## Enabling Performance Tracing

Performance tracing is controlled by the `A2A_TRACE_LATENCY` environment variable. When enabled, the application will emit structured JSON logs containing detailed timing information for each request.

### Setting the Environment Variable

```bash
# Enable tracing (any of these values work)
export A2A_TRACE_LATENCY=true
export A2A_TRACE_LATENCY=1
export A2A_TRACE_LATENCY=yes

# Disable tracing (default)
export A2A_TRACE_LATENCY=false
unset A2A_TRACE_LATENCY
```

### Starting the Server with Tracing Enabled

```bash
# Development server
A2A_TRACE_LATENCY=true python app.py

# Production server with Gunicorn
A2A_TRACE_LATENCY=true gunicorn app:app
```

## Performance Metrics Collected

When tracing is enabled, the following metrics are captured for each `/tasks/send` request:

### Request-Level Metrics (logged by Flask app)

- **json_parsing**: Time spent parsing the incoming JSON request body
- **message_normalization**: Time spent normalizing Telex message format
- **agent_processing**: Total time spent in agent processing (see breakdown below)
- **response_serialization**: Time spent serializing the response to JSON
- **total**: Total request handling time (wall clock)

### Agent-Level Metrics (logged by StudlyAgent)

- **text_extraction**: Time spent extracting text from message parts
- **context_lookup**: Time spent retrieving conversation history from cache
- **llm_invocation**: Time spent calling the LLM (Gemini API)
- **response_building**: Time spent constructing response objects

## Log Format

Trace logs are emitted as structured JSON for easy parsing and analysis:

```json
{
  "event": "tasks_send_latency",
  "request_id": "req-123",
  "method": "message/send",
  "timings_ms": {
    "json_parsing": 0.42,
    "message_normalization": 1.23,
    "agent_processing": 1234.56,
    "response_serialization": 2.15,
    "total": 1238.36
  }
}
```

Agent-level details are logged separately:

```json
{
  "event": "agent_processing_detail",
  "task_id": "task-456",
  "context_id": "context-789",
  "timings_ms": {
    "text_extraction": 0.05,
    "context_lookup": 0.12,
    "llm_invocation": 1230.45,
    "response_building": 3.94
  }
}
```

## Running the Profiling Script

The `scripts/profile_tasks_send.py` script automates load testing and latency analysis.

### Basic Usage

```bash
# Profile against local server (default: 10 requests)
python scripts/profile_tasks_send.py

# Specify number of requests
python scripts/profile_tasks_send.py --requests 50

# Profile against different server
python scripts/profile_tasks_send.py --url https://your-server.com

# Save results to file
python scripts/profile_tasks_send.py --output results.json
```

### Example Output

```
🚀 Starting profiling against http://localhost:5000
📊 Running 10 requests...

Request 1/10... ✓ 1245.32ms
Request 2/10... ✓ 1198.45ms
Request 3/10... ✓ 1287.91ms
...

============================================================
📈 PROFILING RESULTS
============================================================
Total Requests:       10
Successful:           10
Failed:               0

Latency Statistics (ms):
  Mean:               1234.56
  Median:             1225.00
  Min:                1150.23
  Max:                1350.89
  Std Dev:            45.67
  P95:                1320.45
  P99:                1345.12
============================================================
```

### Profiling Workflow

1. Start your server in one terminal:
   ```bash
   A2A_TRACE_LATENCY=true python app.py
   ```

2. Run the profiling script in another terminal:
   ```bash
   python scripts/profile_tasks_send.py --requests 20
   ```

3. Review the server logs for detailed per-stage timings

4. Analyze the profiling output for aggregate statistics

## Interpreting Results

### Common Bottlenecks

Based on the metrics collected, here are typical bottlenecks to look for:

1. **High `llm_invocation` time** (usually 80-95% of total)
   - This is expected as LLM API calls are network-bound
   - Consider caching responses for common queries
   - Look into streaming responses if supported

2. **High `message_normalization` time**
   - May indicate complex message structures
   - Consider optimizing the `normalize_telex_message` function

3. **High `context_lookup` time**
   - May indicate large context caches
   - Consider implementing cache size limits or TTL

4. **High `response_serialization` time**
   - May indicate very large responses
   - Consider response size limits or pagination

### Performance Goals

Target latency goals (excluding LLM invocation):
- JSON parsing: < 1ms
- Message normalization: < 5ms
- Context lookup: < 1ms
- Response serialization: < 10ms

LLM invocation time is variable and depends on:
- Model choice (gemini-2.5-flash vs others)
- Response length
- API latency
- Network conditions

Typical LLM invocation times: 500ms - 3000ms

## Analyzing Trace Logs

### Filtering Trace Logs

If using structured logging with tools like `jq`:

```bash
# Extract only latency events
cat app.log | grep 'tasks_send_latency' | jq .

# Calculate average total time
cat app.log | grep 'tasks_send_latency' | jq '.timings_ms.total' | awk '{sum+=$1; count++} END {print sum/count}'

# Find slowest requests
cat app.log | grep 'tasks_send_latency' | jq '.timings_ms.total' | sort -n | tail -10
```

### Correlating Request and Agent Logs

Match logs by task_id to see the full picture:

```bash
# Extract logs for a specific task
cat app.log | grep 'task-456'
```

## Production Considerations

### When to Enable Tracing

- ✅ **Enable** during:
  - Performance testing and optimization
  - Investigating latency issues
  - Capacity planning exercises
  - Development and staging environments

- ❌ **Disable** during:
  - Normal production operation (unless investigating issues)
  - High-traffic periods (adds logging overhead)

### Performance Impact

Enabling tracing has minimal overhead:
- `time.perf_counter()` calls: ~100 nanoseconds each
- JSON logging: ~1-2ms per request
- Total overhead: < 0.1% of request time

However, increased log volume may impact:
- Disk I/O
- Log aggregation systems
- Log storage costs

### Best Practices

1. **Use log sampling** in high-traffic production:
   ```python
   # Only trace 1% of requests
   if random.random() < 0.01:
       TRACE_LATENCY = True
   ```

2. **Monitor log volume** when enabling tracing

3. **Set up alerts** for P95/P99 latency thresholds

4. **Archive or rotate logs** frequently to manage storage

## Troubleshooting

### Tracing Not Working

1. Verify environment variable is set:
   ```bash
   echo $A2A_TRACE_LATENCY
   ```

2. Check if server picked up the variable:
   ```python
   # In Python console
   import os
   print(os.environ.get('A2A_TRACE_LATENCY'))
   ```

3. Restart the server after setting environment variables

### Profiling Script Fails

1. Ensure server is running:
   ```bash
   curl http://localhost:5000
   ```

2. Check if `/tasks/send` endpoint is accessible:
   ```bash
   curl -X POST http://localhost:5000/tasks/send \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":"test","method":"message/send","params":{}}'
   ```

3. Verify you have the `requests` library installed:
   ```bash
   pip install requests
   ```

## Future Enhancements

Potential improvements to the tracing system:

- [ ] OpenTelemetry integration for distributed tracing
- [ ] Prometheus metrics export
- [ ] Automatic percentile calculation in logs
- [ ] Request sampling for production use
- [ ] Integration with APM tools (DataDog, New Relic, etc.)
- [ ] Flame graphs for detailed profiling
- [ ] Database query timing (if added in future)
