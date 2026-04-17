from app import db, bot, Config
from app.models import User, Message, ChatMessages, Quiz
from app.telegram_bot import texts, telegram_menu
import json
from random import choice
from string import ascii_letters
import aiohttp
import asyncio
from pprint import pprint
from app.telegram_bot import routes as tg_routes


def get_user(req):
    try:
        user = User.query.filter_by(tg_id=req['message']['from']['id']).first()
    except:
        user = User.query.filter_by(tg_id=req['callback_query']['from']['id']).first()
    return user


async def save_income_message(users, text):

    async def save_mes(user):
        message = Message()
        message.type = 'text'
        message.direction = 'input'
        message.seen = True
        message.user_id = user.id
        message.content = json.dumps(
            {
                'message': {
                    'text': text
                }
            }
        )
        db.session.add(message)
        db.session.commit()

    tasks = []
    async with aiohttp.ClientSession() as session:
        for user in users:
            task = asyncio.create_task(save_mes(user))
            tasks.append(task)
        await asyncio.gather(*tasks)


async def start(req):
    user = get_user(req)
    if not user:
        last_name = username = first_name = req['message']['from']['id']
        # if 'last_name' in req['message']['from']:
        #     last_name = req['message']['from']['last_name']
        # if 'username' in req['message']['from']:
        #     last_name = req['message']['from']['username']
        # if 'first_name' in req['message']['from']:
        # #     first_name = req['message']['from']['first_name']
        # if 'language_code' in req['message']['from']:
        #         language_code = req['message']['from']['language_code']
        user = User()
        user.tg_id = int(req['message']['from']['id'])
        # нам не важны данные телеграма, пользователи регистрируются через сайт
        user.first_name = first_name
        # user.code = ''.join(choice(ascii_letters) for i in range(7))
        user.username = username
        user.is_bot = False
        user.last_name = last_name
        user.language_code = 'ru'
        user.password_hash = ''
        user.email = f"{req['message']['from']['id']}@harza.ru"
        user.status = 'waitforcode'
        db.session.add(user)
        db.session.commit()
        await bot.send_message(chat_id=user.tg_id, text=texts.code(user))
        tg_routes.save_message_inline(text='/start', message_type='text', user_tg_id=user.tg_id,
                                      direction='output', seen=True)
        tg_routes.save_message_inline(text=texts.code(user), message_type='text', user_tg_id=user.tg_id,
                                      direction='input', seen=True)

        return user
    else:
        if user.status == 'waitforcode':
            await bot.send_message(chat_id=user.tg_id, text=texts.code(user))
            tg_routes.save_message_inline(text=texts.code(user), message_type='text', user_tg_id=user.tg_id, direction='input', seen=True)
        else:
            text = f'Вы уже регистрировались, {user.username}'
            await bot.send_message(chat_id=user.tg_id, text=text, reply_markup=tg_routes.get_main_menu())
            await bot.send_message(chat_id=user.tg_id, text=texts.greeting, parse_mode='Markdown')
            tg_routes.save_message_inline(text=text, message_type='text', user_tg_id=user.tg_id,
                                          direction='input', seen=True)
            # await bot.send_message(chat_id=user.tg_id, text=texts.greeting, parse_mode='Markdown')


async def send_program(req):
    user = User.query.filter_by(tg_id=req['message']['from']['id']).first()
    await bot.send_message(chat_id=user.tg_id, text=texts.program(), parse_mode='Markdown')


async def send_speakers(req):
    user = User.query.filter_by(tg_id=req['message']['from']['id']).first()
    await bot.send_message(chat_id=user.tg_id, text=texts.speakers(), parse_mode='Markdown')


async def send_refer_link(req):
    user = get_user(req)
    refer_link = f'{Config.VIDGET_PREFIX}/auth/registration?u={user.id}'
    text = texts.refer_link
    await bot.send_message(chat_id=user.tg_id, text=text)
    tg_routes.save_message_inline(text=text, message_type='text', user_tg_id=user.tg_id, direction='input', seen=False)
    await bot.send_message(chat_id=user.tg_id, text=refer_link, disable_web_page_preview=False)
    tg_routes.save_message_inline(text=refer_link, message_type='text', user_tg_id=user.tg_id, direction='input', seen=False)


async def send_contests_info(req):
    # reply_markup = tg_routes.get_main_menu()
    user = get_user(req)
    text = texts.contests()

    buttons = [
        {
            'text': '📲 Подключи коллегу',
            'data': f'contest_link'
        },
        {
            'text': '😎 Travel-челлендж',
            'data': f'contest_letsmeet'
        },
    #     # {
        #     'text': '👋🏼 Давай знакомиться',
        #     'data': f'contest_letsmeet'
        # },
        # {
        #     'text': '👗👔 Твой наряд',
        #     'data': f'contest_yourlook'
        # }
    ]
    map = tg_routes.create_button_map(buttons, 1)
    reply_markup = tg_routes.get_inline_menu(map)

    await bot.send_message(chat_id=user.tg_id, text=text, reply_markup=reply_markup, parse_mode='Markdown')
    # await bot.send_photo(chat_id=user.tg_id,
    #                            photo='AgACAgIAAxkDAAIaCV7helPS8k0eP6XStFQZc90fDfTEAALfrjEbAAFnCEv2crvvvhZD_wh845EuAAMBAAMCAAN5AAMQBQMAARoE',
    #                            caption='Вот здесь находится кнопка для получения ссылки - оранжевая стрелка. '
    #                                    'Если вдруг эта кнопка скроется, нажмите на значок "клавиатура", обозначенный фиолетовой стрелкой.',
    #                            parse_mode='Markdown')

    tg_routes.save_message_inline(text=text, message_type='text', user_tg_id=user.tg_id, direction='input', seen=True)


