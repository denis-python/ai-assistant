import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from gpt import ChatGptService
from util import (
    load_message, send_text, send_image, show_main_menu,
    send_text_buttons, load_prompt, default_callback_handler
)

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")


def get_main_menu_markup() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🧠 Випадковий факт", callback_data="menu_random"),
         InlineKeyboardButton("🤖 Чат з ChatGPT", callback_data="menu_gpt")],
        [InlineKeyboardButton("👤 Особистості", callback_data="menu_talk"),
         InlineKeyboardButton("❓ ШІ-Вікторина", callback_data="menu_quiz")],
        [InlineKeyboardButton("🌐 Перекладач", callback_data="menu_translator"),
         InlineKeyboardButton("🎬 Кінокритик", callback_data="menu_movies")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def is_user_busy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    current_mode = context.user_data.get("mode")
    if current_mode and not update.callback_query:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ **Дія заблокована!**\n\nВи перебуваєте всередині активного режиму. "
                 "Будь ласка, спочатку завершіть поточний сеанс за допомогою кнопки **[ ✅ Закінчити ]**!"
        )
        return True
    return False


async def handle_ai_request(update: Update, context: ContextTypes.DEFAULT_TYPE, waiting_text: str, exit_btn_text: str,
                            callback_data: str, user_text: str):
    chat_id = update.effective_chat.id
    waiting = await send_text(update, context, waiting_text)
    ai_response = await chat_gpt.add_message(user_text)
    await context.bot.delete_message(chat_id=chat_id, message_id=waiting.message_id)
    markup = InlineKeyboardMarkup([[InlineKeyboardButton(exit_btn_text, callback_data=callback_data)]])
    await context.bot.send_message(chat_id=chat_id, text=ai_response, reply_markup=markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_user_busy(update, context):
        return

    context.user_data["mode"] = None
    chat_id = update.effective_chat.id

    if update.callback_query:
        await update.callback_query.answer()
        await send_image(update, context, 'main')
        await context.bot.send_message(
            chat_id=chat_id,
            text="🤖 **Головне ШІ-Меню Помічника** 🤖\n\nВиберіть потрібний режим роботи:",
            reply_markup=get_main_menu_markup()
        )
        return

    text = load_message('main')
    await send_image(update, context, 'main')
    await send_text_buttons(update, context, text, {"open_menu": "Поїхали! 🚀 Відкрити ШІ-Меню"})

    await show_main_menu(update, context, {
        'start': 'Головне меню',
        'random': 'Дізнатися випадковий цікавий факт 🧠',
        'gpt': 'Задати питання чату GPT 🤖',
        'talk': 'Поговорити з відомою особистістю 👤',
        'quiz': 'Взяти участь у квізі ❓',
        'translator': 'Переклад тексту 🌐',
        'movies': 'Добірка кінокритика🎬'
    })


async def open_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, 'main')
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🤖 **Головне ШІ-Меню Помічника** 🤖\n\nВиберіть потрібний режим роботи з асистентом:",
        reply_markup=get_main_menu_markup()
    )


async def main_menu_navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query_data = update.callback_query.data

    modes = {
        "menu_random": random_fact_handler,
        "menu_gpt": gpt_interface_handler,
        "menu_talk": talk_character_handler,
        "menu_quiz": quiz_handler,
        "menu_translator": translator_handler,
        "menu_movies": movies_handler
    }

    handler = modes.get(query_data)
    if handler:
        await handler(update, context)


async def random_fact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_user_busy(update, context):
        return
    context.user_data["mode"] = None
    await send_image(update, context, "random")

    welcome_text = load_message("random")
    waiting_msg = await send_text(update, context, welcome_text)

    prompt = load_prompt("random")
    ai_response = await chat_gpt.send_question(prompt_text=prompt, message_text="Розкажи один випадковий цікавий факт")

    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=waiting_msg.message_id)
    buttons = {"fact_more": "🚀 Хочу ще факт!", "fact_end": "✅ Закінчити"}
    await send_text_buttons(update, context, ai_response, buttons)


async def random_fact_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query_data = update.callback_query.data

    if query_data == "fact_more":
        await random_fact_handler(update, context)
    elif query_data == "fact_end":
        await open_main_menu_callback(update, context)


async def gpt_interface_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_user_busy(update, context):
        return
    await send_image(update, context, "gpt")
    chat_gpt.set_prompt(load_prompt("gpt"))
    context.user_data["mode"] = "gpt_mode"
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад в меню", callback_data="gpt_end")]])
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=load_message("gpt"),
        reply_markup=markup
    )


async def talk_character_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_user_busy(update, context):
        return
    context.user_data["mode"] = None
    await send_image(update, context, "talk")

    characters = {
        "talk_cobain": "🎸 Курт Кобейн",
        "talk_queen": "👑 Єлизавета II",
        "talk_tolkien": "🧝‍♂️ Джон Толкін",
        "talk_nietzsche": "🧠 Фрідріх Ніцше",
        "talk_hawking": "🌌 Стівен Гокінг"
    }
    await send_text_buttons(update, context, load_message("talk"), characters)


