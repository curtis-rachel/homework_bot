import time
import os
import logging
import sys
from http import HTTPStatus
import requests
import telegram
from json.decoder import JSONDecodeError
from dotenv import load_dotenv
from exceptions import APIRequestError

load_dotenv()


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


def check_tokens():
    """Проверяем доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправляет сообщение пользователю."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(f'Пользователю отправилось сообщение {message}')
        return True
    except Exception:
        logging.error('Сбой при отправке сообщения в Telegram')
        return False


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
    """Проверяем API на корректность."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        logging.error('Ключ homeworks не найден в ответе API')
        raise KeyError('Ключ homeworks не найден в ответе API')
    if 'current_date' not in response:
        logging.error('Ключ current_date не найден в ответе API')
        raise KeyError('Ключ current_date не найден в ответе API')
    elif not isinstance(response, dict):
        logging.error('Неверный тип переменной, это должен быть словарь')
        raise TypeError('Неверный тип переменной, это должен быть словарь')
    elif not isinstance(homeworks, list):
        logging.error('Отсутствует список домашних работ')
        raise TypeError('Отсутствует список домашних работ')
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы."""
    try:
        homework_name = str(homework['homework_name'])
    except Exception:
        logging.error('Не удалось узнать название работы')
    try:
        homework_status = homework['status']
    except Exception:
        logging.error('Не удалось узнать статус работы')
    if homework_status == 'approved':
        verdict = str(HOMEWORK_VERDICTS[homework_status])
        return str(
            f'Изменился статус проверки работы "{homework_name}". {verdict}'
        )
    elif homework_status == 'reviewing':
        verdict = str(HOMEWORK_VERDICTS[homework_status])
        return str(
            f'Изменился статус проверки работы "{homework_name}". {verdict}'
        )
    elif homework_status == 'rejected':
        verdict = str(HOMEWORK_VERDICTS[homework_status])
        return str(
            f'Изменился статус проверки работы "{homework_name}". {verdict}'
        )
    else:
        logging.error('Не обнаружен статус домашней робаты')
        raise KeyError


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
            if len(homework) > 0:
                message = parse_status(homework[0])
            elif len(homework) == 0:
                message = 'Отправьте работу на проверку'
            send_message(bot, message)
            current_timestamp = response['current_date']
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(stream=sys.stdout)
    fmt = '[%(asctime)s: %(levelname)s] %(message)s'
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    try:
        main()
    except KeyboardInterrupt:
        logging.info('Работа бота завершена.')
