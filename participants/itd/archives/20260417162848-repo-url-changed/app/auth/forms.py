from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, IntegerField
from wtforms.fields.html5 import TelField, EmailField
from wtforms.validators import DataRequired, EqualTo, ValidationError, Email
from app.models import User


class LoginForm(FlaskForm):
    login = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('ВОЙТИ')


class RegistrationForm(FlaskForm):
    username = StringField('Ваши ФИО', validators=[DataRequired()])
    email = EmailField('Ваш email', validators=[DataRequired()])
    organization = StringField('Ваше место работы', validators=[DataRequired()])
    position = StringField('Ваша должность', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password', message='Пароли не совпадают')])
    submit = SubmitField('ЗАРЕГИСТРИРОВАТЬСЯ')

    def validate_username(self, username):
        no_spaces = username.data.replace(' ', '')
        if no_spaces == '':
            raise ValidationError('Имя пользователя не может состоять только из пробелов')
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Пользователь с таким номером уже есть в системе, выберете другое.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Пользователь с такой почтой уже есть в системе.')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Ваш e-mail', validators=[DataRequired(), Email()])
    submit = SubmitField('Восстановить')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Новый пароль', validators=[DataRequired()])
    password2 = PasswordField('Повторите новый пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Сохранить')