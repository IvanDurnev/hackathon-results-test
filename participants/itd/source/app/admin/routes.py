import asyncio
from app import db, bot
from config import Config
from app.models import ScheduledMessage, User, Group, Quiz, Question, Award, ChatMessages
from app.admin import bp
from app.telegram_bot import chat_commands, routes as tg_routes
from app.telegram_bot.routes import create_button_map, get_inline_menu
from flask_login import login_required, current_user
from flask import render_template, redirect, url_for, request, send_from_directory, after_this_request
from app.admin.forms import ChangeWebhookForm, ScheduledMessageCreateForm, SendTGMessageForm, SendGroupTGMessageForm,\
    CreateGroupForm, CreateModerForm, CreateQuestionForm, EditQuizForm, SearchUserForm
import json
import os
from werkzeug.utils import secure_filename
from pprint import pprint
# import cv2
from datetime import datetime, timedelta
import threading
import math
import time
import zipfile
from shutil import copyfile, rmtree
import cv2


@bp.route('/admin')
@login_required
def admin():
    if current_user.role == 'admin' or current_user.role == 'moderator':
        send_group_tg_mes_form = SendGroupTGMessageForm()
        return render_template('admin/admin.html',
                               send_group_tg_mes_form=send_group_tg_mes_form,
                               title='Админка')
    else:
        return redirect(url_for('main.index'))


@bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if current_user.role == 'admin' or current_user.role == 'moderator':
        webhook_form = ChangeWebhookForm()
        if webhook_form.validate_on_submit():
            # response = bot.set_webhook(url_for('telegram', _external=True))
            # print(url_for('telegram', _external=True))
            response = bot.set_webhook(webhook_form.url.data)
            # response = bot.set_webhook('https://bbcf431f.ngrok.io/telegram')
            return response
        return render_template('admin/admin_settings.html', title='Настройки', form=webhook_form)
    else:
        return redirect(url_for('main.index'))


@bp.route('/admin/message_schedule', methods=['GET', 'POST'])
@login_required
def message_schedule():
    if current_user.role == 'admin' or current_user.role == 'moderator':
        create_task_form = ScheduledMessageCreateForm()
        scheduled_messages = ScheduledMessage.query.order_by(ScheduledMessage.date_time).all()
        if create_task_form.validate_on_submit():
            task = ScheduledMessage()
            task.task_type = create_task_form.task_type.data
            task.message_type = create_task_form.message_type.data
            task.date_time = create_task_form.date_time.data
            task.interval = create_task_form.interval.data
            task.text = json.dumps(create_task_form.text.data)
            if task.message_type != 'text' and task.message_type != 'poll':
                f = create_task_form.content_link.data
                filename = f.filename
                if not os.path.exists(os.path.join(Config.UPLOAD_FOLDER, 'photos')):
                    os.makedirs(os.path.join(Config.UPLOAD_FOLDER, 'photos'))
                f.save(os.path.join(Config.UPLOAD_FOLDER, 'photos', filename))
                task.content_link = os.path.join(Config.UPLOAD_FOLDER, 'photos', filename)
            else:
                task.content_link = ''
            db.session.add(task)
            db.session.commit()
            return redirect(url_for('admin.message_schedule'))
        for mes in scheduled_messages:
            mes.text = json.loads(mes.text)
        return render_template('admin/message_schedule.html',
                               title='Предустановленные сообщения',
                               form=create_task_form,
                               scheduled_messages=scheduled_messages)
    else:
        return redirect(url_for('main.index'))


@bp.route('/admin/message_schedule/delete_<id>', methods=['GET', 'POST'])
@login_required
def delete_task(id):
    if current_user.role == 'admin' or current_user.role == 'moderator':
        task = ScheduledMessage.query.get(id)
        db.session.delete(task)
        db.session.commit()
        return redirect(url_for('admin.message_schedule'))
    else:
        return redirect(url_for('main.index'))


