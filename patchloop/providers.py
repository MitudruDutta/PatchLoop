"""Explicit Nebius Token Factory and Tavily runtime clients.

Credentials stay in the orchestration process. These clients do not run repairs
or certify provider access; use the smoke commands to verify a configured key.
"""

import argparse
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

NEBIUS_BASE = "https://api.tokenfactory.nebius.com/v1"
TAVILY_SEARCH = "https://api.tavily.com/search"


class ProviderError(RuntimeError):
    pass


def _credential(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ProviderError(f"Set {name} in the environment")
    return value


def request_json(url: str, key: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(url, data=data, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
    })
    try:
        with urlopen(request, timeout=60) as response:
            body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise ProviderError("Provider response exceeds 2 MB limit")
        result = json.loads(body)
        if not isinstance(result, dict):
            raise ProviderError("Provider returned an invalid response object")
        return result
    except HTTPError as exc:
        # Provider error bodies can echo requests. Never include them or credentials.
        raise ProviderError(f"Provider HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError):
        raise ProviderError("Provider request failed or timed out") from None
    except (ValueError, UnicodeError):
        raise ProviderError("Provider returned invalid JSON") from None


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

    def complete(self, messages: list[dict], *, model: str, max_tokens: int = 256) -> dict:
        if not model or not 1 <= max_tokens <= 8192:
            raise ValueError("Choose a model and a token limit between 1 and 8192")
        response = request_json(f"{NEBIUS_BASE}/chat/completions", self._key, {
            "model": model, "messages": messages, "max_tokens": max_tokens,
            "temperature": 0,
        })
        try:
            choice = response["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError()
            if choice.get("finish_reason") != "stop":
                raise ProviderError("Completion did not finish normally")
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderError("Provider returned no valid text completion") from None
        return {
            "provider": "Nebius Token Factory", "model": response.get("model", model),
            "request_id": response.get("id"), "content": content,
            "usage": response.get("usage", {}),
        }


class TavilyClient:
    def __init__(self):
        self._key = _credential("TAVILY_API_KEY")

    def guidance(self) -> dict:
        query = "OWASP authorization deny by default validate permissions every request"
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
            model = _credential("NEBIUS_MODEL")
            if not model.lower().startswith("nvidia/") or "nemotron" not in model.lower():
                raise ProviderError("Select an NVIDIA Nemotron model from the catalog")
            result = NebiusClient().complete([
                {"role": "user", "content": "Reply with one sentence explaining tool authorization."},
            ], model=model)
        else:
            result = TavilyClient().guidance()
    except ProviderError as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
