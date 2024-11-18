import logging
import os
import sys
import time
from charset_normalizer import from_path
import requests
from telegram import Bot
from dotenv import load_dotenv
from telegram.error import TelegramError

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
    env_vars = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    missing_tokens = [name for name, value in env_vars.items() if not value]
    if missing_tokens:
        logger.critical(
            "Отсутствуют обязательные переменные окружения:"
            f"{', '.join(missing_tokens)}"
        )
        sys.exit(1)
    logger.debug("Все необходимые переменные окружения доступны.")
    logger.debug("Все необходимые переменные окружения доступны.")


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f"Бот отправил сообщение: {message}")
    except TelegramError as error:
        logger.error(f"Ошибка при отправке сообщения в Telegram: {error}")
    except Exception as error:
        logger.exception(f"Неизвестная ошибка при отправке сообщения: {error}")


def get_api_answer(timestamp):
    """Делает запрос к API и возвращает его ответ в формате Python."""
    params = {'timestamp': timestamp, 'from_date': from_path}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            raise ValueError(
                f"Ошибка API: код ответа - {response.status_code}"
            )
        # Возвращаем данные в формате JSON
        return response.json()
    except requests.RequestExceptio as error:
        raise ConnectionError(f"Ошибка при запросе к API: {error}")


def check_response(response):
    """Проверяет корректность ответа от API."""
    if not isinstance(response, dict):
        raise TypeError(
            "Ответ API должен быть словарем, но вместо этого"
            f"получен объект типа {type(response).__name__}."
        )
    if 'homeworks' not in response:
        raise KeyError("Отсутствует ключ 'homeworks' в ответе API.")
    homeworks = response['homeworks']  # Извлекаем домашние работы в переменную
    if not isinstance(homeworks, list):
        raise TypeError(
            "Данные по домашним работам должны быть списком,"
            f"но вместо этого получен объект типа {type(homeworks).__name__}."
        )
    return homeworks  # Возвращаем список домашних работ


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
            homeworks = check_response(response)
            if homeworks:
                # Обрабатываем только первую домашнюю работу
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logger.debug("Нет новых статусов домашних работ.")
            # Обновляем временную метку
            timestamp = response.get('current_date', timestamp)
        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logger.error(message)
            send_message(bot, message)
        finally:
            # Гарантированная пауза между запросами
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
