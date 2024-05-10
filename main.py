import telebot
import config
from ya_gpt import ask_gpt
from database import *
from vallidators import *
from SpeechKit import *
import logging
from creds import get_bot_token

bot = telebot.TeleBot(get_bot_token())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="log_file.txt",
    filemode="w",
)
u_data = []
@bot.message_handler(commands=['start'])
def start(message):
    u_id = message.chat.id
    if len(u_data) >= MAX_USERS:
        bot.send_message(u_id, 'Достигнут лимит пользователей')
    else:
        if u_id not in u_data:
            u_data.append(u_id)
    print(u_data)
    bot.send_message(u_id, 'Привет, я твой бот помощник использующий ИИ'
                                      ' для поддержания диалога, нахождения ответов на твои '
                                      'вопросы, а также для решение задач которые ты мне кидаешь 😉')

@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.from_user.id, "Чтобы приступить к общению, отправь мне голосовое сообщение или текст."
                                           "если хочешь проверить что SpeechKit работает, то можешь попробовать превратить"
                                           "аудио в текст: /stt или текст в аудио: /tts")

@bot.message_handler(commands=['debug'])
def debug(message):
    with open("logs.txt", "rb") as f:
        bot.send_document(message.chat.id, f)


@bot.message_handler(commands=['tts'])
def tts_handler(message):
    bot.send_message(message.chat.id, 'Отправляй следующим сообщение текст, а я его озвучу!')
    create_table()
    bot.register_next_step_handler(message, proccess_tts)

def proccess_tts(message):
    u_id = message.chat.id
    text = message.text

    if message.content_type != 'text':
        bot.send_message(u_id, 'Пока я умею работать лишь с текстом, можно пожалуйста буквы и слова :)')
        return
    if len(text) > MAX_LEN:
        bot.send_message(u_id, 'Сообщение слишком длинное, укороти его плиз')

    text_symbol = is_tts_symbol_limit(message, text)
    if text_symbol is None:
        return
    insert_row(u_id, text, text_symbol)

    status, content = tts(text)

    if status:
        bot.send_voice(u_id, content)
    else:
        bot.send_message(u_id, content)

def is_tts_symbol_limit(message, text):
    user_id = message.from_user.id
    text_symbols = len(text)

    all_symbols = count_all_symbol(user_id) + text_symbols

    if all_symbols >= MAX_USER_TTS_SYMBOLS:
        msg = f"Превышен общий лимит SpeechKit TTS {MAX_USER_TTS_SYMBOLS}. Использовано: {all_symbols} символов. Доступно: {MAX_USER_TTS_SYMBOLS - all_symbols}"
        bot.send_message(user_id, msg)
        return None

    if text_symbols >= MAX_TTS_SYMBOLS:
        msg = f"Превышен лимит SpeechKit TTS на запрос {MAX_TTS_SYMBOLS}, в сообщении {text_symbols} символов"
        bot.send_message(user_id, msg)
        return None
    return len(text)

@bot.message_handler(commands=['stt'])
def stt_handler(message):
    bot.send_message(message.from_user.id, 'Отправь голосовое сообщение, чтобы я его распознал!')
    bot.register_next_step_handler(message, process_stt)

def process_stt(message):
    u_id = message.chat.id
    if not message.voice:
        bot.send_message(message.chat.id, "Отправь пожалуйста именно голосовое сообщение, это как никак моя фишка :) ")
        bot.register_next_step_handler(message, process_stt)

    stt_blocks = is_stt_block_limit(message, message.voice.duration)
    if not stt_blocks:
        bot.send_message(u_id, "Либо что то пошло не так, либо ты записал[а] пустое "
                               "аудио сообщение.. Попробуй ещё раз пожалуйста")
        bot.register_next_step_handler(message, process_stt)

    file_id = message.voice.file_id
    file_info = bot.get_file(file_id)
    file = bot.download_file(file_info.file_path)
    status, text = stt(file)

    if status:
        insert_row(u_id, text, 'stt_blocks', stt_blocks)
        bot.send_message(u_id, text, reply_to_message_id=message.id)
    else:
        bot.send_message(u_id, text)

def is_stt_block_limit(message, duration):
    user_id = message.from_user.id
    audio_blocks = math.ceil(duration / 15)

    all_blocks = count_all_blocks(user_id)

    if all_blocks is None:
        all_blocks = 0

    all_blocks += audio_blocks

    if duration >= 30:
        msg = "SpeechKit STT работает с голосовыми сообщениями меньше 30 секунд"
        bot.send_message(user_id, msg)
        return None

    if all_blocks >= MAX_USER_STT_BLOCKS:
        msg = f"Превышен общий лимит SpeechKit STT {MAX_USER_STT_BLOCKS}. Использовано {all_blocks} блоков. Доступно: {MAX_USER_STT_BLOCKS - all_blocks}"
        bot.send_message(user_id, msg)
        return None

    return audio_blocks