async def send_contest_terms(req):
    try:
        user = get_user(req)
        contest = req['callback_query']['data'].split('_')[1]

        if contest == 'link':
            text = texts.refer_link
            await bot.send_message(chat_id=user.tg_id, text=text)
            refer_link = f'{Config.VIDGET_PREFIX}/auth/registration?u={user.id}'
            await bot.send_message(chat_id=user.tg_id, text=refer_link)

        elif contest == 'letsmeet':
            video = 'BAACAgIAAxkDAAIDAAFe7FJrZUc2XhDA_T2kYnjkVV1ijgAC6AYAAsOTYUvVeLnyyp2kIBoE'
            text = '''
Я хочу видеть и знать вас всех, давай знакомиться?
⠀
Участвуй в travel-челлендже и увидишь результат в прямом эфире 23 июня.
⠀
Запиши на телефон горизонтальное видео до 30 секунд:
🔹Закрой рукой камеру телефона
🔹Убери руку от камеры телефона
🔹Представься 
🔹Скажи о себе интересный факт
🔹Закрой рукой камеру телефона
⠀
Для примера лови видео от меня.
⠀
Жду твой видосик🎥. Обязательно подпиши его #Давайзнакомиться
'''
            await bot.send_video(chat_id=user.tg_id, video=video, caption=text)

        elif contest == 'yourlook':
            photo = 'AgACAgIAAxkDAAJhIl7ldCDdthSieEijU5oTS2Rj-Qk7AAJprTEb8kPQSlA5qUAUZECcS7DvkS4AAwEAAwIAA3kAA4jMAgABGgQ'
            text = '''
Осталось всего несколько дней до Главного события года😍.

Премия есть премия! А значит, не важно, где ты будешь её смотреть, пришло время задуматься над нарядом👗👔.

Звёзды уже подготовили свои луки.

А ты❓

Пришли мне фото своего наряда.

Если же платье/костюм наглаживать не хочется, подумай о праздничных аксессуарах🎩. Стильный ободок с ушками зайчика или ковбойская шляпа может стать отличным дополнением твоего образа на празднике🥳!

В общем, жду сюда твоё фото в наряде или аксессуарах. Отличного дня👋!
'''
            await bot.send_photo(chat_id=user.tg_id, caption=text, photo=photo)

        elif contest == 'chefoffice':
            photo = 'AgACAgIAAxkDAAKCo17opZaouAS_iFIjJhtx9GR4h30YAAJtrTEb8kPQSsptBaIYU-pzW2roki4AAwEAAwIAA3kAA8xEAgABGgQ'
            text = '''
Привет!
Сегодня тебя ждёт уникальная возможность🧞‍♂️!
⠀
…пишу об этом, и мурашки забегали от предвкушения…
⠀
Конкурс в студию🏆!
Напиши креативный или заковыристый вопрос вице-президенту МРФ ДВ или руководителю своего филиала. Прошу, пусть это будет вопрос не про работу, ведь мы соберемся по праздничному поводу🎊!
⠀
Самые интересные вопросы зададим в прямом эфире 19 июня. А за самые крутые – наградим!
⠀
У меня есть отличные подарки🎁🎁🎁 и мне не терпится ими поделиться.
⠀
Пиши здесь свой вопрос и кому он предназначен. Хотя можешь адресовать его всем.
В конце вопроса поставь #Кабинетдиректора.
⠀
Хорошего дня☀️!
            '''
            await bot.send_photo(chat_id=user.tg_id, caption=text, photo=photo)
    except:
        pass


async def users_count(req):
    users = User.query.all()
    user = User.query.filter_by(tg_id=req['message']['from']['id']).first()
    await bot.send_message(chat_id=user.tg_id, text=f'В боте {len(users)} пользователей')


async def instruction(req):
    user = get_user(req)
    reply_markup = telegram_menu.get_main_menu()
    await bot.send_message(chat_id=user.id, text=texts.instruction, reply_markup=reply_markup, parse_mode='Markdown')


async def help(req):
    user_id = int(req['message']['from']['id'])
    user = User.query.filter_by(id=user_id).first()
    await bot.send_message(user.id, texts.instruction, parse_mode='Markdown', disable_web_page_preview=True)
    await bot.send_message(user.id, texts.help, parse_mode='Markdown', disable_web_page_preview=True)


async def delete_message(req):
    chat_id = req['callback_query']['from']['id']
    message_id = req['callback_query']['message']['message_id']
    await bot.delete_message(chat_id=chat_id, message_id=message_id)


