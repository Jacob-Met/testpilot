"""OpenAI-compatible chat client interface, a deterministic scripted stub, and
planner/editor model routing.

Nebius Token Factory exposes an OpenAI-compatible API. Per the Token Factory
quickstart (https://docs.tokenfactory.nebius.com/quickstart, retrieved
2026-10-04) the client is configured with::

    base_url="https://api.tokenfactory.nebius.com/v1/"
    api_key=os.environ.get("NEBIUS_API_KEY")

and requests go to ``POST {base_url}chat/completions``. Swapping the scripted
stub for Token Factory is therefore a backend + base_url + key change (see
:func:`make_client`).

Default model IDs are NVIDIA Nemotron models named in the Token Factory docs
(https://docs.tokenfactory.nebius.com/august-2026-deprecation-notice lists
``nvidia/nemotron-3-super-120b-a12b`` and ``nvidia/Nemotron-3_5-Lightning`` as
current replacement models). Confirm both in the live model catalog before use;
override via TESTPILOT_PLANNER_MODEL / TESTPILOT_EDITOR_MODEL.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

TOKEN_FACTORY_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
TOKEN_FACTORY_DOCS = "https://docs.tokenfactory.nebius.com/quickstart"
DEFAULT_PLANNER_MODEL = "nvidia/nemotron-3-super-120b-a12b"
DEFAULT_EDITOR_MODEL = "nvidia/Nemotron-3_5-Lightning"


class ModelError(RuntimeError):
    pass


class ScriptExhausted(ModelError):
    pass


@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int
    estimated: bool = False

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class ChatResponse:
    content: str
    model: str
    usage: Usage
    raw: dict | None = None


class ChatClient(Protocol):
    def chat(self, model: str, messages: list[dict], *, temperature: float = 0.2,
             max_tokens: int | None = None) -> ChatResponse: ...


def estimate_tokens(text: str) -> int:
    """Rough chars/4 token estimate; used only when no API usage is available."""
    return max(1, (len(text) + 3) // 4)


def _messages_text(messages: list[dict]) -> str:
    return "\n".join(str(m.get("content", "")) for m in messages)


# --------------------------------------------------------------------------- stub
class ScriptedModel:
    """Deterministic stand-in for an LLM: replays canned responses in order.

    Every call is recorded in ``self.calls`` (model, messages) so tests can
    assert on routing and prompts. Token usage is a deterministic estimate.
    """

    def __init__(self, responses: list[str] | Callable[[str, list[dict]], str], name: str = "scripted"):
        self._responses = responses if callable(responses) else list(responses)
        self.name = name
        self.calls: list[tuple[str, list[dict]]] = []

    @classmethod
    def from_dir(cls, path: str | Path) -> "ScriptedModel":
        files = sorted(p for p in Path(path).iterdir() if p.suffix in (".md", ".txt") and p.is_file())
        if not files:
            raise ModelError(f"no *.md/*.txt responses in script dir {path}")
        return cls([p.read_text(encoding="utf-8") for p in files], name=f"scripted:{Path(path).name}")

    def chat(self, model: str, messages: list[dict], *, temperature: float = 0.2,
             max_tokens: int | None = None) -> ChatResponse:
        self.calls.append((model, messages))
        if callable(self._responses):
            content = self._responses(model, messages)
        else:
            if not self._responses:
                raise ScriptExhausted(f"{self.name}: script exhausted after {len(self.calls) - 1} calls")
            content = self._responses.pop(0)
        usage = Usage(estimate_tokens(_messages_text(messages)), estimate_tokens(content), estimated=True)
        return ChatResponse(content=content, model=model, usage=usage)


# --------------------------------------------------------------------- real client
Transport = Callable[[str, dict, bytes, float], dict]


def _urllib_transport(url: str, headers: dict, body: bytes, timeout: float) -> dict:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https URL from config)
        return json.loads(resp.read().decode("utf-8"))


class OpenAICompatClient:
    """Minimal stdlib client for any OpenAI-compatible ``/chat/completions`` API."""

    RETRY_STATUS = {429, 500, 502, 503, 504}

    def __init__(self, base_url: str = TOKEN_FACTORY_BASE_URL, api_key: str | None = None, *,
                 timeout: float = 120.0, retries: int = 2, transport: Transport | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        if not api_key:
            raise ModelError("API key missing (set NEBIUS_API_KEY)")
        self.base_url = base_url.rstrip("/") + "/"
        self._api_key = api_key
        self.timeout = timeout
        self.retries = retries
        self._transport = transport or _urllib_transport
        self._sleep = sleep

    def chat(self, model: str, messages: list[dict], *, temperature: float = 0.2,
             max_tokens: int | None = None) -> ChatResponse:
        payload: dict = {"model": model, "messages": messages, "temperature": temperature}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        headers = {"Content-Type": "application/json", "Accept": "application/json",
                   "Authorization": f"Bearer {self._api_key}"}
        url = self.base_url + "chat/completions"
        body = json.dumps(payload).encode("utf-8")
        attempt = 0
        while True:
            try:
                data = self._transport(url, headers, body, self.timeout)
                break
            except urllib.error.HTTPError as e:
                if e.code in self.RETRY_STATUS and attempt < self.retries:
                    attempt += 1
                    self._sleep(2 ** attempt)
                    continue
                detail = e.read().decode("utf-8", "replace")[:500] if hasattr(e, "read") else ""
                raise ModelError(f"HTTP {e.code} from {url}: {detail}") from e
            except urllib.error.URLError as e:
                if attempt < self.retries:
                    attempt += 1
                    self._sleep(2 ** attempt)
                    continue
                raise ModelError(f"connection error to {url}: {e.reason}") from e
        try:
            content = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            raise ModelError(f"unexpected response shape: {str(data)[:300]}") from e
        u = data.get("usage") or {}
        if "prompt_tokens" in u:
            usage = Usage(int(u.get("prompt_tokens", 0)), int(u.get("completion_tokens", 0)))
        else:
            usage = Usage(estimate_tokens(_messages_text(messages)), estimate_tokens(content), estimated=True)
        return ChatResponse(content=content, model=data.get("model", model), usage=usage, raw=data)


# ------------------------------------------------------------------------ routing
@dataclass
class RoutingConfig:
    """Which model does which job, plus per-model prices for the cost ledger.

    ``prices`` maps model id -> (USD per 1M input tokens, USD per 1M output
    tokens). It is empty by default: fill it from the Token Factory pricing page
    (or TESTPILOT_PRICES='{"model": [in, out]}') — TestPilot does not guess.
    """

    planner_model: str = DEFAULT_PLANNER_MODEL
    editor_model: str = DEFAULT_EDITOR_MODEL
    prices: dict[str, tuple[float, float]] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env: dict | None = None) -> "RoutingConfig":
        env = os.environ if env is None else env
        prices = {k: (float(v[0]), float(v[1])) for k, v in json.loads(env.get("TESTPILOT_PRICES", "{}")).items()}
        return cls(
            planner_model=env.get("TESTPILOT_PLANNER_MODEL", DEFAULT_PLANNER_MODEL),
            editor_model=env.get("TESTPILOT_EDITOR_MODEL", DEFAULT_EDITOR_MODEL),
            prices=prices,
        )

    def model_for(self, role: str) -> str:
        if role == "planner":
            return self.planner_model
        if role in ("editor", "repair"):
            return self.editor_model
        raise ValueError(f"unknown role {role!r}")

    def cost(self, model: str, usage: Usage) -> float:
        pin, pout = self.prices.get(model, (0.0, 0.0))
        return usage.prompt_tokens * pin / 1e6 + usage.completion_tokens * pout / 1e6

    def has_price(self, model: str) -> bool:
        return model in self.prices


def make_client(backend: str | None = None, *, script: str | Path | None = None,
                base_url: str | None = None, api_key: str | None = None,
                env: dict | None = None) -> ChatClient:
    """Build a client. ``backend`` is ``scripted`` (default) or ``tokenfactory``/``openai``."""
    env = os.environ if env is None else env
    backend = (backend or env.get("TESTPILOT_BACKEND") or "scripted").lower()
    if backend == "scripted":
        script = script or env.get("TESTPILOT_SCRIPT")
        if not script:
            raise ModelError("scripted backend needs --script DIR (or TESTPILOT_SCRIPT)")
        return ScriptedModel.from_dir(script)
    if backend in ("tokenfactory", "openai"):
        return OpenAICompatClient(
            base_url=base_url or env.get("TESTPILOT_BASE_URL") or TOKEN_FACTORY_BASE_URL,
            api_key=api_key or env.get("NEBIUS_API_KEY"),
        )
    raise ModelError(f"unknown backend {backend!r}")
