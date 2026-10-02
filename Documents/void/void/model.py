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
            # Strip non-standard fields (e.g. "dangerous") that some providers reject
            clean_tools = []
            for t in tools:
                clean = {"type": "function", "function": {}}
                fn = t.get("function", {})
                clean["function"] = {
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", {}),
                }
                clean_tools.append(clean)
            kwargs["tools"] = clean_tools
        resp = self._call_with_fallback(kwargs)
        choice = resp.choices[0].message
        return ChatResponse(
            content=choice.content,
            tool_calls=choice.tool_calls,
        )

    def _call_with_fallback(self, kwargs: dict):
        """Try the current model, then walk the fallback chain on failure.

        Each fallback provider is retried with the same messages. The first
        one that answers wins and becomes the active client for later turns.
        """
        from void.providers import get_fallback_chain, get_provider

        try:
            return self._client.chat.completions.create(**kwargs)
        except Exception as first_err:
            last = first_err
            for name in get_fallback_chain():
                cfg = get_provider(name) or {}
                key = cfg.get("api_key")
                if not key:
                    continue
                try:
                    alt_kwargs = {"api_key": key}
                    if cfg.get("base_url"):
                        alt_kwargs["base_url"] = cfg["base_url"]
                    client = OpenAI(**alt_kwargs)
                    # Swap the model name if the provider declares models
                    models = cfg.get("models") or []
                    if models:
                        kwargs = {**kwargs, "model": models[0]}
                    resp = client.chat.completions.create(**kwargs)
                    self._client = client
                    self.api_key = key
                    if cfg.get("base_url"):
                        self.base_url = cfg["base_url"]
                    self.model_name = kwargs["model"]
                    return resp
                except Exception as e:
                    last = e
                    continue
            raise last


class ChatResponse:
    """What the model returns — either text or tool calls."""

    def __init__(self, content: str | None, tool_calls: list | None):
        self.content = content
        self.tool_calls = tool_calls or []


class MissingApiKeyError(Exception):
    """Raised when no API key is available at startup."""