async def alert_message(req):
    # pprint(req)
    message_id = int(req['callback_query']['data'].split('_')[1])
    # если в сообщении есть хэштэги - забираем их в список
    hashtags = []
    try:
        if 'caption_entities' in req['callback_query']['message']:
            for entity in req['callback_query']['message']['caption_entities']:
                if entity['type'] == 'hashtag':
                    hashtags.append(
                        req['callback_query']['message']['caption'][int(entity['offset'])+1:int(entity['offset'])+int(entity['length'])])
                    # print(hashtags)
    except:
        # нет - нет
        hashtags = []
    chat_message = ChatMessages.query.filter_by(message_id=message_id).first()
    if not chat_message:
        chat_message = ChatMessages()
        chat_message.message_id = message_id
        chat_message.shown = False
        if len(hashtags) > 0:
            chat_message.description = ' '.join(hashtags)
        db.session.add(chat_message)
    else:
        chat_message.shown = False
    db.session.commit()
    # меняем кнопку
    chat_message_id = req['callback_query']['message']['message_id']
    user = get_user(req)
    try:
        text = req['callback_query']['message']['text']
    except:
        text = req['callback_query']['message']['caption']
    buttons = [
        {
            'text': 'Повторить в эфире',
            'data': f'alertMessage_{message_id}'
        },
        {
            'text': 'Удалить',
            'data': f'deleteMessage_{message_id}'
        }
    ]
    map = tg_routes.create_button_map(buttons, 2)
    reply_markup = tg_routes.get_inline_menu(map)
    if 'text' in req['callback_query']['message']:
        await bot.edit_message(chat_id=user.tg_id,
                               message_id=chat_message_id,
                               text=text,
                               reply_markup=reply_markup,
                               parse_mode='Markdown')
    if 'caption' in req['callback_query']['message']:
        await bot.edit_message_caption(chat_id=user.tg_id,
                               message_id=chat_message_id,
                               caption=text,
                               reply_markup=reply_markup,
                               parse_mode='Markdown')


async def send_quiz(quiz_id, users):
    quiz = Quiz.query.get(quiz_id)
    buttons = [
        {
            'text': 'Начинаем',
            'data': f'startQuiz_{quiz_id}'
        }
    ]
    map = tg_routes.create_button_map(buttons, 1)
    reply_markup = tg_routes.get_inline_menu(map)
    await bot.send_messages_list(users=users,
                                 text=json.loads(quiz.description),
                                 reply_markup=reply_markup,
                                 parse_mode='Markdown')


async def start_quiz(req):
    # pprint(req)
    quiz_id = req['callback_query']['data'].split('_')[1]
    quiz = Quiz.query.get(quiz_id)
    questions = quiz.questions
    message_id = req['callback_query']['message']['message_id']
    user = get_user(req)
    # await bot.edit_message(chat_id=user.tg_id, text=f'Викторина *"{quiz.name}"*', message_id=message_id, parse_mode='Markdown')
    await send_question(user, quiz, 0)


async def send_question(user, quiz, question_number):
    variants = quiz.questions[question_number].question_variants.split('\n')
    correct_option_id = ''
    options = []

    for index, option in enumerate(variants):
        if not option.split(' ')[-1].strip() == '(верный)':
            options.append(option.strip())
        else:
            options.append(option.strip().split('(верный)')[0])
            correct_option_id = index

    question_type = quiz.questions[question_number].question_type

    if question_type == 'photo':
        await bot.send_photo(chat_id=user.tg_id,
                             photo=quiz.questions[question_number].question_content,
                             caption='')
    elif question_type == 'video':
        await bot.send_video(chat_id=user.tg_id,
                             video=quiz.questions[question_number].question_content,
                             caption='')
    elif question_type == 'text':
        pass

    await bot.send_poll(
        chat_id=user.tg_id,
        question=quiz.questions[question_number].question_text,
        options=json.dumps(options),
        type='quiz',
        correct_option_id=correct_option_id
    )
    user.status = f'playQuiz_{quiz.id}_{question_number}'
    db.session.commit()


async def feedback(req):
    pass


async def donate(req):
    pass


async def daddy(req):
    user_id = int(req['message']['from']['id'])
    user = User.query.filter_by(id=user_id).first()
    await bot.send_message(user.id, texts.daddy, parse_mode='Markdown')


async def cssblag(req):
    user_id = int(req['message']['from']['id'])
    user = User.query.filter_by(id=user_id).first()
    await bot.send_message(user.id, texts.cssblag, parse_mode='Markdown', disable_web_page_preview=True)


async def whoareyou(req):
    user_id = int(req['message']['from']['id'])
    user = User.query.filter_by(id=user_id).first()
    await bot.send_message(user.id, texts.whoareyou, parse_mode='Markdown', disable_web_page_preview=True)


async def portfolio(req):
    user_id = int(req['message']['from']['id'])
    user = User.query.filter_by(id=user_id).first()
    await bot.send_message(user.id, texts.portfolio, parse_mode='Markdown', disable_web_page_preview=True)