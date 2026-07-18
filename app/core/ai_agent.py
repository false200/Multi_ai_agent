from __future__ import annotations

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages.ai import AIMessage
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from app.common.custom_exception import CustomException
from app.common.logger import get_logger
from app.config.settings import settings

logger = get_logger(__name__)


def get_response_from_ai_agents(
    llm_id: str,
    query: list[str],
    allow_search: bool,
    system_prompt: str,
) -> str:
    """Run a LangGraph ReAct agent and return the latest AI message."""
    try:
        llm = ChatGroq(model=llm_id)
        tools = (
            [TavilySearchResults(max_results=settings.tavily_max_results)]
            if allow_search
            else []
        )

        agent = create_react_agent(
            model=llm,
            tools=tools,
            state_modifier=system_prompt,
        )

        logger.info(
            "Invoking agent model=%s allow_search=%s messages=%s",
            llm_id,
            allow_search,
            len(query),
        )
        response = agent.invoke({"messages": query})
        messages = response.get("messages") or []

        ai_contents = [
            message.content
            for message in messages
            if isinstance(message, AIMessage) and message.content
        ]

        if not ai_contents:
            raise CustomException("Agent returned no AI response")

        return ai_contents[-1]
    except CustomException:
        raise
    except Exception as exc:
        raise CustomException("Failed to generate agent response", error_detail=exc) from exc
