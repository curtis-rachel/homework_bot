import time
import logging
from logging.handlers import RotatingFileHandler
import sys
from http import HTTPStatus
import requests
import telegram
from json.decoder import JSONDecodeError
from exceptions import APIRequestError
from settings import (
    PRACTICUM_TOKEN,
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    ENDPOINT,
    HEADERS,
    HOMEWORK_VERDICTS,
    RETRY_PERIOD
)

logger = logging.getLogger(__name__)


def check_tokens() -> bool:
    """Проверяем доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение пользователю."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(f'Пользователю отправилось сообщение {message}')
    except Exception:
        logging.error('Сбой при отправке сообщения в Telegram')


def get_api_answer(current_timestamp: int) -> dict:
    """Делаем запрос к эндпойнту."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logging.error('Эндпойнт не доступен')
            raise requests.RequestException('Эндпойнт не доступен')
    except requests.exceptions.RequestException:
        raise APIRequestError(
            "Сбой при запросе к эндпоинту ",
        )
    try:
        response.json()
    except JSONDecodeError:
        logging.error("Ответ не преобразован в JSON")
        raise JSONDecodeError("Ответ не преобразован в JSON")
    return response.json()


def check_response(response: dict) -> list:
    """Ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Тип "response" не словарь')
    if "homeworks" not in response:
        raise KeyError("Ключа 'homeworks' нет в словаре response")
    if "current_date" not in response:
        raise KeyError("Ключа 'current_date' нет в словаре response")
    if not isinstance(response.get('homeworks'), list):
        raise TypeError("Тип переменной 'homeworks' не список")
    return response.get('homeworks')


def parse_status(homework: dict) -> str:
    """Извлекает статус домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise Exception(f'Неизвестный статус работы: {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(' Отсутствует переменная окружения')
        sys.exit(' Отсутствует переменная окружения,завершение программы')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
            else:
                message = 'Новых работ нет'
            send_message(bot, message)
            current_timestamp = response['current_date']
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='program.log',
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
    )
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    backupCount=5)
logger.addHandler(handler)
