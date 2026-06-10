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
    random_welcome_text = load_message("random")
    waiting_message = await send_text(update, context, random_welcome_text)
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
    gpt_prompt = load_prompt("gpt")
    chat_gpt.set_prompt(gpt_prompt)
    context.user_data["mode"] = "gpt_mode"
    gpt_welcome_text = load_message("gpt")
    await send_text(update, context, gpt_welcome_text)


async def talk_character_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = None
    await send_image(update, context, "talk")
    character_options = {
        "talk_cobain": "🎸 Курт Кобейн",
        "talk_hawking": "🌌 Стівен Гокінг",
        "talk_nietzsche": "🧠 Фрідріх Ніцше",
        "talk_queen": "👑 Єлизавета II",
        "talk_tolkien": "🧝‍♂️ Джон Толкін"
    }
    talk_welcome_text = load_message("talk")
    await send_text_buttons(update, context, talk_welcome_text, character_options)


async def talk_character_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query_data = update.callback_query.data
    prompt_text = load_prompt(query_data)
    chat_gpt.set_prompt(prompt_text)
    context.user_data["mode"] = "talk_mode"
    display_key = query_data.replace("talk_", "")
    display_names = {
        "cobain": "Курта Кобейна 🎸",
        "hawking": "Стівена Гокінга 🌌",
        "nietzsche": "Фрідріха Ніцше 🧠",
        "queen": "Єлизавети II 👑",
        "tolkien": "Джона Толкіна 🧝‍♂️"
    }
    chosen_name = display_names.get(display_key, "обраного персонажа")

    await update.callback_query.edit_message_text(
        text=f"✨ Успішно! ChatGPT перевтілився в {chosen_name}.\n"
             f"Напишіть йому будь-що, і він відповість суворо у своєму новому образі:"
    )


async def quiz_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = None
    await send_image(update, context, "quiz")
    if "quiz_score" not in context.user_data or context.user_data["quiz_score"] is None:
        context.user_data["quiz_score"] = 0
    quiz_options = {
        "quiz_prog": "💻 Програмування (Python)",
        "quiz_math": "📐 Математичні теорії",
        "quiz_biology": "🌿 Біологія та природа"
    }
    quiz_welcome_text = load_message("quiz")
    await send_text_buttons(update, context, quiz_welcome_text, quiz_options)


