# O'rnatish

Noldan ishlab turgan botgacha taxminan 10 daqiqa.

## Talablar

- **Python 3.10 yoki yangiroq**
- **Telegram Premium.** Chat Automation Telegram Business tarkibiga kiradi va faqat Premium akkauntlarda mavjud.
- **Anthropic API kaliti** va hisobda mablag' ([console.anthropic.com](https://console.anthropic.com)). Xarajat haqida: [configuration.md](configuration.md#xarajat).

## 1. Bot yarating

1. Telegram'da [@BotFather](https://t.me/BotFather) ga yozing: `/newbot`. Nom va username bering.
2. BotFather bergan **token**ni saqlab qo'ying.
3. `/mybots` → botingiz → **Bot Settings** → **Business Mode** → **Turn on**.

Business Mode yoqilmasa, botni akkauntingizga ulab bo'lmaydi. Bot ishga tushganda buni tekshiradi va logga ogohlantirish yozadi.

## 2. Telegram ID'ingizni bilib oling

[@userinfobot](https://t.me/userinfobot) ga istalgan xabar yuboring, u raqamli ID'ingizni qaytaradi. Bot faqat shu ID egasiga xizmat qiladi.

## 3. Loyihani o'rnating

```bash
git clone https://github.com/futzone/tg-automation-bot.git
cd tg-automation-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` faylida to'rtta majburiy qiymatni to'ldiring:

```ini
BOT_TOKEN=123456789:AA...          # BotFather'dan
OWNER_ID=123456789                 # @userinfobot'dan
OWNER_NAME=Ali                     # bot sizni suhbatdoshlarga shu nom bilan ataydi
ANTHROPIC_API_KEY=sk-ant-...       # console.anthropic.com → API Keys
```

Qolgan sozlamalarning standart qiymatlari bor: [configuration.md](configuration.md).

## 4. Ishga tushiring

```bash
python bot.py
```

Logda shunga o'xshash qator chiqishi kerak:

```
Bot @sizning_botingiz ishga tushdi (model: claude-haiku-5-5, so'kinish filtri: 248 ta)
```

## 5. Botni akkauntingizga ulang

1. Botingizga **/start** yuboring. Busiz bot sizga bildirishnoma yubora olmaydi.
2. Telegram → **Settings → Business → Chat Automation** (Telegram Business → Chatbots).
3. Bot username'ini kiriting va tanlang.
4. Ruxsatlar ichida **Reply to messages** yoqilganiga ishonch hosil qiling. Usiz bot xabarlarni o'qiydi, lekin javob bera olmaydi.
5. Bot javob bermasligi kerak bo'lgan chatlarni (oila, yaqinlar) **Excluded chats** ga qo'shing.

Ulangach bot sizga "✅ Bot akkauntingizga ulandi va javob bera oladi" deb yozadi.

## 6. Tekshiring

Botning o'z chatida:

```
/status
```

`Akkaunt: ulangan ✅` chiqishi kerak. Keyin javobni hech kimga yubormasdan sinab ko'ring:

```
/test Salom, bugun bo'shmisiz?
```

Haqiqiy sinov uchun boshqa akkauntdan o'zingizga yozing. Sinov paytida o'z akkauntingizdan javob yozmang: bot buni "egasi o'zi javob berdi" deb tushunadi va `PAUSE_MINUTES` daqiqa jim turadi.

## 7. Botni o'rgating

Birinchi kun uchun namuna:

```
/persona Men Ali, Toshkentdagi dizayner. Brending va veb-dizayn bilan shug'ullanaman.
/add Narx yoki hamkorlik haqida so'rashsa, qisqacha talablarni so'ra va o'zim bog'lanishimni ayt
/add Telefon raqam, manzil va shaxsiy ma'lumotlarni hech kimga berma
/add Uchrashuv vaqtini o'zing tasdiqlama, faqat qulay vaqtlarni so'rab ol
```

Narxlar, xizmatlar yoki FAQ bo'lsa, `.txt` yoki `.md` fayl qilib botga yuboring.

Keyingi qadam: botni doimiy ishlatish uchun [serverga joylang](deployment.md).