@bp.route('/user_<id>_<search_str>', methods=['GET', 'POST'])
@login_required
def users_info(id, search_str='*'):

    send_tg_mes_form = SendTGMessageForm()
    send_group_tg_mes_form = SendGroupTGMessageForm()
    regions = Group.query.all()
    scheduled_messages = ScheduledMessage.query.all()
    awards = Award.query.all()

    for group in regions:
        send_group_tg_mes_form.groups.choices.append((group.name, group.name))

    if id != 'all':
        user = User.query.filter_by(id=int(id)).first()
        unread_messages = user.new_messages()
        for message in unread_messages:
            message.seen = True
            db.session.commit()
        messages = []
        for message in user.all_messages():
            text = content = ''
            if message.type == 'text':
                text = json.loads(message.content)['message']['text']
            if message.type == 'photo':
                try:
                    text = json.loads(message.content)['message']['caption']
                except:
                    text = ''
                try:
                    content = 'static'+os.path.join(Config.UPLOAD_FOLDER, str(message.local_link).split('static')[1])
                # content = bot.get_link(json.loads(message.content)['message']['photo'][
                #                            len(json.loads(message.content)['message']['photo']) - 1]['file_id'])
                except:
                    pass
            if message.type == 'video':
                try:
                    text = json.loads(message.content)['message']['caption']
                except:
                    text = ''
                try:
                    content = 'static'+os.path.join(Config.UPLOAD_FOLDER, str(message.local_link).split('static')[1])
                # content = bot.get_link(json.loads(message.content)['message']['video']['file_id'])
                except:
                    pass
            if message.type == 'voice':
                try:
                    text = json.loads(message.content)['message']['caption']
                except:
                    text = ''
                try:
                    content = 'static'+os.path.join(Config.UPLOAD_FOLDER, str(message.local_link).split('static')[1])
                # content = bot.get_link(json.loads(message.content)['message']['voice']['file_id'])
                except:
                    pass

            user_message = {
                'type': message.type,
                'seen': message.seen,
                'date_time': message.date_time,
                'text': text,
                'content': content,
                'direction': message.direction
            }
            messages.append(user_message)

        received_scheduled_messages = []
        for sm in scheduled_messages:
            if user in sm.receivers:
                received_scheduled_messages.append(sm)

        if send_tg_mes_form.validate_on_submit():
            if send_tg_mes_form.submit.data and send_tg_mes_form.validate():
                text = send_tg_mes_form.text.data
                asyncio.run(bot.send_message(chat_id=user.tg_id, text=text))
                asyncio.run(chat_commands.save_income_message([user], text))
                return redirect(url_for('admin.users_info', id=user.id, search_str=search_str))
        return render_template('admin/user_detailed.html',
                               user=user,
                               send_tg_mes_form=send_tg_mes_form,
                               title=f'{user}',
                               user_messages=messages,
                               received_scheduled_messages=received_scheduled_messages)
    elif id == 'all':
        search_user_form = SearchUserForm()
        if search_user_form.validate_on_submit() and search_user_form.search.data:
            if search_user_form.name.data:
                return redirect(url_for('admin.users_info', id='all', search_str=search_user_form.name.data))
            else:
                return redirect(url_for('admin.users_info', id='all', search_str='*'))
        page = request.args.get('page', 1, type=int)
        # users = User.query.paginate(page, Config.USERS_PER_PAGE, False)
        moder_groups = []
        users = []
        all_users = User.query.all()
        for group in current_user.moderation_groups:
            moder_groups.append(group.id)
        for user in all_users:
            if user.group in moder_groups or not user.group:
                if search_str != '*' and search_str != ' ' and search_str:
                    if user.username.find(search_str) > -1:
                        users.append(user)
                else:
                    users.append(user)
        # for user in users.items:
        #     if not user.group in moder_groups:
        #         users.items.remove(user)
        # next_url = url_for('admin.users_info', id='all', page=users.next_num) if users.has_next else None
        # prev_url = url_for('admin.users_info', id='all', page=users.prev_num) if users.has_prev else None
        if send_group_tg_mes_form.validate_on_submit():
            if send_group_tg_mes_form.submit.data and send_group_tg_mes_form.validate():
                text = send_tg_mes_form.text.data
                users = []
                all_tg_users = User.query.filter(User.tg_id.is_(not None)).all()
                if send_group_tg_mes_form.groups.data == 'всем' and send_group_tg_mes_form.prizers.data == 'всем':
                    for user in all_tg_users:
                        users.append(user)
                elif send_group_tg_mes_form.groups.data == 'всем' and send_group_tg_mes_form.prizers.data != 'всем':
                    if send_group_tg_mes_form.prizers.data == 'награждаемым':
                        for user in all_tg_users:
                            if user.awards:
                               users.append(user)
                    elif send_group_tg_mes_form.prizers.data == 'ненаграждаемым':
                        for user in all_tg_users:
                            if not user.awards:
                                users.append(user)
                elif send_group_tg_mes_form.groups.data != 'всем' and send_group_tg_mes_form.prizers.data == 'всем':
                    all_tg_users = User.query.filter(User.region.ilike(send_group_tg_mes_form.groups.data), User.tg_id.is_(not None)).all()
                    for user in all_tg_users:
                        users.append(user)
                elif send_group_tg_mes_form.groups.data != 'всем' and send_group_tg_mes_form.prizers.data != 'всем':
                    all_tg_users = User.query.filter(User.region.ilike(send_group_tg_mes_form.groups.data), User.tg_id.is_(not None)).all()
                    if send_group_tg_mes_form.prizers.data == 'награждаемым':
                        for user in all_tg_users:
                            if user.awards:
                                users.append(user)
                    elif send_group_tg_mes_form.prizers.data == 'ненаграждаемым':
                        for user in all_tg_users:
                            if not user.awards:
                                users.append(user)
                receivers_count = len(users)

                asyncio.run(chat_commands.save_income_message(users, text))
                if receivers_count > 0:
                    thr = threading.Thread(target=send_messages_in_background, args=(users, text,))
                    thr.start()

                asyncio.run(bot.send_message(current_user.tg_id,
                                             f'{current_user.first_name}, твоё сообщение\n'
                                             f'"{text}"\n'
                                             f'отправлено *{receivers_count}* пользователям.\n'
                                             f'*Регион:* _{send_group_tg_mes_form.groups.data}_\n'
                                             f'*Критерий "награда":* _{send_group_tg_mes_form.prizers.data}_',
                                             parse_mode='Markdown'))
                return redirect(url_for('admin.users_info', id='all', search_str='*'))

        return render_template('admin/users_all.html',
                               users=users,
                               awards=awards,
                               search_str=search_str,
                               send_group_tg_mes_form=send_group_tg_mes_form,
                               search_user_form=search_user_form)


