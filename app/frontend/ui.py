from __future__ import annotations

import requests
import streamlit as st

from app.common.custom_exception import CustomException
from app.common.logger import get_logger
from app.config.settings import settings

logger = get_logger(__name__)


def _render_sidebar() -> None:
    st.sidebar.header("About")
    st.sidebar.markdown(
        "Configure a Groq-powered agent, optionally enable Tavily web search, "
        "and ask a question."
    )
    st.sidebar.caption(f"Backend: `{settings.chat_api_url}`")


def _build_payload(
    system_prompt: str,
    selected_model: str,
    allow_web_search: bool,
    user_query: str,
) -> dict:
    return {
        "model_name": selected_model,
        "system_prompt": system_prompt,
        "messages": [user_query],
        "allow_search": allow_web_search,
    }


def _ask_agent(payload: dict) -> str:
    try:
        logger.info("Sending request to backend")
        response = requests.post(
            settings.chat_api_url,
            json=payload,
            timeout=settings.api_timeout_seconds,
        )
    except requests.RequestException as exc:
        logger.error("Failed to reach backend: %s", exc)
        raise CustomException("Failed to communicate with backend", error_detail=exc) from exc

    if response.status_code != 200:
        detail = response.text
        try:
            detail = response.json().get("detail", detail)
        except ValueError:
            pass
        logger.error("Backend error status=%s detail=%s", response.status_code, detail)
        raise CustomException(f"Backend error ({response.status_code}): {detail}")

    data = response.json()
    agent_response = data.get("response", "")
    if not agent_response:
        raise CustomException("Backend returned an empty response")

    logger.info("Successfully received response from backend")
    return agent_response


def main() -> None:
    st.set_page_config(page_title="Multi AI Agent", layout="centered")
    st.title("Multi AI Agent")
    st.caption("Groq LLMs with optional Tavily web search")
    _render_sidebar()

    system_prompt = st.text_area("Define your AI agent", height=80)
    selected_model = st.selectbox("Select AI model", settings.allowed_model_names)
    allow_web_search = st.checkbox("Allow web search")
    user_query = st.text_area("Enter your query", height=150)

    if not st.button("Ask Agent", type="primary"):
        return

    if not user_query.strip():
        st.warning("Please enter a query before asking the agent.")
        return

    payload = _build_payload(
        system_prompt=system_prompt,
        selected_model=selected_model,
        allow_web_search=allow_web_search,
        user_query=user_query.strip(),
    )

    with st.spinner("Thinking..."):
        try:
            agent_response = _ask_agent(payload)
            st.subheader("Agent Response")
            st.markdown(agent_response)
        except CustomException as exc:
            st.error(str(exc))
        except Exception as exc:
            logger.exception("Unexpected UI error")
            st.error(str(CustomException("Unexpected error", error_detail=exc)))


if __name__ == "__main__":
    main()
