from datetime import datetime
from app import db, mail
from app.auth import bp
from flask_login import login_user, logout_user, current_user
from flask import render_template, redirect, url_for, flash, request
from app.models import User, Group
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from string import ascii_letters
from random import choice
from app import Config
from flask_mail import Message


@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    title = 'ТУРИСТИЧЕСКИЙ ФОРУМ «ТУРИЗМ 2.1: МЫСЛИМ ПО-НОВОМУ»'
    bot_name = Config.BOT_NAME
    if current_user.is_authenticated:
        return redirect(url_for('main.index', bot_name=bot_name))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email = form.login.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверный адрес электронной почты или пароль. Если вы не регистрировались, нажмите кнопку "ЗАРЕГИСТРИРОВАТЬСЯ" ниже')
            return redirect(url_for('auth.login'))
        login_user(user, remember=bool(form.remember_me.data))
        user.last_visit = datetime.now()
        db.session.merge(user)
        db.session.commit()
        # if not current_user.tg_id:
        #     return render_template('auth/join_telegram.html', title='Подключитесь к нашему боту', bot_name=bot_name)
        return redirect(url_for('main.index')) #, bot_name=bot_name))
    return render_template('auth/login.html', form=form, title=title) #, bot_name=bot_name)


@bp.route('/registration', methods=['GET', 'POST'])
def register():
    bot_name = Config.BOT_NAME
    invited_user = None
    if request.args:
        if 'u' in request.args:
            invited_user = User.query.get(request.args['u'])
    title = 'Регистрация'
    if current_user.is_authenticated:
        return redirect(url_for('main.index', bot_name=bot_name))
    form = RegistrationForm()
    # form.region.choices = [(region.name, region.name) for region in Region.query.all()]
    if form.validate_on_submit():
        user = User()
        user.username = form.username.data
        user.first_name = form.first_name.data
        user.last_name = ''
        user.email = form.email.data
        user.phone = form.phone.data
        user.is_bot = False
        user.role = 'user'
        user.language_code = 'ru'
        user.group = 1
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Поздравляем! Вы зарегистрированы.')
        if invited_user:
            invited_user.his_invited_users.append(user)
            db.session.commit()
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form, title=title, bot_name=bot_name)


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
            flash('Вам отправлено письмо с инструкцией по восстановлению')
        else:
            flash('Введенного адреса электронной почты не существует. Возможно, вы ошиблись.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', title='Восстановление пароля', form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Ваш пароль был восстановлен')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email(
        subject='Восстановление пароля. Амуртуризм онлайн.',
        sender=Config.MAIL_USERNAME,
        recipients=[user.email],
        text_body=render_template('email/reset_password.txt', user=user, token=token),
        html_body=render_template('email/reset_password.html', user=user, token=token)
    )
