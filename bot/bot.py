import os
import asyncio
import time
from telegram import Update, Document
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from openai import OpenAI
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env (если он есть)
load_dotenv()

# Читаем секреты из окружения (заполните либо .env, либо параметры ниже)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-...")        # ваш API‑ключ
ASSISTANT_ID = os.getenv("ASSISTANT_ID", "asst_...")          # ID ассистента
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "...")
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID", "vs_...")      # ID векторного хранилища

# Инициализируем клиента OpenAI
client = OpenAI(
    api_key=OPENAI_API_KEY,
    default_headers={"OpenAI-Beta": "assistants=v2"},
)

# Словарь для хранения потоков (thread_id) для каждого пользователя
user_threads: dict[int, str] = {}

# Создаём папку для загрузки файлов, если её нет
os.makedirs("downloads", exist_ok=True)

def attach_vector_store_to_assistant() -> None:
    """
    Привязывает векторное хранилище и включает web-search для ассистента.
    Эта операция выполняется один раз при запуске бота.
    """
    try:
        client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            tools=[
                {"type": "file_search"},
                {"type": "web_search"},
            ],
            tool_resources={
                "file_search": {"vector_store_ids": [VECTOR_STORE_ID]},
                # для web_search ресурсов не требуется
            },
        )
        print(f"🔗 Ассистент {ASSISTANT_ID} обновлён: подключены file_search и web_search.")
    except Exception as e:
        print(f"⚠️ Не удалось обновить ассистента: {e}")

async def reset_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сбрасывает контекст диалога для текущего пользователя."""
    user_id = update.effective_user.id
    if user_threads.pop(user_id, None):
        await update.message.reply_text("Контекст диалога сброшен.")
    else:
        await update.message.reply_text("Нет активного диалога для сброса.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения и отправляет их ассистенту."""
    user_id = update.effective_user.id
    thread_id = user_threads.get(user_id)
    # Создаём новый поток для пользователя, если его нет
    if not thread_id:
        thread = client.beta.threads.create()
        thread_id = thread.id
        user_threads[user_id] = thread_id

    # Добавляем сообщение пользователя в поток
    user_text = update.message.text
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_text,
    )

    # Запускаем ассистента и отправляем ответ
    await run_assistant_and_respond(update, thread_id)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает документы, загружает их в OpenAI и прикрепляет к векторному хранилищу."""
    document: Document = update.message.document
    user_id = update.effective_user.id
    thread_id = user_threads.get(user_id)
    if not thread_id:
        thread = client.beta.threads.create()
        thread_id = thread.id
        user_threads[user_id] = thread_id

    # Скачиваем файл во временную папку
    file_path = f"downloads/{document.file_unique_id}_{document.file_name}"
    tg_file = await context.bot.get_file(document.file_id)
    await tg_file.download_to_drive(file_path)

    try:
        # Загружаем файл в OpenAI
        with open(file_path, "rb") as f:
            uploaded = client.files.create(file=f, purpose="assistants")

        # Привязываем файл к векторному хранилищу
        client.vector_stores.files.create(
            vector_store_id=VECTOR_STORE_ID,
            file_id=uploaded.id,
        )

        await update.message.reply_text("✅ Файл добавлен в базу знаний ассистента.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обработке файла: {e}")

async def run_assistant_and_respond(update: Update, thread_id: str) -> None:
    """Запускает ассистента для указанного потока и отправляет пользователю последний текстовый ответ."""
    # Создаём run без tool_resources: векторное хранилище и web-search уже привязаны к ассистенту
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID,
    )

    # Ожидаем завершения run с таймаутом
    timeout = 60  # секунд
    start_time = time.time()
    while time.time() - start_time < timeout:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id,
        )
        if run_status.status == "completed":
            break
        elif run_status.status == "failed":
            await update.message.reply_text("❌ Ошибка при выполнении запроса.")
            return
        await asyncio.sleep(1)
    else:
        await update.message.reply_text("⏰ Время ожидания ответа истекло.")
        return

    # Получаем несколько последних сообщений и ищем текстовый ответ ассистента
    messages = client.beta.threads.messages.list(
        thread_id=thread_id,
        order="desc",
        limit=10,
    )
    for msg in messages.data:
        if msg.role == "assistant":
            text_parts = [
                part.text.value
                for part in msg.content
                if part.type == "text"
            ]
            if text_parts:
                await update.message.reply_text("\n".join(text_parts))
                return

    # Если текстового ответа нет
    await update.message.reply_text("🤷 Ассистент не сгенерировал текстовый ответ.")

def run_telegram_bot() -> None:
    """Запускает Telegram-бота и обновляет ассистента перед началом работы."""
    # Обновляем ассистента: привязываем векторное хранилище и активируем web-search
    attach_vector_store_to_assistant()

    # Строим и запускаем Telegram‑бота
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Команда /reset для сброса диалога
    app.add_handler(CommandHandler("reset", reset_dialog))
    # Обработчик документов
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    # Обработчик текстовых сообщений (все, кроме команд)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Бот запущен и готов принимать сообщения и файлы.")
    app.run_polling()

if __name__ == "__main__":
    run_telegram_bot()
