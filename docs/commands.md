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

## Alohida odamlar uchun qoidalar

Bitta suhbatdoshga qanday javob berishni alohida belgilash mumkin: laqab bilan chaqirish, "sen" yoki "siz" deb gaplashish, unga nima deyish va nima demaslik. Bu qoidalar faqat o'sha odamga javob yozilganda modelga yuboriladi va umumiy qoidalardan ustun turadi.

| Buyruq | Vazifasi |
|---|---|
| `/for @username <qoida>` | Shu odam uchun qoida qo'shish |
| `/for <ID> <qoida>` | Username'i yo'q odam uchun |
| `/for @username` | Shu odamning qoidalari |
| `/people` | Barcha shaxsiy qoidalar |
| `/pdel <raqam>` | O'chirish |
| `/contacts` | Sizga yozgan oxirgi suhbatdoshlar, ularning username va ID si |

### Odamni ro'yxatdan tanlash (eng ishonchli)

`/pick` yozing va **👤 Odamni tanlash** tugmasini bosing. Telegram chatlaringiz ro'yxatini ochadi; tanlangan odamning ID si botga keladi. Username'i yo'q, raqami yashirin yoki yopiq akkauntlar uchun ham ishlaydi. Shundan keyin 10 daqiqa ichida yozgan birinchi oddiy matningiz shu odamning qoidasi bo'lib saqlanadi (`/cancel` — bekor qilish).

### O'sha chatning o'zidan

Username'i yo'q yoki yopiq akkauntlar uchun eng qulay yo'l. Suhbatdosh bilan chatda o'zingiz yozasiz:

| Chatda yozing | Vazifasi |
|---|---|
| `%id` | Shu odamning ID si botga keladi |
| `%add <qoida>` | Shu odam uchun qoida qo'shish |
| `%rules` | Shu odamning qoidalari |
| `%del <raqam>` | Shu odamning qoidasini o'chirish |
| `%clear` | Bot shu chatda yozgan barcha xabarlarni o'chirish |
| `%pause` | Bot shu chatda javob bermaydi (`%pause 2h` — 2 soatga). Rejalashtirilgan xabarlar yuborilaveradi |
| `%resume` | Shu chatda qayta yoqish |
| `%schedule <so'rov>` | Shu odamga xabar rejalashtirish |
| `%schedules` | Shu odam uchun rejalashtirilgan xabarlar |

Barcha chat buyruqlarini `%` o'rniga `#` bilan ham yozish mumkin: `#clear`, `#pause`.

Bot buyruqni chatdan darhol o'chiradi, javob esa botning o'z chatiga keladi. Bu buyruqlar chatni pauzaga qo'ymaydi va tarixga yozilmaydi. Telegram botga faqat Chat Automation qamrab olgan va oxirgi 24 soatda faol bo'lgan chatlardagi xabarlarni yuboradi, shuning uchun eski yoki chiqarib tashlangan chatda `%id` hech narsa qaytarmaydi; bunday holatda `/pick` dan foydalaning. O'chirish uchun Chat Automation sozlamalarida botga xabarlarni o'chirish ruxsati kerak; ruxsat bo'lmasa, bot ogohlantiradi. O'chirilgunga qadar suhbatdosh buyruqni bir lahza ko'rishi yoki bildirishnomada o'qishi mumkin.

### Botning o'z chatidan

```
/for @ali Uni «Aliboy» deb chaqir, sensirab do'stona gaplash
/for 123456789 «Sardorbek aka» deb hurmat bilan murojaat qil
/test @ali Ertaga bo'shmisan?
```

Eslatmalar:

- **Username bo'yicha qoida odam hali yozmagan bo'lsa ham ishlaydi.** Username'i o'zgarsa, qoida eski username'ga bog'liq qolishi mumkin; odam bir marta yozgach ID bo'yicha topiladi, shuning uchun qoidani o'shandan keyin qo'shgan ishonchliroq.
- **Username'i yo'q odamning ID si** u sizga bot ishlab turgan paytda yozgandan keyin `/contacts` da chiqadi.
- `/test @username <xabar>` va `/prompt @username` shu odam uchun qoidalar bilan ishlaydi.

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

## GIF va stikerlar

Bot ayrim xabarlarga matn o'rniga siz tanlagan GIF yoki stikerni yuboradi.

