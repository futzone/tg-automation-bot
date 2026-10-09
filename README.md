# Telegram AI javobchi (Chat Automation)

Siz offline bo'lganingizda shaxsiy Telegram chatlaringizga **sizning nomingizdan** Claude orqali javob beradigan bot.
Qoidalar va bilimlarni botning o'z chatida o'rgatasiz.

## Imkoniyatlar

- Telegram **Chat Automation** (Business) orqali shaxsiy chatlarga javob beradi
- Qoidalar, "o'zim haqimda" tavsifi va bilim bazasi (.txt / .md fayllar) botning o'z chatida boshqariladi
- Siz chatda o'zingiz yozsangiz, bot o'sha chatda `PAUSE_MINUTES` daqiqa jim turadi
- Suhbatdosh ketma-ket bir nechta xabar yozsa, hammasini o'qib, bitta javob beradi
- `ok`, `rahmat`, stiker kabi xabarlarga javob bermaydi
- Muhim yoki shoshilinch xabarlar haqida sizga botda bildirishnoma yuboradi
- So'kingan suhbatdoshni bir marta ogohlantiradi, takrorlansa unga javob berishni to'xtatadi (`badwords.txt`)
- Bitta chatga 10 daqiqada ko'pi bilan 5 ta AI javob beradi, undan keyin AI siz tayyor matn yuboradi (`RATE_LIMIT_*`). Siz biror chatda yozsangiz, limit tozalanadi
- Faqat sizning akkauntingiz bilan ishlaydi. Boshqalar botni o'z akkauntiga ulasa, e'tiborsiz qoldiriladi.

## O'rnatish (5 daqiqa)

1. **BotFather:** `/newbot` → token oling → `/mybots` → bot → *Bot Settings* → *Business Mode* → **Turn on**
2. **Telegram ID:** @userinfobot ga yozib, ID'ingizni oling
3. **Anthropic kalit:** https://console.anthropic.com → API Keys
4. `.env` faylini to'ldiring: `BOT_TOKEN`, `OWNER_ID`, `ANTHROPIC_API_KEY`
5. Ishga tushiring:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

6. Telegram'da botga **/start** bosing (bildirishnomalar kelishi uchun shart)
7. **Settings → Business → Chat Automation** → bot username'ini kiriting → ruxsat bering ("Reply to messages" yoqilgan bo'lsin)
8. Oila, yaqinlar kabi chatlarni **Excluded chats** ga qo'shing

## Boshqaruv buyruqlari (botning o'z chatida)

| Buyruq | Vazifasi |
|---|---|
| `/add <matn>` yoki oddiy matn | Qoida qo'shish |
| `/rules`, `/del <raqam>` | Qoidalarni ko'rish / o'chirish |
| `/persona <matn>` | O'zingiz haqingizda tavsif |
| .txt / .md fayl yuborish | Bilim bazasiga qo'shish |
| `/knowledge`, `/kdel <raqam>` | Bilimlarni ko'rish / o'chirish |
| `/bus`, `/sleep`, `/work`, `/taxi`, `/family`... (jami 22 ta, ro'yxat: `/statuses`) | Hozirgi holatingizni o'rnatish (bot suhbatdoshga shuni aytadi) |
| `/bus 40`, `/sleep 8h`, `/bus 40 <izoh>` | Holatni muddat (daqiqa yoki `h` soat) va izoh bilan o'rnatish |
| `/set [muddat] <matn>`, `/free` | Erkin holat / holatni o'chirish |
| `/statuses`, `/newstatus <nom> <tavsif>`, `/delstatus <nom>` | Holatlar ro'yxati, o'z holatingizni qo'shish / o'chirish |
| `/test <xabar>` | Javobni hech kimga yubormasdan sinash |
| `/pause`, `/resume` | Botni to'xtatish / yoqish |
| `/status`, `/prompt`, `/forget` | Holat, to'liq prompt, tarixni tozalash |

## Boshlash uchun namuna qoidalar

```
/persona Men Zamon, Toshkentdagi dasturchi va team lead. Flutter, backend va AI yechimlar bilan ishlayman.
/add Narx yoki hamkorlik haqida so'rashsa, qisqacha talablarni so'ra va Zamon o'zi bog'lanishini ayt
/add Telefon raqam, manzil va shaxsiy ma'lumotlarni hech kimga berma
/add Uchrashuv vaqtini o'zing tasdiqlama, faqat qulay vaqtlarni so'rab ol
```

## Serverda 24/7 ishlatish

`aibot.service` faylidagi ko'rsatmalarga qarang (systemd). Bot polling rejimida ishlaydi, shuning uchun domen va SSL kerak emas.

## Tuzilma

```
bot.py            — kirish nuqtasi
app/config.py     — .env sozlamalari
app/db.py         — SQLite (qoidalar, bilimlar, tarix, pauzalar)
app/llm.py        — Claude API
app/prompt.py     — system prompt va [SKIP]/[NOTIFY] tahlili
app/business.py   — shaxsiy chatlarga javob berish
app/status.py     — holat shablonlari (/bus, /sleep...)
app/moderation.py — so'kinish filtri (badwords.txt)
app/owner.py      — boshqaruv paneli
```
