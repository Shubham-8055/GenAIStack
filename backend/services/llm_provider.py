"""
LLM Abstraction Layer.
Centralizes LLM creation so no agent has hardcoded URLs or model names.
"""
import os
from langchain_openai import ChatOpenAI


# Read from environment with sensible defaults
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://183.82.7.228:9532/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "EMPTY")
DEFAULT_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "/model")


def get_llm(
    model_name: str = None,
    temperature: float = 0.0,
    base_url: str = None,
    api_key: str = None,
) -> ChatOpenAI:
    """
    Factory function to create an LLM instance.
    
    Args:
        model_name: Model identifier (defaults to env LLM_MODEL_NAME)
        temperature: Sampling temperature
        base_url: Override the base URL (defaults to env LLM_BASE_URL)
        api_key: Override the API key (defaults to env LLM_API_KEY)
    
    Returns:
        ChatOpenAI instance configured for the given parameters.
    """
    return ChatOpenAI(
        model=model_name or DEFAULT_MODEL_NAME,
        base_url=base_url or LLM_BASE_URL,
        api_key=api_key or LLM_API_KEY,
        temperature=temperature,
    )
