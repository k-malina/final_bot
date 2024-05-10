import os

LOGS = 'logs.txt'  # файл для логов
DB_FILE = 'messages.db'  # файл для базы данных
URL = "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"

current_directory = os.getcwd()

IAM_TOKEN_PATH = os.path.join(current_directory, "creds", "iam_token.txt")
FOLDER_ID_PATH = os.path.join(current_directory, "creds", "folder_id.txt")
BOT_TOKEN_PATH = os.path.join(current_directory, "creds", "bot_token.txt")

MAX_USERS = 3  # максимальное кол-во пользователей
MAX_GPT_TOKENS = 120  # максимальное кол-во токенов в ответе GPT
COUNT_LAST_MSG = 4  # кол-во последних сообщений из диалога
MAX_TTS_SYMBOLS = 15

# лимиты для пользователя
MAX_USER_STT_BLOCKS = 10  # 10 аудиоблоков
MAX_USER_TTS_SYMBOLS = 5_000  # 5 000 символов
MAX_USER_GPT_TOKENS = 2_000  # 2 000 токенов

SYSTEM_PROMPT = [{'role': 'system', 'text': 'Ты веселый собеседник. Общайся с пользователем на "ты" и используй юмор. '
                                            'Поддерживай диалог. Не объясняй пользователю, что ты умеешь и можешь. '
                                            'Изображай человека '}]

VOICE = 'fillip'
LANG = 'ru-RU'