def send_messages_in_background(users, text):
    from app import create_app
    app = create_app(config_class=Config)
    app.app_context().push()

    # Разбиваем всех пользователей на группы по x чел
    x = 30
    groups = []
    receivers_count = len(users)
    for i in range(math.ceil(receivers_count / x)):
        groups.append([])
        for j in range(x):
            try:
                groups[i].append(users.pop())
            except IndexError:
                break
            except KeyError:
                break

    for index, group in enumerate(groups):
        asyncio.run(bot.send_messages_list(users=group, text=text, parse_mode='Markdown'))
        time.sleep(1)


@bp.route('/add_award_<user_id>_<award_id>_<search_str>', methods=['GET','POST'])
def add_user_award(user_id, award_id, search_str):
    user = User.query.get(user_id)
    award = Award.query.get(award_id)
    user.awards.append(award)
    db.session.commit()
    return redirect(url_for('admin.users_info', id='all', search_str=search_str))


@bp.route('/del_award_<user_id>_<award_id>_<search_str>', methods=['GET','POST'])
def del_user_award(user_id, award_id, search_str):
    user = User.query.get(user_id)
    award = Award.query.get(award_id)
    user.awards.remove(award)
    db.session.commit()
    return redirect(url_for('admin.users_info', id='all', search_str=search_str))



@bp.route('/test_send_task_<id>')
def test_send_task(id):
    task = ScheduledMessage.query.get(id)
    text = json.loads(task.text)
    if task.message_type == 'photo':
        response = asyncio.run(bot.send_photo(chat_id=current_user.tg_id,
                                   photo=task.content_link,
                                   caption=text,
                                   parse_mode=''))
        if response:
            file_id = response.json()['result']['photo'][len(response.json()['result']['photo'])-1]['file_id']
            task.content_link = file_id
            db.session.commit()
    elif task.message_type == 'text':
        asyncio.run(bot.send_message(chat_id=current_user.tg_id,
                                     text=text,
                                     parse_mode='',
                                     disable_web_page_preview=False))
    elif task.message_type == 'video':
        try:
            file_path = task.content_link
            vid = cv2.VideoCapture(file_path)
            height = vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
            width = vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        except:
            width = 50
            height = 50
        response = asyncio.run(bot.send_video(chat_id=current_user.tg_id,
                                              video=task.content_link,
                                              caption=text,
                                              parse_mode='',
                                              width=width,
                                              height=height))
        if response:
            file_id = response.json()['result']['video']['file_id']
            task.content_link = file_id
            db.session.commit()
    elif task.message_type == 'poll':
        asyncio.run(chat_commands.send_quiz(quiz_id =int(text), users = [current_user]))
    return redirect(url_for('admin.message_schedule'))


