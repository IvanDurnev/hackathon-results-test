from flask import request
import threading
import asyncio
import json
import math
from app.models import Message, User, Quiz, Group
from app import db, bot, Config
from pprint import pprint
from app.telegram_bot import bp, chat_commands, texts
from datetime import datetime
import os
from pprint import pprint
import requests


@bp.route('/telegram', methods=['GET', 'POST'])
def telegram():
    # threading.Thread(target=route_message, args=(request.json,)).start()
    route_message(request.json)
    return 'ok'


def send_to_chanel(req):
    pprint(req)
    message_id = from_chat_id = text = ''
    if 'message_id' in req['message']:
        message_id = req['message']['message_id']
    if 'chat' in req['message']:
        from_chat_id = req['message']['chat']['id']
    if 'text' in req['message']:
        text = req['message']['text']
    if message_id and from_chat_id and text:
        asyncio.run(bot.forward_message(chat_id='@priznaniert2019',
                                        from_chat_id=from_chat_id,
                                        message_id=message_id))
        # asyncio.run(bot.send_message(chat_id='@priznaniert2019', text=text))


def route_message(req):
    # send_to_chanel(req)
    pprint(req)
    if req is not None:
        message_type = get_req_type(req)
        if message_type == 'text':
            asyncio.run(text_message_handler(req))
        if message_type == 'bot_command':
            asyncio.run(command_message_handler(req))
        if message_type == 'photo':
            asyncio.run(photo_message_handler(req))
        if message_type == 'callback_query':
            asyncio.run(callback_message_handler(req))
        if message_type == 'location':
            asyncio.run(location_message_handler(req))
        if message_type == 'voice':
            asyncio.run(voice_message_handler(req))
        if message_type == 'poll':
            asyncio.run(poll_message_handler(req))
        if message_type == 'pre_checkout_query':
            asyncio.run(pre_checkout_query_handler(req))
        if message_type == 'successful_payment':
            asyncio.run(successful_payment_handler(req))
        if message_type == 'video':
            asyncio.run(video_message_handler(req))
        if message_type == 'poll_answer':
            asyncio.run(poll_answer_handler(req))


def get_req_type(req):
    try:
        text = 'text' in req['message']
    except:
        text = False
    try:
        bot_command = req['message']['entities'][0]['type'] == 'bot_command'
    except:
        bot_command = False
    try:
        photo = 'photo' in req['message']
    except:
        photo = False
    try:
        video = 'video' in req['message']
    except:
        video = False
    try:
        photo_command = req['message']['caption_entities'][0]['type'] == 'bot_command'
    except:
        photo_command = False
    try:
        callback_query = 'callback_query' in req
    except:
        callback_query = False
    try:
        poll_answer = 'poll_answer' in req
    except:
        poll_answer = False
    try:
        location = False
        if 'message' in req:
            location = 'location' in req['message']
        elif 'edited_message' in req:
            location = 'location' in req['edited_message']
    except:
        location = False
    try:
        voice = 'voice' in req['message']
    except:
        voice = False
    if bot_command:
        return 'bot_command'
    if photo_command:
        return 'photo_command'
    if text:
        return 'text'
    if photo:
        return 'photo'
    if callback_query:
        return 'callback_query'
    if location:
        return 'location'
    if voice:
        return 'voice'
    if video:
        return 'video'
    if poll_answer:
        return 'poll_answer'


