# Muammolar va yechimlar

Avval ikkita narsani tekshiring: botda `/status` va loglar (`journalctl -u aibot -n 50` yoki terminaldagi chiqish).

## Bot suhbatdoshlarga javob bermayapti

Eng ko'p uchraydigan sabablar, ehtimoli bo'yicha:

| Sabab | Qanday bilish | Yechim |
|---|---|---|
| "Reply to messages" ruxsati o'chiq | `/status` da "ulangan, lekin javob berish ruxsati yo'q ⚠️"; logda `'Reply to messages' ruxsati yo'q` | Settings → Business → Chat Automation → botingiz → ruxsatni yoqing |
| Bot ishlamayapti | `systemctl is-active aibot` `inactive` qaytaradi | `sudo systemctl start aibot`, logdagi xatoni o'qing |
| Bot akkauntga ulanmagan | `/status` da "ulanmagan" | [setup.md](setup.md#5-botni-akkauntingizga-ulang) dagi 5-qadam |
| Chatda o'zingiz yozgansiz | Logda `Egasi chat ... ga yozdi, N daqiqa pauza` | `PAUSE_MINUTES` o'tishini kuting yoki `/resume` |
| Bot `/pause` qilingan | `/status` da "⏸ to'xtatilgan" | `/resume` |
| Chat **Excluded chats** da | Bu chatdan logda hech narsa yo'q | Chat Automation sozlamalaridan olib tashlang |
| Suhbatdosh so'kingani uchun cheklangan | `/status` da cheklangan chatlar soni 0 dan katta | O'sha chatda o'zingiz yozing yoki `/resume` |
| Model javob bermaslikni tanladi | Logda `LLM: ... in / N out` bor, lekin xabar ketmagan | Bu `[SKIP]`: "ok", "rahmat" kabi xabarlarga javob berilmaydi |

## Bot ishga tushmayapti

- **`❌ .env faylida ... ko'rsatilmagan`** — majburiy o'zgaruvchi bo'sh: `BOT_TOKEN`, `OWNER_ID`, `OWNER_NAME`, `ANTHROPIC_API_KEY`.
- **`Unauthorized`** — `BOT_TOKEN` noto'g'ri yoki BotFather'da qayta yaratilgan.
- **`⚠️ BotFather'da Business Mode yoqilmagan!`** — bot ishlaydi, lekin akkauntga ulab bo'lmaydi. BotFather → `/mybots` → Bot Settings → Business Mode.

## `Conflict: terminated by other getUpdates request`

Bitta token bilan ikkita nusxa ishlayapti (masalan, serverda va kompyuteringizda). Bittasini to'xtating.

## Javob o'rtasida uzilib qoldi

Logda `Javob MAX_TOKENS (...) limitida uzilib qoldi` bo'lsa, `.env` da `MAX_TOKENS` ni oshiring (standart 2000). Modelning "o'ylash" tokenlari ham shu chegaraga kiradi.

## "⚠️ ... chatiga javob berishda xato" bildirishnomasi keldi

Bildirishnomada xato turi yozilgan bo'ladi:

- **`AuthenticationError`** — `ANTHROPIC_API_KEY` noto'g'ri.
- **`RateLimitError` yoki kredit haqidagi xato** — Anthropic hisobidagi limit yoki mablag' tugagan.
- **`NotFoundError`** — `ANTHROPIC_MODEL` da mavjud bo'lmagan model nomi.
- **Telegram xatosi** — odatda ruxsat olib tashlangan yoki ulanish uzilgan; `/status` ni tekshiring.

## Bot menga bildirishnoma yubormayapti

Botga hech bo'lmaganda bir marta `/start` yuborgan bo'lishingiz kerak. `OWNER_ID` to'g'ri ekanini ham tekshiring: noto'g'ri bo'lsa, bot sizni egasi deb tanimaydi va buyruqlaringizga "Bu shaxsiy yordamchi bot" deb javob beradi.

## Bot begunoh xabarni so'kinish deb oldi

`badwords.txt` dagi ba'zi so'zlar kundalik nutqda oddiy ma'noda ham ishlatiladi. Kerakmas so'z oldiga `# ` qo'yib o'chiring va botni qayta ishga tushiring. Cheklangan suhbatdoshni ochish uchun o'sha chatda o'zingiz yozing. Batafsil: [configuration.md](configuration.md#sokinish-filtri).

## Bot eski holatni aytyapti ("avtobusda")

Muddatsiz o'rnatilgan holat o'zi o'chmaydi. `/free` bosing va keyingi safar muddat bilan o'rnating: `/bus 40`.

## Bot noto'g'ri yoki ortiqcha narsa aytyapti

1. `/prompt` bilan modelga nima yuborilayotganini ko'ring.
2. Aniqroq qoida qo'shing (`/add ...`) va `/test <xabar>` bilan sinang.
3. Eski yozishmalar chalg'itayotgan bo'lsa, `/forget` bilan tarixni tozalang.