async def quiz_setup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query_data = update.callback_query.data  # Отримуємо сигнал, наприклад "quiz_more"
    chat_id = update.effective_chat.id
    if query_data == "quiz_more":
        await update.callback_query.edit_message_text(text="🧠 ChatGPT генерує нове питання...")
        next_question = await chat_gpt.add_message("quiz_more. Задай строго ОДНЕ наступне питання. Без списків!")
        await send_text(update, context, next_question)
        return
    if query_data == "quiz_end":
        final_score = context.user_data.get("quiz_score", 0)
        total_questions = context.user_data.get("quiz_step", 1) - 1
        if total_questions <= 0:
            total_questions = 1
        success_percentage = round((final_score / total_questions) * 100, 1)
        await update.callback_query.edit_message_text(
            text=f"🏁 **КВІЗ ОФІЦІЙНО ЗАВЕРШЕНО!**\n\n"
                 f"📊 **Твоя статистика дуелі з ШІ:**\n"
                 f"✅ Правильних відповідей: `{final_score}`\n"
                 f"📝 Всього задано питань: `{total_questions}`\n"
                 f"🎯 Твоя точність (вінрейт): `{success_percentage}%` 🎯\n\n"
                 f"Дякую за інтелектуальну гру, Денисе!"
        )
        context.user_data["quiz_score"] = 0
        context.user_data["quiz_step"] = 1
        await start(update, context)
        return
    if query_data == "quiz_change_theme":
        await quiz_handler(update, context)
        return
    quiz_prompt = load_prompt("quiz")
    chat_gpt.set_prompt(quiz_prompt)
    context.user_data["mode"] = "quiz_mode"

    themes = {
        "quiz_prog": "Програмування на Python 💻",
        "quiz_math": "Математичні теорії 📐",
        "quiz_biology": "Біологія та природа 🌿"
    }
    chosen_theme = themes.get(query_data, "загальну тему")
    await update.callback_query.edit_message_text(
        text=f"🚩 Обрано тему: {chosen_theme}.\n🧠 ChatGPT готує перше питання...")
    first_question = await chat_gpt.add_message(f"{query_data} Задай строго ОДНЕ перше питання. Не пиши список!")
    await send_text(update, context, first_question)


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text
    current_mode = context.user_data.get("mode")
    if not current_mode:
        await send_text(update, context,"Будь ласка, виберіть режим роботи в меню (наприклад, /random, /gpt або /talk).")
        return
    try:
        if current_mode == "gpt_mode":
            waiting = await send_text(update, context, "🧠 ChatGPT думає...")
            ai_response = await chat_gpt.add_message(user_text)
            await context.bot.delete_message(chat_id=chat_id, message_id=waiting.message_id)
            await send_text(update, context, ai_response)
        elif current_mode == "talk_mode":
            waiting = await send_text(update, context, "🎭 Персонаж обмірковує відповідь...")
            ai_response = await chat_gpt.add_message(user_text)
            await context.bot.delete_message(chat_id=chat_id, message_id=waiting.message_id)
            await send_text(update, context, ai_response)
        elif current_mode == "quiz_mode":
            waiting = await send_text(update, context, "🔄 Перевіряю відповідь та готую наступне питання...")
            ai_response = await chat_gpt.add_message(user_text)
            if ("правильно" in ai_response.lower() and "неправильно" not in ai_response.lower()) or \
                    ("вірно" in ai_response.lower() and "невірно" not in ai_response.lower()) or \
                    ("молодець" in ai_response.lower()):
                context.user_data["quiz_score"] = context.user_data.get("quiz_score", 0) + 1
            current_score = context.user_data["quiz_score"]
            context.user_data["quiz_step"] = context.user_data.get("quiz_step", 1) + 1
            await context.bot.delete_message(chat_id=chat_id, message_id=waiting.message_id)
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [InlineKeyboardButton("🚀 Ще питання на цю тему", callback_data="quiz_more")],
                [InlineKeyboardButton("🔄 Змінити тему", callback_data="quiz_change_theme")],
                [InlineKeyboardButton("✅ Закінчити квіз", callback_data="quiz_end")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"{ai_response}\n\n🏆 Твій поточний рахунок: {current_score} балів",
                reply_markup=reply_markup
            )
    except Exception as error:
        print(f"🚨 Мережевий збій або помилка API: {error}")
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=waiting.message_id)
        except:
            pass  # Якщо повідомлення вже встигло видалитись — ігноруємо

        await send_text(
            update,
            context,
            "⚠️ **Сервери ШІ або мережа тимчасово перевантажені.**\n"
            "Будь ласка, зачекайте кілька секунд і надішліть повідомлення ще раз! Бот продовжує працювати. 🔄"
        )


chat_gpt = ChatGptService(OPENAI_TOKEN)
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Зареєструвати обробник команди можна так:
# app.add_handler(CommandHandler('command', handler_func))
app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('random', random_fact_handler))
app.add_handler(CommandHandler('gpt', gpt_interface_handler))
app.add_handler(CommandHandler('talk', talk_character_handler))
app.add_handler(CommandHandler('quiz', quiz_handler))
# Зареєструвати обробник колбеку можна так:
# app.add_handler(CallbackQueryHandler(app_button, pattern='^app_.*'))
app.add_handler(CallbackQueryHandler(random_fact_callback, pattern='^fact_.*'))
app.add_handler(CallbackQueryHandler(talk_character_callback, pattern='^talk_.*'))
app.add_handler(CallbackQueryHandler(quiz_setup_callback, pattern='^quiz_.*'))
app.add_handler(CallbackQueryHandler(default_callback_handler))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
print("Бот працює")
app.run_polling()
