from __future__ import annotations

import requests
import streamlit as st

from app.common.custom_exception import CustomException
from app.common.logger import get_logger
from app.config.settings import settings

logger = get_logger(__name__)


def _render_sidebar() -> None:
    st.sidebar.header("How it works")
    st.sidebar.write(
        "A supervisor routes each request across researcher, analyst, "
        "and writer agents before returning a single response."
    )


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


def _ask_agents(payload: dict) -> tuple[str, list[str]]:
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

    agent_trace = data.get("agent_trace") or []
    logger.info("Successfully received response from backend")
    return agent_response, agent_trace


def main() -> None:
    st.set_page_config(page_title="Multi AI Agent", layout="centered")
    st.title("Multi AI Agent")
    st.caption("Multi-agent orchestration on Groq")
    _render_sidebar()

    system_prompt = st.text_area(
        "Writer instructions",
        height=80,
        placeholder="Optional style or format guidance for the final answer",
    )
    selected_model = st.selectbox("Model", settings.allowed_model_names)
    allow_web_search = st.checkbox("Enable web search for the researcher")
    user_query = st.text_area("Query", height=150)

    if not st.button("Submit", type="primary"):
        return

    if not user_query.strip():
        st.warning("Enter a query before submitting.")
        return

    payload = _build_payload(
        system_prompt=system_prompt,
        selected_model=selected_model,
        allow_web_search=allow_web_search,
        user_query=user_query.strip(),
    )

    with st.spinner("Processing"):
        try:
            agent_response, agent_trace = _ask_agents(payload)
            if agent_trace:
                st.subheader("Execution path")
                st.code(" > ".join(agent_trace))
            st.subheader("Response")
            st.markdown(agent_response)
        except CustomException as exc:
            st.error(str(exc))
        except Exception as exc:
            logger.exception("Unexpected UI error")
            st.error(str(CustomException("Unexpected error", error_detail=exc)))


if __name__ == "__main__":
    main()
