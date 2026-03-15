import logging
import time

from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from src import OPENAI_API_KEY, ASSISTANT_ID, TELEGRAM_TOKEN


# инициализация клиента OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# словарь для хранения thread пользователей
user_threads = {}


# команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🚚 Logistics AI Assistant\n\n"
        "Я AI-аналитик транспортной логистики.\n"
        "Отправь данные для анализа эффективности автопарка."
    )


# обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text
    user_id = update.message.from_user.id

    status_msg = await update.message.reply_text("⏳ Анализирую данные...")

    try:

        # создаём thread или используем существующий
        if user_id in user_threads:
            thread_id = user_threads[user_id]
        else:
            thread = client.beta.threads.create()
            thread_id = thread.id
            user_threads[user_id] = thread_id

        # добавляем сообщение пользователя
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        # запускаем ассистента
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
            max_completion_tokens=800,
            temperature=0.3,
            top_p=1
        )

        # ждём завершения обработки
        while run.status in ("queued", "in_progress"):
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )

        # получаем сообщения
        messages = client.beta.threads.messages.list(thread_id=thread_id)

        response = "Нет ответа от ассистента."

        for msg in messages.data:
            if msg.role == "assistant":
                try:
                    response = msg.content[0].text.value
                    break
                except Exception:
                    continue

        # отправляем ответ
        await status_msg.edit_text(response)

    except Exception as e:

        logger.error(e)

        await status_msg.edit_text(
            "❌ Ошибка при обработке запроса. Попробуйте позже."
        )


# запуск бота
def main():

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Бот запущен")

    app.run_polling()


if __name__ == "__main__":
    main()