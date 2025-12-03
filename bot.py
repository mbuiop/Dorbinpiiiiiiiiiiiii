import telebot
import threading
import time
import random
import string

TOKEN = "8198774412:AAHphDh2Wo9Nzgomlk9xq9y3aeETsVpkXr0"
CHAT_ID = "327855654"

bot = telebot.TeleBot(TOKEN)

def make_code():
    parts = ["USD"]
    for _ in range(5):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        parts.append(part)
    return '-'.join(parts)

def send_codes():
    while True:
        code = make_code()
        try:
            bot.send_message(CHAT_ID, code)
        except:
            pass
        time.sleep(5)

# شروع خودکار
print("🤖 شروع تولید کد...")
thread = threading.Thread(target=send_codes, daemon=True)
thread.start()

# فقط برای اینکه ربات فعال بمونه
@bot.message_handler(commands=['ping'])
def ping(m):
    bot.reply_to(m, "✅ کار می‌کنم")

bot.polling()
