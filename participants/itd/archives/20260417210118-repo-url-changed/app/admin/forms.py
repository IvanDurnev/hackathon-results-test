from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateTimeField, IntegerField, TextAreaField, FileField, SelectField, SelectMultipleField
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from wtforms.validators import DataRequired
from app.models import User, Group
from app import Config


class ChangeWebhookForm(FlaskForm):
    url = StringField('Webhook URL', validators=[DataRequired()])
    submit = SubmitField('set webhook')


class SendTGMessageForm(FlaskForm):
    text = TextAreaField('Текст', validators=[DataRequired()])
    submit = SubmitField('Отправить')


class CreateGroupForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    submit = SubmitField('Добавить')


class CreateModerForm(FlaskForm):
    from app import create_app
    app = create_app(config_class=Config)
    with app.app_context():
        group = QuerySelectMultipleField('Группа',
                                         query_factory=Group.query.all,
                                         get_pk=lambda group: group.id,
                                         get_label=lambda group: group.name)
        user = QuerySelectField('Пользователь',
                                query_factory=User.query.filter(User.role == 'admin').all,
                                get_pk=lambda user: user.tg_id,
                                get_label=lambda user: user.first_name)
        submit = SubmitField('Добавить')


class SearchUserForm(FlaskForm):
    name = StringField('ФИО')
    search = SubmitField('Найти')
