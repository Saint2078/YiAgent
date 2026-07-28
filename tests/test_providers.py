"""Smoke tests for yiagent.providers (no live network)."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from yiagent.providers import (
    MODELS,
    PROVIDERS,
    TokenMeter,
    chat_completions,
    extract_content,
    model_ok,
    models_public,
    normalize_usage,
    stream_chat,
)
from yiagent.providers.client import LLMAPIError


class UsageTests(unittest.TestCase):
    def test_normalize_openai(self):
        n = normalize_usage({"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})
        self.assertEqual(n["prompt_tokens"], 10)
        self.assertEqual(n["completion_tokens"], 5)
        self.assertEqual(n["total_tokens"], 15)

    def test_normalize_anthropic(self):
        n = normalize_usage({"input_tokens": 3, "output_tokens": 7})
        self.assertEqual(n["prompt_tokens"], 3)
        self.assertEqual(n["completion_tokens"], 7)
        self.assertEqual(n["total_tokens"], 10)

    def test_meter(self):
        m = TokenMeter()
        with m.activate():
            m.add(purpose="t", model="k3", usage={"prompt_tokens": 1, "completion_tokens": 2})
        s = m.summary()
        self.assertEqual(s["calls"], 1)
        self.assertEqual(s["total_tokens"], 3)


class RegistryTests(unittest.TestCase):
    def test_catalog(self):
        self.assertIn("kimi", PROVIDERS)
        self.assertIn("kimi-plan", PROVIDERS)
        self.assertTrue(model_ok("kimi-k2.5"))
        self.assertTrue(model_ok("k3"))
        self.assertFalse(model_ok("no-such-model"))
        pub = models_public()
        self.assertTrue(any(x["id"] == "kimi-k2.5" for x in pub))
        self.assertFalse(any(x["id"] == "k3" for x in pub))
        self.assertTrue(any(x["id"] == "plan/k3" for x in pub))


class ClientTests(unittest.TestCase):
    def test_chat_openai_shape(self):
        fake = {
            "choices": [{"message": {"role": "assistant", "content": "hi"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }

        def fake_post(*_a, **_k):
            return fake

        with patch("yiagent.providers.client._post_json", side_effect=fake_post):
            meter = TokenMeter()
            with meter.activate():
                resp = chat_completions("sk-test-key-xxxxxxxx", "gpt-4o", [{"role": "user", "content": "x"}])
            self.assertEqual(extract_content(resp), "hi")
            self.assertEqual(meter.summary()["calls"], 1)

    def test_chat_anthropic_normalize(self):
        raw = {
            "id": "msg_1",
            "model": "claude-sonnet-4-5",
            "content": [{"type": "text", "text": "hello"}],
            "usage": {"input_tokens": 2, "output_tokens": 1},
        }

        def fake_post(*_a, **_k):
            return raw

        with patch("yiagent.providers.client._post_json", side_effect=fake_post):
            resp = chat_completions(
                "sk-ant-test-xxxxxxxx",
                "claude-sonnet-4-5",
                [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
            )
        self.assertEqual(extract_content(resp), "hello")
        self.assertEqual(resp["_provider"], "anthropic")

    def test_bad_key(self):
        with self.assertRaises(LLMAPIError):
            chat_completions("short", "k3", [{"role": "user", "content": "x"}])

    def test_stream_openai(self):
        lines = [
            b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n',
            b'data: {"choices":[{"delta":{"content":"lo"}}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}\n',
            b"data: [DONE]\n",
        ]

        class FakeResp:
            def __init__(self):
                self._i = 0

            def readline(self):
                if self._i >= len(lines):
                    return b""
                line = lines[self._i]
                self._i += 1
                return line

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with patch("urllib.request.urlopen", return_value=FakeResp()):
            chunks = list(
                stream_chat(
                    "sk-test-key-xxxxxxxx",
                    "gpt-4o",
                    [{"role": "user", "content": "x"}],
                )
            )
        self.assertEqual("".join(chunks), "Hello")


if __name__ == "__main__":
    unittest.main()
