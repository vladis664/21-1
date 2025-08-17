"""
Утилиты для работы с медиа файлами в медицинском мониторинг-боте
"""

import os
import tempfile
import logging
from typing import Optional, Tuple
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
import asyncio

logger = logging.getLogger(__name__)

class MediaHandler:
    """Класс для обработки медиа файлов"""
    
    SUPPORTED_PHOTO_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    SUPPORTED_VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.mkv'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Получает расширение файла"""
        return os.path.splitext(filename.lower())[1]
    
    @staticmethod
    def is_supported_format(filename: str) -> bool:
        """Проверяет, поддерживается ли формат файла"""
        ext = MediaHandler.get_file_extension(filename)
        return ext in MediaHandler.SUPPORTED_PHOTO_FORMATS or ext in MediaHandler.SUPPORTED_VIDEO_FORMATS
    
    @staticmethod
    def get_media_type(filename: str) -> str:
        """Определяет тип медиа файла"""
        ext = MediaHandler.get_file_extension(filename)
        if ext in MediaHandler.SUPPORTED_PHOTO_FORMATS:
            return 'photo'
        elif ext in MediaHandler.SUPPORTED_VIDEO_FORMATS:
            return 'video'
        else:
            return 'unknown'
    
    @staticmethod
    async def download_media_with_retry(event, max_retries: int = 3, 
                                      delay_base: float = 1.0) -> Optional[str]:
        """
        Скачивает медиа файл с повторными попытками
        
        Args:
            event: Telegram событие с медиа
            max_retries: Максимальное количество попыток
            delay_base: Базовая задержка между попытками
            
        Returns:
            Путь к скачанному файлу или None при ошибке
        """
        for attempt in range(max_retries):
            try:
                # Создаем временный файл
                with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp_file:
                    temp_path = tmp_file.name
                
                # Скачиваем медиа
                downloaded_path = await event.message.download_media(temp_path)
                
                if downloaded_path and os.path.exists(downloaded_path):
                    # Проверяем размер файла
                    file_size = os.path.getsize(downloaded_path)
                    if file_size > MediaHandler.MAX_FILE_SIZE:
                        logger.warning(f"Файл слишком большой: {file_size} bytes")
                        os.unlink(downloaded_path)
                        return None
                    
                    # Проверяем формат
                    if not MediaHandler.is_supported_format(downloaded_path):
                        logger.warning(f"Неподдерживаемый формат файла: {downloaded_path}")
                        os.unlink(downloaded_path)
                        return None
                    
                    logger.info(f"Медиа скачано успешно: {downloaded_path} ({file_size} bytes)")
                    return downloaded_path
                else:
                    logger.warning(f"Файл не был скачан: {downloaded_path}")
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                        
            except Exception as e:
                logger.warning(f"Попытка {attempt + 1} скачивания не удалась: {e}")
                
                # Очищаем временные файлы
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.unlink(temp_path)
                if 'downloaded_path' in locals() and os.path.exists(downloaded_path):
                    os.unlink(downloaded_path)
                
                # Экспоненциальная задержка
                if attempt < max_retries - 1:
                    delay = delay_base * (2 ** attempt)
                    logger.info(f"Ожидание {delay} секунд перед следующей попыткой...")
                    await asyncio.sleep(delay)
        
        logger.error("Не удалось скачать медиа после всех попыток")
        return None
    
    @staticmethod
    def cleanup_temp_files(*file_paths: str):
        """Очищает временные файлы"""
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    logger.info(f"Удален временный файл: {file_path}")
                except Exception as e:
                    logger.error(f"Ошибка при удалении файла {file_path}: {e}")
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Форматирует размер файла в читаемый вид"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f}{size_names[i]}"
    
    @staticmethod
    def get_media_info(file_path: str) -> dict:
        """Получает информацию о медиа файле"""
        if not os.path.exists(file_path):
            return {}
        
        try:
            file_size = os.path.getsize(file_path)
            file_ext = MediaHandler.get_file_extension(file_path)
            media_type = MediaHandler.get_media_type(file_path)
            
            return {
                'path': file_path,
                'size': file_size,
                'size_formatted': MediaHandler.format_file_size(file_size),
                'extension': file_ext,
                'type': media_type,
                'supported': MediaHandler.is_supported_format(file_path)
            }
        except Exception as e:
            logger.error(f"Ошибка при получении информации о файле {file_path}: {e}")
            return {}

class MessageProcessor:
    """Класс для обработки сообщений"""
    
    @staticmethod
    def extract_message_content(event) -> Tuple[Optional[str], bool, Optional[str]]:
        """
        Извлекает содержимое сообщения
        
        Returns:
            Tuple[текст, есть_фото, тип_медиа]
        """
        message_text = event.message.text or event.message.message
        has_photo = bool(event.message.photo)
        has_media = bool(event.message.media)
        
        media_type = None
        if has_media:
            if has_photo:
                media_type = 'photo'
            elif isinstance(event.message.media, MessageMediaDocument):
                media_type = 'document'
            else:
                media_type = 'other'
        
        return message_text, has_photo, media_type
    
    @staticmethod
    def should_process_message(event) -> bool:
        """Проверяет, нужно ли обрабатывать сообщение"""
        # Пропускаем служебные сообщения
        if event.message.action is not None:
            return False
        
        # Пропускаем пустые сообщения
        message_text = event.message.text or event.message.message
        has_photo = bool(event.message.photo)
        
        if not message_text and not has_photo:
            return False
        
        return True
    
    @staticmethod
    def create_caption(text: str, max_length: int = 1024) -> str:
        """Создает подпись для медиа с ограничением длины"""
        if not text:
            return ""
        
        if len(text) <= max_length:
            return text
        
        # Обрезаем текст и добавляем многоточие
        truncated = text[:max_length-3] + "..."
        return truncated
