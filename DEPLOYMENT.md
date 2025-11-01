# Deployment Guide - Async Gemini Pipeline

## Overview

This deployment guide covers the async-enabled version of Studly Agent with timeout handling and improved performance characteristics.

## Key Changes from Previous Version

### 1. Async Pipeline Implementation
- **Async Agent Methods**: `process_messages_async()` uses `await chain.ainvoke()` for non-blocking LLM calls
- **Concurrency Protection**: `asyncio.Lock` protects shared `study_contexts` dictionary
- **Timeout Handling**: 6s hard timeout with `asyncio.wait_for()` at endpoint level
- **ASGI Server**: Hypercorn replaces Gunicorn for true async execution

### 2. Error Handling
- Timeouts return HTTP 408 with JSON-RPC error code -32000
- Graceful error messages for timeout scenarios
- Maintains JSON-RPC 2.0 compliance for all error cases

### 3. Performance Targets
- **Latency**: <5s average for typical study plan requests
- **Timeout**: 6s hard limit (5s LLM timeout + 1s overhead)
- **Concurrency**: Thread-safe with asyncio locks

## Server Requirements

### ASGI vs WSGI

**Recommended: ASGI (Hypercorn)**
```bash
hypercorn app:app --bind 0.0.0.0:$PORT
```
- True async execution
- Native support for Flask 3.x async routes
- Better concurrency handling

**Alternative: WSGI (Gunicorn)**
```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```
- Falls back to thread pool for async routes
- Lower performance but still functional
- Use if ASGI deployment is not available

## Environment Variables

Required:
- `GEMINI_API_KEY`: Your Google Gemini API key
- `PORT`: Server port (default: 5000)

Optional:
- Configure `LLM_TIMEOUT` in `app.py` (default: 6.0s)
- Configure LLM parameters in `agents/agent.py`:
  - `timeout`: Per-request timeout (default: 5.0s)
  - `max_retries`: Retry count (default: 3)
  - `temperature`: LLM temperature (default: 0.3)

## Deployment Steps

### 1. Heroku/Railway/Render

These platforms automatically use the `Procfile`:
```
web: hypercorn app:app --bind 0.0.0.0:$PORT
```

Steps:
1. Set `GEMINI_API_KEY` environment variable
2. Deploy from git repository
3. Platform will automatically install dependencies and start server

### 2. Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

COPY . .

EXPOSE 5000

CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:5000"]
```

Build and run:
```bash
docker build -t studly-agent .
docker run -p 5000:5000 -e GEMINI_API_KEY=your_key studly-agent
```

### 3. Systemd Service (Linux)

Create `/etc/systemd/system/studly-agent.service`:
```ini
[Unit]
Description=Studly Agent Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/studly-agent
Environment="GEMINI_API_KEY=your_key"
ExecStart=/opt/studly-agent/.venv/bin/hypercorn app:app --bind 0.0.0.0:5000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable studly-agent
sudo systemctl start studly-agent
```

## Testing Deployment

### 1. Health Check
```bash
curl http://localhost:5000/
# Expected: "Server is live"
```

### 2. Agent Metadata
```bash
curl http://localhost:5000/.well-known/agent.json
# Expected: JSON with agent capabilities
```

### 3. Test Request
```bash
curl -X POST http://localhost:5000/tasks/send \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "execute",
    "params": {
      "messages": [
        {
          "kind": "message",
          "role": "user",
          "parts": [{"kind": "text", "text": "Help me learn Python"}]
        }
      ]
    }
  }'
```

### 4. Load Testing
```bash
python load_test.py http://localhost:5000/tasks/send 20 5
```

Expected output:
- Success rate: >95%
- Average latency: <5s
- No timeouts under normal load

## Performance Tuning

### 1. Hypercorn Workers
For production, use multiple workers:
```bash
hypercorn app:app --bind 0.0.0.0:$PORT --workers 4
```

Number of workers should be: `(2 x CPU cores) + 1`

### 2. Timeout Configuration
Adjust timeouts based on your use case:

In `app.py`:
```python
LLM_TIMEOUT = 6.0  # Total request timeout
```

In `agents/agent.py`:
```python
self.llm = ChatGoogleGenerativeAI(
    timeout=5.0,  # Per LLM request
    max_retries=3  # Retry on transient failures
)
```

### 3. Context Cache Size
Consider adding cache size limits for long-running deployments:

```python
# In StudlyAgent.__init__
self.max_contexts = 1000  # Limit context history

# In process_messages_async
if len(self.study_contexts) > self.max_contexts:
    # Remove oldest contexts (FIFO)
    oldest_key = min(self.study_contexts.keys(), 
                    key=lambda k: self.study_contexts[k])
    del self.study_contexts[oldest_key]
```

## Monitoring

### Metrics to Track
1. **Request latency**: Average response time for `/tasks/send`
2. **Timeout rate**: Percentage of requests hitting 6s timeout
3. **Error rate**: Non-200 responses
4. **Concurrency**: Number of concurrent requests handled

### Logging
Application logs include:
- Request/response JSON-RPC IDs
- Timeout warnings
- LLM errors
- Context management operations

Access logs via:
```bash
# Systemd
journalctl -u studly-agent -f

# Docker
docker logs -f container_name

# Heroku
heroku logs --tail
```

## Troubleshooting

### High Timeout Rate
- Increase `LLM_TIMEOUT` in `app.py`
- Check Gemini API status/rate limits
- Simplify prompt template in `agents/agent.py`

### Memory Usage Growing
- Add context cache size limits (see Performance Tuning)
- Monitor `study_contexts` dictionary size
- Consider using Redis for distributed context storage

### Slow Response Times
- Increase Hypercorn workers
- Check network latency to Gemini API
- Review LLM parameters (temperature, max_output_tokens)

### Lock Contention
- If many requests use same context_id, consider sharding contexts
- Use Redis with distributed locks for multi-instance deployments

## Upgrading from Sync Version

If upgrading from a synchronous version:

1. **Update dependencies**: `uv sync` to get hypercorn, pytest-asyncio, aiohttp
2. **Update Procfile**: Change from gunicorn to hypercorn
3. **Test async flow**: Run test suite with `pytest`
4. **Load test**: Verify performance with `load_test.py`
5. **Deploy gradually**: Consider blue-green deployment to test under real load

## Security Considerations

1. **API Key Protection**: Never commit `.env` file (in .gitignore)
2. **CORS Configuration**: Review CORS settings in production
3. **Rate Limiting**: Consider adding rate limiting middleware
4. **Input Validation**: All JSON-RPC requests validated with Pydantic
5. **Timeout Protection**: Hard timeouts prevent resource exhaustion

## Support

For deployment issues:
1. Check application logs
2. Verify environment variables
3. Test with simple curl request
4. Run load test script to identify bottlenecks
5. Review this deployment guide

## References

- [Flask Async Views](https://flask.palletsprojects.com/en/3.0.x/async-await/)
- [Hypercorn Deployment](https://hypercorn.readthedocs.io/)
- [LangChain Async](https://python.langchain.com/docs/concepts/async/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
