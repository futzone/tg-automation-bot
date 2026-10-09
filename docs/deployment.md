# Serverga joylash

Bot **polling** rejimida ishlaydi: domen, SSL yoki ochiq port kerak emas. Telegram va Anthropic API'ga chiqa oladigan istalgan Linux server yetarli. Quyidagi qo'llanma Ubuntu / Debian va systemd uchun.

## 1. Kodni serverga ko'chiring

```bash
sudo apt update && sudo apt install -y python3 python3-venv git
sudo git clone https://github.com/futzone/tg-automation-bot.git /opt/tg-automation
cd /opt/tg-automation
sudo python3 -m venv .venv
sudo .venv/bin/pip install -r requirements.txt
```

## 2. `.env` ni yarating

```bash
sudo cp .env.example .env
sudo nano .env      # BOT_TOKEN, OWNER_ID, OWNER_NAME, ANTHROPIC_API_KEY
```

Botni avval kompyuteringizda ishlatgan bo'lsangiz, `.env` va `data/bot.db` ni o'sha yerdan ko'chirsangiz, qoidalar, bilimlar va ulanish saqlanib qoladi.

## 3. Alohida foydalanuvchi oching

Bot root nomidan ishlamasligi uchun:

```bash
sudo useradd --system --home /opt/tg-automation --shell /usr/sbin/nologin aibot
sudo chown -R aibot:aibot /opt/tg-automation
sudo chmod 600 /opt/tg-automation/.env
```

## 4. Service'ni yoqing

```bash
sudo cp aibot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aibot
```

Tekshirish:

```bash
systemctl is-active aibot        # active
journalctl -u aibot -n 20        # "Bot @... ishga tushdi" va "Start polling"
```

Service server qayta yuklanganda yoki bot yiqilganda o'zi qayta ishga tushadi.

## Kundalik buyruqlar

```bash
journalctl -u aibot -f               # jonli loglar
sudo systemctl restart aibot         # qayta ishga tushirish (.env yoki badwords.txt o'zgargach)
sudo systemctl stop aibot            # to'xtatish
```

## Yangilash

```bash
cd /opt/tg-automation
sudo -u aibot git pull
sudo .venv/bin/pip install -r requirements.txt
sudo systemctl restart aibot
```

`data/` va `.env` git'da yo'q, shuning uchun yangilash ularga tegmaydi. Ma'lumotlar bazasi sxemasi bot ishga tushganda o'zi yangilanadi.

## Zaxira nusxa

Barcha holat bitta faylda: `data/bot.db` (qoidalar, bilimlar, chat tarixi, ulanish). Zaxira uchun shu fayl va `.env` yetarli:

```bash
sudo cp /opt/tg-automation/data/bot.db ~/bot.db.bak-$(date +%F)
```

## Bitta token — bitta nusxa

Bitta bot tokeni bilan bir vaqtda faqat **bitta** nusxa ishlashi mumkin. Serverda service ishlab turganda kompyuteringizda `python bot.py` ni ishga tushirsangiz, ikki nusxa to'qnashadi va xabarlar yo'qolishi mumkin. Lokal sinov uchun avval serverdagisini to'xtating yoki alohida test boti oching.
