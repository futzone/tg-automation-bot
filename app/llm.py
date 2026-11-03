"""Anthropic Claude bilan ishlash."""
import logging
import re
from collections.abc import Awaitable, Callable

from anthropic import AsyncAnthropic

log = logging.getLogger(__name__)

_EMOJI_PART = "[\u00a9\u00ae\u203c-\u2bff\u3030\u303d\u3297\u3299\U0001F000-\U0001FAFF]"
_EMOJI_MOD = "[\ufe0f\U0001F3FB-\U0001F3FF]*"
_EMOJI_RE = re.compile(
    f"[\U0001F1E6-\U0001F1FF]{{2}}|{_EMOJI_PART}{_EMOJI_MOD}(?:\u200d{_EMOJI_PART}{_EMOJI_MOD})*"
)
MAX_TOOL_ROUNDS = 3
ToolRunner = Callable[[str, dict], Awaitable[str]]
EMOJI_SYSTEM = (
    "Suhbatdosh messenjerda stiker yubordi. Senga o'sha stikerning emojisi beriladi. "
    "Unga do'stona javob sifatida mos keladigan bitta emoji qaytar. "
    "Faqat bitta emoji yoz, boshqa hech narsa yozma."
)


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
        self._emoji_replies: dict[str, str] = {}

    async def reply(
        self,
        system: str,
        history: list[tuple[str, str]],
        tools: list[dict] | None = None,
        run_tool: ToolRunner | None = None,
    ) -> str:
        messages = normalize_history(history)
        if not messages or messages[-1]["role"] != "user":
            return ""
        return await self._run(system, messages, tools, run_tool)

    async def complete(
        self,
        system: str,
        prompt: str,
        tools: list[dict] | None = None,
        run_tool: ToolRunner | None = None,
    ) -> str:
        """Tarixsiz, bitta so'rov (jadval tahlili, rejalashtirilgan xabar yozish)."""
        return await self._run(system, [{"role": "user", "content": prompt}], tools, run_tool)

    async def _run(self, system: str, messages: list[dict], tools, run_tool) -> str:
        """Model tool chaqirsa, natijasini qaytarib beradi va yakuniy matnni oladi."""
        extra = {"tools": tools} if tools and run_tool else {}
        for _ in range(MAX_TOOL_ROUNDS + 1):
            resp = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=messages,
                **extra,
            )
            log.info("LLM: %s in / %s out tokens", resp.usage.input_tokens, resp.usage.output_tokens)
            if resp.stop_reason != "tool_use" or not extra:
                break
            messages = messages + [{"role": "assistant", "content": resp.content}]
            results = [
                {"type": "tool_result", "tool_use_id": b.id, "content": await run_tool(b.name, b.input)}
                for b in resp.content if b.type == "tool_use"
            ]
            messages.append({"role": "user", "content": results})
        if resp.stop_reason == "max_tokens":
            log.warning("Javob MAX_TOKENS (%s) limitida uzilib qoldi", self.max_tokens)
        return "".join(b.text for b in resp.content if b.type == "text").strip()

    async def pick_emoji(self, emoji: str) -> str:
        """Stiker emojisiga javoban bitta emoji. Har bir emoji uchun model faqat bir marta chaqiriladi."""
        if emoji in self._emoji_replies:
            return self._emoji_replies[emoji]
        try:
            resp = await self.client.messages.create(
                model=self.model,
                max_tokens=20,
                thinking={"type": "disabled"},
                system=EMOJI_SYSTEM,
                messages=[{"role": "user", "content": emoji}],
            )
        except Exception:  # noqa: BLE001
            log.exception("Stiker uchun emoji tanlab bo'lmadi")
            return emoji
        text = "".join(b.text for b in resp.content if b.type == "text")
        found = _EMOJI_RE.search(text)
        self._emoji_replies[emoji] = found[0] if found else emoji
        log.info("LLM (emoji): %s -> %s", emoji, self._emoji_replies[emoji])
        return self._emoji_replies[emoji]
