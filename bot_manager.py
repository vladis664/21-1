#!/usr/bin/env python3
"""
Менеджер для медицинского мониторинг-бота
Предоставляет дополнительные функции управления и мониторинга
"""

import asyncio
import logging
from datetime import datetime, timezone
from telethon import TelegramClient
from medical_monitor_bot import (
    API_ID, API_HASH, BOT_TOKEN, SOURCE_CHANNELS, 
    DESTINATION_CHANNEL, START_DATE, END_DATE
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self):
        self.client = TelegramClient('bot_manager', API_ID, API_HASH)
        
    async def start(self):
        """Запуск менеджера"""
        await self.client.start(bot_token=BOT_TOKEN)
        logger.info("Менеджер бота запущен")
        
    async def stop(self):
        """Остановка менеджера"""
        await self.client.disconnect()
        logger.info("Менеджер бота остановлен")
        
    async def check_channel_access(self):
        """Проверка доступа к каналам"""
        logger.info("Проверка доступа к каналам...")
        
        accessible_channels = []
        inaccessible_channels = []
        
        for channel in SOURCE_CHANNELS:
            try:
                entity = await self.client.get_entity(channel)
                accessible_channels.append(channel)
                logger.info(f"✓ Доступен: {channel}")
            except Exception as e:
                inaccessible_channels.append(channel)
                logger.warning(f"✗ Недоступен: {channel} - {e}")
                
        logger.info(f"Доступных каналов: {len(accessible_channels)}/{len(SOURCE_CHANNELS)}")
        
        if inaccessible_channels:
            logger.warning("Недоступные каналы:")
            for channel in inaccessible_channels:
                logger.warning(f"  - {channel}")
                
        return accessible_channels, inaccessible_channels
        
    async def check_destination_channel(self):
        """Проверка целевого канала"""
        try:
            entity = await self.client.get_entity(DESTINATION_CHANNEL)
            participant = await self.client.get_permissions(entity)
            
            logger.info(f"Целевой канал: {DESTINATION_CHANNEL}")
            logger.info(f"Права бота: {'Администратор' if participant.is_admin else 'Обычный участник'}")
            logger.info(f"Может отправлять сообщения: {participant.post_messages}")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка доступа к целевому каналу: {e}")
            return False
            
    async def get_channel_info(self, channel_url):
        """Получение информации о канале"""
        try:
            entity = await self.client.get_entity(channel_url)
            return {
                'id': entity.id,
                'title': getattr(entity, 'title', 'Неизвестно'),
                'username': getattr(entity, 'username', 'Нет'),
                'participants_count': getattr(entity, 'participants_count', 'Неизвестно'),
                'description': getattr(entity, 'about', 'Нет описания')
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о канале {channel_url}: {e}")
            return None
            
    async def test_message_sending(self):
        """Тест отправки сообщения в целевой канал"""
        try:
            test_message = f"🧪 Тестовое сообщение от медицинского бота\nВремя: {datetime.now()}"
            await self.client.send_message(DESTINATION_CHANNEL, test_message)
            logger.info("✓ Тестовое сообщение отправлено успешно")
            return True
        except Exception as e:
            logger.error(f"✗ Ошибка отправки тестового сообщения: {e}")
            return False
            
    async def get_monitoring_status(self):
        """Получение статуса мониторинга"""
        now = datetime.now(timezone.utc)
        
        status = {
            'current_time': now,
            'monitoring_active': START_DATE <= now <= END_DATE,
            'days_until_start': (START_DATE - now).days if now < START_DATE else 0,
            'days_until_end': (END_DATE - now).days if now < END_DATE else 0,
            'start_date': START_DATE,
            'end_date': END_DATE
        }
        
        logger.info("Статус мониторинга:")
        logger.info(f"  Текущее время: {status['current_time']}")
        logger.info(f"  Мониторинг активен: {'Да' if status['monitoring_active'] else 'Нет'}")
        
        if now < START_DATE:
            logger.info(f"  До начала мониторинга: {status['days_until_start']} дней")
        elif now > END_DATE:
            logger.info(f"  Мониторинг завершен: {abs(status['days_until_end'])} дней назад")
        else:
            logger.info(f"  До окончания мониторинга: {status['days_until_end']} дней")
            
        return status

async def main():
    """Основная функция менеджера"""
    manager = BotManager()
    
    try:
        await manager.start()
        
        print("=" * 50)
        print("МЕДИЦИНСКИЙ МОНИТОРИНГ-БОТ - МЕНЕДЖЕР")
        print("=" * 50)
        
        # Проверка статуса мониторинга
        await manager.get_monitoring_status()
        print()
        
        # Проверка доступа к каналам
        accessible, inaccessible = await manager.check_channel_access()
        print()
        
        # Проверка целевого канала
        await manager.check_destination_channel()
        print()
        
        # Тест отправки сообщения
        print("Тестирование отправки сообщения...")
        await manager.test_message_sending()
        print()
        
        # Информация о каналах
        print("Информация о каналах:")
        for channel in accessible[:3]:  # Показываем только первые 3 канала
            info = await manager.get_channel_info(channel)
            if info:
                print(f"  {info['title']} (@{info['username']}) - {info['participants_count']} участников")
        print()
        
        print("Проверка завершена!")
        
    except KeyboardInterrupt:
        print("\nМенеджер остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка в менеджере: {e}")
    finally:
        await manager.stop()

if __name__ == '__main__':
    asyncio.run(main())
