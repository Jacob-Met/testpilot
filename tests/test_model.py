import io
import json
import urllib.error

import pytest

from testpilot.model import (DEFAULT_EDITOR_MODEL, DEFAULT_PLANNER_MODEL, TOKEN_FACTORY_BASE_URL, ModelError,
                             OpenAICompatClient, RoutingConfig, ScriptedModel, ScriptExhausted, Usage, make_client)

MSG = [{"role": "user", "content": "hello"}]


def test_scripted_replays_in_order_and_records():
    m = ScriptedModel(["one", "two"])
    assert m.chat("a", MSG).content == "one"
    r = m.chat("b", MSG)
    assert r.content == "two" and r.model == "b" and r.usage.estimated
    assert [c[0] for c in m.calls] == ["a", "b"]
    with pytest.raises(ScriptExhausted):
        m.chat("a", MSG)


def test_scripted_callable_and_dir(tmp_path):
    m = ScriptedModel(lambda model, msgs: model.upper())
    assert m.chat("x", MSG).content == "X"
    (tmp_path / "02_b.md").write_text("B")
    (tmp_path / "01_a.md").write_text("A")
    (tmp_path / "notes.json").write_text("{}")
    d = ScriptedModel.from_dir(tmp_path)
    assert [d.chat("m", MSG).content for _ in range(2)] == ["A", "B"]


def test_openai_client_request_shape_and_usage():
    seen = {}

    def transport(url, headers, body, timeout):
        seen.update(url=url, headers=headers, body=json.loads(body))
        return {"model": "nvidia/x", "choices": [{"message": {"content": "hi"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 3}}

    c = OpenAICompatClient(api_key="k", transport=transport)
    r = c.chat("nvidia/x", MSG, max_tokens=50)
    assert seen["url"] == "https://api.tokenfactory.nebius.com/v1/chat/completions"
    assert seen["headers"]["Authorization"] == "Bearer k"
    assert seen["body"] == {"model": "nvidia/x", "messages": MSG, "temperature": 0.2, "max_tokens": 50}
    assert r.content == "hi" and r.usage == Usage(12, 3) and not r.usage.estimated


def test_openai_client_retries_then_fails():
    calls, sleeps = [], []

    def transport(url, headers, body, timeout):
        calls.append(1)
        raise urllib.error.HTTPError(url, 429, "slow down", {}, io.BytesIO(b"rate"))

    c = OpenAICompatClient(api_key="k", transport=transport, retries=2, sleep=sleeps.append)
    with pytest.raises(ModelError, match="HTTP 429"):
        c.chat("m", MSG)
    assert len(calls) == 3 and sleeps == [2, 4]


def test_openai_client_bad_shape_and_missing_key():
    c = OpenAICompatClient(api_key="k", transport=lambda *a: {"oops": 1})
    with pytest.raises(ModelError, match="unexpected"):
        c.chat("m", MSG)
    with pytest.raises(ModelError, match="NEBIUS_API_KEY"):
        OpenAICompatClient(api_key=None)


def test_routing_and_cost():
    r = RoutingConfig.from_env({"TESTPILOT_PRICES": json.dumps({"big": [1.0, 2.0]}),
                                "TESTPILOT_PLANNER_MODEL": "big"})
    assert r.model_for("planner") == "big"
    assert r.model_for("editor") == r.model_for("repair") == DEFAULT_EDITOR_MODEL
    assert r.cost("big", Usage(1_000_000, 500_000)) == pytest.approx(2.0)
    assert r.cost("unpriced", Usage(10, 10)) == 0.0 and not r.has_price("unpriced")
    with pytest.raises(ValueError):
        r.model_for("judge")
    assert RoutingConfig().planner_model == DEFAULT_PLANNER_MODEL


def test_make_client(tmp_path):
    (tmp_path / "01.md").write_text("x")
    assert isinstance(make_client("scripted", script=tmp_path, env={}), ScriptedModel)
    c = make_client("tokenfactory", env={"NEBIUS_API_KEY": "k"})
    assert isinstance(c, OpenAICompatClient) and c.base_url == TOKEN_FACTORY_BASE_URL
    c2 = make_client("openai", env={"NEBIUS_API_KEY": "k", "TESTPILOT_BASE_URL": "http://localhost:8000/v1"})
    assert c2.base_url == "http://localhost:8000/v1/"
    with pytest.raises(ModelError):
        make_client("scripted", env={})
    with pytest.raises(ModelError):
        make_client("nope", env={})
