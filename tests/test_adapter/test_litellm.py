import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adaptive_loop.adapter.litellm import LiteLLMAdapter, AdaptRequest, AdaptResponse
from adaptive_loop.exceptions import AdapterError


def _mock_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class TestAdaptRequest:
    def test_fields(self):
        req = AdaptRequest(
            user_message="Find max tokens",
            system_message="You are helpful.",
        )
        assert req.user_message == "Find max tokens"
        assert req.system_message == "You are helpful."


class TestLiteLLMAdapter:
    def test_init_defaults(self):
        adapter = LiteLLMAdapter()
        assert adapter.model == "gpt-4o-mini"

    def test_init_model(self):
        adapter = LiteLLMAdapter(model="anthropic/claude-3-haiku")
        assert adapter.model == "anthropic/claude-3-haiku"

    @pytest.mark.asyncio
    async def test_send_success(self):
        adapter = LiteLLMAdapter(model="gpt-4o")
        mock_llm = AsyncMock(return_value=_mock_response("max_tokens: 4096"))
        with patch("litellm.acompletion", mock_llm):
            req = AdaptRequest(user_message="Find the field")
            result = await adapter.send(req)
            assert result.raw == "max_tokens: 4096"

    @pytest.mark.asyncio
    async def test_send_timeout_raises(self):
        adapter = LiteLLMAdapter(model="gpt-4o")
        async def slow():
            await asyncio.sleep(10)
        with patch("litellm.acompletion", AsyncMock(side_effect=slow)):
            req = AdaptRequest(user_message="test")
            with pytest.raises(AdapterError, match="timeout"):
                await adapter.send(req, timeout=0.05)

    @pytest.mark.asyncio
    async def test_send_system_message(self):
        adapter = LiteLLMAdapter(model="gpt-4o")
        mock_llm = AsyncMock(return_value=_mock_response("ok"))
        with patch("litellm.acompletion", mock_llm):
            req = AdaptRequest(
                user_message="test",
                system_message="You are helpful.",
            )
            result = await adapter.send(req)
            call_args = mock_llm.call_args
            assert "messages" in call_args.kwargs
            msgs = call_args.kwargs["messages"]
            assert any(m.get("role") == "system" for m in msgs)
            assert any(m.get("role") == "user" for m in msgs)
