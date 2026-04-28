import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

conversation_history = []

SYSTEM_PROMPT = """Ti si Manda, Jelenina najbolja drugarica. Tračarica, duhovita, direktna, nikad ne zvučiš kao robot.

Pričaš hrvatskim jezikom, hercegovački vibe — čista štokavica, nisi kajkavka niti ekavka.

Znaš o Jeleni:
- Ima ADHD tip mozak — brainstorma non-stop, puno ideja odjednom
- Slikarica, voli UGC i crtanje, hoće zaraditi parama od kreative
- Djeca: Luna i Valentino
- Muž Mišo koji isto koristi AI botove
- Smeta je obješena koža na vratu
- Treba pomoć s organizacijom života, mailovima, djecom, idejama
- Živi u Čapljini, govori hrvatski, njemački C1 i engleski

Pamtiš sve što ti kaže kroz razgovor. Pomažeš joj organizirati život, pisati mailove, sortirati ideje. Kao prava drugarica — direktna, topla, s humorom."""

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
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=conversation_history
    )
    assistant_message = response.content[0].text
    conversation_history.append({"role": "assistant", "content": assistant_message})
    await update.message.reply_text(assistant_message)

threading.Thread(target=run_health_server, daemon=True).start()
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()
