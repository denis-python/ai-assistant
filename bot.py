import os
import asyncio
import telegram
from dotenv import load_dotenv

from functools import wraps
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from gpt import ChatGptService
from util import (
    load_message, send_text, send_image, show_main_menu, waiting_message,
    send_text_buttons, send_text_buttons_grid, load_prompt, default_callback_handler
)

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")


class BotModes:
    QUIZ_SETUP = "quiz_setup"
    QUIZ = "quiz_mode"
    GPT = "gpt_mode"
    TALK = "talk_mode"
    TRANSLATOR_SETUP = "translator_setup"  # <-- ДОДАНО для очікування назви мови від користувача
    TRANSLATOR = "translator_mode"
    MOVIES = "movies_mode"


def get_gpt_service(context: ContextTypes.DEFAULT_TYPE) -> ChatGptService:
    if "gpt_instance" not in context.user_data:
        context.user_data["gpt_instance"] = ChatGptService(OPENAI_TOKEN)
    return context.user_data["gpt_instance"]


MAIN_MENU_BUTTONS = {
    "menu_random": "🧠 Випадковий факт",
    "menu_gpt": "🤖 Чат з ChatGPT",
    "menu_talk": "👤 Особистості",
    "menu_quiz": "❓ ШІ-Вікторина",
    "menu_translator": "🌐 Перекладач",
    "menu_movies": "🎬 Кінокритик"
}

QUIZ_THEMES = {
    "quiz_prog": "💻 Програмування на Python",
    "quiz_math": "📐 Математичні теорії",
    "quiz_biology": "🌿 Біологія та природа"
}


