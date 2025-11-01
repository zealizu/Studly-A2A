# Changelog

All notable changes to the Studly Agent async pipeline implementation.

## [Unreleased] - Async Gemini Pipeline

### Added

#### Core Async Functionality
- **Async Agent Method**: Added `process_messages_async()` to `StudlyAgent` using `await self.chain.ainvoke()` for non-blocking Gemini API calls
- **Async LLM Call**: Added `_generate_study_plan_async()` method with proper timeout and error handling
- **Concurrency Protection**: Implemented `asyncio.Lock` (`_context_lock`) to protect shared `study_contexts` dictionary from race conditions
- **Timeout Handling**: Added 6s configurable timeout (`LLM_TIMEOUT`) at endpoint level using `asyncio.wait_for()`
- **Graceful Timeout Response**: Returns HTTP 408 with JSON-RPC error code -32000 instead of 500 on timeout

#### Flask Route Updates
- **Async Endpoint**: Converted `/tasks/send` route to `async def a2a_endpoint()` for true async execution
- **Nested Timeout Handling**: Two-level timeout catch for robustness (inner try-catch + outer exception handler)
- **Error Preservation**: Maintains JSON-RPC 2.0 compliance for all error responses including timeouts

#### Testing Infrastructure
- **Async Agent Tests** (`tests/test_async_agent.py`):
  - Test successful async message processing
  - Test timeout handling with slow responses
  - Test empty/invalid input handling
  - Test LLM error handling
  - Test context locking and race condition prevention
  - Test concurrent context management (5 concurrent requests same context)
  - Test multiple contexts concurrent (10 different contexts)
  
- **Async Endpoint Tests** (`tests/test_async_endpoint.py`):
  - Test successful request/response flow
  - Test timeout error responses (408 status)
  - Test invalid JSON handling
  - Test JSON-RPC validation
  - Test both `execute` and `message/send` methods
  
- **pytest Configuration** (`pytest.ini`): Added with `asyncio_mode = auto` for seamless async testing

#### Load Testing
- **Load Test Script** (`load_test.py`):
  - Async concurrent load testing using aiohttp
  - Configurable number of requests and concurrency level
  - Comprehensive statistics: min/max/mean/median latency, success/failure rates
  - Pass/fail based on <5s average latency target
  - Command-line arguments for customization
  
#### Documentation
- **README.md**: Comprehensive documentation with:
  - Architecture overview
  - Endpoint documentation with request/response examples
  - Timeout response examples
  - Installation and running instructions
  - Testing guide
  - Performance benchmarks and targets
  - Load testing instructions
  - Error code reference table
  - Development guidelines
  
- **DEPLOYMENT.md**: Detailed deployment guide with:
  - ASGI vs WSGI comparison
  - Deployment steps for Heroku/Railway/Render/Docker/Systemd
  - Performance tuning recommendations
  - Monitoring setup
  - Troubleshooting guide
  - Security considerations
  - Upgrade path from sync version
  
- **CHANGELOG.md**: This file documenting all changes

#### Dependencies
- **hypercorn>=0.17.0**: ASGI server for true async execution
- **pytest>=8.3.5**: Testing framework
- **pytest-asyncio>=0.24.0**: Async testing support
- **aiohttp>=3.11.11**: Async HTTP client for load testing

#### Configuration
- **Procfile**: Updated to use Hypercorn instead of Gunicorn for ASGI deployment
- **.gitignore**: Added pytest cache, coverage, and build artifacts
- **LLM Timeout Configuration**: Added 5s timeout to LangChain `ChatGoogleGenerativeAI` client

### Changed

#### Agent Implementation
- Added timeout parameter to LLM client configuration (5s)
- Maintained backward compatibility by keeping synchronous `process_messages()` method
- Enhanced error messages for timeout scenarios

#### Error Handling
- Timeout errors now return proper JSON-RPC error with code -32000 (not -32603)
- HTTP status for timeouts changed from 500 to 408 (Request Timeout)
- More descriptive error messages with timeout duration information

#### Performance
- Non-blocking LLM calls enable concurrent request handling
- Context management protected from race conditions with async locks
- Request timeout enforced at 6s to meet <5s average latency target

### Technical Details

#### Async Implementation Pattern
```python
# Endpoint level timeout
result = await asyncio.wait_for(
    agent.process_messages_async(...),
    timeout=LLM_TIMEOUT  # 6s
)

# Agent level async call
response = await self.chain.ainvoke({"query": query})

# Context protection
async with self._context_lock:
    history = self.study_contexts.get(context_id, [])
```

#### Error Response Format (Timeout)
```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "error": {
    "code": -32000,
    "message": "Request timeout",
    "data": {
      "details": "The request took longer than 6s to process..."
    }
  }
}
```

### Acceptance Criteria Met

✅ **Async Pipeline**: `StudlyAgent.process_messages_async()` uses `await chain.ainvoke()`  
✅ **Shared State Protection**: `asyncio.Lock` protects `study_contexts` dictionary  
✅ **Async Flask Route**: `/tasks/send` is `async def` with ASGI server support  
✅ **Timeout Handling**: `asyncio.wait_for` with 6s timeout, graceful error response  
✅ **Test Coverage**: Comprehensive unit/integration tests including timeout scenarios  
✅ **Documentation**: README updated with ASGI server requirements and deployment docs  
✅ **Performance Target**: Architecture supports <5s latency for typical prompts  
✅ **JSON-RPC Compliance**: Preserves schema and conversation context  
✅ **Non-500 Timeout**: Returns 408 with JSON-RPC error payload

### Migration Notes

For users upgrading from the synchronous version:

1. **Dependencies**: Run `uv sync` to install new dependencies (hypercorn, pytest-asyncio, aiohttp)
2. **Deployment**: Update deployment to use Hypercorn instead of Gunicorn (see Procfile)
3. **Testing**: Run `pytest` to verify async functionality
4. **Load Testing**: Use `python load_test.py` to verify performance targets
5. **Backward Compatibility**: Synchronous `process_messages()` method still available

### Known Limitations

- Context history stored in-memory (consider Redis for multi-instance deployments)
- No automatic cleanup of old contexts (see DEPLOYMENT.md for recommendations)
- Timeout only at request level (individual LLM retry timeouts handled by LangChain)

### Future Enhancements

Potential improvements for future versions:
- Redis-backed context storage for distributed deployments
- Streaming responses using Server-Sent Events (SSE)
- Request queuing and backpressure handling
- Metrics endpoint for monitoring (Prometheus format)
- Context cache size limits with LRU eviction
- Distributed tracing support (OpenTelemetry)
