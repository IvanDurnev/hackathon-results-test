from app.main import bp
from flask import render_template, redirect, url_for, request, send_from_directory
from flask_login import login_required, current_user
from app.admin.forms import SendTGMessageForm
from app import bot, db
from app.models import Group, ScheduledMessage, User, Message, ChatMessages
from app.telegram_bot import texts
from app.telegram_bot import routes as tg_routes
import asyncio
from datetime import datetime, timedelta
from config import Config
import time
import json
import math
import threading
from app.telegram_bot.chat_commands import send_quiz
import xlsxwriter
import os



@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    bot_name = Config.BOT_NAME
    stream_link = Config.STREAM_LINK
    vidget_prefix = Config.VIDGET_PREFIX
    if request.args:
        if 'u' in request.args:
            print(request.args['u'])
    send_tg_mes_form = SendTGMessageForm()
    if send_tg_mes_form.validate_on_submit():
        region = Group.query.filter_by(name=current_user.region).first()
        moderator = region.moderator
        if current_user.tg_id:
            text = f'{texts.tg_user_mention(current_user)} {send_tg_mes_form.text.data}'
        else:
            text = f'*{current_user.id} {current_user.username} ({current_user.first_name} {current_user.last_name}):* {send_tg_mes_form.text.data}'
        asyncio.run(bot.send_message(chat_id=moderator,
                                     text=text,
                                     parse_mode='Markdown'))
        return redirect(url_for('main.index', bot_name=bot_name))
    title = 'ТУРИСТИЧЕСКИЙ ФОРУМ «ТУРИЗМ 2.1: МЫСЛИМ ПО-НОВОМУ»'
    return render_template('index.html',
                           send_tg_mes_form=send_tg_mes_form,
                           bot_name=bot_name,
                           stream_link=stream_link,
                           vidget_prefix=vidget_prefix,
                           title=title)


@bp.route('/cron')
def cron():
    tasks = ScheduledMessage.query.order_by(ScheduledMessage.date_time).all()
    all_tg_users = User.query.filter(User.tg_id.is_(not None)).all()
    groups = Group.query.all()
    time_zones = {}
    for group in groups:
        time_zones[group.name] = datetime.now() + timedelta(hours=int(group.time_zone)) - timedelta(hours=int(Config.SERVER_TIME_ZONE))

    # asyncio.run(bot.send_message(chat_id=253393695, text=f'Заданий запланировано {len(tasks)}\nПользователей с телегой {len(all_tg_users)}'))

    for task in tasks:
        hasnt_received = []
        for user in list(all_tg_users):
            if user.group:
                now = time_zones[user.get_group().name]
                delta = (task.date_time-now).days
                # Если delta>0, то это сообщения будущие, их пользователь не должен видеть
                if delta < 0 and user not in task.receivers:
                    hasnt_received.append(user)
                # если delta = 0, то это сегодняшнее сообщение, оно должно уйти пользователю в то время,
                # которое указано в рассылке +- 5 минут
                elif delta >= 0:
                    # вычисляем разницу в секундах
                    delta_seconds = (task.date_time - now).total_seconds()
                    # delta_seconds - разница в секундах между текущим временем и временем запланированной рассылки
                    # пока delta_seconds больше нуля - эту рассылку пользователю высылать рано
                    if delta_seconds <= 0 and user not in task.receivers:
                        hasnt_received.append(user)

        # asyncio.run(bot.send_message(chat_id=253393695,
        #                              text=f'Сообщение {json.loads(task.text)}:\n'
        #                                   f'Отправлено {len(task.receivers)} пользователям\n'
        #                                   f'Не отправлено {len(hasnt_received)} пользователям'))

        if len(hasnt_received)>0:
            thr = threading.Thread(target=send_scheduled_message, args=(task, hasnt_received,))
            thr.start()

    return 'ok'


