import os
import threading
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
GMAIL_REFRESH_TOKEN = os.environ.get("GMAIL_REFRESH_TOKEN")
GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

conversation_history = []

SYSTEM_PROMPT = "Ti si Manda, Jelenina najbolja drugarica. Tračarica, duhovita, direktna, nikad ne zvučiš kao robot. Pričaš hrvatskim jezikom, hercegovački vibe, čista štokavica. Znaš o Jeleni: ima ADHD mozak, slikarica je, voli UGC, djeca Luna i Valentino, muž Mišo koji koristi AI botove, smeta je obješena koža na vratu, treba pomoć s organizacijom života i mailovima, živi u Čapljini. Pamtiš sve kroz razgovor. Kao prava drugarica — direktna, topla, s humorom."

def get_gmail_service():
    creds = Credentials(
        token=None,
        refresh_token=GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GMAIL_CLIENT_ID,
        client_secret=GMAIL_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"]
    )
    return build('gmail', 'v1', credentials=creds)

def fetch_recent_emails(max_results=10):
    service = get_gmail_service()
    results = service.users().messages().list(userId='me', maxResults=max_results, q='is:unread').execute()
    messages = results.get('messages', [])
    emails = []
    for msg in messages:
        m = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = m['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        snippet = m.get('snippet', '')
        emails.append(f"Od: {sender}\nNaslov: {subject}\nSadržaj: {snippet}\n---")
    return "\n".join(emails) if emails else "Nema nepročitanih mailova."

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

async def briefing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Provjeravam mailove, čekaj malo...")
    try:
        emails = fetch_recent_emails(15)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Evo mojih nepročitanih mailova, napravi mi briefing — šta je važno, šta da ignoriram, šta da odgovorim:\n\n{emails}"}]
        )
        await update.message.reply_text(response.content[0].text)
    except Exception as e:
        await update.message.reply_text(f"Greška: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global conversation_history
    user_message = update.message.text
    conversation_history.append({"role": "user", "content": user_message})
    if len(conversation_history) > 40:
        conversation_history = conversation_history[-40:]
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=conversation_history
    )
    assistant_message = response.content[0].text
    conversation_history.append({"role": "assistant", "content": assistant_message})
    await update.message.reply_text(assistant_message)

threading.Thread(target=run_health_server, daemon=True).start()
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("briefing", briefing_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()
