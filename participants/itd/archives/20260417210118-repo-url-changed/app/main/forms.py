from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectField, DateTimeField, BooleanField, SubmitField, FileField
from wtforms.validators import DataRequired
from datetime import datetime


class CreateOrder(FlaskForm):
    title = StringField(label='Название', validators=[DataRequired()])
    description = TextAreaField(label='Описание', validators=[DataRequired()])
    baseorder = IntegerField()
    file = FileField(label='Подгрузить файл')
    priority = IntegerField(label='Приоритет', default=1)
    type = SelectField(label='Тип задачи', choices=[])
    deadline = DateTimeField(label='Дэдлайн', default=datetime.now())
    interval = IntegerField(label='Интервал выполнения', default=0)
    # done = BooleanField(label='Выполнено', default=False)
    executors = SelectField(label='Исполнители', choices=[])
    submit = SubmitField('Создать')


class CreateNote(FlaskForm):
    text = TextAreaField('Текст', validators=[DataRequired()])
    submit_note = SubmitField('Сохранить')
