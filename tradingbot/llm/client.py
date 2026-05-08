from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import requests

from ..config import LLMConfig


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    def complete(self, *, instructions: str, input_text: str) -> str:
        ...


@dataclass(frozen=True)
class OpenAIResponsesClient:
    config: LLMConfig

    def complete(self, *, instructions: str, input_text: str) -> str:
        if not self.config.api_key:
            raise LLMError("OPENAI_API_KEY is not configured")

        response = requests.post(
            f"{self.config.base_url.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.model,
                "instructions": instructions,
                "input": input_text,
                "max_output_tokens": self.config.max_output_tokens,
            },
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        text = _extract_response_text(payload)
        if not text:
            raise LLMError(f"OpenAI response did not include text output: {payload}")
        return text.strip()


@dataclass(frozen=True)
class DeepSeekChatClient:
    config: LLMConfig

    def complete(self, *, instructions: str, input_text: str) -> str:
        if not self.config.api_key:
            raise LLMError("DEEPSEEK_API_KEY is not configured")

        response = requests.post(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": input_text},
                ],
                "max_tokens": self.config.max_output_tokens,
                "temperature": 0.2,
            },
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        text = _extract_chat_text(payload)
        if not text:
            raise LLMError(f"DeepSeek response did not include text output: {payload}")
        return text.strip()


def _extract_response_text(payload: dict[str, object]) -> str:
    if isinstance(payload.get("output_text"), str):
        return str(payload["output_text"])

    parts: list[str] = []
    output = payload.get("output")
    if not isinstance(output, list):
        return ""
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if isinstance(block.get("text"), str):
                parts.append(str(block["text"]))
    return "\n".join(parts)


def _extract_chat_text(payload: dict[str, object]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return str(content) if isinstance(content, str) else ""


def build_llm_client(config: LLMConfig) -> LLMClient | None:
    if not config.enabled:
        return None
    if config.provider == "deepseek":
        return DeepSeekChatClient(config)
    if config.provider != "openai":
        raise LLMError(f"unsupported llm provider: {config.provider}")
    return OpenAIResponsesClient(config)
