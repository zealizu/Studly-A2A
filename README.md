# Studly Agent - Async Study Plan Generator

A Python 3.13 Flask microservice that provides AI-powered study plan generation through JSON-RPC endpoints. Built with async/await support for optimal performance under load.

## Features

- **Async Pipeline**: Non-blocking Gemini API calls with configurable timeouts
- **JSON-RPC 2.0**: Standard compliant request/response handling
- **Context Management**: Thread-safe conversation history with asyncio locks
- **Telex Agent Integration**: Compatible with Agent-to-Agent (A2A) protocol
- **Timeout Handling**: Graceful degradation with 6s timeout and proper error responses
- **ASGI Server**: Runs on Hypercorn for true async execution

## Architecture

- **Agent**: `StudlyAgent` with async `process_messages_async()` method
- **LLM**: Google Gemini 2.5-flash via LangChain with native async support
- **Concurrency**: Protected shared state using `asyncio.Lock` 
- **Timeouts**: `asyncio.wait_for` with 6s limit, returns JSON-RPC error on timeout

## Endpoints

### GET `/`
Health check endpoint.

**Response**: `Server is live`

### GET `/.well-known/agent.json`
Agent metadata and capabilities.

**Response**: 
```json
{
  "name": "Studly",
  "description": "AI-driven assistant for personalized study schedules",
  "version": "1.0",
  "capabilities": {
    "streaming": false,
    "pushNotifications": false
  },
  "skills": [
    {
      "name": "generate_study_plan",
      "description": "Creates personalized study plans"
    }
  ]
}
```

### POST `/tasks/send`
Main async endpoint for study plan generation.

**Request** (JSON-RPC 2.0):
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "execute",
  "params": {
    "contextId": "optional-context-id",
    "taskId": "optional-task-id",
    "messages": [
      {
        "kind": "message",
        "role": "user",
        "parts": [
          {
            "kind": "text",
            "text": "Help me learn Python in 2 weeks"
          }
        ]
      }
    ]
  }
}
```

**Success Response** (200 OK):
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {
    "id": "task-id",
    "contextId": "context-id",
    "status": {
      "state": "completed",
      "message": {
        "role": "agent",
        "parts": [{"kind": "text", "text": "# 2-Week Python Plan..."}]
      }
    },
    "artifacts": [
      {
        "name": "study_plan",
        "parts": [{"kind": "text", "text": "..."}]
      }
    ],
    "history": [...]
  }
}
```

**Timeout Response** (408 Request Timeout):
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "error": {
    "code": -32000,
    "message": "Request timeout",
    "data": {
      "details": "The request took longer than 6s to process..."
    }
  }
}
```

## Installation

### Prerequisites
- Python 3.13+
- UV or pip package manager
- Google Gemini API key

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd <project-directory>
```

2. Install dependencies:
```bash
uv sync
# or
pip install -e .
```

3. Create `.env` file with your API key:
```bash
GEMINI_API_KEY=your_api_key_here
```

## Running the Application

### Development (ASGI)
```bash
# Using hypercorn for async support
hypercorn app:app --bind 0.0.0.0:5000
```

### Production Deployment

The `Procfile` is configured for ASGI deployment:
```
web: hypercorn app:app --bind 0.0.0.0:$PORT
```

**Note**: This application requires an ASGI server (hypercorn/uvicorn) for true async execution. 
While Flask 3.x supports async routes, they run in a thread pool under WSGI servers like Gunicorn.

📖 **See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment guide**, including:
- Docker, Heroku, and systemd configurations
- Performance tuning recommendations
- Monitoring and troubleshooting tips
- Upgrading from sync version

### Alternative WSGI Deployment (Fallback)
```bash
# Falls back to thread pool execution
gunicorn app:app --bind 0.0.0.0:5000
```

## Configuration

### Timeout Settings
Edit `app.py` to adjust the LLM timeout:
```python
LLM_TIMEOUT = 6.0  # seconds
```

### LLM Parameters
Edit `agents/agent.py` to configure the Gemini model:
```python
self.llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.3,
    max_retries=3,
    timeout=5.0,  # Per-request timeout to LLM
)
```

## Testing

Run the test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=. --cov-report=html
```

### Test Coverage

- **Async Agent Tests** (`tests/test_async_agent.py`):
  - Successful async message processing
  - Timeout handling with slow responses
  - Empty/invalid input handling
  - LLM error handling
  - Context locking and race condition prevention
  - Concurrent context management

- **Async Endpoint Tests** (`tests/test_async_endpoint.py`):
  - Successful request/response flow
  - Timeout error responses (408 status)
  - Invalid JSON handling
  - Method validation
  - Both `execute` and `message/send` methods

## Performance

### Benchmarks

Target metrics:
- **Latency**: <5s for typical study plan requests
- **Timeout**: 6s hard limit with graceful error
- **Concurrency**: Thread-safe context management with async locks

### Load Testing

Use the included `load_test.py` script:
```bash
# Basic load test (20 requests, concurrency 5)
python load_test.py

# Custom configuration
python load_test.py http://localhost:5000/tasks/send 50 10

# Arguments: <url> <num_requests> <concurrency>
```

The script outputs:
- Request statistics (success/failure rates)
- Latency metrics (min/max/mean/median)
- Pass/fail status based on <5s average latency target

Alternative with Apache Bench:
```bash
ab -n 100 -c 10 -p payload.json -T application/json http://localhost:5000/tasks/send
```

## Error Codes

| Code | Message | Description |
|------|---------|-------------|
| -32600 | Invalid Request | Malformed JSON or missing required fields |
| -32601 | Method not found | Unknown JSON-RPC method |
| -32603 | Internal error | Server-side exception |
| -32000 | Request timeout | Request exceeded 6s timeout |

## Development

### Project Structure
```
.
├── agents/
│   └── agent.py          # StudlyAgent with async methods
├── models/
│   └── a2a.py            # Pydantic models for JSON-RPC and A2A
├── tests/
│   ├── test_async_agent.py
│   └── test_async_endpoint.py
├── app.py                # Flask app with async routes
├── utils.py              # Message normalization utilities
├── pyproject.toml        # Dependencies
├── pytest.ini            # Test configuration
└── Procfile              # Deployment configuration
```

### Adding New Features

1. Keep async methods with `async def` and `await`
2. Use `asyncio.Lock` for shared state access
3. Wrap external calls in `asyncio.wait_for` with timeouts
4. Return proper JSON-RPC error responses (not HTTP 500)
5. Add tests for both success and timeout paths

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `pytest`
5. Submit a pull request

## License

[Your License Here]

## Support

For issues or questions, please open a GitHub issue or contact the maintainers.
