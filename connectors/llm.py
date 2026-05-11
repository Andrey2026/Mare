"""LLM provider factory."""

import logging

from langchain_openai import ChatOpenAI

import config

logger = logging.getLogger(__name__)


def get_llm() -> ChatOpenAI:
    """Create LLM instance from config.

    Uses OpenAI-compatible API. Change LLM_BASE_URL to use
    a different provider (AITUNNEL, OpenRouter, etc).

    Returns:
        Configured ChatOpenAI instance.
    """
    logger.info("Using LLM: %s via %s", config.LLM_MODEL, config.LLM_BASE_URL)
    return ChatOpenAI(
        model=config.LLM_MODEL,
        temperature=config.LLM_TEMPERATURE,
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
    )


if __name__ == "__main__":
    print(f"LLM_MODEL:    {config.LLM_MODEL}")
    print(f"LLM_BASE_URL: {config.LLM_BASE_URL}")
    try:
        llm = get_llm()
        print(f"LLM created: {type(llm).__name__}")
        response = llm.invoke("Say 'hello' in one word.")
        print(f"LLM response: {response.content}")
    except Exception as e:
        print(f"LLM test failed: {e}")
