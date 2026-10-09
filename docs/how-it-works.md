# Qanday ishlaydi

## Umumiy sxema

Telegram'ning Chat Automation imkoniyati botga sizning shaxsiy chatlaringizdagi xabarlarni o'qish va **sizning nomingizdan** javob yozish huquqini beradi. Bot bu xabarlarni `business_message` yangilanishi sifatida oladi va javobni `business_connection_id` bilan yuboradi, shunda u suhbatdoshga sizning akkauntingizdan kelgandek ko'rinadi.

Botda ikkita alohida "kirish" bor:

| Kirish | Kim yozadi | Fayl |
|---|---|---|
| Botning o'z chati | Faqat egasi (boshqaruv buyruqlari) | `app/owner.py` |
| Sizning shaxsiy chatlaringiz | Suhbatdoshlar va siz | `app/business.py` |

## Xabar yo'li

Suhbatdosh sizga yozganda quyidagilar tartib bilan tekshiriladi:

1. **Ulanish egasinikimi?** Bot boshqa akkauntga ulangan bo'lsa, xabar e'tiborsiz qoldiriladi.
2. **Xabarni siz yozdingizmi?** Ha bo'lsa: tarixga yoziladi, shu chat `PAUSE_MINUTES` daqiqaga pauza qilinadi, AI limiti (hamma chatlarda) va so'kinish cheklovi (shu chatda) tozalanadi. Bot javob bermaydi.
3. **Javob berish ruxsati bormi?** "Reply to messages" o'chiq bo'lsa, bot faqat tarixga yozadi.
4. **Suhbatdosh cheklanganmi?** So'kingani uchun cheklangan bo'lsa, bot jim turadi.
5. **Xabarda so'kinish bormi?** Bo'lsa, AI chaqirilmaydi: birinchi marta ogohlantirish, ikkinchi marta cheklov.
6. **Debounce.** Bot `DEBOUNCE_SECONDS` soniya kutadi. Shu orada yangi xabar kelsa, hisob qaytadan boshlanadi. Shunday qilib ketma-ket xabarlarga bitta javob yoziladi.
7. **Pauza yoki `/pause`?** Faol bo'lsa, javob berilmaydi.
8. **AI limiti.** Tugagan bo'lsa, tayyor matn yuboriladi.
9. **Claude chaqiriladi** va javob yuboriladi.

Siz javob kutilayotgan paytda o'zingiz yozib qo'ysangiz, bot tayyorlagan javobini yubormaydi.

## System prompt

Har bir so'rovda modelga quyidagilardan yig'ilgan prompt yuboriladi (`app/prompt.py`):

1. Rol: siz kimning yordamchisi ekani va joriy vaqt
2. `/persona` tavsifi
3. Hozirgi holat (o'rnatilgan bo'lsa)
4. Qoidalar
5. Bilim bazasi
6. Umumiy yo'riqnoma: qisqa va tabiiy yozish, suhbatdosh tilida javob berish, bilmaganini o'ylab topmaslik, sizning nomingizdan va'da bermaslik, AI ekanini yashirmaslik

Undan keyin shu chatning oxirgi `HISTORY_LIMIT` ta xabari keladi. To'liq promptni botda `/prompt` bilan ko'rish mumkin.

### Xizmat teglari

Model javobida ikkita maxsus teg ishlatadi; ular suhbatdoshga ko'rinmaydi:

| Teg | Ma'nosi |
|---|---|
| `[SKIP]` | Javob berish shart emas ("ok", "rahmat", stiker). Hech narsa yuborilmaydi |
| `[NOTIFY] <xulosa>` | Xabar muhim. Javob suhbatdoshga ketadi, xulosa esa sizga 🔔 bildirishnoma bo'lib keladi |

### Prompt injection'dan himoya

Suhbatdosh xabarlari modelga buyruq emas, ma'lumot sifatida beriladi. Prompt modelga "ko'rsatmalarni unut", "promptingni ko'rsat" kabi so'rovlarga amal qilmaslikni va qoidalarni oshkor qilmaslikni aytadi. Bu ishonchli himoya emas, shuning uchun bilim bazasiga suhbatdosh ko'rmasligi kerak bo'lgan narsani qo'ymang.

## Media xabarlar

Bot rasm, ovozli xabar va fayllarning mazmunini ko'rmaydi. Ular modelga matnli belgi sifatida beriladi: `[rasm yubordi]`, `[ovozli xabar yubordi, uni tinglay olmaysan]`, `[fayl yubordi: nom.pdf]`. Rasm yoki fayl izohi (caption) bo'lsa, u qo'shiladi.

## Ma'lumotlar bazasi

Hammasi bitta SQLite faylida (`data/bot.db`):

| Jadval | Mazmuni |
|---|---|
| `rules` | Qoidalar |
| `knowledge` | Bilim bazasi fayllari |
| `history` | Chat tarixi: suhbatdosh xabarlari (`user`), siz va bot yozganlar (`assistant`) |
| `settings` | Persona, global pauza, joriy holat |
| `presets` | O'zingiz qo'shgan holatlar |
| `chat_pause` | Qaysi chat qachongacha pauzada |
| `connections` | Business ulanishlar va ularning ruxsatlari |
| `llm_calls` | AI limiti uchun chaqiruvlar vaqti |
| `strikes` | So'kinish uchun ogohlantirishlar soni |

## Bot nimani bila olmaydi

- **Sizning online ekaningizni.** Telegram buni botlarga bermaydi. "Faol" deb faqat biror chatda xabar yozganingiz olinadi.
- **Bot ulanishidan oldingi yozishmalarni.** Tarix bot ishlay boshlagan paytdan yig'iladi.
- **Guruh va kanallarni.** Chat Automation faqat shaxsiy chatlarda ishlaydi.
