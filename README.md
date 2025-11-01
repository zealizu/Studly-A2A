# Studly - AI Study Plan Generator

A Flask-based microservice that generates personalized study plans using Google Gemini AI, designed for Telex Agent-to-Agent integrations.

## Features

- JSON-RPC 2.0 compliant API
- Support for Telex message format normalization
- Conversation context management
- LangChain integration with Google Gemini
- CORS-enabled endpoints
- Structured artifact responses

## Quick Start

### Prerequisites

- Python 3.13+
- Google Gemini API key

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   # or with uv:
   uv sync
   ```

3. Set up environment variables:
   ```bash
   export GEMINI_API_KEY=your_api_key_here
   ```

4. Run the server:
   ```bash
   python app.py
   # or with Gunicorn:
   gunicorn app:app
   ```

## API Endpoints

### `GET /`
Health check endpoint

### `GET /.well-known/agent.json`
Returns agent metadata for A2A discovery

### `POST /tasks/send`
Main endpoint for processing study plan requests

**Supported methods:**
- `message/send` - Telex format messages
- `execute` - Direct A2A execution

Example request:
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "method": "message/send",
  "params": {
    "message": {
      "kind": "message",
      "role": "user",
      "messageId": "msg-456",
      "parts": [
        {
          "kind": "text",
          "text": "Create a study plan for learning Python in 30 days"
        }
      ]
    }
  }
}
```

## Performance Tracing

The application includes built-in performance instrumentation to help identify bottlenecks. For detailed information on enabling tracing and running profiling tests, see:

📚 **[Performance Documentation](docs/performance.md)**

Quick start:
```bash
# Enable tracing
export A2A_TRACE_LATENCY=true

# Run the server
python app.py

# In another terminal, run profiling
python scripts/profile_tasks_send.py --requests 20
```

## Project Structure

```
.
├── app.py                  # Main Flask application
├── agents/
│   └── agent.py           # StudlyAgent implementation
├── models/
│   └── a2a.py             # Pydantic models for A2A protocol
├── utils.py               # Message normalization utilities
├── scripts/
│   └── profile_tasks_send.py  # Performance profiling script
└── docs/
    └── performance.md     # Performance documentation
```

## Configuration

Environment variables:
- `GEMINI_API_KEY` (required) - Google Gemini API key
- `A2A_TRACE_LATENCY` (optional) - Enable performance tracing (true/false)

## Development

Run in development mode:
```bash
python app.py
```

The server will start on `http://localhost:5000`

## Deployment

The application is configured for Gunicorn deployment:
```bash
gunicorn app:app --bind 0.0.0.0:5000
```

## License

[Your license here]
