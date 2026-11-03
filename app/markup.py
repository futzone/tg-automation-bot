"""Model yozgan Markdown'ni Telegram HTML'iga aylantirish (**qalin**, `kod`, *kursiv*, ~~chizilgan~~,
[havola](url), # sarlavha, - ro'yxat). `kod` Telegram'da bosilganda nusxa olinadi."""
import html
import re

_CODE_BLOCK = re.compile(r"```(?:[\w+-]*\n)?(.*?)```", re.DOTALL)
_CODE = re.compile(r"`([^`\n]+)`")
_LINK = re.compile(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)")
_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.DOTALL)
_ITALIC = re.compile(r"(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])")
_STRIKE = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~")
_HEADING = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
_BULLET = re.compile(r"^(\s*)[-*]\s+", re.MULTILINE)


def md_to_html(text: str) -> str:
    slots: list[str] = []

    def keep(fragment: str) -> str:
        slots.append(fragment)
        return f"\x00{len(slots) - 1}\x00"

    # Kod ichidagi belgilarga boshqa qoidalar tegmasligi uchun avval ajratib olamiz
    text = _CODE_BLOCK.sub(lambda m: keep(f"<pre>{html.escape(m[1].strip(), quote=False)}</pre>"), text)
    text = _CODE.sub(lambda m: keep(f"<code>{html.escape(m[1], quote=False)}</code>"), text)
    text = _LINK.sub(
        lambda m: keep(f'<a href="{html.escape(m[2])}">{html.escape(m[1], quote=False)}</a>'), text
    )
    text = html.escape(text, quote=False)
    text = _HEADING.sub(r"<b>\1</b>", text)
    text = _BULLET.sub(r"\1• ", text)
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _ITALIC.sub(r"<i>\1</i>", text)
    text = _STRIKE.sub(r"<s>\1</s>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: slots[int(m[1])], text)