@bp.route('/moderation', methods=['GET', 'POST'])
@login_required
def moderation():
    if current_user.role == 'admin':
        groups = Group.query.all()
        admins = User.query.filter_by(role='admin').all()
        create_group_form = CreateGroupForm()
        create_moderator_form = CreateModerForm()

        current_time = {}

        for group in groups:
            # create_moderator_form['group'].choices.append((group.id, group.name))
            current_time[group.name] = datetime.now() + timedelta(hours=int(group.time_zone)) - timedelta(hours=int(Config.SERVER_TIME_ZONE))

        if create_moderator_form.validate_on_submit():
            if create_moderator_form.submit.data and create_moderator_form.validate():
                group = Group.query.filter_by(name=create_moderator_form.group.data).first()
                print(group)
                user = User.query.filter_by(tg_id=create_moderator_form.tg_id.data).first()
                print(user)
                group.moderators.append(user)
                db.session.commit()
            return redirect(url_for('admin.moderation'))


        if create_group_form.validate_on_submit():
            if create_group_form.submit.data and create_group_form.validate():
                group = Group()
                group.name = create_group_form.name.data
                db.session.add(group)
                db.session.commit()
                return redirect(url_for('admin.moderation'))

        return render_template('admin/moderation.html', groups=groups, create_group_form=create_group_form,
                               create_moderator_form=create_moderator_form, current_time=current_time)
    else:
        return redirect(url_for('main.index'))


@bp.route('/del_moderator_<group_id>_<user_id>', methods=['GET', 'POST'])
@login_required
def del_moderator(group_id, user_id):
    group = Group.query.get(group_id)
    user = User.query.get(user_id)
    group.moderators.remove(user)
    db.session.commit()
    return redirect(url_for('admin.moderation'))


@bp.route('/del_user_<user_id>', methods=['GET', 'POST'])
@login_required
def del_user(user_id):
    user = User.query.get(user_id)
    messages = user.all_messages()
    regions = Group.query.all()
    chat_messages = ChatMessages.query.all()
    for message in messages:
        for chat_message in chat_messages:
            if message.id == chat_message.message_id:
                db.session.delete(chat_message)
        db.session.delete(message)
    for region in regions:
        if user in region.moderators:
            region.moderators.remove(user)
    for invited in user.his_invited_users:
        user.his_invited_users.remove(invited)
    db.session.commit()
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin.users_info', id='all', search_str='*'))


@bp.route('/set_role_<user_id>', methods=['GET', 'POST'])
@login_required
def set_user_role(user_id):
    user = User.query.get(user_id)
    if user.role == 'admin':
        regions = Group.query.all()
        for region in regions:
            if user in region.moderators:
                region.moderators.remove(user)
        user.role = ''
    else:
        user.role = 'admin'
    db.session.commit()
    return redirect(url_for('admin.users_info', id='all', search_str='*'))


@bp.route('/del_group_<group_id>', methods=['GET', 'POST'])
@login_required
def del_group(group_id):
    group = Group.query.get(group_id)
    users = User.query.all()
    for user in users:
        if user.group == group.id:
            user.group = f'{group.name}_удален'
    for moderator in group.moderators:
        group.moderators.remove(moderator)
    db.session.delete(group)
    db.session.commit()
    return redirect(url_for('admin.moderation'))


@bp.route('/quiz_list', methods=['GET', 'POST'])
@login_required
def quiz_list():
    quizes = Quiz.query.all()
    create_question_form = CreateQuestionForm()
    if create_question_form.validate_on_submit():
        print('Создаем вопрос')
    return render_template('admin/quiz_list.html', quizes=quizes, create_question_form=create_question_form)


