# Buyruqlar

Barcha buyruqlar **botning o'z chatida** yoziladi va faqat egasidan (`OWNER_ID`) qabul qilinadi. Boshqa odam botga yozsa, "Bu shaxsiy yordamchi bot" degan javob oladi.

## Qoidalar

Qoidalar botga qanday javob berishni o'rgatadi. Ular har bir javobda modelga yuboriladi.

| Buyruq | Vazifasi |
|---|---|
| `/add <matn>` | Qoida qo'shish |
| oddiy matn (buyruqsiz) | Bu ham qoida sifatida saqlanadi |
| `/rules` | Qoidalar ro'yxati (raqamlari bilan) |
| `/del <raqam>` | Qoidani o'chirish |

```
/add Narx so'rashsa, aniq summa aytma, talablarni so'rab ol
/add Ish vaqtim 9:00–18:00, undan keyin ertaga javob berishimni ayt
```

## Siz haqingizda

| Buyruq | Vazifasi |
|---|---|
| `/persona` | Joriy tavsifni ko'rish |
| `/persona <matn>` | Kim ekaningiz va nima bilan shug'ullanishingizni yozish |

## Bilim bazasi

Uzunroq ma'lumotlar (narxlar ro'yxati, xizmatlar, FAQ) uchun.

| Amal | Vazifasi |
|---|---|
| `.txt` yoki `.md` fayl yuborish | Bilim sifatida saqlash (UTF-8, 200 KB gacha) |
| `/knowledge` | Ro'yxat |
| `/kdel <raqam>` | O'chirish |

Bilim bazasi har bir so'rovga to'liq qo'shiladi, shuning uchun katta fayllar xarajatni oshiradi: [configuration.md](configuration.md#xarajat).

## Hozirgi holatingiz

Holat o'rnatilsa, bot suhbatdoshlarga hozir qayerda ekaningizni va javob bera olmasligingizni aytadi.

| Buyruq | Vazifasi |
|---|---|
| `/<holat>` | Tayyor holatni yoqish, masalan `/bus` |
| `/<holat> 40` | 40 daqiqaga; vaqt tugagach o'zi o'chadi |
| `/<holat> 2h` | 2 soatga |
| `/<holat> 40 <izoh>` | Qo'shimcha izoh bilan: `/bus 40 Chilonzorga ketyapman` |
| `/set [muddat] <matn>` | Erkin holat: `/set 2h Tug'ilgan kundaman` |
| `/free` | Holatni o'chirish |
| `/statuses` | Barcha holatlar ro'yxati |
| `/newstatus <nom> <tavsif>` | O'z holatingizni qo'shish, keyin `/<nom>` ishlaydi |
| `/delstatus <nom>` | O'zingiz qo'shgan holatni o'chirish |

Tayyor holatlar:

| Guruh | Buyruqlar |
|---|---|
| Ish / o'qish | `/work`, `/meeting`, `/majlis`, `/study`, `/interview` |
| Yo'l | `/bus`, `/taxi`, `/metro`, `/drive`, `/trip` |
| Sport | `/football`, `/gym`, `/run`, `/walk` |
| Shaxsiy | `/sleep`, `/lunch`, `/family`, `/guest`, `/sick` |
| Dam olish | `/rest`, `/vacation`, `/shop` |

Eslatmalar:

- **Muddatsiz holat o'zi o'chmaydi.** `/bus` deb qo'yib `/free` ni unutsangiz, bot soatlab "avtobusda" deyaveradi. `/bus 40` kabi muddat bilan ishlatgan ma'qul.
- **`/set` da boshidagi raqam muddat deb olinadi.** `/set 5 daqiqada qaytaman` 5 daqiqalik holat bo'ladi.
- Telegram buyruq nomida chiziqcha ishlatib bo'lmaydi, lekin qo'lda `/bus-set` yoki `/bus_set` deb yozsangiz ham ishlaydi.
- Tayyor holat tavsifini `/newstatus bus <yangi tavsif>` bilan o'zgartirish mumkin.

## Boshqaruv

| Buyruq | Vazifasi |
|---|---|
| `/test <xabar>` | Bot qanday javob berishini ko'rish. Hech kimga yuborilmaydi |
| `/pause` | Botni butunlay to'xtatish |
| `/resume` | Qayta yoqish. Chat pauzalari, AI limiti va so'kinish cheklovlari ham tozalanadi |
| `/status` | Ulanish, model, qoidalar soni, joriy holat, cheklovlar |
| `/prompt` | Modelga yuborilayotgan to'liq system promptni ko'rish |
| `/forget` | Barcha chatlar tarixini o'chirish |
| `/help` | Yordam |

## Bot sizga yuboradigan bildirishnomalar

| Belgi | Ma'nosi |
|---|---|
| ✅ / 🔌 / ⚠️ | Bot akkauntingizga ulandi, uzildi yoki javob berish ruxsati yo'q |
| 🔔 | Suhbatdosh muhim yoki shoshilinch narsa yozdi (bir jumlalik xulosa bilan) |
| 🚦 | Suhbatdosh AI javoblar limitini tugatdi |
| 🚫 | Suhbatdosh so'kingani uchun bot unga javob berishni to'xtatdi |
| 🤖 | Har bir avtomatik javob nusxasi (`REPORT_EVERY_REPLY=true` bo'lsa) |
