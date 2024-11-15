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
        logger.critical(f"Отсутствуют обязательные"
                        f"переменные окружения:{', '.join(missing_tokens)}")
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
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'timestamp': timestamp}
        )
        response.raise_for_status()  # Проверка на ошибки HTTP
        return response.json()
    except requests.exceptions.RequestException as error:
        logger.error(f"Ошибка при запросе к API: {error}")
        return None


def check_response(response):
    """Проверяет корректность ответа от API."""
    if not isinstance(response, dict):
        logger.error("Ответ API не является словарём.")
        return False
    if 'homeworks' not in response:
        logger.error("Отсутствует ключ 'homeworks' в ответе API.")
        return False
    if not isinstance(response['homeworks'], list):
        logger.error("Ключ 'homeworks' не является списком.")
        return False
    return True


def parse_status(homework):
    """Извлекает статус домашней работы и формирует сообщение для Telegram."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')

    if not homework_name or not status:
        logger.error(
            "Отсутствуют обязательные поля в ответе о домашней работе."
        )
        return None

    verdict = HOMEWORK_VERDICTS.get(status)
    if not verdict:
        logger.error(f"Неожиданный статус домашней работы: {status}")
        return None

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    """Основная логика работы бота."""
    check_tokens()  # Проверяем переменные окружения

    # Создаем объект бота
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())  # Начальная метка времени

    while True:
        try:
            # Получаем ответ от API
            response = get_api_answer(timestamp)

            if response is None:
                time.sleep(RETRY_PERIOD)
                continue

            # Проверяем ответ от API
            if not check_response(response):
                time.sleep(RETRY_PERIOD)
                continue

            # Получаем список домашних работ
            homeworks = response['homeworks']
            if not homeworks:
                logger.debug("Нет новых статусов домашних работ.")
                time.sleep(RETRY_PERIOD)
                continue

            # Обрабатываем каждое домашнее задание
            for homework in homeworks:
                message = parse_status(homework)
                if message:
                    send_message(bot, message)

            # Обновляем метку времени для следующего запроса
            timestamp = response.get('current_date', timestamp)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
