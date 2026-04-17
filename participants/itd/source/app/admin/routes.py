import json
import os
from datetime import datetime, timedelta
from app import db, bot
from app.admin import bp
from app.models import User, Group, Tag
from app.admin.forms import ChangeWebhookForm, SendTGMessageForm, CreateGroupForm, CreateModerForm, SearchUserForm
from config import Config
from flask_login import login_required, current_user
from flask import render_template, redirect, url_for, request, flash

from telegram import TelegramError


@bp.route('/admin')
@login_required
def admin():
    if current_user.role == 'admin' or current_user.role == 'moderator':
        return render_template('admin/admin.html',
                               title='Админка')
    else:
        return redirect(url_for('main.index'))


@bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if current_user.role == 'admin' or current_user.role == 'moderator':
        webhook_form = ChangeWebhookForm()
        if webhook_form.validate_on_submit():
            try:
                bot.set_webhook(url=webhook_form.url.data)
                flash(f'Вебхук установлен на {webhook_form.url.data}')
            except(TelegramError):
                flash(f'Вебхук не установлен. Ошибка {str(TelegramError)}')
        webhook_form.url.data = url_for('telegram_bot.telegram', _external=True)
        return render_template('admin/admin_settings.html', title='Настройки', form=webhook_form)
    else:
        return redirect(url_for('main.index'))


@bp.route('/user/<id>', methods=['GET', 'POST'])
@login_required
def user_detailed(id):
    send_tg_mes_form = SendTGMessageForm()
    user = User.query.filter_by(id=int(id)).first()
    tags = Tag.query.all()

    unread_messages = user.new_messages()
    for message in unread_messages:
        message.seen = True
        db.session.commit()
    messages = []

    for message in user.all_messages():
        text = content = ''
        if message.type == 'text':
            try:
                text = json.loads(message.content)['text']
            except:
                text = ''
        if message.type == 'photo':
            try:
                text = json.loads(message.content)['caption']
            except:
                text = ''
            try:
                content = os.path.join('static', message.local_link.split('static')[1])
            except:
                pass
        if message.type == 'video':
            try:
                text = json.loads(message.content)['caption']
            except:
                text = ''
            try:
                content = os.path.join('static', message.local_link.split('static')[1])
            except:
                pass
        if message.type == 'voice':
            try:
                text = json.loads(message.content)['message']['caption']
            except:
                text = ''
            try:
                content = os.path.join('static', message.local_link.split('static')[1])
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


    if send_tg_mes_form.validate_on_submit():
        if send_tg_mes_form.submit.data and send_tg_mes_form.validate():
            text = send_tg_mes_form.text.data
            response = bot.send_message(chat_id=user.tg_id, text=text, parse_mode='Markdown')
            return redirect(url_for('admin.user_detailed', id=user.id))
    return render_template('admin/user_detailed.html',
                           user=user,
                           send_tg_mes_form=send_tg_mes_form,
                           title=f'Личные сообщения пользователя {user.first_name}',
                           user_messages=messages)


@bp.route('/admin/users_list', methods=['GET', 'POST'])
@login_required
def users_list():
    all_users_count = len(User.query.all())
    # Пагинация пользователей
    page = request.args.get('page', 1, type=int)
    users: User = User.query.order_by('id').paginate(page, Config.USERS_PER_PAGE, False)
    next_url = url_for('admin.users_list', id='all', page=users.next_num) if users.has_next else None
    prev_url = url_for('admin.users_list', id='all', page=users.prev_num) if users.has_prev else None


    # Форма поиска
    search_user_form = SearchUserForm()
    if search_user_form.validate_on_submit():
        if search_user_form.search.data:
            users: User = User.query.filter(User.first_name.contains(search_user_form.name.data)).order_by(
                'id').paginate(page, Config.USERS_PER_PAGE, False)

    return render_template('admin/users_all.html',
                           users=users.items,
                           all_users_count=all_users_count,
                           next_url=next_url,
                           prev_url=prev_url,
                           search_user_form=search_user_form)


@bp.route('/admin/user_view_settings', methods=['GET', 'POST'])
@login_required
def user_view_settings():
    if current_user.role == 'admin' or current_user.role == 'moderator':
        return render_template('admin/user_view_settings.html', title='Настройки внешнего вида платформы')
    else:
        return redirect(url_for('main.index'))



@bp.route('/add_tag_<user_id>_<tag_id>', methods=['GET','POST'])
def add_user_tag(user_id, tag_id):
    user = User.query.get(user_id)
    tag = Tag.query.get(tag_id)
    user.tags.append(tag)
    db.session.commit()
    return redirect(url_for('admin.users_list'))


@bp.route('/del_tag_<user_id>_<tag_id>', methods=['GET','POST'])
def del_user_tag(user_id, tag_id):
    user = User.query.get(user_id)
    tag = Tag.query.get(tag_id)
    user.tags.remove(tag)
    db.session.commit()
    return redirect(url_for('admin.users_list'))


@bp.route('/moderation', methods=['GET', 'POST'])
@login_required
def moderation():
    if current_user.role == 'admin':
        groups = Group.query.all()
        admins = User.query.filter_by(role='admin').all()

        current_time = {}

        create_moderator_form = CreateModerForm()
        for group in groups:
            current_time[group.name] = datetime.now() + timedelta(hours=int(group.time_zone)) - timedelta(hours=int(Config.SERVER_TIME_ZONE))

        if create_moderator_form.validate_on_submit():
            if create_moderator_form.submit.data and create_moderator_form.validate():
                for group in create_moderator_form.group.data:
                    gr = Group.query.get(group.id)
                    us = User.query.get(create_moderator_form.user.data.id)
                    gr.moderators.append(us)
                    db.session.commit()
                return redirect(request.referrer)

        create_group_form = CreateGroupForm()
        if create_group_form.validate_on_submit():
            if create_group_form.submit.data and create_group_form.validate():
                group = Group()
                group.name = create_group_form.name.data
                db.session.add(group)
                db.session.commit()
                return redirect(request.referrer)

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
    return redirect(url_for('admin.users_list'))


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
