from __future__ import annotations

import operator
from typing import Annotated, Literal, Sequence, TypedDict

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import create_react_agent

from app.common.custom_exception import CustomException
from app.common.logger import get_logger
from app.config.settings import settings

logger = get_logger(__name__)

AGENT_MEMBERS = ("researcher", "analyst", "writer")
NextWorker = Literal["researcher", "analyst", "writer", "FINISH"]


class MultiAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str
    agent_trace: Annotated[list[str], operator.add]


def _build_tools(allow_search: bool) -> list:
    if not allow_search:
        return []
    return [TavilySearchResults(max_results=settings.tavily_max_results)]


def _last_ai_text(messages: Sequence[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            return str(message.content)
    raise CustomException("Multi-agent run produced no AI response")


def _parse_supervisor_choice(raw: str) -> NextWorker:
    text = (raw or "").strip().lower()
    if "finish" in text:
        return "FINISH"
    for member in AGENT_MEMBERS:
        if member in text:
            return member
    # Prefer finishing if the model is unclear after specialists have spoken.
    return "FINISH"


def _run_specialist(
    state: MultiAgentState,
    agent,
    name: str,
) -> dict:
    result = agent.invoke({"messages": state["messages"]})
    result_messages = result.get("messages") or []
    content = _last_ai_text(result_messages)
    logger.info("Agent '%s' completed", name)
    return {
        "messages": [AIMessage(content=content, name=name)],
        "agent_trace": [name],
    }


def _build_multi_agent_graph(
    llm_id: str,
    allow_search: bool,
    system_prompt: str,
):
    llm = ChatGroq(model=llm_id, temperature=0)
    tools = _build_tools(allow_search)

    researcher = create_react_agent(
        model=llm,
        tools=tools,
        state_modifier=(
            "You are the Researcher agent on a multi-agent team. "
            "Gather relevant facts and evidence for the user's request. "
            "If search tools are available, use them when helpful. "
            "Return concise findings only — do not write the final user answer."
        ),
    )
    analyst = create_react_agent(
        model=llm,
        tools=[],
        state_modifier=(
            "You are the Analyst agent on a multi-agent team. "
            "Review the conversation and researcher findings. "
            "Identify key insights, gaps, and a clear structure for the answer. "
            "Do not write the final polished user answer."
        ),
    )
    writer_instructions = (
        "You are the Writer agent on a multi-agent team. "
        "Using the researcher and analyst messages, write the final answer "
        "for the end user. Be clear and complete."
    )
    if system_prompt.strip():
        writer_instructions = (
            f"{writer_instructions}\n\nAdditional user instructions:\n{system_prompt.strip()}"
        )
    writer = create_react_agent(
        model=llm,
        tools=[],
        state_modifier=writer_instructions,
    )

    members = ", ".join(AGENT_MEMBERS)
    supervisor_system = SystemMessage(
        content=(
            f"You are the supervisor of a multi-agent team: {members}.\n"
            "- researcher: gathers facts (optionally via web search)\n"
            "- analyst: analyzes findings and structures insights\n"
            "- writer: produces the final user-facing answer\n\n"
            "Decide which worker should act next. "
            "Typical flow: researcher → analyst → writer → FINISH. "
            "Skip workers that are unnecessary. "
            "After the writer has produced a complete answer, respond with FINISH.\n"
            f"Reply with exactly one token from: {members}, FINISH."
        )
    )

    def supervisor_node(state: MultiAgentState) -> dict:
        response = llm.invoke([supervisor_system, *state["messages"]])
        choice = _parse_supervisor_choice(str(response.content))
        logger.info("Supervisor routed to %s", choice)
        return {"next": choice, "agent_trace": [f"supervisor:{choice}"]}

    def researcher_node(state: MultiAgentState) -> dict:
        return _run_specialist(state, researcher, "researcher")

    def analyst_node(state: MultiAgentState) -> dict:
        return _run_specialist(state, analyst, "analyst")

    def writer_node(state: MultiAgentState) -> dict:
        return _run_specialist(state, writer, "writer")

    def route_supervisor(state: MultiAgentState) -> str:
        return state["next"]

    graph = StateGraph(MultiAgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("writer", writer_node)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "researcher": "researcher",
            "analyst": "analyst",
            "writer": "writer",
            "FINISH": END,
        },
    )
    graph.add_edge("researcher", "supervisor")
    graph.add_edge("analyst", "supervisor")
    graph.add_edge("writer", "supervisor")

    return graph.compile()


def get_response_from_ai_agents(
    llm_id: str,
    query: list[str],
    allow_search: bool,
    system_prompt: str,
) -> tuple[str, list[str]]:
    """Run the multi-agent supervisor team and return (final answer, agent trace)."""
    try:
        if not query:
            raise CustomException("At least one user message is required")

        graph = _build_multi_agent_graph(llm_id, allow_search, system_prompt)
        initial_messages: list[BaseMessage] = [HumanMessage(content=message) for message in query]

        logger.info(
            "Starting multi-agent run model=%s allow_search=%s messages=%s",
            llm_id,
            allow_search,
            len(query),
        )
        result = graph.invoke(
            {
                "messages": initial_messages,
                "next": "supervisor",
                "agent_trace": [],
            },
            {"recursion_limit": settings.multi_agent_recursion_limit},
        )

        messages = result.get("messages") or []
        # Prefer the writer's final message when present.
        writer_messages = [
            message
            for message in messages
            if isinstance(message, AIMessage)
            and getattr(message, "name", None) == "writer"
            and message.content
        ]
        if writer_messages:
            response_text = str(writer_messages[-1].content)
        else:
            response_text = _last_ai_text(messages)

        agent_trace = list(result.get("agent_trace") or [])
        logger.info("Multi-agent run finished trace=%s", agent_trace)
        return response_text, agent_trace
    except CustomException:
        raise
    except Exception as exc:
        raise CustomException("Failed to generate multi-agent response", error_detail=exc) from exc
