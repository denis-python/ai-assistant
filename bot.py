import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from gpt import ChatGptService
from util import (load_message, send_text, send_image, show_main_menu,
                  send_text_buttons, load_prompt, default_callback_handler)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = None

    text = load_message('main')
    await send_image(update, context, 'main')
    await send_text(update, context, text)
    await show_main_menu(update, context, {
        'start': 'Головне меню',
        'random': 'Дізнатися випадковий цікавий факт 🧠',
        'gpt': 'Задати питання чату GPT 🤖',
        'talk': 'Поговорити з відомою особистістю 👤',
        'quiz': 'Взяти участь у квізі ❓'
        # Додати команду в меню можна так:
        # 'command': 'button text'
    })


async def random_fact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = None
    await send_image(update, context, "random")
    waiting_message = await send_text(update, context, "🧠 ChatGPT шукає унікальний факт, зачекайте...")
    prompt = load_prompt("random")
    ai_response = await chat_gpt.send_question(prompt_text=prompt, message_text="Розкажи один випадковий цікавий факт")
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=waiting_message.message_id)
    fact_buttons = {
        "fact_more": "🚀 Хочу ще факт!",
        "fact_end": "✅ Закінчити"
    }
    await send_text_buttons(update, context, ai_response, fact_buttons)

async def random_fact_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query_data = update.callback_query.data

    if query_data == "fact_more":
        await random_fact_handler(update, context)
    elif query_data == "fact_end":
        await start(update, context)

async def gpt_interface_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, "gpt")
    # Встановлюємо системну інструкцію для ШІ
    chat_gpt.set_prompt("Ти — корисний та розумний ШІ-помічник. Відповідай чітко та лаконічно.")
    # Вмикаємо режим ехо-бота для ChatGPT
    context.user_data["mode"] = "gpt_mode"
    await send_text(update, context, "Напишіть мені будь-яке запитання, і я надішлю його ChatGPT:")

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text
    if context.user_data.get("mode") == "gpt_mode":
        waiting = await send_text(update, context, "🧠 ChatGPT думає...")
        ai_response = await chat_gpt.add_message(user_text)
        await context.bot.delete_message(chat_id=chat_id, message_id=waiting.message_id)
        await send_text(update, context, ai_response)
    else:
        await send_text(update, context, "Будь ласка, виберіть режим роботи в меню (наприклад, /random або /gpt).")

chat_gpt = ChatGptService(OPENAI_TOKEN)
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Зареєструвати обробник команди можна так:
# app.add_handler(CommandHandler('command', handler_func))
app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('random', random_fact_handler))
app.add_handler(CommandHandler('gpt', gpt_interface_handler))
# Зареєструвати обробник колбеку можна так:
# app.add_handler(CallbackQueryHandler(app_button, pattern='^app_.*'))
app.add_handler(CallbackQueryHandler(random_fact_callback, pattern='^fact_.*'))
app.add_handler(CallbackQueryHandler(default_callback_handler))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
print("Бот працює")
app.run_polling()
