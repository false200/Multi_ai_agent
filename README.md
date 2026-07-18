# Multi AI Agent

A small full-stack demo that runs a configurable LLM agent behind a Streamlit UI and a FastAPI service. Models are served through Groq; optional live web search is provided by Tavily via a LangGraph ReAct agent.

## Features

- Choose a Groq model and set a custom system prompt
- Optional Tavily web search during agent runs
- FastAPI chat API with OpenAPI docs at `/docs`
- Streamlit frontend for interactive use
- Docker image and Jenkins pipeline for ECR / ECS deployment

## Stack

| Layer | Technology |
| --- | --- |
| UI | Streamlit |
| API | FastAPI, Uvicorn |
| Agent | LangChain, LangGraph |
| Models | Groq (`llama3-70b-8192`, `llama-3.3-70b-versatile`) |
| Search | Tavily |
| Packaging | uv |
| Deploy | Docker, Jenkins, SonarQube, AWS ECR / ECS Fargate |

## Architecture

```
Streamlit (port 8501)
        │
        ▼
FastAPI  POST /chat  (port 9999)
        │
        ▼
LangGraph ReAct agent ──► Groq LLM
        │
        └── (optional) Tavily search
```

## Project layout

```
app/
  main.py              # Starts API and UI
  backend/api.py       # FastAPI routes
  frontend/ui.py       # Streamlit app
  core/ai_agent.py     # Agent invocation
  config/settings.py   # Env-based settings
  common/              # Logging and errors
Dockerfile
Jenkinsfile
pyproject.toml
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- Python 3.10–3.12 (project pins 3.11 via `.python-version`)
- API keys:
  - [Groq](https://console.groq.com/) — required
  - [Tavily](https://tavily.com/) — required only when web search is enabled

## Setup

```bash
git clone <your-repo-url>
cd MULTI-AI-AGENT-PROJECTS-main

uv sync
```

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_...
TAVILY_API_KEY=tvly-...
```

Optional settings:

```env
BACKEND_HOST=127.0.0.1
BACKEND_PORT=9999
API_TIMEOUT_SECONDS=120
```

A template is available in `.env.example`. Do not commit `.env`.

## Run locally

```bash
uv run python app/main.py
```

| Service | URL |
| --- | --- |
| Streamlit UI | http://127.0.0.1:8501 |
| API root | http://127.0.0.1:9999 |
| OpenAPI docs | http://127.0.0.1:9999/docs |
| Health check | http://127.0.0.1:9999/health |

## API

### `POST /chat`

```json
{
  "model_name": "llama-3.3-70b-versatile",
  "system_prompt": "You are a helpful assistant.",
  "messages": ["What is LangGraph?"],
  "allow_search": false
}
```

Response:

```json
{
  "response": "..."
}
```

Allowed `model_name` values are defined in `app/config/settings.py`.

### Example with curl

```bash
curl -X POST http://127.0.0.1:9999/chat \
  -H "Content-Type: application/json" \
  -d "{\"model_name\":\"llama-3.3-70b-versatile\",\"system_prompt\":\"Be concise.\",\"messages\":[\"Hello\"],\"allow_search\":false}"
```

## Docker

```bash
docker build -t multi-ai-agent .
docker run --rm -p 8501:8501 -p 9999:9999 \
  -e GROQ_API_KEY=gsk_... \
  -e TAVILY_API_KEY=tvly-... \
  multi-ai-agent
```

## CI/CD

`Jenkinsfile` defines a pipeline that:

1. Checks out the repository
2. Runs SonarQube analysis
3. Builds and pushes an image to Amazon ECR
4. Forces a new deployment on ECS Fargate

Cluster and service names in the Jenkinsfile should be updated for your AWS account before use. A custom Jenkins image with Docker support lives under `custom_jenkins/`.

## License

Add a license file if you intend to publish this repository publicly.
