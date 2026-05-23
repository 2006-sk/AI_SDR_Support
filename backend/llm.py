from openai import OpenAI

OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_API_KEY = "ollama"
MODEL = "llama3.2"
OLLAMA_TIMEOUT = 120.0


def get_client() -> OpenAI:
    return OpenAI(
        base_url=OLLAMA_BASE_URL,
        api_key=OLLAMA_API_KEY,
        timeout=OLLAMA_TIMEOUT,
    )


def chat_completion(
    messages: list[dict],
    *,
    model: str = MODEL,
    stream: bool = False,
    temperature: float = 0.4,
):
    client = get_client()
    return client.chat.completions.create(
        model=model,
        messages=messages,
        stream=stream,
        temperature=temperature,
    )


def chat_completion_safe(
    messages: list[dict],
    *,
    model: str = MODEL,
    stream: bool = False,
    temperature: float = 0.4,
) -> tuple[object | None, Exception | None]:
    try:
        result = chat_completion(
            messages,
            model=model,
            stream=stream,
            temperature=temperature,
        )
        return result, None
    except Exception as exc:
        print(f"Ollama error: {exc}")
        return None, exc
