"""Model client — OpenAI-format API wrapper. Reads config for defaults."""

import os
from openai import OpenAI
from void.config import get_api_key, get_base_url, get_model_name


class Model:
    """Wraps an OpenAI-format chat completions endpoint.

    Resolution order (each step falls back to the next):
      1. Explicit constructor args
      2. Config file (~/.void/config.json)
      3. Environment variables
      4. Built-in defaults

    Swap base_url to point at OpenRouter, LM Studio, vLLM, etc.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
    ):
        self.api_key = api_key or get_api_key()
        self.base_url = base_url or get_base_url()
        self.model_name = model_name or get_model_name()
        if not self.api_key:
            raise MissingApiKeyError(
                "No API key set. Run `void setup` or `void config set api_key <key>`, "
                "or set OPENAI_API_KEY."
            )
        kwargs: dict = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        self._client = OpenAI(**kwargs)

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> "ChatResponse":
        from void.config import get
        kwargs: dict = {"model": self.model_name, "messages": messages}
        max_tokens = get("max_tokens")
        if max_tokens:
            kwargs["max_tokens"] = int(max_tokens)
        if tools:
            kwargs["tools"] = tools
        resp = self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0].message
        return ChatResponse(
            content=choice.content,
            tool_calls=choice.tool_calls,
        )


class ChatResponse:
    """What the model returns — either text or tool calls."""

    def __init__(self, content: str | None, tool_calls: list | None):
        self.content = content
        self.tool_calls = tool_calls or []


class MissingApiKeyError(Exception):
    """Raised when no API key is available at startup."""

