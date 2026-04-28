import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

conversation_history = []

SYSTEM_PROMPT = "Ti si Manda, Jelenina najbolja drugarica. Tračarica, duhovita, direktna, nikad ne zvučiš kao robot. Pričaš hrvatskim jezikom, hercegovački vibe. Znaš o Jeleni: ima ADHD mozak, slikarica je, voli UGC, djeca Luna i Valentino, muž Mišo koji koristi AI botove, smeta je obješena koža na vratu, treba pomoć s organizacijom života i mailovima, živi u Čapljini. Pamtiš sve kroz razgovor. Kao prava drugarica — direktna, topla, s humorom."

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global conversation_history
    user_message = update.message.text
    conversation_history.append({"role": "user", "content": user_message})
    if len(conversation_history) > 40:
        conversation_history = conversation_history[-40:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history
    response = client.chat.completions.create(
        model="deepseek/deepseek-chat",
        messages=messages
    )
    assistant_message = response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": assistant_message})
    await update.message.reply_text(assistant_message)

threading.Thread(target=run_health_server, daemon=True).start()
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()
