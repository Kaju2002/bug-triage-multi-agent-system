# config/models.py
# Initialize and return configured Ollama LLM instances
# Used by all agents to get a consistent ChatOllama connection

from langchain_ollama import ChatOllama
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL, DEFAULT_TEMPERATURE


def get_ollama_model(
    model_name: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    format: str = "json",
) -> ChatOllama:
    """
    Get a configured Ollama LLM instance.

    Loads model name and base URL from environment variables (config/settings.py).
    This ensures all agents use the same Ollama configuration.

    Args:
        model_name:   Ollama model to use (e.g. 'llama3:8b', 'phi3').
                      If None, uses OLLAMA_MODEL from settings.
        temperature:  Generation temperature (0.0 = deterministic, 1.0 = creative).
                      If None, uses DEFAULT_TEMPERATURE from settings (0.1).
        max_tokens:   Maximum output tokens. If None, defaults to 2048.
        format:       Output format. 'json' forces JSON-only output.
                      Useful for structured responses.

    Returns:
        ChatOllama: Configured language model instance ready to invoke.

    Example:
        >>> llm = get_ollama_model(temperature=0.7)
        >>> response = llm.invoke([HumanMessage(content="Hello")])
        >>> print(response.content)

    Note:
        Ollama service must be running on OLLAMA_BASE_URL (default: localhost:11434).
        Pre-download the model: ollama pull llama3:8b
    """
    model = model_name or OLLAMA_MODEL
    temp = temperature if temperature is not None else DEFAULT_TEMPERATURE
    tokens = max_tokens or 2048

    return ChatOllama(
        model=model,
        base_url=OLLAMA_BASE_URL,
        temperature=temp,
        num_predict=tokens,
        format=format,
    )