def check_user_status(func):
    """Декоратор, який перевіряє, чи не знаходиться користувач в активному режимі."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        current_mode = context.user_data.get("mode")
        if current_mode and not update.callback_query:
            btn_callback = "gpt_end"
            btn_text = "Закінчити поточний режим"
            if current_mode == BotModes.QUIZ:
                btn_callback = "quiz_end"
                btn_text = "Вийти з квізу"
            await send_text_buttons(
                update,
                context,
                "❗️ **Дія заблокована!**\n\nВи перебуваєте всередині активного режиму. "
                "Будь ласка, продовжіть сеанс або завершіть за допомогою кнопки нижче!",
                buttons={btn_callback: btn_text}
            )
            return
        return await func(update, context, *args, **kwargs)

    return wrapper


async def handle_ai_request(update: Update, context: ContextTypes.DEFAULT_TYPE, waiting_text: str, exit_btn_text: str,
                            callback_data: str, user_text: str, prompt_text: str = None, extra_buttons: dict = None):
    async with waiting_message(update, context, waiting_text):
        user_gpt = get_gpt_service(context)
        if prompt_text:
            ai_response = await user_gpt.send_question(prompt_text=prompt_text, message_text=user_text)
        else:
            ai_response = await user_gpt.add_message(user_text)
    final_buttons = extra_buttons or {}
    final_buttons[callback_data] = exit_btn_text

    await send_text_buttons(update, context, ai_response, final_buttons)


async def activate_translator(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_name: str):
    """Універсальна функція для активації режиму перекладу та ініціалізації промпту"""
    user_gpt = get_gpt_service(context)
    full_prompt = f"{load_prompt('translator')}\nЦільова іноземна мова: {lang_name}."

    user_gpt.set_prompt(full_prompt)
    context.user_data["translator_prompt"] = full_prompt
    context.user_data["mode"] = BotModes.TRANSLATOR

    welcome_msg = (
        f"🔄 **Двосторонній автопереклад активовано!**\n\n"
        f"Напишіть мені будь-яку фразу, і я миттєво перекладу її на мову (*{lang_name}*) або назад українською:"
    )
    await send_text_buttons(update, context, welcome_msg, {
        "trans_change": "🔄 Змінити мову",
        "gpt_end": "❌ Скасувати переклад"
    })


@check_user_status
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = None

    if update.callback_query:
        await update.callback_query.answer()
        await send_image(update, context, 'main')
        await send_text_buttons_grid(update, context,
                                     "**Головне ШІ-Меню Помічника**\n\nВиберіть потрібний режим роботи:",
                                     buttons=MAIN_MENU_BUTTONS)
        return

    text = load_message('main')
    await send_image(update, context, 'main')
    await send_text_buttons(update, context, text, {"open_menu": "🚀 Поїхали! Відкрити ШІ-Меню"})

    await show_main_menu(update, context, {
        'start': 'Головне меню',
        'random': 'Дізнатися випадковий цікавий факт',
        'gpt': 'Задати питання чату GPT',
        'talk': 'Поговорити з відомою особистістю',
        'quiz': 'Взяти участь у квізі',
        'translator': 'Переклад тексту',
        'movies': 'Добірка кінокритика'
    })


async def open_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, 'main')
    await send_text_buttons_grid(update, context,
                                 "**Головне ШІ-Меню Помічника**\n\nВиберіть потрібний режим роботи з асистентом:",
                                 buttons=MAIN_MENU_BUTTONS)


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


@check_user_status
async def random_fact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = None
    await send_image(update, context, "random")

    welcome_text = load_message("random")
    async with waiting_message(update, context, welcome_text):
        prompt = load_prompt("random")
        user_gpt = get_gpt_service(context)
        ai_response = await user_gpt.send_question(prompt_text=prompt,
                                                   message_text="Розкажи один випадковий цікавий факт")

    buttons = {"fact_more": "🚀 Хочу ще факт!", "fact_end": "✅ Закінчити"}
    await send_text_buttons(update, context, ai_response, buttons)


async def random_fact_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query_data = update.callback_query.data

    if query_data == "fact_more":
        await random_fact_handler(update, context)
    elif query_data == "fact_end":
        await open_main_menu_callback(update, context)


@check_user_status
async def gpt_interface_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, "gpt")
    user_gpt = get_gpt_service(context)
    user_gpt.set_prompt(load_prompt("gpt"))
    context.user_data["mode"] = BotModes.GPT
    await send_text_buttons(update, context, load_message("gpt"), {"gpt_end": "⬅️ Назад в меню"})


@check_user_status
async def talk_character_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = None
    await send_image(update, context, "talk")

    characters = {
        "talk_cobain": "🎸 Курт Кобейн",
        "talk_queen": "👑 Єлизавета II",
        "talk_tolkien": "🧝‍♂️ Джон Толкін",
        "talk_nietzsche": "🧠 Фрідріх Ніцше",
        "talk_hawking": "🌌 Стівен Гокінг",
        "talk_end": "⬅️ Назад в меню"
    }
    await send_text_buttons(update, context, load_message("talk"), characters)


async def talk_character_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query_data = update.callback_query.data
    if query_data == "talk_end":
        return

    user_gpt = get_gpt_service(context)
    user_gpt.set_prompt(load_prompt(query_data))
    context.user_data["mode"] = BotModes.TALK

    names = {
        "cobain": "Курта Кобейна 🎸",
        "queen": "Єлизавети II 👑",
        "tolkien": "Джона Толкіна 🧝‍♂️",
        "nietzsche": "Фрідріха Ніцше 🧠",
        "hawking": "Стівена Гокінга 🌌"
    }
    chosen_name = names.get(query_data.replace("talk_", ""), "обраного персонажа")

    await send_text(update, context,
                    f"✨ Успішно! ChatGPT перевтілився в {chosen_name}.\n"
                    f"Напишіть йому будь-що, і він відповість у своєму новому образі:"
                    )


async def ask_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt_text: str):
    """Універсальна функція для запиту питання до ШІ"""
    async with waiting_message(update, context, "🧠 ChatGPT готує питання..."):
        user_gpt = get_gpt_service(context)
        instruction = f"{prompt_text}. Задай строго ОДНЕ питання. Без списків, без вступу!"
        return await user_gpt.add_message(instruction)


@check_user_status
async def quiz_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = BotModes.QUIZ
    await send_image(update, context, "quiz")

    if context.user_data.get("quiz_score") is None:
        context.user_data["quiz_score"] = 0

    quiz_buttons = QUIZ_THEMES.copy()
    quiz_buttons["quiz_end"] = "⬅️ Назад в меню"
    await send_text_buttons(update, context, load_message("quiz"), quiz_buttons)


async def quiz_setup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query_data = update.callback_query.data

    if query_data == "quiz_more":
        current_theme = context.user_data.get("quiz_theme")
        question = await ask_quiz_question(update, context, current_theme)
        await send_text(update, context, question)
        return

    if query_data == "quiz_end":
        score = context.user_data.get("quiz_score", 0)
        total = context.user_data.get("quiz_step", 0)
        if total == 0:
            success_percentage = 0
        else:
            success_percentage = round((score / total) * 100, 1)

        await update.callback_query.edit_message_text(
            text=f"🏁 **КВІЗ ОФІЦІЙНО ЗАВЕРШЕНО!**\n\n📊 **Статистика:**\n"
                 f"✅ Правильних: `{score}`\n📝 Всього питань: `{total}`\n"
                 f"🎯 Точність: `{success_percentage}%` 🎯\n\nПовертаємось до головного меню..."
        )
        context.user_data.update({"quiz_score": 0, "quiz_step": 0, "mode": None})
        await asyncio.sleep(4)
        await open_main_menu_callback(update, context)
        return

    if query_data == "quiz_change_theme":
        context.user_data["mode"] = None
        await quiz_handler(update, context)
        return

    user_gpt = get_gpt_service(context)
    user_gpt.set_prompt(load_prompt("quiz"))
    context.user_data.setdefault("quiz_step", 0)
    context.user_data.setdefault("quiz_score", 0)
    theme_name = QUIZ_THEMES.get(query_data, "загальну тему")
    await send_text(update, context, f"🚩 Обрано тему: {theme_name}.")
    context.user_data["quiz_theme"] = query_data
    question = await ask_quiz_question(update, context, query_data)
    await send_text(update, context, question)


@check_user_status
async def translator_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = None
    await send_image(update, context, "translator")

    trans_buttons = {
        "trans_en": "🇺🇸 Англійська",
        "trans_de": "🇩🇪 Німецька",
        "trans_fr": "🇫🇷 Французька",
        "trans_es": "🇪🇸 Іспанська",
        "trans_other": "✍️ Інша мова",
        "gpt_end": " ⬅️ Назад в меню"
    }
    await send_text_buttons_grid(
        update,
        context,
        "Привіт! Я твій інтелектуальний ШІ-Перекладач.\nВибери мову, на яку потрібно перекласти твій наступний текст, або натисни 'Інша мова':",
        trans_buttons
    )


@check_user_status
async def translator_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query_data = update.callback_query.data
    if query_data == "trans_change":
        await translator_handler(update, context)
        return
    if query_data == "trans_other":
        context.user_data["mode"] = BotModes.TRANSLATOR_SETUP
        await send_text(update, context, "✍️ Напишіть назву мови, на яку ви хочете перекладати (наприклад: *Італійська*, *Польська*, *Японська*):")
        return

    languages = {
        "trans_en": "англійську 🇺🇸", "trans_de": "німецьку 🇩🇪",
        "trans_fr": "французьку 🇫🇷", "trans_es": "іспанську 🇪🇸"
    }
    lang = languages.get(query_data, "англійську")
    await activate_translator(update, context, lang)


@check_user_status
async def movies_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = BotModes.MOVIES
    await send_image(update, context, "movies")

    welcome_movies = (
        "🎬 **Ласкаво запрошую до ШІ-Кінокритика!**\n\n"
        "Напишіть мені через кому кілька ваших улюблені фільмів чи акторів.\n\n"
        "🧠 ChatGPT створить ексклюзивну підбірку особисто під ваш смак!"
    )
    await send_text_buttons(update, context, welcome_movies, {"gpt_end": " ⬅️ Назад в меню"})


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    current_mode = context.user_data.get("mode")
    if user_text and user_text.startswith('/'):
        return

    if not current_mode or current_mode == BotModes.QUIZ_SETUP:
        await send_text(update, context, "Будь ласка, виберіть режим або тему роботи в меню.")
        return

    try:
        if current_mode == BotModes.TRANSLATOR_SETUP:
            await activate_translator(update, context, user_text)
            return
        elif current_mode == BotModes.GPT:
            await handle_ai_request(update, context, "🧠 ChatGPT думає...", "✅ Закінчити діалог", "gpt_end", user_text)
        elif current_mode == BotModes.TALK:
            await handle_ai_request(update, context, "🎭 Персонаж міркує...", "✅ Закінчити розмову", "talk_end",
                                    user_text)
        elif current_mode == BotModes.TRANSLATOR:
            current_prompt = context.user_data.get("translator_prompt", load_prompt("translator"))
            await handle_ai_request(
                update, context, "🔄 Перекладаю...", "✅ Закінчити переклад", "gpt_end", user_text,
                prompt_text=current_prompt, extra_buttons={"trans_change": "🔄 Змінити мову"}
            )
        elif current_mode == BotModes.QUIZ:
            async with waiting_message(update, context, "🔄 Перевіряю відповідь та готую наступне питання..."):
                user_gpt = get_gpt_service(context)
                ai_response = await user_gpt.add_message(user_text)

            normalized = ai_response.lower()
            if any(word in normalized for word in ["правильно", "вірно", "молодець"]) and "не" not in normalized:
                context.user_data["quiz_score"] = context.user_data.get("quiz_score", 0) + 1
            context.user_data["quiz_step"] = context.user_data.get("quiz_step", 0) + 1

            quiz_step_buttons = {
                "quiz_more": "🚀 Ще питання на цю тему",
                "quiz_change_theme": "🔄 Змінити тему",
                "quiz_end": "✅ Закінчити квіз"
            }
            current_score = context.user_data.get("quiz_score", 0)
            current_step = context.user_data.get("quiz_step", 0)

            await send_text_buttons(
                update, context,
                f"{ai_response}\n\n🏆 Рахунок: {current_score} з {current_step}",
                quiz_step_buttons
            )
        elif current_mode == BotModes.MOVIES:
            movie_query = f"Мої улюблені фільми: {user_text}"
            await handle_ai_request(update, context, "🍿 ШІ-Кінокритик сканує базу кінематографу...",
                                    "Закінчити підбір фільмів", "gpt_end", movie_query, load_prompt("movies"))

    except telegram.error.TelegramError as error:
        print(f"Помилка Telegram API: {error}")
        await send_text(update, context, "⚠️ **Виникла помилка мережі.**\nСпробуйте ще раз!")
    except Exception as error:
        print(f"Критична помилка: {error}")
        await send_text(update, context, "🤖 **Сервери ШІ тимчасово перевантажені.**\nСпробуйте ще раз!")


app = ApplicationBuilder().token(BOT_TOKEN).concurrent_updates(True).build()

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