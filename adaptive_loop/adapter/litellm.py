import asyncio
from dataclasses import dataclass
from typing import Optional

import litellm

from adaptive_loop.exceptions import AdapterError


@dataclass
class AdaptRequest:
    user_message: str
    system_message: Optional[str] = None


@dataclass
class AdaptResponse:
    raw: str


class LiteLLMAdapter:
    def __init__(self, model: str = "gpt-4o-mini", **litellm_kwargs):
        self.model = model
        self._kwargs = litellm_kwargs

    async def send(
        self,
        request: AdaptRequest,
        timeout: float = 30.0,
    ) -> AdaptResponse:
        messages = []
        if request.system_message:
            messages.append({"role": "system", "content": request.system_message})
        messages.append({"role": "user", "content": request.user_message})

        try:
            response = await asyncio.wait_for(
                litellm.acompletion(
                    model=self.model,
                    messages=messages,
                    **self._kwargs,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise AdapterError(f"AI request timed out after {timeout}s")
        except Exception as e:
            raise AdapterError(f"AI request failed: {e}") from e

        raw = response.choices[0].message.content
        return AdaptResponse(raw=raw)
