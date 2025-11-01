# Studly - AI Study Planner Agent

A Flask microservice that provides AI-powered study planning through a JSON-RPC interface. Built for Telex Agent-to-Agent integrations with conversation history management and intelligent summarization.

## Features

- **Personalized Study Plans**: Generate structured study plans using Google Gemini
- **Conversation Context**: Maintains context across multiple interactions
- **History Trimming**: Automatically caps conversation history to reduce token usage
- **Smart Summarization**: Generates rolling summaries for long conversations
- **HTML Cleaning**: Aggressively strips HTML and normalizes whitespace from Telex messages
- **Caching**: Per-context caching of summaries and messages for performance

## Configuration

### Environment Variables

Create a `.env` file with the following:

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional - History Management (defaults shown)
HISTORY_CAP_TURNS=4              # Number of conversation turns to retain
ENABLE_SUMMARIZATION=true        # Enable automatic summarization
SUMMARY_THRESHOLD=8              # Messages before summarization kicks in
ENABLE_HISTORY_CACHE=true        # Cache messages per context
```

See [HISTORY_TRIMMING.md](HISTORY_TRIMMING.md) for detailed configuration options and tuning guidance.

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or with uv
uv sync
```

## Running

### Development

```bash
python app.py
```

### Production (Gunicorn)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## API Endpoints

### GET /
Health check endpoint

### GET /.well-known/agent.json
Returns agent metadata and capabilities

### POST /tasks/send
Main JSON-RPC endpoint for processing study plan requests

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "request-123",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "Help me create a study plan for learning Python"
        }
      ]
    }
  }
}
```

## History Management

The agent implements intelligent history management to optimize performance:

1. **Trimming**: Only recent messages are retained (configurable via `HISTORY_CAP_TURNS`)
2. **Summarization**: Long conversations are automatically summarized
3. **HTML Stripping**: HTML tags and entities are removed from all messages
4. **Caching**: Summaries and messages are cached per context

See [HISTORY_TRIMMING.md](HISTORY_TRIMMING.md) for complete documentation.

## Testing

```bash
# Run history trimming tests
python -m pytest test_history_trimming.py -v

# Run all tests
python -m pytest -v
```

## Performance

With history trimming enabled:
- **70-85% reduction** in input tokens
- **~90% faster** message normalization
- **~95% faster** context preparation (with cached summaries)
- Fixed memory usage per context

## Architecture

- **Flask**: Web framework with CORS support
- **LangChain**: LLM orchestration
- **Google Gemini**: AI model (gemini-2.5-flash)
- **Pydantic**: Request/response validation
- **Gunicorn**: Production WSGI server

## Development

### Project Structure

```
.
├── app.py                      # Flask application and routes
├── agents/
│   └── agent.py               # StudlyAgent with LLM logic
├── models/
│   └── a2a.py                 # Pydantic models for A2A protocol
├── utils.py                   # Message normalization utilities
├── config.py                  # Configuration management
├── test_history_trimming.py  # Test suite
└── HISTORY_TRIMMING.md       # Detailed documentation
```

## License

Add your license information here.