def send_scheduled_message(task, receivers):
    from app import create_app
    app = create_app(config_class=Config)
    app.app_context().push()

    current_task = ScheduledMessage.query.get(task.id)
    for user in receivers:
        cur_user = User.query.get(user.id)
        current_task.receivers.append(cur_user)
        db.session.commit()

    t00 = time.time()
    text = json.loads(task.text)
    receivers_number = len(receivers)

    # Разбиваем всех пользователей на группы по x чел
    x = 30
    groups = []
    for i in range(math.ceil(receivers_number/x)):
        groups.append([])
        for j in range(x):
            try:
                groups[i].append(receivers.pop())
            except IndexError:
                break
            except KeyError:
                break

    i = 0
    for index, group in enumerate(groups):
        t0 = time.time()

        if task.message_type == 'text':
            asyncio.run(bot.send_messages_list(users=group, text=text, parse_mode=''))
        elif task.message_type == 'photo':
            asyncio.run(bot.send_photo(chat_id=group, photo=task.content_link, caption=text, parse_mode=''))
        elif task.message_type == 'video':
            asyncio.run(bot.send_video(chat_id=group, video=task.content_link, caption=text, parse_mode=''))
        elif task.message_type == 'poll':
            asyncio.run(send_quiz(int(json.loads(task.text)), group))


        time.sleep(1)
        # asyncio.run(bot.send_message(chat_id=253393695,
        #                              text=f'Рассылка {task.id} отправлена {index + 1}/{len(groups)} группе за {time.time() - t0}'))
        print(f'Рассылка {task.id} отправлена {index + 1}/{len(groups)} группе за {time.time() - t0}')
    print(f'Задача завершена за {(time.time()-t00)/60} минут')
    # asyncio.run(bot.send_message(chat_id=253393695,
    #                              text=f'Рассылка\n {text} отправлена {receivers_number} пользователям за {(time.time()-t00)/60} минут'))
    # app.app_context().pop()
    return 'ok'


@bp.route('/api', methods=['GET', 'POST'])
def api():
    try:
        message = request.json
        user = User.query.get(int(message['data']['user']))
        user_mention = texts.tg_user_mention(user)
        text = message['data']['message']
        moderators = list(user.get_group().moderators)

        message = Message()
        message.type = 'text'
        message.content = json.dumps({
            'message': {
                'text': text,
                'from': {
                    'id': user.id
                }
            }
        })
        message.local_link = ''
        message.file_id = ''
        message.date_time = datetime.now()
        message.direction = 'output'
        message.user_id = user.id
        db.session.add(message)
        db.session.commit()

        buttons = [
            {
                'text': 'В эфир',
                'data': f'alertMessage_{message.id}'
            },
            {
                'text': 'Удалить',
                'data': f'deleteMessage_{message.id}'
            }
        ]
        map = tg_routes.create_button_map(buttons, 2)
        reply_markup = tg_routes.get_inline_menu(map)

        asyncio.run(bot.send_messages_list(users=moderators,
                                           text=f'{user_mention} {text}',
                                           reply_markup=reply_markup,
                                           parse_mode='Markdown'))

    except:
        return 'без вложения'
    return 'ok'