async def talk_character_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query_data = update.callback_query.data
    if query_data == "talk_end":
        return

    chat_gpt.set_prompt(load_prompt(query_data))
    context.user_data["mode"] = "talk_mode"

    names = {
        "cobain": "Курта Кобейна 🎸",
        "queen": "Єлизавети II 👑",
        "tolkien": "Джона Толкіна 🧝‍♂️",
        "nietzsche": "Фрідріха Ніцше 🧠",
        "hawking": "Стівена Гокінга 🌌"
    }
    chosen_name = names.get(query_data.replace("talk_", ""), "обраного персонажа")

    await update.callback_query.edit_message_text(
        text=f"✨ Успішно! ChatGPT перевтілився в {chosen_name}.\n"
             f"Напишіть йому будь-що, і він відповість у своєму новому образі:"
    )


async def quiz_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_user_busy(update, context):
        return
    context.user_data["mode"] = "quiz_setup"
    await send_image(update, context, "quiz")

    if context.user_data.get("quiz_score") is None:
        context.user_data["quiz_score"] = 0

    keyboard = [
        [InlineKeyboardButton("💻 Програмування (Python)", callback_data="quiz_prog")],
        [InlineKeyboardButton("📐 Математичні теорії", callback_data="quiz_math")],
        [InlineKeyboardButton("🌿 Біологія та природа", callback_data="quiz_biology")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="quiz_end")]
    ]

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=load_message("quiz"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def quiz_setup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query_data = update.callback_query.data

    if query_data == "quiz_more":
        await update.callback_query.edit_message_text(text="🧠 ChatGPT генерує нове питання...")
        next_q = await chat_gpt.add_message("quiz_more. Задай строго ОДНЕ наступне питання. Без списків!")
        await send_text(update, context, next_q)
        return

    if query_data == "quiz_end":
        score = context.user_data.get("quiz_score", 0)
        total = max(context.user_data.get("quiz_step", 1) - 1, 1)
        if score > total:
            total = score

        pct = round((score / total) * 100, 1)

        await update.callback_query.edit_message_text(
            text=f"🏁 **КВІЗ ОФІЦІЙНО ЗАВЕРШЕНО!**\n\n📊 **Статистика:**\n"
                 f"✅ Правильних: `{score}`\n📝 Всього питань: `{total}`\n"
                 f"🎯 Точність: `{pct}%` 🎯\n\nПовертаємось до головного меню..."
        )
        context.user_data.update({"quiz_score": 0, "quiz_step": 1, "mode": None})
        await asyncio.sleep(4)
        await open_main_menu_callback(update, context)
        return

    if query_data == "quiz_change_theme":
        context.user_data["mode"] = None
        await quiz_handler(update, context)
        return

    chat_gpt.set_prompt(load_prompt("quiz"))
    context.user_data["mode"] = "quiz_mode"

    themes = {
        "quiz_prog": "Програмування на Python 💻",
        "quiz_math": "Математичні теорії 📐",
        "quiz_biology": "Біологія та природа 🌿"
    }
    await update.callback_query.edit_message_text(
        text=f"🚩 Обрано тему: {themes.get(query_data, 'загальну тему')}.\n🧠 ChatGPT готує перше питання..."
    )
    first_q = await chat_gpt.add_message(f"{query_data} Задай строго ОДНЕ перше питання. Не пиши список!")
    await send_text(update, context, first_q)


async def translator_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_user_busy(update, context):
        return
    context.user_data["mode"] = None
    await send_image(update, context, "translator")

    keyboard = [
        [InlineKeyboardButton("🇺🇸 Англійська", callback_data="trans_en"),
         InlineKeyboardButton("🇩🇪 Німецька", callback_data="trans_de")],
        [InlineKeyboardButton("🇫🇷 Французька", callback_data="trans_fr"),
         InlineKeyboardButton("🇪🇸 Іспанська", callback_data="trans_es")]
    ]
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привіт! Я твій інтелектуальний ШІ-Перекладач. 🌐\n"
             "Виберіть мову, на яку потрібно перекласти ваш наступний текст:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def translator_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query_data = update.callback_query.data

    if await is_user_busy(update, context):
        return

    languages = {
        "trans_en": "англійську 🇺🇸", "trans_de": "німецьку 🇩🇪",
        "trans_fr": "французьку 🇫🇷", "trans_es": "іспанську 🇪🇸"
    }
    lang = languages.get(query_data, "англійську")
    chat_gpt.set_prompt(f"{load_prompt('translator')}\nЦільова іноземна мова: {lang}.")
    context.user_data["mode"] = "translator_mode"

    markup = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Скасувати переклад", callback_data="gpt_end")]])

    await update.callback_query.edit_message_text(
        text=f"🔄 **Двосторонній автопереклад активовано!**\n\n"
             f"Напишіть мне будь-яку фразу, і я миттєво перекладу її на {lang} або назад українською:",
        reply_markup=markup
    )


async def movies_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_user_busy(update, context):
        return

    context.user_data["mode"] = "movies_mode"
    await send_image(update, context, "movies")

    markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад в меню", callback_data="gpt_end")]])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🎬 **Ласкаво запрошую до ШІ-Кінокритика!**\n\n"
             "Напишіть мені через кому кілька ваших улюблені фільмів чи акторів.\n\n"
             "🧠 ChatGPT створить ексклюзивну підбірку особисто під ваш смак!",
        reply_markup=markup
    )


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text
    current_mode = context.user_data.get("mode")

    if not current_mode or current_mode == "quiz_setup":
        await send_text(update, context, "Будь ласка, виберіть режим або тему роботи в меню.")
        return

    try:
        if current_mode == "gpt_mode":
            await handle_ai_request(update, context, "🧠 ChatGPT думає...", "✅ Закінчити діалог", "gpt_end", user_text)

        elif current_mode == "talk_mode":
            await handle_ai_request(update, context, "🎭 Персонаж обмірковує відповідь...", "✅ Закінчити розмову",
                                    "talk_end", user_text)

        elif current_mode == "translator_mode":
            await handle_ai_request(update, context, "🔄 Перекладаю...", "✅ Закінчити переклад", "gpt_end", user_text)

        elif current_mode == "quiz_mode":
            waiting = await send_text(update, context, "🔄 Перевіряю відповідь та готую наступне питання...")
            ai_response = await chat_gpt.add_message(user_text)
            normalized = ai_response.lower()

            if any(word in normalized for word in ["правильно", "вірно", "молодець"]) and "не" not in normalized:
                context.user_data["quiz_score"] = context.user_data.get("quiz_score", 0) + 1

            context.user_data["quiz_step"] = context.user_data.get("quiz_step", 1) + 1
            await context.bot.delete_message(chat_id=chat_id, message_id=waiting.message_id)

            keyboard = [
                [InlineKeyboardButton("🚀 Ще питання на цю тему", callback_data="quiz_more")],
                [InlineKeyboardButton("🔄 Змінити тему", callback_data="quiz_change_theme")],
                [InlineKeyboardButton("✅ Закінчити квіз", callback_data="quiz_end")]
            ]
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"{ai_response}\n\n🏆 Поточний рахунок: {context.user_data['quiz_score']} балів",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif current_mode == "movies_mode":
            waiting = await send_text(update, context, "🍿 ШІ-Кінокритик сканує базу кінематографу...")
            ai_response = await chat_gpt.send_question(prompt_text=load_prompt("movies"),
                                                       message_text=f"Мої улюблені фільми: {user_text}")
            await context.bot.delete_message(chat_id=chat_id, message_id=waiting.message_id)
            markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("✅ Закінчити підбір фільмів", callback_data="gpt_end")]])
            await context.bot.send_message(chat_id=chat_id, text=ai_response, reply_markup=markup)

    except Exception as error:
        print(f"🚨 Помилка: {error}")
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=waiting.message_id)
        except Exception:
            pass
        await send_text(update, context, "⚠️ **Сервери ШІ тимчасово перевантажені.**\nСпробуйте ще раз!")


