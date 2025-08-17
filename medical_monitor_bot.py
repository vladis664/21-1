from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageAction
import tempfile
import os
import logging
import asyncio
from datetime import datetime, timezone
import hashlib
from typing import Set, Optional
from media_utils import MediaHandler, MessageProcessor

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('medical_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
API_ID = int(os.getenv('API_ID', '27717201'))
API_HASH = os.getenv('API_HASH', 'f64bbdb83fc622bcc52f2740348457c3')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8325424545:AAEOUPCJYp0KFjnNUoTwUmzRfOkGt798dQE')

# Конфигурация каналов
SOURCE_CHANNELS = [
    "https://t.me/docters_smp",
    "https://t.me/onco_beseda",
    "https://t.me/minzdrav_ru",
    "https://t.me/immunobee",
    "https://t.me/PSOmedics",
    "https://t.me/DrButriy",
    "https://t.me/dr_komarovskiy",
    "https://t.me/mediamedics",
    "https://t.me/medach",
    "https://t.me/redcross_ru",
    "https://t.me/oncolya",
    "https://t.me/ru2ch_ban",
    "https://t.me/pornhub_pr",
    "https://t.me/Eric_Davidich_D3",
    "https://t.me/labkovskiy",
    "https://t.me/toplesofficial",
    "https://t.me/naebnet",
    "https://t.me/Wylsared"
]

DESTINATION_CHANNEL = "@medical_news_aggregator"  # Целевой канал

# Временные рамки мониторинга
START_DATE = datetime(2025, 8, 17, 20, 0, 0, tzinfo=timezone.utc)
END_DATE = datetime(2026, 8, 17, 20, 0, 0, tzinfo=timezone.utc)

# Множество для отслеживания уже обработанных сообщений (защита от дублирования)
processed_messages: Set[str] = set()

# Создание клиента
client = TelegramClient('medical_monitor_bot', API_ID, API_HASH)

def generate_message_hash(event) -> str:
    """Генерирует уникальный хеш для сообщения на основе его содержимого"""
    message_data = f"{event.chat_id}_{event.message.id}_{event.message.date}"
    if event.message.text:
        message_data += event.message.text
    if event.message.media:
        message_data += str(event.message.media)
    return hashlib.md5(message_data.encode()).hexdigest()

def is_within_monitoring_period(message_date: datetime) -> bool:
    """Проверяет, находится ли сообщение в рамках периода мониторинга"""
    return START_DATE <= message_date <= END_DATE

async def check_bot_permissions():
    """Проверяет права бота в целевом канале"""
    try:
        chat = await client.get_entity(DESTINATION_CHANNEL)
        participant = await client.get_permissions(chat)
        
        if not participant.is_admin:
            logger.warning("Бот не является администратором целевого канала!")
            return False
            
        logger.info("Права бота в целевом канале проверены успешно")
        return True
    except Exception as e:
        logger.error(f"Ошибка при проверке прав бота: {e}")
        return False

async def download_media_with_retry(event, max_retries: int = 3) -> Optional[str]:
    """Скачивает медиа с повторными попытками"""
    return await MediaHandler.download_media_with_retry(event, max_retries)

async def send_large_file(file_path: str, caption: str = None):
    """Отправляет большой файл с разбивкой на части при необходимости"""
    try:
        file_size = os.path.getsize(file_path)
        max_size = 50 * 1024 * 1024  # 50 MB
        
        if file_size > max_size:
            logger.warning(f"Файл слишком большой ({file_size} bytes), попытка отправки...")
        
        await client.send_file(
            entity=DESTINATION_CHANNEL,
            file=file_path,
            caption=caption,
            supports_streaming=True
        )
        logger.info("Файл отправлен успешно")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке файла: {e}")
        raise

@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def handle_new_message(event):
    """Обработчик новых сообщений"""
    try:
        # Проверяем, нужно ли обрабатывать сообщение
        if not MessageProcessor.should_process_message(event):
            logger.info("Сообщение пропущено (служебное или пустое)")
            return
            
        # Проверяем период мониторинга
        if not is_within_monitoring_period(event.message.date):
            logger.info(f"Сообщение вне периода мониторинга: {event.message.date}")
            return
            
        # Проверяем на дублирование
        message_hash = generate_message_hash(event)
        if message_hash in processed_messages:
            logger.info("Сообщение уже обработано (дубликат)")
            return
            
        # Извлекаем содержимое сообщения
        message_text, has_photo, media_type = MessageProcessor.extract_message_content(event)
        
        logger.info(f"Обрабатывается новое сообщение из {event.chat.title} (тип медиа: {media_type})")

        if has_photo:
            # Скачиваем фото
            photo_path = await download_media_with_retry(event)
            if not photo_path:
                logger.error("Не удалось скачать фото")
                return
                
            try:
                # Получаем информацию о файле
                file_info = MediaHandler.get_media_info(photo_path)
                logger.info(f"Скачан файл: {file_info.get('size_formatted', 'N/A')} {file_info.get('extension', '')}")
                
                # Создаем подпись с ограничением длины
                caption = MessageProcessor.create_caption(message_text) if message_text else None
                
                # Отправляем фото с подписью
                await send_large_file(photo_path, caption)
                logger.info("Отправлено фото с текстом" if caption else "Отправлено фото")
                
            finally:
                # Удаляем временный файл
                MediaHandler.cleanup_temp_files(photo_path)
        else:
            # Отправляем только текст
            await client.send_message(
                entity=DESTINATION_CHANNEL,
                message=message_text
            )
            logger.info("Отправлен текст")
            
        # Добавляем сообщение в обработанные
        processed_messages.add(message_hash)
        
        # Ограничиваем размер множества обработанных сообщений
        if len(processed_messages) > 10000:
            processed_messages.clear()
            logger.info("Очищено множество обработанных сообщений")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {str(e)}")
        # Удаляем временный файл при ошибке
        if 'photo_path' in locals() and os.path.exists(photo_path):
            MediaHandler.cleanup_temp_files(photo_path)

async def main():
    """Основная функция запуска бота"""
    try:
        logger.info("Запуск медицинского мониторинг-бота...")
        
        # Запускаем клиент
        await client.start(bot_token=BOT_TOKEN)
        logger.info("Клиент Telegram успешно запущен")
        
        # Проверяем права бота
        if not await check_bot_permissions():
            logger.error("Бот не имеет необходимых прав в целевом канале!")
            return
            
        # Выводим информацию о мониторинге
        logger.info(f"Мониторинг запущен для {len(SOURCE_CHANNELS)} каналов")
        logger.info(f"Период мониторинга: {START_DATE} - {END_DATE}")
        logger.info(f"Целевой канал: {DESTINATION_CHANNEL}")
        
        # Запускаем бота
        await client.run_until_disconnected()
        
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await client.disconnect()
        logger.info("Бот завершил работу")

if __name__ == '__main__':
    asyncio.run(main())