async def save_file(req):
    def save(current_catalog, hashtag):
        user = User.query.filter_by(tg_id=req['message']['from']['id']).first()
        file_id = extension = ''
        hashtag_catalog = f"{current_catalog}/{hashtag}"
        if not os.path.exists(hashtag_catalog):
            os.mkdir(hashtag_catalog)
        if get_req_type(req) == 'photo':
            file_id = req['message']['photo'][len(req['message']['photo']) - 1]['file_id']
            extension = 'jpg'
        elif get_req_type(req) == 'video':
            file_id = req['message']['video']['file_id']
            extension = req['message']['video']['mime_type'].split('/')[1]
        elif get_req_type(req) == 'voice':
            pprint(req)
            file_id = req['message']['voice']['file_id']
            extension = req['message']['voice']['mime_type'].split('/')[1]
        link = bot.get_link(file_id)
        print(link)
        if link:
            local_file = f'{hashtag_catalog}/файл_файл_{date}.{extension}'
            with open(local_file, 'wb') as new_file:
                file = requests.get(link)
                new_file.write(file.content)
            return local_file, file_id
        else:
            return None

    user = User.query.filter_by(tg_id=req['message']['from']['id']).first()
    date = req['message']['date']
    # current_catalog = f'app/static/uploads/{get_req_type(req)}'
    current_catalog = os.path.join(Config.UPLOAD_FOLDER, get_req_type(req))
    local_file = file_id = ''

    if not os.path.exists(current_catalog):
        os.makedirs(current_catalog)

    if 'caption_entities' in req['message']:
        entities = req['message']['caption_entities']
        for entity in entities:
            length = int(entity['length'])
            offset = int(entity['offset'])
            type = entity['type']
            if type == 'hashtag':
                try:
                    hashtag = req['message']['caption'][offset + 1:offset + length].lower()
                except:
                    hashtag = 'unknown'

                try:
                    local_file, file_id = save(current_catalog, hashtag)

                    await bot.send_message(chat_id=user.tg_id,
                                       text=f'*Спасибо, {user.username}!*\n'
                                            f'Ваше медиа с тэгом *#{hashtag}* принято.',
                                       parse_mode='Markdown')
                except:
                    print(f'Не удалось сохранить видео от\n{req}')
    else:
        try:
            local_file, file_id = save(current_catalog, 'unknown')
        except:
            print(f'Не удалось сохранить видео от\n{req}')

    if local_file and file_id:
        return local_file, file_id
    else:
        return None


def save_message(message_handler):
    async def wrapper(req):
        file_path = ''
        file_id = ''
        if get_req_type(req) == 'photo' or get_req_type(req) == 'video' or get_req_type(req) == 'voice':
            try:
                file_path, file_id = await save_file(req)
            except:
                pass

        message_id = ''
        try:
            message = Message()
            message.type = get_req_type(req)
            message.content = json.dumps(req)
            message.local_link = file_path
            message.file_id = file_id
            message.date_time = datetime.now()
            message.direction = 'output'
            message.user_id = chat_commands.get_user(req).id
            db.session.add(message)
            db.session.commit()
        except:
            pass
        await message_handler(req, message_id=message.id)
    return wrapper


def save_message_inline(text, message_type, user_tg_id, direction, seen):
    message = Message()
    message.type = message_type
    message.content = json.dumps({
        'message': {
            'text': text,
            'from': {
                'id': user_tg_id
            }
        }
    })
    message.local_link = ''
    message.file_id = ''
    message.date_time = datetime.now()
    message.direction = direction
    message.seen = seen
    message.user_id = User.query.filter_by(tg_id=user_tg_id).first().id
    db.session.add(message)
    db.session.commit()


def get_main_menu():
    buttons_list = []
    buttons_list.append([{
        'text': '#Спикеры'
    }])
    buttons_list.append([{
        'text': '#Программа'
    }])
    buttons_list.append([{
        'text': '#Активности'
    }])
    buttons_list.append([{
        'text': '#ПодключиКоллегу'
    }])


    buttons = [*buttons_list]
    ReplyKeyboardMarkup = {
        'keyboard': buttons,
        'resize_keyboard': True,
        'selective': False
    }
    return json.dumps(ReplyKeyboardMarkup)