1. Botga GIF yoki stiker yuboring.
2. Bot so'ragach, u qachon yuborilishini bitta xabar bilan yozing: `Rahmat deyishsa`, `Tug'ilgan kunim bilan tabriklashsa`.

GIF'ni izoh (caption) bilan yuborsangiz, izoh shart sifatida olinadi va ikkinchi qadam kerak bo'lmaydi.

| Buyruq | Vazifasi |
|---|---|
| `/media` | Saqlangan GIF va stikerlar ro'yxati |
| `/media <raqam>` | Bittasini ko'rish |
| `/mdel <raqam>` | O'chirish |
| `/cancel` | Hozirgina yuborilgan GIF/stikerni saqlamaslik |

Eslatmalar:

- Shart mos keladimi-yo'qmi, modelning o'zi hal qiladi. Aniq va qisqa yozing; `/test <xabar>` bilan tekshiring — mos kelsa, bot o'sha GIF/stikerni sizga ko'rsatadi.
- GIF/stiker yuborgandan keyin 10 daqiqa ichida yozgan birinchi oddiy matningiz qoida emas, shu GIF/stikerning sharti bo'lib saqlanadi.
- Mos kelgan xabarga faqat GIF/stiker yuboriladi, matn qo'shilmaydi.

## Rejalashtirilgan xabarlar

Bir martalik yoki takroriy xabar. Oddiy tilda yozasiz, bot jadvalni o'zi tushunadi.

| Buyruq | Vazifasi |
|---|---|
| `/schedule <so'rov>` | Odamni bot `/contacts` ro'yxatidan ism, username yoki shaxsiy qoida (masalan "CEO") bo'yicha topadi |
| `/schedule @username <so'rov>` | Aniq odamga |
| `%schedule <so'rov>` | O'sha odam bilan chatda (eng ishonchli) |
| `/schedules` | Ro'yxat |
| `/sdel <raqam>` | O'chirish |

```
/schedule bugun 21:00 da Oybekni tug'ilgan kuni bilan batafsil va chiroyli qilib tabrikla
/schedule har oyning 10-sanasida CEO ga "Bugun $120 serverlar uchun to'lov qilishimiz kerak" deb yubor
/schedule @dostim har juma 08:00 da "Juma muborak" deb yubor
```

- Matn qo'shtirnoqda yoki "... deb yubor" shaklida bo'lsa, **aynan shu matn** ketadi. Nima yozishni tasvirlasangiz ("tabrikla", "eslat"), **AI** har safar yangi matn yozadi.
- Vaqt aytilmasa, 09:00 olinadi. Turlar: bir martalik, har kuni, har hafta, har oy, har yili.
- Yuborilgach sizga 📤 nusxa keladi. `/pause` va `%pause` rejalashtirilgan xabarlarga ta'sir qilmaydi.
- **Telegram cheklovi:** bot faqat oxirgi 24 soatda faol bo'lgan chatlarga yoza oladi. Yuborib bo'lmasa, bot sizga ⚠️ va tayyor matnni yuboradi.

## Pauzadagi chatlar

| Buyruq | Vazifasi |
|---|---|
| `/paused` | `%pause` qilingan chatlar |
| `/unpause <ID yoki @username>` | Botning o'z chatidan qayta yoqish |

## Namoz vaqti

| Buyruq | Vazifasi |
|---|---|
| `/namoz` | Bugungi namoz vaqtlari |
| `/location <hudud>` | Hududni o'rnatish: `/location buxoro`, `/location samarqand-shahri`, `/location olmazor` |
| `/location` | Hozirgi hudud |

Suhbatdosh namoz vaqtini so'rasa ham bot shu hudud bo'yicha javob beradi (boshqa hudud so'ralsa, o'shani).

## Suhbatdoshlar uchun xizmatlar

Suhbatdosh botdan valyuta kursi, ob-havo, namoz vaqti, Vikipediya ma'lumoti, «tarixda bugun», hikmatli so'z yoki qiziq fakt so'rashi mumkin (masalan «kurs», «ob-havo», «wiki Amir Temur»). Javob suhbatdosh yozgan tilda bo'ladi. Suhbatdosh AI bilan 3 marta yozishgach, bot bu imkoniyatlarni o'zi taklif qiladi. Sinash: `/test kurs`.

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
| `/test <xabar>` | Bot qanday javob berishini ko'rish. Hech kimga yuborilmaydi. `/test @username <xabar>` — shu odamga |
| `/pause` | Botni butunlay to'xtatish |
| `/resume` | Qayta yoqish. Chat pauzalari, AI limiti va so'kinish cheklovlari ham tozalanadi |
| `/status` | Ulanish, model, qoidalar soni, joriy holat, cheklovlar |
| `/prompt` | Modelga yuborilayotgan to'liq system promptni ko'rish. `/prompt @username` — shu odam uchun |
| `/forget` | Barcha chatlar tarixini o'chirish |
| `/help` | Yordam |

## Bot sizga yuboradigan bildirishnomalar

| Belgi | Ma'nosi |
|---|---|
| ✅ / 🔌 / ⚠️ | Bot akkauntingizga ulandi, uzildi yoki javob berish ruxsati yo'q |
| 🔔 | Suhbatdosh muhim yoki shoshilinch narsa yozdi (bir jumlalik xulosa bilan) |
| 🚦 | Suhbatdosh AI javoblar limitini tugatdi |
| 🎭 | Suhbatdosh stiker yubordi: stiker emojisi va bot javoban yuborgan emoji |
| 🚫 | Suhbatdosh so'kingani uchun bot unga javob berishni to'xtatdi |
| 🤖 | Har bir avtomatik javob nusxasi (`REPORT_EVERY_REPLY=true` bo'lsa) |
| 📤 | Rejalashtirilgan xabar yuborildi |
| ⏰ | Rejalashtirilgan xabar bot o'chiq bo'lgani uchun yuborilmadi |
