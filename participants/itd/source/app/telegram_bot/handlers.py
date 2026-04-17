from telegram import chat
from telegram import user
from app import db, bot
from app.models import User, MainMenuItems, Note
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.telegram_bot import texts
from app import Config
from telegram import ParseMode
import json
import math
import dialogflow_v2 as dialogflow
import speech_recognition as sr
import random
import os
import subprocess


def command_start(update, context):
    from app import create_app
    app = create_app(config_class=Config)    
    app.app_context().push()

    if User.query.filter_by(tg_id=update.message.chat_id).first() is None:
        bot.send_message(chat_id=update.message.chat_id, text='Введите табельный номер')
    else:
        btn_map = create_button_map(
            [
                {"text": "Задачи", "callback_data": "tasks"},
                {"text": "Новая заметка", "callback_data": "newtask"}
                ]
            , 1)
        bot.send_message(chat_id=update.message.chat_id,
                    text="Что будем делать?",
                    reply_markup=get_inline_menu(btn_map),
                    parse_mode="Markdown")

def user_tasks(update, context):
    from app import create_app
    app = create_app(config_class=Config)
    app.app_context().push()

    


def command_users_count(update, context):
    from app import create_app
    app = create_app(config_class=Config)
    app.app_context().push()

    all_users = User.query.all()
    tg_users = User.query.filter(User.tg_id.isnot(None)).all()
    unsubscribed_users = User.query.filter(User.tg_id.isnot(None), User.unsubscribed.is_(True)).all()
    user = User.query.filter_by(tg_id=update.message.from_user.id).first()
    bot.send_message(chat_id=user.tg_id,
                     text=f'*Всего в системе* {len(all_users)}\n'
                          f'*Бота подключили* {len(tg_users)}\n'
                          f'*Отписались* {len(unsubscribed_users)}',
                     parse_mode=ParseMode.MARKDOWN)


def text_message(update, context):
    from app import create_app
    app = create_app(config_class=Config)
    app.app_context().push()

    if User.query.filter_by(tg_id=update.message.chat_id).first() is None:
        user = User.query.filter_by(private_number=update.message.text).first()
        user.tg_id = update.message.from_user.id
        db.session.add(user)
        db.session.commit()
        bot.send_message(chat_id=user.tg_id,
                     text=f"Привет, {user.first_name}")
        bot.send_message(chat_id=user.tg_id,
                     text=get_main_menu(),
                     parse_mode=ParseMode.MARKDOWN)

def reply_message(update, context):
    pass


def contact_message(update, context):
    pass

def photo_message(update, context):
    pass


def audio_message(update, context):
    from app import create_app
    app = create_app(config_class=Config)
    app.app_context().push()

    audio = update.message.voice.get_file()
    audio = audio.download_as_bytearray()
    rand = str(random.randint(100000,1000000))
    filename =  rand+"note.ogg"
    with open(os.path.join(Config.UPLOAD_FOLDER, filename), 'wb') as f:
        f.write(audio)
    subprocess.run(['ffmpeg', '-i', os.path.join(Config.UPLOAD_FOLDER, filename), os.path.join(Config.UPLOAD_FOLDER, filename.replace('ogg', 'wav'))])
    with sr.AudioFile(os.path.join(Config.UPLOAD_FOLDER, filename.replace('ogg', 'wav'))) as s:
        r = sr.Recognizer()
        txt = r.listen(s)
        text = r.recognize_google(txt, language = 'ru-RU')
        note = Note()
        note.text = text
        note.sound_file = filename
        note.creator = User.query.filter_by(tg_id=update.message.chat_id).first().id
        db.session.add(note)
        db.session.commit()
        bot.send_message(
            chat_id=update.message.chat_id,
            text=f"Заметка сохранена"
        )


def inline_buttons_handler(update, context):
    from app import create_app
    app = create_app(config_class=Config)
    with app.app_context():
        command = update.callback_query.data.split('_')[1]
        sender = User.query.filter_by(tg_id=update.callback_query.from_user.id).first()

        if command == 'referal':
            texts.refer_link(sender)
        elif command == 'congrat':
            texts.congrat(sender)
        elif command == 'story':
            texts.story(sender)
        elif command == 'photo':
            texts.photo_template(sender)
        elif command == 'poem':
            texts.poem(sender)
        elif command == 'sport':
            texts.sport(sender)

            return 'ok'


def delete_message(update, context):
    chat_id = update.callback_query.from_user.id
    message_id = update.callback_query.message.message_id
    bot.delete_message(chat_id=chat_id, message_id=message_id)


def get_main_menu():
    buttons_list = []
    main_menu_items = MainMenuItems.query.filter(MainMenuItems.enabled.is_(True)).order_by(MainMenuItems.order).all()
    if main_menu_items == None:
        return None
    for item in main_menu_items:
        buttons_list.append([{
            'text': item.text
        }])
    buttons = [*buttons_list]
    ReplyKeyboardMarkup = {
        'keyboard': buttons,
        'resize_keyboard': True,
        'selective': False
    }
    return json.dumps(ReplyKeyboardMarkup)


# def create_button_map(buttons, col_count):
#     button_map = []
#     row_count = math.ceil(len(buttons) / col_count)
#     current_button = 0
#     for i in range(row_count):
#         button_map.append([])
#         for j in range(col_count):
#             if current_button < len(buttons):
#                 button_map[len(button_map) - 1].append(buttons[current_button])
#                 current_button += 1
#     return button_map


# def get_inline_menu(button_lists):
#     buttons = []
#     item_count = -1
#     for item in button_lists:
#         if isinstance(item, list):
#             item_count += 1
#             buttons.append([])
#             for subitem in item:
#                 inline_button = {
#                     'text': f'{subitem["text"]}',
#                     'callback_data': f'{subitem["data"]}'
#                 }
#                 buttons[item_count].append(inline_button)
#         else:
#             item_count += 1
#             inline_button = {
#                 'text': f'{item["text"]}',
#                 'callback_data': f'{item["data"]}'
#             }
#             buttons.append([inline_button])

#     ReplyKeyboardMarkup = {
#         'inline_keyboard': buttons
#     }
#     return json.dumps(ReplyKeyboardMarkup)

def create_button_map(buttons, col_count):
    button_map = []
    row_count = math.ceil(len(buttons) / col_count)
    current_button = 0
    for i in range(row_count):
        button_map.append([])
        for j in range(col_count):
            if current_button < len(buttons):
                button_map[len(button_map) - 1].append(buttons[current_button])
                current_button += 1
    return button_map


def get_inline_menu(button_lists):
    buttons = []
    item_count = -1
    for item in button_lists:
        if isinstance(item, list):
            item_count += 1
            buttons.append([])
            for subitem in item:
                inline_button = {
                    'text': f'{subitem["text"]}',
                    'callback_data': f'{subitem["callback_data"]}'
                }
                buttons[item_count].append(inline_button)
        else:
            item_count += 1
            inline_button = {
                'text': f'{item["text"]}',
                'callback_data': f'{item["callback_data"]}'
            }
            buttons.append([inline_button])

    ReplyKeyboardMarkup = {
        'inline_keyboard': buttons
    }
    return json.dumps(ReplyKeyboardMarkup)