@save_message
async def text_message_handler(req, **kwargs):
    text = req['message']['text']
    user = chat_commands.get_user(req)
    commands_dict = {
        '#Спикеры': chat_commands.send_speakers,
        '#Программа': chat_commands.send_program,
        '#Активности': chat_commands.send_contests_info,
        '#ПодключиКоллегу': chat_commands.send_refer_link,
    }
    if text in commands_dict:
        await commands_dict[text](req)
    else:
        if user:
            if user.role == 'admin':
                if 'reply_to_message' in req['message']:
                    text = req['message']['text']
                    asking_user_tg_ig = ''
                    if 'entities' in req['message']['reply_to_message']:
                        for entity in req['message']['reply_to_message']['entities']:
                            if entity['type'] == 'text_mention':
                                asking_user_tg_ig = entity['user']['id']
                        asking_user = User.query.filter_by(tg_id = asking_user_tg_ig).first()
                        if asking_user:
                            await bot.send_message(chat_id=asking_user.tg_id, text=text,
                                                   parse_mode='Markdown')
                            save_message_inline(text=text, message_type='text', user_tg_id=asking_user_tg_ig, direction='input', seen=True)
                            print(f'Ответ через бота отвечал {user} пользователю {asking_user}')
                        return f'Ответ через бота отвечал {user} пользователю {asking_user}'
                else:
                    return 'ok'
            if user.status == 'waitforcode':
                main_user = User.query.filter_by(email=text).first()
                if main_user:
                    main_user.tg_id = user.tg_id
                    main_user.registered = datetime.now()
                    db.session.commit()
                    for message in Message.query.filter_by(user_id=user.id).all():
                        message.user_id = main_user.id
                        db.session.commit()
                    db.session.delete(user)
                    db.session.commit()
                    text = f'Спасибо, {main_user.username}, вы зарегистрированы!'
                    # reply_markup = ''
                    reply_markup=get_main_menu()
                    await bot.send_message(main_user.tg_id, text, reply_markup=reply_markup)
                    await bot.send_message(chat_id=main_user.tg_id,
                                         caption=texts.greeting,
                                         parse_mode='Markdown')
                    save_message_inline(text=text, message_type='text', user_tg_id=main_user.tg_id, direction='input', seen=True)
                    save_message_inline(text=texts.greeting, message_type='text', user_tg_id=main_user.tg_id, direction='input', seen=True)
                else:
                    text = 'Вам надо *сначала* зарегистрироваться на сайте, а потому прислать сюда ваш email, под которым вы зарегистрировались'
                    await bot.send_message(user.tg_id,
                                           text,
                                           parse_mode='Markdown')
                    save_message_inline(text=text, message_type='text', user_tg_id=user.tg_id, direction='input', seen=True)
            else:
                moderators = user.get_group().moderators
                buttons = [
                    {
                        'text': 'В эфир',
                        'data': f'alertMessage_{kwargs["message_id"]}'
                    },
                    {
                        'text': 'Удалить',
                        'data': f'deleteMessage_{kwargs["message_id"]}'
                    }
                ]
                map = create_button_map(buttons, 2)
                reply_markup = get_inline_menu(map)
                await bot.send_messages_list(users=moderators,
                                             text=f'{texts.tg_user_mention(user)} _({user.group})_: {text}',
                                             reply_markup=reply_markup,
                                             parse_mode='Markdown')


async def command_message_handler(req, **kwargs):
    commands_dict = {
        '/start': chat_commands.start,
        '/program': chat_commands.send_program,
        '/users_count': chat_commands.users_count,
        # '/daddy': chat_commands.daddy,
        # '/cssblag': chat_commands.cssblag,
        # '/whoareyou': chat_commands.whoareyou
    }
    command = req['message']['text'].split(' ')[0]
    if command in commands_dict:
        await commands_dict[command](req)


@save_message
async def photo_message_handler(req, **kwargs):
    text = ''
    try:
        text = req['message']['caption']
    except:
        pass
    user = chat_commands.get_user(req)

    file_id = req['message']['photo'][len(req['message']['photo'])-1]['file_id']
    moderators = list(user.get_group().moderators)
    group = Group.query.filter_by(id=user.group).first()
    moderators = list(group.moderators)

    buttons = [
        {
            'text': 'В эфир',
            'data': f'alertMessage_{kwargs["message_id"]}'
        },
        {
            'text': 'Удалить',
            'data': f'deleteMessage_{kwargs["message_id"]}'
        }
    ]
    map = create_button_map(buttons, 2)
    reply_markup = get_inline_menu(map)

    await bot.send_photo(chat_id=moderators,
                         caption=f'{texts.tg_user_mention(user)}: {text}',
                         parse_mode='Markdown',
                         photo=file_id,
                         reply_markup=reply_markup)


