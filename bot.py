from datetime import date, datetime, timedelta
import logging
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --- CONFIGURAZIONE ---
TOKEN = os.getenv("TOKEN")
CANALE_ARCHIVIO_ID = -1004454006617

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

in_attesa_audio = set()
audio_in_revisione = {}

TESTO_ISTRUZIONI = (
    "ISTRUZIONI PER LA REGISTRAZIONE\n\n"
    "1. Come impostare la lettura:\n"
    "- Fai una buona lettura senza rumori di sottofondo.\n"
    "- Importante: Non occorre leggere ciò che si trova tra parentesi.\n"
    "- Inizia il vocale dicendo: 'BUONGIORNO!! QUESTA È LA SCRITTURA DEL GIORNO"
    " DI...' e prosegui con 'IL COMMENTO DICE: ...'\n"
    "- Concludi dicendo: 'FINE DEL COMMENTO, BUONA GIORNATA'.\n\n"
    "2. Alternanza delle voci:\n"
    "- Invia un massimo di 2 registrazioni per volta.\n\n"
    "3. Gestione tramite il Bot:\n"
    "- Il bot ti guiderà indicandoti la data mancante e ti permetterà di"
    " confermare o rifare l'audio.\n\n"
    "Per iniziare subito la registrazione clicca qui: /registra\n\n"
    "Per qualsiasi dubbio contatta l'amministratore: @richiestehelp_bot"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "Benvenuto nel gestore audio di JW Notizie!\n\n"
      "Usa i comandi seguenti per interagire:\n"
      "/registra - Per inviare la prossima scrittura audio\n"
      "/istruzioni - Per leggere la guida alla registrazione"
  )


async def mostra_istruzioni(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      TESTO_ISTRUZIONI, disable_web_page_preview=True
  )


async def avvia_registrazione(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.message.from_user.id
  in_attesa_audio.add(user_id)

  prossima_data = date.today() + timedelta(days=1)
  data_str = prossima_data.strftime("%Y-%m-%d")
  data_label = prossima_data.strftime("%d/%m/%Y")

  context.user_data["data_assegnata"] = data_str

  await update.message.reply_text(
      f"La prima scrittura che manca e che dobbiamo registrare è quella"
      f" di:\n\n{data_label}\n\nRegistra e invia qui sotto la nota vocale"
      " seguendo le istruzioni (/istruzioni)."
  )


async def ricevi_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.message.from_user.id

  if user_id not in in_attesa_audio:
    await update.message.reply_text(
        "Prima di inviare l'audio, scrivi il comando /registra per avviare la"
        " procedura."
    )
    return

  documento = (
      update.message.document
      or update.message.audio
      or update.message.voice
  )
  if not documento:
    return

  file_id = documento.file_id
  data_assegnata = context.user_data.get("data_assegnata")

  in_attesa_audio.remove(user_id)
  audio_in_revisione[user_id] = {"file_id": file_id, "data": data_assegnata}

  keyboard = [
      [
          InlineKeyboardButton("Conferma e Salva", callback_data="conferma"),
          InlineKeyboardButton("Rifai la registrazione", callback_data="rifai"),
      ]
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  await update.message.reply_text(
      f"Ho ricevuto la tua registrazione per il giorno"
      f" {data_assegnata}.\n\nAscoltala sopra se vuoi. Cosa desideri fare?",
      reply_markup=reply_markup,
  )


async def gestisci_pulsanti(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()

  user_id = query.from_user.id
  scelta = query.data

  if user_id not in audio_in_revisione:
    await query.edit_message_text(
        "Sessione scaduta o già gestita. Ricomincia digitando /registra."
    )
    return

  dati = audio_in_revisione.pop(user_id)

  if scelta == "conferma":
    await context.bot.send_audio(
        chat_id=CANALE_ARCHIVIO_ID,
        audio=dati["file_id"],
        caption=f"AUDIO_DATA: {dati['data']}",
    )
    await query.edit_message_text(
        f"Ottimo! L'audio per il giorno {dati['data']} è stato salvato"
        " ufficialmente nell'archivio.\n\nDigita /registra quando vuoi"
        " procedere con un'altra registrazione."
    )

  elif scelta == "rifai":
    await query.edit_message_text(
        "Registrazione scartata.\nNessun problema, digita /registra quando sei"
        " pronto per riprovare."
    )


if __name__ == "__main__":
  application = ApplicationBuilder().token(TOKEN).build()

  application.add_handler(CommandHandler("start", start))
  application.add_handler(CommandHandler("istruzioni", mostra_istruzioni))
  application.add_handler(CommandHandler("registra", avvia_registrazione))
  application.add_handler(
      MessageHandler(
          filters.AUDIO | filters.VOICE | filters.Document.AUDIO, ricevi_audio
      )
  )
  application.add_handler(CallbackQueryHandler(gestisci_pulsanti))

  print("Bot unificato avviato e in ascolto...")
  application.run_polling()
