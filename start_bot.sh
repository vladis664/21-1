#!/bin/bash

# Скрипт для запуска медицинского мониторинг-бота
# Автор: Medical Bot Team
# Версия: 1.0

BOT_NAME="medical_monitor_bot"
LOG_FILE="medical_bot.log"
PID_FILE="bot.pid"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== МЕДИЦИНСКИЙ МОНИТОРИНГ-БОТ ===${NC}"

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Ошибка: Python3 не установлен${NC}"
    exit 1
fi

# Проверка наличия основного файла
if [ ! -f "medical_monitor_bot.py" ]; then
    echo -e "${RED}Ошибка: Файл medical_monitor_bot.py не найден${NC}"
    exit 1
fi

# Проверка наличия .env файла
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Предупреждение: Файл .env не найден${NC}"
    echo "Создайте файл .env на основе config.env.example"
    echo "cp config.env.example .env"
fi

# Функция для остановки бота
stop_bot() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}Остановка бота (PID: $PID)...${NC}"
            kill $PID
            sleep 2
            if ps -p $PID > /dev/null 2>&1; then
                echo -e "${RED}Принудительная остановка бота...${NC}"
                kill -9 $PID
            fi
        fi
        rm -f "$PID_FILE"
        echo -e "${GREEN}Бот остановлен${NC}"
    else
        echo -e "${YELLOW}Файл PID не найден${NC}"
    fi
}

# Функция для проверки статуса
check_status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${GREEN}Бот запущен (PID: $PID)${NC}"
            return 0
        else
            echo -e "${RED}Бот не запущен (PID файл устарел)${NC}"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        echo -e "${RED}Бот не запущен${NC}"
        return 1
    fi
}

# Обработка аргументов командной строки
case "$1" in
    start)
        if check_status > /dev/null 2>&1; then
            echo -e "${YELLOW}Бот уже запущен${NC}"
            exit 0
        fi
        
        echo -e "${GREEN}Запуск бота...${NC}"
        nohup python3 medical_monitor_bot.py > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        sleep 2
        
        if check_status > /dev/null 2>&1; then
            echo -e "${GREEN}Бот успешно запущен${NC}"
            echo "Логи: tail -f $LOG_FILE"
        else
            echo -e "${RED}Ошибка запуска бота${NC}"
            echo "Проверьте логи: cat $LOG_FILE"
            exit 1
        fi
        ;;
        
    stop)
        stop_bot
        ;;
        
    restart)
        echo -e "${YELLOW}Перезапуск бота...${NC}"
        stop_bot
        sleep 2
        $0 start
        ;;
        
    status)
        check_status
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Статус: Работает${NC}"
            echo "Логи: tail -f $LOG_FILE"
        else
            echo -e "${RED}Статус: Остановлен${NC}"
        fi
        ;;
        
    logs)
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            echo -e "${YELLOW}Файл логов не найден${NC}"
        fi
        ;;
        
    test)
        echo -e "${GREEN}Запуск тестирования...${NC}"
        python3 bot_manager.py
        ;;
        
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|test}"
        echo ""
        echo "Команды:"
        echo "  start   - Запустить бота"
        echo "  stop    - Остановить бота"
        echo "  restart - Перезапустить бота"
        echo "  status  - Показать статус"
        echo "  logs    - Показать логи в реальном времени"
        echo "  test    - Запустить тестирование"
        exit 1
        ;;
esac
