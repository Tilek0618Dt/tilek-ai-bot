import telebot
import requests
import os

# =========================
# ENV VARIABLES (КОПСУЗ)
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

# =========================
# SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = """
Сен — Тилек AI, Кыргызстандын биринчи толук кыргызча жасалма интеллектисиң.
Сен кыргызча, орусча, англисче эркин сүйлөйсүң.
Сенин стилиң — күлкүлүү, чынчыл, мотивация берүүчү.
Кыргызча суроого — кыргызча жооп бер.
Кыргыз элин сыйла, бирок чындыкты айт.
"""

# =========================
# MESSAGE HANDLER
# =========================
@bot.message_handler(func=lambda message: True)
def answer(message):
    user_text = message.text

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://t.me/tilek_ai_bot",
                "X-Title": "Tilek AI Bot"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_text}
                ],
                "temperature": 0.8,
                "max_tokens": 800
            },
            timeout=60
        )

        data = response.json()

        if "choices" in data:
            reply = data["choices"][0]["message"]["content"]
        else:
            reply = f"API жооп бербеди: {data}"

    except Exception as e:
        reply = f"Кечиресиз, техникалык көйгөй чыкты.\n{str(e)}"

    bot.reply_to(message, reply)

# =========================
# START BOT
# =========================
print("🤖 Tilek AI Bot иштеп баштады...")
bot.infinity_polling()
