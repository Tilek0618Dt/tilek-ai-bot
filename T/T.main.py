# tilek_ai_bot.py
import telebot
import requests

# =========================
# TELEGRAM BOT TOKEN
# =========================
BOT_TOKEN = "8542143817:AAGrHFfSt9AzvmAPP8EwTvlbp3oLmDDtTG8"
bot = telebot.TeleBot(BOT_TOKEN)

# =========================
# OPENROUTER API KEY
# =========================
OPENROUTER_API_KEY = "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"

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
                "HTTP-Referer": "https://t.me/tilek_ai_bot",  # каалаган ссылка
                "X-Title": "Tilek AI Bot"
            },
            json={
                "model": "openai/gpt-4o-mini",  # же башка модель
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_text}
                ],
                "temperature": 0.8,
                "max_tokens": 1000
            },
            timeout=60
        )

        data = response.json()

        if "choices" in data:
            reply = data["choices"][0]["message"]["content"]
        else:
            reply = f"API жооп бербеди: {data}"

    except Exception as e:
        reply = f"Кечиресиз, техникалык көйгөй чыкты.\n{e}"

    bot.reply_to(message, reply)


print("🔥 ТИЛЕК AI (OpenRouter) ИШТЕП ЖАТАТ!")
bot.infinity_polling()
