from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, TimeField, FloatField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired


class RenameRegulationForm(FlaskForm):
    name = StringField('Новое наименование', validators=[DataRequired()])
    rename = SubmitField('Сохранить')


class AddBaseDocumentLink(FlaskForm):
    link = StringField('Добавить ссылку на документ с pravo.gov.ru')
    add = SubmitField('Добавить')