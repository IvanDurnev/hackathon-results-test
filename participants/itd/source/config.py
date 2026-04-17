import os
from dotenv import load_dotenv


basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config(object):
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'key-secret-secret'
    TG_TOKEN = os.environ.get('TG_TOKEN') or None
    TG_ADMIN = os.environ.get('TG_ADMIN') or None

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    USERS_PER_PAGE = 20
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'ogg', 'mp4', 'avi'}
    SERVER_TIME_ZONE = os.environ.get('SERVER_TIME_ZONE') or 0
    BOT_NAME = os.environ.get('BOT_NAME')
    STREAM_LINK = os.environ.get('STREAM_LINK')
    VIDGET_PREFIX = os.environ.get('VIDGET_PREFIX')

    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.yandex.ru'
    MAIL_PORT = os.environ.get('MAIL_PORT') or 465
    # MAIL_USE_SSL = 1
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
