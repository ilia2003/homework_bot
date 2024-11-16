import logging
import os
import sys
import time
import requests
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()
bot = Bot

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def check_tokens():
    """Проверка наличия обязательных переменных окружения."""
    missing_tokens = []
    if not PRACTICUM_TOKEN:
        missing_tokens.append('PRACTICUM_TOKEN')
    if not TELEGRAM_TOKEN:
        missing_tokens.append('TELEGRAM_TOKEN')
    if not TELEGRAM_CHAT_ID:
        missing_tokens.append('TELEGRAM_CHAT_ID')

    if missing_tokens:
        logger.critical(
            f"Отсутствуют обязательные переменные окружения:"
            f"{', '.join(missing_tokens)}")
        sys.exit(1)

    logger.debug("Все необходимые переменные окружения доступны.")


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f"Бот отправил сообщение: {message}")
    except Exception as error:
        logger.error(f"Ошибка при отправке сообщения в Telegram: {error}")


def get_api_answer(timestamp):
    """Делает запрос к API и возвращает его ответ в формате Python."""
    params = {'timestamp': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            logger.error(f"Ошибка: код ответа API - {response.status_code}")
            return None
        return response.json()
    except requests.exceptions.RequestException as error:
        logger.error(f"Ошибка при запросе к API: {error}")
        return None


def check_response(response):
    """Проверяет корректность ответа от API."""
    if not isinstance(response, dict):
        raise TypeError("Ответ API должен быть словарем.")
    if 'homeworks' not in response:
        raise KeyError("Отсутствует ключ 'homeworks' в ответе API.")
    if not isinstance(response['homeworks'], list):
        raise TypeError("Данные по домашним работам должны быть списком.")
    return True


def parse_status(homework):
    """Извлекает статус домашней работы и формирует сообщение для Telegram."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')

    if not homework_name:
        raise KeyError("Отсутствует ключ 'homework_name' в ответе API.")

    if not status:
        raise KeyError("Отсутствует статус домашней работы.")

    verdict = HOMEWORK_VERDICTS.get(status)
    if not verdict:
        raise ValueError(f"Неожиданный статус домашней работы: {status}")

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()  # Проверка переменных окружения
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)

            if response is None:
                time.sleep(RETRY_PERIOD)
                continue

            if not check_response(response):
                time.sleep(RETRY_PERIOD)
                continue

            homeworks = response['homeworks']
            if not homeworks:
                logger.debug("Нет новых статусов домашних работ.")
                time.sleep(RETRY_PERIOD)
                continue

            for homework in homeworks:
                message = parse_status(homework)
                if message:
                    send_message(bot, message)

            timestamp = response.get('current_date', timestamp)

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logger.error(message)
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)  # Пауза при ошибке


if __name__ == '__main__':
    main()
