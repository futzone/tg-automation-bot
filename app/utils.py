from aiogram.types import Message

TG_LIMIT = 4000


def split_text(text: str, limit: int = TG_LIMIT) -> list[str]:
    """Telegram 4096 belgidan uzun xabarni qabul qilmaydi, shuning uchun bo'laklarga ajratamiz."""
    chunks = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


def describe_message(message: Message) -> str:
    """Xabarni LLM tushunadigan matnga aylantiradi."""
    if message.text:
        return message.text
    caption = f" Izoh: {message.caption}" if message.caption else ""
    if message.photo:
        return f"[rasm yubordi]{caption}"
    if message.voice:
        return "[ovozli xabar yubordi, uni tinglay olmaysan]"
    if message.video_note:
        return "[video-xabar (dumaloq) yubordi]"
    if message.video:
        return f"[video yubordi]{caption}"
    if message.document:
        return f"[fayl yubordi: {message.document.file_name}]{caption}"
    if message.sticker:
        return f"[stiker yubordi {message.sticker.emoji or ''}]"
    if message.audio:
        return f"[audio yubordi]{caption}"
    if message.location:
        return "[joylashuv yubordi]"
    if message.contact:
        return f"[kontakt yubordi: {message.contact.first_name}]"
    return "[qo'llab-quvvatlanmaydigan turdagi xabar]"


def chat_label(message: Message) -> str:
    chat = message.chat
    name = chat.full_name or "Noma'lum"
    return f"{name} (@{chat.username})" if chat.username else name