@save_message
async def video_message_handler(req, **kwargs):
    try:
        text = req['message']['caption']
    except:
        text = ''
    user = chat_commands.get_user(req)
    file_id = req['message']['video']['file_id']
    moderators = list(user.get_group().moderators)
    await bot.send_video(chat_id=moderators,
                         caption=f'{texts.tg_user_mention(user)}: {text}',
                         parse_mode='Markdown',
                         video=file_id)


async def callback_message_handler(req, **kwargs):
    command = req['callback_query']['data'].split('_')[0]
    user = chat_commands.get_user(req)
    commands_dict = {
        'deleteMessage': chat_commands.delete_message,
        'alertMessage': chat_commands.alert_message,
        'startQuiz': chat_commands.start_quiz,
        'contest': chat_commands.send_contest_terms
    }
    if command in commands_dict:
        await commands_dict[command](req)
    elif command == 'sendQuestion':
        quiz = Quiz.query.get(int(req['callback_query']['data'].split('_')[1]))
        question_number = int(req['callback_query']['data'].split('_')[-1])
        await chat_commands.send_question(user, quiz, question_number)


async def location_message_handler(req):
    pass


@save_message
async def voice_message_handler(req, **kwargs):
    pass


async def poll_answer_handler(req):
    user = User.query.filter_by(tg_id = int(req['poll_answer']['user']['id'])).first()
    quiz = Quiz.query.get(int(user.status.split('_')[1]))
    current_question = int(user.status.split('_')[-1])
    answer_type = quiz.questions[current_question].answer_type

    if answer_type == 'text':
        await bot.send_message(chat_id=user.tg_id,
                               text=quiz.questions[current_question].answer_text)
    elif answer_type == 'photo':
        await bot.send_photo(chat_id=user.tg_id,
                             photo=quiz.questions[current_question].answer_content,
                             caption=quiz.questions[current_question].answer_text)
    elif answer_type == 'video':
        await bot.send_video(chat_id=user.tg_id,
                             video=quiz.questions[current_question].answer_content,
                             caption=quiz.questions[current_question].answer_text)

    if current_question+1 < len(quiz.questions):
        # await chat_commands.send_question(user, quiz, current_question+1)
        buttons = [
            {
                'text': 'Да',
                'data': f'sendQuestion_{quiz.id}_{current_question+1}'
            }
        ]
        map = chat_commands.tg_routes.create_button_map(buttons, 1)
        reply_markup = chat_commands.tg_routes.get_inline_menu(map)
        await bot.send_message(chat_id=user.tg_id,
                               text=f'Готовы к вопросу {current_question+2} из {len(quiz.questions)}?',
                               reply_markup=reply_markup)
    else:
        if quiz.final_text:
            await bot.send_message(chat_id=user.tg_id,
                                   text=json.loads(quiz.final_text))
        else:
            await bot.send_message(chat_id=user.tg_id,
                               text='Спасибо за участие! До встречи!')


async def poll_message_handler(req):
    pass


async def pre_checkout_query_handler(req):
    pass


async def successful_payment_handler(req):
    pass


def create_button_map(buttons, col_count):
    button_map = []
    row_count = math.ceil(len(buttons)/col_count)
    current_button = 0
    for i in range(row_count):
        button_map.append([])
        for j in range(col_count):
            if current_button < len(buttons):
                button_map[len(button_map)-1].append(buttons[current_button])
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
                    'callback_data': f'{subitem["data"]}'
                }
                buttons[item_count].append(inline_button)
        else:
            item_count += 1
            inline_button = {
                'text': f'{item["text"]}',
                'callback_data': f'{item["data"]}'
            }
            buttons.append([inline_button])

    ReplyKeyboardMarkup = {
        'inline_keyboard': buttons
    }
    return json.dumps(ReplyKeyboardMarkup)