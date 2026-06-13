"""
LLM Abstraction Layer.
Centralizes LLM creation so no agent has hardcoded URLs or model names.
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load .env file
load_dotenv()

# Read from environment with sensible defaults
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
DEFAULT_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")


def get_llm(
    model_name: str = None,
    temperature: float = 0.0,
    base_url: str = None,
    api_key: str = None,
) -> ChatOpenAI:

    # If model_name is the database default, prioritize env model if configured
    env_model = os.getenv("LLM_MODEL_NAME")
    model = model_name or DEFAULT_MODEL_NAME
    if env_model and (model_name == "google/gemma-4-31b-it:free" or model_name == "/model"):
        model = env_model

    return ChatOpenAI(
        model=model,
        base_url=base_url or LLM_BASE_URL,
        api_key=api_key or LLM_API_KEY,
        temperature=temperature,
    )