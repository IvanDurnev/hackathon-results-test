from app import db, login, Config
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from random import choice
from string import ascii_letters
from datetime import datetime
import jwt
from time import time
# import app



@login.user_loader
def load_user(id):
    return User.query.get(int(id))


user_award = db.Table('user_award',
                              db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                              db.Column('award_id', db.Integer, db.ForeignKey('award.id'))
                              )


group_moderators = db.Table('group_moderators',
                              db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
                              db.Column('user_tg_id', db.Integer, db.ForeignKey('user.tg_id'))
                              )

invited_users = db.Table('invited_users',
                         db.Column('inviter', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                         db.Column('invited', db.Integer, db.ForeignKey('user.id'), primary_key=True))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tg_id = db.Column(db.Integer, index=True)
    username = db.Column(db.String(64), index=True)
    email = db.Column(db.String(100), index=True)
    phone = db.Column(db.String(18), index=True, unique=True)
    is_bot = db.Column(db.Boolean, index=True)
    first_name = db.Column(db.String(64), index=True)
    last_name = db.Column(db.String(64), index=True)
    language_code = db.Column(db.String(5), index=True)
    password_hash = db.Column(db.String(128))
    status = db.Column(db.String(12), index=True)
    role = db.Column(db.String(12), index=True)
    group = db.Column(db.Integer, db.ForeignKey('group.id'), index=True)
    his_invited_users = db.relationship('User',
                                        secondary=invited_users,
                                        primaryjoin=(invited_users.c.inviter == id),
                                        secondaryjoin=(invited_users.c.invited == id),
                                        backref=db.backref('inviter', lazy=True),
                                        lazy='dynamic')
    registered = db.Column(db.DateTime, index=True, nullable=True, default=datetime.now)
    messages = db.relationship('Message', backref='user', lazy=True)
    awards = db.relationship('Award',
                             secondary=user_award,
                             lazy='subquery',
                             backref=db.backref('awards', lazy=True))
    moderation_groups = db.relationship('Group',
                                 secondary=group_moderators,
                                 lazy='subquery',
                                 backref=db.backref('moderation_groups', lazy=True))
    user_moderators = db.relationship('User',
                                 secondary=group_moderators,
                                 lazy='subquery',
                                 backref=db.backref('my_moderators', lazy=True))
    last_visit = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def new_messages(self):
        return Message.query.filter_by(user_id=self.id, seen=False).all()

    def all_messages(self):
        return Message.query.filter_by(user_id=self.id).all()


    def get_group(self):
        if self.group:
            return Group.query.filter_by(id=self.group).first()

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {
                'reset_password': self.id,
                'exp': time() + expires_in
            },
            Config.SECRET_KEY,
            algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)


    def __repr__(self):
        return f'{self.username}'


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(30), index=True)
    time_zone = db.Column(db.Integer, default=9)
    moderators = db.relationship('User',
                                 secondary=group_moderators,
                                 lazy='subquery',
                                 backref=db.backref('moderators', lazy=True))
    users = db.relationship('User', backref='users', lazy=True)


class Award(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(30), index=True)
    description = db.Column(db.String(128), index=True)
    prizers = db.relationship('User',
                              secondary=user_award,
                              lazy='subquery',
                              backref=db.backref('prizers', lazy=True))


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.JSON, nullable=False)
    local_link = db.Column(db.String(4096), default='')
    file_id = db.Column(db.String(256), default='')
    type = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    direction = db.Column(db.String(20), nullable=False)
    date_time = db.Column(db.DateTime, default=datetime.now())
    seen = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'{self.content}'


received_messages = db.Table('received_messages',
                             db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                             db.Column('scheduled_message_id', db.Integer, db.ForeignKey('scheduled_message.id'))
                             )


class ScheduledMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_type = db.Column(db.String(20), nullable=False)
    message_type = db.Column(db.String(20), nullable=False)
    date_time = db.Column(db.DateTime)
    interval = db.Column(db.Integer)
    text = db.Column(db.String(4096), nullable=False)
    content_link = db.Column(db.String(256), nullable=False)
    receivers = db.relationship('User',
                                secondary=received_messages,
                                lazy='subquery',
                                backref=db.backref('received', lazy='subquery'))


quiz_questions = db.Table('quiz_questions',
                             db.Column('quiz_id', db.Integer, db.ForeignKey('quiz.id')),
                             db.Column('question_id', db.Integer, db.ForeignKey('question.id'))
                             )


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(4096))
    questions = db.relationship('Question',
                                secondary=quiz_questions,
                                lazy='subquery',
                                backref=db.backref('questions', lazy=True))
    final_text = db.Column(db.String(4096))


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_type = db.Column(db.String(20), nullable=False)
    question_text = db.Column(db.String(1024), nullable=False)
    question_variants = db.Column(db.String(1024), nullable=False)
    question_content = db.Column(db.String(1024))
    question_content_link = db.Column(db.String(1024))
    answer_type = db.Column(db.String(1024), nullable=False)
    answer_text = db.Column(db.String(1024), nullable=False)
    answer_content = db.Column(db.String(1024))
    answer_content_link = db.Column(db.String(1024))


class ChatMessages(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    shown = db.Column(db.Boolean)
    description = db.Column(db.String(1024))