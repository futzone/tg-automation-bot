# Sozlamalar

Sozlamalar loyiha ildizidagi `.env` faylidan o'qiladi. O'zgartirgandan keyin botni qayta ishga tushiring.

## `.env` o'zgaruvchilari

| O'zgaruvchi | Standart | Vazifasi |
|---|---|---|
| `BOT_TOKEN` | majburiy | BotFather bergan token |
| `OWNER_ID` | majburiy | Sizning raqamli Telegram ID'ingiz |
| `OWNER_NAME` | majburiy | Bot sizni suhbatdoshlarga shu nom bilan ataydi |
| `ANTHROPIC_API_KEY` | majburiy | Anthropic API kaliti |
| `ANTHROPIC_MODEL` | `claude-haiku-5-5` | Javob yozadigan model |
| `MAX_TOKENS` | `2000` | Bitta javob uchun chiqish tokenlari chegarasi |
| `HISTORY_LIMIT` | `20` | Har bir chatdan kontekst sifatida yuboriladigan oxirgi xabarlar soni |
| `PAUSE_MINUTES` | `30` | Chatda o'zingiz yozganingizdan keyin bot shu chatda necha daqiqa jim turadi |
| `DEBOUNCE_SECONDS` | `4` | Suhbatdosh ketma-ket yozsa, javobdan oldin necha soniya kutish |
| `RATE_LIMIT_COUNT` | `5` | Bitta chatga `RATE_LIMIT_MINUTES` ichida ko'pi bilan nechta AI javob |
| `RATE_LIMIT_MINUTES` | `10` | Limit oynasi, daqiqada |
| `RATE_LIMIT_MESSAGE` | bo'sh | Limit tugaganda yuboriladigan matn. Bo'sh bo'lsa: "*{ism}* hozir band. Xabaringizni qoldiring, bo'shaganda o'zi javob beradi." |
| `TIMEZONE` | `Asia/Tashkent` | Modelga aytiladigan joriy vaqt va holat muddati shu zonada |
| `REPORT_EVERY_REPLY` | `false` | `true` bo'lsa, har bir avtomatik javob nusxasi sizga yuboriladi |
| `DB_PATH` | `data/bot.db` | SQLite fayli joyi |

### `MAX_TOKENS` haqida

Modelning javobdan oldingi "o'ylash" tokenlari ham shu chegaraga kiradi. Qiymat juda past bo'lsa, javob o'rtasida uzilib qoladi. Narx amalda ishlatilgan tokenlarga qarab hisoblanadi, shuning uchun chegarani baland qo'yish xarajatni oshirmaydi. Javob baribir uzilsa, logda `Javob MAX_TOKENS ... limitida uzilib qoldi` degan ogohlantirish chiqadi.

### Model tanlash

`claude-haiku-5-5` tez va arzon, kundalik yozishmalar uchun yetarli. Murakkabroq qoidalar yoki nozikroq ohang kerak bo'lsa, `claude-sonnet-5-5` ni sinab ko'ring; u qimmatroq.

## AI javoblar limiti

Bitta suhbatdosh `RATE_LIMIT_MINUTES` daqiqa ichida `RATE_LIMIT_COUNT` tadan ortiq AI javob ololmaydi. Limit tugagach:

- AI chaqirilmaydi, bot har safar tayyor matnni (`RATE_LIMIT_MESSAGE`) yuboradi;
- sizga 🚦 bildirishnoma keladi (har bir chat uchun bir marta).

Limit qachon tozalanadi:

- oyna o'tgach o'z-o'zidan;
- istalgan shaxsiy chatda o'zingiz xabar yozsangiz (hamma chatlar uchun);
- botda `/resume` bossangiz.

Javobsiz qoldirilgan (`[SKIP]`) chaqiruvlar ham sanaladi, chunki ular ham token sarflaydi.

## So'kinish filtri

Ro'yxat `badwords.txt` faylida, har qatorda bitta so'z yoki ibora. Asosi: [milliytech/uzbek-badwords](https://github.com/milliytech/uzbek-badwords).

Bot qanday javob beradi:

1. **Birinchi marta:** AI siz ogohlantiradi — "Iltimos, hurmatni saqlaylik..."
2. **Ikkinchi marta:** "Hurmatsizlik qilganingiz uchun endi men sizga javob bera olmayman..." deydi, shundan keyin bu chatga jim turadi va sizga 🚫 bildirishnoma yuboradi.

Cheklov o'sha chatda o'zingiz yozsangiz yoki `/resume` bossangiz olinadi.

Moslashtirish qoidalari:

- **Faqat butun so'zlar mos keladi.** `ker` so'zi `kerak` ichida topilmaydi.
- Katta-kichik harf, apostrof (`qo'toq` = `qotoq`) va takror harflar (`suuuka` = `suka`) farqlanmaydi.
- Kirillcha yozilgan so'zlar lotinchaga o'girib tekshiriladi.
- `#` bilan boshlangan qator izoh. So'zni o'chirish uchun oldiga `# ` qo'ying.
- `=` bilan boshlangan so'z faqat apostrofi bilan aynan yozilganda mos keladi. Masalan `=o'l` oddiy `ol` so'ziga mos kelmaydi.

Ro'yxatdagi ba'zi so'zlar (`it`, `mol`, `jala`...) kundalik nutqda oddiy ma'noda ham ishlatiladi va begunoh xabarni ushlashi mumkin. O'z auditoriyangizga qarab ro'yxatni tahrirlang. Faylni o'zgartirgandan keyin botni qayta ishga tushiring.

## Xarajat

Xarajat faqat Anthropic API uchun; har bir javob alohida so'rov.

`claude-haiku-5-5` bilan odatiy javob taxminan 1 000 kirish va 250 chiqish tokeni sarflaydi, bu bitta javob uchun sentning yuzdan bir necha qismi. Ya'ni $10 o'n minglab javobga yetadi. Aniq narxlar: [Anthropic pricing](https://www.anthropic.com/pricing).

Xarajatni oshiradigan narsalar:

- **Bilim bazasi.** Yuklangan fayllar har bir so'rovga to'liq qo'shiladi. 50 KB li fayl bitta javob narxini taxminan o'n baravar oshiradi.
- **`HISTORY_LIMIT`.** Qancha katta bo'lsa, har so'rovda shuncha ko'p eski xabar yuboriladi.
- **Qimmatroq model.**

Haqiqiy sarfni Anthropic Console'dagi Usage bo'limida yoki logdagi `LLM: ... in / ... out tokens` qatorlarida ko'rish mumkin.
