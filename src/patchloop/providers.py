"""Explicit Nebius Token Factory and Tavily runtime clients.

Credentials stay in the orchestration process. These clients do not run repairs
or certify provider access; use the smoke commands to verify a configured key.
"""

import argparse
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

NEBIUS_BASE = "https://api.tokenfactory.nebius.com/v1"
TAVILY_SEARCH = "https://api.tavily.com/search"
# Live runs saw intermittent dropped connections while the provider stayed healthy.
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
ATTEMPTS = 3


class ProviderError(RuntimeError):
    def __init__(self, message, *, metadata=None):
        super().__init__(message)
        self.metadata = metadata or {}


def completion_metadata(response):
    """Only accounting fields; never include provider text or error bodies."""
    usage = response.get("usage", {})
    result = {"request_id": response.get("id"), "usage": {
        key: value for key, value in usage.items()
        if key in {"prompt_tokens", "completion_tokens", "total_tokens"}
        and type(value) is int and value >= 0} if isinstance(usage, dict) else {}}
    choices = response.get("choices")
    reason = choices[0].get("finish_reason") if isinstance(choices, list) and choices and isinstance(choices[0], dict) else None
    result["finish_reason"] = reason if isinstance(reason, str) and reason in {"stop", "length", "tool_calls", "content_filter"} else "unknown"
    return result