@bp.route('/update_chat', methods=['GET', 'POST'])
def update_user_chat():
    try:
        req = json.loads(request.data)['request']
        messages_dict = {'data': []}
        response = ''
        if req == 'marquee2':
            current_message = ChatMessages.query.order_by(ChatMessages.id).filter(ChatMessages.shown.is_(False)).first()
            message_type = tg_routes.get_req_type(json.loads(Message.query.get(current_message.message_id).content))
            if message_type == 'text':
                username = User.query.get(Message.query.get(current_message.message_id).user_id).username
                text = json.loads(Message.query.get(current_message.message_id).content)['message']['text']
                messages_dict['data'].append({'user': username, 'text': text})
                current_message.shown = True
                db.session.commit()
            if message_type == 'photo':
                try:
                    photozone = current_message.description.count('фотозона')
                except:
                    photozone = 0
                if not photozone:
                    username = User.query.get(Message.query.get(current_message.message_id).user_id).username
                    text = ''
                    try:
                        text = json.loads(Message.query.get(current_message.message_id).content)['message']['caption']
                    except:
                        pass
                    link = ''
                    try:
                        link = './static'+Message.query.get(current_message.message_id).local_link.split('static')[1]
                    except:
                        pass
                    messages_dict['data'].append({'user': username, 'text': text, 'link': link})
                    current_message.shown = True
                    db.session.commit()
            response = json.dumps(messages_dict)
            return response
        elif req == 'chat' or req == 'marquee':
            messages_list = []
            if req == 'chat':
                messages_list = Message.query.order_by(Message.id.desc()).limit(50)
            if req == 'marquee':
                messages_list = Message.query.filter(Message.type.ilike('text')).order_by(Message.id.desc()).limit(20)
            for message in messages_list:
                message_type = tg_routes.get_req_type(json.loads(message.content))
                if message_type == 'text' and message.direction == 'output':
                    username = User.query.get(message.user_id).username
                    text = json.loads(message.content)['message']['text']
                    messages_dict['data'].append({'user': username, 'text': text})
                if message_type == 'photo' and message.direction == 'output':
                    username = User.query.get(message.user_id).username
                    text = ''
                    try:
                        text = json.loads(message.content)['message']['caption']
                    except:
                        pass
                    link=''
                    try:
                        link = './static'+message.local_link.split('static')[1]
                    except:
                        pass
                    messages_dict['data'].append({'user': username, 'text': text, 'link': link})
            response = json.dumps(messages_dict)
            return response
        elif req == 'photozone':
            current_message = ChatMessages.query\
                .order_by(ChatMessages.id)\
                .filter(ChatMessages.description.contains('фотозона'), ChatMessages.shown.is_(False)).first()

            message_type = tg_routes.get_req_type(json.loads(Message.query.get(current_message.message_id).content))
            if message_type == 'photo':
                username = User.query.get(Message.query.get(current_message.message_id).user_id).username
                try:
                    link = './static' + Message.query.get(current_message.message_id).local_link.split('static')[1]
                except:
                    link = ''
                messages_dict['data'].append({'user': username, 'text': '', 'link': link})
                current_message.shown = True
                db.session.commit()
            response = json.dumps(messages_dict)
            return response
    except:
        return 'не грузит'


@bp.route('/chat', methods=['GET', 'POST'])
def user_chat():
    vidget_prefix = Config.VIDGET_PREFIX
    return render_template('__chat.html', vidget_prefix=vidget_prefix)


@bp.route('/marquee', methods=['GET', 'POST'])
def marquee():
    vidget_prefix = Config.VIDGET_PREFIX
    return render_template('marquee.html', vidget_prefix=vidget_prefix)


@bp.route('/marquee2', methods=['GET', 'POST'])
def marquee2():
    vidget_prefix = Config.VIDGET_PREFIX
    return render_template('marquee2.html', vidget_prefix=vidget_prefix)


@bp.route('/photozone', methods=['GET', 'POST'])
def photozone():
    vidget_prefix = Config.VIDGET_PREFIX
    return render_template('photozone.html', vidget_prefix=vidget_prefix)


@bp.route('/serv', methods=['GET', 'POST'])
def serv():
    users = User.query.all()
    workbook = xlsxwriter.Workbook(os.path.join(Config.UPLOAD_FOLDER, 'Конференция_все_пользователи.xlsx'))
    worksheet = workbook.add_worksheet()
    worksheet.write(0, 0, '№')
    worksheet.write(0, 1, 'Имя')
    worksheet.write(0, 2, 'E-mail')
    worksheet.write(0, 3, 'Телефон')
    worksheet.write(0, 4, 'Организация')
    for index, user in enumerate(users):
        worksheet.write(index + 1, 0, str(index+1))
        worksheet.write(index + 1, 1, user.username)
        worksheet.write(index + 1, 2, user.email)
        worksheet.write(index + 1, 3, user.phone)
        worksheet.write(index + 1, 3, user.first_name)
    workbook.close()

    return send_from_directory(directory=Config.UPLOAD_FOLDER, filename='Конференция_все_пользователи.xlsx', as_attachment=True)

