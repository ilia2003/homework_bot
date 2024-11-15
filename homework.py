import logging
import os
import time
from json.decoder import JSONDecodeError
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from telegram import Bot

logging.basicConfig(
    level=logging.DEBUG,
    filename='homework_bot_log.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'homework_bot_log.log',
    maxBytes=50_000_000,
    backupCount=5
)
logger.addHandler(handler)

load_dotenv()

PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
URL_YAND = 'https://praktikum.yandex.ru/api/user_api/'
PAUSE_CHECK = 300
PAUSE_ER = 5
ANSWERS = {
    'rejected': 'К сожалению, в работе нашлись ошибки.',
    'reviewing': 'Работа взята на ревью.',
    'approved': 'Ревьюеру всё понравилось, работа зачтена!',
}

bot = Bot(token=TELEGRAM_TOKEN)


def parse_homework_status(homework):
    homework_name = homework.get('homework_name', 'название неизвестно')
    status = homework.get('status', 'статус неизвестен')
    if status in ANSWERS:
        verdict = ANSWERS[status]
    else:
        logging.info(status)
        return f'Ваша работа {homework_name} пришла с неизвестным статусом'
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def get_homeworks(current_timestamp):
    if current_timestamp is None:
        current_timestamp = int(time.time())
    url = f'{URL_YAND}homework_statuses/'
    headers = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(url, headers=headers, params=payload)
        return homework_statuses.json()
    except requests.exceptions.RequestException as e:
        send_exc_message(e)
    except JSONDecodeError as e:
        send_exc_message(e)


def send_message(message):
    bot.send_message(CHAT_ID, message)
    logging.info('Сообщение отправлено!')


def send_exc_message(e):
    exc = f'Бот упал с ошибкой: {e}'
    logging.exception(f'ошибка{e}')
    send_message(exc)


def main():
    current_timestamp = int(time.time())

    while True:
        try:
            homeworks_all = get_homeworks(current_timestamp)
            homeworks = homeworks_all['homeworks']
            if homeworks:
                for homework in homeworks:
                    message = parse_homework_status(homework)
                    send_message(message)
            time.sleep(PAUSE_CHECK)
            current_timestamp = homeworks_all['current_date']

        except Exception as e:
            send_exc_message(e)
            time.sleep(PAUSE_ER)


if __name__ == '__main__':
    main()
