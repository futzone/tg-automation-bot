"""Anthropic Claude bilan ishlash."""
import logging

from anthropic import AsyncAnthropic

log = logging.getLogger(__name__)


def normalize_history(history: list[tuple[str, str]]) -> list[dict]:
    """API talabi: xabarlar 'user' bilan boshlanib, rollar navbatma-navbat kelishi kerak.
    Ketma-ket bir xil roldagi xabarlar bittaga birlashtiriladi."""
    messages: list[dict] = []
    for role, content in history:
        if not content.strip():
            continue
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n" + content
        else:
            messages.append({"role": role, "content": content})
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    return messages


class LLM:
    def __init__(self, api_key: str, model: str, max_tokens: int):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    async def reply(self, system: str, history: list[tuple[str, str]]) -> str:
        messages = normalize_history(history)
        if not messages or messages[-1]["role"] != "user":
            return ""
        resp = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        if resp.stop_reason == "max_tokens":
            log.warning("Javob MAX_TOKENS (%s) limitida uzilib qoldi", self.max_tokens)
        log.info("LLM: %s in / %s out tokens", resp.usage.input_tokens, resp.usage.output_tokens)
        return text