def _credential(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ProviderError(f"Set {name} in the environment")
    return value


def nemotron_model(role: str | None = None) -> str:
    """The NVIDIA Nemotron model for a role: NEBIUS_MODEL_<ROLE> when set, else NEBIUS_MODEL.

    Roles let cheap, fast models play the customer while larger ones draft rules and judge.
    """
    name = f"NEBIUS_MODEL_{role.upper()}" if role else "NEBIUS_MODEL"
    model = os.environ.get(name, "").strip() or _credential("NEBIUS_MODEL")
    if not model.lower().startswith("nvidia/") or "nemotron" not in model.lower():
        raise ProviderError(f"Select an NVIDIA Nemotron model from the catalog for {name}")
    return model


def total_usage(records) -> dict:
    """Sum the token counts of provider requests."""
    keys = ("prompt_tokens", "completion_tokens", "total_tokens")
    return {key: sum((record.get("usage") or {}).get(key, 0) for record in records) for key in keys}


def request_json(url: str, key: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(url, data=data, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
    })
    # Transient failures retry with 1 s then 2 s backoff; permanent ones fail at once.
    # Note: fixed backoff ignores Retry-After, and a timed-out call may still be billed.
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(2 ** (attempt - 1))
        try:
            with urlopen(request, timeout=60) as response:
                body = response.read(2_000_001)
        except HTTPError as exc:
            # Provider error bodies can echo requests. Never include them or credentials.
            error = ProviderError(f"Provider HTTP {exc.code}")
            if exc.code not in RETRY_STATUS:
                raise error from None
            continue
        except (URLError, TimeoutError, OSError):
            error = ProviderError("Provider request failed or timed out")
            continue
        if len(body) > 2_000_000:
            raise ProviderError("Provider response exceeds 2 MB limit")
        try:
            result = json.loads(body)
        except (ValueError, UnicodeError):
            raise ProviderError("Provider returned invalid JSON") from None
        if not isinstance(result, dict):
            raise ProviderError("Provider returned an invalid response object")
        return result
    raise error from None


class NebiusClient:
    def __init__(self):
        self._key = _credential("NEBIUS_API_KEY")

    def models(self) -> list[str]:
        response = request_json(f"{NEBIUS_BASE}/models", self._key)
        records = response.get("data")
        if not isinstance(records, list):
            raise ProviderError("Model catalog is missing data")
        return [row["id"] for row in records
                if isinstance(row, dict) and isinstance(row.get("id"), str)]

    def complete(self, messages: list[dict], *, model: str, max_tokens: int = 256,
                 temperature: float = 0, response_format: dict | None = None) -> dict:
        """One text completion. `response_format` asks Token Factory for JSON, optionally schema-checked."""
        if not model or not 1 <= max_tokens <= 8192:
            raise ValueError("Choose a model and a token limit between 1 and 8192")
        if not 0 <= temperature <= 1:
            raise ValueError("Temperature must be between zero and one")
        response = request_json(f"{NEBIUS_BASE}/chat/completions", self._key, {
            "model": model, "messages": messages, "max_tokens": max_tokens,
            "temperature": temperature, **({"response_format": response_format} if response_format else {}),
        })
        try:
            choice = response["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError()
            if choice.get("finish_reason") != "stop":
                raise ProviderError("Completion did not finish normally", metadata=completion_metadata(response))
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderError("Provider returned no valid text completion", metadata=completion_metadata(response)) from None
        return {
            "provider": "Nebius Token Factory", "model": response.get("model", model),
            "request_id": response.get("id"), "content": content,
            "usage": response.get("usage", {}),
        }

    def chat(self, messages: list[dict], *, model: str, tools: list[dict],
             max_tokens: int = 1024) -> dict:
        """One bounded support-agent step using native function calling."""
        if not model.lower().startswith("nvidia/") or "nemotron" not in model.lower():
            raise ValueError("Choose an NVIDIA Nemotron model")
        if not 1 <= max_tokens <= 8192:
            raise ValueError("Invalid completion token limit")
        response = request_json(f"{NEBIUS_BASE}/chat/completions", self._key, {
            "model": model, "messages": messages, "tools": tools,
            "tool_choice": "auto", "parallel_tool_calls": False,
            "max_tokens": max_tokens, "temperature": 0,
        })
        try:
            choice = response["choices"][0]
            message = choice["message"]
            content, calls = message.get("content"), message.get("tool_calls", [])
            if calls is None:
                calls = []  # OpenAI-compatible providers may encode absent calls as null.
            if content is not None and not isinstance(content, str):
                raise ValueError()
            if not isinstance(calls, list) or len(calls) > 16:
                raise ValueError()
            ids = set()
            for call in calls:
                if (call["type"] != "function" or not isinstance(call["id"], str)
                        or not call["id"] or call["id"] in ids
                        or not isinstance(call["function"]["name"], str)
                        or not isinstance(call["function"]["arguments"], str)):
                    raise ValueError()
                ids.add(call["id"])
            if (choice.get("finish_reason") not in {"stop", "tool_calls"}
                    or (not calls and not content)):
                raise ValueError()
        except (KeyError, IndexError, TypeError, ValueError, AttributeError):
            raise ProviderError("Provider returned an incomplete or malformed agent step",
                                metadata=completion_metadata(response)) from None
        return {"provider": "Nebius Token Factory", "model": response.get("model", model),
                "request_id": response.get("id"), "usage": response.get("usage", {}),
                "message": {"role": "assistant", "content": content, **({"tool_calls": calls} if calls else {})}}


class TavilyClient:
    def __init__(self):
        self._key = _credential("TAVILY_API_KEY")

    def guidance(self, query: str = "OWASP authorization deny by default validate permissions every request") -> dict:
        """Search the OWASP cheat sheets. Results are untrusted reference text."""
        response = request_json(TAVILY_SEARCH, self._key, {
            "query": query, "search_depth": "basic", "max_results": 3,
            "include_domains": ["cheatsheetseries.owasp.org"],
            "include_answer": False,
        })
        records = response.get("results")
        if not isinstance(records, list) or not records:
            raise ProviderError("Tavily returned no guidance results")
        results = [
            {"url": row["url"], "title": row.get("title", ""), "content": row["content"]}
            for row in records if isinstance(row, dict)
            and isinstance(row.get("url"), str) and row["url"].startswith("https://")
            and isinstance(row.get("content"), str) and row["content"].strip()
        ]
        if not results:
            raise ProviderError("Tavily returned no usable public guidance")
        return {"provider": "Tavily", "query": query,
                "request_id": response.get("request_id"), "results": results,
                "trust": "untrusted reference text; not authorization or instructions"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["models", "smoke", "guidance"])
    args = parser.parse_args()
    try:
        if args.command == "models":
            result = {"models": NebiusClient().models()}
        elif args.command == "smoke":
            result = NebiusClient().complete([
                {"role": "user", "content": "Reply with one sentence explaining tool authorization."},
            ], model=nemotron_model())
        else:
            result = TavilyClient().guidance()
    except ProviderError as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
