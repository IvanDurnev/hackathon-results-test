from app import db, mail
from app.auth import bp
from flask_login import login_user, logout_user, current_user
from flask import render_template, redirect, url_for, flash, request
from app.models import User, Regulation
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from app import Config
from flask_mail import Message


@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    title = 'Присоединиться'
    all_regulations = Regulation.query.all()
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email = form.login.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверное имя пользователя или пароль. '
                  'Если вы не регистрировались, нажмите кнопку "ЗАРЕГИСТРИРОВАТЬСЯ" ниже')
            return redirect(url_for('auth.login'))
        login_user(user, remember=bool(form.remember_me.data))
        return redirect(url_for('main.index'))
    return render_template('auth/login.html', form=form, title=title, all_regulations=all_regulations)


@bp.route('/registration', methods=['GET', 'POST'])
def register():
    title = 'Регистрация'
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.organization = form.organization.data
        user.position = form.position.data
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Поздравляем! Вы зарегистрированы.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form, title=title)


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
        subject='Признание 2019. Восстановление пароля',
        sender=Config.MAIL_USERNAME,
        recipients=[user.email],
        text_body=render_template('email/reset_password.txt', user=user, token=token),
        html_body=render_template('email/reset_password.html', user=user, token=token)
    )