chat_gpt = ChatGptService(OPENAI_TOKEN)
app = ApplicationBuilder().token(BOT_TOKEN).build()

commands = {
    'start': start, 'random': random_fact_handler, 'gpt': gpt_interface_handler,
    'talk': talk_character_handler, 'quiz': quiz_handler, 'translator': translator_handler,
    'movies': movies_handler
}
for cmd, handler in commands.items():
    app.add_handler(CommandHandler(cmd, handler))

app.add_handler(CallbackQueryHandler(start, pattern='^gpt_end$'))
app.add_handler(CallbackQueryHandler(start, pattern='^talk_end$'))
app.add_handler(CallbackQueryHandler(open_main_menu_callback, pattern='^open_menu$'))
app.add_handler(CallbackQueryHandler(main_menu_navigation_callback, pattern='^menu_.*'))
app.add_handler(CallbackQueryHandler(translator_callback, pattern='^trans_.*'))
app.add_handler(CallbackQueryHandler(random_fact_callback, pattern='^fact_.*'))
app.add_handler(CallbackQueryHandler(talk_character_callback, pattern='^talk_.*'))
app.add_handler(CallbackQueryHandler(quiz_setup_callback, pattern='^quiz_.*'))
app.add_handler(CallbackQueryHandler(default_callback_handler))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

print("Бот працює")
app.run_polling()
