from __future__ import annotations

from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.common.custom_exception import CustomException
from app.common.logger import get_logger
from app.config.settings import settings
from app.core.ai_agent import get_response_from_ai_agents

logger = get_logger(__name__)

app = FastAPI(
    title="Multi AI Agent",
    description="Chat API powered by Groq models with optional Tavily web search",
    version="0.1.0",
)


class ChatRequest(BaseModel):
    model_name: str = Field(..., description="Groq model identifier")
    system_prompt: str = Field(default="", description="Agent system instructions")
    messages: List[str] = Field(..., min_length=1, description="User messages")
    allow_search: bool = Field(default=False, description="Enable Tavily web search")


class ChatResponse(BaseModel):
    response: str


@app.get("/")
def root() -> dict[str, object]:
    return {
        "service": "Multi AI Agent API",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "chat": "POST /chat",
        "ui": "http://127.0.0.1:8501",
        "allowed_models": list(settings.allowed_model_names),
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    logger.info("Chat request received for model=%s", request.model_name)

    if request.model_name not in settings.allowed_model_names:
        logger.warning("Rejected invalid model name: %s", request.model_name)
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid model name. Allowed: {', '.join(settings.allowed_model_names)}"
            ),
        )

    try:
        response_text = get_response_from_ai_agents(
            request.model_name,
            request.messages,
            request.allow_search,
            request.system_prompt,
        )
        logger.info("Successfully generated response with model=%s", request.model_name)
        return ChatResponse(response=response_text)
    except CustomException as exc:
        logger.error("Agent error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error during response generation")
        raise HTTPException(
            status_code=500,
            detail=str(CustomException("Failed to get AI response", error_detail=exc)),
        ) from exc