@bp.route('/create_quiz_<quiz_id>', methods=['GET', 'POST'])
@login_required
def create_quiz(quiz_id):
    if quiz_id == 'new':
        quiz = Quiz()
        quiz.name = f'Новая_{len(Quiz.query.all())+1}'
        db.session.add(quiz)
        db.session.commit()
        return redirect(url_for('admin.create_quiz', quiz_id=quiz.id))
    else:
        quiz = Quiz.query.get(quiz_id)
        create_question_form = CreateQuestionForm()
        edit_quiz_form = EditQuizForm()
        quiz_files_catalog = f'app/static/uploads/quiz/{quiz.id}'

        if edit_quiz_form.validate_on_submit() and edit_quiz_form.save_quiz.data:

            quiz.name = edit_quiz_form.quiz_name.data

            if not edit_quiz_form.quiz_description.data:
                quiz.description = None
            else:
                quiz.description = json.dumps(edit_quiz_form.quiz_description.data)

            if edit_quiz_form.quiz_final_text.data == '':
                quiz.final_text = None
            else:
                quiz.final_text = json.dumps(edit_quiz_form.quiz_final_text.data)
            db.session.commit()
            return redirect(url_for('admin.create_quiz', quiz_id=quiz.id))

        if create_question_form.validate_on_submit() and create_question_form.save_question.data:
            question = Question()
            question.question_type = create_question_form.question_type.data
            question.question_text = create_question_form.question_text.data
            question.question_variants = create_question_form.variants.data
            if question.question_type != 'text':
                # проверили, что есть каталог или создали
                if not os.path.exists(quiz_files_catalog):
                    os.makedirs(quiz_files_catalog)
                f = create_question_form.question_content.data
                filename = f.filename
                f.save(os.path.join(quiz_files_catalog, filename))
                question.question_content_link = os.path.join(quiz_files_catalog, filename)

                if question.question_type == 'photo':
                    response = asyncio.run(bot.send_photo(chat_id=current_user.tg_id,
                                                          photo=question.question_content_link,
                                                          caption=f'Викторина {quiz_id}, вопрос {question.question_text}'))
                    pprint(response.json())
                    question.question_content = response.json()['result']['photo'][len(response.json()['result']['photo'])-1]['file_id']
                elif question.question_type == 'video':
                    response = asyncio.run(bot.send_video(chat_id=current_user.tg_id,
                                                          video=question.question_content_link,
                                                          caption=f'Викторина {quiz_id}, вопрос {question.question_text}'))
                    question.question_content = response.json()['result']['video']['file_id']
            else:
                question.question_content_link = ''
                question.question_content = ''
            question.answer_type = create_question_form.answer_type.data
            question.answer_text = create_question_form.answer_text.data
            if question.answer_type != 'text':
                if not os.path.exists(quiz_files_catalog):
                    os.makedirs(quiz_files_catalog)
                f = create_question_form.answer_content.data
                filename = f.filename
                f.save(os.path.join(quiz_files_catalog, filename))
                question.answer_content_link = os.path.join(quiz_files_catalog, filename)
                if question.answer_type == 'photo':
                    response = asyncio.run(bot.send_photo(chat_id=current_user.tg_id,
                                                          photo=question.answer_content_link,
                                                          caption=f'Викторина {quiz_id}, ответ {question.answer_text}'))
                    pprint(response.json())
                    question.answer_content = \
                    response.json()['result']['photo'][len(response.json()['result']['photo']) - 1]['file_id']
                elif question.answer_type == 'video':
                    response = asyncio.run(bot.send_video(chat_id=current_user.tg_id,
                                                          video=question.answer_content_link,
                                                          caption=f'Викторина {quiz_id}, ответ {question.answer_text}'))
                    question.answer_content = response.json()['result']['video']['file_id']
            else:
                question.answer_content = ''
                question.answer_content_link = ''
            db.session.add(question)
            quiz.questions.append(question)
            db.session.commit()
            return redirect(url_for('admin.create_quiz', quiz_id=quiz.id, edit_quiz_form=edit_quiz_form))

        if quiz.description:
            edit_quiz_form.quiz_description.data = json.loads(quiz.description)
        if quiz.final_text:
            edit_quiz_form.quiz_final_text.data = json.loads(quiz.final_text)


        return render_template('admin/create_quiz.html', quiz=quiz, create_question_form=create_question_form, edit_quiz_form=edit_quiz_form)