@bot.message_handler(content_types=['voice'])
def handle_voice(message: telebot.types.Message):
    user_id = message.from_user.id
    try:
        #проверяем количество юзеров
        status_check_users, error_message = check_number_of_users(user_id)
        logging.info(f"error_message - {error_message}")
        if not status_check_users:
            bot.send_message(user_id, f"Ошибка - {error_message}")
            bot.register_next_step_handler(handle_voice)

        # проверяем доступ к аудиоблокам
        stt_blocks = is_stt_block_limit(message, message.voice.duration)
        logging.info(f"stt blocks - {stt_blocks}")
        logging.info(f"error_message - {error_message}")
        if error_message:
            bot.send_message(user_id, f"Ошибка - {error_message}. Либо что то пошло не так, либо ты записал[а] пустое "
                                   "аудио сообщение.. Попробуй ещё раз пожалуйста")
            logging.info(f'error_message - {error_message}')
            return

        # обрабатываем голосовуху
        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)
        status_stt, stt_text = speech_to_text(file)
        logging.info(f"file_id - {file_id}, file_info - {file_info}, status_stt - {status_stt}, stt_text - {stt_text}")
        if not status_stt:
            bot.send_message(user_id, stt_text)
            return

        # Записываем в бд
        add_message(user_id=user_id, full_message=[stt_text, 'user', 0, 0, stt_blocks])

        # проверяем если остались gpt токены
        last_messages, total_spent_tokens = select_n_last_messages(user_id, config.COUNT_LAST_MSG)
        total_gpt_tokens, error_message = is_gpt_token_limit(last_messages, total_spent_tokens)
        if error_message:
            bot.send_message(user_id, error_message)
            return

        # отправялем запрос в гпт
        status_gpt, answer_gpt, tokens_in_answer = ask_gpt(last_messages)
        # проверям на ошибки
        if not status_gpt:
            bot.send_message(user_id, answer_gpt)
            return
        total_gpt_tokens += tokens_in_answer

        # проверяем лимит символов SpeechKit
        tts_symbols = is_tts_symbol_limit(message, answer_gpt)

        # записываем ответ от гпт в бд
        add_message(user_id=user_id, full_message=[answer_gpt, 'assistant', total_gpt_tokens, tts_symbols, 0])

        if error_message:
            bot.send_message(user_id, error_message)
            return

        # из аудио в текст + отправка
        status_tts, voice_response = text_to_speech(answer_gpt)
        if status_tts:
            bot.send_voice(user_id, voice_response, reply_to_message_id=message.id)
        else:
            bot.send_message(user_id, answer_gpt, reply_to_message_id=message.id)

    except Exception as e:
        logging.error(e)
        bot.send_message(user_id, "Не получилось ответить. Попробуй записать другое сообщение")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        user_id = message.from_user.id

        # проверяем если место хватает для нью юзера
        status_check_users, error_message = check_number_of_users(user_id)
        if not status_check_users:
            bot.send_message(user_id, error_message)
            return

        # добавляем сообщение от пользователя + роль в бд
        full_user_message = [message.text, 'user', 0, 0, 0]
        add_message(user_id=user_id, full_message=full_user_message)

        # проверяем доступность гпт токенов
        # получаем прошлые сообщения + потраченные токены
        last_messages, total_spent_tokens = select_n_last_messages(user_id, config.COUNT_LAST_MSG)
        # получаем потраченные токены + токены в новом сообщении + оставшиеся
        total_gpt_tokens, error_message = is_gpt_token_limit(last_messages, total_spent_tokens)
        if error_message:
            bot.send_message(user_id, error_message)
            return

        # отправка запроса в гпт
        status_gpt, answer_gpt, tokens_in_answer = ask_gpt(last_messages)
        if not status_gpt:
            bot.send_message(user_id, answer_gpt)
            return
        # сумма всех потраченных токенов + токены в ответе GPT
        total_gpt_tokens += tokens_in_answer

        # добавляем ответ от гпт + потраченные токены в бд
        full_gpt_message = [answer_gpt, 'assistant', total_gpt_tokens, 0, 0]
        add_message(user_id=user_id, full_message=full_gpt_message)

        bot.send_message(user_id, answer_gpt, reply_to_message_id=message.id)  # отвечаем пользователю текстом
    except Exception as e:
        logging.error(e)
        bot.send_message(message.from_user.id, "Упс, что то пошло не так. Попробуй еще раз ")

@bot.message_handler(func=lambda: True)
def handler(message):
    bot.send_message(message.from_user.id, "Пока я умею обрабатывать только текстовые и аудио сообщения, "
                                           "поэтому отправь одно из них и я тебе обязательно помогу!)")

if __name__ == "__main__":
    logging.info("Бот запущен")
    create_database()
    logging.info("База данных создана")
    bot.infinity_polling()