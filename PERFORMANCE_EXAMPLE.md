# Performance Tracing - Quick Start Example

This is a quick reference guide showing how to use the performance tracing features.

## Quick Test

### Step 1: Start server with tracing enabled

Terminal 1:
```bash
cd /home/engine/project
export A2A_TRACE_LATENCY=true
python app.py
```

Expected output will include your normal Flask startup messages.

### Step 2: Send a test request

Terminal 2:
```bash
curl -X POST http://localhost:5000/tasks/send \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-001",
    "method": "message/send",
    "params": {
      "message": {
        "kind": "message",
        "role": "user",
        "messageId": "msg-001",
        "parts": [
          {
            "kind": "text",
            "text": "Create a study plan for learning Python in 2 weeks"
          }
        ]
      },
      "configuration": {
        "blocking": true,
        "acceptedOutputModes": ["text/plain"]
      }
    }
  }'
```

### Step 3: Check the logs

In Terminal 1, you should see structured JSON logs like:

```json
{
  "event": "tasks_send_latency",
  "request_id": "test-001",
  "method": "message/send",
  "timings_ms": {
    "json_parsing": 0.15,
    "message_normalization": 1.23,
    "agent_processing": 1234.56,
    "response_serialization": 2.34,
    "total": 1238.28
  }
}
```

And agent-level details:

```json
{
  "event": "agent_processing_detail",
  "task_id": "msg-001",
  "context_id": "abc-123",
  "timings_ms": {
    "text_extraction": 0.05,
    "context_lookup": 0.08,
    "llm_invocation": 1230.12,
    "response_building": 4.31
  }
}
```

## Run Profiling Script

### Basic profiling

```bash
# Make sure server is running first (see Step 1 above)
# Then in another terminal:
python scripts/profile_tasks_send.py --requests 10
```

### Save results to file

```bash
python scripts/profile_tasks_send.py --requests 20 --output profile_results.json
```

### Profile different server

```bash
python scripts/profile_tasks_send.py --url https://your-server.com --requests 5
```

## Expected Results

Typical latency breakdown (ms):
- **json_parsing**: 0.1 - 1ms (very fast)
- **message_normalization**: 1 - 5ms (depends on message complexity)
- **agent_processing**: 500 - 3000ms (dominated by LLM API call)
  - text_extraction: 0.05 - 0.5ms
  - context_lookup: 0.05 - 1ms
  - llm_invocation: 500 - 2800ms (most time here)
  - response_building: 2 - 10ms
- **response_serialization**: 1 - 10ms (depends on response size)
- **total**: 502 - 3016ms

The LLM invocation time dominates (typically 90-98% of total time).

## Disabling Tracing

Simply unset the environment variable or set it to false:

```bash
export A2A_TRACE_LATENCY=false
# or
unset A2A_TRACE_LATENCY

# Then restart the server
python app.py
```

When disabled, no performance logs are emitted, and the overhead is minimal (< 0.01%).

## Analyzing Logs

### Extract only latency logs

```bash
# Assuming logs are in stderr or a log file
python app.py 2>&1 | grep 'tasks_send_latency'
```

### Pretty print logs

```bash
python app.py 2>&1 | grep 'tasks_send_latency' | jq .
```

### Calculate average total latency

```bash
python app.py 2>&1 | grep 'tasks_send_latency' | jq '.timings_ms.total' | awk '{sum+=$1; count++} END {print "Average:", sum/count, "ms"}'
```

## Troubleshooting

### No logs appearing?

1. Check the environment variable:
   ```bash
   echo $A2A_TRACE_LATENCY
   ```
   Should output: `true`

2. Make sure you restarted the server after setting the variable

3. Check that your request actually reached `/tasks/send`

### Profiling script fails?

1. Ensure server is running:
   ```bash
   curl http://localhost:5000
   ```
   Should return: `Server is live`

2. Check network connectivity:
   ```bash
   curl -v http://localhost:5000/tasks/send
   ```

3. Verify you're using the correct URL (default is `http://localhost:5000`)

## Next Steps

For comprehensive documentation, see:
- [docs/performance.md](docs/performance.md) - Full performance documentation
- [README.md](README.md) - General project documentation

For questions or issues, check the main README or project documentation.
