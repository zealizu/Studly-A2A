# StudlyAgent: A2A Study Plan Generator

![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![Flask](https://img.shields.io/badge/Flask-2.3%2B-green) ![Gemini](https://img.shields.io/badge/Gemini-2.5-FF6B6B) ![A2A](https://img.shields.io/badge/A2A-Protocol-orange)

StudlyAgent is an AI-powered Agent2Agent (A2A) server built with Flask that generates personalized study plans using Google's Gemini model via LangChain. It integrates seamlessly with platforms like Telex for workflow orchestration, handling streaming, history, and interpreted queries. Designed for education tools, it creates structured, motivational plans based on user inputs like topic and duration.

## Features

- **Personalized Plans**: Generates markdown-formatted study schedules with duration, daily goals, time estimates, and tips.
- **A2A Compliance**: Supports discovery (`/.well-known/agent.json`) and task processing (`/tasks/send`).
- **Telex Integration**: Normalizes Telex's nested `parts` and `data` history for multi-turn convos without bloat.
- **Error-Resilient**: Fallbacks for empty inputs, validation errors, and malformed payloads.

## Quick Start

1. Clone the repo:
   ```bash
   git clone <your-repo-url>
   cd studly-agent
   ```
2. Install dependencies:

   ```bash
   uv sync
   ```

3. Set environment variables:
   ```bash
   export GEMINI_API_KEY="your-key-from-aistudio.google.com"
   ```
4. Run locally:

   ```bash
   python main.py
   or
   uv run main.py
   ```

5. Test with curl:
   ```bash
   curl -X POST "http://127.0.0.1:5000/tasks/send" \
   -H "Content-Type: application/json" \
   -d '{
     "jsonrpc": "2.0",
     "id": "test-1",
     "method": "message/send",
     "params": {
       "message": {
         "role": "user",
         "parts": [{"kind": "text", "text": "7-day Python study plan"}]
       }
     }
   }'
   ```
   - Expected: JSON with `result.artifacts` containing a markdown plan.

## Installation

### Prerequisites

- Python 3.8+
- Git

### Setup

1. Install dependencies:

   ```bash
   pip install flask pydantic langchain langchain-google-genai python-dotenv flask-cors uvicorn
   or
   uv sync
   ```

2. Environment:

   - Create `.env`:
     ```
     GEMINI_API_KEY=your-api-key
     ```
   - Source it: `source .env`.

3. Directory Structure:
   ```
   studly-agent/
   ├── app.py          # Main Flask app with A2A endpoints
   ├── agents/agent.py # StudlyAgent class (Gemini integration)
   ├── models/a2a.py   # Pydantic models (Task, Message, etc.)
   ├── utils.py        # normalize_telex_message function
   ├── pyproject.toml
   └── .env            # Secrets
   ```

## Usage

### Local Development

- Run: `python app.py` (port 5000).
- Endpoints:
  - `GET /.well-known/agent.json`: Agent card for discovery.
  - `POST /tasks/send`: Process task (JSON-RPC or raw Task).

### API Example (Streaming)

```bash
curl -N -X POST "http://127.0.0.1:5000/tasks/sendSubscribe" \
-H "Content-Type: application/json" \
-d '{
  "jsonrpc": "2.0",
  "id": "stream-test",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{"kind": "text", "text": "3-day Python basics"}]
    }
  }
}'
```

- Output: Live chunks like `data: {"id": "stream-test", "chunk": "Alright, let's start..."}` ending with `[DONE]`.

### Telex Integration

1. Update workflow JSON:
   ```json
   {
     "name": "studly_agent",
     "nodes": [
       {
         "id": "study_agent",
         "type": "a2a/mastra-a2a-node",
         "url": "https://your-railway-url.com",
         "streaming": true // For /tasks/sendSubscribe
       }
     ]
   }
   ```
2. Import to Telex dashboard—test with "Study plan for FastAPI in 1 week".

## Development

### Logging

- Logs to stdout (Railway-visible). Levels: INFO for requests, WARNING for fallbacks, ERROR for exceptions.
- Debug: Add `app.logger.debug(f"Debug: {var}")` in normalizer/agent.

### Optimization

- Response Time: <5s median (Gemini 2.5-flash, cached, <250 tokens).

### Troubleshooting

- **Validation Errors**: Update `models/a2a.py` for new Telex fields (e.g., `reason: Optional[str]` in `Part`).
- **Empty Messages**: Normalizer logs "No parts"—check Telex payload in "Raw Telex body".
- **Timeouts**: Telex 15s limit—use streaming for long Gemini turns.

## Deployment

### Railway

1. Connect GitHub repo in Railway dashboard.
2. Add env vars: `GEMINI_API_KEY`.
3. Deploy: Auto-builds from `requirements.txt`.
4. Logs: `railway logs --watch`.
5. Custom Domain: Add for HTTPS (A2A required).

## Contributing

1. Fork the repo.
2. Create branch: `git checkout -b feature/new-feature`.
3. Commit: `git commit -m "Add new feature"`.
4. Push: `git push origin feature/new-feature`.
5. Open PR.