@bp.route('/send_quiz_<quiz_id>_<user_id>', methods=['GET', 'POST'])
@login_required
def send_quiz(quiz_id, user_id):
    user = User.query.get(user_id)
    asyncio.run(chat_commands.send_quiz(quiz_id, [user]))
    return redirect(url_for('admin.create_quiz', quiz_id=quiz_id))


@bp.route('/del_question_<quiz_id>_<question_id>', methods=['GET', 'POST'])
@login_required
def del_question(quiz_id, question_id):
    question = Question.query.get(question_id)
    if question.question_content_link and os.path.exists(question.question_content_link):
        os.remove(question.question_content_link)
    if question.answer_content_link and os.path.exists(question.answer_content_link):
        os.remove(question.answer_content_link)
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for('admin.create_quiz', quiz_id=quiz_id))


@bp.route('/del_quiz_<quiz_id>', methods=['GET', 'POST'])
@login_required
def del_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    for question in quiz.questions:
        if question.question_content_link and os.path.exists(question.question_content_link):
            os.remove(question.question_content_link)
        if question.answer_content_link and os.path.exists(question.answer_content_link):
            os.remove(question.answer_content_link)
        db.session.delete(question)
    db.session.commit()
    db.session.delete(quiz)
    db.session.commit()
    return redirect(url_for('admin.quiz_list'))


@bp.route('/uploads/<path:filename>', methods=['GET', 'POST'])
@login_required
def uploads(filename):
    users = User.query.all()
    if filename == '*':
        files = os.listdir(Config.UPLOAD_FOLDER)
        filename = ''
    else:
        if os.path.isfile(os.path.join(Config.UPLOAD_FOLDER, filename)):
            current_file = os.path.join(Config.UPLOAD_FOLDER, filename)
            for user in users:
                for message in user.all_messages():
                    if message.local_link == current_file:
                        return send_from_directory(directory=Config.UPLOAD_FOLDER,
                                                   filename=filename,
                                                   as_attachment=True,
                                                   attachment_filename=f'{user}_{os.path.basename(current_file)}')
            return send_from_directory(directory=Config.UPLOAD_FOLDER,
                                       filename=filename,
                                       as_attachment=True)
        else:
            files = os.listdir(os.path.join(Config.UPLOAD_FOLDER, filename))
    return render_template('admin/my_files.html',
                           files=files,
                           filename=filename)


def create_archive(dir):
    users = User.query.all()
    os.chdir(os.path.join(Config.UPLOAD_FOLDER, dir))
    z = zipfile.ZipFile(f'{dir.split("/")[-1]}.zip', 'w', zipfile.ZIP_DEFLATED)

    for root, dirs, files in os.walk(os.path.join(Config.UPLOAD_FOLDER, dir)):
        for file in files:
            owner = ''
            if file.split('.')[-1] != 'zip':
                # for user in users:
                #     messages = user.all_messages()
                #     for message in messages:
                #         if os.path.join(Config.UPLOAD_FOLDER, dir, file) == message.local_link:
                #             owner = user
                # if owner:
                #     print(owner)
                #     if not os.path.exists(str(owner)):
                #         os.mkdir(str(owner))
                #     copyfile(file, f'{str(owner)}/{file}')
                #     z.write(f'{owner}')
                #     z.write(f'{owner}/{file}')
                #     rmtree(str(owner))
                # else:
                #     z.write(file)
                z.write(file)

    z.close()
    return z.filename.split('/')[-1]


@bp.route('/download/<path:filename>', methods=['GET', 'POST'])
@login_required
def download_folder(filename):
    zip_file_name = create_archive(filename)

    # @after_this_request
    # def remove_archive(response):
    #     print('привет')
    #     os.remove(os.path.join(Config.UPLOAD_FOLDER, filename, zip_file_name))

    return send_from_directory(directory=Config.UPLOAD_FOLDER,
                               filename=os.path.join(filename, zip_file_name),
                               as_attachment=True)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def upload_file(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
        return redirect(url_for('uploaded_file',
                                filename=filename))