from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateTimeField, IntegerField, TextAreaField, FileField, \
    BooleanField
from wtforms.fields import SelectField
from wtforms.validators import DataRequired


class ChangeWebhookForm(FlaskForm):
    url = StringField('Webhook URL', validators=[DataRequired()])
    submit = SubmitField('set webhook')


class ScheduledMessageCreateForm(FlaskForm):
    task_type = SelectField('Тип планирования',
                                choices=[('Абсолютное', 'Абсолютное'), ('Относительное', 'Относительное')])
    message_type = SelectField('Тип сообщения', choices=[('text', 'Текст'), ('photo', 'Фото'), ('video', 'Видео'), ('poll', 'Опрос')])
    date_time = DateTimeField('Дата и время отправки')
    interval = IntegerField('Через какой промежуток после регистрации пользователя отправлять?\n'
                            'В минутах. Сутки = 1440')
    text = TextAreaField('Текст сообщения')
    content_link = FileField('Ссылка на вложение')
    submit = SubmitField('Запланировать')


class SendTGMessageForm(FlaskForm):
    text = TextAreaField('Текст', validators=[DataRequired()])
    submit = SubmitField('Отправить')


class SendGroupTGMessageForm(FlaskForm):
    groups = SelectField('Регион', choices=[('всем', 'всем')])
    prizers = SelectField('Награждаемый/ненаграждаемый', choices=[('всем', 'всем'), ('награждаемым','награждаемым'), ('ненаграждаемым','ненаграждаемым')])
    text = TextAreaField('Текст', validators=[DataRequired()])
    submit = SubmitField('Отправить')


class CreateGroupForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    submit = SubmitField('Добавить')


class CreateModerForm(FlaskForm):
    group = StringField('Группа')
    tg_id = IntegerField('Пользователь')
    submit = SubmitField('Добавить')


class CreateQuestionForm(FlaskForm):
    question_type = SelectField('Тип вопроса', choices=[('text','text'),('photo', 'photo'),('video', 'video')])
    question_text = StringField('Текст вопроса', validators=[DataRequired()])
    variants = TextAreaField('Варианты ответов')
    question_content = FileField('Ссылка на вложение')
    answer_type = SelectField('Тип ответа', choices=[('text','text'),('photo', 'photo'),('video', 'video')])
    answer_text = StringField('Текст ответа', validators=[DataRequired()])
    answer_content = FileField('Ссылка на вложение')
    save_question = SubmitField('Добавить')


class EditQuizForm(FlaskForm):
    quiz_name = StringField('Название викторины')
    quiz_description = TextAreaField('Сообщение перед началом')
    quiz_final_text = TextAreaField('Сообщение после окончания')
    save_quiz = SubmitField('Сохранить')


class SearchUserForm(FlaskForm):
    name = StringField('ФИО')
    search = SubmitField('Найти')